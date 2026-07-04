from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.skip(reason="TODO: rewrite for async StoreClient after plugin SDK port")


from skillberry_plugin_simulate.config import SimulateConfig
from skillberry_plugin_simulate.orchestrator import SimulateOrchestrator
from skillberry_plugin_simulate.registry import ActiveVmcpRegistry


def _orch(tmp_path, store, harness_mgr=None):
    cfg = SimulateConfig(llm_api_key="sk", llm_api_base=None, harness_image="sim:latest",
                         data_dir=str(tmp_path), skills_store_path=None, logs_path=None)
    reg = ActiveVmcpRegistry(str(tmp_path / "reg.json"))
    return SimulateOrchestrator(
        store=store, config=cfg, registry=reg, synthesizer=MagicMock(),
        harness_manager=harness_mgr or MagicMock(),
        harness_client_factory=lambda url: MagicMock(),
    ), reg


def test_resolve_returns_active_url_and_mode(tmp_path):
    store = MagicMock()
    store.get_vmcp.return_value = {"uuid": "real-vmcp", "port": 10001}
    orch, reg = _orch(tmp_path, store)
    reg.upsert("skill-1", real_vmcp_uuid="real-vmcp", sim_vmcp_uuid="sim-vmcp")

    out = orch.resolve("skill-1")
    assert out["mode"] == "real"
    assert out["mcp_url"] == "http://127.0.0.1:10001/sse"

    reg.set_active("skill-1", "sim")
    store.get_vmcp.return_value = {"uuid": "sim-vmcp", "port": 10002}
    out = orch.resolve("skill-1")
    assert out["mode"] == "sim"
    assert out["mcp_url"] == "http://127.0.0.1:10002/sse"


def test_resolve_sim_vmcp_uses_harness_mcp_url(tmp_path):
    """resolve() must return harness mcp_url for sim vMCPs (port is None for those)."""
    store = MagicMock()
    harness_mcp_url = "http://127.0.0.1:8700/sse"
    store.get_vmcp.return_value = {
        "uuid": "sim-vmcp",
        "port": None,
        "extra": {
            "simulation": True,
            "harness": {"mcp_url": harness_mcp_url},
        },
    }
    orch, reg = _orch(tmp_path, store)
    reg.upsert("skill-1", real_vmcp_uuid="real-vmcp", sim_vmcp_uuid="sim-vmcp")
    reg.set_active("skill-1", "sim")

    out = orch.resolve("skill-1")
    assert out["mode"] == "sim"
    assert out["mcp_url"] == harness_mcp_url


def test_resolve_unknown_skill_raises(tmp_path):
    orch, _ = _orch(tmp_path, MagicMock())
    with pytest.raises(KeyError):
        orch.resolve("nope")


def test_toggle_delegates_to_registry(tmp_path):
    store = MagicMock()
    orch, reg = _orch(tmp_path, store)
    reg.upsert("skill-1", real_vmcp_uuid="real-vmcp", sim_vmcp_uuid="sim-vmcp")
    assert orch.toggle("skill-1")["active"] == "sim"


def test_teardown_deletes_sim_artifacts_and_stops_harness(tmp_path):
    store = MagicMock()
    harness_mgr = MagicMock()
    store.get_vmcp.return_value = {
        "uuid": "sim-vmcp", "skill_uuid": "sim-skill",
        "extra": {"sim_skill_uuid": "sim-skill", "harness": {"container_id": "c1"}},
    }
    store.get_skill.return_value = {"uuid": "sim-skill", "tool_uuids": ["sim-t1"]}
    orch, reg = _orch(tmp_path, store, harness_mgr=harness_mgr)
    reg.upsert("skill-1", real_vmcp_uuid="real-vmcp", sim_vmcp_uuid="sim-vmcp")

    out = orch.teardown("skill-1")

    store.delete_vmcp.assert_called_once_with("sim-vmcp")
    store.delete_tool.assert_called_once_with("sim-t1")
    store.delete_skill.assert_called_once_with("sim-skill")
    harness_mgr.stop.assert_called_once_with("c1")
    assert reg.get("skill-1") is None
    assert out["success"] is True


def test_check_drift_detects_changed_tools(tmp_path):
    store = MagicMock()
    store.get_vmcp.return_value = {"uuid": "sim-vmcp", "extra": {"tools_fingerprint": "OLD"}}
    store.get_skill.return_value = {"uuid": "skill-1", "tool_uuids": ["t1"]}
    store.get_tool.return_value = {"name": "get_weather", "params": {"type": "object"}}
    orch, reg = _orch(tmp_path, store)
    reg.upsert("skill-1", real_vmcp_uuid="real-vmcp", sim_vmcp_uuid="sim-vmcp")
    out = orch.check_drift("skill-1")
    assert out["drifted"] is True
