"""Unit tests for SkillberryPluginMcpImporter — structural checks (no live MCP server)."""

import uuid
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from skillberry_plugin_mcp_importer.plugin import SkillberryPluginMcpImporter


# ── URL helpers ──────────────────────────────────────────────────────────────

def test_hostname_from_url_standard():
    assert SkillberryPluginMcpImporter._hostname_from_url("http://localhost:3001/sse") == "localhost"


def test_hostname_from_url_no_port():
    assert SkillberryPluginMcpImporter._hostname_from_url("http://localhost/sse") == "localhost"


def test_hostname_from_url_domain():
    assert SkillberryPluginMcpImporter._hostname_from_url("https://api.acme.com/mcp/sse") == "api.acme.com"


def test_hostname_from_url_malformed():
    assert SkillberryPluginMcpImporter._hostname_from_url("not-a-url") == "mcp"


def test_skill_name_derived_from_url():
    """_skill_name_from_url produces a clean name from various URL formats."""
    P = SkillberryPluginMcpImporter
    assert P._skill_name_from_url("http://localhost:3001/sse") == "localhost_3001_sse"
    assert P._skill_name_from_url("http://my-server.example.com/sse") == "my_server_example_com_sse"
    assert P._skill_name_from_url("http://127.0.0.1:9500/") == "127_0_0_1_9500"


# ── Manifest ─────────────────────────────────────────────────────────────────

def test_plugin_manifest_slug():
    plugin = SkillberryPluginMcpImporter()
    assert plugin.manifest.slug == "mcp-importer"


def test_plugin_manifest_type_importer():
    plugin = SkillberryPluginMcpImporter()
    assert plugin.manifest.plugin_type == "importer"


def test_plugin_manifest_version():
    plugin = SkillberryPluginMcpImporter()
    assert plugin.manifest.version == "0.1.0"


def test_plugin_manifest_has_api():
    plugin = SkillberryPluginMcpImporter()
    assert plugin.manifest.has_api is True


def test_plugin_provides_router():
    plugin = SkillberryPluginMcpImporter()
    router = plugin.get_router()
    assert router is not None
    route_paths = [route.path for route in router.routes]
    assert any("import-tools" in path for path in route_paths)


# ── Test helpers ──────────────────────────────────────────────────────────────

class _MockTool:
    """Minimal stand-in for mcp.types.Tool so vars() returns the right keys."""

    def __init__(self, name, description="", properties=None, required=None):
        self.name = name
        self.description = description
        self.inputSchema = {
            "type": "object",
            "properties": properties
            or {"message": {"type": "string", "description": "A message"}},
            "required": required or ["message"],
        }


def _make_client(tools=None, create_tool_side_effect=None, create_skill_return=None):
    """Build a TestClient with the plugin mounted and its store writes mocked."""
    plugin = SkillberryPluginMcpImporter()

    async def _default_create_tool(data, module_content, module_filename):
        return {"uuid": str(uuid.uuid4()), "name": data["name"]}

    if create_tool_side_effect is not None:
        plugin._create_tool = AsyncMock(side_effect=create_tool_side_effect)
    else:
        plugin._create_tool = AsyncMock(side_effect=_default_create_tool)

    plugin._create_skill = AsyncMock(
        return_value=create_skill_return or {"uuid": "s-uuid", "name": "auto-skill"}
    )

    app = FastAPI()
    app.include_router(plugin.get_router(), prefix="/plugins/mcp-importer")
    return TestClient(app), plugin


def _patch_mcp(tools):
    """Return a context manager that patches sse_client + ClientSession."""
    mock_tools_result = MagicMock()
    mock_tools_result.tools = tools

    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock(return_value=None)
    mock_session.list_tools = AsyncMock(return_value=mock_tools_result)

    mock_cs_cm = MagicMock()
    mock_cs_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cs_cm.__aexit__ = AsyncMock(return_value=False)
    mock_client_session = MagicMock(return_value=mock_cs_cm)

    mock_sse_cm = MagicMock()
    mock_sse_cm.__aenter__ = AsyncMock(return_value=("read", "write"))
    mock_sse_cm.__aexit__ = AsyncMock(return_value=False)
    mock_sse_client = MagicMock(return_value=mock_sse_cm)

    stack = ExitStack()
    stack.enter_context(
        patch("skillberry_plugin_mcp_importer.plugin.sse_client", mock_sse_client)
    )
    stack.enter_context(
        patch("skillberry_plugin_mcp_importer.plugin.ClientSession", mock_client_session)
    )
    return stack


# ── Tool tag generation ──────────────────────────────────────────────────────

def test_tool_tags_include_mcp_and_hostname():
    tools = [_MockTool("tool_a")]
    client, plugin = _make_client(tools=tools)
    with _patch_mcp(tools):
        resp = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp:9500/sse", "create_skill": False},
        )
    assert resp.status_code == 200
    data_arg = plugin._create_tool.call_args.args[0]
    assert "mcp" in data_arg["tags"]
    assert "mock-mcp" in data_arg["tags"]


def test_tool_tags_include_skill_reference_when_skill_created():
    tools = [_MockTool("tool_b")]
    client, plugin = _make_client(
        tools=tools,
        create_skill_return={"uuid": "s-uuid", "name": "mock-mcp_9500_sse"},
    )
    with _patch_mcp(tools):
        resp = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp:9500/sse", "create_skill": True},
        )
    assert resp.status_code == 200
    data_arg = plugin._create_tool.call_args.args[0]
    assert "skill:mock_mcp_9500_sse" in data_arg["tags"]


def test_tool_tags_no_skill_reference_when_skill_not_created():
    tools = [_MockTool("tool_c")]
    client, plugin = _make_client(tools=tools)
    with _patch_mcp(tools):
        resp = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp:9500/sse", "create_skill": False},
        )
    assert resp.status_code == 200
    data_arg = plugin._create_tool.call_args.args[0]
    assert not any(t.startswith("skill:") for t in data_arg["tags"])


# ── Skill tag generation ─────────────────────────────────────────────────────

def test_skill_tags_include_mcp_imported_and_hostname():
    tools = [_MockTool("tool_d")]
    client, plugin = _make_client(
        tools=tools,
        create_skill_return={"uuid": "s-uuid", "name": "mock_mcp_9500_sse"},
    )
    with _patch_mcp(tools):
        resp = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp:9500/sse", "create_skill": True},
        )
    assert resp.status_code == 200
    skill_data = plugin._create_skill.call_args.args[0]
    assert "mcp" in skill_data["tags"]
    assert "imported" in skill_data["tags"]
    assert "mock-mcp" in skill_data["tags"]


# ── User-supplied tag merging ────────────────────────────────────────────────

def test_user_tags_merged_into_tool_tags():
    tools = [_MockTool("tool_e")]
    client, plugin = _make_client(tools=tools)
    with _patch_mcp(tools):
        resp = client.post(
            "/plugins/mcp-importer/import-tools",
            json={
                "mcp_url": "http://mock-mcp:9500/sse",
                "create_skill": False,
                "tags": ["my-project", "prod"],
            },
        )
    assert resp.status_code == 200
    data_arg = plugin._create_tool.call_args.args[0]
    assert "my-project" in data_arg["tags"]
    assert "prod" in data_arg["tags"]


def test_user_tags_merged_into_skill_tags():
    tools = [_MockTool("tool_f")]
    client, plugin = _make_client(
        tools=tools,
        create_skill_return={"uuid": "s-uuid", "name": "mock_mcp_9500_sse"},
    )
    with _patch_mcp(tools):
        resp = client.post(
            "/plugins/mcp-importer/import-tools",
            json={
                "mcp_url": "http://mock-mcp:9500/sse",
                "create_skill": True,
                "tags": ["team-alpha"],
            },
        )
    assert resp.status_code == 200
    skill_data = plugin._create_skill.call_args.args[0]
    assert "team-alpha" in skill_data["tags"]


def test_user_tags_deduped():
    tools = [_MockTool("tool_g")]
    client, plugin = _make_client(tools=tools)
    with _patch_mcp(tools):
        resp = client.post(
            "/plugins/mcp-importer/import-tools",
            json={
                "mcp_url": "http://mock-mcp:9500/sse",
                "create_skill": False,
                "tags": ["mcp", "unique-tag"],  # "mcp" is already auto-generated
            },
        )
    assert resp.status_code == 200
    data_arg = plugin._create_tool.call_args.args[0]
    assert data_arg["tags"].count("mcp") == 1
    assert "unique-tag" in data_arg["tags"]


# ── Validation tests ─────────────────────────────────────────────────────────

def test_import_missing_url_returns_400():
    client, _ = _make_client()
    response = client.post("/plugins/mcp-importer/import-tools", json={"mcp_url": ""})
    assert response.status_code == 400
    assert "mcp_url" in response.json()["detail"].lower()


def test_import_invalid_url_scheme_returns_400():
    client, _ = _make_client()
    response = client.post(
        "/plugins/mcp-importer/import-tools",
        json={"mcp_url": "ftp://some-server/sse"},
    )
    assert response.status_code == 400
    assert "http" in response.json()["detail"].lower()


# ── Successful import tests ──────────────────────────────────────────────────

def test_import_creates_tools_for_each_mcp_tool():
    tools = [_MockTool("echo"), _MockTool("add_numbers")]
    client, plugin = _make_client(tools=tools)

    with _patch_mcp(tools):
        response = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp/sse", "create_skill": False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["imported"] == 2
    assert len(data["tools"]) == 2
    names = {t["name"] for t in data["tools"]}
    assert names == {"echo", "add_numbers"}

    assert plugin._create_tool.await_count == 2
    call_args_list = [c.args for c in plugin._create_tool.call_args_list]
    for args in call_args_list:
        data_arg = args[0]
        assert data_arg["packaging_format"] == "mcp"
        assert data_arg["packaging_params"]["mcp_url"] == "http://mock-mcp/sse"
        assert data_arg["packaging_params"]["mcp_tool_name"] in ("echo", "add_numbers")


def test_import_allows_duplicate_names():
    """Two calls with the same MCP server both succeed — store uses UUIDs, not names."""
    tools = [_MockTool("echo")]
    client, _ = _make_client(tools=tools)

    with _patch_mcp(tools):
        r1 = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp/sse", "create_skill": False},
        )
    with _patch_mcp(tools):
        r2 = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp/sse", "create_skill": False},
        )

    assert r1.status_code == 200
    assert r2.status_code == 200
    uuid1 = r1.json()["tools"][0]["uuid"]
    uuid2 = r2.json()["tools"][0]["uuid"]
    assert uuid1 != uuid2   # each import produces a fresh UUID


def test_import_creates_skill_by_default():
    """When create_skill=True (default), a skill is created from the imported tools."""
    tools = [_MockTool("echo"), _MockTool("add_numbers")]
    imported_uuids = []

    async def _create_tool(data, module_content, module_filename):
        uid = str(uuid.uuid4())
        imported_uuids.append(uid)
        return {"uuid": uid, "name": data["name"]}

    client, plugin = _make_client(
        tools=tools,
        create_tool_side_effect=_create_tool,
        create_skill_return={"uuid": "skill-uuid-123", "name": "localhost_9500_sse"},
    )

    with _patch_mcp(tools):
        response = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://localhost:9500/sse"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["imported"] == 2
    assert data["skill"] is not None
    assert data["skill"]["uuid"] == "skill-uuid-123"
    assert data["skill"]["name"] == "localhost_9500_sse"
    plugin._create_skill.assert_awaited_once()
    call_data = plugin._create_skill.call_args[0][0]
    assert set(call_data["tool_uuids"]) == set(imported_uuids)


def test_import_no_skill_when_create_skill_false():
    """When create_skill=False, no skill is created and skill is None in response."""
    tools = [_MockTool("echo")]
    client, plugin = _make_client(tools=tools)

    with _patch_mcp(tools):
        response = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp/sse", "create_skill": False},
        )

    assert response.status_code == 200
    assert response.json()["skill"] is None
    plugin._create_skill.assert_not_awaited()


def test_import_custom_skill_name():
    """skill_name parameter overrides the auto-derived name."""
    tools = [_MockTool("echo")]
    client, plugin = _make_client(
        tools=tools,
        create_skill_return={"uuid": "s1", "name": "my_custom_skill"},
    )

    with _patch_mcp(tools):
        response = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock/sse", "skill_name": "my_custom_skill"},
        )

    assert response.status_code == 200
    call_data = plugin._create_skill.call_args[0][0]
    assert call_data["name"] == "my_custom_skill"


# ── Failure tests ────────────────────────────────────────────────────────────

def test_import_404_returns_502_with_sse_hint():
    """When the server returns 404, error message should mention the SSE endpoint path."""
    import httpx
    client, _ = _make_client()
    mock_sse_cm = MagicMock()
    # Simulate ExceptionGroup wrapping a 404 HTTPStatusError (Python 3.11+ anyio behaviour)
    status_error = httpx.HTTPStatusError(
        "Client error '404 Not Found' for url 'http://host:3001/'",
        request=MagicMock(),
        response=MagicMock(status_code=404),
    )
    exc_group = Exception("unhandled errors in a TaskGroup (1 sub-exception)")
    exc_group.exceptions = [status_error]  # type: ignore[attr-defined]
    mock_sse_cm.__aenter__ = AsyncMock(side_effect=exc_group)
    mock_sse_cm.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "skillberry_plugin_mcp_importer.plugin.sse_client",
        MagicMock(return_value=mock_sse_cm),
    ):
        response = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://host:3001/"},
        )

    assert response.status_code == 502
    detail = response.json()["detail"]
    assert "404" in detail
    assert "/sse" in detail or "SSE" in detail.upper()


def test_import_sse_connection_failure_returns_502():
    client, _ = _make_client()
    mock_sse_cm = MagicMock()
    mock_sse_cm.__aenter__ = AsyncMock(
        side_effect=ConnectionError("Connection refused")
    )
    mock_sse_cm.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "skillberry_plugin_mcp_importer.plugin.sse_client",
        MagicMock(return_value=mock_sse_cm),
    ):
        response = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://unreachable/sse"},
        )

    assert response.status_code == 502
    assert "mcp server" in response.json()["detail"].lower()
