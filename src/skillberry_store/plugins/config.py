"""Persisted plugin state: enablement, and the owner tenant per plugin.

The config file records only the plugins that have been explicitly DISABLED.
A plugin is enabled unless its slug appears in the ``disabled`` list, so a
missing, empty, or corrupt file means every plugin is enabled.

It also records an ``owners`` map — the tenant a plugin's autonomous work
runs as (plugin-identity §5.1, P1). Plugins are discovered from entry points
and instantiated before any tenant exists, so "the tenant that created it"
has no record to hang on; the closest real one is *the tenant that enabled
it*, which ``PATCH /plugins/{plugin_name}`` writes here::

    {"disabled": ["dedupe"], "owners": {"sast": "team-blue"}}

A plugin with no entry falls back to the deployment-wide owner tenant from
the access-control config, and failing that has no identity at all — at
which point P5 makes its outward calls fail rather than proceed anonymously.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Set, Union

logger = logging.getLogger(__name__)


class PluginConfigStore:
    """Reads/writes the global plugin enable/disable config (JSON on disk)."""

    def __init__(self, path: Optional[Union[str, Path]] = None):
        self.path: Path = Path(path) if path is not None else self._default_path()
        self._disabled: Set[str] = set()
        self._owners: Dict[str, str] = {}
        self.load()

    @staticmethod
    def _default_path() -> Path:
        env = os.getenv("SKILLBERRY_PLUGIN_CONFIG")
        if env:
            return Path(env)
        return Path.home() / ".skillberry" / "plugins.json"

    def load(self) -> None:
        """Load state from disk. Any error -> all enabled, no owners."""
        try:
            data = json.loads(self.path.read_text())
            disabled = data.get("disabled", [])
            self._disabled = {str(s) for s in disabled}
            owners = data.get("owners") or {}
            self._owners = (
                {str(k): str(v) for k, v in owners.items() if v}
                if isinstance(owners, dict)
                else {}
            )
        except FileNotFoundError:
            self._disabled = set()
            self._owners = {}
        except (json.JSONDecodeError, OSError, AttributeError, TypeError) as e:
            logger.warning(
                f"Could not read plugin config at {self.path}: {e}; "
                f"treating all plugins as enabled"
            )
            self._disabled = set()
            self._owners = {}

    def is_enabled(self, slug: str) -> bool:
        """A plugin is enabled unless explicitly recorded as disabled."""
        return slug not in self._disabled

    def set_enabled(self, slug: str, value: bool) -> None:
        """Enable or disable a plugin and persist immediately."""
        if value:
            self._disabled.discard(slug)
        else:
            self._disabled.add(slug)
        self._save()

    def get_owner(self, slug: str) -> Optional[str]:
        """The tenant recorded as this plugin's owner, or ``None``."""
        return self._owners.get(slug)

    def set_owner(self, slug: str, tenant_id: Optional[str]) -> None:
        """Record (or clear) the owner tenant for a plugin and persist."""
        current = self._owners.get(slug)
        if tenant_id:
            if current == tenant_id:
                return
            self._owners[slug] = tenant_id
        else:
            if current is None:
                return
            self._owners.pop(slug, None)
        self._save()

    def owners(self) -> Dict[str, str]:
        """A copy of the whole slug -> owner tenant map."""
        return dict(self._owners)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(
            json.dumps(
                {
                    "disabled": sorted(self._disabled),
                    "owners": dict(sorted(self._owners.items())),
                },
                indent=2,
            )
        )
        os.replace(tmp, self.path)

# Made with Bob
