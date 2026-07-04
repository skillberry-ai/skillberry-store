"""PluginManager — installs, starts, stops, and uninstalls plugins as subprocesses.

Design highlights (see docs/plugin-process-migration-plan.md):

- Catalog is the ``plugins/`` folder inside the repo. A plugin is *installable*
  if its directory contains ``pyproject.toml`` **and** a ``manifest.yaml``.
- Install creates a per-plugin venv under ``~/.skillberry/plugins/<slug>/venv``
  and pip-installs the plugin (editable). Records go into the plugin state file.
- Start allocates a free port from an internal range, generates a token, spawns
  ``<venv>/bin/python -m <module>``, then health-probes ``/lifecycle/health``.
- Stop tries POST /lifecycle/shutdown first, then SIGTERM, then SIGKILL after 5 s.
- Env validation runs *before* spawn — a missing required var raises
  ``MissingEnvError`` and is surfaced as HTTP 422.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import yaml

from skillberry_store.fast_api.plugin_proxy import PluginRegistry, ProxyTarget
from skillberry_store.plugins.state_store import PluginStateStore

logger = logging.getLogger(__name__)


# ── Errors ────────────────────────────────────────────────────────────────────


class PluginError(Exception):
    """Base class for manager errors."""


class UnknownPluginError(PluginError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"plugin '{slug}' not found in catalog")
        self.slug = slug


class AlreadyInstalledError(PluginError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"plugin '{slug}' is already installed")
        self.slug = slug


class NotInstalledError(PluginError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"plugin '{slug}' is not installed")
        self.slug = slug


class AlreadyRunningError(PluginError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"plugin '{slug}' is already running")
        self.slug = slug


class NotRunningError(PluginError):
    def __init__(self, slug: str) -> None:
        super().__init__(f"plugin '{slug}' is not running")
        self.slug = slug


class MissingEnvError(PluginError):
    def __init__(self, slug: str, missing: List[str]) -> None:
        super().__init__(f"plugin '{slug}' is missing required env vars: {missing}")
        self.slug = slug
        self.missing = missing


class InstallFailedError(PluginError):
    def __init__(self, slug: str, stderr: str) -> None:
        super().__init__(f"pip install for plugin '{slug}' failed: {stderr[:400]}")
        self.slug = slug
        self.stderr = stderr


class StartupFailedError(PluginError):
    def __init__(self, slug: str, detail: str) -> None:
        super().__init__(f"plugin '{slug}' failed to start: {detail}")
        self.slug = slug
        self.detail = detail


# ── Catalog helpers ───────────────────────────────────────────────────────────


def _repo_plugins_dir() -> Path:
    """Return the plugins/ folder relative to the repo root."""
    here = Path(__file__).resolve()
    # /src/skillberry_store/plugins/manager.py -> repo root is 3 parents up
    return here.parents[3] / "plugins"


def _plugin_state_home() -> Path:
    override = os.environ.get("SKILLBERRY_PLUGIN_HOME")
    if override:
        return Path(override)
    return Path.home() / ".skillberry" / "plugins"


def _read_manifest(plugin_dir: Path) -> Optional[Dict[str, Any]]:
    manifest_path = plugin_dir / "manifest.yaml"
    if not manifest_path.exists():
        return None
    try:
        return yaml.safe_load(manifest_path.read_text()) or {}
    except yaml.YAMLError as e:
        logger.warning("bad manifest for %s: %s", plugin_dir.name, e)
        return None


def _read_manifest_from_installed_or_repo(slug: str, catalog_dir: Path) -> Optional[Dict[str, Any]]:
    return _read_manifest(catalog_dir / slug)


def _package_module_from_pyproject(plugin_dir: Path) -> Optional[str]:
    """Guess the ``python -m`` entrypoint from pyproject.toml packages list."""
    py = plugin_dir / "pyproject.toml"
    if not py.exists():
        return None
    try:
        import tomllib  # type: ignore[attr-defined]
    except ModuleNotFoundError:  # pragma: no cover - <3.11
        import tomli as tomllib  # type: ignore[import]
    try:
        data = tomllib.loads(py.read_text())
    except Exception as e:
        logger.warning("cannot parse pyproject.toml for %s: %s", plugin_dir.name, e)
        return None
    packages = data.get("tool", {}).get("setuptools", {}).get("packages")
    if isinstance(packages, list) and packages:
        return packages[0]
    return None


# ── Manager ───────────────────────────────────────────────────────────────────


class _RunningProc:
    """Bookkeeping for a live plugin subprocess."""

    def __init__(self, slug: str, proc: subprocess.Popen, port: int, token: str) -> None:
        self.slug = slug
        self.proc = proc
        self.port = port
        self.token = token
        self.started_at = datetime.now(timezone.utc).isoformat()


class PluginManager:
    """Installs, starts, and stops plugin subprocesses driven by a state file."""

    PORT_RANGE: Tuple[int, int] = (8100, 8200)
    HEALTH_PROBE_TIMEOUT = 30.0
    STOP_GRACE_SECONDS = 5.0

    def __init__(
        self,
        registry: PluginRegistry,
        state_store: Optional[PluginStateStore] = None,
        *,
        catalog_dir: Optional[Path] = None,
        plugin_home: Optional[Path] = None,
        sbs_base_url: Optional[str] = None,
    ) -> None:
        self._registry = registry
        self._state = state_store or PluginStateStore()
        self._catalog_dir = catalog_dir or _repo_plugins_dir()
        self._plugin_home = plugin_home or _plugin_state_home()
        self._sbs_base_url = sbs_base_url or os.environ.get(
            "SKILLBERRY_STORE_URL", "http://127.0.0.1:8000"
        )
        self._running: Dict[str, _RunningProc] = {}
        self._lock = asyncio.Lock()

    # -- catalog / listing --------------------------------------------------

    def list_available(self) -> List[Dict[str, Any]]:
        """Enumerate installable plugin manifests found under ``plugins/``."""
        catalog: List[Dict[str, Any]] = []
        if not self._catalog_dir.exists():
            return catalog
        for entry in sorted(self._catalog_dir.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name == "skillberry-plugin-sdk":
                continue
            manifest = _read_manifest(entry)
            if manifest is None:
                continue
            manifest_out = dict(manifest)
            manifest_out.setdefault("slug", manifest.get("slug") or _slug_from_dir(entry.name))
            manifest_out["directory"] = entry.name
            catalog.append(manifest_out)
        return catalog

    def _catalog_by_slug(self) -> Dict[str, Dict[str, Any]]:
        by_slug: Dict[str, Dict[str, Any]] = {}
        for entry in self.list_available():
            by_slug[entry["slug"]] = entry
        return by_slug

    def _find_plugin_dir(self, slug: str) -> Optional[Path]:
        for entry in self._catalog_dir.iterdir():
            if not entry.is_dir():
                continue
            manifest = _read_manifest(entry)
            if manifest is None:
                continue
            catalog_slug = manifest.get("slug") or _slug_from_dir(entry.name)
            if catalog_slug == slug:
                return entry
        return None

    def list_installed(self) -> List[Dict[str, Any]]:
        """List installed plugins with runtime state + missing env."""
        by_slug = self._catalog_by_slug()
        result: List[Dict[str, Any]] = []
        for slug, entry in self._state.all().items():
            manifest = by_slug.get(slug, {})
            missing = self._missing_env(slug, manifest, entry.get("env_overrides") or {})
            item = {
                "slug": slug,
                "state": entry.get("last_state", "installed"),
                "installed_at": entry.get("installed_at"),
                "autostart": entry.get("autostart", False),
                "env_overrides": entry.get("env_overrides", {}),
                "manifest": manifest,
                "missing_env": missing,
                "port": self._running.get(slug).port if slug in self._running else None,
                "error": entry.get("error"),
            }
            result.append(item)
        return result

    # -- install / uninstall -----------------------------------------------

    def _plugin_home_dir(self, slug: str) -> Path:
        return self._plugin_home / slug

    def _venv_python(self, slug: str) -> Path:
        return self._plugin_home_dir(slug) / "venv" / "bin" / "python"

    async def install(
        self,
        slug: str,
        *,
        autostart: bool = True,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        async with self._lock:
            if self._state.get(slug) is not None:
                raise AlreadyInstalledError(slug)
            plugin_dir = self._find_plugin_dir(slug)
            if plugin_dir is None:
                raise UnknownPluginError(slug)
            home = self._plugin_home_dir(slug)
            venv_dir = home / "venv"
            home.mkdir(parents=True, exist_ok=True)
            if venv_dir.exists():
                shutil.rmtree(venv_dir)
            await self._run_venv(venv_dir)
            try:
                await self._pip_install(slug, venv_dir, plugin_dir)
            except InstallFailedError:
                shutil.rmtree(venv_dir, ignore_errors=True)
                raise
            entry = {
                "installed_at": datetime.now(timezone.utc).isoformat(),
                "autostart": autostart,
                "env_overrides": dict(env_overrides or {}),
                "last_state": "installed",
                "plugin_dir": str(plugin_dir),
            }
            self._state.upsert(slug, entry)

        if autostart:
            try:
                await self.start(slug)
            except MissingEnvError:
                raise
            except PluginError as e:
                self._state.update(slug, last_state="error", error=str(e))
                raise

        entry = self._state.get(slug) or {}
        return {"slug": slug, **entry}

    async def uninstall(self, slug: str) -> None:
        async with self._lock:
            if self._state.get(slug) is None:
                raise NotInstalledError(slug)
        if slug in self._running:
            await self.stop(slug)
        async with self._lock:
            home = self._plugin_home_dir(slug)
            if home.exists():
                shutil.rmtree(home, ignore_errors=True)
            self._state.delete(slug)

    # -- start / stop / restart --------------------------------------------

    async def start(self, slug: str) -> Dict[str, Any]:
        async with self._lock:
            entry = self._state.get(slug)
            if entry is None:
                raise NotInstalledError(slug)
            if slug in self._running:
                raise AlreadyRunningError(slug)

            plugin_dir = self._find_plugin_dir(slug)
            if plugin_dir is None:
                raise UnknownPluginError(slug)
            manifest = _read_manifest(plugin_dir) or {}

            missing = self._missing_env(slug, manifest, entry.get("env_overrides") or {})
            if missing:
                self._state.update(slug, last_state="error", error=f"missing_env: {missing}")
                raise MissingEnvError(slug, missing)

            self._state.update(slug, last_state="starting", error=None)

        try:
            port = _allocate_port(*self.PORT_RANGE)
            token = secrets.token_urlsafe(32)
            proc = await self._spawn(slug, port, token, manifest, entry.get("env_overrides") or {})
        except PluginError as e:
            self._state.update(slug, last_state="error", error=str(e))
            raise

        running = _RunningProc(slug=slug, proc=proc, port=port, token=token)
        try:
            await self._probe_health(port)
        except StartupFailedError as e:
            with contextlib.suppress(Exception):
                proc.terminate()
                proc.wait(timeout=2)
            self._state.update(slug, last_state="error", error=str(e))
            raise

        self._running[slug] = running
        self._registry.register(ProxyTarget(slug=slug, port=port, token=token))
        self._state.update(slug, last_state="running", error=None)
        logger.info("plugin %s running on 127.0.0.1:%s", slug, port)
        return {"slug": slug, "state": "running", "port": port}

    async def stop(self, slug: str) -> None:
        running = self._running.get(slug)
        if running is None:
            raise NotRunningError(slug)

        # Try graceful shutdown first.
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                await client.post(f"http://127.0.0.1:{running.port}/lifecycle/shutdown")
        except Exception:
            pass

        proc = running.proc
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            await asyncio.wait_for(_wait_proc(proc), timeout=self.STOP_GRACE_SECONDS)
        except asyncio.TimeoutError:
            with contextlib.suppress(Exception):
                proc.kill()
                await _wait_proc(proc)

        self._registry.unregister(slug)
        self._running.pop(slug, None)
        self._state.update(slug, last_state="installed", error=None)

    async def restart(self, slug: str) -> Dict[str, Any]:
        if slug in self._running:
            await self.stop(slug)
        return await self.start(slug)

    async def stop_all(self) -> None:
        for slug in list(self._running.keys()):
            with contextlib.suppress(Exception):
                await self.stop(slug)

    def is_running(self, slug: str) -> bool:
        return slug in self._running

    async def bootstrap(self) -> None:
        """Autostart plugins whose state entries request it.

        Never blocks server startup on failure — failing plugins land in
        ``last_state = error`` and remain out of the proxy registry.
        """
        for slug, entry in self._state.all().items():
            if not entry.get("autostart"):
                continue
            plugin_dir = self._find_plugin_dir(slug)
            if plugin_dir is None:
                self._state.update(slug, last_state="error", error="not in catalog")
                continue
            venv_python = self._venv_python(slug)
            if not venv_python.exists():
                try:
                    manifest = _read_manifest(plugin_dir) or {}
                    home = self._plugin_home_dir(slug)
                    venv_dir = home / "venv"
                    home.mkdir(parents=True, exist_ok=True)
                    await self._run_venv(venv_dir)
                    await self._pip_install(slug, venv_dir, plugin_dir)
                except PluginError as e:
                    self._state.update(slug, last_state="error", error=str(e))
                    continue
            try:
                await self.start(slug)
            except PluginError as e:
                logger.warning("autostart of %s failed: %s", slug, e)

    # -- helpers -----------------------------------------------------------

    def _missing_env(
        self,
        slug: str,
        manifest: Dict[str, Any],
        env_overrides: Dict[str, str],
    ) -> List[str]:
        merged = {**os.environ, **env_overrides}
        missing = []
        for spec in manifest.get("required_env") or []:
            if not isinstance(spec, dict):
                continue
            if not spec.get("required", True):
                continue
            name = spec.get("name")
            if not name:
                continue
            if not merged.get(name):
                missing.append(name)
        return missing

    async def _run_venv(self, venv_dir: Path) -> None:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "venv",
            str(venv_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise InstallFailedError("venv", stderr.decode("utf-8", "replace"))

    async def _pip_install(self, slug: str, venv_dir: Path, plugin_dir: Path) -> None:
        pip = venv_dir / "bin" / "pip"
        args = [
            str(pip),
            "install",
            "--quiet",
            "-e",
            str(plugin_dir),
        ]
        # Also install the SDK from source (editable) since the plugins depend on it.
        sdk_dir = _repo_plugins_dir() / "skillberry-plugin-sdk"
        if sdk_dir.exists():
            args = [
                str(pip),
                "install",
                "--quiet",
                "-e",
                str(sdk_dir),
                "-e",
                str(plugin_dir),
            ]
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise InstallFailedError(slug, stderr.decode("utf-8", "replace"))

    async def _spawn(
        self,
        slug: str,
        port: int,
        token: str,
        manifest: Dict[str, Any],
        env_overrides: Dict[str, str],
    ) -> subprocess.Popen:
        plugin_dir = self._find_plugin_dir(slug)
        assert plugin_dir is not None
        module = _package_module_from_pyproject(plugin_dir)
        if module is None:
            raise StartupFailedError(slug, "cannot determine plugin __main__ module")

        env = os.environ.copy()
        env.update(env_overrides or {})
        env["SKILLBERRY_STORE_URL"] = self._sbs_base_url
        env["SKILLBERRY_EVENTS_URL"] = self._sbs_base_url
        env["SKILLBERRY_STORE_TOKEN"] = token
        env["SKILLBERRY_PLUGIN_PORT"] = str(port)
        env["SKILLBERRY_PLUGIN_SLUG"] = slug

        preexec_fn = None
        if sys.platform == "linux":
            preexec_fn = _linux_pdeathsig

        try:
            proc = subprocess.Popen(  # noqa: S603
                [str(self._venv_python(slug)), "-m", module],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=preexec_fn,
            )
        except OSError as e:
            raise StartupFailedError(slug, f"spawn failed: {e}")

        pid_file = self._plugin_home_dir(slug) / f"{slug}.pid"
        try:
            pid_file.write_text(str(proc.pid))
        except OSError:
            pass
        return proc

    async def _probe_health(self, port: int) -> None:
        deadline = asyncio.get_event_loop().time() + self.HEALTH_PROBE_TIMEOUT
        backoff = 0.1
        last_err = "not started"
        async with httpx.AsyncClient(timeout=2.0) as client:
            while asyncio.get_event_loop().time() < deadline:
                try:
                    r = await client.get(f"http://127.0.0.1:{port}/lifecycle/health")
                    if r.status_code == 200:
                        return
                    last_err = f"HTTP {r.status_code}"
                except httpx.HTTPError as e:
                    last_err = str(e)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.5, 1.0)
        raise StartupFailedError("(unknown)", f"health-probe timeout: {last_err}")


# ── Module-level helpers ──────────────────────────────────────────────────────


def _slug_from_dir(dir_name: str) -> str:
    """Convert 'skillberry-plugin-dedupe' to 'dedupe'."""
    if dir_name.startswith("skillberry-plugin-"):
        return dir_name[len("skillberry-plugin-"):]
    return dir_name


def _allocate_port(start: int, end: int) -> int:
    for p in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", p))
            except OSError:
                continue
            return p
    raise StartupFailedError("(unknown)", f"no free port in {start}-{end}")


async def _wait_proc(proc: subprocess.Popen) -> None:
    while proc.poll() is None:
        await asyncio.sleep(0.05)


def _linux_pdeathsig() -> None:
    """When the parent dies, deliver SIGTERM to this child."""
    try:
        import ctypes

        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        PR_SET_PDEATHSIG = 1
        libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0)
    except Exception:  # pragma: no cover - best effort
        pass
