"""Tests for the Creator Plugin."""

import pytest
from skillberry_plugin_creator.plugin import AICreatorPlugin
from skillberry_store.plugins.base import PluginType


def test_plugin_metadata():
    """Test that plugin provides correct metadata."""
    plugin = AICreatorPlugin()
    metadata = plugin.metadata
    
    assert metadata.name == "AI Content Creator"
    assert metadata.plugin_type == PluginType.CREATOR
    assert metadata.version == "0.1.0"
    assert "AI" in metadata.description or "generate" in metadata.description.lower()


def test_plugin_disabled_without_api_key(monkeypatch):
    """Test that plugin is disabled when OpenAI API key is not configured."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    
    plugin = AICreatorPlugin()
    assert not plugin.is_enabled()


def test_plugin_enabled_with_api_key(monkeypatch):
    """Test that plugin is enabled when OpenAI API key is configured."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    
    plugin = AICreatorPlugin()
    assert plugin.is_enabled()


def test_plugin_provides_router():
    """Test that plugin provides a FastAPI router."""
    plugin = AICreatorPlugin()
    router = plugin.get_router()
    
    assert router is not None
    # Router should have routes for creating content
    route_paths = [route.path for route in router.routes]
    assert any("create" in path for path in route_paths)


def test_plugin_provides_cli_commands():
    """Test that plugin provides CLI commands."""
    plugin = AICreatorPlugin()
    commands = plugin.get_cli_commands()
    
    assert commands is not None
    assert isinstance(commands, dict)
    # Should have commands for creating different content types
    assert len(commands) > 0


def test_plugin_provides_ui_config():
    """Test that plugin provides UI configuration."""
    plugin = AICreatorPlugin()
    ui_config = plugin.get_ui_config()
    
    assert ui_config is not None
    assert "icon" in ui_config
    assert "color" in ui_config
    assert "actions" in ui_config
    assert len(ui_config["actions"]) > 0

# Made with Bob
