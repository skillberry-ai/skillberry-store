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
