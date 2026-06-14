"""Tests for the Skill Optimizer plugin."""

import json
import os
import pytest
from unittest.mock import Mock, patch, AsyncMock

from skillberry_plugin_skill_optimizer.prompt import (
    REQUIRED_OUTPUTS_FILENAME,
    REQUIRED_OUTPUTS_TEMPLATE,
    build_runspace_prompt,
)


# ---------------------------------------------------------------------------
# prompt.py tests
# ---------------------------------------------------------------------------

def test_required_outputs_template_has_all_fields():
    required_keys = {
        "skill_name", "skill_description", "optimization_rationale",
        "issues_addressed", "tools_added", "tools_modified", "tools_removed",
        "snippets_added", "snippets_modified", "snippets_removed",
        "ready_for_deployment",
    }
    assert required_keys == set(REQUIRED_OUTPUTS_TEMPLATE.keys())


def test_required_outputs_filename():
    assert REQUIRED_OUTPUTS_FILENAME == "required_outputs.json"


def test_build_prompt_no_context():
    prompt = build_runspace_prompt(
        has_metadata=False, has_trajectories=False, has_additional_context=False
    )
    assert "optimizing a Skillberry skill" in prompt
    assert "REQUIRED OUTPUT CONTRACT" in prompt
    assert "required_outputs.json" in prompt
    assert "SKILLBERRY STORE ANTHROPIC SKILL FORMAT" in prompt
    # No context sections should appear
    assert "skill_metadata.json" not in prompt
    assert "trajectories/" not in prompt
    assert "additional_context/" not in prompt


def test_build_prompt_with_metadata():
    prompt = build_runspace_prompt(
        has_metadata=True, has_trajectories=False, has_additional_context=False
    )
    assert "skill_metadata.json" in prompt


def test_build_prompt_with_trajectories():
    prompt = build_runspace_prompt(
        has_metadata=False, has_trajectories=True, has_additional_context=False
    )
    assert "trajectories/" in prompt
    assert "reward" in prompt  # trajectory analysis instructions
    assert "overfit" in prompt


def test_build_prompt_with_additional_context():
    prompt = build_runspace_prompt(
        has_metadata=False, has_trajectories=False, has_additional_context=True
    )
    assert "additional_context/" in prompt


def test_build_prompt_all_context():
    prompt = build_runspace_prompt(
        has_metadata=True, has_trajectories=True, has_additional_context=True
    )
    assert "skill_metadata.json" in prompt
    assert "trajectories/" in prompt
    assert "additional_context/" in prompt


def test_build_prompt_contains_required_outputs_template():
    prompt = build_runspace_prompt(
        has_metadata=False, has_trajectories=False, has_additional_context=False
    )
    # The template JSON must appear verbatim in the prompt
    for key in REQUIRED_OUTPUTS_TEMPLATE:
        assert key in prompt


from skillberry_store.plugins.base import PluginType
from skillberry_plugin_skill_optimizer.plugin import SkillberryPluginSkillOptimizer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def plugin():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("skillberry_plugin_skill_optimizer.plugin.runspace_agent", new=Mock()):
            p = SkillberryPluginSkillOptimizer()
    return p


@pytest.fixture
def mock_store():
    store = Mock()
    store.get_skill = Mock(return_value={
        "uuid": "skill-uuid-123",
        "name": "my-skill",
        "description": "A test skill",
        "tags": ["python", "test"],
        "extra": {},
        "tool_uuids": ["tool-uuid-1"],
        "snippet_uuids": [],
        "tools": [
            {
                "uuid": "tool-uuid-1",
                "name": "my_tool",
                "description": "A tool",
                "programming_language": "python",
                "module_name": "my_tool.py",
                "tags": [],
            }
        ],
        "snippets": [],
    })
    store.list_skills = Mock(return_value=[{"name": "other-skill"}])
    store.tools = Mock()
    store.tools.read_file = Mock(return_value="def my_tool():\n    pass\n")
    store.create_tool = Mock(return_value={"uuid": "new-tool-uuid", "name": "my_tool"})
    store.create_snippet = Mock(return_value={"uuid": "new-snip-uuid", "name": "my_snip"})
    store.create_skill = Mock(return_value={
        "uuid": "new-skill-uuid",
        "name": "my-skill_optimized",
        "description": "Optimized skill",
    })
    store.update_skill_metadata = Mock(return_value=True)
    return store


# ---------------------------------------------------------------------------
# Plugin init / metadata tests
# ---------------------------------------------------------------------------

def test_plugin_metadata(plugin):
    assert plugin.metadata.name == "Skill Optimizer"
    assert plugin.metadata.plugin_type == PluginType.OPTIMIZER
    assert plugin.metadata.version == "0.1.0"


def test_is_enabled_with_runspace_and_credentials(plugin):
    assert plugin.is_enabled() is True


def test_is_enabled_without_runspace():
    with patch("skillberry_plugin_skill_optimizer.plugin.runspace_agent", new=None):
        p = SkillberryPluginSkillOptimizer()
    assert p.is_enabled() is False


def test_is_enabled_without_credentials():
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN")}
    with patch.dict(os.environ, env, clear=True):
        with patch("skillberry_plugin_skill_optimizer.plugin.runspace_agent", new=Mock()):
            p = SkillberryPluginSkillOptimizer()
    assert p.is_enabled() is False


def test_status_message_ready(plugin):
    msg = plugin.get_status_message()
    assert "Ready" in msg


def test_status_message_missing_runspace():
    with patch("skillberry_plugin_skill_optimizer.plugin.runspace_agent", new=None):
        p = SkillberryPluginSkillOptimizer()
    assert "runspace-agent" in p.get_status_message()


def test_status_message_missing_credentials():
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN")}
    with patch.dict(os.environ, env, clear=True):
        with patch("skillberry_plugin_skill_optimizer.plugin.runspace_agent", new=Mock()):
            p = SkillberryPluginSkillOptimizer()
    assert "credentials" in p.get_status_message().lower()
