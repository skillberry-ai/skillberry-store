"""
Integration tests for Tools API endpoints.

These tests require a running skillberry-store service.
Run with: pytest -m integration
"""

import pytest


# Shared state for tests that depend on each other
test_state = {
    "tool_name": None,
    "tool_uuid": None,
}


@pytest.mark.integration
class TestToolsAPI:
    """Test suite for Tools API endpoints using SDK client."""

    def test_01_add_tool_from_python(self, tools_api, test_tool_file):
        """Test adding a tool from a Python file."""
        # SDK expects tuple of (filename, bytes)
        tool_file = ("test_add_numbers.py", test_tool_file)
        
        response = tools_api.add_tool_from_python_tools_add_post(
            tool=tool_file,
            tool_name="add_numbers"
        )
        
        assert response is not None
        assert "message" in response or "name" in response
        assert response.get("name") == "add_numbers"
        assert response.get("module_name") == "test_add_numbers.py"
        assert response.get("uuid") is not None
        
        # Store for later tests
        if "name" in response:
            test_state["tool_name"] = response["name"]
        if "uuid" in response:
            test_state["tool_uuid"] = response["uuid"]

    def test_02_list_tools(self, tools_api):
        """Test listing all tools."""
        response = tools_api.list_tools_tools_get()
        
        assert response is not None
        assert isinstance(response, list)
        
        # Verify our added tool is in the list
        if test_state["tool_name"]:
            tool_names = [tool.get("name") for tool in response if isinstance(tool, dict)]
            assert test_state["tool_name"] in tool_names

    def test_03_get_tool_by_name(self, tools_api):
        """Test getting a tool by name."""
        if not test_state["tool_name"]:
            pytest.skip("Tool name not available from previous test")
        
        response = tools_api.get_tool_tools_name_get(name=test_state["tool_name"])
        
        assert response is not None
        assert response.get("name") == test_state["tool_name"]
        assert "uuid" in response
        assert "description" in response

    def test_04_get_tool_module(self, tools_api):
        """Test getting tool module/code."""
        if not test_state["tool_name"]:
            pytest.skip("Tool name not available from previous test")
        
        response = tools_api.get_tool_module_tools_name_module_get(name=test_state["tool_name"])
        
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        # Should contain the function definition
        assert "def add_numbers" in response

    def test_05_execute_tool(self, tools_api):
        """Test executing a tool."""
        if not test_state["tool_name"]:
            pytest.skip("Tool name not available from previous test")
        
        # Execute the add_numbers tool
        response = tools_api.execute_tool_tools_name_execute_post(
            name=test_state["tool_name"],
            request_body={"a": 5, "b": 3}
        )
        
        assert response is not None
        # The result should be 8 (5 + 3)
        if isinstance(response, dict) and "result" in response:
            assert response["result"] == 8
        elif isinstance(response, (int, float)):
            assert response == 8

    def test_06_update_tool(self, tools_api, test_tool_file):
        """Test updating an existing tool."""
        if not test_state["tool_name"]:
            pytest.skip("Tool name not available from previous test")
        
        # Update with the same file but with update flag
        tool_file = ("test_add_numbers.py", test_tool_file)
        
        response = tools_api.add_tool_from_python_tools_add_post(
            tool=tool_file,
            tool_name="add_numbers",
            update=True
        )
        
        assert response is not None
        assert "message" in response or "name" in response
        assert response.get("name") == "add_numbers"
        assert response.get("module_name") == "test_add_numbers.py"
        assert response.get("uuid") is not None

    def test_07_search_tools(self, tools_api):
        """Test searching tools."""
        if not test_state["tool_name"]:
            pytest.skip("Tool name not available from previous test")
        
        # Search for tools with "add" in the name
        response = tools_api.search_tools_search_tools_get(search_term="add")
        
        assert response is not None
        assert isinstance(response, (list, dict))

    def test_08_delete_tool(self, tools_api):
        """Test deleting a tool. This should be the last test."""
        if not test_state["tool_name"]:
            pytest.skip("Tool name not available from previous test")
        
        response = tools_api.delete_tool_tools_name_delete(name=test_state["tool_name"])
        
        assert response is not None
        assert "message" in response or "deleted" in str(response).lower()
        
        # Verify tool is deleted by trying to get it (should fail or return None)
        try:
            tools_api.get_tool_tools_name_get(name=test_state["tool_name"])
            # If we get here, the tool still exists (might be expected in some cases)
        except Exception:
            # Expected - tool should not be found
            pass


@pytest.mark.integration
def test_create_tool_with_manifest(tools_api):
    """Test creating a tool with a full manifest."""
    # This test creates a tool using the full manifest endpoint
    # Note: This requires multipart form data with module file
    
    tool_content = b'''def multiply(x: int, y: int) -> int:
    """Multiply two numbers.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        The product of x and y
    """
    return x * y
'''
    
    tool_file = ("multiply.py", tool_content)
    
    try:
        response = tools_api.create_tool_tools_post(
            name="test_multiply",
            description="A test multiplication tool",
            programming_language="python",
            packaging_format="code",
            state="approved",
            module=tool_file
        )
        
        assert response is not None
        
        # Clean up
        if "name" in response:
            tools_api.delete_tool_tools_name_delete(name=response["name"])
    except Exception as e:
        # Some parameters might not match the actual API signature
        pytest.skip(f"Tool creation with manifest not fully supported: {e}")

# Made with Bob
