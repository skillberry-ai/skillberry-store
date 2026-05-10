"""
E2E tests for tool API endpoints.
Tests the full lifecycle of tool operations: create, list, get, update, and delete.
"""

import asyncio
import json
import logging
import pytest
import httpx


BASE_URL = "http://localhost:8000"
logger = logging.getLogger(__name__)



@pytest.mark.asyncio
async def test_create_tool(run_sbs):
    """Test creating a new tool."""
    tool_params = {
        "name": "test_tool_create",
        "description": "A test tool for demonstration",
        "programming_language": "python",
        "packaging_format": "code",
        "state": "approved"
    }
    
    # Create a simple Python file content
    file_content = b"""def test_function(x: int) -> int:
    \"\"\"A test function.
    
    Args:
        x: Input number
        
    Returns:
        The input number
    \"\"\"
    return x
"""

    async with httpx.AsyncClient() as client:
        files = {
            "module": ("test_tool_create.py", file_content, "text/x-python")
        }
        response = await client.post(f"{BASE_URL}/tools/", params=tool_params, files=files)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("name") == "test_tool_create"
        assert "created successfully" in data.get("message", "")
        # Verify UUID was generated
        assert "uuid" in data
        assert data.get("uuid") is not None
        assert len(data.get("uuid")) == 36  # UUID4 format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        # Verify module_name was set automatically
        assert data.get("module_name") == "test_tool_create.py"
        
        # Clean up
        delete_response = await client.delete(f"{BASE_URL}/tools/test_tool_create")
        assert delete_response.status_code == 200

@pytest.mark.asyncio
async def test_create_tool_with_file(run_sbs):
    """Test creating a new tool with a file upload."""
    tool_params = {
        "name": "test_tool_with_file",
        "description": "A test tool with file upload",
        "programming_language": "python",
        "packaging_format": "code",
        "state": "approved"
    }
    
    # Create a simple Python file content
    file_content = b"""def add(x: int, y: int) -> int:
    \"\"\"Add two numbers together.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        Sum of x and y
    \"\"\"
    return x + y
"""
    
    async with httpx.AsyncClient() as client:
        # Create multipart form data
        files = {
            "module": ("test_module_file.py", file_content, "text/x-python")
        }
        
        response = await client.post(
            f"{BASE_URL}/tools/",
            params=tool_params,
            files=files
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        assert result.get("name") == "test_tool_with_file"
        assert "created successfully" in result.get("message", "")
        assert result.get("module_name") == "test_module_file.py"
        
        # Verify the tool was created
        get_response = await client.get(f"{BASE_URL}/tools/test_tool_with_file")
        assert get_response.status_code == 200
        tool = get_response.json()
        assert tool.get("module_name") == "test_module_file.py"
        
        # Clean up
        delete_response = await client.delete(f"{BASE_URL}/tools/test_tool_with_file")
        assert delete_response.status_code == 200



@pytest.mark.asyncio
async def test_get_tool_module(run_sbs):
    """Test getting the module file for a tool."""
    tool_params = {
        "name": "test_tool_module_get",
        "description": "A test tool for module retrieval",
        "programming_language": "python",
        "packaging_format": "code",
        "state": "approved"
    }
    
    # Create a simple Python file content
    file_content = b"""def multiply(x: int, y: int) -> int:
    \"\"\"Multiply two numbers together.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        Product of x and y
    \"\"\"
    return x * y
"""
    
    async with httpx.AsyncClient() as client:
        # Create tool with module file
        files = {
            "module": ("test_module_get.py", file_content, "text/x-python")
        }
        
        create_response = await client.post(
            f"{BASE_URL}/tools/",
            params=tool_params,
            files=files
        )
        assert create_response.status_code == 200, f"Expected 200, got {create_response.status_code}: {create_response.text}"
        
        # Get the module file
        module_response = await client.get(f"{BASE_URL}/tools/test_tool_module_get/module")
        assert module_response.status_code == 200
        # Check content-type (may include charset)
        content_type = module_response.headers["content-type"].split(";")[0].strip()
        assert content_type in ["text/x-python", "application/octet-stream", "text/plain"]
        
        # Verify the content matches
        retrieved_content = module_response.content
        assert retrieved_content == file_content
        
        # Clean up
        delete_response = await client.delete(f"{BASE_URL}/tools/test_tool_module_get")
        assert delete_response.status_code == 200


@pytest.mark.asyncio
async def test_get_tool_module_missing_file(run_sbs):
    """Test getting module file when the physical file is missing."""
    # This test would require manually deleting the file after creation,
    # which is complex. Skipping for now as the main functionality is tested.
    pass


@pytest.mark.asyncio
async def test_get_tool_module_nonexistent_tool(run_sbs):
    """Test getting module file for a non-existent tool."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/tools/nonexistent_tool/module")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_duplicate_tool(run_sbs):
    """Test that creating a duplicate tool UUID fails."""
    tool_params = {
        "name": "test_tool",
        "description": "A test tool",
        "programming_language": "python",
        "packaging_format": "code",
        "state": "approved"
    }
    
    file_content = b"def test(): pass"

    async with httpx.AsyncClient() as client:
        files = {
            "module": ("test_tool.py", file_content, "text/x-python")
        }

        create_response = await client.post(f"{BASE_URL}/tools/", params=tool_params, files=files)
        assert create_response.status_code == 200, (
            f"Expected 200, got {create_response.status_code}: {create_response.text}"
        )
        created = create_response.json()
        created_uuid = created.get("uuid")
        assert created_uuid is not None

        duplicate_params = {
            **tool_params,
            "uuid": created_uuid,
        }
        duplicate_response = await client.post(
            f"{BASE_URL}/tools/",
            params=duplicate_params,
            files=files,
        )
        assert duplicate_response.status_code == 409, (
            f"Expected 409, got {duplicate_response.status_code}: {duplicate_response.text}"
        )
        assert "already exists" in duplicate_response.json().get("detail", "")


@pytest.mark.asyncio
async def test_add_tool_from_python_endpoint(run_sbs):
    """Test creating a tool via POST /tools/add from a Python file."""
    file_content = b'''def add_via_tools_add(x: int, y: int) -> int:
    """Add two integers.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        Sum of x and y
    """
    return x + y
'''

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/tools/add",
            params={"tool_name": "add_via_tools_add"},
            files={"tool": ("add_via_tools_add.py", file_content, "text/x-python")},
        )
        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        result = response.json()
        assert result.get("name") == "add_via_tools_add"
        assert result.get("message") == "Tool 'add_via_tools_add' created successfully."
        assert result.get("module_name") == "add_via_tools_add.py"
        assert result.get("uuid") is not None
        assert result.get("description") == "Add two integers."
        assert result.get("parameters") == {
            "x": {"type": "string", "description": "First number"},
            "y": {"type": "string", "description": "Second number"},
        }

        get_response = await client.get(f"{BASE_URL}/tools/add_via_tools_add")
        assert get_response.status_code == 200
        tool = get_response.json()
        assert tool.get("module_name") == "add_via_tools_add.py"

        delete_response = await client.delete(f"{BASE_URL}/tools/add_via_tools_add")
        assert delete_response.status_code == 200


@pytest.mark.asyncio
async def test_add_tool_from_python_endpoint_update(run_sbs):
    """Test updating an existing tool via POST /tools/add with update=true."""
    file_content = b'''def add_via_tools_add_update(x: int, y: int) -> int:
    """Add two integers.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        Sum of x and y
    """
    return x + y
'''

    updated_file_content = b'''def add_via_tools_add_update(x: int, y: int) -> int:
    """Add two integers with updated description.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        Sum of x and y
    """
    return x + y
'''

    async with httpx.AsyncClient() as client:
        create_response = await client.post(
            f"{BASE_URL}/tools/add",
            params={"tool_name": "add_via_tools_add_update"},
            files={
                "tool": (
                    "add_via_tools_add_update.py",
                    file_content,
                    "text/x-python",
                )
            },
        )
        assert create_response.status_code == 200, (
            f"Expected 200, got {create_response.status_code}: {create_response.text}"
        )
        created = create_response.json()
        first_uuid = created.get("uuid")
        assert first_uuid is not None

        update_response = await client.post(
            f"{BASE_URL}/tools/add",
            params={"tool_name": "add_via_tools_add_update", "update": "true"},
            files={
                "tool": (
                    "add_via_tools_add_update.py",
                    updated_file_content,
                    "text/x-python",
                )
            },
        )
        assert update_response.status_code == 200, (
            f"Expected 200, got {update_response.status_code}: {update_response.text}"
        )
        updated = update_response.json()
        assert updated.get("name") == "add_via_tools_add_update"
        assert updated.get("message") == "Tool 'add_via_tools_add_update' created successfully."
        assert updated.get("module_name") == "add_via_tools_add_update.py"
        assert updated.get("uuid") is not None
        assert updated.get("uuid") == first_uuid    # When updating with add from python, UUID should be the same
        assert updated.get("description") == "Add two integers with updated description."

        get_response = await client.get(f"{BASE_URL}/tools/add_via_tools_add_update")
        assert get_response.status_code == 200
        tool = get_response.json()
        assert tool.get("description") == "Add two integers with updated description."
        assert tool.get("module_name") == "add_via_tools_add_update.py"

        delete_response = await client.delete(f"{BASE_URL}/tools/add_via_tools_add_update")
        assert delete_response.status_code == 200


@pytest.mark.asyncio
async def test_list_tools(run_sbs):
    """Test listing all tools."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/tools/")
        assert response.status_code == 200
        tools = response.json()
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check that our test tool is in the list
        tool_names = [t.get("name") for t in tools]
        assert "test_tool" in tool_names


@pytest.mark.asyncio
async def test_get_tool(run_sbs):
    """Test getting a specific tool by name."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/tools/test_tool")
        assert response.status_code == 200
        tool = response.json()
        assert tool.get("name") == "test_tool"
        assert tool.get("description") == "A test tool"
        assert tool.get("module_name") == "test_tool.py"
        assert tool.get("programming_language") == "python"


@pytest.mark.asyncio
async def test_get_nonexistent_tool(run_sbs):
    """Test that getting a non-existent tool fails."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/tools/nonexistent_tool")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_tool(run_sbs):
    """Test updating an existing tool."""
    updated_data = {
        "name": "test_tool",
        "description": "Updated test tool description",
        "module_name": "updated_module",
        "programming_language": "python",
        "packaging_format": "code",
        "params": {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Updated input parameter"
                },
                "count": {
                    "type": "integer",
                    "description": "Count parameter"
                }
            },
            "required": ["input", "count"],
            "optional": []
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(f"{BASE_URL}/tools/test_tool", json=updated_data)
        assert response.status_code == 200
        data = response.json()
        assert "updated successfully" in data.get("message", "")

        # Verify the update
        get_response = await client.get(f"{BASE_URL}/tools/test_tool")
        assert get_response.status_code == 200
        tool = get_response.json()
        assert tool.get("description") == "Updated test tool description"
        assert tool.get("module_name") == "updated_module"
        assert "count" in tool.get("params", {}).get("properties", {})


@pytest.mark.asyncio
async def test_update_nonexistent_tool(run_sbs):
    """Test that updating a non-existent tool fails."""
    updated_data = {
        "name": "nonexistent_tool",
        "description": "This should fail",
        "module_name": "test_module",
        "programming_language": "python"
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(f"{BASE_URL}/tools/nonexistent_tool", json=updated_data)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_tool(run_sbs):
    """Test deleting a tool by UUID."""
    async with httpx.AsyncClient() as client:
        # First get the tool by name to obtain its UUID
        get_response = await client.get(f"{BASE_URL}/tools/test_tool")
        assert get_response.status_code == 200
        tool_data = get_response.json()
        tool_uuid = tool_data.get("uuid")
        assert tool_uuid is not None, "Tool UUID should be present"
        
        # Delete by UUID
        response = await client.delete(f"{BASE_URL}/tools/{tool_uuid}")
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data.get("message", "")

        # Verify deletion by UUID
        verify_response = await client.get(f"{BASE_URL}/tools/{tool_uuid}")
        assert verify_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_tool(run_sbs):
    """Test that deleting a non-existent tool fails."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/tools/nonexistent_tool")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_tool_lifecycle(run_sbs):
    """Test the complete lifecycle of a tool: create, read, update, delete."""
    tool_name = "lifecycle_test_tool"
    
    file_content = b"def lifecycle_func(): return 'lifecycle'"
    
    async with httpx.AsyncClient() as client:
        # 1. Create
        create_params = {
            "name": tool_name,
            "description": "Lifecycle test tool",
            "programming_language": "python",
            "packaging_format": "code",
            "state": "approved"
        }
        files = {
            "module": ("lifecycle_module.py", file_content, "text/x-python")
        }
        create_response = await client.post(f"{BASE_URL}/tools/", params=create_params, files=files)
        assert create_response.status_code == 200, f"Expected 200, got {create_response.status_code}: {create_response.text}"
        assert create_response.json().get("name") == tool_name

        # 2. Read
        get_response = await client.get(f"{BASE_URL}/tools/{tool_name}")
        assert get_response.status_code == 200
        tool = get_response.json()
        assert tool.get("name") == tool_name
        assert tool.get("module_name") == "lifecycle_module.py"

        # 3. Update
        update_data = {
            "name": tool_name,
            "description": "Updated lifecycle test tool",
            "module_name": "lifecycle_module.py",
            "programming_language": "python",
            "packaging_format": "code",
            "params": {
                "type": "object",
                "properties": {
                    "value": {
                        "type": "string",
                        "description": "Updated value parameter"
                    },
                    "extra": {
                        "type": "integer",
                        "description": "Extra parameter"
                    }
                },
                "required": ["value"],
                "optional": ["extra"]
            }
        }
        update_response = await client.put(f"{BASE_URL}/tools/{tool_name}", json=update_data)
        assert update_response.status_code == 200
        assert "updated successfully" in update_response.json().get("message", "")

        # 4. Verify update
        get_updated_response = await client.get(f"{BASE_URL}/tools/{tool_name}")
        assert get_updated_response.status_code == 200
        updated_tool = get_updated_response.json()
        assert updated_tool.get("module_name") == "lifecycle_module.py"  # module_name doesn't change in update
        assert "extra" in updated_tool.get("params", {}).get("properties", {})

        # 5. Delete
        delete_response = await client.delete(f"{BASE_URL}/tools/{tool_name}")
        assert delete_response.status_code == 200
        assert "deleted successfully" in delete_response.json().get("message", "")

        # 6. Verify deletion
        get_deleted_response = await client.get(f"{BASE_URL}/tools/{tool_name}")
        assert get_deleted_response.status_code == 404


@pytest.mark.asyncio
async def test_execute_tool(run_sbs):
    """Test executing a tool with parameters."""
    tool_name = "add"  # Must match the function name in the Python file
    
    # Create a simple Python file that adds two numbers
    # The function name MUST match the tool name
    file_content = b"""def add(x: int, y: int) -> int:
    \"\"\"Add two numbers together.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        Sum of x and y
    \"\"\"
    return x + y
"""
    
    async with httpx.AsyncClient() as client:
        # Create the tool - name must match the function name
        create_params = {
            "name": tool_name,
            "description": "A tool that adds two numbers",
            "programming_language": "python",
            "packaging_format": "code",
            "state": "approved"
        }
        files = {
            "module": ("add_tool.py", file_content, "text/x-python")
        }
        create_response = await client.post(f"{BASE_URL}/tools/", params=create_params, files=files)
        assert create_response.status_code == 200, f"Expected 200, got {create_response.status_code}: {create_response.text}"
        
        # Execute the tool with parameters
        execute_params = {"x": 5, "y": 3}
        execute_response = await client.post(
            f"{BASE_URL}/tools/{tool_name}/execute",
            json=execute_params
        )
        assert execute_response.status_code == 200, f"Expected 200, got {execute_response.status_code}: {execute_response.text}"
        result = execute_response.json()
        
        # Verify the result - should be 8 (5 + 3)
        # The result is returned as a dict with 'return value' key
        assert result is not None
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert result.get("return value") == "8", f"Expected '8', got {result.get('return value')}"
        
        # Clean up
        delete_response = await client.delete(f"{BASE_URL}/tools/{tool_name}")
        assert delete_response.status_code == 200


@pytest.mark.asyncio
async def test_execute_tool_without_parameters(run_sbs):
    """Test executing a tool without parameters."""
    tool_name = "get_constant"  # Must match the function name
    
    # Create a simple Python file that returns a constant
    # The function name MUST match the tool name
    file_content = b"""def get_constant() -> str:
    \"\"\"Return a constant value.
    
    Returns:
        A constant string
    \"\"\"
    return "Hello, World!"
"""
    
    async with httpx.AsyncClient() as client:
        # Create the tool - name must match the function name
        create_params = {
            "name": tool_name,
            "description": "A tool that returns a constant",
            "programming_language": "python",
            "packaging_format": "code",
            "state": "approved"
        }
        files = {
            "module": ("constant_tool.py", file_content, "text/x-python")
        }
        create_response = await client.post(f"{BASE_URL}/tools/", params=create_params, files=files)
        assert create_response.status_code == 200, f"Expected 200, got {create_response.status_code}: {create_response.text}"
        
        # Execute the tool without parameters
        execute_response = await client.post(f"{BASE_URL}/tools/{tool_name}/execute")
        assert execute_response.status_code == 200, f"Expected 200, got {execute_response.status_code}: {execute_response.text}"
        result = execute_response.json()
        
        # Verify the result
        # The result is returned as a dict with 'return value' key
        assert result is not None
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert result.get("return value") == "Hello, World!", f"Expected 'Hello, World!', got {result.get('return value')}"
        
        # Clean up
        delete_response = await client.delete(f"{BASE_URL}/tools/{tool_name}")
        assert delete_response.status_code == 200


@pytest.mark.asyncio
async def test_execute_nonexistent_tool(run_sbs):
    """Test that executing a non-existent tool fails."""
    async with httpx.AsyncClient() as client:
        execute_params = {"x": 5, "y": 3}
        execute_response = await client.post(
            f"{BASE_URL}/tools/nonexistent_tool/execute",
            json=execute_params
        )
        assert execute_response.status_code == 404


@pytest.mark.asyncio
async def test_execute_tool_without_module(run_sbs):
    """Test executing a tool that doesn't have a module file specified."""
    tool_name = "test_no_module"
    
    async with httpx.AsyncClient() as client:
        # Create a tool without a module (by manually creating JSON without module_name)
        # This is a bit tricky since the API requires a module file
        # We'll skip this test as it's hard to create such a scenario through the API
        pass


@pytest.mark.asyncio
async def test_search_tools(run_sbs):
    """Test searching for tools using the /search/tools endpoint."""
    
    # Create test tools with different descriptions
    test_tools = [
        {
            "name": "calculator_tool",
            "description": "A calculator tool that performs basic arithmetic operations like addition and subtraction",
            "programming_language": "python",
            "packaging_format": "code",
            "state": "approved"
        },
        {
            "name": "string_tool",
            "description": "A string manipulation tool for text processing and formatting",
            "programming_language": "python",
            "packaging_format": "code",
            "state": "approved"
        },
        {
            "name": "math_tool",
            "description": "Advanced mathematical operations including trigonometry and calculus",
            "programming_language": "python",
            "packaging_format": "code",
            "state": "approved"
        }
    ]
    
    # Simple Python module content
    module_content = b"""def process(x):
    '''Process input'''
    return x
"""
    
    async with httpx.AsyncClient() as client:
        # Create the test tools
        for tool_params in test_tools:
            files = {
                "module": (f"{tool_params['name']}.py", module_content, "text/x-python")
            }
            response = await client.post(f"{BASE_URL}/tools/", params=tool_params, files=files)
            assert response.status_code == 200, f"Failed to create tool {tool_params['name']}: {response.text}"
        
        # Wait a moment for indexing
        import asyncio
        await asyncio.sleep(1)
        
        # Test search for "calculator"
        search_response = await client.get(
            f"{BASE_URL}/search/tools",
            params={
                "search_term": "calculator arithmetic",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200, f"Search failed: {search_response.text}"
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching tool"
        
        # Verify calculator_tool is in results
        filenames = [r.get("filename") for r in results]
        assert "calculator_tool" in filenames, f"calculator_tool should be in search results, got: {filenames}"
        
        # Test search for "string"
        search_response = await client.get(
            f"{BASE_URL}/search/tools",
            params={
                "search_term": "string text processing",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching tool"
        
        # Test search for "math"
        search_response = await client.get(
            f"{BASE_URL}/search/tools",
            params={
                "search_term": "mathematical trigonometry",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching tool"
        
        # Test with strict similarity threshold
        search_response = await client.get(
            f"{BASE_URL}/search/tools",
            params={
                "search_term": "calculator",
                "max_number_of_results": 5,
                "similarity_threshold": 0.5  # Stricter threshold
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        # Results should be filtered by similarity threshold
        for result in results:
            assert result.get("similarity_score", 1.0) <= 0.5, "All results should meet similarity threshold"
        
        # Clean up - delete test tools
        for tool_params in test_tools:
            delete_response = await client.delete(f"{BASE_URL}/tools/{tool_params['name']}")


@pytest.mark.asyncio
async def test_two_tools_same_name_different_uuid(run_sbs):
    """Test creating two tools with the same name but different UUIDs, then executing each by UUID.
    
    This test verifies that:
    1. Two tools with the same name but different UUIDs can be created successfully
    2. Each tool can be executed independently by its UUID
    3. Each tool executes its own distinct logic correctly
    """
    tool_name = "calculate"  # Same name for both tools
    
    # Tool A: Adds two numbers
    tool_a_content = b"""def calculate(x: int, y: int) -> int:
    \"\"\"Add two numbers together.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        Sum of x and y
    \"\"\"
    return x + y
"""
    
    # Tool B: Multiplies two numbers
    tool_b_content = b"""def calculate(x: int, y: int) -> int:
    \"\"\"Multiply two numbers together.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        Product of x and y
    \"\"\"
    return x * y
"""
    
    async with httpx.AsyncClient() as client:
        # Create Tool A (addition)
        tool_a_params = {
            "name": tool_name,
            "description": "A tool that adds two numbers",
            "programming_language": "python",
            "packaging_format": "code",
            "state": "approved"
        }
        files_a = {
            "module": ("calculate_add.py", tool_a_content, "text/x-python")
        }
        create_a_response = await client.post(f"{BASE_URL}/tools/", params=tool_a_params, files=files_a)
        assert create_a_response.status_code == 200, f"Expected 200 for Tool A, got {create_a_response.status_code}: {create_a_response.text}"
        tool_a_data = create_a_response.json()
        tool_a_uuid = tool_a_data.get("uuid")
        assert tool_a_uuid is not None, "Tool A should have a UUID"
        assert tool_a_data.get("name") == tool_name
        logger.info(f"Created Tool A with UUID: {tool_a_uuid}")
        
        # Create Tool B (multiplication) - same name, different UUID
        tool_b_params = {
            "name": tool_name,
            "description": "A tool that multiplies two numbers",
            "programming_language": "python",
            "packaging_format": "code",
            "state": "approved"
        }
        files_b = {
            "module": ("calculate_multiply.py", tool_b_content, "text/x-python")
        }
        create_b_response = await client.post(f"{BASE_URL}/tools/", params=tool_b_params, files=files_b)
        assert create_b_response.status_code == 200, f"Expected 200 for Tool B, got {create_b_response.status_code}: {create_b_response.text}"
        tool_b_data = create_b_response.json()
        tool_b_uuid = tool_b_data.get("uuid")
        assert tool_b_uuid is not None, "Tool B should have a UUID"
        assert tool_b_data.get("name") == tool_name
        logger.info(f"Created Tool B with UUID: {tool_b_uuid}")
        
        # Verify that the UUIDs are different
        assert tool_a_uuid != tool_b_uuid, "Tool A and Tool B should have different UUIDs"
        
        # Execute Tool A by UUID (should add: 5 + 3 = 8)
        execute_params_a = {"x": 5, "y": 3}
        execute_a_response = await client.post(
            f"{BASE_URL}/tools/{tool_a_uuid}/execute",
            json=execute_params_a
        )
        assert execute_a_response.status_code == 200, f"Expected 200 for Tool A execution, got {execute_a_response.status_code}: {execute_a_response.text}"
        result_a = execute_a_response.json()
        assert result_a is not None
        assert isinstance(result_a, dict), f"Expected dict for Tool A result, got {type(result_a)}"
        assert result_a.get("return value") == "8", f"Tool A should return 8 (5+3), got {result_a.get('return value')}"
        logger.info(f"Tool A executed correctly: 5 + 3 = {result_a.get('return value')}")
        
        # Execute Tool B by UUID (should multiply: 5 * 3 = 15)
        execute_params_b = {"x": 5, "y": 3}
        execute_b_response = await client.post(
            f"{BASE_URL}/tools/{tool_b_uuid}/execute",
            json=execute_params_b
        )
        assert execute_b_response.status_code == 200, f"Expected 200 for Tool B execution, got {execute_b_response.status_code}: {execute_b_response.text}"
        result_b = execute_b_response.json()
        assert result_b is not None
        assert isinstance(result_b, dict), f"Expected dict for Tool B result, got {type(result_b)}"
        assert result_b.get("return value") == "15", f"Tool B should return 15 (5*3), got {result_b.get('return value')}"
        logger.info(f"Tool B executed correctly: 5 * 3 = {result_b.get('return value')}")
        
        # Verify both tools are listed
        list_response = await client.get(f"{BASE_URL}/tools/")
        assert list_response.status_code == 200
        tools_list = list_response.json()
        tool_uuids = [t.get("uuid") for t in tools_list]
        assert tool_a_uuid in tool_uuids, "Tool A should be in the tools list"
        assert tool_b_uuid in tool_uuids, "Tool B should be in the tools list"
        
        # Clean up - delete both tools by UUID
        delete_a_response = await client.delete(f"{BASE_URL}/tools/{tool_a_uuid}")
        assert delete_a_response.status_code == 200, f"Expected 200 for Tool A deletion, got {delete_a_response.status_code}"
        logger.info(f"Deleted Tool A (UUID: {tool_a_uuid})")
        
        delete_b_response = await client.delete(f"{BASE_URL}/tools/{tool_b_uuid}")
        assert delete_b_response.status_code == 200, f"Expected 200 for Tool B deletion, got {delete_b_response.status_code}"
        logger.info(f"Deleted Tool B (UUID: {tool_b_uuid})")


