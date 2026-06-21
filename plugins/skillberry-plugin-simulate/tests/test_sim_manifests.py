from skillberry_plugin_simulate.sim_manifests import build_simulated_tool_manifest


def _real_tool():
    return {
        "uuid": "real-1",
        "name": "get_weather",
        "description": "Real weather tool",
        "programming_language": "python",
        "packaging_format": "code",
        "params": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        "tags": ["weather"],
    }


def test_builds_mcp_manifest_pointing_at_harness():
    m = build_simulated_tool_manifest(_real_tool(), harness_mcp_url="http://127.0.0.1:8701/sse")
    assert m["packaging_format"] == "mcp"
    assert m["packaging_params"] == {"mcp_url": "http://127.0.0.1:8701/sse", "mcp_tool_name": "get_weather"}


def test_params_copied_and_name_preserved():
    m = build_simulated_tool_manifest(_real_tool(), harness_mcp_url="http://h/sse")
    assert m["name"] == "get_weather"
    assert m["params"]["properties"]["city"]["type"] == "string"


def test_marked_as_simulation_and_not_indexed():
    m = build_simulated_tool_manifest(_real_tool(), harness_mcp_url="http://h/sse")
    assert "simulation" in m["tags"]
    assert m["extra"]["simulation"] is True
    assert m["extra"]["simulation_of_tool"] == "real-1"
    # no description => never written to the semantic vector index
    assert "description" not in m or not m["description"]


def test_no_uuid_carried_over():
    m = build_simulated_tool_manifest(_real_tool(), harness_mcp_url="http://h/sse")
    assert "uuid" not in m  # store assigns a fresh uuid on create
