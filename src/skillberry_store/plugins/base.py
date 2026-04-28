"""Plugin protocol and activation-file management.

Plugins are self-describing add-ons that contribute a FastAPI router and a
UI manifest. The main codebase never references any individual plugin by
name; it iterates the registry instead.

Activation state lives in `$SBS_BASE_DIR/plugins/enabled.json`. Each plugin
may also use `$SBS_BASE_DIR/plugins/<plugin_id>/` for its own settings.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

from fastapi import APIRouter, FastAPI

from skillberry_store.tools.configure import (
    get_plugin_directory,
    get_plugins_directory,
)

logger = logging.getLogger(__name__)

_ENABLED_FILE_NAME = "enabled.json"


@dataclass
class UIManifest:
    """Serialized description of a plugin's UI contributions.

    Consumed by the browser via `GET /plugins`. All paths are relative to
    the SPA root; component identifiers are strings resolved by the UI
    registry.
    """

    routes: List[Dict[str, str]] = field(default_factory=list)
    nav_items: List[Dict[str, str]] = field(default_factory=list)
    slots: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "routes": self.routes,
            "nav_items": self.nav_items,
            "slots": self.slots,
        }


class Plugin(Protocol):
    id: str
    name: str
    description: str
    prefix: str
    requires_restart: bool
    router: APIRouter
    ui_manifest: UIManifest

    def on_enable(self) -> None: ...
    def on_disable(self) -> None: ...


def read_enabled() -> List[str]:
    """Return the list of enabled plugin ids from enabled.json.

    Missing or malformed files are treated as an empty list (opt-in default).
    """
    path = os.path.join(get_plugins_directory(), _ENABLED_FILE_NAME)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        enabled = data.get("enabled", [])
        if isinstance(enabled, list):
            return [str(x) for x in enabled]
    except Exception as e:
        logger.warning(f"Failed to read {path}: {e}")
    return []


def write_enabled(enabled: List[str]) -> None:
    plugins_dir = get_plugins_directory()
    os.makedirs(plugins_dir, exist_ok=True)
    path = os.path.join(plugins_dir, _ENABLED_FILE_NAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"enabled": list(enabled)}, f, indent=2)


def ensure_plugin_directory(plugin_id: str) -> str:
    path = get_plugin_directory(plugin_id)
    os.makedirs(path, exist_ok=True)
    return path


def mount_plugin(app: FastAPI, plugin: Plugin) -> None:
    """Include a plugin's router on the live app."""
    app.include_router(plugin.router, prefix=plugin.prefix, tags=[plugin.name])
    try:
        plugin.on_enable()
    except Exception as e:
        logger.warning(f"Plugin '{plugin.id}' on_enable hook failed: {e}")
    # Force OpenAPI schema regeneration so newly-mounted routes show up.
    app.openapi_schema = None


def unmount_plugin(app: FastAPI, plugin: Plugin) -> None:
    """Remove a plugin's routes from the live app.

    Filters `app.router.routes` in place, dropping any route whose path
    begins with the plugin's prefix. If the prefix is empty, drops routes
    whose tags include the plugin's name.
    """
    prefix = plugin.prefix or ""
    removed = 0
    keep = []
    for route in list(app.router.routes):
        path = getattr(route, "path", "")
        tags = getattr(route, "tags", []) or []
        matches = False
        if prefix:
            if path.startswith(prefix):
                matches = True
        else:
            if plugin.name in tags:
                matches = True
        if matches:
            removed += 1
            continue
        keep.append(route)
    app.router.routes = keep
    logger.info(f"Unmounted plugin '{plugin.id}' ({removed} routes removed)")
    try:
        plugin.on_disable()
    except Exception as e:
        logger.warning(f"Plugin '{plugin.id}' on_disable hook failed: {e}")
    app.openapi_schema = None
