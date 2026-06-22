"""Thin wrapper around runspace_agent execution and summary retrieval."""
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Terminal session states reported by the runspace server's /sessions/{id}.
_SERVER_DONE = {"completed", "failed"}


def normalize_server_url(url: Optional[str]) -> str:
    """Normalize a runspace server base URL (scheme default, no trailing slash)."""
    url = (url or "").strip() or "http://localhost:6767"
    if "://" not in url:
        url = "http://" + url
    return url.rstrip("/")


@dataclass
class ServerRunResult:
    """Outcome of a run executed against a remote runspace server."""

    session_id: str
    summary: Optional[str]
    session_url: str


async def run_task_session(prompt: str, editable_dir: str, context_dir: str,
                           options: Any, mode: str,
                           remote_skills: Optional[list[str]] = None,
                           skills_dir: Optional[str] = None):
    """Run a single Runspace agent session and return its RunspaceResult.

    ``skills_dir`` is an optional local directory of custom skills (one
    subfolder per skill, each with its own SKILL.md); it is loaded into the
    agent alongside any ``remote_skills``. MCP servers are passed through the
    agent ``options`` (``ClaudeCodeOptions.mcp_servers``).
    """
    from runspace_agent import RunspaceSession, run_agent

    session = RunspaceSession(
        editable_dir=Path(editable_dir),
        context_dir=Path(context_dir),
        prompt=prompt,
        agent_options=options,
        mode="container" if mode == "container" else "local",
        remote_skills=remote_skills or None,
        skills_dir=Path(skills_dir) if skills_dir else None,
    )
    result = await run_agent(session)
    if not result.success:
        raise RuntimeError(result.agent_result.error or "Agent run failed")
    return result


async def run_via_server(base_url: str, prompt: str, editable_dir: str, context_dir: str,
                         mode: str, remote_skills: Optional[list[str]] = None,
                         skills_dir: Optional[str] = None,
                         mcp_servers: Optional[Dict[str, Any]] = None,
                         agent_env: Optional[Dict[str, str]] = None,
                         poll_interval: float = 2.0,
                         timeout: float = 3600.0) -> ServerRunResult:
    """Run a task on a remote runspace server instead of the in-process library.

    POSTs to ``{base_url}/run``, polls ``/sessions/{id}`` until the session is
    completed/failed, then fetches the summary. ``editable_dir``/``context_dir``
    are server-side paths — this works when the server shares the filesystem
    (the localhost default); for a truly remote host those paths must exist
    there. Returns the session id, summary text, and a clickable session URL.
    """
    import httpx

    base = normalize_server_url(base_url)
    body: Dict[str, Any] = {
        "prompt": prompt,
        "editable_dir": editable_dir,
        "context_dir": context_dir,
        "mode": "container" if mode == "container" else "local",
        "remote_skills": remote_skills or None,
        "skills_dir": skills_dir or None,
        "mcp_servers": mcp_servers or None,
    }
    if agent_env:
        body["agent_settings"] = {"env": agent_env}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{base}/run", json=body)
        resp.raise_for_status()
        session_id = resp.json()["session_id"]
        session_url = f"{base}/ui/sessions/{session_id}"

        waited = 0.0
        while True:
            detail = (await client.get(f"{base}/sessions/{session_id}")).json()
            status = detail.get("status")
            if status in _SERVER_DONE:
                break
            if waited >= timeout:
                raise RuntimeError(f"Timed out waiting for session {session_id} ({status})")
            await asyncio.sleep(poll_interval)
            waited += poll_interval

        if status == "failed":
            raise RuntimeError(detail.get("error") or "Runspace server reported a failed run")

        summary = None
        if detail.get("has_summary"):
            sresp = await client.get(f"{base}/sessions/{session_id}/summary")
            if sresp.status_code == 200:
                summary = sresp.json().get("content")

    return ServerRunResult(session_id=session_id, summary=summary, session_url=session_url)


def read_summary(session_id: str, editable_dir: str, mode: str) -> Optional[str]:
    """Read summary.md produced by the agent for this session, if present."""
    from runspace_agent.workspaces import session_workspace

    candidates = []
    try:
        ws = session_workspace(session_id)
        candidates += [ws / "agent_workspace" / "summary.md", ws / "summary.md"]
    except Exception:  # noqa: BLE001
        pass
    candidates += [Path(editable_dir) / "summary.md"]
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return None
