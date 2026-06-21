from skillberry_plugin_simulate.openapi_synth import OpenApiSynthesizer


def _tool(name="get_weather"):
    return {
        "name": name,
        "description": "Get weather for a city",
        "params": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    }


def test_operation_id_is_tool_name_not_execute_prefixed():
    spec = OpenApiSynthesizer().synthesize([_tool()], title="skill")
    op = spec["paths"]["/get_weather"]["post"]
    assert op["operationId"] == "get_weather"
    assert not op["operationId"].startswith("execute_")


def test_openapi_version_and_structure():
    spec = OpenApiSynthesizer().synthesize([_tool()], title="skill")
    assert spec["openapi"] == "3.0.3"
    assert spec["info"]["title"] == "skill"
    op = spec["paths"]["/get_weather"]["post"]
    body_schema = op["requestBody"]["content"]["application/json"]["schema"]
    assert body_schema["properties"]["city"]["type"] == "string"
    assert "200" in op["responses"]


def test_multiple_tools_each_get_a_path():
    spec = OpenApiSynthesizer().synthesize([_tool("a"), _tool("b")], title="s")
    assert set(spec["paths"]) == {"/a", "/b"}


def test_tool_without_params_still_valid():
    spec = OpenApiSynthesizer().synthesize([{"name": "ping"}], title="s")
    op = spec["paths"]["/ping"]["post"]
    assert op["operationId"] == "ping"
    schema = op["requestBody"]["content"]["application/json"]["schema"]
    assert schema["type"] == "object"
