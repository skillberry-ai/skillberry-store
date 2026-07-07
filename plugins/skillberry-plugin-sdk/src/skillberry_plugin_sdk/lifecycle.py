"""PluginLifecycleBase — base FastAPI plugin process exposing /lifecycle/*."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, FastAPI

from skillberry_plugin_sdk.decorators import get_event_handlers
from skillberry_plugin_sdk.events import EventsClient
from skillberry_plugin_sdk.manifest import PluginManifest, load_manifest
from skillberry_plugin_sdk.store import StoreClient, get_store_client

logger = logging.getLogger(__name__)


class PluginLifecycleBase:
    """Base class for out-of-process plugins.

    Subclasses set ``manifest_path`` (relative to their module) and optionally
    override ``on_start``, ``on_stop``, ``is_ready``, or ``get_router``.
    """

    manifest_path: str = "manifest.yaml"

    def __init__(self, manifest: Optional[PluginManifest] = None) -> None:
        self._manifest = manifest
        self._store: Optional[StoreClient] = None
        self._events: Optional[EventsClient] = None
        self._events_task: Optional[asyncio.Task] = None
        self._shutdown_event: Optional[asyncio.Event] = None

    # Configuration hooks ---------------------------------------------------

    @property
    def manifest(self) -> PluginManifest:
        if self._manifest is None:
            self._manifest = self._load_default_manifest()
        return self._manifest

    def _load_default_manifest(self) -> PluginManifest:
        import sys
        module = sys.modules.get(type(self).__module__)
        base_dir: Path
        if module is not None and getattr(module, "__file__", None):
            base_dir = Path(module.__file__).resolve().parent
        else:
            base_dir = Path.cwd()
        return load_manifest(base_dir / self.manifest_path)

    @property
    def store(self) -> StoreClient:
        if self._store is None:
            raise RuntimeError("StoreClient not initialised — on_start not yet called")
        return self._store

    @property
    def events(self) -> EventsClient:
        if self._events is None:
            raise RuntimeError("EventsClient not initialised — on_start not yet called")
        return self._events

    # Extension points ------------------------------------------------------

    async def on_start(self) -> None:
        """Override to run plugin-specific startup (LLM clients, etc.)."""
        return None

    async def on_stop(self) -> None:
        """Override to run plugin-specific teardown."""
        return None

    async def is_ready(self) -> Dict[str, Any]:
        """Override to expose readiness (defaults to always-ready)."""
        return {"ready": True, "missing_config": []}

    def get_router(self) -> Optional[APIRouter]:
        """Override to add plugin-specific REST endpoints under ``/plugins/<slug>/``."""
        return None

    # Wiring ---------------------------------------------------------------

    def _build_events_client(self) -> Optional[EventsClient]:
        base = os.environ.get("SKILLBERRY_EVENTS_URL") or os.environ.get(
            "SKILLBERRY_STORE_URL", "http://127.0.0.1:8000"
        )
        token = os.environ.get("SKILLBERRY_STORE_TOKEN") or None
        return EventsClient(base, token=token)

    async def _start_event_subscriber(self) -> None:
        handlers = get_event_handlers(self)
        if not handlers:
            return
        assert self._events is not None
        topics = list(handlers.keys())

        async def dispatch(event) -> None:
            for handler in handlers.get(event.topic, []):
                await handler(event)

        loop = asyncio.get_running_loop()
        self._events_task = loop.create_task(
            self._events.subscribe(topics, dispatch),
            name=f"plugin-events-{self.manifest.slug}",
        )

    async def _startup(self) -> None:
        self._shutdown_event = asyncio.Event()
        self._store = get_store_client()
        self._events = self._build_events_client()
        await self.on_start()
        await self._start_event_subscriber()

    async def _shutdown(self) -> None:
        try:
            await self.on_stop()
        finally:
            if self._events is not None:
                self._events.stop()
            if self._events_task is not None:
                self._events_task.cancel()
                try:
                    await self._events_task
                except (asyncio.CancelledError, Exception):
                    pass
            if self._shutdown_event is not None:
                self._shutdown_event.set()

    def build_app(self) -> FastAPI:
        """Construct the FastAPI app used by the runner (also useful for tests)."""
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def lifespan(app):  # type: ignore[no-redef]
            await self._startup()
            try:
                yield
            finally:
                await self._shutdown()

        app = FastAPI(title=f"skillberry-plugin-{self.manifest.slug}", lifespan=lifespan)

        lifecycle_router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])

        @lifecycle_router.get("/health")
        async def _health() -> Dict[str, str]:
            return {"status": "ok"}

        @lifecycle_router.get("/info")
        async def _info() -> Dict[str, Any]:
            return self.manifest.model_dump()

        @lifecycle_router.get("/ready")
        async def _ready() -> Dict[str, Any]:
            return await self.is_ready()

        @lifecycle_router.post("/shutdown")
        async def _shutdown_ep() -> Dict[str, str]:
            await self._shutdown()
            return {"status": "stopping"}

        app.include_router(lifecycle_router)

        router = self.get_router()
        if router is not None:
            app.include_router(router)

        return app

    # Env validation --------------------------------------------------------

    def validate_env(self, env: Optional[Dict[str, str]] = None) -> List[str]:
        """Return the list of required env vars missing from *env* (or os.environ)."""
        env = env if env is not None else dict(os.environ)
        return self.manifest.missing_env(env)
