"""Event system for plugin hooks.

Plugins can register handlers for content lifecycle events (added, updated, deleted).
The store emits these events when content changes occur.
"""

from typing import Callable, Dict, List
import logging

logger = logging.getLogger(__name__)

# Global registry of event handlers
_event_handlers: Dict[str, List[Callable]] = {}


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


async def emit_event(event_name: str, **kwargs):
    """Emit an event to all registered handlers.
    
    Called by store when content lifecycle events occur.
    Handlers are called in registration order. If a handler fails,
    the error is logged but other handlers continue to execute.
    
    Args:
        event_name: Name of the event (e.g., "content_added:tool")
        **kwargs: Arguments to pass to event handlers
    """
    handlers = _event_handlers.get(event_name, [])
    for handler in handlers:
        try:
            await handler(**kwargs)
        except Exception as e:
            logger.error(f"Event handler failed for {event_name}: {e}", exc_info=True)


async def emit_content_added(content_type: str, uuid: str):
    """Convenience function to emit content_added event.
    
    Args:
        content_type: Type of content (tool, skill, snippet, etc.)
        uuid: UUID of the added content
    """
    await emit_event(f"content_added:{content_type}", uuid=uuid)


async def emit_content_updated(content_type: str, uuid: str):
    """Convenience function to emit content_updated event.
    
    Args:
        content_type: Type of content (tool, skill, snippet, etc.)
        uuid: UUID of the updated content
    """
    await emit_event(f"content_updated:{content_type}", uuid=uuid)


async def emit_content_deleted(content_type: str, uuid: str):
    """Convenience function to emit content_deleted event.
    
    Args:
        content_type: Type of content (tool, skill, snippet, etc.)
        uuid: UUID of the deleted content
    """
    await emit_event(f"content_deleted:{content_type}", uuid=uuid)

# Made with Bob
