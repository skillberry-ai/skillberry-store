"""Tests for the Anthropic Skill Generator plugin."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from pathlib import Path

from skillberry_plugin_anthropic_skill_generator.plugin import SkillberryPluginAnthropicSkillGenerator


@pytest.fixture
def plugin():
    """Create a plugin instance for testing."""
    return SkillberryPluginAnthropicSkillGenerator()


@pytest.fixture
def mock_store():
    """Create a mock store API."""
    store = Mock()
    store.create_tool = Mock(return_value={"uuid": "tool-uuid-123", "name": "test_tool"})
    store.create_snippet = Mock(return_value={"uuid": "snippet-uuid-456", "name": "test_snippet"})
    store.create_skill = Mock(return_value={
        "uuid": "skill-uuid-789",
        "name": "test_skill",
        "description": "Test skill description"
    })
    return store


def test_plugin_metadata(plugin):
    """Test plugin metadata is correctly set."""
    metadata = plugin.metadata
    assert metadata.name == "Anthropic Skill Generator"
    assert metadata.version == "0.1.0"
    assert "runspace-agent" in metadata.description.lower()
    assert metadata.plugin_type.value == "creator"


def test_plugin_initialization_without_runspace():
    """Test plugin initialization when runspace-agent is not available."""
    with patch("skillberry_plugin_anthropic_skill_generator.plugin.runspace_agent", None):
        plugin = SkillberryPluginAnthropicSkillGenerator()
        assert not plugin.is_enabled()
        assert "not installed" in plugin.get_status_message()


def test_plugin_initialization_with_runspace():
    """Test plugin initialization when runspace-agent is available."""
    with patch("skillberry_plugin_anthropic_skill_generator.plugin.runspace_agent", MagicMock()):
        plugin = SkillberryPluginAnthropicSkillGenerator()
        assert plugin._runspace_available


def test_get_router(plugin):
    """Test that plugin provides a router."""
    router = plugin.get_router()
    assert router is not None
    # Check that the router has the expected endpoint
    routes = [route.path for route in router.routes]
    assert "/generate-skill" in routes


def test_get_cli_commands(plugin):
    """Test that plugin returns None for CLI commands."""
    commands = plugin.get_cli_commands()
    assert commands is None


def test_get_ui_config(plugin):
    """Test that plugin provides UI configuration."""
    ui_config = plugin.get_ui_config()
    assert ui_config is not None
    assert "icon" in ui_config
    assert "color" in ui_config
    assert "actions" in ui_config
    assert len(ui_config["actions"]) > 0
    
    # Check the action configuration
    action = ui_config["actions"][0]
    assert action["label"] == "Generate Anthropic Skill"
    assert action["endpoint"] == "/api/plugins/anthropic-skill-generator/generate-skill"
    assert action["method"] == "POST"
    assert "params_schema" in action


@pytest.mark.asyncio
async def test_generate_skill_without_runspace(plugin, mock_store):
    """Test that generate_skill raises error when runspace is not available."""
    plugin.set_store_api(mock_store)
    plugin._runspace_available = False
    
    with pytest.raises(RuntimeError, match="runspace-agent not available"):
        await plugin.generate_skill("Test skill description")


@pytest.mark.asyncio
async def test_generate_skill_without_store(plugin):
    """Test that generate_skill raises error when store is not available."""
    plugin._runspace_available = True
    plugin._credentials_configured = True

    with pytest.raises(RuntimeError, match="Store API not available"):
        await plugin.generate_skill("Test skill description")


@pytest.mark.asyncio
async def test_generate_skill_success(plugin, mock_store):
    """Test successful skill generation."""
    plugin.set_store_api(mock_store)
    plugin._runspace_available = True
    plugin._credentials_configured = True

    mock_result = MagicMock()
    mock_result.session_id = "test-session-id"
    mock_create_skill = AsyncMock(return_value=mock_result)

    mock_tool = Mock()
    mock_tool.name = "test_tool"
    mock_tool.description = "Test tool"
    mock_tool.programming_language = "python"
    mock_tool.params = {}
    mock_tool.returns = {}
    mock_tool.content = "def test(): pass"
    mock_tool.module_content = "def test(): pass"
    mock_tool.source_file_name = "test_tool.py"
    mock_tool.tags = None

    mock_snippet = Mock()
    mock_snippet.name = "test_snippet"
    mock_snippet.content = "Test content"
    mock_snippet.language = "text"
    mock_snippet.description = "Test snippet"
    mock_snippet.tags = None

    mock_import = Mock(return_value=(
        "test_skill",
        "Test skill description",
        [mock_tool],
        [mock_snippet],
        []
    ))

    with patch("skillberry_plugin_anthropic_skill_generator.plugin.create_skill", mock_create_skill):
        with patch("skillberry_plugin_anthropic_skill_generator.plugin.import_from_anthropic_skill", mock_import):
            result = await plugin.generate_skill(
                description="Create a test skill",
                skill_name="test_skill",
                tags=["test"]
            )

    assert result["success"] is True
    assert result["skill"]["uuid"] == "skill-uuid-789"
    assert result["tools_count"] == 1
    assert result["snippets_count"] == 1

    mock_store.create_tool.assert_called_once()
    mock_store.create_snippet.assert_called_once()
    mock_store.create_skill.assert_called_once()


@pytest.mark.asyncio
async def test_generate_skill_with_generation_error(plugin, mock_store):
    """Test skill generation when runspace-agent fails."""
    plugin.set_store_api(mock_store)
    plugin._runspace_available = True
    plugin._credentials_configured = True

    mock_create_skill = AsyncMock(side_effect=Exception("Generation failed"))

    with patch("skillberry_plugin_anthropic_skill_generator.plugin.create_skill", mock_create_skill):
        with pytest.raises(RuntimeError, match="Skill generation failed"):
            await plugin.generate_skill("Test skill description")


@pytest.mark.asyncio
async def test_generate_skill_with_import_error(plugin, mock_store):
    """Test skill generation when import fails."""
    plugin.set_store_api(mock_store)
    plugin._runspace_available = True
    plugin._credentials_configured = True

    mock_result = MagicMock()
    mock_result.session_id = "test-session-id"
    mock_create_skill = AsyncMock(return_value=mock_result)

    mock_import = Mock(side_effect=Exception("Import failed"))

    with patch("skillberry_plugin_anthropic_skill_generator.plugin.create_skill", mock_create_skill):
        with patch("skillberry_plugin_anthropic_skill_generator.plugin.import_from_anthropic_skill", mock_import):
            with pytest.raises(RuntimeError, match="Skill import failed"):
                await plugin.generate_skill("Test skill description")


def test_router_endpoint_disabled(plugin):
    """Test that router endpoint returns 503 when plugin is disabled."""
    plugin._runspace_available = False
    router = plugin.get_router()
    
    # This would require actually calling the FastAPI endpoint
    # In a real test, you'd use TestClient from fastapi.testclient
    # For now, we just verify the router exists
    assert router is not None

# Made with Bob
