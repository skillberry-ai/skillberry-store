"""The plugin in a full in-process store, against the fake rossoctl backend."""

import io
import json
import zipfile

from skillberry_plugin_rossoctl_tools import proxy, skill as skill_mod

from rossoctl_fake_backend import SEARCH_SCHEMA, WEATHER_SCHEMA

SKILL = {
    "name": "night-out-planner",
    "description": "Plan and book a restaurant evening.",
    "instructions": "# Night-out planner\n\nUse the tools.",
    "tags": ["rossoctl-approved"],
}
READ_ONLY = {
    "weather-tool": ["get_weather"],
    "reservation-tool": ["search_restaurants"],
}


def _import(client, tools=("weather-tool", "reservation-tool"), skill=SKILL):
    body = {
        "namespace": "team1",
        "tools": [{"name": t, "read_only": READ_ONLY.get(t, [])} for t in tools],
    }
    if skill:
        body["skill"] = skill
    r = client.post("/plugins/rossoctl-tools/import", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _export(client, name="night-out-planner"):
    r = client.get(f"/skills/{name}/export-anthropic")
    assert r.status_code == 200, r.text
    return zipfile.ZipFile(io.BytesIO(r.content))


def test_import_creates_code_tools_and_skill(store_client, fake):
    out = _import(store_client)
    assert out["errors"] == []
    assert [t["name"] for t in out["tools"]] == [
        "get_weather",
        "search_restaurants",
        "place_reservation",
    ]
    weather = store_client.get("/tools/get_weather", params={"fields": "full"}).json()
    assert (
        weather["packaging_format"] == "code"
        and weather["module_name"] == "get_weather.py"
    )
    assert weather["params"]["required"] == ["city"]
    assert (
        skill_mod.PROXY_TAG in weather["tags"]
        and "rossoctl-tool:weather-tool" in weather["tags"]
    )
    assert weather["extra"]["rossoctl"] == {
        "tool": "weather-tool",
        "namespace": "team1",
        "port": 8000,
        "path": "/mcp",
        "mcp_tool_name": "get_weather",
        "read_only": True,
        "input_schema_sha256": proxy.canonical_schema_sha256(WEATHER_SCHEMA),
        "generator_version": proxy.GENERATOR_VERSION,
    }
    assert weather["dependencies"] in ([], None)
    sk = store_client.get("/skills/night-out-planner", params={"fields": "wide"}).json()
    assert sk["extra"]["rossoctl"]["required_tools"] == [
        "reservation-tool",
        "weather-tool",
    ]
    assert len(sk["tool_uuids"]) == 3 and len(sk["snippet_uuids"]) == 2
    assert {r["host"] for r in fake.requests} == {
        "rossoctl-backend.test",
        "keycloak.test",
    }


def test_import_errors(store_client):
    r = store_client.post(
        "/plugins/rossoctl-tools/import",
        json={"namespace": "team1", "tools": [{"name": "missing-tool"}]},
    )
    assert r.status_code == 404
    r = store_client.post(
        "/plugins/rossoctl-tools/import",
        json={"namespace": "team1", "tools": [{"name": "unreachable-tool"}]},
    )
    assert r.status_code == 502
    r = store_client.post(
        "/plugins/rossoctl-tools/import",
        json={"namespace": "Team_1", "tools": [{"name": "x"}]},
    )
    assert r.status_code == 400


def test_name_collision_prefixes_only_across_tools(store_client):
    _import(store_client, tools=("reservation-tool",), skill=None)
    out = _import(store_client, tools=("other-search", "reservation-tool"), skill=None)
    names = [t["name"] for t in out["tools"]]
    assert names[0] == "other_search__search_restaurants"
    assert "search_restaurants" in names


def test_store_side_execute_goes_through_invoke(store_client, fake, served_fake):
    _import(store_client, skill=None)
    r = store_client.post(
        "/tools/search_restaurants/execute",
        json={"city": "Boston", "cuisine": "Italian"},
    )
    assert r.status_code == 200, r.text
    assert "Trattoria di Mare" in r.json()["return value"]
    invokes = [x for x in fake.http_requests if x["path"].endswith("/invoke")]
    assert (
        invokes and invokes[-1]["path"] == "/api/v1/tools/team1/reservation-tool/invoke"
    )
    assert invokes[-1]["auth"] and invokes[-1]["auth"].startswith("Bearer ")
    # A tool error is an execution error. Core maps error text containing
    # "not found" to 404 for every code tool (tools_service.execute); unchanged (P-2).
    r = store_client.post("/tools/get_weather/execute", json={"city": "Atlantis"})
    assert (
        r.status_code in (404, 500) and "City Atlantis not found" in r.json()["detail"]
    )


def test_recipe(store_client, fake):
    _import(store_client)
    r = store_client.post(
        "/plugins/rossoctl-tools/recipe",
        json={"skill": "night-out-planner", "namespace": "team1"},
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["ok"] and out["request"]["skills"] == ["night-out-planner"]
    env = {e["name"]: e["value"] for e in out["request"]["envVars"]}
    assert env["MCP_URLS"].split(",") == [
        "http://reservation-tool-mcp.team1.svc.cluster.local:8000/mcp",
        "http://weather-tool-mcp.team1.svc.cluster.local:8000/mcp",
    ]
    fake.tools.pop("team1/reservation-tool")
    out = store_client.post(
        "/plugins/rossoctl-tools/recipe",
        json={"skill": "night-out-planner", "namespace": "team1"},
    ).json()
    assert out["missing"] == ["reservation-tool"] and not out["ok"]


def test_recipe_for_skill_without_rossoctl_tools_is_400(store_client):
    r = store_client.post("/skills/", params={"name": "plain", "description": "d"})
    assert r.status_code == 200, r.text
    r = store_client.post(
        "/plugins/rossoctl-tools/recipe", json={"skill": "plain", "namespace": "team1"}
    )
    assert r.status_code == 400


def test_export_package(store_client):
    _import(store_client)
    zf = _export(store_client)
    names = set(zf.namelist())
    assert {
        "night-out-planner/SKILL.md",
        "night-out-planner/rossoctl-tools.json",
        "night-out-planner/scripts/get_weather.py",
        "night-out-planner/scripts/search_restaurants.py",
    } <= names
    md = zf.read("night-out-planner/SKILL.md").decode()
    assert md.index("# Night-out planner") < md.index("## Tools")
    assert "| `get_weather` | — | city | read-only |" in md
    doc = json.loads(zf.read("night-out-planner/rossoctl-tools.json"))
    assert [t["tool"] for t in doc["tools"]] == ["reservation-tool", "weather-tool"]
    script = zf.read("night-out-planner/scripts/search_restaurants.py").decode()
    assert proxy.extract_spec(script)[
        "input_schema_sha256"
    ] == proxy.canonical_schema_sha256(SEARCH_SCHEMA)


def test_reimport_of_export_gives_working_code_tools(store_client):
    _import(store_client)
    zf = _export(store_client)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as out:
        for n in zf.namelist():
            data = zf.read(n)
            if n.endswith("SKILL.md"):
                data = data.replace(b"name: night-out-planner", b"name: night-out-copy")
            out.writestr(n.replace("night-out-planner/", "night-out-copy/"), data)
    r = store_client.post(
        "/skills/import-anthropic",
        data={"source_type": "zip"},
        files={"zip_file": ("c.zip", buf.getvalue(), "application/zip")},
    )
    assert r.status_code == 200, r.text
    copy = store_client.get("/skills/night-out-copy", params={"fields": "full"}).json()
    # Same names as the originals: the store keeps them as new versions.
    assert sorted(t["name"] for t in copy["tools"]) == [
        "get_weather",
        "place_reservation",
        "search_restaurants",
    ]
    weather = next(t for t in copy["tools"] if t["name"] == "get_weather")
    assert weather["params"]["required"] == ["city"]
    assert any(
        "rossoctl-tools.json" in tag
        for s in copy["snippets"]
        for tag in s.get("tags", [])
    )


def test_check_and_refresh(store_client, fake):
    _import(store_client)
    r = store_client.post(
        "/plugins/rossoctl-tools/check",
        json={"skill": "night-out-planner", "namespaces": ["team1"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert not any(t["drift"] for t in body["tools"])
    assert {c["tool"]: c["present"] for c in body["namespaces"]["team1"]} == {
        "reservation-tool": True,
        "weather-tool": True,
    }
    fake.tools["team1/weather-tool"]["mcp"][0]["input_schema"] = {
        **WEATHER_SCHEMA,
        "properties": {**WEATHER_SCHEMA["properties"], "units": {"type": "string"}},
    }
    body = store_client.post(
        "/plugins/rossoctl-tools/check", json={"skill": "night-out-planner"}
    ).json()
    assert {t["name"]: t["drift"] for t in body["tools"]}["get_weather"] is True
    r = store_client.post(
        "/plugins/rossoctl-tools/refresh", json={"skill": "night-out-planner"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["required_tools"] == ["reservation-tool", "weather-tool"]
    md = _export(store_client).read("night-out-planner/SKILL.md").decode()
    assert md.count(skill_mod.BEGIN) == 1


def test_plugin_disabled(store_client):
    _import(store_client)
    store_client.loader.set_enabled("rossoctl-tools", False)
    try:
        assert (
            store_client.post(
                "/plugins/rossoctl-tools/recipe",
                json={"skill": "night-out-planner", "namespace": "team1"},
            ).status_code
            == 404
        )
        zf = _export(store_client)
        assert "night-out-planner/scripts/get_weather.py" in zf.namelist()
        assert "night-out-planner/rossoctl-tools.json" in zf.namelist()
    finally:
        store_client.loader.set_enabled("rossoctl-tools", True)
