"""StoreAPI-backed tool source for the benign vMCP twin.

Implements the store's ``ToolSource`` protocol using nothing but the sanctioned
plugin API, so the twin resolves manifests and executes tools **through
StoreAPI** rather than reaching into store internals.

Execution delegates to ``StoreAPI.execute_tool``, i.e. the store's own
execution path — which is what a *faithful* twin wants: the skill's tools run
exactly as they would in production, dependency closure and all, rather than
through a bundle this plugin assembled itself.

One deliberate difference from the in-process path: the store re-resolves the
tool by uuid at execution time, so the twin does not get the in-process path's
"pinned manifest" protection against a tool's JSON being overwritten mid-flight.
That is acceptable for a short-lived scan over a known tool set.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class StoreApiToolSource:
    """Resolve and execute tools via ``StoreAPI`` only."""

    def __init__(self, store: Any):
        self._store = store

    def get_manifest(self, uuid: str) -> Dict[str, Any]:
        """Full manifest for ``uuid``.

        Raises:
            KeyError: If the store has no such tool — the server treats this as
                "skip this tool" rather than a fatal error.
        """
        manifest = self._store.get_tool(uuid)
        if not manifest:
            raise KeyError(f"tool {uuid} not found in store")
        return manifest

    async def execute(
        self, manifest: Dict[str, Any], parameters: Dict[str, Any], env_id: str
    ) -> Dict[str, Any]:
        """Run the tool through the store's own execution path."""
        uuid = manifest.get("uuid")
        if not uuid:
            raise ValueError(f"manifest for {manifest.get('name')!r} has no uuid")
        return await self._store.execute_tool(uuid, parameters, env_id=env_id)
