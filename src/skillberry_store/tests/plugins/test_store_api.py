"""Tests for plugin Store API."""

import pytest
from unittest.mock import Mock, MagicMock
from typing import Optional


def _mock_service(data_dict=None, list_data=None):
    """Create a mock service that mimics the service interface StoreAPI uses."""
    svc = MagicMock()
    if data_dict is not None:
        svc.get.return_value = data_dict
    else:
        from fastapi import HTTPException
        svc.get.side_effect = KeyError("not found")
    svc.list_all.return_value = list_data or []
    svc.handler = MagicMock()
    svc.handler.write_dict.return_value = None
    return svc


@pytest.fixture
def mock_services():
    """Create mock services for tools, skills, and snippets."""
    tools_service = MagicMock()
    tools_service.handler = MagicMock()
    tools_service.handler.write_dict.return_value = None

    skills_service = MagicMock()
    skills_service.handler = MagicMock()
    skills_service.handler.write_dict.return_value = None

    snippets_service = MagicMock()
    snippets_service.handler = MagicMock()
    snippets_service.handler.write_dict.return_value = None

    return {
        "tools": tools_service,
        "skills": skills_service,
        "snippets": snippets_service,
    }


def test_store_api_initialization(mock_services):
    """Test StoreAPI initialization with services."""
    from skillberry_store.plugins.store_api import StoreAPI

    store_api = StoreAPI(mock_services)

    assert store_api.tools_service == mock_services["tools"]
    assert store_api.skills_service == mock_services["skills"]
    assert store_api.snippets_service == mock_services["snippets"]


def test_get_tool_by_uuid(mock_services):
    """Test getting a tool by UUID."""
    from skillberry_store.plugins.store_api import StoreAPI

    tool_dict = {"uuid": "test-uuid", "name": "test_tool", "description": "A test tool", "tags": ["test"]}
    mock_services["tools"].get.return_value = tool_dict

    store_api = StoreAPI(mock_services)
    tool = store_api.get_tool("test-uuid")

    assert tool is not None
    assert tool["uuid"] == "test-uuid"
    assert tool["name"] == "test_tool"
    mock_services["tools"].get.assert_called_once_with("test-uuid")


def test_get_tool_not_found(mock_services):
    """Test getting a non-existent tool returns None."""
    from skillberry_store.plugins.store_api import StoreAPI

    mock_services["tools"].get.side_effect = KeyError("not found")

    store_api = StoreAPI(mock_services)
    tool = store_api.get_tool("nonexistent-uuid")

    assert tool is None


def test_list_tools(mock_services):
    """Test listing all tools."""
    from skillberry_store.plugins.store_api import StoreAPI

    tools_data = [{"uuid": "uuid1", "name": "tool1"}, {"uuid": "uuid2", "name": "tool2"}]
    mock_services["tools"].list_all.return_value = tools_data

    store_api = StoreAPI(mock_services)
    tools = store_api.list_tools()

    assert len(tools) == 2
    assert tools[0]["uuid"] == "uuid1"


def test_list_tools_with_filter(mock_services):
    """Test listing tools with filter criteria."""
    from skillberry_store.plugins.store_api import StoreAPI

    filtered_data = [{"uuid": "uuid1", "name": "tool1", "tags": ["python"]}]
    mock_services["tools"].list_all.return_value = filtered_data

    store_api = StoreAPI(mock_services)
    filtered = store_api.list_tools(filter_criteria={"name": "tool1"})
    assert len(filtered) == 1


def test_update_tool_tags(mock_services):
    """Test adding tags to a tool."""
    from skillberry_store.plugins.store_api import StoreAPI

    tool_dict = {"uuid": "test-uuid", "name": "test_tool", "tags": ["existing"]}
    mock_services["tools"].get.return_value = tool_dict

    store_api = StoreAPI(mock_services)
    result = store_api.update_tool_tags("test-uuid", ["new", "tags"])

    assert result is True
    call_args = mock_services["tools"].handler.write_dict.call_args
    updated_dict = call_args[0][1]
    assert set(updated_dict["tags"]) == {"existing", "new", "tags"}


def test_update_tool_tags_nonexistent(mock_services):
    """Test updating tags for non-existent tool returns False."""
    from skillberry_store.plugins.store_api import StoreAPI

    mock_services["tools"].get.side_effect = KeyError("not found")

    store_api = StoreAPI(mock_services)
    result = store_api.update_tool_tags("nonexistent", ["tags"])

    assert result is False


def test_update_tool_metadata(mock_services):
    """Test updating tool metadata."""
    from skillberry_store.plugins.store_api import StoreAPI

    tool_dict = {"uuid": "test-uuid", "name": "test_tool", "extra": {"existing": "data"}}
    mock_services["tools"].get.return_value = tool_dict

    store_api = StoreAPI(mock_services)
    result = store_api.update_tool_metadata("test-uuid", {"new": "metadata"})

    assert result is True
    call_args = mock_services["tools"].handler.write_dict.call_args
    updated_dict = call_args[0][1]
    assert updated_dict["extra"]["existing"] == "data"
    assert updated_dict["extra"]["new"] == "metadata"


def test_update_tool_metadata_creates_extra(mock_services):
    """Test updating metadata creates extra field if missing."""
    from skillberry_store.plugins.store_api import StoreAPI

    tool_dict = {"uuid": "test-uuid", "name": "test_tool"}
    mock_services["tools"].get.return_value = tool_dict

    store_api = StoreAPI(mock_services)
    result = store_api.update_tool_metadata("test-uuid", {"new": "metadata"})

    assert result is True
    call_args = mock_services["tools"].handler.write_dict.call_args
    updated_dict = call_args[0][1]
    assert "extra" in updated_dict
    assert updated_dict["extra"]["new"] == "metadata"


def test_get_skill(mock_services):
    """Test getting a skill by UUID."""
    from skillberry_store.plugins.store_api import StoreAPI

    skill_dict = {"uuid": "skill-uuid", "name": "test_skill"}
    mock_services["skills"].get.return_value = skill_dict

    store_api = StoreAPI(mock_services)
    skill = store_api.get_skill("skill-uuid")

    assert skill is not None
    assert skill["uuid"] == "skill-uuid"


def test_list_skills(mock_services):
    """Test listing all skills."""
    from skillberry_store.plugins.store_api import StoreAPI

    skills_data = [{"uuid": "uuid1", "name": "skill1"}, {"uuid": "uuid2", "name": "skill2"}]
    mock_services["skills"].list_all.return_value = skills_data

    store_api = StoreAPI(mock_services)
    skills = store_api.list_skills()

    assert len(skills) == 2


def test_update_skill_tags(mock_services):
    """Test updating skill tags."""
    from skillberry_store.plugins.store_api import StoreAPI

    skill_dict = {"uuid": "skill-uuid", "name": "test_skill", "tags": []}
    mock_services["skills"].get.return_value = skill_dict

    store_api = StoreAPI(mock_services)
    result = store_api.update_skill_tags("skill-uuid", ["new-tag"])

    assert result is True


def test_get_snippet(mock_services):
    """Test getting a snippet by UUID."""
    from skillberry_store.plugins.store_api import StoreAPI

    snippet_dict = {"uuid": "snippet-uuid", "name": "test_snippet"}
    mock_services["snippets"].get.return_value = snippet_dict

    store_api = StoreAPI(mock_services)
    snippet = store_api.get_snippet("snippet-uuid")

    assert snippet is not None
    assert snippet["uuid"] == "snippet-uuid"


def test_list_snippets(mock_services):
    """Test listing all snippets."""
    from skillberry_store.plugins.store_api import StoreAPI

    snippets_data = [{"uuid": "uuid1", "name": "snippet1"}, {"uuid": "uuid2", "name": "snippet2"}]
    mock_services["snippets"].list_all.return_value = snippets_data

    store_api = StoreAPI(mock_services)
    snippets = store_api.list_snippets()

    assert len(snippets) == 2


def test_update_snippet_tags(mock_services):
    """Test updating snippet tags."""
    from skillberry_store.plugins.store_api import StoreAPI

    snippet_dict = {"uuid": "snippet-uuid", "name": "test_snippet", "tags": []}
    mock_services["snippets"].get.return_value = snippet_dict

    store_api = StoreAPI(mock_services)
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


def test_update_skill_metadata_merges_with_existing_extra(mock_services):
    """Test updating skill metadata merges with existing extra fields."""
    from skillberry_store.plugins.store_api import StoreAPI

    skill_dict = {"uuid": "skill-uuid", "name": "test_skill", "extra": {"old_key": "old_val"}, "tags": []}
    mock_services["skills"].get.return_value = skill_dict

    store_api = StoreAPI(mock_services)
    result = store_api.update_skill_metadata("skill-uuid", {"duplicate_analysis": {"skill-y": "reason"}})

    assert result is True
    written = mock_services["skills"].handler.write_dict.call_args[0][1]
    assert written["extra"]["old_key"] == "old_val"
    assert written["extra"]["duplicate_analysis"] == {"skill-y": "reason"}


def test_update_skill_metadata_creates_extra_when_missing(mock_services):
    """Test updating skill metadata creates extra field if missing."""
    from skillberry_store.plugins.store_api import StoreAPI

    skill_dict = {"uuid": "skill-uuid", "name": "test_skill", "tags": []}
    mock_services["skills"].get.return_value = skill_dict

    store_api = StoreAPI(mock_services)
    result = store_api.update_skill_metadata("skill-uuid", {"duplicate_analysis": {"skill-z": "r"}})

    assert result is True
    written = mock_services["skills"].handler.write_dict.call_args[0][1]
    assert written["extra"]["duplicate_analysis"] == {"skill-z": "r"}


def test_update_skill_metadata_returns_false_when_not_found(mock_services):
    """Test updating metadata for non-existent skill returns False."""
    from skillberry_store.plugins.store_api import StoreAPI

    mock_services["skills"].get.side_effect = KeyError("not found")

    store_api = StoreAPI(mock_services)
    result = store_api.update_skill_metadata("missing", {"key": "val"})

    assert result is False
    mock_services["skills"].handler.write_dict.assert_not_called()


def test_update_skill_metadata_returns_false_when_skills_handler_none():
    """Test updating skill metadata returns False when skills service not set."""
    from skillberry_store.plugins.store_api import StoreAPI

    store_api = StoreAPI({"tools": None, "skills": None, "snippets": None})
    assert store_api.update_skill_metadata("any", {}) is False


def test_create_tool(mock_services):
    """Test creating a tool via StoreAPI delegates to tools_service.create."""
    from skillberry_store.plugins.store_api import StoreAPI

    expected = {"uuid": "new-uuid", "name": "echo", "module_name": "echo.py"}
    mock_services["tools"].create.return_value = expected

    store_api = StoreAPI(mock_services)
    data = {"name": "echo", "packaging_format": "mcp"}
    result = store_api.create_tool(data, b"def echo(): pass", "echo.py")

    assert result == expected
    mock_services["tools"].create.assert_called_once_with(
        data, b"def echo(): pass", "echo.py"
    )


def test_create_tool_raises_when_service_unavailable():
    """Test that create_tool raises RuntimeError when tools service is None."""
    from skillberry_store.plugins.store_api import StoreAPI

    store_api = StoreAPI({"tools": None, "skills": None, "snippets": None})
    with pytest.raises(RuntimeError, match="Tools service not available"):
        store_api.create_tool({"name": "x"}, b"", "x.py")

# Made with Bob
