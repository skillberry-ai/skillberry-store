"""Unit tests for SkillberryPluginMcpImporter — structural checks (no live MCP server)."""

import pytest
from skillberry_plugin_mcp_importer.plugin import SkillberryPluginMcpImporter
from skillberry_store.plugins.base import PluginType


# --- _hostname_from_url ---

def test_hostname_from_url_standard():
    assert SkillberryPluginMcpImporter._hostname_from_url("http://localhost:3001/sse") == "localhost"

def test_hostname_from_url_no_port():
    assert SkillberryPluginMcpImporter._hostname_from_url("http://localhost/sse") == "localhost"

def test_hostname_from_url_domain():
    assert SkillberryPluginMcpImporter._hostname_from_url("https://api.acme.com/mcp/sse") == "api.acme.com"

def test_hostname_from_url_malformed():
    assert SkillberryPluginMcpImporter._hostname_from_url("not-a-url") == "mcp"


def test_plugin_metadata():
    plugin = SkillberryPluginMcpImporter()
    meta = plugin.metadata
    assert meta.name == "MCP Importer"
    assert meta.plugin_type == PluginType.IMPORTER
    assert meta.version == "0.1.0"
    assert "mcp" in meta.description.lower() or "import" in meta.description.lower()


def test_plugin_always_enabled():
    plugin = SkillberryPluginMcpImporter()
    assert plugin.is_enabled() is True


def test_plugin_status_message():
    plugin = SkillberryPluginMcpImporter()
    assert plugin.get_status_message() == "Ready"


def test_plugin_provides_router():
    plugin = SkillberryPluginMcpImporter()
    router = plugin.get_router()
    assert router is not None
    route_paths = [route.path for route in router.routes]
    assert any("import-tools" in path for path in route_paths)


def test_plugin_no_cli_commands():
    plugin = SkillberryPluginMcpImporter()
    assert plugin.get_cli_commands() is None


def test_plugin_provides_ui_config():
    plugin = SkillberryPluginMcpImporter()
    ui = plugin.get_ui_config()
    assert ui is not None
    assert "icon" in ui
    assert "color" in ui
    assert "actions" in ui
    assert len(ui["actions"]) > 0
    action = ui["actions"][0]
    assert "mcp_url" in action["params_schema"]["properties"]
    assert "mcp_url" in action["params_schema"]["required"]


# ── Helpers ──────────────────────────────────────────────────────────────────

import uuid
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


class _MockTool:
    """Minimal stand-in for mcp.types.Tool so vars() returns the right keys."""
    def __init__(self, name, description="", properties=None, required=None):
        self.name = name
        self.description = description
        self.inputSchema = {
            "type": "object",
            "properties": properties or {
                "message": {"type": "string", "description": "A message"}
            },
            "required": required or ["message"],
        }


def _make_client(tools=None, create_tool_side_effect=None):
    """Build a TestClient with the plugin mounted and its store API mocked."""
    plugin = SkillberryPluginMcpImporter()
    mock_store = MagicMock()
    if create_tool_side_effect:
        mock_store.create_tool.side_effect = create_tool_side_effect
    else:
        def _create(data, module_content, module_filename):
            return {"uuid": str(uuid.uuid4()), "name": data["name"]}
        mock_store.create_tool.side_effect = _create
    plugin.set_store_api(mock_store)

    app = FastAPI()
    app.include_router(plugin.get_router(), prefix="/plugins/mcp-importer")
    return TestClient(app), plugin, mock_store


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

    from contextlib import ExitStack
    stack = ExitStack()
    stack.enter_context(
        patch("skillberry_plugin_mcp_importer.plugin.sse_client", mock_sse_client)
    )
    stack.enter_context(
        patch("skillberry_plugin_mcp_importer.plugin.ClientSession", mock_client_session)
    )
    return stack


# --- tool tag generation ---

def test_tool_tags_include_mcp_and_hostname():
    tools = [_MockTool("tool_a")]
    client, _, mock_store = _make_client(tools=tools)
    with _patch_mcp(tools):
        resp = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp:9500/sse", "create_skill": False},
        )
    assert resp.status_code == 200
    data_arg = mock_store.create_tool.call_args.args[0]
    assert "mcp" in data_arg["tags"]
    assert "mock-mcp" in data_arg["tags"]


def test_tool_tags_include_skill_reference_when_skill_created():
    tools = [_MockTool("tool_b")]
    client, _, mock_store = _make_client(tools=tools)
    mock_store.create_skill.return_value = {"uuid": "s-uuid", "name": "mock-mcp_9500_sse"}
    with _patch_mcp(tools):
        resp = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp:9500/sse", "create_skill": True},
        )
    assert resp.status_code == 200
    data_arg = mock_store.create_tool.call_args.args[0]
    assert "skill:mock_mcp_9500_sse" in data_arg["tags"]


def test_tool_tags_no_skill_reference_when_skill_not_created():
    tools = [_MockTool("tool_c")]
    client, _, mock_store = _make_client(tools=tools)
    with _patch_mcp(tools):
        resp = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp:9500/sse", "create_skill": False},
        )
    assert resp.status_code == 200
    data_arg = mock_store.create_tool.call_args.args[0]
    assert not any(t.startswith("skill:") for t in data_arg["tags"])


# ── Validation tests ──────────────────────────────────────────────────────────

def test_import_missing_url_returns_400():
    client, _, _ = _make_client()
    response = client.post("/plugins/mcp-importer/import-tools", json={"mcp_url": ""})
    assert response.status_code == 400
    assert "mcp_url" in response.json()["detail"].lower()


def test_import_invalid_url_scheme_returns_400():
    client, _, _ = _make_client()
    response = client.post(
        "/plugins/mcp-importer/import-tools",
        json={"mcp_url": "ftp://some-server/sse"},
    )
    assert response.status_code == 400
    assert "http" in response.json()["detail"].lower()


# ── Successful import tests ───────────────────────────────────────────────────

def test_import_creates_tools_for_each_mcp_tool():
    tools = [_MockTool("echo"), _MockTool("add_numbers")]
    client, _, mock_store = _make_client(tools=tools)

    with _patch_mcp(tools):
        response = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp/sse"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["imported"] == 2
    assert len(data["tools"]) == 2
    names = {t["name"] for t in data["tools"]}
    assert names == {"echo", "add_numbers"}

    assert mock_store.create_tool.call_count == 2
    call_args_list = [c.args for c in mock_store.create_tool.call_args_list]
    for args in call_args_list:
        data_arg = args[0]
        assert data_arg["packaging_format"] == "mcp"
        assert data_arg["packaging_params"]["mcp_url"] == "http://mock-mcp/sse"
        assert data_arg["packaging_params"]["mcp_tool_name"] in ("echo", "add_numbers")


def test_import_allows_duplicate_names():
    """Two calls with the same MCP server both succeed — store uses UUIDs, not names."""
    tools = [_MockTool("echo")]
    client, _, mock_store = _make_client(tools=tools)

    with _patch_mcp(tools):
        r1 = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp/sse"},
        )
    with _patch_mcp(tools):
        r2 = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp/sse"},
        )

    assert r1.status_code == 200
    assert r2.status_code == 200
    uuid1 = r1.json()["tools"][0]["uuid"]
    uuid2 = r2.json()["tools"][0]["uuid"]
    assert uuid1 != uuid2   # each import produces a fresh UUID


# ── Failure tests ─────────────────────────────────────────────────────────────

def test_import_creates_skill_by_default():
    """When create_skill=True (default), a skill is created from the imported tools."""
    tools = [_MockTool("echo"), _MockTool("add_numbers")]
    plugin = SkillberryPluginMcpImporter()
    mock_store = MagicMock()
    imported_uuids = []

    def _create_tool(data, module_content, module_filename):
        uid = str(uuid.uuid4())
        imported_uuids.append(uid)
        return {"uuid": uid, "name": data["name"]}

    mock_store.create_tool.side_effect = _create_tool
    mock_store.create_skill.return_value = {
        "uuid": "skill-uuid-123",
        "name": "localhost_9500_sse",
    }
    plugin.set_store_api(mock_store)

    app = FastAPI()
    app.include_router(plugin.get_router(), prefix="/plugins/mcp-importer")
    client = TestClient(app)

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
    mock_store.create_skill.assert_called_once()
    call_data = mock_store.create_skill.call_args[0][0]
    assert set(call_data["tool_uuids"]) == set(imported_uuids)


def test_import_no_skill_when_create_skill_false():
    """When create_skill=False, no skill is created and skill is None in response."""
    tools = [_MockTool("echo")]
    client, _, mock_store = _make_client(tools=tools)

    with _patch_mcp(tools):
        response = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock-mcp/sse", "create_skill": False},
        )

    assert response.status_code == 200
    assert response.json()["skill"] is None
    mock_store.create_skill.assert_not_called()


def test_import_custom_skill_name():
    """skill_name parameter overrides the auto-derived name."""
    tools = [_MockTool("echo")]
    plugin = SkillberryPluginMcpImporter()
    mock_store = MagicMock()
    mock_store.create_tool.side_effect = lambda data, **kw: {"uuid": str(uuid.uuid4()), "name": data["name"]}
    mock_store.create_skill.return_value = {"uuid": "s1", "name": "my_custom_skill"}
    plugin.set_store_api(mock_store)

    app = FastAPI()
    app.include_router(plugin.get_router(), prefix="/plugins/mcp-importer")
    client = TestClient(app)

    with _patch_mcp(tools):
        response = client.post(
            "/plugins/mcp-importer/import-tools",
            json={"mcp_url": "http://mock/sse", "skill_name": "my_custom_skill"},
        )

    assert response.status_code == 200
    call_data = mock_store.create_skill.call_args[0][0]
    assert call_data["name"] == "my_custom_skill"


def test_skill_name_derived_from_url():
    """_skill_name_from_url produces a clean name from various URL formats."""
    from skillberry_plugin_mcp_importer.plugin import SkillberryPluginMcpImporter as P
    assert P._skill_name_from_url("http://localhost:3001/sse") == "localhost_3001_sse"
    assert P._skill_name_from_url("http://my-server.example.com/sse") == "my_server_example_com_sse"
    assert P._skill_name_from_url("http://127.0.0.1:9500/") == "127_0_0_1_9500"


def test_import_404_returns_502_with_sse_hint():
    """When the server returns 404, error message should mention the SSE endpoint path."""
    import httpx
    client, _, _ = _make_client()
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
    client, _, _ = _make_client()
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
