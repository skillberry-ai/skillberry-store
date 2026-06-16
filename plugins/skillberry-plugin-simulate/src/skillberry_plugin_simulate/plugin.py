"""Simulate This plugin: parallel simulated vMCP + real/sim routing registry."""
from typing import Any, Dict, Optional

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
from skillberry_plugin_simulate.config import SimulateConfig


class SkillberryPluginSimulate(PluginBase):
    """Build a simulated parallel vMCP for a skill and route real/sim."""

    def __init__(self):
        super().__init__()
        self._config = SimulateConfig.from_env()
        self._orchestrator = None
        self._metadata = PluginMetadata(
            name="Simulate This",
            version="0.1.0",
            description=(
                "Stand up a simulated parallel vMCP backed by the simulation-harness "
                "and toggle whether consumers reach the real or simulated vMCP."
            ),
            plugin_type=PluginType.CREATOR,
        )

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def _docker_available(self) -> bool:
        try:
            import docker
            docker.from_env().ping()
            return True
        except Exception:
            return False

    def is_enabled(self) -> bool:
        return self._config.is_configured() and self._docker_available()

    def get_status_message(self) -> str:
        if not self._config.is_configured():
            return "Disabled: set SIMULATE_LLM_API_KEY"
        if not self._docker_available():
            return "Disabled: Docker runtime not reachable"
        return "Ready"

    def get_cli_commands(self) -> Optional[Dict[str, Any]]:
        return None

    def get_router(self):
        from fastapi import APIRouter

        router = APIRouter()

        @router.post("/simulate")
        async def simulate(payload: dict):  # bodies fleshed out in Task 13
            return {"success": False, "detail": "not implemented"}

        @router.post("/toggle")
        async def toggle(payload: dict):
            return {"success": False, "detail": "not implemented"}

        @router.post("/teardown")
        async def teardown(payload: dict):
            return {"success": False, "detail": "not implemented"}

        @router.get("/active/{skill_uuid}")
        async def active(skill_uuid: str):
            return {"success": False, "detail": "not implemented"}

        return router

    def get_ui_config(self) -> Optional[Dict[str, Any]]:
        return {
            "icon": "CubesIcon",
            "color": "#0EA5E9",
            "actions": [
                {
                    "label": "Simulate this",
                    "endpoint": "/plugins/simulate/simulate",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "vmcp_uuid": {"type": "string", "description": "UUID of the real vMCP to simulate"}
                        },
                        "required": ["vmcp_uuid"],
                    },
                },
                {
                    "label": "Toggle real/sim",
                    "endpoint": "/plugins/simulate/toggle",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "skill_uuid": {"type": "string", "description": "Skill whose active vMCP to flip"}
                        },
                        "required": ["skill_uuid"],
                    },
                },
                {
                    "label": "Tear down",
                    "endpoint": "/plugins/simulate/teardown",
                    "method": "POST",
                    "params_schema": {
                        "type": "object",
                        "properties": {
                            "skill_uuid": {"type": "string", "description": "Skill whose simulation to tear down"}
                        },
                        "required": ["skill_uuid"],
                    },
                },
            ],
        }
