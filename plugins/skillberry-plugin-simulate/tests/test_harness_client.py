import httpx
import pytest

from skillberry_plugin_simulate.harness_client import HarnessClient


def _client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport, base_url="http://harness:8086")


@pytest.mark.asyncio
async def test_create_simulation_posts_spec():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["json"] = httpx.Response(200)  # marker
        return httpx.Response(200, json={"status": "starting"})

    hc = HarnessClient(_client(handler))
    await hc.create_simulation({"openapi": "3.0.3"}, mcp_port=8701)
    assert seen["url"].endswith("/api/v1/simulation")


@pytest.mark.asyncio
async def test_wait_until_ready_returns_mcp_url():
    states = iter([
        httpx.Response(200, json={"status": "starting"}),
        httpx.Response(200, json={"status": "ready", "mcp_url": "http://harness:8701/sse"}),
    ])

    def handler(request):
        return next(states)

    hc = HarnessClient(_client(handler))
    mcp_url = await hc.wait_until_ready(timeout=5, interval=0)
    assert mcp_url == "http://harness:8701/sse"


@pytest.mark.asyncio
async def test_410_triggers_resubmit():
    calls = {"post": 0}

    def handler(request):
        if request.method == "POST":
            calls["post"] += 1
            return httpx.Response(200, json={"status": "starting"})
        if calls["post"] == 1:
            return httpx.Response(410, json={"error": "SessionExpiredError"})
        return httpx.Response(200, json={"status": "ready", "mcp_url": "http://h/sse"})

    hc = HarnessClient(_client(handler))
    await hc.create_simulation({"openapi": "3.0.3"}, mcp_port=8701)
    mcp_url = await hc.wait_until_ready(timeout=5, interval=0)
    assert calls["post"] == 2  # auto-resubmitted after 410
    assert mcp_url == "http://h/sse"


@pytest.mark.asyncio
async def test_delete_simulation():
    def handler(request):
        assert request.method == "DELETE"
        return httpx.Response(200, json={"status": "deleted"})

    hc = HarnessClient(_client(handler))
    await hc.delete_simulation()
