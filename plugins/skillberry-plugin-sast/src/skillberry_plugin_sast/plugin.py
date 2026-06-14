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
_DEFAULT_ENGINE = "bandit"

# Env vars (both comma-separated):
#   SBS_SAST_AVAILABLE_ENGINES - which engines are OFFERED (the dropdown set),
#       intersected with what's actually implemented. Unset => all implemented.
#   SBS_SAST_ACTIVE_ENGINES    - which engines are ACTIVE by default (pre-selected
#       and used by auto-scan). Must be a subset of available; defaults to bandit.
_ENV_AVAILABLE = "SBS_SAST_AVAILABLE_ENGINES"
_ENV_ACTIVE = "SBS_SAST_ACTIVE_ENGINES"


def _parse_engine_env(value: Optional[str]) -> List[str]:
    """Parse a comma-separated engine env var into a clean name list."""
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

        # AVAILABLE set: engines offered in the UI dropdown. Take the env list
        # (if set) intersected with what's actually implemented in the registry,
        # preserving env order; unknown names are dropped with a warning. Unset
        # => all implemented engines.
        implemented = available_engine_names()
        env_available = _parse_engine_env(os.getenv(_ENV_AVAILABLE))
        if env_available:
            self._available_engines = [n for n in env_available if n in implemented]
            ignored = [n for n in env_available if n not in implemented]
            if ignored:
                logger.warning(
                    "%s lists engines that are not implemented and were ignored: %s",
                    _ENV_AVAILABLE,
                    ", ".join(ignored),
                )
        else:
            self._available_engines = list(implemented)

        # ACTIVE/default set: pre-selected in the UI and used by auto-scan.
        # SBS_SAST_ACTIVE_ENGINES overrides the built-in bandit default when set;
        # it is then constrained to the available set.
        active = _parse_engine_env(os.getenv(_ENV_ACTIVE)) or [_DEFAULT_ENGINE]
        self._default_engines = [n for n in active if n in self._available_engines]
        if not self._default_engines:
            # Active set fell outside available (or available is empty); fall back
            # to whatever is available so the plugin isn't silently inert.
            self._default_engines = list(self._available_engines)

        self._status_message = self._compute_status_message()
        logger.info("SAST plugin status: %s", self._status_message)

        # Optional LLM client for the "Fix" capability. Scanning works without
        # it; only Fix is gated on a usable model/key. Mirrors the init pattern
        # of skillberry-plugin-security.
        self._llm = None
        self._llm_model = os.getenv("LLM_MODEL", "gpt-4")
        self._llm_status = (
            "Set OPENAI_API_KEY (and LLM_PROVIDER/LLM_MODEL) to enable Fix"
        )
        try:
            from llm_switchboard import get_llm

            provider = os.getenv("LLM_PROVIDER", "openai.async")
            self._llm = get_llm(provider)(model_name=self._llm_model)
            self._llm_status = f"Ready (fix via {provider} / {self._llm_model})"
            logger.info("SAST Fix LLM initialized: %s / %s", provider, self._llm_model)
        except ImportError:
            self._llm_status = "Fix unavailable: llm-switchboard not installed"
            logger.info("SAST Fix disabled: llm-switchboard not installed")
        except Exception as e:  # noqa: BLE001 - missing key/config disables Fix only
            self._llm_status = f"Fix unavailable: {e}"
            logger.info("SAST Fix disabled: %s", e)

        self._register_event_handlers()

    # ── status / enablement ──────────────────────────────────────────────────

    def _fix_available(self) -> bool:
        """True if the LLM client is initialized (key/config present)."""
        return self._llm is not None

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
                f"(active={self._default_engines}, "
                f"available: {self._available_engines})"
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

    def _infer_type(self, uuid: str) -> Optional[str]:
        """Infer an object's content type from its UUID by probing the store.

        The store's ``get_*`` accessors return ``None`` for a wrong-type UUID
        (they don't raise), so probing in order is safe. Returns the content
        type ("tool"/"skill"/"snippet") or ``None`` if the UUID matches nothing.
        """
        if self._store_api is None:
            return None
        if self.store.get_tool(uuid):
            return "tool"
        if self.store.get_skill(uuid):
            return "skill"
        if self.store.get_snippet(uuid):
            return "snippet"
        return None

    async def scan_object(
        self,
        uuid: str,
        content_type: Optional[str] = None,
        engines: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Scan a store object's code and persist normalized findings.

        Args:
            uuid: UUID of the object.
            content_type: "tool", "skill", or "snippet". When omitted, the type
                is inferred from the UUID.
            engines: engine names to run; defaults to the active set
                (SBS_SAST_ACTIVE_ENGINES). Requested-but-missing engines are
                reported per-engine, not raised.

        Returns:
            {uuid, content_type, engines: {name: {findings|status}}, summary, findings}
        """
        if self._store_api is None:
            raise RuntimeError("Store API not available")

        if content_type is None:
            content_type = self._infer_type(uuid)
            if content_type is None:
                raise ValueError(f"Object {uuid} not found in store")
        elif content_type not in _CONTENT_TYPES:
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
            "name": obj.get("name"),
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

    # ── batch scan (type inferred per object) ─────────────────────────────────

    async def scan_objects(
        self,
        uuids: List[str],
        engines: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Scan one or more objects, inferring each object's type from its UUID.

        Selecting a skill fans out to the skill's referenced tools and snippets
        (a skill has no code of its own), matching the auto-scan-on-ingest
        behavior. UUIDs that resolve to nothing are reported in ``not_found``
        rather than raising, so a mixed batch still scans its valid members.

        Returns:
            {results: [<scan_object result>, ...], not_found: [uuid, ...],
             summary: {<combined severity counts>}}
        """
        if self._store_api is None:
            raise RuntimeError("Store API not available")

        results: List[Dict[str, Any]] = []
        not_found: List[str] = []
        scanned: set = set()

        async def _scan(uuid: str, content_type: Optional[str]) -> None:
            if uuid in scanned:
                return
            scanned.add(uuid)
            try:
                results.append(await self.scan_object(uuid, content_type, engines))
            except ValueError:
                not_found.append(uuid)

        for uuid in uuids:
            ctype = self._infer_type(uuid)
            if ctype is None:
                not_found.append(uuid)
                continue
            if ctype == "skill":
                # Skills carry no code; fan out to referenced tools/snippets.
                await _scan(uuid, "skill")  # records a skill-level (empty) result
                skill_obj = self.store.get_skill(uuid) or {}
                for tool_uuid in skill_obj.get("tool_uuids") or []:
                    await _scan(tool_uuid, "tool")
                for snippet_uuid in skill_obj.get("snippet_uuids") or []:
                    await _scan(snippet_uuid, "snippet")
            else:
                await _scan(uuid, ctype)

        summary = {sev: 0 for sev in SEVERITIES}
        for r in results:
            for sev, count in (r.get("summary") or {}).items():
                if sev in summary:
                    summary[sev] += count

        return {"results": results, "not_found": not_found, "summary": summary}

    # ── LLM-based fix ─────────────────────────────────────────────────────────

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove a surrounding ```lang ... ``` markdown fence if present."""
        s = text.strip()
        if not s.startswith("```"):
            return text
        lines = s.splitlines()
        # drop opening fence (``` or ```python)
        lines = lines[1:]
        # drop closing fence
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines)

    def _build_fix_prompt(
        self, code: str, findings: List[Dict[str, Any]], language: str
    ) -> str:
        issues = "\n".join(
            f"- [{f.get('severity')}] {f.get('rule_id')} (line {f.get('line')}): {f.get('message')}"
            for f in findings
        )
        return (
            f"You are fixing static-analysis security findings in {language or 'source'} code.\n\n"
            f"Findings to fix:\n{issues}\n\n"
            f"Original code:\n```\n{code}\n```\n\n"
            "Rewrite the code to resolve every listed finding while preserving the "
            "original behavior and public interface. Do not add commentary. Return "
            "ONLY the complete corrected source file, with no markdown fences."
        )

    async def fix_object(
        self,
        uuid: str,
        severities: Optional[List[str]] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Use the LLM to fix an object's code for findings at given severities.

        Re-scans to get current findings, filters to ``severities`` (default:
        all), asks the model to rewrite the code, overwrites the stored code in
        place, and records the fix in extra["evaluation"]["sast_fix"].

        Returns a per-object result dict with ``status`` one of: fixed,
        no_code, no_matching_findings, error.
        """
        if self._store_api is None:
            raise RuntimeError("Store API not available")
        if self._llm is None:
            raise RuntimeError(self._llm_status)

        if content_type is None:
            content_type = self._infer_type(uuid)
            if content_type is None:
                raise ValueError(f"Object {uuid} not found in store")

        if content_type == "tool":
            obj = self.store.get_tool(uuid)
        elif content_type == "snippet":
            obj = self.store.get_snippet(uuid)
        else:
            obj = None  # skills have no code of their own
        if content_type == "skill" or not obj:
            return {
                "uuid": uuid,
                "content_type": content_type,
                "status": "no_code",
            }

        blobs = self._extract_code(obj, content_type)
        if not blobs:
            return {
                "uuid": uuid,
                "name": obj.get("name"),
                "content_type": content_type,
                "status": "no_code",
            }
        blob = blobs[0]

        # Current findings, filtered to requested severities.
        wanted = set(severities) if severities else set(SEVERITIES)
        scan = await self.scan_object(uuid, content_type)
        findings = [f for f in scan.get("findings", []) if f.get("severity") in wanted]
        if not findings:
            return {
                "uuid": uuid,
                "name": obj.get("name"),
                "content_type": content_type,
                "status": "no_matching_findings",
            }

        old_code = blob["code"]
        prompt = self._build_fix_prompt(old_code, findings, blob["language"])
        try:
            raw = await self._llm.generate_async(prompt=prompt)
        except Exception as e:  # noqa: BLE001
            logger.error("LLM fix failed for %s %s: %s", content_type, uuid, e)
            return {
                "uuid": uuid,
                "name": obj.get("name"),
                "content_type": content_type,
                "status": "error",
                "error": str(e),
            }
        new_code = self._strip_code_fences(raw)

        # Persist the fixed code in place.
        if content_type == "tool":
            self.store.tools.write_file(uuid, obj["module_name"], new_code)
        else:  # snippet
            obj["content"] = new_code
            self.store.snippets.write_dict(uuid, obj)

        # Record the fix without clobbering the existing sast block.
        obj = (
            self.store.get_tool(uuid)
            if content_type == "tool"
            else self.store.get_snippet(uuid)
        ) or obj
        if not isinstance(obj.get("extra"), dict):
            obj["extra"] = {}
        if not isinstance(obj["extra"].get("evaluation"), dict):
            obj["extra"]["evaluation"] = {}
        obj["extra"]["evaluation"]["sast_fix"] = {
            "model": self._llm_model,
            "severities": sorted(wanted),
            "rule_ids": sorted(
                {f.get("rule_id") for f in findings if f.get("rule_id")}
            ),
        }
        if content_type == "tool":
            self.store.tools.write_dict(uuid, obj)
        else:
            self.store.snippets.write_dict(uuid, obj)

        return {
            "uuid": uuid,
            "name": obj.get("name"),
            "content_type": content_type,
            "status": "fixed",
            "old_code": old_code,
            "new_code": new_code,
            "fixed_findings": findings,
        }

    async def fix_objects(
        self,
        uuids: List[str],
        severities: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Fix several objects; type inferred per UUID. Skills are skipped
        (no code of their own); unresolved UUIDs go to ``not_found``."""
        if self._store_api is None:
            raise RuntimeError("Store API not available")
        if self._llm is None:
            raise RuntimeError(self._llm_status)

        results: List[Dict[str, Any]] = []
        not_found: List[str] = []
        for uuid in uuids:
            try:
                results.append(await self.fix_object(uuid, severities))
            except ValueError:
                not_found.append(uuid)
        return {"results": results, "not_found": not_found}

    # ── plugin interface ──────────────────────────────────────────────────────

    def get_router(self):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter()

        class ScanRequest(BaseModel):
            uuid: str
            content_type: Optional[str] = None

        class FixRequest(BaseModel):
            # Objects to fix (tool/snippet uuids) + which severities to address.
            object_uuids: List[str]
            severities: Optional[List[str]] = None

        @router.post("/scan")
        async def scan_endpoint(request: ScanRequest):
            """Scan a store object and persist SAST findings."""
            if not self.is_enabled():
                raise HTTPException(status_code=503, detail=self._status_message)
            try:
                result = await self.scan_object(
                    uuid=request.uuid,
                    content_type=request.content_type,
                )
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error(
                    "SAST scan failed for %s: %s",
                    request.uuid,
                    e,
                    exc_info=True,
                )
                raise HTTPException(status_code=500, detail=str(e))

            return {"success": True, **result}

        @router.post("/fix")
        async def fix_endpoint(request: FixRequest):
            """Fix selected objects' findings (at given severities) with the LLM."""
            if not self._fix_available():
                raise HTTPException(status_code=503, detail=self._llm_status)
            if not request.object_uuids:
                raise HTTPException(
                    status_code=400, detail="object_uuids must not be empty"
                )
            try:
                result = await self.fix_objects(
                    uuids=request.object_uuids,
                    severities=request.severities,
                )
            except Exception as e:
                logger.error(
                    "SAST fix failed for %s: %s", request.object_uuids, e, exc_info=True
                )
                raise HTTPException(status_code=500, detail=str(e))
            return {"success": True, **result}

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
                                "enum": ["tool", "skill", "snippet"],
                                "description": "Type of object to scan",
                            },
                        },
                        "required": ["uuid"],
                    },
                }
            ],
        }
