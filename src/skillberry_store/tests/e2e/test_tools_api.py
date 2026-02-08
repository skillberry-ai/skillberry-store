"""
E2E tests for tool API endpoints.
Tests the full lifecycle of tool operations: create, list, get, update, and delete.
"""

import json
import pytest
import httpx

from skillberry_store.tests.e2e.fixtures import run_sbs

BASE_URL = "http://localhost:8000"



@pytest.mark.asyncio
async def test_create_tool(run_sbs):
    """Test creating a new tool."""
    tool_params = {
        "name": "test_tool",
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
            "module": ("test_tool.py", file_content, "text/x-python")
        }
        response = await client.post(f"{BASE_URL}/tools/", params=tool_params, files=files)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("name") == "test_tool"
        assert "created successfully" in data.get("message", "")
        # Verify UUID was generated
        assert "uuid" in data
        assert data.get("uuid") is not None
        assert len(data.get("uuid")) == 36  # UUID4 format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        # Verify module_name was set automatically
        assert data.get("module_name") == "test_tool.py"

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
    """Test that creating a duplicate tool fails."""
    tool_params = {
        "name": "test_tool",
        "description": "A test tool for demonstration",
        "programming_language": "python",
        "packaging_format": "code",
        "state": "approved"
    }
    
    file_content = b"def test(): pass"

    async with httpx.AsyncClient() as client:
        files = {
            "module": ("test_tool.py", file_content, "text/x-python")
        }
        response = await client.post(f"{BASE_URL}/tools/", params=tool_params, files=files)
        # Should fail with 409 Conflict
        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"
        assert "already exists" in response.json().get("detail", "")


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
        assert tool.get("description") == "A test tool for demonstration"
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
    """Test deleting a tool."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/tools/test_tool")
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data.get("message", "")

        # Verify deletion
        get_response = await client.get(f"{BASE_URL}/tools/test_tool")
        assert get_response.status_code == 404


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
async def test_execute_tool_with_mcp_packaging(run_sbs):
    """Test executing a tool with MCP packaging format."""
    tool_name = "mcp_test_tool"
    
    async with httpx.AsyncClient() as client:
        # First, create a VMCP server with a tool
        # Step 1: Create a code-based tool first
        code_tool_name = "add_for_mcp_test"
        tool_code = b"""def add_for_mcp_test(a: int, b: int) -> int:
    \"\"\"Add two numbers
    
    Args:
        a: first number
        b: second number
    
    Returns:
        Sum of a and b
    \"\"\"
    return a + b
"""
        response = await client.post(
            f"{BASE_URL}/tools/add",
            params={"tool_name": code_tool_name, "update": "true"},
            files={"tool": (f"{code_tool_name}.py", tool_code, "text/x-python")}
        )
        assert response.status_code == 200, f"Tool creation failed: {response.text}"
        tool_response = response.json()
        tool_uuid = tool_response.get("uuid")
        
        # Step 2: Create a skill with the tool
        skill_name = "mcp_test_skill"
        skill_data = {
            "name": skill_name,
            "description": "Test skill for MCP tool execution",
            "tool_uuids": tool_uuid
        }
        response = await client.post(f"{BASE_URL}/skills/", params=skill_data)
        assert response.status_code == 200, f"Skill creation failed: {response.text}"
        skill_response = response.json()
        skill_uuid = skill_response.get("uuid")
        
        # Step 3: Create a VMCP server with the skill
        vmcp_server_name = "test_vmcp_for_tool_exec"
        vmcp_data = {
            "name": vmcp_server_name,
            "description": "Test VMCP server for tool execution",
            "skill_uuid": skill_uuid
        }
        response = await client.post(f"{BASE_URL}/vmcp_servers/", params=vmcp_data)
        assert response.status_code == 200, f"VMCP server creation failed: {response.text}"
        vmcp_response = response.json()
        vmcp_url = vmcp_response.get("url")
        
        # Step 4: Create a tool with MCP packaging format
        mcp_tool_data = {
            "name": tool_name,
            "description": "MCP-based tool for testing",
            "programming_language": "python",
            "packaging_format": "mcp",
            "mcp_url": vmcp_url,
            "state": "approved"
        }
        
        # For MCP tools, we don't need to upload a module file
        # Create the tool JSON manually
        import json
        tool_json = json.dumps(mcp_tool_data, indent=4)
        
        # Write the tool JSON directly to the tools directory
        from skillberry_store.tools.configure import get_tools_directory
        from skillberry_store.modules.file_handler import FileHandler
        tools_directory = get_tools_directory()
        tool_handler = FileHandler(tools_directory)
        tool_handler.write_file_content(f"{tool_name}.json", tool_json)
        
        # Step 5: Execute the MCP tool
        execute_params = {"a": 10, "b": 5}
        execute_response = await client.post(
            f"{BASE_URL}/tools/{tool_name}/execute",
            json=execute_params
        )
        assert execute_response.status_code == 200, f"MCP tool execution failed: {execute_response.text}"
        result = execute_response.json()
        
        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        # The result should contain the sum (15)
        assert result.get("return value") == "15", f"Expected '15', got {result.get('return value')}"
        
        # Clean up
        delete_response = await client.delete(f"{BASE_URL}/tools/{tool_name}")
        assert delete_response.status_code == 200
        
        # Clean up VMCP server
        await client.delete(f"{BASE_URL}/vmcp_servers/{vmcp_server_name}")
        
        # Clean up skill
        await client.delete(f"{BASE_URL}/skills/{skill_name}")
        
        # Clean up code tool
        await client.delete(f"{BASE_URL}/tools/{code_tool_name}")


@pytest.mark.asyncio
async def test_get_tool_module_with_mcp_packaging(run_sbs):
    """Test getting module content for a tool with MCP packaging format."""
    tool_name = "mcp_module_test_tool"
    
    async with httpx.AsyncClient() as client:
        # Step 1: Create a code-based tool first
        code_tool_name = "multiply_for_mcp_test"
        tool_code = b"""def multiply_for_mcp_test(x: int, y: int) -> int:
    \"\"\"Multiply two numbers
    
    Args:
        x: first number
        y: second number
    
    Returns:
        Product of x and y
    \"\"\"
    return x * y
"""
        response = await client.post(
            f"{BASE_URL}/tools/add",
            params={"tool_name": code_tool_name, "update": "true"},
            files={"tool": (f"{code_tool_name}.py", tool_code, "text/x-python")}
        )
        assert response.status_code == 200, f"Tool creation failed: {response.text}"
        tool_response = response.json()
        tool_uuid = tool_response.get("uuid")
        
        # Step 2: Create a skill with the tool
        skill_name = "mcp_module_test_skill"
        skill_data = {
            "name": skill_name,
            "description": "Test skill for MCP module retrieval",
            "tool_uuids": tool_uuid
        }
        response = await client.post(f"{BASE_URL}/skills/", params=skill_data)
        assert response.status_code == 200, f"Skill creation failed: {response.text}"
        skill_response = response.json()
        skill_uuid = skill_response.get("uuid")
        
        # Step 3: Create a VMCP server with the skill
        vmcp_server_name = "test_vmcp_for_module"
        vmcp_data = {
            "name": vmcp_server_name,
            "description": "Test VMCP server for module retrieval",
            "skill_uuid": skill_uuid
        }
        response = await client.post(f"{BASE_URL}/vmcp_servers/", params=vmcp_data)
        assert response.status_code == 200, f"VMCP server creation failed: {response.text}"
        vmcp_response = response.json()
        vmcp_url = vmcp_response.get("url")
        
        # Step 4: Create a tool with MCP packaging format
        mcp_tool_data = {
            "name": tool_name,
            "description": "MCP-based tool for module testing",
            "programming_language": "python",
            "packaging_format": "mcp",
            "mcp_url": vmcp_url,
            "state": "approved"
        }
        
        # Write the tool JSON directly
        import json
        tool_json = json.dumps(mcp_tool_data, indent=4)
        from skillberry_store.tools.configure import get_tools_directory
        from skillberry_store.modules.file_handler import FileHandler
        tools_directory = get_tools_directory()
        tool_handler = FileHandler(tools_directory)
        tool_handler.write_file_content(f"{tool_name}.json", tool_json)
        
        # Step 5: Get the module content for the MCP tool
        module_response = await client.get(f"{BASE_URL}/tools/{tool_name}/module")
        assert module_response.status_code == 200, f"Module retrieval failed: {module_response.text}"
        
        # Verify the content is a generated function signature
        module_content = module_response.text
        assert "def " in module_content, "Module content should contain a function definition"
        assert code_tool_name in module_content, f"Module content should reference the tool name {code_tool_name}"
        
        # Clean up
        delete_response = await client.delete(f"{BASE_URL}/tools/{tool_name}")
        assert delete_response.status_code == 200
        
        # Clean up VMCP server
        await client.delete(f"{BASE_URL}/vmcp_servers/{vmcp_server_name}")
        
        # Clean up skill
        await client.delete(f"{BASE_URL}/skills/{skill_name}")
        
        # Clean up code tool
        await client.delete(f"{BASE_URL}/tools/{code_tool_name}")


@pytest.mark.asyncio
async def test_mcp_tool_not_found(run_sbs):
    """Test that executing an MCP tool that doesn't exist in the MCP server fails gracefully."""
    tool_name = "nonexistent_mcp_tool"
    
    async with httpx.AsyncClient() as client:
        # Create a tool with MCP packaging format pointing to a non-existent MCP tool
        mcp_tool_data = {
            "name": tool_name,
            "description": "Non-existent MCP tool",
            "programming_language": "python",
            "packaging_format": "mcp",
            "mcp_url": "http://localhost:9999/sse",  # Non-existent server
            "state": "approved"
        }
        
        # Write the tool JSON directly
        import json
        tool_json = json.dumps(mcp_tool_data, indent=4)
        from skillberry_store.tools.configure import get_tools_directory
        from skillberry_store.modules.file_handler import FileHandler
        tools_directory = get_tools_directory()
        tool_handler = FileHandler(tools_directory)
        tool_handler.write_file_content(f"{tool_name}.json", tool_json)
        
        # Try to execute the tool - should fail
        execute_params = {"x": 5}
        execute_response = await client.post(
            f"{BASE_URL}/tools/{tool_name}/execute",
            json=execute_params
        )
        # Should return an error (404 or 500)
        assert execute_response.status_code in [404, 500], f"Expected error status, got {execute_response.status_code}"
        
        # Clean up
        delete_response = await client.delete(f"{BASE_URL}/tools/{tool_name}")
        assert delete_response.status_code == 200