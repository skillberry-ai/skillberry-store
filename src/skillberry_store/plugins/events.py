"""Event system for plugin hooks.

Plugins can register handlers for content lifecycle events (added, updated, deleted).
The store emits these events when content changes occur.

The event contract is deliberately actor-free: a handler subscribes to "a
skill was added", not to "tenant X added a skill", and the payload carries a
uuid and nothing else. A triggering tenant is nonetheless *ambiently* present
at handling time, because every emit path today sits inside a request and
``loop.create_task`` copies the caller's context — so trigger-driven work
would inherit the uploader's identity by accident.

Per plugin-identity §1 that is the wrong identity: trigger-driven work runs as
the **owning plugin's owner tenant** (P1), so a scanner's coverage does not
become a function of who uploaded, and a plugin-triggered cascade does not run
plugin B's handler under whatever identity plugin A was carrying.
``_run_handler`` therefore has to **actively override** the inherited context
(§4.3) — if that override is ever dropped the system silently reverts to
trigger inheritance and still looks correct, because the annotations still
appear. Only the identity behind them is wrong.
"""

import asyncio
from typing import Callable, Dict, List, Optional
import logging

from skillberry_store.access_control.context import (
    reset_current_subject,
    set_current_subject,
)

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

# Optional resolver injected by the loader: slug -> Optional[Subject], the
# identity a plugin's trigger-driven work runs as. Called per dispatch, never
# captured at startup, so a config reload takes effect without a restart
# (§5.2). When None — or when it returns None — the handler runs with no
# ambient identity, and P5 fails any outward call it attempts.
_owner_resolver: Optional[Callable[[str], Optional[object]]] = None


def register_handler_owner(func: Callable, slug: str) -> None:
    """Record which plugin owns a handler callable (called by the loader)."""
    _handler_owners[func] = slug


def set_enabled_resolver(resolver: Optional[Callable[[str], bool]]) -> None:
    """Inject the loader's 'is this plugin enabled?' resolver (or None to clear)."""
    global _enabled_resolver
    _enabled_resolver = resolver


def set_owner_resolver(resolver: Optional[Callable[[str], Optional[object]]]) -> None:
    """Inject the loader's 'which Subject owns this plugin?' resolver.

    Injected rather than imported: this module has no access to the ACL config
    or the plugin config store, and should not grow one. Mirrors
    :func:`set_enabled_resolver`.
    """
    global _owner_resolver
    _owner_resolver = resolver


def owner_subject_for_handler(handler: Callable):
    """The Subject a given handler's work should run as, or ``None``.

    ``None`` means no owner is assigned, which is a real state rather than an
    error here: the handler still runs, and P5 fails at the first outward call
    it makes with a message naming the missing assignment.
    """
    if _owner_resolver is None:
        return None
    slug = _handler_owners.get(handler)
    if slug is None:
        return None
    try:
        return _owner_resolver(slug)
    except Exception as e:  # a broken resolver must not silently grant identity
        logger.error(
            "Owner resolution failed for plugin %r: %s", slug, e, exc_info=True
        )
        return None


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
    """Run a single handler under its plugin's owner tenant.

    The set happens here rather than at task creation because each handler
    task already owns a copied context: a ``set`` inside it is private to that
    task and cannot leak back to the emitting request or across to a sibling
    handler owned by a different plugin.

    Exceptions are logged and never propagated — background tasks sit outside
    any request, so the app-level exception handlers cannot fire for them. That
    is why an authorization denial on this path records its outcome on the
    object itself rather than relying on the raise reaching a handler (§9.1).
    """
    token = set_current_subject(owner_subject_for_handler(handler))
    try:
        await handler(**kwargs)
    except Exception as e:
        logger.error(f"Event handler failed for handler {handler.__name__}: {e}", exc_info=True)
    finally:
        reset_current_subject(token)


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
