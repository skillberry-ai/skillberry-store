import os
from unittest.mock import Mock, patch

from skillberry_plugin_ask_runspace.presets import PRESETS, compose_prompt
from skillberry_plugin_ask_runspace.plugin import SkillberryPluginAskRunspace


def test_presets_have_id_label_guidance():
    assert PRESETS
    for p in PRESETS:
        assert {"id", "label", "guidance"} <= set(p)


def test_compose_prompt_combines_guidance_and_request():
    pid = PRESETS[0]["id"]
    out = compose_prompt(pid, "do the thing")
    assert "do the thing" in out
    assert PRESETS[0]["guidance"] in out


def test_compose_prompt_request_only():
    assert compose_prompt(None, "just this") .strip().endswith("just this")


def _plugin(env):
    with patch.dict(os.environ, env, clear=True):
        with patch("skillberry_plugin_ask_runspace.plugin.runspace_agent", new=Mock()):
            with patch.object(SkillberryPluginAskRunspace, "_load_claude_settings", lambda self: None):
                return SkillberryPluginAskRunspace()


def test_disabled_without_credentials():
    p = _plugin({})
    assert p.is_enabled() is False
    assert "credentials" in p.get_status_message().lower()


def test_enabled_with_api_key():
    p = _plugin({"ANTHROPIC_API_KEY": "k"})
    assert p.is_enabled() is True
