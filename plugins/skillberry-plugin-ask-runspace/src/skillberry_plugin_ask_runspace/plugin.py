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
            description=(
                "Run the Runspace agent on any free-text task — create tools & skills, "
                "build MCP servers, optimize skills, research, document, or debug — with "
                "optional starter examples, then view the agent's summary."
            ),
            plugin_type=PluginType.CREATOR,
        )
        self._execution_mode = os.getenv("RUNSPACE_MODE", "container")
        self._claude_settings = None
        self._jobs: Dict[str, Any] = {}
        self._workspaces: Dict[str, str] = {}
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
        import shutil
        import tempfile
        import uuid
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel
        from claude_code_sdk import ClaudeCodeOptions

        from skillberry_plugin_ask_runspace.presets import PRESETS
        from skillberry_plugin_ask_runspace import runner

        router = APIRouter()

        class RunRequest(BaseModel):
            request: str
            skills: list[str] = []
            execution_mode: Optional[str] = None
            agent_env: Optional[Dict[str, str]] = None
            keep_workspace: bool = False

        @router.get("/presets")
        async def presets():
            return PRESETS

        async def _execute(job_id: str, req: RunRequest):
            # By default the scratch workspace only needs to live for the
            # duration of the run: read_summary returns the summary as a string
            # (from the runspace-managed session workspace in container mode, or
            # the editable dir in local mode), so we delete the temp dir once we
            # have it. When keep_workspace is set, we retain it for inspection
            # and expose a delete endpoint instead.
            tmp = tempfile.mkdtemp(prefix="ask-runspace-")
            if req.keep_workspace:
                self._workspaces[job_id] = tmp
            try:
                editable = Path(tmp) / "editable"; editable.mkdir()
                context = Path(tmp) / "context"; context.mkdir()
                mode = req.execution_mode or self._execution_mode
                options = ClaudeCodeOptions(env=self._build_claude_env(req.agent_env))
                result = await runner.run_task_session(
                    req.request, str(editable), str(context), options, mode,
                    remote_skills=req.skills,
                )
                summary = runner.read_summary(result.session_id, str(editable), mode)
                payload = {
                    "session_id": result.session_id,
                    "summary_md": summary or "_The agent finished but did not produce a summary._",
                }
                if req.skills:
                    payload["message"] = "Loaded skills: " + ", ".join(req.skills)
                if req.keep_workspace:
                    payload["workspace_dir"] = tmp
                return payload
            finally:
                if not req.keep_workspace:
                    shutil.rmtree(tmp, ignore_errors=True)

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

        @router.post("/cleanup/{job_id}")
        async def cleanup_workspace(job_id: str):
            path = self._workspaces.pop(job_id, None)
            if path is None:
                raise HTTPException(status_code=404, detail="No kept workspace for this job")
            shutil.rmtree(path, ignore_errors=True)
            return {"success": True, "message": "Workspace deleted", "data": {"deleted": path}}

        return router

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        return {
            "icon": "RobotIcon",
            "color": "#7C3AED",
            "actions": [
                {
                    "label": "Run task",
                    "endpoint": "/plugins/ask-runspace/run",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "preset_id": {
                                "type": "string",
                                "title": "Example task (optional)",
                                "x-options-from": "/api/plugins/ask-runspace/presets",
                                "x-option-label": "label",
                                "x-option-value": "id",
                                "x-prefill": {"request": "prompt", "skills": "skills"},
                            },
                            "request": {
                                "type": "string",
                                "title": "Your request",
                                "format": "textarea",
                                "description": "Describe what you want the agent to do.",
                            },
                            "skills": {
                                "type": "array",
                                "title": "Skills to load (npx)",
                                "description": (
                                    "Remote skill sources installed into the agent via npx "
                                    "(GitHub URLs or owner/repo). Selecting an example fills "
                                    "this in; edit freely."
                                ),
                            },
                            "execution_mode": {
                                "type": "string",
                                "enum": ["container", "local"],
                                "default": "container",
                                "title": "Execution mode",
                            },
                            "agent_env": {
                                "type": "object",
                                "title": "Environment overrides (optional)",
                                "description": (
                                    "Per-run overrides for the Claude Code agent environment. "
                                    "Your ~/.claude/settings.json env block and the server's "
                                    "ANTHROPIC_*/CLAUDE_* variables are already loaded automatically; "
                                    "only set this to override them."
                                ),
                            },
                            "keep_workspace": {
                                "type": "boolean",
                                "default": False,
                                "title": "Keep workspace folder after run",
                                "description": (
                                    "Keep the agent's scratch workspace on the server for inspection. "
                                    "When off (default) it is deleted automatically after the run."
                                ),
                            },
                        },
                        "required": ["request"],
                    },
                    "async_action": {
                        "status_endpoint": "/api/plugins/ask-runspace/status/{job_id}",
                        "result_markdown_field": "summary_md",
                        "cleanup_action": {
                            "endpoint": "/api/plugins/ask-runspace/cleanup/{job_id}",
                            "label": "Delete workspace",
                            "when_field": "workspace_dir",
                        },
                        "labels": {
                            "pending": "Agent is working…",
                            "ready": "Task complete",
                            "failed": "Task failed",
                            "timeout": "Could not confirm status — check the plugin logs",
                            "done": "Done",
                        },
                    },
                }
            ],
        }
