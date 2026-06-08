"""Event system for plugin hooks.

Plugins can register handlers for content lifecycle events (added, updated, deleted).
The store emits these events when content changes occur.
"""

import asyncio
from typing import Callable, Dict, List
import logging

logger = logging.getLogger(__name__)

# Global registry of event handlers
_event_handlers: Dict[str, List[Callable]] = {}

# Holds strong references to background tasks so they are not garbage-collected
# before they complete.
_background_tasks: set = set()


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

    Args:
        event_name: Name of the event (e.g., "content_added:tool")
        **kwargs: Arguments to pass to event handlers
    """
    handlers = _event_handlers.get(event_name, [])
    for handler in handlers:
        task = asyncio.create_task(_run_handler(handler, **kwargs))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)


def emit_content_added(content_type: str, uuid: str):
    """Convenience function to emit content_added event.

    Args:
        content_type: Type of content (tool, skill, snippet, etc.)
        uuid: UUID of the added content
    """
    emit_event(f"content_added:{content_type}", uuid=uuid)


def emit_content_updated(content_type: str, uuid: str):
    """Convenience function to emit content_updated event.

    Args:
        content_type: Type of content (tool, skill, snippet, etc.)
        uuid: UUID of the updated content
    """
    emit_event(f"content_updated:{content_type}", uuid=uuid)


def emit_content_deleted(content_type: str, uuid: str):
    """Convenience function to emit content_deleted event.

    Args:
        content_type: Type of content (tool, skill, snippet, etc.)
        uuid: UUID of the deleted content
    """
    emit_event(f"content_deleted:{content_type}", uuid=uuid)

# Made with Bob
