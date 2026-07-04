"""Plugin lifecycle API — install/start/stop/restart/uninstall + listings."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PluginEnabledUpdate(BaseModel):
    enabled: bool


class PluginInstallBody(BaseModel):
    env_overrides: Optional[Dict[str, str]] = None


def register_plugins_api(
    app: FastAPI,
    plugin_loader: Any = None,
    plugin_manager: Any = None,
    tags: str = "plugins",
) -> None:
    """Register plugin management endpoints.

    ``plugin_manager`` handles the out-of-process subprocess lifecycle. If
    ``plugin_loader`` is also supplied (transitional, Stages 3-6), its
    in-process plugin catalog is exposed via ``GET /plugins/`` when no
    manager entries exist.
    """

    from skillberry_store.plugins.manager import (
        AlreadyInstalledError,
        AlreadyRunningError,
        InstallFailedError,
        MissingEnvError,
        NotInstalledError,
        NotRunningError,
        PluginError,
        StartupFailedError,
        UnknownPluginError,
    )

    def _raise_from(e: PluginError) -> None:
        if isinstance(e, MissingEnvError):
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "missing_env",
                    "missing": e.missing,
                    "slug": e.slug,
                },
            )
        if isinstance(e, (AlreadyInstalledError, AlreadyRunningError)):
            raise HTTPException(status_code=409, detail=str(e))
        if isinstance(e, (NotInstalledError, NotRunningError)):
            raise HTTPException(status_code=409, detail=str(e))
        if isinstance(e, UnknownPluginError):
            raise HTTPException(status_code=404, detail=str(e))
        if isinstance(e, InstallFailedError):
            raise HTTPException(
                status_code=500, detail={"error": "install_failed", "stderr": e.stderr[-800:]}
            )
        if isinstance(e, StartupFailedError):
            raise HTTPException(status_code=500, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    # ── Available (catalog scan) ─────────────────────────────────────────────

    @app.get(
        "/plugins/available",
        tags=[tags],
        summary="List installable plugin manifests",
        response_model=List[Dict[str, Any]],
    )
    async def list_available_plugins():
        if plugin_manager is None:
            return []
        return plugin_manager.list_available()

    # ── List installed / list in-process ─────────────────────────────────────

    @app.get(
        "/plugins/",
        tags=[tags],
        summary="List installed plugins with runtime state",
        response_model=List[Dict[str, Any]],
    )
    async def list_plugins():
        if plugin_manager is not None:
            installed = plugin_manager.list_installed()
            if installed:
                return installed
        # Fallback: legacy in-process view (Stage 3–5 transitional).
        if plugin_loader is not None:
            try:
                return plugin_loader.list_plugins()
            except Exception as e:  # pragma: no cover - defensive
                logger.error("legacy list_plugins failed: %s", e)
                return []
        return []

    # ── Get one --------------------------------------------------------------

    @app.get(
        "/plugins/{slug}",
        tags=[tags],
        summary="Get plugin information",
        response_model=Dict[str, Any],
    )
    async def get_plugin(slug: str):
        if plugin_manager is not None:
            for item in plugin_manager.list_installed():
                if item["slug"] == slug:
                    return item
            for item in plugin_manager.list_available():
                if item["slug"] == slug:
                    return {"slug": slug, "state": "not_installed", "manifest": item}
        if plugin_loader is not None:
            info = plugin_loader.get_plugin_info(slug)
            if info is not None:
                return info
        raise HTTPException(status_code=404, detail=f"Plugin '{slug}' not found")

    # ── Install / uninstall --------------------------------------------------

    @app.post(
        "/plugins/{slug}/install",
        tags=[tags],
        summary="Install a plugin from the catalog",
    )
    async def install_plugin(
        slug: str,
        autostart: bool = True,
        body: Optional[PluginInstallBody] = None,
    ):
        if plugin_manager is None:
            raise HTTPException(status_code=503, detail="Plugin manager not available")
        env_overrides = body.env_overrides if body else None
        try:
            return await plugin_manager.install(
                slug, autostart=autostart, env_overrides=env_overrides
            )
        except PluginError as e:
            _raise_from(e)

    @app.delete(
        "/plugins/{slug}",
        tags=[tags],
        summary="Uninstall a plugin",
    )
    async def uninstall_plugin(slug: str):
        if plugin_manager is None:
            raise HTTPException(status_code=503, detail="Plugin manager not available")
        try:
            await plugin_manager.uninstall(slug)
            return {"slug": slug, "state": "not_installed"}
        except PluginError as e:
            _raise_from(e)

    # ── Start / stop / restart ----------------------------------------------

    @app.post("/plugins/{slug}/start", tags=[tags], summary="Start a plugin")
    async def start_plugin(slug: str):
        if plugin_manager is None:
            raise HTTPException(status_code=503, detail="Plugin manager not available")
        try:
            return await plugin_manager.start(slug)
        except PluginError as e:
            _raise_from(e)

    @app.post("/plugins/{slug}/stop", tags=[tags], summary="Stop a plugin")
    async def stop_plugin(slug: str):
        if plugin_manager is None:
            raise HTTPException(status_code=503, detail="Plugin manager not available")
        try:
            await plugin_manager.stop(slug)
            return {"slug": slug, "state": "installed"}
        except PluginError as e:
            _raise_from(e)

    @app.post("/plugins/{slug}/restart", tags=[tags], summary="Restart a plugin")
    async def restart_plugin(slug: str):
        if plugin_manager is None:
            raise HTTPException(status_code=503, detail="Plugin manager not available")
        try:
            return await plugin_manager.restart(slug)
        except PluginError as e:
            _raise_from(e)

    # ── Legacy in-process toggle (kept for the transitional period) ────────

    if plugin_loader is not None:

        @app.patch(
            "/plugins/{slug}",
            tags=[tags],
            summary="Enable/disable a legacy in-process plugin",
            response_model=Dict[str, Any],
        )
        async def update_plugin(slug: str, body: PluginEnabledUpdate):
            if plugin_loader.get_plugin_info(slug) is None:
                raise HTTPException(status_code=404, detail=f"Plugin '{slug}' not found")
            try:
                plugin_loader.set_enabled(slug, body.enabled)
            except KeyError:
                raise HTTPException(status_code=404, detail=f"Plugin '{slug}' not found")
            return plugin_loader.get_plugin_info(slug)
