"""Simulate This plugin: parallel simulated vMCP + real/sim routing registry."""
import os
from typing import Any, Dict, Optional

import httpx

from skillberry_store.plugins.base import PluginBase, PluginMetadata, PluginType
from skillberry_plugin_simulate.config import SimulateConfig
from skillberry_plugin_simulate.harness_client import HarnessClient
from skillberry_plugin_simulate.harness_manager import HarnessManager
from skillberry_plugin_simulate.openapi_synth import OpenApiSynthesizer
from skillberry_plugin_simulate.orchestrator import SimulateOrchestrator
from skillberry_plugin_simulate.registry import ActiveVmcpRegistry


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

    def _get_orchestrator(self) -> SimulateOrchestrator:
        if self._orchestrator is None:
            registry = ActiveVmcpRegistry(os.path.join(self._config.data_dir, "registry.json"))
            harness_manager = HarnessManager(self._config)

            def client_factory(rest_url: str) -> HarnessClient:
                return HarnessClient(httpx.AsyncClient(base_url=rest_url, timeout=30.0))

            self._orchestrator = SimulateOrchestrator(
                store=self.store,
                config=self._config,
                registry=registry,
                synthesizer=OpenApiSynthesizer(),
                harness_manager=harness_manager,
                harness_client_factory=client_factory,
            )
        return self._orchestrator

    def get_router(self):
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter()

        class SimulateRequest(BaseModel):
            vmcp_uuid: str

        class SkillRequest(BaseModel):
            skill_uuid: str

        @router.post("/simulate")
        async def simulate(request: SimulateRequest):
            try:
                return await self._get_orchestrator().simulate(request.vmcp_uuid)
            except ValueError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @router.post("/toggle")
        async def toggle(request: SkillRequest):
            try:
                return self._get_orchestrator().toggle(request.skill_uuid)
            except KeyError:
                raise HTTPException(status_code=404, detail=f"No simulation for skill {request.skill_uuid}")
            except ValueError as e:
                raise HTTPException(status_code=409, detail=str(e))

        @router.post("/teardown")
        async def teardown(request: SkillRequest):
            try:
                return self._get_orchestrator().teardown(request.skill_uuid)
            except KeyError:
                raise HTTPException(status_code=404, detail=f"No simulation for skill {request.skill_uuid}")

        @router.get("/active/{skill_uuid}")
        async def active(skill_uuid: str):
            try:
                return self._get_orchestrator().resolve(skill_uuid)
            except KeyError:
                raise HTTPException(status_code=404, detail=f"No registry entry for skill {skill_uuid}")

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
