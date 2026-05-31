"""Tests for the Evaluator Plugin."""

import pytest
from skillberry_plugin_evaluator.plugin import EvaluatorPlugin
from skillberry_store.plugins.base import PluginType


def test_plugin_metadata():
    """Test that plugin provides correct metadata."""
    plugin = EvaluatorPlugin()
    metadata = plugin.metadata
    
    assert metadata.name == "AI Content Evaluator"
    assert metadata.plugin_type == PluginType.EVALUATOR
    assert metadata.version == "0.1.0"
    assert "evaluate" in metadata.description.lower() or "tag" in metadata.description.lower()


def test_plugin_disabled_without_llm_config(monkeypatch):
    """Test that plugin is disabled when LLM is not configured."""
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    
    plugin = EvaluatorPlugin()
    assert not plugin.is_enabled()


def test_plugin_enabled_with_llm_config(monkeypatch):
    """Test that plugin is enabled when LLM is configured."""
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    
    plugin = EvaluatorPlugin()
    assert plugin.is_enabled()


def test_plugin_provides_router():
    """Test that plugin provides a FastAPI router."""
    plugin = EvaluatorPlugin()
    router = plugin.get_router()
    
    assert router is not None
    # Router should have routes for evaluation
    route_paths = [route.path for route in router.routes]
    assert any("evaluate" in path for path in route_paths)


def test_plugin_provides_cli_commands():
    """Test that plugin provides CLI commands."""
    plugin = EvaluatorPlugin()
    commands = plugin.get_cli_commands()
    
    assert commands is not None
    assert isinstance(commands, dict)
    # Should have commands for evaluation
    assert "evaluate" in commands or any("eval" in cmd for cmd in commands.keys())


def test_plugin_provides_ui_config():
    """Test that plugin provides UI configuration."""
    plugin = EvaluatorPlugin()
    ui_config = plugin.get_ui_config()
    
    assert ui_config is not None
    assert "icon" in ui_config
    assert "color" in ui_config
    assert "actions" in ui_config
    assert len(ui_config["actions"]) > 0
    # Should have evaluate action
    action_labels = [action["label"] for action in ui_config["actions"]]
    assert any("evaluate" in label.lower() for label in action_labels)

# Made with Bob
