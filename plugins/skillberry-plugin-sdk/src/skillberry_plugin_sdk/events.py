"""SSE events client — subscribes to the SBS /events/stream endpoint."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional

import httpx
from httpx_sse import aconnect_sse

logger = logging.getLogger(__name__)


@dataclass
class Event:
    topic: str
    id: str
    data: dict


class EventsClient:
    """Subscribes to SBS SSE events with auto-reconnect + Last-Event-ID replay."""

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        *,
        max_backoff: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.max_backoff = max_backoff
        self._last_event_id: Optional[str] = None
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stop_event.set()

    async def subscribe(
        self,
        topics: List[str],
        handler: Callable[[Event], Awaitable[None]],
        *,
        last_event_id: Optional[str] = None,
    ) -> None:
        """Long-running: connect to SSE, dispatch events, reconnect on failure."""
        if last_event_id is not None:
            self._last_event_id = last_event_id

        backoff = 1.0
        params = {"topics": ",".join(topics)} if topics else {}

        while not self._stop_event.is_set():
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            if self._last_event_id:
                headers["Last-Event-ID"] = self._last_event_id

            url = f"{self.base_url}/events/stream"
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with aconnect_sse(
                        client, "GET", url, params=params, headers=headers
                    ) as sse:
                        backoff = 1.0
                        async for msg in sse.aiter_sse():
                            if self._stop_event.is_set():
                                break
                            if msg.id:
                                self._last_event_id = msg.id
                            topic = msg.event or "message"
                            try:
                                data = json.loads(msg.data) if msg.data else {}
                            except (json.JSONDecodeError, ValueError):
                                data = {"raw": msg.data}
                            try:
                                await handler(Event(topic=topic, id=msg.id or "", data=data))
                            except Exception:
                                logger.exception("Event handler raised")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("SSE subscribe failed: %s; reconnecting in %.1fs", e, backoff)
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=backoff)
                    return
                except asyncio.TimeoutError:
                    pass
                backoff = min(backoff * 2, self.max_backoff)
