import os
from unittest.mock import patch

from skillberry_store.plugins.claude_credentials import (
    settings_env, has_api_access, build_agent_env,
)


def test_settings_env_returns_env_block():
    assert settings_env({"env": {"ANTHROPIC_MODEL": "m"}}) == {"ANTHROPIC_MODEL": "m"}
    assert settings_env({}) == {}
    assert settings_env(None) == {}
    assert settings_env({"env": "nope"}) == {}


def test_has_api_access():
    assert has_api_access({"ANTHROPIC_API_KEY": "k"}) is True
    assert has_api_access({"ANTHROPIC_BASE_URL": "u", "ANTHROPIC_AUTH_TOKEN": "t"}) is True
    assert has_api_access({"ANTHROPIC_BASE_URL": "u"}) is False
    assert has_api_access({}) is False


def test_build_agent_env_forwards_full_block_then_overrides():
    settings = {"env": {"ANTHROPIC_MODEL": "from-settings", "ANTHROPIC_SMALL_FAST_MODEL": "s"}}
    clean = {k: v for k, v in os.environ.items()
             if not (k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_"))}
    with patch.dict(os.environ, {**clean, "ANTHROPIC_MODEL": "from-process"}, clear=True):
        env = build_agent_env(settings, {"ANTHROPIC_AUTH_TOKEN": "tok"})
    assert env["ANTHROPIC_SMALL_FAST_MODEL"] == "s"   # from settings block
    assert env["ANTHROPIC_MODEL"] == "from-process"   # process overrides settings
    assert env["ANTHROPIC_AUTH_TOKEN"] == "tok"       # explicit override wins
