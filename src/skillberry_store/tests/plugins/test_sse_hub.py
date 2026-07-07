"""Tests for the in-process SSE hub."""

import asyncio

import pytest

from skillberry_store.plugins.sse_hub import SSEHub, _topic_matches


def test_topic_wildcards() -> None:
    assert _topic_matches("content.skill.*", "content.skill.added") is True
    assert _topic_matches("content.skill.added", "content.skill.added") is True
    assert _topic_matches("content.*.added", "content.tool.added") is True
    assert _topic_matches("content.*.added", "content.tool.deleted") is False
    assert _topic_matches("**", "anything.at.all") is True
    assert _topic_matches("content.**", "content.tool.deleted") is True


@pytest.mark.asyncio
async def test_publish_delivers_to_subscribers() -> None:
    hub = SSEHub()
    sub = hub.subscribe(topics=("content.skill.*",))
    hub.publish("content.skill.added", {"uuid": "1"})
    hub.publish("content.tool.added", {"uuid": "2"})
    hub.publish("content.skill.updated", {"uuid": "3"})

    received = []
    async for event in sub:
        received.append(event)
        if len(received) == 2:
            break
    assert [e.data["uuid"] for e in received] == ["1", "3"]
    sub.close()


@pytest.mark.asyncio
async def test_replay_from_last_event_id() -> None:
    hub = SSEHub()
    hub.publish("content.skill.added", {"uuid": "a"})
    hub.publish("content.skill.added", {"uuid": "b"})
    hub.publish("content.skill.added", {"uuid": "c"})

    sub = hub.subscribe(topics=(), last_event_id=1)
    received = []
    async for event in sub:
        received.append(event)
        if len(received) == 2:
            break
    assert [e.data["uuid"] for e in received] == ["b", "c"]


@pytest.mark.asyncio
async def test_slow_consumer_evicted() -> None:
    hub = SSEHub(queue_maxsize=2)
    sub = hub.subscribe(topics=())
    hub.publish("a", {"i": 1})
    hub.publish("a", {"i": 2})
    hub.publish("a", {"i": 3})  # queue full, subscriber evicted
    assert hub.subscriber_count() == 0
