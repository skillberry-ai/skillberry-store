"""Build simulated tool manifests that target the harness instead of real backends."""
from typing import Any, Dict

SIMULATION_TAG = "simulation"


def build_simulated_tool_manifest(real_tool: Dict[str, Any], harness_mcp_url: str) -> Dict[str, Any]:
    """Return a manifest dict for an MCP-packaged tool that proxies to the harness.

    The returned dict carries NO uuid (the store assigns one) and NO description
    (so it is excluded from the semantic index). The tool name is preserved so it
    matches the harness operationId and the real vMCP tool name.
    """
    name = real_tool["name"]
    tags = list(real_tool.get("tags", []))
    if SIMULATION_TAG not in tags:
        tags.append(SIMULATION_TAG)
    return {
        "name": name,
        "programming_language": real_tool.get("programming_language", "python"),
        "packaging_format": "mcp",
        "packaging_params": {"mcp_url": harness_mcp_url, "mcp_tool_name": name},
        "params": real_tool.get("params", {"type": "object", "properties": {}}),
        "tags": tags,
        "extra": {"simulation": True, "simulation_of_tool": real_tool.get("uuid")},
    }
