from pathlib import Path

import pytest

from skillberry_plugin_sdk.manifest import PluginManifest, load_manifest


def test_manifest_missing_env_reports_required(tmp_path: Path) -> None:
    manifest = PluginManifest(
        name="Test",
        slug="test",
        version="0.1.0",
        required_env=[
            {"name": "REQ_A", "required": True},
            {"name": "REQ_B", "required": True},
            {"name": "OPT_C", "required": False},
        ],
    )
    missing = manifest.missing_env({"REQ_A": "x"})
    assert missing == ["REQ_B"]


def test_load_manifest_from_yaml(tmp_path: Path) -> None:
    p = tmp_path / "manifest.yaml"
    p.write_text(
        """
name: Test Plugin
slug: test-plugin
version: 0.1.0
description: hi
plugin_type: evaluator
has_api: false
required_env:
  - name: FOO
    required: true
""".strip()
    )
    m = load_manifest(p)
    assert m.slug == "test-plugin"
    assert m.required_env[0].name == "FOO"


def test_manifest_empty_string_env_is_missing() -> None:
    manifest = PluginManifest(
        name="T", slug="t", version="0.1.0",
        required_env=[{"name": "REQ_A", "required": True}],
    )
    assert manifest.missing_env({"REQ_A": ""}) == ["REQ_A"]
