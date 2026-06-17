"""Simulate This plugin: parallel simulated vMCP + real/sim routing registry."""
import asyncio
import logging
import os
import uuid
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

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
        self._jobs: Dict[str, asyncio.Task] = {}
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
            skill_uuid: str
            vmcp_uuid: Optional[str] = None

        class SkillRequest(BaseModel):
            skill_uuid: str

        @router.post("/simulate")
        async def simulate(request: SimulateRequest):
            job_id = str(uuid.uuid4())
            task = asyncio.create_task(
                self._get_orchestrator().simulate(request.skill_uuid, request.vmcp_uuid),
                name=f"simulate-{job_id}",
            )
            self._jobs[job_id] = task
            return {
                "success": True,
                "message": "Simulation is starting...",
                "data": {"job_id": job_id, "status": "pending"},
            }

        @router.get("/status/{job_id}")
        async def simulate_status(job_id: str):
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
                logger.error("simulate job %s failed: %s", job_id, exc)
                return {"job_id": job_id, "status": "failed", "detail": str(exc)}
            return {"job_id": job_id, "status": "ready", **task.result()}

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
                            "skill_uuid": {
                                "type": "string",
                                "title": "Skill",
                                "x-options-from": "/api/skills/",
                                "x-option-label": "name",
                                "x-option-value": "uuid",
                                "x-exclude-tags": ["simulation"],
                            },
                            "vmcp_uuid": {
                                "type": "string",
                                "title": "vMCP Server",
                                "x-options-from": "/api/vmcp_servers/?skill_uuid={skill_uuid}",
                                "x-depends-on": "skill_uuid",
                                "x-option-label": "name",
                                "x-option-value": "uuid",
                                "x-exclude-tags": ["simulation"],
                            },
                        },
                        "required": ["skill_uuid"],
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
