"""Tests for the dependency-tracker plugin (mocked store, offline PyPI)."""

import copy

import pytest

from skillberry_plugin_dependency_tracker.plugin import (
    SkillberryPluginDependencyTracker,
)
from skillberry_store.plugins.base import PluginType


class _Tools:
    """Stand-in for store.tools, backed by an in-memory module map."""

    def __init__(self, modules):
        # (uuid, filename) -> source
        self._modules = modules

    def read_file(self, uuid, filename, raw_content=False):
        return self._modules[(uuid, filename)]


class FakeStore:
    """In-memory store with get_/update_ round-trip and tools.read_file."""

    def __init__(self, objects=None, modules=None):
        self._objs = objects or {}
        self.tools = _Tools(modules or {})

    def get_skill(self, uuid):
        return copy.deepcopy(self._objs.get(("skill", uuid)))

    def get_tool(self, uuid):
        return copy.deepcopy(self._objs.get(("tool", uuid)))

    def get_snippet(self, uuid):
        return copy.deepcopy(self._objs.get(("snippet", uuid)))

    def update_skill(self, uuid, data):
        self._objs[("skill", uuid)] = copy.deepcopy(data)
        return True

    def update_tool(self, uuid, data):
        self._objs[("tool", uuid)] = copy.deepcopy(data)
        return True

    def update_snippet(self, uuid, data):
        self._objs[("snippet", uuid)] = copy.deepcopy(data)
        return True


def _plugin(store, monkeypatch):
    # Default PyPI off in tests so nothing hits the network.
    monkeypatch.setenv("DEPENDENCY_TRACKER_PYPI", "off")
    p = SkillberryPluginDependencyTracker()
    p.set_store_api(store)
    return p


# ── metadata / interface ──────────────────────────────────────────────────────


def test_metadata_and_enablement():
    p = SkillberryPluginDependencyTracker()
    assert p.metadata.name == "Dependency Tracker"
    assert p.metadata.plugin_type == PluginType.EVALUATOR
    assert p.is_enabled() is True


def test_router_exposes_scan():
    p = SkillberryPluginDependencyTracker()
    paths = {r.path for r in p.get_router().routes}
    assert "/resolve-dependencies" in paths


def test_ui_config_action_has_object_type_default():
    p = SkillberryPluginDependencyTracker()
    cfg = p.get_ui_config()
    action = cfg["actions"][0]
    assert action["label"] == "Scan dependencies"
    assert action["params_schema"]["properties"]["object_type"]["default"] == "tool"


def test_registers_no_event_handlers():
    """On-demand only: instantiation must not add content_added handlers."""
    from skillberry_store.plugins import events

    before = {k: len(v) for k, v in events._event_handlers.items()}
    SkillberryPluginDependencyTracker()
    after = {k: len(v) for k, v in events._event_handlers.items()}
    assert before == after


# ── validation ────────────────────────────────────────────────────────────────


def test_endpoint_blank_input_is_400_not_422():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(SkillberryPluginDependencyTracker().get_router())
    client = TestClient(app)

    r = client.post("/resolve-dependencies", json={})
    assert r.status_code == 400
    assert "uuid is required" in r.json()["detail"]

    r = client.post("/resolve-dependencies", json={"object_type": "widget", "uuid": "x"})
    assert r.status_code == 400
    assert "object_type must be one of" in r.json()["detail"]


# ── scan end-to-end (offline) ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scan_tool_populates_dependencies(monkeypatch):
    store = FakeStore(
        objects={
            ("tool", "t1"): {
                "uuid": "t1",
                "name": "fetcher",
                "module_name": "main.py",
                "extra": {"other": "keep me"},  # must be preserved
                "tags": ["python"],
            }
        },
        modules={("t1", "main.py"): "import os\nimport requests\n"},
    )
    p = _plugin(store, monkeypatch)
    result = await p.scan("tool", "t1")

    block = result["dependencies"]
    assert block["languages_inspected"] == ["python"]
    assert "python" in block["supported_languages"]
    assert "shell" in block["supported_languages"]
    assert "requests" in block["packages"]
    assert block["packages"]["requests"]["direct"] is True
    assert block["packages"]["requests"]["language"] == "python"
    assert block["summary"]["total_count"] >= 1
    assert block["summary"]["skipped_count"] == 0
    assert block["summary"]["pypi_status"] == "skipped"  # PyPI off

    # persisted non-destructively + dep tags added
    stored = store.get_tool("t1")
    assert stored["extra"]["dependencies"]["languages_inspected"] == ["python"]
    assert stored["extra"]["other"] == "keep me"
    assert any(t.startswith("dep:count:") for t in stored["tags"])
    assert "dep:lang:python" in stored["tags"]
    assert "python" in stored["tags"]  # pre-existing tag kept


@pytest.mark.asyncio
async def test_scan_snippet(monkeypatch):
    store = FakeStore(
        objects={
            ("snippet", "s1"): {"uuid": "s1", "name": "n", "content": "import requests"}
        }
    )
    p = _plugin(store, monkeypatch)
    result = await p.scan("snippet", "s1")
    assert "requests" in result["dependencies"]["packages"]


@pytest.mark.asyncio
async def test_scan_skill_aggregates_children(monkeypatch):
    store = FakeStore(
        objects={
            ("skill", "sk1"): {
                "uuid": "sk1",
                "name": "skill",
                "tool_uuids": ["t1"],
                "snippet_uuids": ["s1"],
            },
            ("tool", "t1"): {"uuid": "t1", "name": "t", "module_name": "m.py"},
            ("snippet", "s1"): {
                "uuid": "s1",
                "name": "s",
                "content": "import requests",
            },
        },
        modules={("t1", "m.py"): "import urllib3\n"},
    )
    p = _plugin(store, monkeypatch)
    result = await p.scan("skill", "sk1")
    pkgs = result["dependencies"]["packages"]
    # both children's imports surfaced
    assert "requests" in pkgs
    assert "urllib3" in pkgs


@pytest.mark.asyncio
async def test_scan_shell_tool_finds_commands(monkeypatch):
    store = FakeStore(
        objects={
            ("tool", "sh1"): {
                "uuid": "sh1",
                "name": "bundle",
                "module_name": "bundle.sh",
            }
        },
        modules={
            ("sh1", "bundle.sh"): (
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "curl -sSL https://example.com -o out.json\n"
                "jq '.x' out.json\n"
                "zip -r bundle.zip .\n"
            )
        },
    )
    p = _plugin(store, monkeypatch)
    result = await p.scan("tool", "sh1")
    block = result["dependencies"]
    assert block["languages_inspected"] == ["shell"]
    pkgs = block["packages"]
    # external commands captured as system-source shell deps
    for cmd in ("curl", "jq", "zip"):
        assert cmd in pkgs, f"missing {cmd}"
        assert pkgs[cmd]["source"] == "system"
        assert pkgs[cmd]["language"] == "shell"
        assert pkgs[cmd]["version"] is None
    # shell builtins / keywords are NOT deps
    for builtin in ("set", "export", "if", "fi"):
        assert builtin not in pkgs


@pytest.mark.asyncio
async def test_mixed_skill_python_and_shell(monkeypatch):
    store = FakeStore(
        objects={
            ("skill", "sk2"): {
                "uuid": "sk2",
                "name": "mixed",
                "tool_uuids": ["pyt", "sht"],
                "snippet_uuids": [],
            },
            ("tool", "pyt"): {"uuid": "pyt", "name": "py", "module_name": "a.py"},
            ("tool", "sht"): {"uuid": "sht", "name": "sh", "module_name": "b.sh"},
        },
        modules={
            ("pyt", "a.py"): "import requests\n",
            ("sht", "b.sh"): "#!/bin/sh\naws s3 cp x y\n",
        },
    )
    p = _plugin(store, monkeypatch)
    block = (await p.scan("skill", "sk2"))["dependencies"]
    assert set(block["languages_inspected"]) == {"python", "shell"}
    assert block["packages"]["requests"]["language"] == "python"
    assert block["packages"]["aws"]["language"] == "shell"


@pytest.mark.asyncio
async def test_local_modules_not_counted_as_missing(monkeypatch):
    # A skill that imports its own bundled `helpers` package (leaf merge_runs is
    # a bundled tool module) plus a real-but-absent external (`lxml`).
    store = FakeStore(
        objects={
            ("skill", "sk3"): {
                "uuid": "sk3",
                "name": "doc-skill",
                "tool_uuids": ["mr", "user"],
                "snippet_uuids": [],
            },
            # bundled helper module: its stem `merge_runs` makes `helpers` local
            ("tool", "mr"): {
                "uuid": "mr",
                "name": "merge_runs",
                "module_name": "merge_runs.py",
            },
            ("tool", "user"): {"uuid": "user", "name": "u", "module_name": "u.py"},
        },
        modules={
            ("mr", "merge_runs.py"): "def merge_runs():\n    pass\n",
            ("user", "u.py"): (
                "from helpers.merge_runs import merge_runs\n" "import lxml.etree\n"
            ),
        },
    )
    p = _plugin(store, monkeypatch)
    block = (await p.scan("skill", "sk3"))["dependencies"]
    reasons = {u["import_name"]: u["reason"] for u in block["unresolved_imports"]}
    # `helpers` recognized as first-party, lxml flagged as a real missing pkg
    assert reasons.get("helpers") == "local_module"
    assert reasons.get("lxml") == "no_distribution"
    assert block["summary"]["local_module_count"] == 1
    assert block["summary"]["missing_count"] == 1
    # tag reflects only the real missing external
    stored = store.get_skill("sk3")
    assert "dep:missing:1" in stored["tags"]


@pytest.mark.asyncio
async def test_local_package_detected_via_imported_symbol(monkeypatch):
    # `from office.soffice import get_soffice_env` — the imported symbol matches
    # a bundled tool (`get_soffice_env`), so `office` is first-party even though
    # `soffice` itself isn't a tool stem.
    store = FakeStore(
        objects={
            ("skill", "sk4"): {
                "uuid": "sk4",
                "name": "office-skill",
                "tool_uuids": ["env", "caller"],
                "snippet_uuids": [],
            },
            ("tool", "env"): {
                "uuid": "env",
                "name": "get_soffice_env",
                "module_name": "get_soffice_env.py",
            },
            ("tool", "caller"): {"uuid": "caller", "name": "c", "module_name": "c.py"},
        },
        modules={
            ("env", "get_soffice_env.py"): "def get_soffice_env():\n    return {}\n",
            ("caller", "c.py"): "from office.soffice import get_soffice_env\n",
        },
    )
    p = _plugin(store, monkeypatch)
    block = (await p.scan("skill", "sk4"))["dependencies"]
    reasons = {u["import_name"]: u["reason"] for u in block["unresolved_imports"]}
    assert reasons.get("office") == "local_module"
    assert block["summary"]["missing_count"] == 0


@pytest.mark.asyncio
async def test_unsupported_file_recorded_in_skipped(monkeypatch):
    # A tool whose module is, say, JavaScript -> can't inspect -> skipped.
    store = FakeStore(
        objects={
            ("tool", "js1"): {
                "uuid": "js1",
                "name": "widget",
                "module_name": "widget.js",
            }
        },
        modules={("js1", "widget.js"): "const x = require('left-pad');\n"},
    )
    p = _plugin(store, monkeypatch)
    block = (await p.scan("tool", "js1"))["dependencies"]
    assert block["packages"] == {}
    assert block["summary"]["skipped_count"] == 1
    skipped = block["skipped_files"]
    assert skipped and skipped[0]["file"] == "widget.js"
    assert skipped[0]["reason"] == "unsupported_language"
    # tag surfaced
    stored = store.get_tool("js1")
    assert any(t == "dep:skipped:1" for t in stored["tags"])


@pytest.mark.asyncio
async def test_missing_object_raises_valueerror(monkeypatch):
    p = _plugin(FakeStore(), monkeypatch)
    with pytest.raises(ValueError):
        await p.scan("tool", "nope")


@pytest.mark.asyncio
async def test_pypi_failure_degrades_gracefully(monkeypatch):
    # Force PyPI on, but make every call raise -> scan still succeeds.
    import skillberry_plugin_dependency_tracker.resolver.pypi as pypi_mod

    store = FakeStore(
        objects={("tool", "t1"): {"uuid": "t1", "name": "t", "module_name": "m.py"}},
        modules={("t1", "m.py"): "import requests"},
    )
    monkeypatch.setenv("DEPENDENCY_TRACKER_PYPI", "on")

    def _boom(dist, ver, timeout, session):
        return {"status": "error"}

    monkeypatch.setattr(pypi_mod, "enrich_from_pypi", _boom)

    p = SkillberryPluginDependencyTracker()
    p.set_store_api(store)
    result = await p.scan("tool", "t1")  # must not raise
    assert "requests" in result["dependencies"]["packages"]
    assert result["dependencies"]["summary"]["pypi_status"] in ("partial", "skipped")
