"""
Skillberry Plugin: Dependency Tracker.

Discovers the EXTERNAL Python package dependencies of skills, tools, and
snippets — exact version + artifact hashes, transitively at maximum depth — and
writes them into a hierarchical ``extra["dependencies"]`` block. This is the
external supply-chain layer the store lacks today (it only tracks store-tool ->
store-tool links via the top-level ``dependencies`` field). See issue #224.

Resolution is HYBRID: local ``importlib.metadata`` is the source of truth (the
version the object actually runs against, plus RECORD hashes and the transitive
Requires-Dist graph); the PyPI JSON API best-effort-enriches each package with
its canonical published sha256 and an "update available" signal. PyPI is
time-boxed and never fails a scan.

Like the SAST/provenance/doc-generator plugins this is informational and
non-destructive: results land in ``extra["dependencies"]`` + ``dep:`` tags and
are surfaced through the generic plugin UI. Unlike those, it runs **on demand
only** — there is no import event hook.
"""

import asyncio
import logging
import platform
import re
from typing import Any, Dict, List, Optional

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType

from .resolver import build_resolver
from .resolver.base import OBJECT_TYPES
from .resolver.pypi import pypi_enabled_from_env

logger = logging.getLogger(__name__)

_PLUGIN_VERSION = "0.1.0"
_EXTRA_KEY = "dependencies"
_TAG_PREFIX = "dep:"


def _summary_message(block: Dict[str, Any]) -> str:
    """One-line verdict for the success banner in the generic plugin UI."""
    s = block.get("summary") or {}
    langs = ", ".join(block.get("languages_inspected") or []) or "none"
    msg = (
        f"{s.get('total_count', 0)} dependencies "
        f"({s.get('direct_count', 0)} direct) in [{langs}]"
    )
    if s.get("missing_count"):
        msg += f", {s['missing_count']} missing external"
    if s.get("local_module_count"):
        msg += f", {s['local_module_count']} local module(s)"
    if s.get("skipped_count"):
        msg += f", {s['skipped_count']} file(s) skipped (unsupported language)"
    if s.get("update_available_count"):
        msg += f", {s['update_available_count']} update(s) available"
    return msg


class SkillberryPluginDependencyTracker(PluginBase):
    """Discovers external Python dependencies (version + hash, transitive)."""

    def __init__(self):
        super().__init__()
        self._metadata = PluginMetadata(
            name="Dependency Tracker",
            version=_PLUGIN_VERSION,
            description=(
                "Discovers external Python package dependencies — exact version "
                "and artifact hashes, transitively at maximum depth — for skills, "
                "tools and snippets, and records them under extra['dependencies']."
            ),
            plugin_type=PluginType.EVALUATOR,
        )
        # Default PyPI enrichment from env; overridable per request.
        self._pypi_enabled = pypi_enabled_from_env()
        # NOTE: intentionally NO _register_event_handlers — on-demand only.

    # ── status / enablement ──────────────────────────────────────────────────

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def is_enabled(self) -> bool:
        # Local resolution needs no credentials or network; always available.
        return True

    def get_status_message(self) -> str:
        mode = "on" if self._pypi_enabled else "off"
        return f"Ready (local resolution; PyPI enrichment best-effort, default {mode})"

    # ── object access + code collection ───────────────────────────────────────

    def _get_object(self, object_type: str, uuid: str) -> Optional[Dict[str, Any]]:
        if self._store_api is None:
            raise RuntimeError("Store API not available")
        getter = {
            "skill": self.store.get_skill,
            "tool": self.store.get_tool,
            "snippet": self.store.get_snippet,
        }.get(object_type)
        if getter is None:
            raise ValueError(f"Unsupported object_type: {object_type!r}")
        return getter(uuid)

    def _collect_code(self, object_type: str, obj: Dict[str, Any]) -> List[tuple]:
        """Gather ``(filename, source)`` blobs to scan.

        The filename drives language detection (Python vs. shell) and the
        skipped-file report, so each blob carries the best name we have: a tool's
        ``module_name``, or a synthesized ``<snippet:name>`` for inline content.
        A tool contributes its module file; a snippet its inline content; a skill
        aggregates the modules and content of its referenced tools/snippets.
        """
        blobs: List[tuple] = []
        if object_type == "snippet":
            content = obj.get("content")
            if content:
                blobs.append((self._snippet_filename(obj), content))
            return blobs
        if object_type == "tool":
            blob = self._read_tool_module(obj)
            if blob is not None:
                blobs.append(blob)
            return blobs
        if object_type == "skill" and self._store_api is not None:
            for tool_uuid in obj.get("tool_uuids") or []:
                try:
                    tool = self.store.get_tool(tool_uuid)
                    if tool:
                        blob = self._read_tool_module(tool)
                        if blob is not None:
                            blobs.append(blob)
                except Exception as e:
                    logger.debug("dep-tracker: could not read child tool: %s", e)
            for snippet_uuid in obj.get("snippet_uuids") or []:
                try:
                    snippet = self.store.get_snippet(snippet_uuid)
                    content = (snippet or {}).get("content")
                    if content:
                        blobs.append((self._snippet_filename(snippet), content))
                except Exception as e:
                    logger.debug("dep-tracker: could not read child snippet: %s", e)
        return blobs

    def _read_tool_module(self, tool: Dict[str, Any]) -> Optional[tuple]:
        """Return ``(module_name, source)`` for a tool, or None if unreadable."""
        module = tool.get("module_name")
        if not module or self._store_api is None:
            return None
        try:
            source = self.store.tools.read_file(
                tool.get("uuid"), module, raw_content=True
            )
        except Exception as e:
            logger.debug("dep-tracker: could not read tool module: %s", e)
            return None
        return (module, source)

    @staticmethod
    def _snippet_filename(snippet: Dict[str, Any]) -> str:
        """A synthetic filename for a snippet so language detection can run.

        Snippets have no extension; we use the snippet name as a hint (e.g. a
        ``setup.sh`` snippet) and otherwise fall back to a neutral name that
        detection will resolve via shebang/heuristic.
        """
        name = snippet.get("name") or snippet.get("uuid") or "snippet"
        return str(name)

    def _local_module_names(
        self, object_type: str, obj: Dict[str, Any], blobs: List[tuple]
    ) -> set:
        """Top-level module names that are first-party to this object.

        An import resolving to one of these is the object's own bundled code, not
        a missing external dependency. Two complementary signals:

        1. The stem and name of each bundled tool module (e.g. ``merge_runs.py``
           -> ``merge_runs``), which catches direct sibling imports.
        2. Package roots inferred from the code itself: in ``from helpers.X
           import`` / ``import office.Y``, the leaf (``X``/``Y``) is a bundled
           module, so the root (``helpers``/``office``) is a local package.
        """
        names: set = set()

        # (1) bundled tool module stems + tool names
        tool_uuids: List[str] = []
        if object_type == "tool":
            tool_uuids = [obj.get("uuid")] if obj.get("uuid") else []
        elif object_type == "skill":
            tool_uuids = list(obj.get("tool_uuids") or [])
        bundled_stems: set = set()
        for tu in tool_uuids:
            try:
                tool = obj if (object_type == "tool") else self.store.get_tool(tu)
            except Exception:
                tool = None
            if not tool:
                continue
            module = tool.get("module_name") or ""
            stem = module.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            if stem:
                bundled_stems.add(stem)
                names.add(stem)
            if tool.get("name"):
                names.add(str(tool["name"]))
        # snippet names are first-party too
        if object_type == "skill":
            for su in obj.get("snippet_uuids") or []:
                try:
                    sn = self.store.get_snippet(su)
                except Exception:
                    sn = None
                if sn and sn.get("name"):
                    names.add(str(sn["name"]))

        # (2) Infer first-party package roots from the code's own imports, using
        # two signals — either is strong evidence the root is bundled:
        #   (a) `from <root>.<leaf> import ...` where <leaf> is a bundled module
        #       stem (e.g. `from helpers.merge_runs import ...`), or
        #   (b) `from <root>[...] import SYM, ...` where an imported symbol SYM
        #       matches a bundled module name/stem (e.g.
        #       `from office.soffice import get_soffice_env`, and a tool
        #       `get_soffice_env` is bundled).
        dotted_re = re.compile(
            r"(?m)^\s*(?:from|import)\s+([A-Za-z_]\w*)\.([A-Za-z_]\w*)"
        )
        from_import_re = re.compile(
            r"(?m)^\s*from\s+([A-Za-z_][\w.]*)\s+import\s+(.+)$"
        )
        for _filename, code in blobs:
            text = code or ""
            for m in dotted_re.finditer(text):
                root, leaf = m.group(1), m.group(2)
                if leaf in bundled_stems:
                    names.add(root)
            for m in from_import_re.finditer(text):
                root = m.group(1).split(".")[0]
                imported = m.group(2)
                symbols = re.findall(r"[A-Za-z_]\w*", imported.replace(" as ", " "))
                if any(s in bundled_stems for s in symbols):
                    names.add(root)

        return names

    # ── core scan ──────────────────────────────────────────────────────────────

    async def scan(
        self,
        object_type: str,
        uuid: str,
        *,
        pypi: Optional[bool] = None,
        generated_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve external dependencies for one object and persist them.

        Returns ``{object_type, uuid, dependencies, summary}``. Raises ValueError
        when the object is not found (the router maps that to 404).
        """
        obj = self._get_object(object_type, uuid)
        if not obj:
            raise ValueError(f"{object_type} {uuid} not found in store")

        blobs = self._collect_code(object_type, obj)
        local_modules = self._local_module_names(object_type, obj, blobs)

        if generated_at is None:
            # Computed here (not in the engine) so the engine stays deterministic.
            from datetime import datetime, timezone

            generated_at = datetime.now(timezone.utc).isoformat()

        pypi_enabled = self._pypi_enabled if pypi is None else bool(pypi)
        resolver = build_resolver(pypi_enabled=pypi_enabled)

        # Resolution is synchronous (and PyPI uses blocking requests); run it off
        # the event loop, mirroring the provenance plugin's gather.
        report = await asyncio.to_thread(resolver.scan, blobs, local_modules)

        block = report.to_extra_block(
            generated_at=generated_at,
            plugin_version=_PLUGIN_VERSION,
            python_version=platform.python_version(),
        )
        self._persist(object_type, uuid, block, report.summary_tags())
        return {
            "object_type": object_type,
            "uuid": uuid,
            "dependencies": block,
            "summary": block["summary"],
        }

    # ── persistence ──────────────────────────────────────────────────────────

    def _persist(
        self,
        object_type: str,
        uuid: str,
        block: Dict[str, Any],
        tags: List[str],
    ) -> None:
        """Write the dependency block to ``extra["dependencies"]`` + tags.

        Non-destructive: other ``extra`` keys and non-``dep:`` tags are preserved.
        """
        obj = self._get_object(object_type, uuid)
        if not obj:
            return
        if not isinstance(obj.get("extra"), dict):
            obj["extra"] = {}
        obj["extra"][_EXTRA_KEY] = block

        obj["tags"] = self._strip_dep_tags(obj.get("tags") or []) + tags
        self._write_object(object_type, uuid, obj)

    def _write_object(self, object_type: str, uuid: str, obj: Dict[str, Any]) -> None:
        writer = {
            "skill": self.store.update_skill,
            "tool": self.store.update_tool,
            "snippet": self.store.update_snippet,
        }.get(object_type)
        if writer is None:
            raise ValueError(f"Unsupported object_type: {object_type!r}")
        writer(uuid, obj)

    @staticmethod
    def _strip_dep_tags(tags: List[str]) -> List[str]:
        return [t for t in tags if not t.startswith(_TAG_PREFIX)]

    # ── plugin interface ──────────────────────────────────────────────────────

    def get_router(self):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter()

        # Tolerant model: the store's generic action form only submits an enum
        # field once changed, so a freshly-opened form may omit object_type. We
        # default it and validate explicitly -> a friendly 400 (not a 422).
        class ScanRequest(BaseModel):
            object_type: str = "tool"
            uuid: Optional[str] = None
            pypi: Optional[bool] = None  # per-call override of the env default

        def _validate(object_type: str, uuid: Optional[str]) -> None:
            if object_type not in OBJECT_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"object_type must be one of {list(OBJECT_TYPES)}; "
                        f"got {object_type!r}"
                    ),
                )
            if not (uuid and uuid.strip()):
                raise HTTPException(status_code=400, detail="uuid is required")

        @router.post("/scan")
        async def scan_endpoint(request: ScanRequest):
            """Resolve & record external Python dependencies for an object."""
            _validate(request.object_type, request.uuid)
            try:
                data = await self.scan(
                    request.object_type, request.uuid, pypi=request.pypi
                )
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except HTTPException:
                raise
            except Exception as e:
                logger.error("dependency scan failed: %s", e, exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
            return {
                "success": True,
                "message": _summary_message(data["dependencies"]),
                "data": data,
            }

        return router

    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        return None

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        return {
            "icon": "CubesIcon",
            "color": "#C9190B",
            "actions": [
                {
                    "label": "Scan dependencies",
                    "endpoint": "/api/plugins/dependency_tracker/scan",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "object_type": {
                                "type": "string",
                                "enum": list(OBJECT_TYPES),
                                "default": "tool",
                                "description": "Which object type to scan",
                            },
                            "uuid": {
                                "type": "string",
                                "description": "UUID of the object to scan",
                            },
                        },
                        "required": ["object_type", "uuid"],
                    },
                }
            ],
        }
