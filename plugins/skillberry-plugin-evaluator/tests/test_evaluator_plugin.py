"""Tests for the Evaluator Plugin."""

import pytest
from skillberry_plugin_evaluator.plugin import SkillberryPluginEvaluator
from skillberry_store.plugins.base import PluginType


def test_plugin_metadata():
    """Test that plugin provides correct metadata."""
    plugin = SkillberryPluginEvaluator()
    metadata = plugin.metadata

    assert metadata.name == "Content Evaluator"
    assert metadata.plugin_type == PluginType.EVALUATOR
    assert metadata.version == "0.1.0"
    assert "evaluate" in metadata.description.lower() or "tag" in metadata.description.lower()


def test_plugin_disabled_when_llm_unavailable():
    """Test that plugin is disabled when LLM cannot be initialized."""
    from unittest.mock import patch, MagicMock
    mock_module = MagicMock()
    mock_module.get_llm.side_effect = RuntimeError("LLM unavailable")
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginEvaluator()
        assert not plugin.is_enabled()


def test_plugin_enabled_when_llm_available():
    """Test that plugin is enabled when LLM initializes successfully."""
    from unittest.mock import patch, MagicMock
    mock_client = MagicMock()
    mock_llm_class = MagicMock(return_value=mock_client)
    mock_module = MagicMock()
    mock_module.get_llm.return_value = mock_llm_class
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginEvaluator()
        assert plugin.is_enabled()


def test_plugin_provides_router():
    """Test that plugin provides a FastAPI router."""
    plugin = SkillberryPluginEvaluator()
    router = plugin.get_router()

    assert router is not None
    # Router should have routes for evaluation
    route_paths = [route.path for route in router.routes]
    assert any("evaluate" in path for path in route_paths)


def test_plugin_provides_no_cli_commands():
    """Test that plugin has no CLI commands."""
    plugin = SkillberryPluginEvaluator()
    assert plugin.get_cli_commands() is None


def test_plugin_provides_ui_config():
    """Test that plugin provides UI configuration."""
    plugin = SkillberryPluginEvaluator()
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
