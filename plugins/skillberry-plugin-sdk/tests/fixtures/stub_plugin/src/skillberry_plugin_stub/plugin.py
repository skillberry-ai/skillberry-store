"""Stub plugin — echoes an event count via /api/count."""

from fastapi import APIRouter

from skillberry_plugin_sdk import PluginLifecycleBase, on_event


class StubPlugin(PluginLifecycleBase):
    manifest_path = "manifest.yaml"

    def __init__(self) -> None:
        super().__init__()
        self._counter = 0

    @on_event("content.skill.added")
    async def on_skill_added(self, event) -> None:
        self._counter += 1

    def get_router(self):
        router = APIRouter()

        @router.get("/api/count")
        async def count():
            return {"count": self._counter}

        return router
