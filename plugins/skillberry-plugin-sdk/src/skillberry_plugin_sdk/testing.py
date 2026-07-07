"""Pytest helpers for plugin authors."""

from __future__ import annotations

from typing import Any, Dict

from fastapi.testclient import TestClient

from skillberry_plugin_sdk.lifecycle import PluginLifecycleBase


def make_test_client(plugin: PluginLifecycleBase) -> TestClient:
    """Build a FastAPI TestClient around a plugin instance's app."""
    return TestClient(plugin.build_app())


def dummy_event(topic: str, data: Dict[str, Any] | None = None):
    """Build an Event-like object for hand-calling handlers in tests."""
    from skillberry_plugin_sdk.events import Event

    return Event(topic=topic, id="0", data=data or {})
