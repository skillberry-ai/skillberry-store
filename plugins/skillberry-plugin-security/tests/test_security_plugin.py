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
