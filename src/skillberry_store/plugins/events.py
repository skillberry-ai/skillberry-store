"""Event system for plugin hooks.

Plugins can register handlers for content lifecycle events (added, updated, deleted).
The store emits these events when content changes occur.
"""

import asyncio
from typing import Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Global registry of event handlers
_event_handlers: Dict[str, List[Callable]] = {}

# Holds strong references to background tasks so they are not garbage-collected
# before they complete.
_background_tasks: set = set()

# Maps each registered handler callable to the slug of the plugin that owns it.
# Populated by the plugin loader via register_handler_owner(); plugins themselves
# are unchanged. A handler with no recorded owner always runs.
_handler_owners: Dict[Callable, str] = {}

# Optional resolver injected by the loader: slug -> bool (is the plugin enabled?).
# When None, every handler runs (default-on / backward compatible).
_enabled_resolver: Optional[Callable[[str], bool]] = None


def register_handler_owner(func: Callable, slug: str) -> None:
    """Record which plugin owns a handler callable (called by the loader)."""
    _handler_owners[func] = slug


def set_enabled_resolver(resolver: Optional[Callable[[str], bool]]) -> None:
    """Inject the loader's 'is this plugin enabled?' resolver (or None to clear)."""
    global _enabled_resolver
    _enabled_resolver = resolver


def on_content_added(content_type: str):
    """Decorator to register handler for content addition events.

    Usage in plugin:
        @on_content_added("tool")
        async def handle_new_tool(uuid: str):
            # Process new tool
            pass

    Args:
        content_type: Type of content (tool, skill, snippet, etc.)
    """
    def decorator(func: Callable):
        event_name = f"content_added:{content_type}"
        if event_name not in _event_handlers:
            _event_handlers[event_name] = []
        _event_handlers[event_name].append(func)
        return func
    return decorator


def on_content_updated(content_type: str):
    """Decorator to register handler for content update events.

    Usage in plugin:
        @on_content_updated("tool")
        async def handle_tool_update(uuid: str):
            # Process tool update
            pass

    Args:
        content_type: Type of content (tool, skill, snippet, etc.)
    """
    def decorator(func: Callable):
        event_name = f"content_updated:{content_type}"
        if event_name not in _event_handlers:
            _event_handlers[event_name] = []
        _event_handlers[event_name].append(func)
        return func
    return decorator


def on_content_deleted(content_type: str):
    """Decorator to register handler for content deletion events.

    Usage in plugin:
        @on_content_deleted("tool")
        async def handle_tool_deletion(uuid: str):
            # Process tool deletion
            pass

    Args:
        content_type: Type of content (tool, skill, snippet, etc.)
    """
    def decorator(func: Callable):
        event_name = f"content_deleted:{content_type}"
        if event_name not in _event_handlers:
            _event_handlers[event_name] = []
        _event_handlers[event_name].append(func)
        return func
    return decorator


async def _run_handler(handler: Callable, **kwargs):
    """Run a single handler, logging any exception without propagating it."""
    try:
        await handler(**kwargs)
    except Exception as e:
        logger.error(f"Event handler failed for handler {handler.__name__}: {e}", exc_info=True)


def emit_event(event_name: str, **kwargs):
    """Schedule all registered handlers for an event as background tasks.

    Returns immediately. Handlers run concurrently on the running event loop.
    If a handler raises, the error is logged and other handlers still run.

    When no event loop is running (e.g., a synchronous caller from a unit test
    or CLI), handlers are skipped silently — they are fire-and-forget by design.

    Args:
        event_name: Name of the event (e.g., "content_added:tool")
        **kwargs: Arguments to pass to event handlers
    """
    handlers = _event_handlers.get(event_name, [])
    if not handlers:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.debug(
            f"emit_event({event_name!r}): no running event loop, "
            f"skipping {len(handlers)} handler(s)"
        )
        return
    for handler in handlers:
        owner = _handler_owners.get(handler)
        if owner is not None and _enabled_resolver is not None and not _enabled_resolver(owner):
            continue
        task = loop.create_task(_run_handler(handler, **kwargs))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)


def _publish_to_sse(topic: str, payload: Dict[str, str]) -> None:
    """Publish an event to the SSE hub, tolerating failures silently."""
    try:
        from skillberry_store.plugins.sse_hub import get_hub

        get_hub().publish(topic, payload)
    except Exception:  # pragma: no cover - defensive
        logger.debug("SSE publish failed", exc_info=True)


def emit_content_added(content_type: str, uuid: str):
    """Convenience function to emit content_added event.

    Also publishes ``content.<type>.added`` on the SSE hub for out-of-process
    plugin subscribers.
    """
    emit_event(f"content_added:{content_type}", uuid=uuid)
    _publish_to_sse(f"content.{content_type}.added", {"uuid": uuid, "type": content_type})


def emit_content_updated(content_type: str, uuid: str):
    """Convenience function to emit content_updated event.

    Also publishes ``content.<type>.updated`` on the SSE hub.
    """
    emit_event(f"content_updated:{content_type}", uuid=uuid)
    _publish_to_sse(f"content.{content_type}.updated", {"uuid": uuid, "type": content_type})


def emit_content_deleted(content_type: str, uuid: str):
    """Convenience function to emit content_deleted event.

    Also publishes ``content.<type>.deleted`` on the SSE hub.
    """
    emit_event(f"content_deleted:{content_type}", uuid=uuid)
    _publish_to_sse(f"content.{content_type}.deleted", {"uuid": uuid, "type": content_type})

# Made with Bob
