import httpx
import pytest

from skillberry_plugin_simulate.harness_client import (
    HarnessClient,
    HarnessError,
    HarnessTimeout,
)


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
async def test_create_simulation_sends_name_when_given():
    """The name keys the harness's generated-skill cache directory."""
    seen = {}

    def handler(request):
        import json
        seen["body"] = json.loads(request.content)
        return httpx.Response(202, json={"status": "pending"})

    hc = HarnessClient(_client(handler))
    await hc.create_simulation({"openapi": "3.0.3"}, mcp_port=8701, name="weather-1a2b3c4d")
    assert seen["body"]["name"] == "weather-1a2b3c4d"


@pytest.mark.asyncio
async def test_create_simulation_omits_name_when_not_given():
    seen = {}

    def handler(request):
        import json
        seen["body"] = json.loads(request.content)
        return httpx.Response(202, json={"status": "pending"})

    hc = HarnessClient(_client(handler))
    await hc.create_simulation({"openapi": "3.0.3"}, mcp_port=8701)
    assert "name" not in seen["body"]


@pytest.mark.asyncio
async def test_transitional_statuses_are_not_terminal():
    """pending / generating_skill / initializing all mean "keep polling"."""
    states = iter([
        httpx.Response(200, json={"status": "pending"}),
        httpx.Response(200, json={"status": "generating_skill",
                                  "progress": {"phase": "analyze"}}),
        httpx.Response(200, json={"status": "initializing"}),
        httpx.Response(200, json={"status": "ready",
                                  "mcp_url": "http://127.0.0.1:8701/mcp/sse"}),
    ])

    hc = HarnessClient(_client(lambda request: next(states)))
    assert await hc.wait_until_ready(timeout=5, interval=0) == "http://127.0.0.1:8701/mcp/sse"


@pytest.mark.asyncio
async def test_create_simulation_409_names_both_causes():
    def handler(request):
        return httpx.Response(409, json={"detail": "Port 8701 is already in use"})

    hc = HarnessClient(_client(handler))
    with pytest.raises(HarnessError, match="409"):
        await hc.create_simulation({"openapi": "3.0.3"}, mcp_port=8701)


@pytest.mark.asyncio
async def test_create_simulation_422_blames_the_spec():
    def handler(request):
        return httpx.Response(422, json={"detail": "OpenAPI validation failed"})

    hc = HarnessClient(_client(handler))
    with pytest.raises(HarnessError, match="synthesized OpenAPI spec"):
        await hc.create_simulation({"openapi": "3.0.3"}, mcp_port=8701)


@pytest.mark.asyncio
async def test_get_status_404_says_no_active_simulation():
    def handler(request):
        return httpx.Response(404, json={"detail": "No simulation is active"})

    hc = HarnessClient(_client(handler))
    with pytest.raises(HarnessError, match="no active simulation"):
        await hc.get_status()


@pytest.mark.asyncio
async def test_failed_status_renders_structured_error_payload():
    """As of v0.1.x the harness reports `error` as an object, not a string."""
    def handler(request):
        return httpx.Response(200, json={
            "status": "failed",
            "error": {"code": "sidecar_start_failed",
                      "message": "Port 8701 is already in use",
                      "details": None},
        })

    hc = HarnessClient(_client(handler))
    with pytest.raises(HarnessError, match="Port 8701 is already in use"):
        await hc.wait_until_ready(timeout=10, interval=0)


@pytest.mark.asyncio
async def test_timeout_reports_last_status_and_phase():
    def handler(request):
        return httpx.Response(200, json={"status": "generating_skill",
                                         "progress": {"phase": "operations"}})

    hc = HarnessClient(_client(handler))
    with pytest.raises(HarnessTimeout, match="operations"):
        await hc.wait_until_ready(timeout=0, interval=0)


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
