"""E2E: the recipe's MCP wiring works with the client generic_agent uses,
and the exported proxies work as scripts against the same tools.

Two FastMCP streamable-HTTP servers stand in for the rossoctl tool pods. The
recipe's ``MCP_URLS`` are rewritten from cluster DNS to these local servers
(the only thing a cluster provides), then handed to ``MultiServerMCPClient``,
configured exactly as ``generic_agent`` configures it (``graph.py``:
``{"url", "transport", "timeout"}`` per URL).
"""

import asyncio
import io
import json
import socket
import subprocess
import sys
import threading
import time
import zipfile

import pytest

pytestmark = pytest.mark.integration


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve(mcp, port):
    import uvicorn

    server = uvicorn.Server(
        uvicorn.Config(
            mcp.streamable_http_app(), host="127.0.0.1", port=port, log_level="warning"
        )
    )
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    deadline = time.time() + 15
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started
    return server, t


@pytest.fixture(scope="module")
def tool_pods():
    from mcp.server.fastmcp import FastMCP

    weather = FastMCP("weather", host="127.0.0.1")

    @weather.tool()
    def get_weather(city: str) -> str:
        return json.dumps({"temperature": 52, "weathercode": 53, "city": city})

    reservations = FastMCP("reservations", host="127.0.0.1")

    @reservations.tool()
    def search_restaurants(city: str, cuisine: str = "", party_size: int = 2) -> str:
        return json.dumps(
            [{"id": "rest_001", "name": "Trattoria di Mare", "city": city}]
        )

    @reservations.tool()
    def place_reservation(
        restaurant_id: str,
        date_time: str,
        party_size: int,
        name: str,
        phone: str,
        email: str,
    ) -> str:
        return json.dumps(
            {"confirmation_code": "RES001000", "restaurant_id": restaurant_id}
        )

    ports = {"weather-tool": _free_port(), "reservation-tool": _free_port()}
    servers = [
        _serve(weather, ports["weather-tool"]),
        _serve(reservations, ports["reservation-tool"]),
    ]
    yield ports
    for server, t in servers:
        server.should_exit = True
        t.join(timeout=5)


def _local(url, ports):
    # http://<tool>-mcp.<ns>.svc.cluster.local:<port>/mcp -> the local stand-in
    tool = url.split("//", 1)[1].split("-mcp.", 1)[0]
    return f"http://127.0.0.1:{ports[tool]}/mcp"


@pytest.fixture
def recipe_and_package(store_client):
    body = {
        "namespace": "team1",
        "tools": [
            {"name": "weather-tool", "read_only": ["get_weather"]},
            {"name": "reservation-tool"},
        ],
        "skill": {
            "name": "night-out-planner",
            "description": "Plan an evening.",
            "instructions": "# Night-out planner\n",
        },
    }
    assert (
        store_client.post("/plugins/rossoctl-tools/import", json=body).status_code
        == 200
    )
    r = store_client.post(
        "/plugins/rossoctl-tools/recipe",
        json={"skill": "night-out-planner", "namespace": "team1"},
    )
    assert r.status_code == 200, r.text
    z = store_client.get("/skills/night-out-planner/export-anthropic")
    assert z.status_code == 200
    return r.json(), zipfile.ZipFile(io.BytesIO(z.content))


def test_generic_agent_mcp_client_sees_and_calls_the_tools(
    recipe_and_package, tool_pods
):
    adapters = pytest.importorskip(
        "langchain_mcp_adapters.client", reason="generic_agent's MCP client (dev extra)"
    )
    MultiServerMCPClient = adapters.MultiServerMCPClient

    recipe, _ = recipe_and_package
    env = {e["name"]: e["value"] for e in recipe["request"]["envVars"]}
    urls = [_local(u, tool_pods) for u in env["MCP_URLS"].split(",")]
    client = MultiServerMCPClient(
        {
            f"mcp{i}": {"url": u, "transport": env["MCP_TRANSPORT"], "timeout": 60}
            for i, u in enumerate(urls, 1)
        }
    )

    async def go():
        tools = {t.name: t for t in await client.get_tools()}
        assert {"get_weather", "search_restaurants", "place_reservation"} <= set(tools)
        found = await tools["search_restaurants"].ainvoke(
            {"city": "Boston", "cuisine": "Italian"}
        )
        weather = await tools["get_weather"].ainvoke({"city": "Boston"})
        return json.dumps(found, default=str), json.dumps(weather, default=str)

    found, weather = asyncio.run(go())
    assert "Trattoria di Mare" in found and "52" in weather


def test_exported_proxies_run_as_scripts(recipe_and_package, tool_pods, tmp_path):
    _, zf = recipe_and_package
    zf.extractall(tmp_path)
    root = tmp_path / "night-out-planner"
    env = {
        "PATH": "/usr/bin:/bin",
        "ROSSOCTL_TOOL_RESERVATION_TOOL_URL": f"http://127.0.0.1:{tool_pods['reservation-tool']}/mcp",
        "ROSSOCTL_TOOL_WEATHER_TOOL_URL": f"http://127.0.0.1:{tool_pods['weather-tool']}/mcp",
    }

    def run(script, *args, extra=None):
        return subprocess.run(
            [sys.executable, "-I", str(root / "scripts" / script), *args],
            capture_output=True,
            text=True,
            timeout=60,
            env={**env, **(extra or {})},
        )

    r = run("search_restaurants.py", "--city", "Boston", "--cuisine", "Italian")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)[0]["name"] == "Trattoria di Mare"
    r = run(
        "place_reservation.py",
        "--restaurant_id",
        "rest_001",
        "--date_time",
        "2026-10-28T19:30:00",
        "--party_size",
        "4",
        "--name",
        "Ada",
        "--phone",
        "555",
        "--email",
        "ada@example.com",
    )
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["confirmation_code"] == "RES001000"
    r = run(
        "get_weather.py",
        "--city",
        "Boston",
        extra={
            "ROSSOCTL_TOOL_WEATHER_TOOL_URL": f"http://127.0.0.1:{_free_port()}/mcp"
        },
    )
    assert r.returncode == 3
