"""
Skillberry Plugin: Skill Provenance & Background.

Gathers the trust "background" of a skill — where it came from, who published
it, whether it is legally safe, whether the bytes are genuine, and what it
reaches out to or runs — so an importer (or a later auditor) has a basis for
confidence. See issue #197.

Three modes, one code path:
  - pre-import  : caller passes a ``github_url`` (nothing stored yet)
  - post-import : caller passes a skill ``uuid`` (origin read from extra["origin"])
  - drift       : ``recheck`` re-gathers and diffs against the stored baseline

Like the SAST plugin, this is flag-only and never blocks an import: results are
written to tags + ``extra["provenance"]`` and surfaced in the generic plugin UI.
"""

import asyncio
import hashlib
import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from skillberry_plugin_sdk import PluginLifecycleBase, on_event

from .sources import resolve_source
from .sources.base import Background


class _CheckRequest(BaseModel):
    github_url: Optional[str] = None
    uuid: Optional[str] = None


class _RecheckRequest(BaseModel):
    uuid: str

logger = logging.getLogger(__name__)

# Lightweight behavioral-risk heuristics over stored skill code. This is a
# disclosure aid, not a scanner — the SAST plugin owns real static analysis,
# and we cross-link its result when present.
_URL_RE = re.compile(r"https?://[^\s\"'`)<>]+", re.IGNORECASE)
_SENSITIVE_PATTERNS = {
    "subprocess": re.compile(r"\b(subprocess|os\.system|os\.popen|pty\.spawn)\b"),
    "network": re.compile(r"\b(requests|urllib|httpx|socket|aiohttp)\b"),
    "filesystem": re.compile(r"\b(open\s*\(|shutil|pathlib|os\.remove|os\.unlink)\b"),
    "eval_exec": re.compile(r"\b(eval|exec)\s*\("),
}


def _confidence_message(bg_dict: Dict[str, Any]) -> str:
    """One-line verdict for the success banner in the generic UI."""
    conf = (bg_dict.get("confidence") or "unknown").upper()
    lic = (bg_dict.get("license") or {}).get("spdx_id") or "no license"
    pub = bg_dict.get("publisher") or {}
    who = pub.get("owner") or "unknown"
    stars = pub.get("stars")
    star_str = f", {stars}★" if isinstance(stars, int) else ""
    return f"Confidence: {conf} — {who}{star_str}, license: {lic}"


class SkillberryPluginProvenance(PluginLifecycleBase):
    """Gathers provenance / authenticity / legality background for skills."""

    manifest_path = "manifest.yaml"

    # ── readiness ─────────────────────────────────────────────────────────────

    async def is_ready(self) -> Dict[str, Any]:
        # Always available: GitHub's anonymous API works without a key; a token
        # only raises rate limits. Resolution degrades gracefully otherwise.
        return {"ready": True, "missing_config": []}

    # ── event handler (auto-baseline on import) ──────────────────────────────

    @on_event("content.skill.added")
    async def on_skill_added(self, event) -> None:
        """On skill add, if it carries an origin, compute & store the baseline.

        Best-effort, mirrors the SAST auto-scan pattern; never blocks import.
        """
        uuid = event.data.get("uuid") if isinstance(event.data, dict) else None
        if not uuid:
            return
        try:
            skill = await self.store.get_skill(uuid)
        except Exception:
            skill = None
        origin = ((skill or {}).get("extra") or {}).get("origin")
        if not origin:
            return  # not a URL import / nothing to base a check on
        try:
            await self.gather_background(uuid=uuid, persist_baseline=True)
        except Exception as e:
            logger.error(
                "Auto-provenance failed for skill %s: %s", uuid, e, exc_info=True
            )

    # ── origin resolution ────────────────────────────────────────────────────

    async def _origin_from_args(
        self, url: Optional[str], uuid: Optional[str]
    ) -> Dict[str, Any]:
        """Build an origin dict from an explicit URL, or a stored skill's uuid.

        Raises ValueError when neither yields a usable origin.
        """
        if url:
            return {"type": "github", "url": url}
        if uuid:
            skill = await self.store.get_skill(uuid)
            if not skill:
                raise ValueError(f"Skill {uuid} not found in store")
            origin = (skill.get("extra") or {}).get("origin")
            if not origin:
                raise ValueError(
                    f"Skill {uuid} has no recorded origin "
                    "(import predates provenance capture, or was not a URL import). "
                    "Pass github_url to check it."
                )
            return origin
        raise ValueError("Provide either github_url or uuid")

    # ── behavior (local, plugin-owned) ───────────────────────────────────────

    async def _gather_behavior(self, uuid: Optional[str]) -> Dict[str, Any]:
        """Disclose external endpoints / sensitive ops / SAST cross-link.

        Reads the skill's referenced tool/snippet code from the store. When no
        uuid (pure pre-import URL check) we can't see content yet, so report
        ``status: unavailable``.
        """
        if not uuid:
            return {
                "status": "unavailable",
                "note": "content not in store yet (pre-import check)",
            }
        try:
            skill = await self.store.get_skill(uuid)
        except Exception:
            skill = None
        if not skill:
            return {"status": "unavailable"}

        blobs = await self._collect_skill_code(skill)
        domains: set = set()
        ops: set = set()
        for code in blobs:
            for m in _URL_RE.findall(code):
                dom = re.sub(r"^https?://", "", m).split("/")[0]
                if dom:
                    domains.add(dom)
            for op, pat in _SENSITIVE_PATTERNS.items():
                if pat.search(code):
                    ops.add(op)

        # Cross-link an existing SAST result if the SAST plugin ran.
        sast = ((skill.get("extra") or {}).get("evaluation") or {}).get("sast")
        sast_summary = sast.get("summary") if isinstance(sast, dict) else None

        return {
            "status": "ok",
            "external_domains": sorted(domains),
            "sensitive_operations": sorted(ops),
            "files_inspected": len(blobs),
            "sast_summary": sast_summary,  # None if SAST has not run
        }

    async def _read_tool_module(self, tool_uuid: str) -> Optional[str]:
        """Fetch a tool's module source via the REST module endpoint."""
        try:
            content = await self.store.get(f"/tools/{tool_uuid}/module")
        except Exception as e:
            logger.debug("provenance: could not read tool %s: %s", tool_uuid, e)
            return None
        if content is None:
            return None
        return content if isinstance(content, str) else str(content)

    async def _collect_skill_code(self, skill: Dict[str, Any]) -> List[str]:
        """Best-effort: gather code/content strings from a skill's children."""
        out: List[str] = []
        for tool_uuid in skill.get("tool_uuids") or []:
            try:
                tool = await self.store.get_tool(tool_uuid)
                module = (tool or {}).get("module_name")
                if tool and module:
                    code = await self._read_tool_module(tool_uuid)
                    if code is not None:
                        out.append(code)
            except Exception as e:
                logger.debug("provenance: could not read tool %s: %s", tool_uuid, e)
        for snippet_uuid in skill.get("snippet_uuids") or []:
            try:
                snippet = await self.store.get_snippet(snippet_uuid)
                content = (snippet or {}).get("content")
                if content:
                    out.append(content)
            except Exception as e:
                logger.debug(
                    "provenance: could not read snippet %s: %s", snippet_uuid, e
                )
        return out

    async def _content_hashes(self, uuid: Optional[str]) -> Optional[Dict[str, str]]:
        """SHA-256 of each stored child file — a record of the imported bytes."""
        if not uuid:
            return None
        try:
            skill = await self.store.get_skill(uuid)
        except Exception:
            return None
        if not skill:
            return None
        hashes: Dict[str, str] = {}
        for tool_uuid in skill.get("tool_uuids") or []:
            try:
                tool = await self.store.get_tool(tool_uuid)
                module = (tool or {}).get("module_name")
                if tool and module:
                    code = await self._read_tool_module(tool_uuid)
                    if code is None:
                        continue
                    hashes[f"tool:{tool.get('name') or tool_uuid}"] = hashlib.sha256(
                        code.encode("utf-8", "replace")
                    ).hexdigest()
            except Exception:
                continue
        for snippet_uuid in skill.get("snippet_uuids") or []:
            try:
                snippet = await self.store.get_snippet(snippet_uuid)
                content = (snippet or {}).get("content")
                if content:
                    hashes[
                        f"snippet:{snippet.get('name') or snippet_uuid}"
                    ] = hashlib.sha256(
                        content.encode("utf-8", "replace")
                    ).hexdigest()
            except Exception:
                continue
        return hashes or None

    # ── core gather ──────────────────────────────────────────────────────────

    async def gather_background(
        self,
        url: Optional[str] = None,
        uuid: Optional[str] = None,
        persist_baseline: bool = False,
    ) -> Dict[str, Any]:
        """Gather the full background for a URL and/or stored skill uuid.

        Returns the Background as a dict. When ``uuid`` is given, also fills the
        behavior + integrity-hash sections from stored content and (optionally)
        persists the result to the skill as the baseline.
        """
        origin = await self._origin_from_args(url, uuid)
        source = resolve_source(origin)
        if source is None:
            bg = Background(source="unknown")
            bg.provenance = {
                "status": "error",
                "error": f"no provenance source for origin {origin!r}",
            }
            return bg.to_dict()

        # Remote sections (network; offloaded to a thread to avoid blocking the
        # event loop — source.gather() uses synchronous requests.get()).
        bg = await asyncio.to_thread(source.gather, origin)

        # Local sections the plugin owns (content it can see in the store).
        bg.behavior = await self._gather_behavior(uuid)
        hashes = await self._content_hashes(uuid)
        if hashes is not None:
            if not isinstance(bg.integrity, dict):
                bg.integrity = {}
            bg.integrity["content_sha256"] = hashes

        result = bg.to_dict()
        if uuid and persist_baseline:
            try:
                await self._persist(uuid, result, is_baseline=True)
            except Exception as e:
                logger.error(
                    "provenance: failed to persist baseline for %s: %s",
                    uuid, e, exc_info=True,
                )
        return result

    async def recheck(self, uuid: str) -> Dict[str, Any]:
        """Re-gather background for a stored skill and diff against its baseline.

        Returns ``{current, baseline, drift}`` where ``drift`` is a list of
        human-readable change descriptors (empty when nothing material changed).
        """
        skill = await self.store.get_skill(uuid)
        if not skill:
            raise ValueError(f"Skill {uuid} not found in store")
        baseline = ((skill.get("extra") or {}).get("provenance") or {}).get("baseline")

        current = await self.gather_background(uuid=uuid)
        drift = _compute_drift(baseline, current)

        # Record the latest check (and any drift) without losing the baseline.
        try:
            await self._persist(uuid, current, is_baseline=baseline is None, drift=drift)
        except Exception as e:
            logger.error(
                "provenance: failed to persist recheck for %s: %s",
                uuid, e, exc_info=True,
            )
        return {"uuid": uuid, "drift": drift, "current": current, "baseline": baseline}

    # ── persistence ──────────────────────────────────────────────────────────

    async def _persist(
        self,
        uuid: str,
        background: Dict[str, Any],
        is_baseline: bool,
        drift: Optional[List[str]] = None,
    ) -> None:
        """Write background to the skill's tags + extra["provenance"]."""
        skill = await self.store.get_skill(uuid)
        if not skill:
            return
        if not isinstance(skill.get("extra"), dict):
            skill["extra"] = {}
        prov = skill["extra"].get("provenance")
        if not isinstance(prov, dict):
            prov = {}
        if is_baseline:
            prov["baseline"] = background
        prov["latest"] = background
        if drift is not None:
            prov["last_drift"] = drift
        skill["extra"]["provenance"] = prov

        skill["tags"] = self._provenance_tags(
            self._strip_provenance_tags(skill.get("tags") or []), background, drift
        )
        await self.store.update_skill(uuid, skill)

    @staticmethod
    def _strip_provenance_tags(tags: List[str]) -> List[str]:
        return [t for t in tags if not t.startswith("provenance:")]

    @staticmethod
    def _provenance_tags(
        tags: List[str], background: Dict[str, Any], drift: Optional[List[str]]
    ) -> List[str]:
        out = list(tags)
        out.append(f"provenance:confidence:{background.get('confidence', 'low')}")
        lic = (background.get("license") or {}).get("spdx_id")
        out.append(f"provenance:license:{lic or 'none'}")
        if (background.get("integrity") or {}).get("commit_verified"):
            out.append("provenance:verified")
        if drift:
            out.append("provenance:drift")
        return out

    # ── plugin interface ──────────────────────────────────────────────────────

    def get_router(self):
        from fastapi import APIRouter, HTTPException

        router = APIRouter(prefix=f"/plugins/{self.manifest.slug}", tags=[self.manifest.slug])

        @router.post("/check")
        async def check_endpoint(request: _CheckRequest):
            """Gather provenance/background for a URL (pre-import) or uuid (post)."""
            try:
                data = await self.gather_background(
                    url=request.github_url,
                    uuid=request.uuid,
                    persist_baseline=bool(request.uuid),
                )
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error("provenance check failed: %s", e, exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
            return {"success": True, "message": _confidence_message(data), "data": data}

        @router.post("/recheck")
        async def recheck_endpoint(request: _RecheckRequest):
            """Re-check a stored skill and report drift vs. its baseline."""
            try:
                data = await self.recheck(request.uuid)
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                logger.error("provenance recheck failed: %s", e, exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
            drift = data.get("drift") or []
            msg = "No drift since baseline" if not drift else f"{len(drift)} change(s) detected"
            return {"success": True, "message": msg, "data": data}

        return router


# ── drift diffing (standalone, unit-tested) ──────────────────────────────────


def _compute_drift(
    baseline: Optional[Dict[str, Any]], current: Dict[str, Any]
) -> List[str]:
    """Describe material changes from ``baseline`` to ``current``.

    Returns an empty list when there is no baseline (nothing to compare) or no
    material change. Watches the fields most relevant to a trust decision:
    commit SHA, license, repo archival, star count, and per-file content hashes.
    """
    if not baseline:
        return []
    changes: List[str] = []

    b_prov, c_prov = baseline.get("provenance") or {}, current.get("provenance") or {}
    if b_prov.get("commit_sha") != c_prov.get("commit_sha"):
        changes.append(
            f"commit changed: {b_prov.get('commit_sha')} → {c_prov.get('commit_sha')}"
        )

    b_lic = (baseline.get("license") or {}).get("spdx_id")
    c_lic = (current.get("license") or {}).get("spdx_id")
    if b_lic != c_lic:
        changes.append(f"license changed: {b_lic} → {c_lic}")

    b_pub, c_pub = baseline.get("publisher") or {}, current.get("publisher") or {}
    if b_pub.get("archived") != c_pub.get("archived"):
        changes.append(
            f"archived changed: {b_pub.get('archived')} → {c_pub.get('archived')}"
        )

    b_hash = (baseline.get("integrity") or {}).get("content_sha256") or {}
    c_hash = (current.get("integrity") or {}).get("content_sha256") or {}
    for key in set(b_hash) | set(c_hash):
        if b_hash.get(key) != c_hash.get(key):
            changes.append(f"content changed: {key}")

    return changes
