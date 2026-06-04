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
