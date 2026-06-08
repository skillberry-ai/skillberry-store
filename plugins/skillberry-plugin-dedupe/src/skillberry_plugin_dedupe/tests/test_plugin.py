"""Tests for SkillberryPluginDedupe."""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from skillberry_store.plugins.base import PluginType


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_plugin_with_mock_llm():
    """Return a plugin instance with a mocked LLM client."""
    mock_client = MagicMock()
    mock_llm_class = MagicMock(return_value=mock_client)
    mock_module = MagicMock()
    mock_module.get_llm.return_value = mock_llm_class
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        from skillberry_plugin_dedupe.plugin import SkillberryPluginDedupe
        plugin = SkillberryPluginDedupe()
    return plugin


def _make_plugin_disabled():
    """Return a plugin instance where LLM is unavailable."""
    mock_module = MagicMock()
    mock_module.get_llm.side_effect = RuntimeError("LLM unavailable")
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        from skillberry_plugin_dedupe.plugin import SkillberryPluginDedupe
        plugin = SkillberryPluginDedupe()
    return plugin


def _make_mock_store(skills=None):
    mock_store = MagicMock()
    mock_store.list_skills.return_value = skills or []
    mock_store.get_skill.return_value = None
    mock_store.update_skill_tags.return_value = True
    mock_store.update_skill_metadata.return_value = True
    return mock_store


# ── metadata ─────────────────────────────────────────────────────────────────

def test_plugin_metadata_name_and_type():
    from skillberry_plugin_dedupe.plugin import SkillberryPluginDedupe
    plugin = SkillberryPluginDedupe()
    assert plugin.metadata.name == "Skill Deduplicator"
    assert plugin.metadata.plugin_type == PluginType.EVALUATOR
    assert plugin.metadata.version == "0.1.0"


def test_plugin_disabled_when_llm_unavailable():
    plugin = _make_plugin_disabled()
    assert not plugin.is_enabled()
    assert "llm" in plugin.get_status_message().lower() or "unavailable" in plugin.get_status_message().lower()


def test_plugin_enabled_when_llm_available():
    plugin = _make_plugin_with_mock_llm()
    assert plugin.is_enabled()


def test_plugin_no_router():
    plugin = _make_plugin_with_mock_llm()
    assert plugin.get_router() is None


def test_plugin_no_cli_commands():
    plugin = _make_plugin_with_mock_llm()
    assert plugin.get_cli_commands() is None


def test_plugin_no_ui_config():
    plugin = _make_plugin_with_mock_llm()
    assert plugin.get_ui_config() is None


# ── event handler registration ────────────────────────────────────────────────

def test_event_handlers_registered_for_skill_added_and_updated():
    from skillberry_store.plugins import events as events_module
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        plugin = _make_plugin_with_mock_llm()
        assert len(events_module._event_handlers.get("content_added:skill", [])) > 0
        assert len(events_module._event_handlers.get("content_updated:skill", [])) > 0
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


def test_event_handlers_not_registered_for_tools_or_snippets():
    from skillberry_store.plugins import events as events_module
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        _make_plugin_with_mock_llm()
        assert "content_added:tool" not in events_module._event_handlers
        assert "content_added:snippet" not in events_module._event_handlers
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


@pytest.mark.asyncio
async def test_event_handler_skipped_when_plugin_disabled():
    from skillberry_store.plugins import events as events_module
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        plugin = _make_plugin_disabled()
        plugin.set_store_api(_make_mock_store())
        handler = events_module._event_handlers.get("content_added:skill", [None])[0]
        if handler:
            await handler(uuid="any-uuid")  # must not raise
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)


@pytest.mark.asyncio
async def test_event_handler_skipped_when_store_not_set():
    from skillberry_store.plugins import events as events_module
    saved = dict(events_module._event_handlers)
    events_module._event_handlers.clear()
    try:
        _make_plugin_with_mock_llm()
        handler = events_module._event_handlers["content_added:skill"][0]
        await handler(uuid="any-uuid")  # must not raise — store not injected
    finally:
        events_module._event_handlers.clear()
        events_module._event_handlers.update(saved)
