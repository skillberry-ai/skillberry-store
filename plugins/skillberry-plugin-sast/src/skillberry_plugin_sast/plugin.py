"""
Skillberry Plugin SAST - static analysis of skill/tool/snippet code.

Runs one or more open-source SAST engines (Bandit shipped now; the engine
registry is multi-engine by design) over content code and records concrete,
reproducible findings. Complementary to skillberry-plugin-security, which is an
LLM-based posture *score*; this plugin produces deterministic, line-level
findings and runs offline.

Flag-only: findings are written back as tags + extra["evaluation"]["sast"]. The
plugin never blocks or rejects content (the store has no such mechanism).
"""

import logging
import os
from typing import Any, Dict, List, Optional

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType

from .engines import available_engine_names, get_engines
from .engines.base import SEVERITIES

logger = logging.getLogger(__name__)

_CONTENT_TYPES = ("tool", "skill", "snippet")
_DEFAULT_ENGINES = "bandit"


def _parse_engine_env(value: Optional[str]) -> List[str]:
    """Parse SBS_SAST_ENGINES (comma-separated) into a clean name list."""
    if not value:
        return []
    return [name.strip() for name in value.split(",") if name.strip()]


class SkillberryPluginSast(PluginBase):
    """Plugin that statically scans tool/skill/snippet code for security issues."""

    def __init__(self):
        super().__init__()

        self._metadata = PluginMetadata(
            name="SAST Scanner",
            version="0.1.0",
            description=(
                "Static analysis of skill/tool/snippet code for vulnerabilities "
                "and malicious intent using open-source SAST engines (Bandit)."
            ),
            plugin_type=PluginType.EVALUATOR,
        )

        # Default engine set used by auto-scan and as the fallback when a scan
        # request omits `engines`.
        self._default_engines = _parse_engine_env(
            os.getenv("SBS_SAST_ENGINES")
        ) or _parse_engine_env(_DEFAULT_ENGINES)

        self._status_message = self._compute_status_message()
        logger.info("SAST plugin status: %s", self._status_message)

        self._register_event_handlers()

    # ── status / enablement ──────────────────────────────────────────────────

    def _installed_default_engines(self) -> List[str]:
        """Default engines that are both known and actually installed."""
        engines, _ = get_engines(self._default_engines)
        return [e.name for e in engines if e.is_available()]

    def _compute_status_message(self) -> str:
        engines, unknown = get_engines(self._default_engines)
        installed = [e.name for e in engines if e.is_available()]
        not_installed = [e.name for e in engines if not e.is_available()]
        if not engines:
            return (
                "No known SAST engines configured "
                f"(SBS_SAST_ENGINES={self._default_engines}, "
                f"available: {available_engine_names()})"
            )
        if not installed:
            return (
                "Disabled: no configured engine is installed "
                f"(configured: {[e.name for e in engines]}; "
                "install e.g. `pip install bandit`)"
            )
        msg = f"Ready (engines: {', '.join(installed)})"
        if not_installed:
            msg += f"; not installed: {', '.join(not_installed)}"
        if unknown:
            msg += f"; unknown: {', '.join(unknown)}"
        return msg

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def get_status_message(self) -> str:
        return self._status_message

    def is_enabled(self) -> bool:
        """Enabled when at least one configured engine is installed."""
        return bool(self._installed_default_engines())

    # ── event handlers (auto-scan on ingest) ─────────────────────────────────

    def _register_event_handlers(self) -> None:
        """Auto-scan tools/skills/snippets when they are added to the store.

        Mirrors skillberry-plugin-security: for a skill, also scan its
        referenced tools/snippets, since import flows write those directly
        without emitting per-object events.
        """
        from skillberry_store.plugins.events import _event_handlers

        for content_type in _CONTENT_TYPES:

            async def _handle_added(uuid: str, ct=content_type):
                if not self.is_enabled() or self._store_api is None:
                    return
                try:
                    await self.scan_object(uuid, ct)
                except Exception as e:
                    logger.error(
                        "Auto-SAST-scan failed for %s %s: %s",
                        ct,
                        uuid,
                        e,
                        exc_info=True,
                    )
                if ct == "skill":
                    try:
                        skill_obj = self.store.get_skill(uuid)
                    except Exception:
                        skill_obj = None
                    if skill_obj:
                        for tool_uuid in skill_obj.get("tool_uuids") or []:
                            try:
                                await self.scan_object(tool_uuid, "tool")
                            except Exception as e:
                                logger.error(
                                    "Auto-SAST-scan failed for tool %s: %s",
                                    tool_uuid,
                                    e,
                                    exc_info=True,
                                )
                        for snippet_uuid in skill_obj.get("snippet_uuids") or []:
                            try:
                                await self.scan_object(snippet_uuid, "snippet")
                            except Exception as e:
                                logger.error(
                                    "Auto-SAST-scan failed for snippet %s: %s",
                                    snippet_uuid,
                                    e,
                                    exc_info=True,
                                )

            event_name = f"content_added:{content_type}"
            if event_name not in _event_handlers:
                _event_handlers[event_name] = []
            _event_handlers[event_name].append(_handle_added)

    # ── tag helpers ──────────────────────────────────────────────────────────

    def _strip_sast_tags(self, tags: List[str]) -> List[str]:
        """Drop prior sast:* tags so a re-scan replaces rather than accumulates."""
        return [t for t in tags if not t.startswith("sast:")]

    def _summary_tags(self, summary: Dict[str, int]) -> List[str]:
        """Build `sast:<severity>:<count>` tags, or `sast:clean` when empty."""
        tags = [f"sast:{sev}:{summary[sev]}" for sev in SEVERITIES if summary.get(sev)]
        return tags or ["sast:clean"]

    # ── code extraction ──────────────────────────────────────────────────────

    def _extract_code(
        self, obj: Dict[str, Any], content_type: str
    ) -> List[Dict[str, Any]]:
        """Return a list of {code, filename, language} blobs to scan for an object.

        Tools have a module file; snippets carry inline content; skills have no
        own code (handled via fan-out in the event handler / scan_object).
        """
        blobs: List[Dict[str, Any]] = []
        if content_type == "tool":
            module_name = obj.get("module_name")
            language = (obj.get("programming_language") or "").lower()
            if module_name and self._store_api is not None:
                try:
                    code = self.store.tools.read_file(
                        obj["uuid"], module_name, raw_content=True
                    )
                    blobs.append(
                        {"code": code, "filename": module_name, "language": language}
                    )
                except Exception as e:
                    logger.info(
                        "Could not read code for tool %s: %s", obj.get("uuid"), e
                    )
        elif content_type == "snippet":
            content = obj.get("content")
            if content:
                blobs.append(
                    {
                        "code": content,
                        "filename": obj.get("name") or "snippet",
                        "language": (obj.get("content_type") or "").lower(),
                    }
                )
        return blobs

    # ── core scan ────────────────────────────────────────────────────────────

    async def scan_object(
        self,
        uuid: str,
        content_type: str,
        engines: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Scan a store object's code and persist normalized findings.

        Args:
            uuid: UUID of the object.
            content_type: "tool", "skill", or "snippet".
            engines: engine names to run; defaults to the configured default set
                (SBS_SAST_ENGINES). Requested-but-missing engines are reported
                per-engine, not raised.

        Returns:
            {uuid, content_type, engines: {name: {findings|status}}, summary, findings}
        """
        if self._store_api is None:
            raise RuntimeError("Store API not available")
        if content_type not in _CONTENT_TYPES:
            raise ValueError(f"Unknown content_type: {content_type}")

        requested = engines or self._default_engines
        resolved, unknown = get_engines(requested)

        if content_type == "tool":
            obj = self.store.get_tool(uuid)
        elif content_type == "skill":
            obj = self.store.get_skill(uuid)
        else:
            obj = self.store.get_snippet(uuid)
        if not obj:
            raise ValueError(f"{content_type.capitalize()} {uuid} not found in store")

        logger.info(
            "SAST scanning %s %s: %s", content_type, uuid, obj.get("name", "unnamed")
        )

        blobs = self._extract_code(obj, content_type)

        # Per-engine results: either a findings list or a status note.
        engine_results: Dict[str, Any] = {}
        all_findings: List[Dict[str, Any]] = []

        for name in unknown:
            engine_results[name] = {"status": "unknown_engine"}

        for engine in resolved:
            if not engine.is_available():
                engine_results[engine.name] = {"status": "not_installed"}
                continue
            applicable = [b for b in blobs if engine.supports(b["language"])]
            if not blobs:
                engine_results[engine.name] = {"status": "no_code", "findings": []}
                continue
            if not applicable:
                engine_results[engine.name] = {
                    "status": "language_unsupported",
                    "findings": [],
                }
                continue
            findings: List[Dict[str, Any]] = []
            try:
                for blob in applicable:
                    for f in engine.scan(
                        blob["code"],
                        filename=blob["filename"],
                        language=blob["language"],
                    ):
                        d = f.to_dict()
                        d["file"] = blob["filename"]
                        findings.append(d)
            except Exception as e:
                logger.error(
                    "Engine %s failed on %s %s: %s", engine.name, content_type, uuid, e
                )
                engine_results[engine.name] = {"status": "error", "error": str(e)}
                continue
            engine_results[engine.name] = {"status": "ok", "findings": findings}
            all_findings.extend(findings)

        summary = {sev: 0 for sev in SEVERITIES}
        for f in all_findings:
            sev = f.get("severity")
            if sev in summary:
                summary[sev] += 1

        result = {
            "uuid": uuid,
            "content_type": content_type,
            "engines": engine_results,
            "summary": summary,
            "findings": all_findings,
        }

        # Skills have no own code; only persist for tool/snippet (skills are
        # covered via fan-out to their children).
        if content_type in ("tool", "snippet") and blobs:
            self._write_findings_to_store(uuid, content_type, obj, result)

        return result

    def _write_findings_to_store(
        self,
        uuid: str,
        content_type: str,
        obj: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        """Persist findings into tags + extra["evaluation"]["sast"].

        Merges alongside any existing extra["evaluation"]["security"] without
        wiping it (parity with skillberry-plugin-security).
        """
        summary = result["summary"]
        existing_tags = self._strip_sast_tags(obj.get("tags") or [])
        obj["tags"] = existing_tags + self._summary_tags(summary)

        if not isinstance(obj.get("extra"), dict):
            obj["extra"] = {}
        if not isinstance(obj["extra"].get("evaluation"), dict):
            obj["extra"]["evaluation"] = {}
        obj["extra"]["evaluation"]["sast"] = {
            "engines_run": [
                name for name, r in result["engines"].items() if r.get("status") == "ok"
            ],
            "summary": summary,
            "findings": result["findings"],
        }

        if content_type == "tool":
            self.store.tools.write_dict(uuid, obj)
        elif content_type == "snippet":
            self.store.snippets.write_dict(uuid, obj)

    # ── plugin interface ──────────────────────────────────────────────────────

    def get_router(self):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter()

        class ScanRequest(BaseModel):
            uuid: str
            content_type: str  # "tool", "skill", or "snippet"
            engines: Optional[List[str]] = None

        @router.post("/scan")
        async def scan_endpoint(request: ScanRequest):
            """Scan a store object and persist SAST findings."""
            if not self.is_enabled():
                raise HTTPException(status_code=503, detail=self._status_message)
            if request.content_type not in _CONTENT_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail="content_type must be 'tool', 'skill', or 'snippet'",
                )
            try:
                result = await self.scan_object(
                    uuid=request.uuid,
                    content_type=request.content_type,
                    engines=request.engines,
                )
                return {"success": True, **result}
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(
                    "SAST scan failed for %s %s: %s",
                    request.content_type,
                    request.uuid,
                    e,
                    exc_info=True,
                )
                raise HTTPException(status_code=500, detail=str(e))

        return router

    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        return None

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        return {
            "icon": "BugIcon",
            "color": "#8E44AD",
            "actions": [
                {
                    "label": "Scan code (SAST)",
                    "endpoint": "/api/plugins/sast/scan",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "uuid": {
                                "type": "string",
                                "description": "UUID of the object to scan",
                            },
                            "content_type": {
                                "type": "string",
                                "enum": list(_CONTENT_TYPES),
                                "description": "Type of object to scan",
                            },
                            "engines": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": available_engine_names(),
                                },
                                "description": (
                                    "SAST engines to run (default: SBS_SAST_ENGINES). "
                                    "Multiple may be selected."
                                ),
                            },
                        },
                        "required": ["uuid", "content_type"],
                    },
                }
            ],
        }
