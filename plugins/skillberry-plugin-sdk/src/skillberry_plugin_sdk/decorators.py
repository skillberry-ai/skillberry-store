"""Event handler decorators for plugin classes."""

from __future__ import annotations

from typing import Callable

_ON_EVENT_ATTR = "_sbs_plugin_event_topics"


def on_event(topic: str) -> Callable:
    """Register a method as a handler for SSE topic(s).

    Usage:
        class MyPlugin(PluginLifecycleBase):
            @on_event("content.skill.added")
            async def on_new_skill(self, event):
                ...
    """
    def decorator(func: Callable) -> Callable:
        topics = getattr(func, _ON_EVENT_ATTR, None)
        if topics is None:
            topics = []
            setattr(func, _ON_EVENT_ATTR, topics)
        topics.append(topic)
        return func

    return decorator


def get_event_handlers(obj) -> dict:
    """Collect all @on_event handlers on *obj* → {topic: [bound_method,...]}."""
    handlers: dict = {}
    for attr_name in dir(obj):
        # Skip private helpers and descriptor lookups that could raise.
        if attr_name.startswith("__"):
            continue
        try:
            member = getattr(obj, attr_name)
        except Exception:
            continue
        topics = getattr(member, _ON_EVENT_ATTR, None)
        if not topics:
            continue
        for topic in topics:
            handlers.setdefault(topic, []).append(member)
    return handlers
