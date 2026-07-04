"""Tests for the plugin state file."""

import json
from pathlib import Path

import pytest

from skillberry_store.plugins.state_store import PluginStateStore


def test_state_store_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "plugins.state.json"
    store = PluginStateStore(p)
    store.upsert(
        "kagenti-approver",
        {"installed_at": "now", "autostart": True, "env_overrides": {}, "last_state": "running"},
    )
    assert store.get("kagenti-approver")["autostart"] is True
    reloaded = PluginStateStore(p)
    assert "kagenti-approver" in reloaded.all()
    reloaded.update("kagenti-approver", last_state="installed")
    parsed = json.loads(p.read_text())
    assert parsed["plugins"]["kagenti-approver"]["last_state"] == "installed"


def test_state_store_in_memory_when_env_empty(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SKILLBERRY_PLUGIN_STATE_FILE", "")
    store = PluginStateStore()
    assert store.persistent is False
    store.upsert("stub", {"autostart": False, "last_state": "installed"})
    assert store.get("stub") is not None
    # A fresh instance loads nothing (in-memory).
    reloaded = PluginStateStore()
    assert reloaded.all() == {}


def test_state_store_ignores_corrupt_file(tmp_path: Path) -> None:
    p = tmp_path / "plugins.state.json"
    p.write_text("not json at all")
    store = PluginStateStore(p)
    assert store.all() == {}


def test_state_store_delete(tmp_path: Path) -> None:
    p = tmp_path / "plugins.state.json"
    store = PluginStateStore(p)
    store.upsert("x", {"last_state": "installed"})
    store.delete("x")
    assert store.get("x") is None
