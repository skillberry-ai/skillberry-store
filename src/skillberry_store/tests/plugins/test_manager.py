"""Tests for the PluginManager (mocked pip / subprocess)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from skillberry_store.fast_api.plugin_proxy import PluginRegistry
from skillberry_store.plugins.manager import (
    AlreadyInstalledError,
    MissingEnvError,
    NotInstalledError,
    PluginManager,
    _allocate_port,
    _slug_from_dir,
)
from skillberry_store.plugins.state_store import PluginStateStore


def _make_catalog(catalog: Path, slug: str, required_env=None) -> None:
    dir_name = f"skillberry-plugin-{slug}"
    plugin_dir = catalog / dir_name
    plugin_dir.mkdir(parents=True)
    manifest = {
        "name": slug.title(),
        "slug": slug,
        "version": "0.1.0",
        "sdk_version": "^0.1",
        "has_api": False,
    }
    if required_env:
        manifest["required_env"] = required_env
    (plugin_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest))
    (plugin_dir / "pyproject.toml").write_text(
        f"""[build-system]
requires = ["setuptools>=45"]
build-backend = "setuptools.build_meta"

[project]
name = "skillberry-plugin-{slug}"
version = "0.1.0"

[tool.setuptools]
packages = ["skillberry_plugin_{slug.replace('-', '_')}"]
package-dir = {{"" = "src"}}
"""
    )


@pytest.fixture
def manager(tmp_path: Path) -> PluginManager:
    catalog = tmp_path / "plugins"
    catalog.mkdir()
    _make_catalog(catalog, "alpha")
    _make_catalog(catalog, "beta", required_env=[{"name": "MUST_SET", "required": True}])
    state = PluginStateStore(tmp_path / "state.json")
    registry = PluginRegistry()
    m = PluginManager(
        registry=registry,
        state_store=state,
        catalog_dir=catalog,
        plugin_home=tmp_path / "home",
        sbs_base_url="http://127.0.0.1:0",
    )
    return m


def test_slug_from_dir() -> None:
    assert _slug_from_dir("skillberry-plugin-foo") == "foo"
    assert _slug_from_dir("other") == "other"


def test_allocate_port_returns_free(tmp_path: Path) -> None:
    port = _allocate_port(8100, 8200)
    assert 8100 <= port <= 8200


def test_list_available(manager: PluginManager) -> None:
    catalog = manager.list_available()
    slugs = {p["slug"] for p in catalog}
    assert slugs == {"alpha", "beta"}


@pytest.mark.asyncio
async def test_install_missing_env_becomes_422_style(manager: PluginManager, monkeypatch) -> None:
    async def fake_run_venv(self, venv_dir: Path) -> None:
        venv_dir.mkdir(parents=True, exist_ok=True)
        (venv_dir / "bin").mkdir(parents=True, exist_ok=True)

    async def fake_pip(self, slug, venv_dir, plugin_dir) -> None:
        return None

    monkeypatch.setattr(PluginManager, "_run_venv", fake_run_venv)
    monkeypatch.setattr(PluginManager, "_pip_install", fake_pip)
    # Purge any leftover env from the test environment.
    monkeypatch.delenv("MUST_SET", raising=False)

    with pytest.raises(MissingEnvError) as info:
        await manager.install("beta", autostart=True)
    assert info.value.missing == ["MUST_SET"]


@pytest.mark.asyncio
async def test_install_already_installed_raises(manager: PluginManager, monkeypatch) -> None:
    async def fake_run_venv(self, venv_dir: Path) -> None:
        venv_dir.mkdir(parents=True, exist_ok=True)
        (venv_dir / "bin").mkdir(parents=True, exist_ok=True)

    async def fake_pip(self, slug, venv_dir, plugin_dir) -> None:
        return None

    monkeypatch.setattr(PluginManager, "_run_venv", fake_run_venv)
    monkeypatch.setattr(PluginManager, "_pip_install", fake_pip)

    await manager.install("alpha", autostart=False)
    with pytest.raises(AlreadyInstalledError):
        await manager.install("alpha", autostart=False)


@pytest.mark.asyncio
async def test_uninstall_not_installed_raises(manager: PluginManager) -> None:
    with pytest.raises(NotInstalledError):
        await manager.uninstall("alpha")


def test_missing_env_uses_env_overrides(manager: PluginManager, monkeypatch) -> None:
    monkeypatch.delenv("MUST_SET", raising=False)
    manifest = {"required_env": [{"name": "MUST_SET", "required": True}]}
    assert manager._missing_env("beta", manifest, {"MUST_SET": "x"}) == []
    assert manager._missing_env("beta", manifest, {}) == ["MUST_SET"]
