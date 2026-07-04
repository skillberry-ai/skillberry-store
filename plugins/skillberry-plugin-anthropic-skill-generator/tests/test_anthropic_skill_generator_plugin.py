"""Tests for the Anthropic Skill Generator plugin (SDK-based)."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from skillberry_plugin_anthropic_skill_generator.plugin import (
    SkillberryPluginAnthropicSkillGenerator,
)


# ── fixtures ──────────────────────────────────────────────────────────────────


def _make_plugin() -> SkillberryPluginAnthropicSkillGenerator:
    """Fresh plugin with an AsyncMock StoreClient wired in (no on_start)."""
    plugin = SkillberryPluginAnthropicSkillGenerator()
    store = AsyncMock()
    plugin._store = store
    return plugin


@pytest.fixture
def plugin():
    return _make_plugin()


# ── manifest ──────────────────────────────────────────────────────────────────


def test_plugin_manifest_slug():
    plugin = _make_plugin()
    assert plugin.manifest.slug == "anthropic-skill-generator"


def test_plugin_manifest_type_creator():
    plugin = _make_plugin()
    assert plugin.manifest.plugin_type == "creator"


def test_plugin_manifest_version():
    plugin = _make_plugin()
    assert plugin.manifest.version == "0.1.0"


def test_plugin_manifest_has_api():
    plugin = _make_plugin()
    assert plugin.manifest.has_api is True


# ── lifecycle / on_start ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_on_start_without_runspace_marks_unavailable():
    plugin = _make_plugin()
    with patch("skillberry_plugin_anthropic_skill_generator.plugin.runspace_agent", None):
        await plugin.on_start()
    assert plugin._runspace_available is False
    assert plugin.is_enabled() is False
    assert "not installed" in plugin.get_status_message()


@pytest.mark.asyncio
async def test_on_start_with_runspace_available(monkeypatch):
    plugin = _make_plugin()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    with patch(
        "skillberry_plugin_anthropic_skill_generator.plugin.runspace_agent",
        MagicMock(),
    ):
        await plugin.on_start()
    assert plugin._runspace_available is True
    assert plugin._credentials_configured is True


@pytest.mark.asyncio
async def test_is_ready_reflects_client_state():
    plugin = _make_plugin()
    plugin._runspace_available = True
    plugin._credentials_configured = True
    ready = await plugin.is_ready()
    assert ready["ready"] is True
    assert ready["missing_config"] == []


@pytest.mark.asyncio
async def test_is_ready_reports_missing():
    plugin = _make_plugin()
    plugin._runspace_available = False
    plugin._credentials_configured = False
    ready = await plugin.is_ready()
    assert ready["ready"] is False
    assert "runspace-agent" in ready["missing_config"]
    assert "anthropic-credentials" in ready["missing_config"]


# ── router ────────────────────────────────────────────────────────────────────


def test_get_router_has_generate_endpoint(plugin):
    router = plugin.get_router()
    assert router is not None
    routes = [route.path for route in router.routes]
    assert "/generate-skill" in routes


# ── generate_skill ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_skill_without_runspace_raises(plugin):
    plugin._runspace_available = False
    with pytest.raises(RuntimeError, match="runspace-agent not available"):
        await plugin.generate_skill("Test skill description")


@pytest.mark.asyncio
async def test_generate_skill_without_store_raises():
    plugin = SkillberryPluginAnthropicSkillGenerator()
    plugin._runspace_available = True
    plugin._credentials_configured = True
    with pytest.raises(RuntimeError, match="Store API not available"):
        await plugin.generate_skill("Test skill description")


@pytest.mark.asyncio
async def test_generate_skill_success(plugin):
    plugin._runspace_available = True
    plugin._credentials_configured = True

    # Mock the create_skill (runspace) result
    mock_result = MagicMock()
    mock_result.session_id = "test-session-id"
    mock_create_skill = AsyncMock(return_value=mock_result)

    # Mock a tool and snippet returned by the importer
    mock_tool = Mock()
    mock_tool.name = "test_tool"
    mock_tool.description = "Test tool"
    mock_tool.programming_language = "python"
    mock_tool.params = {}
    mock_tool.returns = {}
    mock_tool.module_content = "def test(): pass"
    mock_tool.source_file_name = "test_tool.py"
    mock_tool.tags = None

    mock_snippet = Mock()
    mock_snippet.name = "test_snippet"
    mock_snippet.content = "Test content"
    mock_snippet.description = "Test snippet"
    mock_snippet.tags = None

    mock_import = Mock(
        return_value=(
            "test_skill",
            "Test skill description",
            [mock_tool],
            [mock_snippet],
            [],
        )
    )

    # Patch the plugin's async create helpers to return dicts with uuids.
    plugin._create_tool = AsyncMock(return_value={"uuid": "tool-uuid-123", "name": "test_tool"})
    plugin._create_snippet = AsyncMock(
        return_value={"uuid": "snippet-uuid-456", "name": "test_snippet"}
    )
    plugin._create_skill = AsyncMock(
        return_value={
            "uuid": "skill-uuid-789",
            "name": "test_skill",
            "description": "Test skill description",
        }
    )

    # Stub ClaudeCodeOptions so we don't require the sdk import to succeed.
    fake_claude_code_sdk = MagicMock()
    fake_claude_code_sdk.ClaudeCodeOptions = MagicMock()

    with patch.dict("sys.modules", {"claude_code_sdk": fake_claude_code_sdk}):
        with patch(
            "skillberry_plugin_anthropic_skill_generator.plugin.create_skill",
            mock_create_skill,
        ):
            with patch(
                "skillberry_plugin_anthropic_skill_generator.plugin.import_from_anthropic_skill",
                mock_import,
            ):
                result = await plugin.generate_skill(
                    description="Create a test skill",
                    skill_name="test_skill",
                    tags=["test"],
                    execution_mode="local",
                )

    assert result["success"] is True
    assert result["skill"]["uuid"] == "skill-uuid-789"
    assert result["tools_count"] == 1
    assert result["snippets_count"] == 1
    plugin._create_tool.assert_awaited_once()
    plugin._create_snippet.assert_awaited_once()
    plugin._create_skill.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_skill_with_generation_error(plugin):
    plugin._runspace_available = True
    plugin._credentials_configured = True

    mock_create_skill = AsyncMock(side_effect=Exception("Generation failed"))

    fake_claude_code_sdk = MagicMock()
    fake_claude_code_sdk.ClaudeCodeOptions = MagicMock()

    with patch.dict("sys.modules", {"claude_code_sdk": fake_claude_code_sdk}):
        with patch(
            "skillberry_plugin_anthropic_skill_generator.plugin.create_skill",
            mock_create_skill,
        ):
            with pytest.raises(RuntimeError, match="Skill generation failed"):
                await plugin.generate_skill("Test skill description", execution_mode="local")


@pytest.mark.asyncio
async def test_generate_skill_with_import_error(plugin):
    plugin._runspace_available = True
    plugin._credentials_configured = True

    mock_result = MagicMock()
    mock_result.session_id = "test-session-id"
    mock_create_skill = AsyncMock(return_value=mock_result)
    mock_import = Mock(side_effect=Exception("Import failed"))

    fake_claude_code_sdk = MagicMock()
    fake_claude_code_sdk.ClaudeCodeOptions = MagicMock()

    with patch.dict("sys.modules", {"claude_code_sdk": fake_claude_code_sdk}):
        with patch(
            "skillberry_plugin_anthropic_skill_generator.plugin.create_skill",
            mock_create_skill,
        ):
            with patch(
                "skillberry_plugin_anthropic_skill_generator.plugin.import_from_anthropic_skill",
                mock_import,
            ):
                with pytest.raises(RuntimeError, match="Skill import failed"):
                    await plugin.generate_skill(
                        "Test skill description", execution_mode="local"
                    )
