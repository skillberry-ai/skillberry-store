from unittest.mock import MagicMock

import httpx
import pytest

from skillberry_plugin_simulate.config import SimulateConfig
from skillberry_plugin_simulate.harness_client import HarnessClient
from skillberry_plugin_simulate.openapi_synth import OpenApiSynthesizer
from skillberry_plugin_simulate.orchestrator import SimulateOrchestrator
from skillberry_plugin_simulate.registry import ActiveVmcpRegistry


def _store():
    store = MagicMock()
    store.get_vmcp.return_value = {"uuid": "real-vmcp", "name": "weather", "skill_uuid": "skill-1"}
    store.get_skill.return_value = {"uuid": "skill-1", "name": "weather", "tool_uuids": ["t1"]}
    store.get_tool.return_value = {
        "uuid": "t1", "name": "get_weather", "description": "real",
        "params": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        "tags": [], "programming_language": "python",
    }
    store.create_tool.return_value = {"uuid": "sim-t1", "name": "get_weather"}
    store.create_skill.return_value = {"uuid": "sim-skill", "name": "weather-sim"}
    store.create_vmcp.return_value = {"uuid": "sim-vmcp", "port": 10002}
    return store


def _orch(tmp_path, store):
    cfg = SimulateConfig(llm_api_key="sk", llm_api_base=None, harness_image="sim:latest",
                         data_dir=str(tmp_path), skills_store_path=None, logs_path=None)
    harness_mgr = MagicMock()
    harness_mgr.allocate_ports.return_value = (8600, 8700)
    harness_mgr.start.return_value = {
        "container_id": "c1", "rest_port": 8600, "mcp_port": 8700, "rest_url": "http://127.0.0.1:8600",
    }

    def ready_handler(request):
        if request.method == "POST":
            return httpx.Response(200, json={"status": "starting"})
        return httpx.Response(200, json={"status": "ready", "mcp_url": "http://127.0.0.1:8700/sse"})

    def client_factory(rest_url):
        transport = httpx.MockTransport(ready_handler)
        return HarnessClient(httpx.AsyncClient(transport=transport, base_url=rest_url))

    reg = ActiveVmcpRegistry(str(tmp_path / "reg.json"))
    return SimulateOrchestrator(
        store=store, config=cfg, registry=reg, synthesizer=OpenApiSynthesizer(),
        harness_manager=harness_mgr, harness_client_factory=client_factory,
    ), harness_mgr, reg


@pytest.mark.asyncio
async def test_simulate_creates_sim_tools_skill_vmcp_and_registers(tmp_path):
    store = _store()
    orch, harness_mgr, reg = _orch(tmp_path, store)

    result = await orch.simulate("real-vmcp")

    # sim tool created as mcp-packaged pointing at harness
    tool_call = store.create_tool.call_args
    assert tool_call.args[0]["packaging_format"] == "mcp"
    assert tool_call.args[0]["packaging_params"]["mcp_url"] == "http://127.0.0.1:8700/sse"

    # sim skill references the new sim tool uuid and is tagged simulation
    skill_data = store.create_skill.call_args.args[0]
    assert skill_data["tool_uuids"] == ["sim-t1"]
    assert "simulation" in skill_data["tags"]

    # sim vMCP references the sim skill and records pairing in extra
    vmcp_data = store.create_vmcp.call_args.args[0]
    assert vmcp_data["skill_uuid"] == "sim-skill"
    assert vmcp_data["extra"]["simulation_of"] == "real-vmcp"
    assert vmcp_data["extra"]["simulation_of_skill"] == "skill-1"
    assert vmcp_data["extra"]["harness"]["container_id"] == "c1"

    # registry paired, default active=real
    entry = reg.get("skill-1")
    assert entry == {"active": "real", "real_vmcp_uuid": "real-vmcp", "sim_vmcp_uuid": "sim-vmcp"}
    assert result["sim_vmcp_uuid"] == "sim-vmcp"


@pytest.mark.asyncio
async def test_simulate_unknown_vmcp_raises(tmp_path):
    store = _store()
    store.get_vmcp.return_value = None
    orch, _, _ = _orch(tmp_path, store)
    with pytest.raises(ValueError):
        await orch.simulate("missing")
