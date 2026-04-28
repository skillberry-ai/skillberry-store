"""Runspace plugin: agent-driven skill export + Store Agent chat.

Talks to an external `runspace-srv` daemon (default http://localhost:6767)
to run Claude Code agents. The Python server never calls runspace directly —
it only builds request bodies that the browser submits to runspace-srv.
"""

from __future__ import annotations

from fastapi import APIRouter

from skillberry_store.plugins.base import UIManifest

from .router import build_router

PLUGIN_ID = "runspace"


class RunspacePlugin:
    id: str = PLUGIN_ID
    name: str = "Runspace"
    description: str = (
        "Agent-driven skill export and a Store Agent chat, powered by the "
        "Runspace daemon (runspace-srv). The browser talks to runspace-srv; "
        "the store only assembles request payloads."
    )
    prefix: str = ""
    requires_restart: bool = False

    def __init__(self) -> None:
        self._router: APIRouter | None = None
        self._app_settings_provider = None

    def bind_app(self, app) -> None:
        """Called by the server before mount so the plugin can read app state."""
        self._app_settings_provider = lambda: getattr(app, "settings", None)

    @property
    def router(self) -> APIRouter:
        if self._router is None:
            provider = self._app_settings_provider or (lambda: None)
            self._router = build_router(provider)
        return self._router

    @property
    def ui_manifest(self) -> UIManifest:
        return UIManifest(
            routes=[
                {"path": "/runspace", "component": "runspace.RunspacePage"},
            ],
            nav_items=[
                {"id": "runspace", "label": "Runspace", "path": "/runspace"},
            ],
            slots={
                "skill.detail.actions": [
                    {"component": "runspace.ExportWithAgentAction"},
                ],
            },
        )

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass


__all__ = ["RunspacePlugin", "PLUGIN_ID"]
