"""In-memory pub/sub for SSE event streaming.

Design:
- Publishers call ``publish(topic, data)``; every subscribed client receives a copy
  through its own bounded ``asyncio.Queue``.
- Each event carries a monotonically increasing ``id`` (per-hub) so a reconnecting
  subscriber can pass ``last_event_id`` to replay the tail of a ring buffer.
- Slow subscribers (queue full) are evicted; they can reconnect and replay from
  ``Last-Event-ID`` up to the ring-buffer size.
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class HubEvent:
    id: int
    topic: str
    data: Any


def _topic_matches(pattern: str, topic: str) -> bool:
    if pattern in ("", "*", "**"):
        return True
    # dot-segment wildcards: * matches one segment; ** matches many.
    p_parts = pattern.split(".")
    t_parts = topic.split(".")
    return _match(p_parts, t_parts)


def _match(pp: List[str], tp: List[str]) -> bool:
    if not pp and not tp:
        return True
    if not pp:
        return False
    if pp[0] == "**":
        if len(pp) == 1:
            return True
        for i in range(len(tp) + 1):
            if _match(pp[1:], tp[i:]):
                return True
        return False
    if not tp:
        return False
    if pp[0] == "*" or fnmatch.fnmatchcase(tp[0], pp[0]):
        return _match(pp[1:], tp[1:])
    return False


class SSEHub:
    """Per-process publish/subscribe bus for SSE events."""

    def __init__(self, buffer_size: int = 1000, queue_maxsize: int = 5000) -> None:
        self._buffer: Deque[HubEvent] = deque(maxlen=buffer_size)
        self._queue_maxsize = queue_maxsize
        self._next_id = 1
        self._subscribers: Dict[int, Tuple[asyncio.Queue, Tuple[str, ...]]] = {}
        self._sub_id = 0
        self._lock = asyncio.Lock()

    def publish(self, topic: str, data: Any) -> HubEvent:
        """Publish an event to all matching subscribers.

        Safe to call from any thread that has an event loop reference; here it just
        appends to the ring buffer and pushes to each subscriber queue.
        """
        event = HubEvent(id=self._next_id, topic=topic, data=data)
        self._next_id += 1
        self._buffer.append(event)
        evict: List[int] = []
        for sub_id, (queue, topics) in self._subscribers.items():
            if topics and not any(_topic_matches(t, topic) for t in topics):
                continue
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("SSE subscriber %s slow — evicting", sub_id)
                evict.append(sub_id)
        for sub_id in evict:
            self._subscribers.pop(sub_id, None)
        return event

    def _replay(self, last_id: Optional[int], topics: Tuple[str, ...]) -> List[HubEvent]:
        if last_id is None:
            return []
        out: List[HubEvent] = []
        for ev in self._buffer:
            if ev.id <= last_id:
                continue
            if topics and not any(_topic_matches(t, ev.topic) for t in topics):
                continue
            out.append(ev)
        return out

    def subscribe(
        self, topics: Tuple[str, ...] = (), last_event_id: Optional[int] = None
    ) -> "SSESubscription":
        self._sub_id += 1
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._queue_maxsize)
        for ev in self._replay(last_event_id, topics):
            try:
                queue.put_nowait(ev)
            except asyncio.QueueFull:
                break
        self._subscribers[self._sub_id] = (queue, topics)
        return SSESubscription(hub=self, sub_id=self._sub_id, queue=queue)

    def unsubscribe(self, sub_id: int) -> None:
        self._subscribers.pop(sub_id, None)

    def subscriber_count(self) -> int:
        return len(self._subscribers)


class SSESubscription:
    """A subscription handle; iterate to consume events."""

    def __init__(self, hub: SSEHub, sub_id: int, queue: asyncio.Queue) -> None:
        self._hub = hub
        self._sub_id = sub_id
        self._queue = queue

    async def __aenter__(self) -> "SSESubscription":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self._hub.unsubscribe(self._sub_id)

    async def __aiter__(self):
        try:
            while True:
                event = await self._queue.get()
                yield event
        except asyncio.CancelledError:
            raise

    def close(self) -> None:
        self._hub.unsubscribe(self._sub_id)


# Module-level singleton the SBS server wires up on startup.
_hub: Optional[SSEHub] = None


def get_hub() -> SSEHub:
    global _hub
    if _hub is None:
        _hub = SSEHub()
    return _hub


def reset_hub_for_tests() -> None:
    global _hub
    _hub = SSEHub()
