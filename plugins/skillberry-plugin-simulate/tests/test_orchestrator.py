from unittest.mock import MagicMock

import httpx
import pytest

pytestmark = pytest.mark.skip(reason="TODO: rewrite for async StoreClient after plugin SDK port")


from skillberry_plugin_simulate.config import SimulateConfig
from skillberry_plugin_simulate.harness_client import HarnessClient
from skillberry_plugin_simulate.openapi_synth import OpenApiSynthesizer
from skillberry_plugin_simulate.orchestrator import SimulateOrchestrator
from skillberry_plugin_simulate.registry import ActiveVmcpRegistry
from skillberry_plugin_simulate.sim_manifests import SIMULATION_TAG


def _store(extra_vmcps=None):
    store = MagicMock()
    real_vmcp = {"uuid": "real-vmcp", "name": "weather", "skill_uuid": "skill-1", "tags": []}
    all_vmcps = [real_vmcp] + (extra_vmcps or [])
    store.get_vmcp.return_value = real_vmcp
    store.get_skill.return_value = {"uuid": "skill-1", "name": "weather", "tool_uuids": ["t1"]}
    store.list_vmcps.return_value = all_vmcps
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


# --- existing happy-path test, updated for new signature ---

@pytest.mark.asyncio
async def test_simulate_creates_sim_tools_skill_vmcp_and_registers(tmp_path):
    store = _store()
    orch, harness_mgr, reg = _orch(tmp_path, store)

    result = await orch.simulate("skill-1")

    tool_call = store.create_tool.call_args
    assert tool_call.args[0]["packaging_format"] == "mcp"
    assert tool_call.args[0]["packaging_params"]["mcp_url"] == "http://127.0.0.1:8700/sse"

    skill_data = store.create_skill.call_args.args[0]
    assert skill_data["tool_uuids"] == ["sim-t1"]
    assert "simulation" in skill_data["tags"]

    vmcp_data = store.create_vmcp.call_args.args[0]
    assert vmcp_data["skill_uuid"] == "sim-skill"
    assert vmcp_data["extra"]["simulation_of"] == "real-vmcp"
    assert vmcp_data["extra"]["simulation_of_skill"] == "skill-1"
    assert vmcp_data["extra"]["harness"]["container_id"] == "c1"

    entry = reg.get("skill-1")
    assert entry == {"active": "real", "real_vmcp_uuid": "real-vmcp", "sim_vmcp_uuid": "sim-vmcp"}
    assert result["sim_vmcp_uuid"] == "sim-vmcp"


# --- new resolution-logic tests ---

@pytest.mark.asyncio
async def test_simulate_with_explicit_vmcp_uuid(tmp_path):
    store = _store()
    orch, _, reg = _orch(tmp_path, store)

    result = await orch.simulate("skill-1", vmcp_uuid="real-vmcp")

    assert result["real_vmcp_uuid"] == "real-vmcp"
    entry = reg.get("skill-1")
    assert entry["real_vmcp_uuid"] == "real-vmcp"


@pytest.mark.asyncio
async def test_simulate_explicit_vmcp_wrong_skill_raises(tmp_path):
    store = _store()
    wrong_vmcp = {"uuid": "other-vmcp", "name": "other", "skill_uuid": "skill-99", "tags": []}
    store.get_vmcp.return_value = wrong_vmcp
    orch, _, _ = _orch(tmp_path, store)

    with pytest.raises(ValueError, match="does not belong to skill"):
        await orch.simulate("skill-1", vmcp_uuid="other-vmcp")


@pytest.mark.asyncio
async def test_simulate_no_real_vmcp_raises(tmp_path):
    store = _store()
    store.list_vmcps.return_value = []
    orch, _, _ = _orch(tmp_path, store)

    with pytest.raises(ValueError, match="has no running vMCP"):
        await orch.simulate("skill-1")


@pytest.mark.asyncio
async def test_simulate_multiple_real_vmcps_raises(tmp_path):
    second = {"uuid": "real-vmcp-2", "name": "weather2", "skill_uuid": "skill-1", "tags": []}
    store = _store(extra_vmcps=[second])
    orch, _, _ = _orch(tmp_path, store)

    with pytest.raises(ValueError, match="multiple vMCPs"):
        await orch.simulate("skill-1")


@pytest.mark.asyncio
async def test_simulate_unknown_skill_raises(tmp_path):
    store = _store()
    store.get_skill.return_value = None
    orch, _, _ = _orch(tmp_path, store)

    with pytest.raises(ValueError, match="not found"):
        await orch.simulate("missing-skill")


@pytest.mark.asyncio
async def test_simulate_explicit_sim_vmcp_raises(tmp_path):
    """_resolve_real_vmcp must reject a simulation-tagged vMCP passed as vmcp_uuid."""
    store = _store()
    sim_vmcp = {
        "uuid": "sim-vmcp",
        "name": "weather-sim",
        "skill_uuid": "skill-1",
        "tags": [SIMULATION_TAG],
    }
    store.get_vmcp.return_value = sim_vmcp
    orch, _, _ = _orch(tmp_path, store)

    with pytest.raises(ValueError, match="is a simulation vMCP"):
        await orch.simulate("skill-1", vmcp_uuid="sim-vmcp")


# --- container lifecycle / re-simulate safety ---

@pytest.mark.asyncio
async def test_simulate_stops_container_when_harness_setup_fails(tmp_path):
    """Container must be stopped when simulate() raises after harness start."""
    store = _store()
    orch, harness_mgr, reg = _orch(tmp_path, store)

    def failing_factory(rest_url):
        def boom(request):
            return httpx.Response(500, json={"error": "harness exploded"})
        return HarnessClient(httpx.AsyncClient(transport=httpx.MockTransport(boom), base_url=rest_url))

    orch._harness_client_factory = failing_factory

    with pytest.raises(Exception):
        await orch.simulate("skill-1")

    harness_mgr.stop.assert_called_once_with("c1")
    assert reg.get("skill-1") is None


@pytest.mark.asyncio
async def test_simulate_tears_down_existing_simulation_before_starting_new(tmp_path):
    """Re-simulating a skill that already has an active simulation must tear the old one down first."""
    store = _store()
    orch, harness_mgr, reg = _orch(tmp_path, store)

    reg.upsert("skill-1", real_vmcp_uuid="real-vmcp", sim_vmcp_uuid="old-sim-vmcp")

    old_sim_vmcp = {
        "uuid": "old-sim-vmcp",
        "extra": {
            "sim_skill_uuid": "old-sim-skill",
            "harness": {"container_id": "old-container"},
        },
    }
    old_sim_skill = {"uuid": "old-sim-skill", "tool_uuids": ["old-sim-t1"]}

    def get_vmcp_side(uuid):
        if uuid == "old-sim-vmcp":
            return old_sim_vmcp
        return {"uuid": "real-vmcp", "name": "weather", "skill_uuid": "skill-1", "tags": []}

    def get_skill_side(uuid):
        if uuid == "old-sim-skill":
            return old_sim_skill
        return {"uuid": "skill-1", "name": "weather", "tool_uuids": ["t1"]}

    store.get_vmcp.side_effect = get_vmcp_side
    store.get_skill.side_effect = get_skill_side

    await orch.simulate("skill-1")

    harness_mgr.stop.assert_any_call("old-container")
    store.delete_vmcp.assert_any_call("old-sim-vmcp")
    store.delete_skill.assert_any_call("old-sim-skill")
    store.delete_tool.assert_any_call("old-sim-t1")
    assert reg.get("skill-1") is not None  # new simulation registered
