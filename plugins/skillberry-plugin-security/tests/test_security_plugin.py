"""Tests for the Security Plugin."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from skillberry_plugin_security.plugin import SkillberryPluginSecurity
from skillberry_store.plugins.base import PluginType


def test_plugin_metadata():
    plugin = SkillberryPluginSecurity()
    metadata = plugin.metadata
    assert metadata.name == "Security Evaluator"
    assert metadata.plugin_type == PluginType.EVALUATOR
    assert metadata.version == "0.1.0"
    assert "security" in metadata.description.lower()


# ── helper: _strip_score_tags ────────────────────────────────────────────────

def test_strip_score_tags_removes_only_security():
    plugin = SkillberryPluginSecurity()
    tags = ["python", "security-score:4", "quality-score:8", "performance-score:7", "utility"]
    result = plugin._strip_score_tags(tags)
    assert result == ["python", "quality-score:8", "performance-score:7", "utility"]


def test_strip_score_tags_no_security_tag_unchanged():
    plugin = SkillberryPluginSecurity()
    tags = ["python", "utility"]
    assert plugin._strip_score_tags(tags) == ["python", "utility"]


def test_strip_score_tags_empty_list():
    plugin = SkillberryPluginSecurity()
    assert plugin._strip_score_tags([]) == []


# ── helper: _build_context ───────────────────────────────────────────────────

def test_build_context_excludes_previous_security_from_extra():
    plugin = SkillberryPluginSecurity()
    obj = {
        "name": "my_tool",
        "description": "does something",
        "extra": {
            "custom_key": "keep_me",
            "evaluation": {"security": {"score": 4, "evaluation": "old finding"}},
        },
        "tags": [],
    }
    context = plugin._build_context(obj, "tool")
    assert "keep_me" in context
    assert "old finding" not in context
    assert "evaluation" not in context


def test_build_context_tool_includes_key_fields():
    plugin = SkillberryPluginSecurity()
    obj = {
        "uuid": "tool-1",
        "name": "my_tool",
        "description": "does something useful",
        "programming_language": "python",
        "packaging_format": "code",
        "params": {"type": "object", "properties": {}},
        "tags": ["utility"],
        "extra": {},
    }
    context = plugin._build_context(obj, "tool")
    assert "my_tool" in context
    assert "does something useful" in context
    assert "python" in context


def test_build_context_skill_includes_uuids():
    plugin = SkillberryPluginSecurity()
    obj = {
        "name": "my_skill",
        "description": "orchestrates things",
        "tool_uuids": ["uuid-a", "uuid-b"],
        "snippet_uuids": ["uuid-c"],
        "tags": [],
        "extra": {},
    }
    context = plugin._build_context(obj, "skill")
    assert "my_skill" in context
    assert "uuid-a" in context
    assert "uuid-c" in context


def test_build_context_snippet_includes_content():
    plugin = SkillberryPluginSecurity()
    obj = {
        "name": "my_snippet",
        "description": "a greeting",
        "content": "Hello World",
        "content_type": "text/plain",
        "tags": [],
        "extra": {},
    }
    context = plugin._build_context(obj, "snippet")
    assert "Hello World" in context
    assert "my_snippet" in context


# ── helper: _write_security_to_store ────────────────────────────────────────

@pytest.mark.asyncio
async def test_write_security_adds_tag_and_metadata_to_tool():
    plugin = SkillberryPluginSecurity()
    mock_store = MagicMock()
    mock_store.tools = MagicMock()
    plugin.set_store_api(mock_store)

    obj = {"uuid": "tool-1", "name": "t", "description": "", "tags": ["keeper"], "extra": {}}
    evaluation = {"security_score": 6, "security_evaluation": "Found SQL injection risk."}

    await plugin._write_security_to_store("tool-1", "tool", obj, evaluation)

    written = mock_store.tools.write_dict.call_args[0][1]
    assert "security-score:6" in written["tags"]
    assert "keeper" in written["tags"]
    assert written["extra"]["evaluation"]["security"]["score"] == 6
    assert written["extra"]["evaluation"]["security"]["evaluation"] == "Found SQL injection risk."


@pytest.mark.asyncio
async def test_write_security_preserves_quality_and_performance_metadata():
    plugin = SkillberryPluginSecurity()
    mock_store = MagicMock()
    mock_store.tools = MagicMock()
    plugin.set_store_api(mock_store)

    obj = {
        "uuid": "tool-1", "name": "t", "description": "",
        "tags": ["quality-score:8", "performance-score:7"],
        "extra": {
            "evaluation": {
                "quality": {"score": 8, "evaluation": "Great quality."},
                "performance": {"score": 7, "evaluation": "Good perf."},
            }
        },
    }
    evaluation = {"security_score": 5, "security_evaluation": "Weak input validation."}

    await plugin._write_security_to_store("tool-1", "tool", obj, evaluation)

    written = mock_store.tools.write_dict.call_args[0][1]
    assert "quality-score:8" in written["tags"]
    assert "performance-score:7" in written["tags"]
    assert "security-score:5" in written["tags"]
    eval_meta = written["extra"]["evaluation"]
    assert "quality" in eval_meta
    assert "performance" in eval_meta
    assert "security" in eval_meta


@pytest.mark.asyncio
async def test_write_security_replaces_old_security_tag_on_snippet():
    plugin = SkillberryPluginSecurity()
    mock_store = MagicMock()
    mock_store.snippets = MagicMock()
    plugin.set_store_api(mock_store)

    obj = {
        "uuid": "snip-1", "name": "s", "description": "",
        "tags": ["keeper", "security-score:2"],
        "extra": {},
    }
    evaluation = {"security_score": 9, "security_evaluation": "Minor issue only."}

    await plugin._write_security_to_store("snip-1", "snippet", obj, evaluation)

    written = mock_store.snippets.write_dict.call_args[0][1]
    tags = written["tags"]
    assert "security-score:9" in tags
    assert "security-score:2" not in tags
    assert "keeper" in tags


@pytest.mark.asyncio
async def test_write_security_uses_skills_writer_for_skill():
    plugin = SkillberryPluginSecurity()
    mock_store = MagicMock()
    mock_store.skills = MagicMock()
    plugin.set_store_api(mock_store)

    obj = {"uuid": "skill-1", "name": "s", "description": "", "tags": [], "extra": {}}
    evaluation = {"security_score": 10, "security_evaluation": "No security issues identified."}

    await plugin._write_security_to_store("skill-1", "skill", obj, evaluation)

    assert mock_store.skills.write_dict.called
    assert not mock_store.tools.write_dict.called if hasattr(mock_store, 'tools') else True


# ── evaluate_security ────────────────────────────────────────────────────────

def _make_plugin_with_mock_llm():
    """Create a plugin instance with a mocked LLM client."""
    mock_client = MagicMock()
    mock_llm_class = MagicMock(return_value=mock_client)
    mock_module = MagicMock()
    mock_module.get_llm.return_value = mock_llm_class
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginSecurity()
    return plugin


def _llm_json(score=7):
    return json.dumps({
        "security_score": score,
        "security_evaluation": f"Score: {score}/10. Found a minor path traversal risk.",
    })


@pytest.mark.asyncio
async def test_evaluate_security_tool_returns_both_fields():
    plugin = _make_plugin_with_mock_llm()
    mock_store = MagicMock()
    mock_store.get_tool.return_value = {
        "uuid": "tool-1", "name": "test_tool", "description": "A test tool",
        "programming_language": "python", "packaging_format": "code",
        "params": {}, "tags": [], "extra": {},
    }
    mock_store.tools = MagicMock()
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json(score=7))

    result = await plugin.evaluate_security("tool-1", "tool")

    assert result["security_score"] == 7
    assert "path traversal" in result["security_evaluation"]


@pytest.mark.asyncio
async def test_evaluate_security_writes_tag_and_metadata():
    plugin = _make_plugin_with_mock_llm()
    mock_store = MagicMock()
    mock_store.get_tool.return_value = {
        "uuid": "tool-1", "name": "t", "description": "",
        "tags": ["existing-tag"], "extra": {},
    }
    mock_store.tools = MagicMock()
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(return_value=_llm_json(score=5))

    await plugin.evaluate_security("tool-1", "tool")

    written = mock_store.tools.write_dict.call_args[0][1]
    assert "security-score:5" in written["tags"]
    assert "existing-tag" in written["tags"]
    assert written["extra"]["evaluation"]["security"]["score"] == 5


@pytest.mark.asyncio
async def test_evaluate_security_raises_value_error_when_uuid_not_found():
    plugin = _make_plugin_with_mock_llm()
    mock_store = MagicMock()
    mock_store.get_tool.return_value = None
    plugin.set_store_api(mock_store)

    with pytest.raises(ValueError, match="not found"):
        await plugin.evaluate_security("nonexistent", "tool")


@pytest.mark.asyncio
async def test_evaluate_security_raises_runtime_error_on_bad_llm_response():
    plugin = _make_plugin_with_mock_llm()
    mock_store = MagicMock()
    mock_store.get_tool.return_value = {
        "uuid": "t1", "name": "t", "description": "", "tags": [], "extra": {},
    }
    mock_store.tools = MagicMock()
    plugin.set_store_api(mock_store)
    plugin.llm_client.generate_async = AsyncMock(return_value="not json at all")

    with pytest.raises(RuntimeError, match="Failed to parse"):
        await plugin.evaluate_security("t1", "tool")


@pytest.mark.asyncio
async def test_evaluate_security_raises_value_error_on_unknown_content_type():
    plugin = _make_plugin_with_mock_llm()
    mock_store = MagicMock()
    plugin.set_store_api(mock_store)

    with pytest.raises(ValueError, match="Unknown content_type"):
        await plugin.evaluate_security("uuid-1", "banana")


# ── router + UI config ───────────────────────────────────────────────────────

def test_plugin_disabled_when_llm_unavailable():
    mock_module = MagicMock()
    mock_module.get_llm.side_effect = RuntimeError("LLM unavailable")
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginSecurity()
        assert not plugin.is_enabled()


def test_plugin_enabled_when_llm_available():
    mock_client = MagicMock()
    mock_llm_class = MagicMock(return_value=mock_client)
    mock_module = MagicMock()
    mock_module.get_llm.return_value = mock_llm_class
    with patch.dict("sys.modules", {"llm_switchboard": mock_module}):
        plugin = SkillberryPluginSecurity()
        assert plugin.is_enabled()


def test_plugin_provides_router():
    plugin = SkillberryPluginSecurity()
    router = plugin.get_router()
    assert router is not None
    route_paths = [route.path for route in router.routes]
    assert any("evaluate" in path for path in route_paths)


def test_plugin_provides_no_cli_commands():
    plugin = SkillberryPluginSecurity()
    assert plugin.get_cli_commands() is None


def test_plugin_provides_ui_config():
    plugin = SkillberryPluginSecurity()
    ui_config = plugin.get_ui_config()
    assert ui_config is not None
    assert "icon" in ui_config
    assert "color" in ui_config
    assert "actions" in ui_config
    assert len(ui_config["actions"]) > 0
    action_labels = [action["label"] for action in ui_config["actions"]]
    assert any("security" in label.lower() for label in action_labels)
