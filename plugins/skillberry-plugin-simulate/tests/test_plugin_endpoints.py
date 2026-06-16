from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from skillberry_plugin_simulate.plugin import SkillberryPluginSimulate


def _app_with_plugin(orchestrator):
    plugin = SkillberryPluginSimulate()
    plugin.set_store_api(MagicMock())
    plugin._orchestrator = orchestrator  # inject test double
    app = FastAPI()
    app.include_router(plugin.get_router(), prefix="/plugins/simulate")
    return TestClient(app)


def test_simulate_endpoint_invokes_orchestrator():
    orch = MagicMock()
    orch.simulate = AsyncMock(return_value={"success": True, "sim_vmcp_uuid": "sim-1"})
    client = _app_with_plugin(orch)
    resp = client.post("/plugins/simulate/simulate", json={"vmcp_uuid": "real-1"})
    assert resp.status_code == 200
    assert resp.json()["sim_vmcp_uuid"] == "sim-1"
    orch.simulate.assert_awaited_once()


def test_active_endpoint_returns_mode_and_url():
    orch = MagicMock()
    orch.resolve.return_value = {"mode": "real", "mcp_url": "http://127.0.0.1:10001/sse", "vmcp_uuid": "real-1"}
    client = _app_with_plugin(orch)
    resp = client.get("/plugins/simulate/active/skill-1")
    assert resp.status_code == 200
    assert resp.json()["mode"] == "real"
    assert resp.json()["mcp_url"].endswith("/sse")


def test_active_endpoint_404_when_skill_unknown():
    orch = MagicMock()
    orch.resolve.side_effect = KeyError("skill-x")
    client = _app_with_plugin(orch)
    resp = client.get("/plugins/simulate/active/skill-x")
    assert resp.status_code == 404


def test_toggle_endpoint():
    orch = MagicMock()
    orch.toggle.return_value = {"success": True, "active": "sim"}
    client = _app_with_plugin(orch)
    resp = client.post("/plugins/simulate/toggle", json={"skill_uuid": "skill-1"})
    assert resp.status_code == 200
    assert resp.json()["active"] == "sim"


def test_teardown_endpoint():
    orch = MagicMock()
    orch.teardown.return_value = {"success": True, "skill_uuid": "skill-1"}
    client = _app_with_plugin(orch)
    resp = client.post("/plugins/simulate/teardown", json={"skill_uuid": "skill-1"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True
