"""Tests for plugin event system."""

import pytest


@pytest.mark.asyncio
async def test_event_handler_registration():
    """Test registering event handlers with decorators."""
    from skillberry_store.plugins.events import on_content_added, _event_handlers
    
    # Clear any existing handlers
    _event_handlers.clear()
    
    handler_called = []
    
    @on_content_added("tool")
    async def handle_tool_added(uuid: str):
        handler_called.append(uuid)
    
    assert "content_added:tool" in _event_handlers
    assert len(_event_handlers["content_added:tool"]) == 1


@pytest.mark.asyncio
async def test_emit_event_calls_handlers():
    """Test that emitting events calls registered handlers."""
    from skillberry_store.plugins.events import on_content_added, emit_event, _event_handlers
    
    _event_handlers.clear()
    
    results = []
    
    @on_content_added("tool")
    async def handler1(uuid: str):
        results.append(f"handler1:{uuid}")
    
    @on_content_added("tool")
    async def handler2(uuid: str):
        results.append(f"handler2:{uuid}")
    
    await emit_event("content_added:tool", uuid="test-uuid-123")
    
    assert len(results) == 2
    assert "handler1:test-uuid-123" in results
    assert "handler2:test-uuid-123" in results


@pytest.mark.asyncio
async def test_emit_content_added_convenience():
    """Test convenience function for emitting content_added events."""
    from skillberry_store.plugins.events import on_content_added, emit_content_added, _event_handlers
    
    _event_handlers.clear()
    
    results = []
    
    @on_content_added("skill")
    async def handle_skill(uuid: str):
        results.append(uuid)
    
    await emit_content_added("skill", "skill-uuid-456")
    
    assert len(results) == 1
    assert results[0] == "skill-uuid-456"


@pytest.mark.asyncio
async def test_emit_content_updated():
    """Test content_updated event."""
    from skillberry_store.plugins.events import on_content_updated, emit_content_updated, _event_handlers
    
    _event_handlers.clear()
    
    results = []
    
    @on_content_updated("snippet")
    async def handle_update(uuid: str):
        results.append(f"updated:{uuid}")
    
    await emit_content_updated("snippet", "snippet-123")
    
    assert len(results) == 1
    assert results[0] == "updated:snippet-123"


@pytest.mark.asyncio
async def test_emit_content_deleted():
    """Test content_deleted event."""
    from skillberry_store.plugins.events import on_content_deleted, emit_content_deleted, _event_handlers
    
    _event_handlers.clear()
    
    results = []
    
    @on_content_deleted("tool")
    async def handle_delete(uuid: str):
        results.append(f"deleted:{uuid}")
    
    await emit_content_deleted("tool", "tool-789")
    
    assert len(results) == 1
    assert results[0] == "deleted:tool-789"


@pytest.mark.asyncio
async def test_multiple_content_types():
    """Test handlers for different content types don't interfere."""
    from skillberry_store.plugins.events import (
        on_content_added, 
        emit_content_added,
        _event_handlers
    )
    
    _event_handlers.clear()
    
    tool_results = []
    skill_results = []
    
    @on_content_added("tool")
    async def handle_tool(uuid: str):
        tool_results.append(uuid)
    
    @on_content_added("skill")
    async def handle_skill(uuid: str):
        skill_results.append(uuid)
    
    await emit_content_added("tool", "tool-1")
    await emit_content_added("skill", "skill-1")
    
    assert tool_results == ["tool-1"]
    assert skill_results == ["skill-1"]


@pytest.mark.asyncio
async def test_handler_error_doesnt_stop_other_handlers():
    """Test that if one handler fails, others still execute."""
    from skillberry_store.plugins.events import on_content_added, emit_event, _event_handlers
    
    _event_handlers.clear()
    
    results = []
    
    @on_content_added("tool")
    async def failing_handler(uuid: str):
        raise ValueError("Handler failed!")
    
    @on_content_added("tool")
    async def working_handler(uuid: str):
        results.append(uuid)
    
    # Should not raise, but log error
    await emit_event("content_added:tool", uuid="test-123")
    
    # Working handler should still execute
    assert len(results) == 1
    assert results[0] == "test-123"


@pytest.mark.asyncio
async def test_no_handlers_registered():
    """Test emitting event with no handlers doesn't error."""
    from skillberry_store.plugins.events import emit_event, _event_handlers
    
    _event_handlers.clear()
    
    # Should not raise
    await emit_event("content_added:nonexistent", uuid="test")


@pytest.mark.asyncio
async def test_handler_receives_correct_kwargs():
    """Test that handlers receive all kwargs passed to emit."""
    from skillberry_store.plugins.events import on_content_added, emit_event, _event_handlers
    
    _event_handlers.clear()
    
    received_kwargs = {}
    
    @on_content_added("tool")
    async def handler(uuid: str, extra_data: str = None):
        received_kwargs["uuid"] = uuid
        received_kwargs["extra_data"] = extra_data
    
    await emit_event("content_added:tool", uuid="test-uuid", extra_data="extra")
    
    assert received_kwargs["uuid"] == "test-uuid"
    assert received_kwargs["extra_data"] == "extra"

# Made with Bob
