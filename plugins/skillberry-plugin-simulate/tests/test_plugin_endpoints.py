import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from skillberry_plugin_simulate.plugin import SkillberryPluginSimulate


def _make_app(orchestrator):
    plugin = SkillberryPluginSimulate()
    plugin.set_store_api(MagicMock())
    plugin._orchestrator = orchestrator
    app = FastAPI()
    app.include_router(plugin.get_router(), prefix="/plugins/simulate")
    return app


def _app_with_plugin(orchestrator):
    return TestClient(_make_app(orchestrator))


def test_simulate_endpoint_returns_pending_job():
    orch = MagicMock()
    orch.simulate = AsyncMock(return_value={"success": True, "sim_vmcp_uuid": "sim-1"})
    client = _app_with_plugin(orch)
    resp = client.post("/plugins/simulate/simulate", json={"skill_uuid": "skill-1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["message"] == "Simulation is starting..."
    assert body["data"]["status"] == "pending"
    assert "job_id" in body["data"]


def test_simulate_endpoint_passes_optional_vmcp_uuid():
    orch = MagicMock()
    orch.simulate = AsyncMock(return_value={"success": True, "sim_vmcp_uuid": "sim-1"})
    client = _app_with_plugin(orch)
    resp = client.post(
        "/plugins/simulate/simulate",
        json={"skill_uuid": "skill-1", "vmcp_uuid": "real-vmcp"},
    )
    assert resp.status_code == 200


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


# --- async job pattern tests ---


@pytest.mark.asyncio
async def test_simulate_returns_pending_job_immediately():
    blocked = asyncio.Event()

    async def hanging_simulate(*a, **kw):
        await blocked.wait()
        return {"success": True}

    orch = MagicMock()
    orch.simulate = hanging_simulate
    app = _make_app(orch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await asyncio.wait_for(
            client.post("/plugins/simulate/simulate", json={"skill_uuid": "skill-1"}),
            timeout=2.0,
        )
        blocked.set()

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["status"] == "pending"
    assert "job_id" in body["data"]


@pytest.mark.asyncio
async def test_simulate_status_404_for_unknown_job():
    app = _make_app(MagicMock())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/plugins/simulate/status/no-such-job")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_simulate_status_returns_ready_with_result():
    sim_result = {"success": True, "sim_vmcp_uuid": "sim-1", "harness_mcp_url": "http://h/sse"}
    orch = MagicMock()
    orch.simulate = AsyncMock(return_value=sim_result)
    app = _make_app(orch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        post_resp = await client.post("/plugins/simulate/simulate", json={"skill_uuid": "skill-1"})
        assert post_resp.status_code == 200
        job_id = post_resp.json()["data"]["job_id"]

        await asyncio.sleep(0)

        status_resp = await client.get(f"/plugins/simulate/status/{job_id}")

    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["status"] == "ready"
    assert body["sim_vmcp_uuid"] == "sim-1"


@pytest.mark.asyncio
async def test_simulate_status_returns_failed_on_orchestrator_error():
    orch = MagicMock()
    orch.simulate = AsyncMock(side_effect=RuntimeError("harness boom"))
    app = _make_app(orch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        post_resp = await client.post("/plugins/simulate/simulate", json={"skill_uuid": "skill-1"})
        job_id = post_resp.json()["data"]["job_id"]

        await asyncio.sleep(0)

        status_resp = await client.get(f"/plugins/simulate/status/{job_id}")

    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["status"] == "failed"
    assert "boom" in body["detail"]
