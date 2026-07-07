"""SSE /events/stream endpoint — plugin subscribers use this to receive events."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import FastAPI, Header, Query, Request
from sse_starlette.sse import EventSourceResponse

from skillberry_store.plugins.sse_hub import get_hub

logger = logging.getLogger(__name__)


def register_events_api(app: FastAPI, tags: str = "events") -> None:
    @app.get("/events/stream", tags=[tags], summary="SSE event stream for plugins")
    async def events_stream(
        request: Request,
        topics: Optional[str] = Query(
            None, description="Comma-separated topic patterns"
        ),
        last_event_id_header: Optional[str] = Header(None, alias="Last-Event-ID"),
    ):
        topic_tuple = (
            tuple(t.strip() for t in topics.split(",") if t.strip()) if topics else ()
        )

        last_id_int: Optional[int] = None
        if last_event_id_header:
            try:
                last_id_int = int(last_event_id_header)
            except ValueError:
                last_id_int = None

        hub = get_hub()

        async def event_iterator():
            subscription = hub.subscribe(topics=topic_tuple, last_event_id=last_id_int)
            try:
                async for event in subscription:
                    if await request.is_disconnected():
                        break
                    payload = event.data
                    if not isinstance(payload, str):
                        payload = json.dumps(payload, default=str)
                    yield {
                        "event": event.topic,
                        "id": str(event.id),
                        "data": payload,
                    }
            except asyncio.CancelledError:
                raise
            finally:
                subscription.close()

        return EventSourceResponse(event_iterator())
