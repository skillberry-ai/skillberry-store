"""The deployment recipe (design D3–D7) and the generated skill content (D12, D15)."""

import asyncio
import json

import pytest

from skillberry_plugin_rossoctl_tools import recipe, skill as skill_mod


def run(coro):
    return asyncio.run(coro)


def test_direct_recipe(backend, fake):
    fake.tools["team1/reservation-tool"]["port"] = 9090
    out = run(
        recipe.build(
            backend,
            skill_name="night-out-planner",
            required=["reservation-tool", "weather-tool"],
            namespace="team1",
        )
    )
    req = out["request"]
    assert out["ok"] and out["missing"] == []
    assert req["skills"] == ["night-out-planner"]
    assert req["containerImage"] == recipe.DEFAULT_AGENT_IMAGE
    assert (
        req["deploymentMethod"] == "image"
        and req["namespace"] == "team1"
        and req["name"] == "night-out-planner"
    )
    env = {e["name"]: e["value"] for e in req["envVars"]}
    assert env["MCP_URLS"] == (
        "http://reservation-tool-mcp.team1.svc.cluster.local:9090/mcp,"
        "http://weather-tool-mcp.team1.svc.cluster.local:8000/mcp"
    )
    assert env["MCP_TRANSPORT"] == "streamable_http"
    assert (
        "rossoctl agents import from-image" in out["cli"]
        and "night-out-planner" in out["cli"]
    )


def test_recipe_never_contains_secrets_or_model_settings(backend):
    out = run(
        recipe.build(
            backend, skill_name="s", required=["weather-tool"], namespace="team1"
        )
    )
    names = {e["name"] for e in out["request"]["envVars"]}
    assert names == {"MCP_URLS", "MCP_TRANSPORT"}
    blob = json.dumps(out["request"]).lower()
    assert "secret" not in blob and "token" not in blob and "llm_api_key" not in blob
    assert any("LLM_API_BASE" in t for t in out["todo"])


def test_missing_tool_is_reported(backend):
    out = run(
        recipe.build(
            backend,
            skill_name="s",
            required=["missing-tool", "weather-tool"],
            namespace="team1",
        )
    )
    assert out["missing"] == ["missing-tool"] and not out["ok"]
    env = {e["name"]: e["value"] for e in out["request"]["envVars"]}
    assert env["MCP_URLS"] == "http://weather-tool-mcp.team1.svc.cluster.local:8000/mcp"
    assert any("missing-tool" in t for t in out["todo"])


def test_gateway_mode(backend, monkeypatch):
    monkeypatch.setenv("ROSSOCTL_MCP_GATEWAY_URL", "http://gw.test:8080/mcp")
    out = run(
        recipe.build(
            backend,
            skill_name="s",
            required=["weather-tool"],
            namespace="team1",
            mode="gateway",
            image="my/agent:1",
        )
    )
    env = {e["name"]: e["value"] for e in out["request"]["envVars"]}
    assert env["MCP_URL"] == env["MCP_URLS"] == "http://gw.test:8080/mcp"
    assert out["request"]["containerImage"] == "my/agent:1"
    assert any("MCPServerRegistration" in t for t in out["todo"])


def test_bad_inputs(backend):
    with pytest.raises(ValueError):
        run(
            recipe.build(
                backend, skill_name="s", required=[], namespace="team1", mode="nope"
            )
        )
    with pytest.raises(ValueError):
        run(recipe.build(backend, skill_name="s", required=[], namespace="Team1"))
    with pytest.raises(ValueError):
        run(
            recipe.build(
                backend,
                skill_name="s",
                required=[],
                namespace="team1",
                agent_name="Bad_Name",
            )
        )


# --- generated skill content ----------------------------------------------------


def _tool(name, tool, mcp, read_only=False, prefix=None):
    meta = {
        "tool": tool,
        "namespace": "team1",
        "port": 8000,
        "path": "/mcp",
        "mcp_tool_name": mcp,
        "read_only": read_only,
        "input_schema_sha256": "abc",
    }
    if prefix:
        meta["gateway_prefix"] = prefix
    return {
        "name": name,
        "params": {"properties": {"city": {}, "cuisine": {}}, "required": ["city"]},
        "extra": {"rossoctl": meta},
    }


TOOLS = [
    _tool(
        "get_weather", "weather-tool", "get_weather", read_only=True, prefix="weather_"
    ),
    _tool("place_reservation", "reservation-tool", "place_reservation"),
    {"name": "plain_code_tool", "extra": {}},
]


def test_required_tools():
    assert skill_mod.required_tools(TOOLS) == ["reservation-tool", "weather-tool"]
    assert skill_mod.skill_required_tools(
        {"extra": {"rossoctl": {"required_tools": ["x-tool"]}}}, TOOLS
    ) == ["x-tool"]
    assert skill_mod.skill_required_tools({}, TOOLS) == [
        "reservation-tool",
        "weather-tool",
    ]


def test_tools_json():
    doc = json.loads(skill_mod.tools_json(TOOLS))
    assert doc["schema"] == skill_mod.TOOLS_JSON_SCHEMA
    assert [t["tool"] for t in doc["tools"]] == ["reservation-tool", "weather-tool"]
    weather = doc["tools"][1]
    assert weather["gateway_prefix"] == "weather_"
    assert weather["mcp_tools"] == [
        {
            "name": "get_weather",
            "store_tool": "get_weather",
            "script": "scripts/get_weather.py",
            "schema_sha256": "abc",
            "read_only": True,
        }
    ]


def test_tools_section_and_replacement():
    section = skill_mod.tools_section(TOOLS)
    assert (
        "`get_weather` | `weather_get_weather` | city, cuisine? | read-only" in section
    )
    assert "`place_reservation` | — | city, cuisine? | **changes state**" in section
    assert "explicit confirmation" in section
    text = skill_mod.with_tools_section("# Planner\n\nDo it.\n", section)
    assert text.startswith("# Planner") and text.count(skill_mod.BEGIN) == 1
    again = skill_mod.with_tools_section(text, skill_mod.tools_section(TOOLS[:1]))
    assert (
        again.count(skill_mod.BEGIN) == 1
        and "place_reservation" not in again
        and "Do it." in again
    )
    assert skill_mod.BEGIN not in skill_mod.with_tools_section(text, "")
