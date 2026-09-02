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


def test_file_shape_lists_only_disabled_plus_owners(tmp_path):
    cfg = tmp_path / "plugins.json"
    store = PluginConfigStore(path=cfg)
    store.set_enabled("plugin-a", False)
    store.set_enabled("plugin-b", False)
    store.set_enabled("plugin-a", True)  # re-enable removes it

    data = json.loads(cfg.read_text())
    assert data == {"disabled": ["plugin-b"], "owners": {}}


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


# ── owner tenant (plugin-identity §5.1) ─────────────────────────────────── #


def test_owner_is_absent_by_default(tmp_path):
    store = PluginConfigStore(path=tmp_path / "plugins.json")
    assert store.get_owner("sast") is None
    assert store.owners() == {}


def test_owner_round_trips_through_disk(tmp_path):
    cfg = tmp_path / "plugins.json"
    store = PluginConfigStore(path=cfg)
    store.set_owner("sast", "team-blue")
    store.set_owner("provenance", "team-blue")

    reloaded = PluginConfigStore(path=cfg)
    assert reloaded.get_owner("sast") == "team-blue"
    assert reloaded.owners() == {"provenance": "team-blue", "sast": "team-blue"}


def test_owner_and_enablement_coexist(tmp_path):
    cfg = tmp_path / "plugins.json"
    store = PluginConfigStore(path=cfg)
    store.set_owner("sast", "team-blue")
    store.set_enabled("sast", False)

    reloaded = PluginConfigStore(path=cfg)
    assert reloaded.get_owner("sast") == "team-blue"
    assert reloaded.is_enabled("sast") is False


def test_clearing_an_owner_removes_it(tmp_path):
    cfg = tmp_path / "plugins.json"
    store = PluginConfigStore(path=cfg)
    store.set_owner("sast", "team-blue")
    store.set_owner("sast", None)
    assert store.get_owner("sast") is None
    assert json.loads(cfg.read_text())["owners"] == {}


def test_legacy_file_without_owners_key_loads(tmp_path):
    """A config written before owners existed must still load."""
    cfg = tmp_path / "plugins.json"
    cfg.write_text(json.dumps({"disabled": ["dedupe"]}))
    store = PluginConfigStore(path=cfg)
    assert store.is_enabled("dedupe") is False
    assert store.owners() == {}


def test_malformed_owners_value_is_ignored(tmp_path):
    cfg = tmp_path / "plugins.json"
    cfg.write_text(json.dumps({"disabled": [], "owners": ["not", "a", "map"]}))
    store = PluginConfigStore(path=cfg)
    assert store.owners() == {}
