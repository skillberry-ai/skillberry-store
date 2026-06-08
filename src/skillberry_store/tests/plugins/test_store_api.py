"""Tests for plugin Store API."""

import pytest
from unittest.mock import Mock, AsyncMock
from typing import Optional


@pytest.fixture
def mock_object_handler():
    """Create a mock ObjectHandler."""
    handler = Mock()
    handler.read_dict = Mock()
    handler.iter_dicts = Mock()
    handler.write_dict = Mock()
    return handler


@pytest.fixture
def mock_handlers():
    """Create mock handlers for tools, skills, and snippets."""
    tools_handler = Mock()
    tools_handler.read_dict = Mock()
    tools_handler.iter_dicts = Mock()
    tools_handler.write_dict = Mock()
    
    skills_handler = Mock()
    skills_handler.read_dict = Mock()
    skills_handler.iter_dicts = Mock()
    skills_handler.write_dict = Mock()
    
    snippets_handler = Mock()
    snippets_handler.read_dict = Mock()
    snippets_handler.iter_dicts = Mock()
    snippets_handler.write_dict = Mock()
    
    return {
        "tools": tools_handler,
        "skills": skills_handler,
        "snippets": snippets_handler
    }


def test_store_api_initialization(mock_handlers):
    """Test StoreAPI initialization with handlers."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    store_api = StoreAPI(mock_handlers)
    
    assert store_api.tools == mock_handlers["tools"]
    assert store_api.skills == mock_handlers["skills"]
    assert store_api.snippets == mock_handlers["snippets"]


def test_get_tool_by_uuid(mock_handlers):
    """Test getting a tool by UUID."""
    from skillberry_store.plugins.store_api import StoreAPI
    from skillberry_store.schemas.tool_schema import ToolSchema
    
    # Setup mock
    tool_dict = {
        "uuid": "test-uuid",
        "name": "test_tool",
        "description": "A test tool",
        "tags": ["test"]
    }
    mock_handlers["tools"].read_dict.return_value = tool_dict
    
    store_api = StoreAPI(mock_handlers)
    tool = store_api.get_tool("test-uuid")
    
    assert tool is not None
    assert tool["uuid"] == "test-uuid"
    assert tool["name"] == "test_tool"
    mock_handlers["tools"].read_dict.assert_called_once_with("test-uuid")


def test_get_tool_not_found(mock_handlers):
    """Test getting a non-existent tool returns None."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    mock_handlers["tools"].read_dict.return_value = None
    
    store_api = StoreAPI(mock_handlers)
    tool = store_api.get_tool("nonexistent-uuid")
    
    assert tool is None


def test_list_tools(mock_handlers):
    """Test listing all tools."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    tools_data = [
        {"uuid": "uuid1", "name": "tool1"},
        {"uuid": "uuid2", "name": "tool2"}
    ]
    mock_handlers["tools"].iter_dicts.return_value = iter(tools_data)
    
    store_api = StoreAPI(mock_handlers)
    tools = store_api.list_tools()
    
    assert len(tools) == 2
    assert tools[0]["uuid"] == "uuid1"
    assert tools[1]["uuid"] == "uuid2"


def test_list_tools_with_filter(mock_handlers):
    """Test listing tools with filter criteria."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    tools_data = [
        {"uuid": "uuid1", "name": "tool1", "tags": ["python"]},
        {"uuid": "uuid2", "name": "tool2", "tags": ["javascript"]},
        {"uuid": "uuid3", "name": "tool3", "tags": ["python"]}
    ]
    mock_handlers["tools"].iter_dicts.return_value = iter(tools_data)
    
    store_api = StoreAPI(mock_handlers)
    
    # Filter by name
    filtered = store_api.list_tools(filter_criteria={"name": "tool1"})
    assert len(filtered) == 1
    assert filtered[0]["name"] == "tool1"


def test_update_tool_tags(mock_handlers):
    """Test adding tags to a tool."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    tool_dict = {
        "uuid": "test-uuid",
        "name": "test_tool",
        "tags": ["existing"]
    }
    mock_handlers["tools"].read_dict.return_value = tool_dict
    mock_handlers["tools"].write_dict.return_value = True
    
    store_api = StoreAPI(mock_handlers)
    result = store_api.update_tool_tags("test-uuid", ["new", "tags"])
    
    assert result is True
    # Verify write_dict was called with updated tags
    call_args = mock_handlers["tools"].write_dict.call_args
    updated_dict = call_args[0][1]
    assert set(updated_dict["tags"]) == {"existing", "new", "tags"}


def test_update_tool_tags_nonexistent(mock_handlers):
    """Test updating tags for non-existent tool returns False."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    mock_handlers["tools"].read_dict.return_value = None
    
    store_api = StoreAPI(mock_handlers)
    result = store_api.update_tool_tags("nonexistent", ["tags"])
    
    assert result is False


def test_update_tool_metadata(mock_handlers):
    """Test updating tool metadata."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    tool_dict = {
        "uuid": "test-uuid",
        "name": "test_tool",
        "extra": {"existing": "data"}
    }
    mock_handlers["tools"].read_dict.return_value = tool_dict
    mock_handlers["tools"].write_dict.return_value = True
    
    store_api = StoreAPI(mock_handlers)
    result = store_api.update_tool_metadata("test-uuid", {"new": "metadata"})
    
    assert result is True
    call_args = mock_handlers["tools"].write_dict.call_args
    updated_dict = call_args[0][1]
    assert updated_dict["extra"]["existing"] == "data"
    assert updated_dict["extra"]["new"] == "metadata"


def test_update_tool_metadata_creates_extra(mock_handlers):
    """Test updating metadata creates extra field if missing."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    tool_dict = {
        "uuid": "test-uuid",
        "name": "test_tool"
    }
    mock_handlers["tools"].read_dict.return_value = tool_dict
    mock_handlers["tools"].write_dict.return_value = True
    
    store_api = StoreAPI(mock_handlers)
    result = store_api.update_tool_metadata("test-uuid", {"new": "metadata"})
    
    assert result is True
    call_args = mock_handlers["tools"].write_dict.call_args
    updated_dict = call_args[0][1]
    assert "extra" in updated_dict
    assert updated_dict["extra"]["new"] == "metadata"


def test_get_skill(mock_handlers):
    """Test getting a skill by UUID."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    skill_dict = {
        "uuid": "skill-uuid",
        "name": "test_skill"
    }
    mock_handlers["skills"].read_dict.return_value = skill_dict
    
    store_api = StoreAPI(mock_handlers)
    skill = store_api.get_skill("skill-uuid")
    
    assert skill is not None
    assert skill["uuid"] == "skill-uuid"


def test_list_skills(mock_handlers):
    """Test listing all skills."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    skills_data = [
        {"uuid": "uuid1", "name": "skill1"},
        {"uuid": "uuid2", "name": "skill2"}
    ]
    mock_handlers["skills"].iter_dicts.return_value = iter(skills_data)
    
    store_api = StoreAPI(mock_handlers)
    skills = store_api.list_skills()
    
    assert len(skills) == 2


def test_update_skill_tags(mock_handlers):
    """Test updating skill tags."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    skill_dict = {
        "uuid": "skill-uuid",
        "name": "test_skill",
        "tags": []
    }
    mock_handlers["skills"].read_dict.return_value = skill_dict
    mock_handlers["skills"].write_dict.return_value = True
    
    store_api = StoreAPI(mock_handlers)
    result = store_api.update_skill_tags("skill-uuid", ["new-tag"])
    
    assert result is True


def test_get_snippet(mock_handlers):
    """Test getting a snippet by UUID."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    snippet_dict = {
        "uuid": "snippet-uuid",
        "name": "test_snippet"
    }
    mock_handlers["snippets"].read_dict.return_value = snippet_dict
    
    store_api = StoreAPI(mock_handlers)
    snippet = store_api.get_snippet("snippet-uuid")
    
    assert snippet is not None
    assert snippet["uuid"] == "snippet-uuid"


def test_list_snippets(mock_handlers):
    """Test listing all snippets."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    snippets_data = [
        {"uuid": "uuid1", "name": "snippet1"},
        {"uuid": "uuid2", "name": "snippet2"}
    ]
    mock_handlers["snippets"].iter_dicts.return_value = iter(snippets_data)
    
    store_api = StoreAPI(mock_handlers)
    snippets = store_api.list_snippets()
    
    assert len(snippets) == 2


def test_update_snippet_tags(mock_handlers):
    """Test updating snippet tags."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    snippet_dict = {
        "uuid": "snippet-uuid",
        "name": "test_snippet",
        "tags": []
    }
    mock_handlers["snippets"].read_dict.return_value = snippet_dict
    mock_handlers["snippets"].write_dict.return_value = True
    
    store_api = StoreAPI(mock_handlers)
    result = store_api.update_snippet_tags("snippet-uuid", ["new-tag"])
    
    assert result is True


def test_matches_filter_simple():
    """Test _matches_filter with simple criteria."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    store_api = StoreAPI({})
    
    item = {"name": "test", "type": "python"}
    
    assert store_api._matches_filter(item, {"name": "test"}) is True
    assert store_api._matches_filter(item, {"name": "other"}) is False
    assert store_api._matches_filter(item, {"type": "python"}) is True


def test_matches_filter_multiple_criteria():
    """Test _matches_filter with multiple criteria."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    store_api = StoreAPI({})
    
    item = {"name": "test", "type": "python", "version": "1.0"}
    
    assert store_api._matches_filter(item, {"name": "test", "type": "python"}) is True
    assert store_api._matches_filter(item, {"name": "test", "type": "javascript"}) is False


def test_matches_filter_missing_attribute():
    """Test _matches_filter with missing attribute."""
    from skillberry_store.plugins.store_api import StoreAPI
    
    store_api = StoreAPI({})
    
    item = {"name": "test"}
    
    assert store_api._matches_filter(item, {"nonexistent": "value"}) is False


def test_update_skill_metadata_merges_with_existing_extra(mock_handlers):
    """Test updating skill metadata merges with existing extra fields."""
    from skillberry_store.plugins.store_api import StoreAPI

    skill_dict = {
        "uuid": "skill-uuid",
        "name": "test_skill",
        "extra": {"old_key": "old_val"},
        "tags": [],
    }
    mock_handlers["skills"].read_dict.return_value = skill_dict
    mock_handlers["skills"].write_dict.return_value = True

    store_api = StoreAPI(mock_handlers)
    result = store_api.update_skill_metadata("skill-uuid", {"duplicate_analysis": {"skill-y": "reason"}})

    assert result is True
    written = mock_handlers["skills"].write_dict.call_args[0][1]
    assert written["extra"]["old_key"] == "old_val"
    assert written["extra"]["duplicate_analysis"] == {"skill-y": "reason"}


def test_update_skill_metadata_creates_extra_when_missing(mock_handlers):
    """Test updating skill metadata creates extra field if missing."""
    from skillberry_store.plugins.store_api import StoreAPI

    skill_dict = {"uuid": "skill-uuid", "name": "test_skill", "tags": []}
    mock_handlers["skills"].read_dict.return_value = skill_dict
    mock_handlers["skills"].write_dict.return_value = True

    store_api = StoreAPI(mock_handlers)
    result = store_api.update_skill_metadata("skill-uuid", {"duplicate_analysis": {"skill-z": "r"}})

    assert result is True
    written = mock_handlers["skills"].write_dict.call_args[0][1]
    assert written["extra"]["duplicate_analysis"] == {"skill-z": "r"}


def test_update_skill_metadata_returns_false_when_not_found(mock_handlers):
    """Test updating metadata for non-existent skill returns False."""
    from skillberry_store.plugins.store_api import StoreAPI

    mock_handlers["skills"].read_dict.return_value = None

    store_api = StoreAPI(mock_handlers)
    result = store_api.update_skill_metadata("missing", {"key": "val"})

    assert result is False
    mock_handlers["skills"].write_dict.assert_not_called()


def test_update_skill_metadata_returns_false_when_skills_handler_none():
    """Test updating skill metadata returns False when skills handler not set."""
    from skillberry_store.plugins.store_api import StoreAPI

    store_api = StoreAPI({"tools": None, "skills": None, "snippets": None})
    assert store_api.update_skill_metadata("any", {}) is False

# Made with Bob
