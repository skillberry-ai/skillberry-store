"""Ask Runspace: run the Runspace agent on a free-text task and show its summary."""
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
from skillberry_store.plugins.claude_credentials import (
    load_claude_settings, settings_env, has_api_access, build_agent_env,
)

logger = logging.getLogger(__name__)

try:
    import runspace_agent
    from runspace_agent import RunspaceSession, run_agent
    from runspace_agent.workspaces import session_workspace
except ImportError:
    runspace_agent = None
    RunspaceSession = None
    run_agent = None
    session_workspace = None


class SkillberryPluginAskRunspace(PluginBase):
    def __init__(self):
        super().__init__()
        self._metadata = PluginMetadata(
            name="Ask Runspace",
            version="0.1.0",
            description="Run the Runspace agent on a free-text task and view its summary.",
            plugin_type=PluginType.CREATOR,
        )
        self._execution_mode = os.getenv("RUNSPACE_MODE", "container")
        self._claude_settings = None
        self._jobs: Dict[str, Any] = {}
        self._load_claude_settings()
        self._runspace_available = runspace_agent is not None
        self._credentials_configured = self._check_credentials()

    def _load_claude_settings(self):
        self._claude_settings = load_claude_settings()

    def _check_credentials(self) -> bool:
        return has_api_access(os.environ) or has_api_access(settings_env(self._claude_settings))

    def _build_claude_env(self, override_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        return build_agent_env(self._claude_settings, override_env)

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def is_enabled(self) -> bool:
        return self._runspace_available and self._credentials_configured

    def get_status_message(self) -> str:
        if not self._runspace_available:
            return "Missing dependency: runspace-agent not installed"
        if not self._credentials_configured:
            return ("Missing credentials: Set ANTHROPIC_API_KEY, configure ~/.claude/settings.json, "
                    "or provide ANTHROPIC_BASE_URL + ANTHROPIC_AUTH_TOKEN")
        return f"Ready ({self._execution_mode} mode)"

    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        return None

    def get_router(self):
        import asyncio
        import tempfile
        import uuid
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel
        from claude_code_sdk import ClaudeCodeOptions

        from skillberry_plugin_ask_runspace.presets import PRESETS, compose_prompt
        from skillberry_plugin_ask_runspace import runner

        router = APIRouter()

        class RunRequest(BaseModel):
            request: str
            preset_id: Optional[str] = None
            execution_mode: Optional[str] = None
            agent_env: Optional[Dict[str, str]] = None

        @router.get("/presets")
        async def presets():
            return PRESETS

        async def _execute(job_id: str, req: RunRequest):
            tmp = tempfile.mkdtemp(prefix="ask-runspace-")
            editable = Path(tmp) / "editable"; editable.mkdir()
            context = Path(tmp) / "context"; context.mkdir()
            prompt = compose_prompt(req.preset_id, req.request)
            mode = req.execution_mode or self._execution_mode
            options = ClaudeCodeOptions(env=self._build_claude_env(req.agent_env))
            result = await runner.run_task_session(prompt, str(editable), str(context), options, mode)
            summary = runner.read_summary(result.session_id, str(editable), mode)
            return {"session_id": result.session_id, "summary_md": summary}

        @router.post("/run")
        async def run(req: RunRequest):
            if not req.request or not req.request.strip():
                raise HTTPException(status_code=400, detail="request must not be empty")
            job_id = str(uuid.uuid4())
            self._jobs[job_id] = asyncio.create_task(_execute(job_id, req), name=f"ask-runspace-{job_id}")
            return {"success": True, "message": "Task is starting…",
                    "data": {"job_id": job_id, "status": "pending"}}

        @router.get("/status/{job_id}")
        async def status(job_id: str):
            task = self._jobs.get(job_id)
            if task is None:
                raise HTTPException(status_code=404, detail=f"Unknown job {job_id}")
            if not task.done():
                return {"job_id": job_id, "status": "pending"}
            try:
                exc = task.exception()
            except asyncio.CancelledError:
                return {"job_id": job_id, "status": "failed", "detail": "Job was cancelled"}
            if exc is not None:
                logger.error("ask-runspace job %s failed: %s", job_id, exc)
                return {"job_id": job_id, "status": "failed", "detail": str(exc)}
            return {"job_id": job_id, "status": "ready", **task.result()}

        return router

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        return None  # implemented in Task 5
