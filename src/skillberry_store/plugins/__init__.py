"""Plugin registry.

`INSTALLED` is the hand-maintained list of plugins shipped with the store.
Enabling/disabling is controlled at runtime via `plugins/enabled.json` and
the `/plugins/{id}/enable|disable` admin endpoints.

Main code must never branch on a plugin id. Use `active_plugins()` or
`installed_plugins()` and iterate.
"""

from __future__ import annotations

from typing import List, Optional

from .base import (
    Plugin,
    UIManifest,
    read_enabled,
    write_enabled,
    mount_plugin,
    unmount_plugin,
    ensure_plugin_directory,
)
from .runspace import RunspacePlugin


INSTALLED: List[Plugin] = [RunspacePlugin()]


def installed_plugins() -> List[Plugin]:
    return list(INSTALLED)


def get_plugin(plugin_id: str) -> Optional[Plugin]:
    for p in INSTALLED:
        if p.id == plugin_id:
            return p
    return None


def active_plugins() -> List[Plugin]:
    enabled = set(read_enabled())
    return [p for p in INSTALLED if p.id in enabled]


def is_enabled(plugin_id: str) -> bool:
    return plugin_id in set(read_enabled())


def set_enabled(plugin_id: str, enabled: bool) -> List[str]:
    current = read_enabled()
    if enabled and plugin_id not in current:
        current.append(plugin_id)
    elif not enabled and plugin_id in current:
        current = [x for x in current if x != plugin_id]
    write_enabled(current)
    return current


__all__ = [
    "Plugin",
    "UIManifest",
    "INSTALLED",
    "installed_plugins",
    "get_plugin",
    "active_plugins",
    "is_enabled",
    "set_enabled",
    "mount_plugin",
    "unmount_plugin",
    "read_enabled",
    "write_enabled",
    "ensure_plugin_directory",
]
