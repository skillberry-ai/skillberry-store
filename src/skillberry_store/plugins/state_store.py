"""Persistent state store for installed plugins.

Records every installed plugin in a JSON file at the repo root (path overridable
via ``SKILLBERRY_PLUGIN_STATE_FILE``). Setting the env var to an empty string
disables persistence entirely — the tests boot SBS this way so pytest sessions
never write to a shared file.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DEFAULT_STATE_FILE = "plugins.state.json"
_STATE_VERSION = 1


class PluginStateStore:
    """Reads/writes the plugin state file, or holds it in memory when disabled."""

    def __init__(self, path: Optional[str | Path] = None) -> None:
        self._path: Optional[Path]
        self._in_memory = False

        raw_path = path if path is not None else os.environ.get("SKILLBERRY_PLUGIN_STATE_FILE")
        if raw_path is None:
            self._path = Path.cwd() / _DEFAULT_STATE_FILE
        elif str(raw_path) == "":
            self._path = None
            self._in_memory = True
        else:
            self._path = Path(raw_path)

        self._data: Dict[str, Any] = {"version": _STATE_VERSION, "plugins": {}}
        self.load()

    @property
    def path(self) -> Optional[Path]:
        return self._path

    @property
    def persistent(self) -> bool:
        return not self._in_memory

    def load(self) -> None:
        if self._in_memory or self._path is None:
            return
        try:
            raw = self._path.read_text()
        except FileNotFoundError:
            self._data = {"version": _STATE_VERSION, "plugins": {}}
            return
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("plugin state file %s is corrupt: %s; starting empty", self._path, e)
            self._data = {"version": _STATE_VERSION, "plugins": {}}
            return
        if not isinstance(parsed, dict) or "plugins" not in parsed:
            logger.warning("plugin state file %s has unexpected shape; starting empty", self._path)
            self._data = {"version": _STATE_VERSION, "plugins": {}}
            return
        parsed.setdefault("version", _STATE_VERSION)
        parsed.setdefault("plugins", {})
        self._data = parsed

    def all(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._data.get("plugins", {}))

    def get(self, slug: str) -> Optional[Dict[str, Any]]:
        return self._data.get("plugins", {}).get(slug)

    def upsert(self, slug: str, entry: Dict[str, Any]) -> None:
        self._data.setdefault("plugins", {})[slug] = entry
        self._save()

    def update(self, slug: str, **fields: Any) -> None:
        current = self._data.setdefault("plugins", {}).get(slug)
        if current is None:
            return
        current.update(fields)
        self._save()

    def delete(self, slug: str) -> None:
        self._data.setdefault("plugins", {}).pop(slug, None)
        self._save()

    def _save(self) -> None:
        if self._in_memory or self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning("Cannot create parent dir for state file %s: %s", self._path, e)
            return
        tmp = self._path.with_name(self._path.name + ".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, sort_keys=True))
        os.replace(tmp, self._path)
