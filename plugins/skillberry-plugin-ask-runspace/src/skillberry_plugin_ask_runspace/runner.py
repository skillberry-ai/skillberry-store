"""Thin wrapper around runspace_agent execution and summary retrieval."""
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def run_task_session(prompt: str, editable_dir: str, context_dir: str,
                           options: Any, mode: str):
    """Run a single Runspace agent session and return its RunspaceResult."""
    from runspace_agent import RunspaceSession, run_agent

    session = RunspaceSession(
        editable_dir=Path(editable_dir),
        context_dir=Path(context_dir),
        prompt=prompt,
        agent_options=options,
        mode="container" if mode == "container" else "local",
    )
    result = await run_agent(session)
    if not result.success:
        raise RuntimeError(result.agent_result.error or "Agent run failed")
    return result


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
