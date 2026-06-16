"""Orchestrates the simulate/teardown/toggle/resolve flows for the plugin."""
import hashlib
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from skillberry_plugin_simulate.config import SimulateConfig
from skillberry_plugin_simulate.harness_client import HarnessClient
from skillberry_plugin_simulate.openapi_synth import Synthesizer
from skillberry_plugin_simulate.registry import ActiveVmcpRegistry
from skillberry_plugin_simulate.sim_manifests import (
    SIMULATION_TAG,
    build_simulated_tool_manifest,
)

logger = logging.getLogger(__name__)

_SIM_STUB = b"# Simulated MCP tool: backend is the simulation-harness.\n"


def tools_fingerprint(tools: List[Dict[str, Any]]) -> str:
    """Stable hash of the (name, params) pairs, used to detect skill drift (O6)."""
    basis = sorted(
        (t.get("name", ""), json.dumps(t.get("params", {}), sort_keys=True)) for t in tools
    )
    return hashlib.sha256(json.dumps(basis, sort_keys=True).encode()).hexdigest()


class SimulateOrchestrator:
    def __init__(
        self,
        store: Any,
        config: SimulateConfig,
        registry: ActiveVmcpRegistry,
        synthesizer: Synthesizer,
        harness_manager: Any,
        harness_client_factory: Callable[[str], HarnessClient],
    ):
        self._store = store
        self._config = config
        self._registry = registry
        self._synth = synthesizer
        self._harness_manager = harness_manager
        self._harness_client_factory = harness_client_factory

    def _real_tools(self, vmcp: Dict[str, Any]):
        skill_uuid = vmcp.get("skill_uuid")
        if not skill_uuid:
            raise ValueError(f"vMCP {vmcp.get('uuid')} has no skill_uuid; nothing to simulate")
        skill = self._store.get_skill(skill_uuid)
        if not skill:
            raise ValueError(f"skill {skill_uuid} not found")
        tools = [self._store.get_tool(u) for u in skill.get("tool_uuids", [])]
        tools = [t for t in tools if t]
        if not tools:
            raise ValueError(f"skill {skill_uuid} has no tools to simulate")
        return skill_uuid, tools

    async def simulate(self, real_vmcp_uuid: str, env_id: str = "") -> Dict[str, Any]:
        vmcp = self._store.get_vmcp(real_vmcp_uuid)
        if not vmcp:
            raise ValueError(f"vMCP {real_vmcp_uuid} not found")
        real_skill_uuid, tools = self._real_tools(vmcp)
        base_name = vmcp.get("name") or real_vmcp_uuid

        spec = self._synth.synthesize(tools, title=base_name)
        rest_port, mcp_port = self._harness_manager.allocate_ports()
        harness = self._harness_manager.start(rest_port=rest_port, mcp_port=mcp_port)

        client = self._harness_client_factory(harness["rest_url"])
        await client.create_simulation(spec, mcp_port=mcp_port)
        harness_mcp_url = await client.wait_until_ready(
            timeout=self._config.ready_timeout_seconds,
            interval=self._config.poll_interval_seconds,
        )

        sim_tool_uuids: List[str] = []
        for tool in tools:
            manifest = build_simulated_tool_manifest(tool, harness_mcp_url=harness_mcp_url)
            created = self._store.create_tool(
                manifest, module_content=_SIM_STUB, module_filename=f"{manifest['name']}.py"
            )
            sim_tool_uuids.append(created["uuid"])

        sim_skill = self._store.create_skill(
            {
                "name": f"{base_name}-sim",
                "tool_uuids": sim_tool_uuids,
                "tags": [SIMULATION_TAG],
                "extra": {"simulation": True, "simulation_of_skill": real_skill_uuid},
            }
        )

        sim_vmcp = self._store.create_vmcp(
            {
                "name": f"{base_name}-sim",
                "skill_uuid": sim_skill["uuid"],
                "tags": [SIMULATION_TAG],
                "extra": {
                    "simulation": True,
                    "simulation_of": real_vmcp_uuid,
                    "simulation_of_skill": real_skill_uuid,
                    "sim_skill_uuid": sim_skill["uuid"],
                    "tools_fingerprint": tools_fingerprint(tools),
                    "harness": {
                        "container_id": harness["container_id"],
                        "rest_url": harness["rest_url"],
                        "rest_port": harness["rest_port"],
                        "mcp_port": harness["mcp_port"],
                        "mcp_url": harness_mcp_url,
                    },
                },
            },
            env_id=env_id,
        )

        self._registry.upsert(
            real_skill_uuid, real_vmcp_uuid=real_vmcp_uuid, sim_vmcp_uuid=sim_vmcp["uuid"]
        )
        logger.info("Simulated vMCP %s created for skill %s", sim_vmcp["uuid"], real_skill_uuid)
        return {
            "success": True,
            "skill_uuid": real_skill_uuid,
            "real_vmcp_uuid": real_vmcp_uuid,
            "sim_vmcp_uuid": sim_vmcp["uuid"],
            "sim_skill_uuid": sim_skill["uuid"],
            "harness_mcp_url": harness_mcp_url,
        }
