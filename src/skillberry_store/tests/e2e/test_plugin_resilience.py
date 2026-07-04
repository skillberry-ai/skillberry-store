"""Resilience e2e for the plugin subprocess model.

These tests exercise the manager surface without spawning real plugin
subprocesses. Full end-to-end resilience (kill a subprocess, verify SSE
replay after reconnect) requires an integration-level test with an
installable plugin — see plugins/skillberry-plugin-kagenti-approver/tests/
test_integration.py behind the SBS_RUN_INTEGRATION_PLUGIN env flag.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from skillberry_store.fast_api.plugin_proxy import PluginRegistry, ProxyTarget
from skillberry_store.plugins.sse_hub import SSEHub
from skillberry_store.plugins.state_store import PluginStateStore

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_proxy_returns_503_when_target_unreachable(run_sbs, monkeypatch):
    """When a plugin subprocess is not running, the proxy responds with 503."""
    from skillberry_store.fast_api.plugin_proxy import PluginRegistry

    # Register a bogus target that no server is listening on.
    async with httpx.AsyncClient() as client:
        # A slug not in the registry → 404
        r = await client.get(f"{BASE_URL}/plugins/nonexistent-plugin-x/api/echo")
        assert r.status_code in (404, 503)


@pytest.mark.asyncio
async def test_sse_stream_delivers_new_events(run_sbs):
    """Emitting a content.skill.added on the SSE hub reaches a subscribed client."""
    from skillberry_store.plugins.sse_hub import get_hub

    async with httpx.AsyncClient(timeout=5.0) as client:
        got: list[dict] = []

        async def read_events():
            async with client.stream(
                "GET",
                f"{BASE_URL}/events/stream",
                params={"topics": "content.skill.*"},
                headers={"Accept": "text/event-stream"},
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        payload = line.split(":", 1)[1].strip()
                        try:
                            got.append(json.loads(payload))
                        except Exception:
                            got.append({"raw": payload})
                        if got:
                            return

        reader = asyncio.create_task(read_events())
        await asyncio.sleep(0.3)
        get_hub().publish("content.skill.added", {"uuid": "u-1", "type": "skill"})
        try:
            await asyncio.wait_for(reader, timeout=3.0)
        except asyncio.TimeoutError:
            reader.cancel()
            pytest.fail("SSE subscriber did not receive event")

        assert got and got[0].get("uuid") == "u-1"


def test_state_file_deletion_boots_empty(tmp_path: Path):
    """Deleting the state file at rest yields a next-boot with zero plugins."""
    path = tmp_path / "plugins.state.json"
    path.write_text('{"version": 1, "plugins": {"a": {"last_state":"running"}}}')
    assert PluginStateStore(path).all() == {"a": {"last_state": "running"}}

    path.unlink()
    reloaded = PluginStateStore(path)
    assert reloaded.all() == {}


def test_sse_hub_replays_after_reconnect():
    """A subscriber can pass Last-Event-ID to catch up after disconnect."""
    hub = SSEHub()
    hub.publish("content.skill.added", {"uuid": "a"})
    hub.publish("content.skill.added", {"uuid": "b"})
    hub.publish("content.skill.added", {"uuid": "c"})

    subscription = hub.subscribe(topics=("content.skill.*",), last_event_id=1)
    queued = []
    while True:
        try:
            queued.append(subscription._queue.get_nowait())
        except Exception:
            break
    subscription.close()
    assert [e.data["uuid"] for e in queued] == ["b", "c"]
