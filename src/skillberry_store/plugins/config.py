"""Persisted, default-on enable/disable state for plugins.

The config file records only the plugins that have been explicitly DISABLED.
A plugin is enabled unless its slug appears in the ``disabled`` list, so a
missing, empty, or corrupt file means every plugin is enabled.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Set, Union

logger = logging.getLogger(__name__)


class PluginConfigStore:
    """Reads/writes the global plugin enable/disable config (JSON on disk)."""

    def __init__(self, path: Optional[Union[str, Path]] = None):
        self.path: Path = Path(path) if path is not None else self._default_path()
        self._disabled: Set[str] = set()
        self.load()

    @staticmethod
    def _default_path() -> Path:
        env = os.getenv("SKILLBERRY_PLUGIN_CONFIG")
        if env:
            return Path(env)
        return Path.home() / ".skillberry" / "plugins.json"

    def load(self) -> None:
        """Load the disabled set from disk. Any error -> all plugins enabled."""
        try:
            data = json.loads(self.path.read_text())
            disabled = data.get("disabled", [])
            self._disabled = {str(s) for s in disabled}
        except FileNotFoundError:
            self._disabled = set()
        except (json.JSONDecodeError, OSError, AttributeError, TypeError) as e:
            logger.warning(
                f"Could not read plugin config at {self.path}: {e}; "
                f"treating all plugins as enabled"
            )
            self._disabled = set()

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

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(json.dumps({"disabled": sorted(self._disabled)}, indent=2))
        os.replace(tmp, self.path)

# Made with Bob
