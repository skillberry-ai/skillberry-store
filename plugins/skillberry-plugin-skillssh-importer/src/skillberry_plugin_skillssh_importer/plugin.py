"""
Skillberry Plugin skills.sh Importer

Searches the skills.sh directory, lets the caller select skills,
then imports the SKILL.md + supporting files using the existing
Anthropic skill importer pipeline.

Authentication (automatic, no user interaction required):
  Token priority:
    1. ``skills_sh_token`` request field
    2. ``SKILLS_SH_TOKEN`` env var
    3. Auto-acquired via ``@vercel/oidc`` + Vercel CLI credentials
       (requires a one-time ``vercel login && vercel link`` in the project root)

  On every API call the plugin checks whether the current token is still
  valid.  If it is expired or missing it silently calls the ``@vercel/oidc``
  Node helper, which uses the locally-stored Vercel CLI session to mint a
  fresh OIDC token and writes it back to SKILLS_SH_TOKEN so subsequent
  calls within the same process skip the refresh.
"""

import json
import logging
import os
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

import httpx

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType

logger = logging.getLogger(__name__)

_BASE_URL = "https://skills.sh/api/v1"

# ---------------------------------------------------------------------------
# Vercel OIDC token auto-acquisition
# ---------------------------------------------------------------------------

# In-process cache: (token_string, expires_at_epoch).
# Avoids spawning a Node subprocess on every API call.
_TOKEN_CACHE: Optional[tuple] = None  # (token, expires_at)
_TOKEN_LOCK = threading.Lock()

# Buffer: treat a token as expired 60 s before its real expiry so we never
# send a token that expires mid-flight.
_EXPIRY_BUFFER_S = 60


def _jwt_exp(token: str) -> Optional[float]:
    """Decode the ``exp`` claim from a JWT without verifying the signature."""
    try:
        import base64
        parts = token.split(".")
        if len(parts) != 3:
            return None
        # Fix padding and decode the payload segment
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp")
        return float(exp) if exp is not None else None
    except Exception:
        return None


def _cached_token_valid() -> Optional[str]:
    """Return the cached token if it is still fresh, else None."""
    global _TOKEN_CACHE
    if _TOKEN_CACHE is None:
        return None
    token, expires_at = _TOKEN_CACHE
    if expires_at is None or time.time() < expires_at - _EXPIRY_BUFFER_S:
        return token
    _TOKEN_CACHE = None
    return None


def _find_vercel_project_root() -> Optional[str]:
    """Walk up from cwd to find the directory containing .vercel/project.json."""
    try:
        d = os.getcwd()
        while True:
            if os.path.isfile(os.path.join(d, ".vercel", "project.json")):
                return d
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    except OSError:
        pass
    return None


def _node_path_for_vercel_oidc() -> Optional[str]:
    """Return a NODE_PATH that includes the node_modules containing @vercel/oidc.

    Tries, in order:
      1. node_modules/ sibling of .vercel/project.json (the linked project root)
      2. node_modules/ next to this plugin file (workspace root fallback)
    """
    # Option 1: node_modules beside the linked Vercel project
    root = _find_vercel_project_root()
    if root:
        candidate = os.path.join(root, "node_modules")
        if os.path.isdir(os.path.join(candidate, "@vercel", "oidc")):
            return candidate

    # Option 2: node_modules relative to this source file
    # Installed layout: plugins/.../plugin.py → workspace_root/node_modules
    here = os.path.dirname(__file__)
    for _ in range(6):  # walk up at most 6 levels
        candidate = os.path.join(here, "node_modules")
        if os.path.isdir(os.path.join(candidate, "@vercel", "oidc")):
            return candidate
        here = os.path.dirname(here)

    return None


def _acquire_via_vercel_oidc() -> Optional[str]:
    """Call ``@vercel/oidc`` via Node to get a fresh OIDC token.

    Uses the locally-stored Vercel CLI credentials (written by ``vercel login``
    and ``vercel link``).  Returns None if Node is unavailable or the CLI is
    not linked — callers fall back to a clear error message.
    """
    # The Node one-liner calls getVercelOidcToken(), which:
    # 1. Reads VERCEL_OIDC_TOKEN env / request header if present and valid.
    # 2. Otherwise reads the Vercel CLI auth.json + project.json,
    #    exchanges the CLI access token for a short-lived OIDC JWT via
    #    POST https://api.vercel.com/v1/projects/{id}/token
    # 3. Caches the result under ~/.local/share/com.vercel.token/{projectId}
    # 4. Writes the token to process.env.VERCEL_OIDC_TOKEN and returns it.
    script = (
        "const {getVercelOidcToken} = require('@vercel/oidc');"
        "getVercelOidcToken()"
        ".then(t => { process.stdout.write(t); process.exit(0); })"
        ".catch(e => { process.stderr.write(e.message); process.exit(1); })"
    )

    # Build the environment for the child process:
    # • NODE_PATH — ensures require('@vercel/oidc') resolves even when the
    #   server process was not started from the workspace root.
    # • cwd — @vercel/oidc walks up from cwd to find .vercel/project.json,
    #   so we point it at the directory that contains that file.
    node_path = _node_path_for_vercel_oidc()
    project_root = _find_vercel_project_root()

    child_env = os.environ.copy()
    if node_path:
        existing = child_env.get("NODE_PATH", "")
        child_env["NODE_PATH"] = f"{node_path}:{existing}" if existing else node_path

    try:
        result = subprocess.run(
            ["node", "-e", script],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=project_root or None,
            env=child_env,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        logger.debug(
            "vercel oidc refresh failed (rc=%d): %s",
            result.returncode,
            result.stderr.strip(),
        )
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.debug("node not available for vercel oidc refresh: %s", exc)
        return None


def _token_from_env() -> Optional[str]:
    return os.getenv("SKILLS_SH_TOKEN") or None


def _resolve_token(override: Optional[str]) -> Optional[str]:
    """Return the best available token, refreshing silently when needed.

    Priority:
      1. ``override`` (per-request field)
      2. ``SKILLS_SH_TOKEN`` env var — checked fresh each call so that
         external token rotation (e.g. vercel env pull) is picked up.
      3. In-process cache (a previously acquired + still-valid token)
      4. Auto-acquire via ``@vercel/oidc`` Node helper (uses Vercel CLI creds)
    """
    # 1. Explicit per-request override — trust it as-is
    if override:
        return override

    # 2. Env var — always check fresh (could be rotated externally)
    env_tok = _token_from_env()
    if env_tok:
        exp = _jwt_exp(env_tok)
        if exp is None or time.time() < exp - _EXPIRY_BUFFER_S:
            return env_tok
        # env var token is expired — fall through to auto-refresh

    # 3 + 4: in-process cache, then Node-based refresh
    with _TOKEN_LOCK:
        cached = _cached_token_valid()
        if cached:
            return cached

        fresh = _acquire_via_vercel_oidc()
        if fresh:
            global _TOKEN_CACHE
            _TOKEN_CACHE = (fresh, _jwt_exp(fresh))
            # Propagate to env so other processes / tools also see it
            os.environ["SKILLS_SH_TOKEN"] = fresh
            logger.debug("skills.sh: OIDC token refreshed via Vercel CLI")
            return fresh

    return None


def _has_token_source() -> bool:
    """Return True if any token source is available (env var OR Vercel CLI linked)."""
    if _token_from_env():
        return True
    # Check whether the Vercel CLI is installed and the project is linked
    # (.vercel/project.json exists in any ancestor directory).
    try:
        d = os.getcwd()
        while True:
            if os.path.isfile(os.path.join(d, ".vercel", "project.json")):
                return True
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    except OSError:
        pass
    return False


# ---------------------------------------------------------------------------
# Low-level API helpers
# ---------------------------------------------------------------------------

def _headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _require_token(override: Optional[str]) -> str:
    """Return a valid token or raise a clear ValueError.

    On a 401 the callers invalidate the cache and call this again —
    that triggers a fresh _acquire_via_vercel_oidc() attempt.
    """
    tok = _resolve_token(override)
    if not tok:
        raise ValueError(
            "No skills.sh token available. "
            "Set SKILLS_SH_TOKEN, pass skills_sh_token, or run "
            "`vercel login && vercel link` to enable automatic token acquisition."
        )
    return tok


def _invalidate_cache() -> None:
    """Drop the in-process token cache so the next call forces a refresh."""
    global _TOKEN_CACHE
    with _TOKEN_LOCK:
        _TOKEN_CACHE = None


def search_skills(
    query: str,
    limit: int = 50,
    owner: Optional[str] = None,
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Call GET /api/v1/skills/search and return the data list."""
    tok = _require_token(token)
    params: Dict[str, Any] = {"q": query, "limit": limit}
    if owner:
        params["owner"] = owner
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{_BASE_URL}/skills/search", params=params, headers=_headers(tok))
    if resp.status_code == 401:
        # Token rejected — invalidate cache and retry once with a fresh one
        _invalidate_cache()
        tok = _require_token(token)
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{_BASE_URL}/skills/search", params=params, headers=_headers(tok))
        if resp.status_code == 401:
            raise ValueError("Invalid or expired skills.sh API token (refresh also failed)")
    resp.raise_for_status()
    return resp.json().get("data", [])


def fetch_skill_detail(
    skill_id: str,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Call GET /api/v1/skills/{id} — returns installs + files."""
    tok = _require_token(token)
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{_BASE_URL}/skills/{skill_id}", headers=_headers(tok))
    if resp.status_code == 401:
        _invalidate_cache()
        tok = _require_token(token)
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{_BASE_URL}/skills/{skill_id}", headers=_headers(tok))
        if resp.status_code == 401:
            raise ValueError("Invalid or expired skills.sh API token (refresh also failed)")
    if resp.status_code == 404:
        raise ValueError(f"Skill '{skill_id}' not found on skills.sh")
    resp.raise_for_status()
    return resp.json()


def fetch_skill_audits(
    skill_id: str,
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Call GET /api/v1/skills/audit/{id}.

    Returns [] if no audits exist yet (404 is treated as empty).
    """
    tok = _resolve_token(token)
    if not tok:
        return []
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{_BASE_URL}/skills/audit/{skill_id}", headers=_headers(tok))
    if resp.status_code == 401:
        # Retry once with a refreshed token
        _invalidate_cache()
        tok = _resolve_token(token)
        if tok:
            with httpx.Client(timeout=30) as client:
                resp = client.get(f"{_BASE_URL}/skills/audit/{skill_id}", headers=_headers(tok))
    if resp.status_code in (401, 404):
        return []
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError:
        return []
    return resp.json().get("audits", [])


# ---------------------------------------------------------------------------
# Tag builders
# ---------------------------------------------------------------------------

def _installs_tag(installs: int) -> str:
    """Bucket install counts into human-readable tags."""
    if installs >= 10_000:
        return "installs:10k+"
    if installs >= 1_000:
        return "installs:1k+"
    if installs >= 100:
        return "installs:100+"
    if installs >= 10:
        return "installs:10+"
    return "installs:<10"


def _audit_tags(audits: List[Dict[str, Any]]) -> List[str]:
    """Return one tag per audit result, e.g. audit:socket:pass."""
    tags: List[str] = []
    for audit in audits:
        slug = audit.get("slug") or audit.get("provider", "unknown").lower().replace(" ", "-")
        status = audit.get("status", "unknown")
        tags.append(f"audit:{slug}:{status}")
    return tags


def _overall_audit_tag(audits: List[Dict[str, Any]]) -> Optional[str]:
    """Return a single summary tag: audit:pass / audit:warn / audit:fail."""
    if not audits:
        return None
    statuses = {a.get("status", "unknown") for a in audits}
    if "fail" in statuses:
        return "audit:fail"
    if "warn" in statuses:
        return "audit:warn"
    if statuses == {"pass"}:
        return "audit:pass"
    return None


# ---------------------------------------------------------------------------
# Core import logic
# ---------------------------------------------------------------------------

def _files_from_detail(detail: Dict[str, Any]) -> List[Dict[str, str]]:
    """Convert the skills.sh detail 'files' list to the importer format."""
    raw: Optional[List[Dict[str, Any]]] = detail.get("files")
    if not raw:
        return []
    result: List[Dict[str, str]] = []
    for f in raw:
        path: str = f.get("path", "")
        contents: str = f.get("contents", "")
        name = path.split("/")[-1] if "/" in path else path
        result.append({"name": name, "path": path, "content": contents})
    return result


def import_skill_from_skillssh(
    skill_id: str,
    extra_tags: Optional[List[str]] = None,
    token: Optional[str] = None,
    fetch_audits: bool = True,
) -> Dict[str, Any]:
    """Fetch a skill from skills.sh and run it through the Anthropic importer.

    Returns the same shape as import_from_anthropic_skill (skill_name,
    skill_description, tools, snippets, ignored_files) plus the computed tags.
    """
    from skillberry_store.tools.anthropic.importer import (
        import_from_anthropic_skill,
        parse_skill_metadata,
    )

    detail = fetch_skill_detail(skill_id, token=token)
    files = _files_from_detail(detail)

    if not files:
        raise ValueError(f"Skill '{skill_id}' has no importable files")

    # Use the existing Anthropic skill importer — source_type 'folder' mode
    # accepts a pre-built list of file dicts.  We pass them via the 'folder'
    # pathway by writing a temp directory so we can reuse the full pipeline.
    import tempfile, os, json

    with tempfile.TemporaryDirectory() as tmpdir:
        for f in files:
            file_path = os.path.join(tmpdir, f["path"])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as fh:
                fh.write(f["content"])

        skill_name, skill_description, tools, snippets, ignored_files = (
            import_from_anthropic_skill(
                source_type="folder",
                source_data=tmpdir,
                snippet_mode="file",
            )
        )

    # Build tags
    installs: int = detail.get("installs", 0)
    tags: List[str] = ["skills.sh", _installs_tag(installs)]

    audits: List[Dict[str, Any]] = []
    if fetch_audits:
        audits = fetch_skill_audits(skill_id, token=token)
    tags.extend(_audit_tags(audits))
    overall = _overall_audit_tag(audits)
    if overall:
        tags.append(overall)

    for t in (extra_tags or []):
        if t and t not in tags:
            tags.append(t)

    return {
        "skill_name": skill_name,
        "skill_description": skill_description,
        "tools": tools,
        "snippets": snippets,
        "ignored_files": ignored_files,
        "tags": tags,
        "installs": installs,
        "audits": audits,
        "skill_id": skill_id,
    }


# ---------------------------------------------------------------------------
# Plugin class
# ---------------------------------------------------------------------------

class SkillberryPluginSkillsShImporter(PluginBase):
    """Import skills from the skills.sh directory into the store."""

    def __init__(self):
        super().__init__()
        self._metadata = PluginMetadata(
            name="skills.sh Importer",
            version="0.1.0",
            description="Search skills.sh and import selected skills into the store",
            plugin_type=PluginType.IMPORTER,
            homepage="https://skills.sh",
        )

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def is_enabled(self) -> bool:
        return _has_token_source()

    def get_status_message(self) -> str:
        if _token_from_env():
            return "Ready — token from SKILLS_SH_TOKEN env var"
        if _has_token_source():
            return "Ready — token will be auto-acquired via Vercel CLI"
        return (
            "Disabled: no token source configured. "
            "Option A — set the SKILLS_SH_TOKEN environment variable to a Vercel OIDC token "
            "(run `vercel env pull` in your project to obtain one). "
            "Option B — run `vercel login` then `vercel link` once in the project root; "
            "the plugin will then mint and refresh tokens automatically with no further setup."
        )

    def get_router(self):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel, Field

        router = APIRouter()

        # ── Search endpoint ──────────────────────────────────────────────────

        class SearchRequest(BaseModel):
            query: str = Field(..., min_length=2, description="Search query (min 2 chars)")
            limit: int = Field(50, ge=1, le=200)
            owner: Optional[str] = Field(None, description="Filter by GitHub owner")
            skills_sh_token: Optional[str] = Field(
                None, description="Vercel OIDC token; falls back to SKILLS_SH_TOKEN env var"
            )

        @router.post("/search")
        async def search(request: SearchRequest):
            """Search the skills.sh directory. Returns up to ``limit`` skill entries."""
            try:
                results = search_skills(
                    query=request.query,
                    limit=request.limit,
                    owner=request.owner,
                    token=request.skills_sh_token,
                )
                return {
                    "success": True,
                    "message": f"Found {len(results)} skill{'s' if len(results) != 1 else ''} for '{request.query}'",
                    "data": {"results": results, "count": len(results), "query": request.query},
                }
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
            except httpx.HTTPStatusError as exc:
                raise HTTPException(status_code=exc.response.status_code, detail=str(exc))
            except Exception as exc:
                logger.error(f"skills.sh search failed: {exc}", exc_info=True)
                raise HTTPException(status_code=502, detail=f"Search failed: {exc}")

        # ── Import endpoint ──────────────────────────────────────────────────

        class ImportRequest(BaseModel):
            skill_ids: List[str] = Field(
                ..., min_length=1, description="List of skills.sh skill IDs to import"
            )
            tags: Optional[List[str]] = Field(None, description="Extra tags for all imported items")
            fetch_audits: bool = Field(
                True, description="Fetch security audit results and add as tags"
            )
            skills_sh_token: Optional[str] = Field(
                None, description="Vercel OIDC token; falls back to SKILLS_SH_TOKEN env var"
            )

        @router.post("/import")
        async def import_skills(request: ImportRequest):
            """Import one or more skills from skills.sh into the store.

            For each skill ID the endpoint:
            1. Fetches the skill's files (including SKILL.md) from skills.sh.
            2. Optionally fetches security audit results.
            3. Runs the files through the Anthropic skill importer pipeline.
            4. Persists the resulting tools / snippets / skill in the store.
            5. Attaches tags: ``skills.sh``, ``installs:<bucket>``,
               ``audit:<provider>:<status>``, ``audit:<overall>``.
            """
            imported_skills: List[Dict[str, Any]] = []
            failed: List[Dict[str, Any]] = []

            for skill_id in request.skill_ids:
                try:
                    result = import_skill_from_skillssh(
                        skill_id=skill_id,
                        extra_tags=request.tags,
                        token=request.skills_sh_token,
                        fetch_audits=request.fetch_audits,
                    )
                except (ValueError, Exception) as exc:
                    logger.warning(f"Failed to import skill '{skill_id}': {exc}")
                    failed.append({"skill_id": skill_id, "error": str(exc)})
                    continue

                skill_name = result["skill_name"]
                skill_description = result["skill_description"]
                tags = result["tags"]
                tools_data = result["tools"]
                snippets_data = result["snippets"]

                # --- persist tools ---
                tool_uuids: List[str] = []
                for tool in tools_data:
                    try:
                        tool_dict = {
                            "name": tool.name,
                            "description": tool.description or "",
                            "params": getattr(tool, "params", {}),
                            "programming_language": getattr(tool, "language", "python"),
                            "packaging_format": "anthropic",
                            "packaging_params": {},
                            "tags": tags,
                        }
                        module_content = (getattr(tool, "content", "") or "").encode()
                        module_filename = getattr(tool, "source_file_name", f"{tool.name}.py")
                        stored = self.store.create_tool(
                            tool_dict,
                            module_content=module_content,
                            module_filename=module_filename,
                        )
                        tool_uuids.append(stored["uuid"])
                    except Exception as exc:
                        logger.warning(f"Tool '{tool.name}' import failed: {exc}")

                # --- persist snippets ---
                snippet_uuids: List[str] = []
                for snippet in snippets_data:
                    try:
                        snippet_dict = {
                            "name": getattr(snippet, "name", snippet_name_from(snippet)),
                            "content": getattr(snippet, "content", ""),
                            "tags": tags,
                        }
                        stored = self.store.create_snippet(snippet_dict)
                        snippet_uuids.append(stored["uuid"])
                    except Exception as exc:
                        logger.warning(f"Snippet import failed: {exc}")

                # --- persist skill ---
                skill_uuid: Optional[str] = None
                try:
                    skill_stored = self.store.create_skill(
                        {
                            "name": skill_name,
                            "description": skill_description,
                            "tool_uuids": tool_uuids,
                            "snippet_uuids": snippet_uuids,
                            "tags": tags,
                        }
                    )
                    skill_uuid = skill_stored["uuid"]
                except Exception as exc:
                    logger.warning(f"Skill creation failed for '{skill_name}': {exc}")

                imported_skills.append(
                    {
                        "skill_id": skill_id,
                        "skill_name": skill_name,
                        "skill_uuid": skill_uuid,
                        "tools_imported": len(tool_uuids),
                        "snippets_imported": len(snippet_uuids),
                        "tags": tags,
                        "installs": result["installs"],
                        "audits": result["audits"],
                    }
                )

            all_ok = len(failed) == 0 and len(imported_skills) > 0
            partial = len(failed) > 0 and len(imported_skills) > 0
            payload = {
                "imported": len(imported_skills),
                "skills": imported_skills,
                "failed": failed,
            }
            if all_ok:
                message = f"Imported {len(imported_skills)} skill{'s' if len(imported_skills) != 1 else ''} successfully"
            elif partial:
                message = f"Imported {len(imported_skills)}, failed {len(failed)}"
            else:
                message = f"All {len(failed)} skill{'s' if len(failed) != 1 else ''} failed to import"
            return {
                "success": len(failed) == 0 and len(imported_skills) > 0,
                "message": message,
                "data": payload,
            }

        return router

    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        return None

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        enabled = _has_token_source()
        base: Dict[str, Any] = {
            "icon": "SearchIcon",
            "color": "#0F766E" if enabled else "#6B7280",
        }
        if not enabled:
            base["disabled_message"] = self.get_status_message()
            base["setup_instructions"] = {
                "title": "Authentication required",
                "steps": [
                    {
                        "label": "Option A — environment variable (quickest)",
                        "description": (
                            "Set SKILLS_SH_TOKEN to a Vercel OIDC token before starting the store. "
                            "Obtain one with: npm i -g vercel && vercel env pull (.env.local)"
                        ),
                    },
                    {
                        "label": "Option B — automatic via Vercel CLI (zero maintenance)",
                        "description": (
                            "Run once in the project root: "
                            "npm i -g vercel && vercel login && vercel link  "
                            "Tokens are then minted and refreshed automatically. "
                            "No env var needed."
                        ),
                    },
                ],
                "docs_url": "https://skills.sh/docs/api#authentication",
            }
            base["actions"] = []
            return base
        base["actions"] = [
            {
                "label": "Search skills.sh",
                "endpoint": "/plugins/skillssh-importer/search",
                "method": "POST",
                "params_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (min 2 chars). Single-word: fuzzy, multi-word: semantic.",
                        },
                        "limit": {
                            "type": "integer",
                            "default": 50,
                            "description": "Max results (1–200)",
                        },
                        "owner": {
                            "type": "string",
                            "description": "Filter results to a specific GitHub owner",
                        },
                        "skills_sh_token": {
                            "type": "string",
                            "description": "Vercel OIDC token for skills.sh (overrides SKILLS_SH_TOKEN env var)",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "label": "Import Selected Skills",
                "endpoint": "/plugins/skillssh-importer/import",
                "method": "POST",
                "params_schema": {
                    "type": "object",
                    "properties": {
                        "skill_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Skill IDs from search results (e.g. ['vercel-labs/skills/find-skills'])",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Extra tags to add to all imported items",
                        },
                        "fetch_audits": {
                            "type": "boolean",
                            "default": True,
                            "description": "Fetch and attach security audit tags (audit:provider:status)",
                        },
                        "skills_sh_token": {
                            "type": "string",
                            "description": "Vercel OIDC token for skills.sh (overrides SKILLS_SH_TOKEN env var)",
                        },
                    },
                    "required": ["skill_ids"],
                },
            },
        ]
        return base


# ---------------------------------------------------------------------------
# Small private helper used inside the import endpoint
# ---------------------------------------------------------------------------

def snippet_name_from(snippet: Any) -> str:
    """Best-effort name extraction from a snippet object."""
    for attr in ("name", "title", "filename", "path"):
        v = getattr(snippet, attr, None)
        if v:
            return str(v)
    return "snippet"

# Made with Bob
