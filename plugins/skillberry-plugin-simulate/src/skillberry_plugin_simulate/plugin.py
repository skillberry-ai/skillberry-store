"""Simulate This plugin: parallel simulated vMCP + real/sim routing registry."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any, Dict, Optional

import httpx

from skillberry_plugin_sdk import PluginLifecycleBase

from skillberry_plugin_simulate.config import SimulateConfig
from skillberry_plugin_simulate.harness_client import HarnessClient
from skillberry_plugin_simulate.harness_manager import HarnessManager
from skillberry_plugin_simulate.openapi_synth import OpenApiSynthesizer
from skillberry_plugin_simulate.orchestrator import SimulateOrchestrator
from skillberry_plugin_simulate.registry import ActiveVmcpRegistry
from skillberry_plugin_simulate.store_adapter import SimulateStoreAdapter

logger = logging.getLogger(__name__)


class SkillberryPluginSimulate(PluginLifecycleBase):
    """Build a simulated parallel vMCP for a skill and route real/sim."""

    manifest_path = "manifest.yaml"

    def __init__(self):
        super().__init__()
        self._config: Optional[SimulateConfig] = None
        self._orchestrator: Optional[SimulateOrchestrator] = None
        self._jobs: Dict[str, asyncio.Task] = {}

    async def on_start(self) -> None:
        """Initialise the plugin's config, harness manager and orchestrator."""
        self._config = SimulateConfig.from_env()
        # Orchestrator is built lazily on first use — Docker may become
        # available after the plugin has started (self-hosted runners, etc.).
        self._orchestrator = None

    async def on_stop(self) -> None:
        # Cancel outstanding simulate jobs so the process can exit cleanly.
        for task in list(self._jobs.values()):
            if not task.done():
                task.cancel()
        self._jobs.clear()

    async def is_ready(self) -> Dict[str, Any]:
        """Report readiness. Docker must be reachable for the plugin to work."""
        try:
            import docker  # type: ignore
        except Exception:  # pragma: no cover - docker package always present
            return {"ready": False, "missing_config": ["docker socket"]}
        try:
            docker.from_env().ping()
        except Exception:
            return {"ready": False, "missing_config": ["docker socket"]}
        return {"ready": True, "missing_config": []}

    # Public accessor mostly used by tests to swap in a mock orchestrator.
    def _get_orchestrator(self) -> SimulateOrchestrator:
        if self._orchestrator is None:
            if self._config is None:
                self._config = SimulateConfig.from_env()
            registry = ActiveVmcpRegistry(os.path.join(self._config.data_dir, "registry.json"))
            harness_manager = HarnessManager(self._config)

            def client_factory(rest_url: str) -> HarnessClient:
                return HarnessClient(httpx.AsyncClient(base_url=rest_url, timeout=30.0))

            self._orchestrator = SimulateOrchestrator(
                store=SimulateStoreAdapter(self.store),
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
                return await self._get_orchestrator().teardown(request.skill_uuid)
            except KeyError:
                raise HTTPException(status_code=404, detail=f"No simulation for skill {request.skill_uuid}")

        @router.get("/active/{skill_uuid}")
        async def active(skill_uuid: str):
            try:
                return await self._get_orchestrator().resolve(skill_uuid)
            except KeyError:
                raise HTTPException(status_code=404, detail=f"No registry entry for skill {skill_uuid}")

        return router
