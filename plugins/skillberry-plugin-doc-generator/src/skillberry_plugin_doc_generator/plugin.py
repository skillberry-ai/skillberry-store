"""
Skillberry Plugin: Documentation Generator & Enricher.

The store has plugins to *assess* objects (security, SAST, provenance, dedupe,
evaluation) and to *improve code* (optimizer) — but nothing maintains their
**documentation**. Imported objects arrive with thin or missing docs, and docs
drift out of sync when code changes. This plugin closes that gap for all three
object types (skills, tools, snippets). See issue #201.

Three operations, one code path:
  - generate  : produce docs for an object that lacks them
  - enrich    : expand thin docs without discarding good author content
  - refresh   : detect drift (source changed since docs were written) and,
                optionally, regenerate

LLM integration mirrors the security evaluator plugin exactly: documentation is
produced by a frontier model through ``llm-switchboard``
(``get_llm(LLM_PROVIDER)`` → ``Client(model_name=LLM_MODEL)`` →
``await client.generate_async(prompt=...)``). No specific model is hardcoded;
the provider/model are read from ``LLM_PROVIDER`` / ``LLM_MODEL``. If the LLM is
unavailable the plugin is not ready.

Persistence is non-destructive and review-before-apply: results are written to a
structured ``extra["documentation"]`` block and to tags; the raw object
``description`` is never overwritten. ``proposed`` is the default; applying is
explicit.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from skillberry_plugin_sdk import PluginLifecycleBase, on_event

from .models import (
    MODE_ENRICHED,
    MODE_GENERATED,
    MODE_KEPT,
    OBJECT_TYPES,
    Documentation,
    ObjectDoc,
    ParamDoc,
)

logger = logging.getLogger(__name__)

# Where structured docs live on an object.
_EXTRA_KEY = "documentation"
_TAG_PREFIX = "doc:"

# A description shorter than this is treated as "thin" and eligible for enrich.
_THIN_DESCRIPTION_CHARS = 40

_SYSTEM_INSTRUCTION = (
    "You are documenting a {object_type} from a curated store of reusable "
    "AI-agent building blocks. Produce clear, accurate, reusable documentation "
    "grounded ONLY in the information given — do not invent behavior, "
    "parameters, or examples that are not supported by the input."
)


def _summary_message(doc: Dict[str, Any], drift: Optional[List[str]] = None) -> str:
    """One-line verdict for the success banner in the generic plugin UI."""
    mode = (doc.get("mode") or "generated").upper()
    n_params = len(doc.get("parameters") or [])
    n_examples = len(doc.get("examples") or [])
    if drift:
        return f"{len(drift)} drift signal(s); docs {mode.lower()}"
    return f"Docs {mode} — {n_params} param(s), {n_examples} example(s)"


class SkillberryPluginDocGenerator(PluginLifecycleBase):
    """Generates, enriches and drift-checks documentation for store objects."""

    manifest_path = "manifest.yaml"

    def __init__(self, manifest=None) -> None:
        super().__init__(manifest=manifest)
        self.llm_client = None
        self._backend = ""
        self._status_message = "Initializing..."

    # ── lifecycle ────────────────────────────────────────────────────────────

    async def on_start(self) -> None:
        """Initialize the LLM client (expensive; wired exactly like the security plugin)."""
        try:
            from llm_switchboard import get_llm

            provider_name = os.getenv("LLM_PROVIDER", "openai.async")
            model_name = os.getenv("LLM_MODEL", "gpt-4")

            logger.info(
                f"Initializing LLM: provider={provider_name}, model={model_name}"
            )

            LLMClientClass = get_llm(provider_name)
            self.llm_client = LLMClientClass(model_name=model_name)
            self._backend = f"{provider_name}:{model_name}"
            self._status_message = f"Ready (using {provider_name}; review-before-apply)"

            logger.info("LLM client initialized successfully")

        except ImportError:
            self._status_message = "Missing dependency: llm-switchboard not installed"
            logger.warning("llm-switchboard not installed, plugin will be disabled")
        except Exception as e:
            self._status_message = f"Configuration error: {str(e)}"
            logger.error(f"Failed to initialize LLM client: {e}", exc_info=True)

    async def is_ready(self) -> Dict[str, Any]:
        """Ready when the LLM client initialized successfully."""
        ready = self.llm_client is not None
        missing = self.validate_env()
        return {
            "ready": ready and not missing,
            "missing_config": missing,
            "status_message": self._status_message,
        }

    def is_enabled(self) -> bool:
        """Legacy accessor used by the router / auto-hook."""
        return self.llm_client is not None

    # ── event handler (auto-propose docs on import) ──────────────────────────

    @on_event("content.tool.added")
    async def _on_tool_added(self, event) -> None:
        await self._auto_propose("tool", event)

    @on_event("content.skill.added")
    async def _on_skill_added(self, event) -> None:
        await self._auto_propose("skill", event)

    @on_event("content.snippet.added")
    async def _on_snippet_added(self, event) -> None:
        await self._auto_propose("snippet", event)

    async def _auto_propose(self, object_type: str, event) -> None:
        """On object add, propose documentation if it is missing/thin.

        Best-effort and non-blocking, mirroring the provenance/SAST auto-hooks.
        It only *proposes* (never auto-applies), so author intent is never
        silently overwritten on import.
        """
        if not self.is_enabled() or self._store is None:
            return
        uuid = event.data.get("uuid") if isinstance(event.data, dict) else None
        if not uuid:
            return
        try:
            await self.generate_docs(
                object_type, uuid, apply=False, only_if_missing=True
            )
        except Exception as e:
            logger.error(
                "Auto-doc proposal failed for %s %s: %s",
                object_type,
                uuid,
                e,
                exc_info=True,
            )

    # ── store object -> normalized ObjectDoc ─────────────────────────────────

    async def _get_object(
        self, object_type: str, uuid: str
    ) -> Optional[Dict[str, Any]]:
        if object_type == "skill":
            return await self.store.get_skill(uuid)
        if object_type == "tool":
            return await self.store.get_tool(uuid)
        if object_type == "snippet":
            return await self.store.get_snippet(uuid)
        raise ValueError(f"Unsupported object_type: {object_type!r}")

    async def _to_object_doc(
        self, object_type: str, uuid: str, obj: Dict[str, Any]
    ) -> ObjectDoc:
        """Normalize a raw store object into the generation input shape."""
        name = obj.get("name") or uuid
        params = self._extract_parameters(obj)
        code_blobs = await self._collect_code(object_type, obj)
        references = await self._collect_references(object_type, obj)
        return ObjectDoc(
            object_type=object_type,
            uuid=uuid,
            name=name,
            description=obj.get("description") or "",
            tags=list(obj.get("tags") or []),
            parameters=params,
            code_blobs=code_blobs,
            references=references,
        )

    @staticmethod
    def _extract_parameters(obj: Dict[str, Any]) -> List[ParamDoc]:
        """Pull a parameter list out of a tool's schema, if present.

        Accepts either a JSON-schema-ish ``parameters`` object (properties +
        required) or a flat list of ``{name, type, description, required}``.
        """
        raw = obj.get("parameters") or (obj.get("input_schema") or {})
        out: List[ParamDoc] = []
        if isinstance(raw, dict) and isinstance(raw.get("properties"), dict):
            required = set(raw.get("required") or [])
            for pname, spec in raw["properties"].items():
                spec = spec if isinstance(spec, dict) else {}
                out.append(
                    ParamDoc(
                        name=pname,
                        type=spec.get("type"),
                        required=pname in required,
                        description=(spec.get("description") or "").strip(),
                    )
                )
        elif isinstance(raw, list):
            for spec in raw:
                if not isinstance(spec, dict) or not spec.get("name"):
                    continue
                out.append(
                    ParamDoc(
                        name=spec["name"],
                        type=spec.get("type"),
                        required=bool(spec.get("required")),
                        description=(spec.get("description") or "").strip(),
                    )
                )
        return out

    async def _collect_code(
        self, object_type: str, obj: Dict[str, Any]
    ) -> List[str]:
        """Best-effort code/content blobs to infer behavior from.

        Note: the previous in-process implementation reached into raw store
        files via ``self.store.tools.read_file(...)``. That surface is not
        exposed over the plugin SDK's HTTP StoreClient, so out-of-process
        plugins rely on any code/content that is already present on the object
        record itself (e.g. snippet ``content``, or a ``code`` field on the
        tool if provided by the store). Skills recurse into their child
        objects via async ``get_tool`` / ``get_snippet``.
        """
        blobs: List[str] = []
        if object_type == "snippet":
            content = obj.get("content")
            if content:
                blobs.append(content)
            return blobs
        if object_type == "tool":
            # Prefer any inline code/content available on the tool record.
            for key in ("code", "content", "source"):
                v = obj.get(key)
                if isinstance(v, str) and v:
                    blobs.append(v)
                    break
            return blobs
        # skill: gather child tool code + snippet content
        if object_type == "skill":
            for tool_uuid in obj.get("tool_uuids") or []:
                try:
                    tool = await self.store.get_tool(tool_uuid)
                except Exception as e:
                    logger.debug("doc-gen: could not read child tool: %s", e)
                    continue
                if not tool:
                    continue
                for key in ("code", "content", "source"):
                    v = tool.get(key)
                    if isinstance(v, str) and v:
                        blobs.append(v)
                        break
            for snippet_uuid in obj.get("snippet_uuids") or []:
                try:
                    snippet = await self.store.get_snippet(snippet_uuid)
                    content = (snippet or {}).get("content")
                    if content:
                        blobs.append(content)
                except Exception as e:
                    logger.debug("doc-gen: could not read child snippet: %s", e)
        return blobs

    async def _collect_references(
        self, object_type: str, obj: Dict[str, Any]
    ) -> List[str]:
        """For skills: short names of referenced tools/snippets."""
        if object_type != "skill":
            return []
        refs: List[str] = []
        for tool_uuid in obj.get("tool_uuids") or []:
            try:
                tool = await self.store.get_tool(tool_uuid)
                if tool:
                    refs.append(f"tool:{tool.get('name') or tool_uuid}")
            except Exception:
                continue
        for snippet_uuid in obj.get("snippet_uuids") or []:
            try:
                snippet = await self.store.get_snippet(snippet_uuid)
                if snippet:
                    refs.append(f"snippet:{snippet.get('name') or snippet_uuid}")
            except Exception:
                continue
        return refs

    # ── LLM generation ────────────────────────────────────────────────────────

    async def _generate_documentation(
        self, object_doc: ObjectDoc, existing: Optional[Documentation]
    ) -> Documentation:
        """Ask the LLM for documentation, parse it, and label its mode.

        Mirrors the security evaluator's call shape:
        ``await self.llm_client.generate_async(prompt=...)`` then a strict JSON
        parse (raises ``RuntimeError`` on a bad response — no silent fallback).
        The ``mode`` is decided here from the author content so the
        non-destructive guarantee holds: when the author already wrote a
        sufficient description, it is kept verbatim.
        """
        if not self.llm_client:
            raise RuntimeError("LLM client not initialized")

        prompt = self._build_prompt(object_doc, existing)
        logger.debug(
            "doc-gen: calling LLM for %s %s",
            object_doc.object_type,
            object_doc.uuid,
        )
        response = await self.llm_client.generate_async(prompt=prompt)
        logger.info(f"doc-gen: received LLM response ({len(response)} chars)")

        doc = self._parse_documentation(response)
        if doc.is_empty():
            raise RuntimeError("LLM returned empty documentation")

        author_desc = (object_doc.description or "").strip()
        doc.mode = self._classify_mode(author_desc)
        if doc.mode == MODE_KEPT:
            # Non-destructive: sufficient author content is preserved verbatim.
            doc.description = author_desc
        return doc

    @staticmethod
    def _classify_mode(author_desc: str) -> str:
        """Label docs relative to pre-existing author content (see MODE_*)."""
        text = (author_desc or "").strip()
        if not text:
            return MODE_GENERATED
        if len(text) < _THIN_DESCRIPTION_CHARS:
            return MODE_ENRICHED
        return MODE_KEPT

    @staticmethod
    def _build_prompt(obj: ObjectDoc, existing: Optional[Documentation]) -> str:
        """Construct the generation prompt from the normalized object view."""
        parts: List[str] = [_SYSTEM_INSTRUCTION.format(object_type=obj.object_type)]
        parts.append(f"\nName: {obj.name}")
        if obj.description:
            parts.append(
                f"Existing author description (preserve its intent): {obj.description}"
            )
        if obj.tags:
            parts.append(f"Tags: {', '.join(obj.tags)}")
        if obj.parameters:
            param_lines = [
                f"  - {p.name} (type={p.type}, required={p.required})"
                + (f": {p.description}" if p.description else "")
                for p in obj.parameters
            ]
            parts.append("Parameters:\n" + "\n".join(param_lines))
        if obj.references:
            parts.append(f"References: {', '.join(obj.references)}")
        if obj.code_blobs:
            # Bound the code we send; this is documentation, not analysis.
            joined = "\n\n".join(obj.code_blobs)
            parts.append("Code / content (truncated):\n" + joined[:6000])

        parts.append(
            "\nReturn ONLY a JSON object with exactly these fields:\n"
            '- "description": string — a clear summary of what this is and does\n'
            '- "when_to_use": string — when an agent/user should reach for it\n'
            '- "parameters": array of {"name","type","required","description"} '
            "(echo the inputs above, filling in clear descriptions; [] if none)\n"
            '- "examples": array of strings — at least one concise usage example\n'
            "Return ONLY the JSON object, no prose, no code fences."
        )
        return "\n".join(parts)

    @staticmethod
    def _parse_documentation(response: str) -> Documentation:
        """Parse the model's JSON response into a Documentation.

        Tolerant of surrounding prose (extracts the first ``{...}`` block, like
        the security plugin) but raises ``RuntimeError`` when no usable JSON is
        present so the endpoint reports a clean error.
        """
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start < 0 or end <= start:
                raise ValueError("No JSON object found in LLM response")
            data: Dict[str, Any] = json.loads(response[start:end])
        except Exception as e:
            logger.warning(f"doc-gen: failed to parse LLM response: {e}")
            raise RuntimeError(f"Failed to parse LLM response: {str(e)}")

        params: List[ParamDoc] = []
        for p in data.get("parameters") or []:
            if not isinstance(p, dict) or not p.get("name"):
                continue
            params.append(
                ParamDoc(
                    name=p["name"],
                    type=p.get("type"),
                    required=bool(p.get("required")),
                    description=(p.get("description") or "").strip(),
                )
            )
        examples = [str(e) for e in (data.get("examples") or []) if str(e).strip()]
        return Documentation(
            description=(data.get("description") or "").strip(),
            when_to_use=(data.get("when_to_use") or "").strip(),
            parameters=params,
            examples=examples,
        )

    # ── core operations ───────────────────────────────────────────────────────

    async def generate_docs(
        self,
        object_type: str,
        uuid: str,
        apply: bool = False,
        only_if_missing: bool = False,
    ) -> Dict[str, Any]:
        """Generate/enrich documentation for one object.

        Returns ``{object_type, uuid, documentation, applied, skipped}``. When
        ``apply`` is False (default) the documentation is only *proposed* and
        stored under ``extra["documentation"]["proposed"]`` for review. When
        ``only_if_missing`` is True and good docs already exist, it is a no-op.
        """
        if not self.llm_client:
            raise RuntimeError("LLM client not initialized")

        obj = await self._get_object(object_type, uuid)
        if not obj:
            raise ValueError(f"{object_type} {uuid} not found in store")

        existing_block = self._existing_block(obj)
        if only_if_missing and self._has_applied_docs(existing_block):
            return {
                "object_type": object_type,
                "uuid": uuid,
                "skipped": "documentation already present",
                "applied": False,
                "documentation": (existing_block or {}).get("current"),
            }

        object_doc = await self._to_object_doc(object_type, uuid, obj)
        prior = self._existing_documentation(existing_block)
        doc = await self._generate_documentation(object_doc, prior)
        doc_dict = doc.to_dict()
        doc_dict["source_fingerprint"] = object_doc.source_fingerprint()
        doc_dict["backend"] = self._backend

        await self._persist(object_type, uuid, doc_dict, apply=apply)
        return {
            "object_type": object_type,
            "uuid": uuid,
            "documentation": doc_dict,
            "applied": apply,
            "skipped": None,
        }

    async def refresh_docs(self, object_type: str, uuid: str) -> Dict[str, Any]:
        """Detect documentation drift and propose refreshed docs.

        Drift = the object's source fingerprint (code/params/references) has
        changed since the *applied* documentation was written. Returns
        ``{drift, documentation, applied}``. Always proposes (never auto-applies)
        so a human reviews regenerated docs.
        """
        if not self.llm_client:
            raise RuntimeError("LLM client not initialized")

        obj = await self._get_object(object_type, uuid)
        if not obj:
            raise ValueError(f"{object_type} {uuid} not found in store")

        existing_block = self._existing_block(obj)
        applied = (existing_block or {}).get("current") or {}
        old_fp = applied.get("source_fingerprint")

        object_doc = await self._to_object_doc(object_type, uuid, obj)
        new_fp = object_doc.source_fingerprint()
        drift = self._compute_drift(old_fp, new_fp, applied)

        result: Dict[str, Any] = {
            "object_type": object_type,
            "uuid": uuid,
            "drift": drift,
            "documentation": applied or None,
            "applied": False,
        }
        if drift:
            doc = await self._generate_documentation(
                object_doc, self._existing_documentation(existing_block)
            )
            doc_dict = doc.to_dict()
            doc_dict["source_fingerprint"] = new_fp
            doc_dict["backend"] = self._backend
            await self._persist(object_type, uuid, doc_dict, apply=False)
            result["documentation"] = doc_dict
        return result

    @staticmethod
    def _compute_drift(
        old_fp: Optional[str], new_fp: str, applied: Dict[str, Any]
    ) -> List[str]:
        """Human-readable drift descriptors (empty when docs are still valid)."""
        if not applied:
            return ["no applied documentation to compare against"]
        if old_fp is None:
            return ["documentation predates source-fingerprint tracking"]
        if old_fp != new_fp:
            return ["source changed since documentation was written"]
        return []

    # ── existing-doc helpers ─────────────────────────────────────────────────

    @staticmethod
    def _existing_block(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        block = (obj.get("extra") or {}).get(_EXTRA_KEY)
        return block if isinstance(block, dict) else None

    @staticmethod
    def _has_applied_docs(block: Optional[Dict[str, Any]]) -> bool:
        return bool(block and isinstance(block.get("current"), dict))

    @staticmethod
    def _existing_documentation(
        block: Optional[Dict[str, Any]],
    ) -> Optional[Documentation]:
        """Reconstruct a prior Documentation (applied, else proposed) if any."""
        if not block:
            return None
        src = block.get("current") or block.get("proposed")
        if not isinstance(src, dict):
            return None
        params = [
            ParamDoc(
                name=p.get("name", ""),
                type=p.get("type"),
                required=bool(p.get("required")),
                description=p.get("description", ""),
            )
            for p in (src.get("parameters") or [])
            if isinstance(p, dict)
        ]
        return Documentation(
            description=src.get("description", ""),
            when_to_use=src.get("when_to_use", ""),
            parameters=params,
            examples=list(src.get("examples") or []),
            mode=src.get("mode", "generated"),
            notes=list(src.get("notes") or []),
        )

    # ── persistence ──────────────────────────────────────────────────────────

    async def _persist(
        self,
        object_type: str,
        uuid: str,
        doc_dict: Dict[str, Any],
        apply: bool,
    ) -> None:
        """Write docs to ``extra["documentation"]`` + tags, non-destructively.

        ``apply=False`` stores under ``proposed`` (review-before-apply);
        ``apply=True`` promotes to ``current`` (what the UI/consumers read).
        Author-written object ``description`` is never overwritten here — the
        applied description lives in the documentation block, leaving the raw
        object field intact for explicit user action.
        """
        obj = await self._get_object(object_type, uuid)
        if not obj:
            return
        if not isinstance(obj.get("extra"), dict):
            obj["extra"] = {}
        block = obj["extra"].get(_EXTRA_KEY)
        if not isinstance(block, dict):
            block = {}
        if apply:
            block["current"] = doc_dict
            block.pop("proposed", None)
        else:
            block["proposed"] = doc_dict
        obj["extra"][_EXTRA_KEY] = block

        obj["tags"] = self._doc_tags(
            self._strip_doc_tags(obj.get("tags") or []), doc_dict, applied=apply
        )
        await self._write_object(object_type, uuid, obj)

    async def _write_object(
        self, object_type: str, uuid: str, obj: Dict[str, Any]
    ) -> None:
        if object_type == "skill":
            await self.store.update_skill(uuid, obj)
        elif object_type == "tool":
            await self.store.update_tool(uuid, obj)
        elif object_type == "snippet":
            await self.store.update_snippet(uuid, obj)
        else:
            raise ValueError(f"Unsupported object_type: {object_type!r}")

    @staticmethod
    def _strip_doc_tags(tags: List[str]) -> List[str]:
        return [t for t in tags if not t.startswith(_TAG_PREFIX)]

    @staticmethod
    def _doc_tags(
        tags: List[str], doc_dict: Dict[str, Any], applied: bool
    ) -> List[str]:
        out = list(tags)
        out.append(f"{_TAG_PREFIX}mode:{doc_dict.get('mode', 'generated')}")
        out.append(f"{_TAG_PREFIX}status:{'applied' if applied else 'proposed'}")
        return out

    # ── HTTP API ─────────────────────────────────────────────────────────────

    def get_router(self):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter()

        # Fields are tolerant by design: the store's generic action form only
        # submits an enum field once the user changes it, so a freshly-opened
        # form can omit ``object_type``. We default it and validate explicitly,
        # returning a friendly 400 instead of a raw pydantic 422.
        class GenerateRequest(BaseModel):
            object_type: str = "tool"
            uuid: Optional[str] = None
            apply: bool = False
            only_if_missing: bool = False

        class RefreshRequest(BaseModel):
            object_type: str = "tool"
            uuid: Optional[str] = None

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

        @router.post("/generate")
        async def generate_endpoint(request: GenerateRequest):
            """Generate/enrich docs for an object (proposed unless apply=True)."""
            if not self.is_enabled():
                raise HTTPException(status_code=503, detail=self._status_message)
            _validate(request.object_type, request.uuid)
            try:
                data = await self.generate_docs(
                    request.object_type,
                    request.uuid,
                    apply=request.apply,
                    only_if_missing=request.only_if_missing,
                )
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except HTTPException:
                raise
            except Exception as e:
                logger.error("doc generate failed: %s", e, exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
            msg = (
                data["skipped"]
                if data.get("skipped")
                else _summary_message(data.get("documentation") or {})
            )
            return {"success": True, "message": msg, "data": data}

        @router.post("/refresh")
        async def refresh_endpoint(request: RefreshRequest):
            """Detect drift and propose refreshed docs for an object."""
            if not self.is_enabled():
                raise HTTPException(status_code=503, detail=self._status_message)
            _validate(request.object_type, request.uuid)
            try:
                data = await self.refresh_docs(request.object_type, request.uuid)
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except HTTPException:
                raise
            except Exception as e:
                logger.error("doc refresh failed: %s", e, exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
            drift = data.get("drift") or []
            msg = (
                "No drift; docs current"
                if not drift
                else f"{len(drift)} drift signal(s)"
            )
            return {"success": True, "message": msg, "data": data}

        return router
