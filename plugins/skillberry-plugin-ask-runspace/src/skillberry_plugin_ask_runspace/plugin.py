"""Ask Runspace: run the Runspace agent on a free-text task and show its summary."""
import logging
import os
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
        return None  # implemented in Task 4

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        return None  # implemented in Task 5
