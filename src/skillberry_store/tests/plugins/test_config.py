"""Tests for PluginConfigStore (plugin enable/disable persistence)."""

import json
import pytest
from skillberry_store.plugins.config import PluginConfigStore


def test_default_is_enabled(tmp_path):
    store = PluginConfigStore(path=tmp_path / "plugins.json")
    # Nothing recorded yet -> every plugin is enabled by default.
    assert store.is_enabled("any-plugin") is True


def test_disable_then_enable_roundtrip(tmp_path):
    store = PluginConfigStore(path=tmp_path / "plugins.json")
    store.set_enabled("plugin-a", False)
    assert store.is_enabled("plugin-a") is False
    store.set_enabled("plugin-a", True)
    assert store.is_enabled("plugin-a") is True


def test_persists_across_reload(tmp_path):
    cfg = tmp_path / "plugins.json"
    store = PluginConfigStore(path=cfg)
    store.set_enabled("plugin-a", False)

    reloaded = PluginConfigStore(path=cfg)
    assert reloaded.is_enabled("plugin-a") is False
    assert reloaded.is_enabled("plugin-b") is True


def test_file_shape_lists_only_disabled(tmp_path):
    cfg = tmp_path / "plugins.json"
    store = PluginConfigStore(path=cfg)
    store.set_enabled("plugin-a", False)
    store.set_enabled("plugin-b", False)
    store.set_enabled("plugin-a", True)  # re-enable removes it

    data = json.loads(cfg.read_text())
    assert data == {"disabled": ["plugin-b"]}


def test_corrupt_file_falls_back_to_all_enabled(tmp_path):
    cfg = tmp_path / "plugins.json"
    cfg.write_text("{ this is not valid json")
    store = PluginConfigStore(path=cfg)
    assert store.is_enabled("plugin-a") is True


def test_env_var_overrides_default_path(tmp_path, monkeypatch):
    cfg = tmp_path / "custom.json"
    monkeypatch.setenv("SKILLBERRY_PLUGIN_CONFIG", str(cfg))
    store = PluginConfigStore()
    assert store.path == cfg
