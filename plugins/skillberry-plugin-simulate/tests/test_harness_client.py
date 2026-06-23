import httpx
import pytest

from skillberry_plugin_simulate.harness_client import HarnessClient, HarnessError


def _client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport, base_url="http://harness:8086")


@pytest.mark.asyncio
async def test_create_simulation_posts_spec():
    seen = {}

    def handler(request):
        import json
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "starting"})

    hc = HarnessClient(_client(handler))
    spec = {"openapi": "3.0.3"}
    await hc.create_simulation(spec, mcp_port=8701)
    assert seen["url"].endswith("/api/v1/simulation")
    # harness expects "openapi_spec", not "openapi"
    assert seen["body"]["openapi_spec"] == spec
    assert seen["body"]["mcp_port"] == 8701


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
async def test_create_simulation_retries_on_connect_error():
    """Connection and read errors during harness startup are retried, not raised immediately."""
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("not yet")
        if calls["n"] == 2:
            raise httpx.ReadError("connection dropped")
        return httpx.Response(202, json={"status": "pending"})

    hc = HarnessClient(_client(handler))
    # Should succeed on the 3rd attempt without raising
    await hc.create_simulation({"openapi": "3.0.3"}, mcp_port=8701, startup_delay=0)
    assert calls["n"] == 3


@pytest.mark.asyncio
async def test_create_simulation_retries_on_remote_protocol_error():
    """Docker publishes the port before uvicorn binds; the proxy accepts then
    drops the connection, surfacing as RemoteProtocolError. This is startup lag
    and must be retried, not raised."""
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.RemoteProtocolError(
                "Server disconnected without sending a response."
            )
        return httpx.Response(202, json={"status": "pending"})

    hc = HarnessClient(_client(handler))
    await hc.create_simulation({"openapi": "3.0.3"}, mcp_port=8701, startup_delay=0)
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_create_simulation_raises_after_all_retries():
    def handler(request):
        raise httpx.ConnectError("still not ready")

    hc = HarnessClient(_client(handler))
    with pytest.raises(HarnessError, match="not reachable after"):
        await hc.create_simulation({"openapi": "3.0.3"}, mcp_port=8701, startup_retries=2, startup_delay=0)


@pytest.mark.asyncio
async def test_wait_until_ready_fails_fast_on_failed_status():
    def handler(request):
        return httpx.Response(200, json={"status": "failed", "error": "LLM timeout"})

    hc = HarnessClient(_client(handler))
    with pytest.raises(HarnessError, match="LLM timeout"):
        await hc.wait_until_ready(timeout=10, interval=0)


@pytest.mark.asyncio
async def test_delete_simulation():
    def handler(request):
        assert request.method == "DELETE"
        return httpx.Response(200, json={"status": "deleted"})

    hc = HarnessClient(_client(handler))
    await hc.delete_simulation()
