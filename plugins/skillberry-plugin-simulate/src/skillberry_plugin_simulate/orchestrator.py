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

    def _resolve_real_vmcp(
        self, skill_uuid: str, vmcp_uuid: Optional[str] = None
    ) -> Dict[str, Any]:
        if vmcp_uuid:
            vmcp = self._store.get_vmcp(vmcp_uuid)
            if not vmcp:
                raise ValueError(f"vMCP {vmcp_uuid} not found")
            if vmcp.get("skill_uuid") != skill_uuid:
                raise ValueError(
                    f"vMCP {vmcp_uuid} does not belong to skill {skill_uuid}"
                )
            if SIMULATION_TAG in vmcp.get("tags", []):
                raise ValueError(f"vMCP {vmcp_uuid} is a simulation vMCP; provide the real vMCP UUID")
            return vmcp
        all_vmcps = self._store.list_vmcps()
        real = [
            v for v in all_vmcps
            if v.get("skill_uuid") == skill_uuid
            and SIMULATION_TAG not in v.get("tags", [])
        ]
        if not real:
            raise ValueError(
                f"skill {skill_uuid} has no running vMCP to simulate against"
            )
        if len(real) > 1:
            raise ValueError(
                f"skill {skill_uuid} has multiple vMCPs — provide vmcp_uuid to specify which is 'real'"
            )
        return real[0]

    async def simulate(
        self, skill_uuid: str, vmcp_uuid: Optional[str] = None, env_id: str = ""
    ) -> Dict[str, Any]:
        skill = self._store.get_skill(skill_uuid)
        if not skill:
            raise ValueError(f"skill {skill_uuid} not found")

        tools = [self._store.get_tool(u) for u in skill.get("tool_uuids", [])]
        tools = [t for t in tools if t]
        if not tools:
            raise ValueError(f"skill {skill_uuid} has no tools to simulate")

        vmcp = self._resolve_real_vmcp(skill_uuid, vmcp_uuid)
        real_vmcp_uuid = vmcp["uuid"]
        base_name = vmcp.get("name") or skill.get("name") or skill_uuid

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
                "extra": {"simulation": True, "simulation_of_skill": skill_uuid},
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
                    "simulation_of_skill": skill_uuid,
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
            skill_uuid, real_vmcp_uuid=real_vmcp_uuid, sim_vmcp_uuid=sim_vmcp["uuid"]
        )
        logger.info("Simulated vMCP %s created for skill %s", sim_vmcp["uuid"], skill_uuid)
        return {
            "success": True,
            "skill_uuid": skill_uuid,
            "real_vmcp_uuid": real_vmcp_uuid,
            "sim_vmcp_uuid": sim_vmcp["uuid"],
            "sim_skill_uuid": sim_skill["uuid"],
            "harness_mcp_url": harness_mcp_url,
        }

    def resolve(self, skill_uuid: str) -> Dict[str, Any]:
        active_uuid = self._registry.active_vmcp_uuid(skill_uuid)
        if active_uuid is None:
            raise KeyError(skill_uuid)
        entry = self._registry.get(skill_uuid)
        vmcp = self._store.get_vmcp(active_uuid)
        if not vmcp:
            raise ValueError(f"active vMCP {active_uuid} not found")
        extra = vmcp.get("extra", {}) or {}
        harness_url = (extra.get("harness") or {}).get("mcp_url")
        port = vmcp.get("port")
        mcp_url = harness_url if harness_url else f"http://127.0.0.1:{port}/sse"
        return {
            "skill_uuid": skill_uuid,
            "mode": entry["active"],
            "vmcp_uuid": active_uuid,
            "mcp_url": mcp_url,
        }

    def toggle(self, skill_uuid: str) -> Dict[str, Any]:
        new_active = self._registry.toggle(skill_uuid)
        return {"success": True, "skill_uuid": skill_uuid, "active": new_active}

    def teardown(self, skill_uuid: str) -> Dict[str, Any]:
        entry = self._registry.get(skill_uuid)
        if entry is None:
            raise KeyError(skill_uuid)
        sim_vmcp_uuid = entry.get("sim_vmcp_uuid")
        if sim_vmcp_uuid:
            sim_vmcp = self._store.get_vmcp(sim_vmcp_uuid)
            extra = (sim_vmcp or {}).get("extra", {})
            sim_skill_uuid = extra.get("sim_skill_uuid")
            container_id = (extra.get("harness") or {}).get("container_id")
            self._store.delete_vmcp(sim_vmcp_uuid)
            if sim_skill_uuid:
                sim_skill = self._store.get_skill(sim_skill_uuid)
                for tool_uuid in (sim_skill or {}).get("tool_uuids", []):
                    self._store.delete_tool(tool_uuid)
                self._store.delete_skill(sim_skill_uuid)
            if container_id:
                self._harness_manager.stop(container_id)
        self._registry.remove(skill_uuid)
        return {"success": True, "skill_uuid": skill_uuid}

    def check_drift(self, skill_uuid: str) -> Dict[str, Any]:
        entry = self._registry.get(skill_uuid)
        if entry is None:
            raise KeyError(skill_uuid)
        sim_vmcp = self._store.get_vmcp(entry["sim_vmcp_uuid"])
        recorded = (sim_vmcp or {}).get("extra", {}).get("tools_fingerprint")
        skill = self._store.get_skill(skill_uuid)
        tools = [self._store.get_tool(u) for u in (skill or {}).get("tool_uuids", [])]
        tools = [t for t in tools if t]
        current = tools_fingerprint(tools)
        return {"skill_uuid": skill_uuid, "drifted": recorded != current,
                "recorded": recorded, "current": current}
