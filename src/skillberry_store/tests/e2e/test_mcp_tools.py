"""
E2E tests for MCP (Model Context Protocol) tool operations.
Tests tools that use MCP packaging format and interact with VMCP servers.
"""

import asyncio
import json
import pytest
import httpx


BASE_URL = "http://localhost:8000"


async def create_vmcp_server_with_tool(client, tool_name: str, tool_code: bytes, vmcp_server_name: str, skill_name: str):
    """
    Helper function to create a VMCP server with a tool.
    
    Returns:
        tuple: (vmcp_url, vmcp_port, tool_uuid, skill_uuid, vmcp_server_name)
    """
    # Step 1: Create a code-based tool
    print(f"Step 1: Creating code-based tool '{tool_name}'...")
    response = await client.post(
        f"{BASE_URL}/tools/add",
        params={"tool_name": tool_name, "update": "true"},
        files={"tool": (f"{tool_name}.py", tool_code, "text/x-python")}
    )
    print(f"Tool creation response: {response.status_code}")
    assert response.status_code == 200, f"Tool creation failed: {response.text}"
    tool_response = response.json()
    tool_uuid = tool_response.get("uuid")
    print(f"Created tool with UUID: {tool_uuid}")
    
    # Step 2: Create a skill with the tool
    print(f"Step 2: Creating skill '{skill_name}' with tool...")
    skill_data = {
        "name": skill_name,
        "description": f"Test skill for {vmcp_server_name}",
        "tool_uuids": [tool_uuid]
    }
    response = await client.post(f"{BASE_URL}/skills/", params=skill_data)
    print(f"Skill creation response: {response.status_code}")
    assert response.status_code == 200, f"Skill creation failed: {response.text}"
    skill_response = response.json()
    skill_uuid = skill_response.get("uuid")
    print(f"Created skill with UUID: {skill_uuid}")
    
    # Step 3: Create a VMCP server with the skill
    print("\n" + "="*60)
    print(f"Step 3: Creating VMCP server '{vmcp_server_name}'...")
    print("="*60)
    vmcp_data = {
        "name": vmcp_server_name,
        "description": f"Test VMCP server for {tool_name}",
        "skill_uuid": skill_uuid
    }
    print(f"VMCP data: {vmcp_data}")
    response = await client.post(f"{BASE_URL}/vmcp_servers/", params=vmcp_data)
    print(f"VMCP server creation response status: {response.status_code}")
    print(f"VMCP server creation response body: {response.text}")
    assert response.status_code == 200, f"VMCP server creation failed: {response.text}"
    vmcp_response = response.json()
    print(f"VMCP response JSON: {vmcp_response}")
    vmcp_port = vmcp_response.get("port")
    vmcp_url = f"http://localhost:{vmcp_port}/sse"
    print(f"Created VMCP server on port {vmcp_port}, URL: {vmcp_url}")
    
    # Wait for the VMCP server to fully start and verify it's responsive
    print("\n" + "="*60)
    print("Step 3a: Waiting for VMCP server to be ready...")
    print("="*60)
    await asyncio.sleep(5)
    
    # Verify the VMCP server is in the list and is running
    print("Checking if VMCP server is in the list...")
    list_response = await client.get(f"{BASE_URL}/vmcp_servers/")
    print(f"List response status: {list_response.status_code}")
    server_running = False
    if list_response.status_code == 200:
        servers = list_response.json().get("virtual_mcp_servers", {})
        print(f"Available VMCP servers: {list(servers.keys())}")
        if vmcp_server_name in servers:
            server_info = servers[vmcp_server_name]
            print(f"Server info: {server_info}")
            server_running = server_info.get('running', False)
            print(f"Server running: {server_running}")
            print(f"Server port: {server_info.get('port')}")
            if server_running:
                print("✓ VMCP server is marked as running")
            else:
                print("✗ VMCP server is NOT running")
        else:
            print(f"WARNING: VMCP server '{vmcp_server_name}' not found in list!")
    
    # If server is marked as running, proceed
    # Note: SSE endpoint check is skipped as it may timeout even when server is functional
    if server_running:
        print("\n✓ VMCP server is ready (marked as running in server list)")
    else:
        # Try SSE endpoint as fallback verification
        print("\nServer not marked as running, trying SSE endpoint verification...")
        max_retries = 3
        retry_delay = 2
        sse_ready = False
        
        for attempt in range(max_retries):
            try:
                print(f"\nAttempt {attempt + 1}/{max_retries}: Connecting to http://localhost:{vmcp_port}/sse")
                response = await client.get(f"http://localhost:{vmcp_port}/sse", timeout=5.0)
                print(f"  Response status: {response.status_code}")
                if response.status_code in [200, 404]:  # 404 is ok for SSE GET
                    sse_ready = True
                    print("  ✓ SSE endpoint is responsive!")
                    break
            except Exception as e:
                print(f"  ✗ Failed to connect: {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    print(f"  Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
        
        assert sse_ready or server_running, f"VMCP server not ready: running={server_running}, sse_ready={sse_ready}"
    
    return vmcp_url, vmcp_port, tool_uuid, skill_uuid, vmcp_server_name


@pytest.mark.asyncio
async def test_execute_tool_with_mcp_packaging(run_sbs):
    """Test executing a tool with MCP packaging format."""
    # The MCP tool name must match the actual tool name on the VMCP server
    code_tool_name = "concat_for_mcp_test"
    tool_name = code_tool_name  # MCP tool uses the same name as the underlying tool
    
    async with httpx.AsyncClient() as client:
        # Create VMCP server with tool using helper function
        tool_code = b"""def concat_for_mcp_test(first: str, second: str) -> str:
    \"\"\"Concatenate two strings
    
    Args:
        first: first string
        second: second string
    
    Returns:
        Concatenated string
    \"\"\"
    return first + " " + second
"""
        vmcp_url, vmcp_port, tool_uuid, skill_uuid, vmcp_server_name = await create_vmcp_server_with_tool(
            client,
            tool_name=code_tool_name,
            tool_code=tool_code,
            vmcp_server_name="test_vmcp_for_tool_exec",
            skill_name="mcp_test_skill"
        )
        
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
        tool_json = json.dumps(mcp_tool_data, indent=4)
        
        # Write the tool JSON directly to the tools directory
        from skillberry_store.tools.configure import get_tools_directory
        from skillberry_store.modules.file_handler import FileHandler
        tools_directory = get_tools_directory()
        tool_handler = FileHandler(tools_directory)
        tool_handler.write_file_content(f"{tool_name}.json", tool_json)
        
        # Step 4a: Verify the tool is visible in the tools list
        print("\n" + "="*60)
        print("Step 4a: Verifying tool is in tools list...")
        print("="*60)
        list_response = await client.get(f"{BASE_URL}/tools/")
        assert list_response.status_code == 200, f"Failed to list tools: {list_response.text}"
        tools_list = list_response.json()
        tool_names = [t.get("name") for t in tools_list]
        print(f"Available tools: {tool_names}")
        assert tool_name in tool_names, f"Tool '{tool_name}' not found in tools list"
        
        # Find our tool in the list and verify its properties
        our_tool = next((t for t in tools_list if t.get("name") == tool_name), None)
        assert our_tool is not None, f"Tool '{tool_name}' not found in tools list"
        print(f"Tool found in list: {our_tool.get('name')}")
        print(f"  - packaging_format: {our_tool.get('packaging_format')}")
        print(f"  - mcp_url: {our_tool.get('mcp_url')}")
        print(f"  - state: {our_tool.get('state')}")
        
        # Verify the tool properties match what we created
        assert our_tool.get("packaging_format") == "mcp", f"Expected packaging_format 'mcp', got '{our_tool.get('packaging_format')}'"
        assert our_tool.get("mcp_url") == vmcp_url, f"Expected mcp_url '{vmcp_url}', got '{our_tool.get('mcp_url')}'"
        print("✓ Tool verified in tools list with correct properties")
        
        # Step 5: Execute the MCP tool
        # Note: MCP tools expect string parameters
        print("\n" + "="*60)
        print("Step 5: Executing MCP tool...")
        print("="*60)
        execute_params = {"first": "Hello", "second": "World"}
        print(f"Executing tool '{tool_name}' with params: {execute_params}")
        
        try:
            execute_response = await client.post(
                f"{BASE_URL}/tools/{tool_name}/execute",
                json=execute_params,
                timeout=60.0  # Increase timeout to accommodate MCP initialization (10s) + tool listing (10s) + execution (30s) + buffer
            )
        except Exception as e:
            print(f"Failed to execute MCP tool: {e}")
            raise

        print(f"Execution response status: {execute_response.status_code}")
        assert execute_response.status_code == 200, f"MCP tool execution failed: {execute_response.text}"
        result = execute_response.json()
        print(f"Execution result: {result}")
        
        # Verify the result
        assert result is not None
        assert isinstance(result, dict)
        # The result should contain the concatenated string
        assert result.get("return value") == "Hello World", f"Expected 'Hello World', got {result.get('return value')}"
        print("✓ MCP tool execution successful")
        
        # Clean up
        print("\nCleaning up resources...")
        delete_response = await client.delete(f"{BASE_URL}/tools/{tool_name}")
        assert delete_response.status_code == 200
        print(f"Deleted MCP tool")
        
        # Clean up VMCP server
        await client.delete(f"{BASE_URL}/vmcp_servers/{vmcp_server_name}")
        print(f"Deleted VMCP server")
        
        # Clean up skill
        await client.delete(f"{BASE_URL}/skills/mcp_test_skill")
        print(f"Deleted skill")
        
        # Clean up code tool
        await client.delete(f"{BASE_URL}/tools/{code_tool_name}")
        print(f"Deleted code tool")
        
        # Add delay to allow resources to be fully released before next test
        await asyncio.sleep(3)
        print("✓ Cleanup complete")

@pytest.mark.asyncio
async def test_create_mcp_tool_via_post_endpoint(run_sbs):
    """Test creating an MCP tool via POST /tools/ endpoint with a different name than the underlying tool."""
    # The underlying code tool name on the VMCP server
    code_tool_name = "add_for_mcp_test"
    # The MCP tool will have a different name
    mcp_tool_name = "mcp_add_wrapper"
    
    async with httpx.AsyncClient() as client:
        # Step 1: Create VMCP server with the underlying tool
        print("\n" + "="*60)
        print("Step 1: Creating VMCP server with underlying tool...")
        print("="*60)
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
        vmcp_url, vmcp_port, tool_uuid, skill_uuid, vmcp_server_name = await create_vmcp_server_with_tool(
            client,
            tool_name=code_tool_name,
            tool_code=tool_code,
            vmcp_server_name="test_vmcp_for_post_endpoint",
            skill_name="mcp_post_endpoint_skill"
        )
        print(f"✓ VMCP server created on port {vmcp_port}")
        print(f"✓ VMCP URL: {vmcp_url}")
        
        # Step 2: Create an MCP tool via POST /tools/ endpoint
        print("\n" + "="*60)
        print("Step 2: Creating MCP tool via POST /tools/ endpoint...")
        print("="*60)
        
        # Create a dummy Python file (required by the endpoint but not used for MCP tools)
        dummy_module_content = b"""# This is a placeholder module for MCP tool
def placeholder():
    pass
"""
        
        # Prepare the tool data with MCP packaging
        mcp_tool_data = {
            "name": mcp_tool_name,
            "description": "MCP wrapper tool for add_for_mcp_test",
            "programming_language": "python",
            "packaging_format": "mcp",
            "mcp_url": vmcp_url,
            "state": "approved"
        }
        
        files = {
            "module": (f"{mcp_tool_name}.py", dummy_module_content, "text/x-python")
        }
        
        # Create the tool using POST /tools/
        response = await client.post(
            f"{BASE_URL}/tools/",
            params=mcp_tool_data,
            files=files
        )
        print(f"Tool creation response: {response.status_code}")
        assert response.status_code == 200, f"Tool creation failed: {response.text}"
        tool_response = response.json()
        print(f"✓ Created MCP tool: {tool_response.get('name')}")
        print(f"  - packaging_format: mcp")
        print(f"  - mcp_url: {vmcp_url}")
        
        # Step 3: Retrieve the tool and verify it has MCP packaging
        print("\n" + "="*60)
        print("Step 3: Verifying MCP tool properties...")
        print("="*60)
        
        verify_response = await client.get(f"{BASE_URL}/tools/{mcp_tool_name}")
        assert verify_response.status_code == 200, f"Failed to get tool: {verify_response.text}"
        retrieved_tool = verify_response.json()
        
        print(f"Tool name: {retrieved_tool.get('name')}")
        print(f"Packaging format: {retrieved_tool.get('packaging_format')}")
        print(f"MCP URL: {retrieved_tool.get('mcp_url')}")
        
        # Assert the tool has MCP packaging
        assert retrieved_tool.get("packaging_format") == "mcp", \
            f"Expected packaging_format 'mcp', got '{retrieved_tool.get('packaging_format')}'"
        assert retrieved_tool.get("mcp_url") == vmcp_url, \
            f"Expected mcp_url '{vmcp_url}', got '{retrieved_tool.get('mcp_url')}'"
        
        print("✓ Tool verified with MCP packaging format")
        print(f"✓ MCP URL correctly stored: {retrieved_tool.get('mcp_url')}")
        
        # Clean up
        print("\nCleaning up resources...")
        
        # Delete the MCP tool
        delete_response = await client.delete(f"{BASE_URL}/tools/{mcp_tool_name}")
        assert delete_response.status_code == 200
        print(f"Deleted MCP tool: {mcp_tool_name}")
        
        # Clean up VMCP server
        await client.delete(f"{BASE_URL}/vmcp_servers/{vmcp_server_name}")
        print(f"Deleted VMCP server: {vmcp_server_name}")
        
        # Clean up skill
        await client.delete(f"{BASE_URL}/skills/mcp_post_endpoint_skill")
        print(f"Deleted skill: mcp_post_endpoint_skill")
        
        # Clean up the code tool
        await client.delete(f"{BASE_URL}/tools/{code_tool_name}")
        print(f"Deleted code tool: {code_tool_name}")
        
        # Add delay to allow resources to be fully released
        await asyncio.sleep(3)
        print("✓ Cleanup complete")



@pytest.mark.asyncio
async def test_get_tool_module_with_mcp_packaging(run_sbs):
    """Test getting module content for a tool with MCP packaging format."""
    # The MCP tool name must match the actual tool name on the VMCP server
    code_tool_name = "multiply_for_mcp_test"
    tool_name = code_tool_name  # MCP tool uses the same name as the underlying tool
    
    async with httpx.AsyncClient() as client:
        # Step 1: Create a code-based tool first
        print("Step 1: Creating code-based tool...")
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
        print(f"Tool creation response: {response.status_code}")
        assert response.status_code == 200, f"Tool creation failed: {response.text}"
        tool_response = response.json()
        tool_uuid = tool_response.get("uuid")
        print(f"Created tool with UUID: {tool_uuid}")
        
        # Step 2: Create a skill with the tool
        print("Step 2: Creating skill with tool...")
        skill_name = "mcp_module_test_skill"
        skill_data = {
            "name": skill_name,
            "description": "Test skill for MCP module retrieval",
            "tool_uuids": [tool_uuid]  # Fixed: should be a list
        }
        response = await client.post(f"{BASE_URL}/skills/", params=skill_data)
        print(f"Skill creation response: {response.status_code}")
        assert response.status_code == 200, f"Skill creation failed: {response.text}"
        skill_response = response.json()
        skill_uuid = skill_response.get("uuid")
        print(f"Created skill with UUID: {skill_uuid}")
        
        # Step 3: Create a VMCP server with the skill
        print("\n" + "="*60)
        print("Step 3: Creating VMCP server...")
        print("="*60)
        vmcp_server_name = "test_vmcp_for_module"
        vmcp_data = {
            "name": vmcp_server_name,
            "description": "Test VMCP server for module retrieval",
            "skill_uuid": skill_uuid
        }
        print(f"VMCP data: {vmcp_data}")
        response = await client.post(f"{BASE_URL}/vmcp_servers/", params=vmcp_data)
        print(f"VMCP server creation response status: {response.status_code}")
        print(f"VMCP server creation response body: {response.text}")
        assert response.status_code == 200, f"VMCP server creation failed: {response.text}"
        vmcp_response = response.json()
        print(f"VMCP response JSON: {vmcp_response}")
        vmcp_port = vmcp_response.get("port")
        vmcp_url = f"http://localhost:{vmcp_port}/sse"
        print(f"Created VMCP server on port {vmcp_port}, URL: {vmcp_url}")
        
        # Wait for the VMCP server to fully start and verify it's responsive
        print("\n" + "="*60)
        print("Step 3a: Waiting for VMCP server to be ready...")
        print("="*60)
        await asyncio.sleep(5)
        
        # First, verify the VMCP server is in the list and is running
        print("Checking if VMCP server is in the list...")
        list_response = await client.get(f"{BASE_URL}/vmcp_servers/")
        print(f"List response status: {list_response.status_code}")
        server_running = False
        if list_response.status_code == 200:
            servers = list_response.json().get("virtual_mcp_servers", {})
            print(f"Available VMCP servers: {list(servers.keys())}")
            if vmcp_server_name in servers:
                server_info = servers[vmcp_server_name]
                print(f"Server info: {server_info}")
                server_running = server_info.get('running', False)
                print(f"Server running: {server_running}")
                print(f"Server port: {server_info.get('port')}")
                if server_running:
                    print("✓ VMCP server is marked as running")
                else:
                    print("✗ VMCP server is NOT running")
            else:
                print(f"WARNING: VMCP server '{vmcp_server_name}' not found in list!")
        
        # If server is marked as running, proceed with the test
        # Note: SSE endpoint check is skipped as it may timeout even when server is functional
        if server_running:
            print("\n✓ VMCP server is ready (marked as running in server list)")
        else:
            # Try SSE endpoint as fallback verification
            print("\nServer not marked as running, trying SSE endpoint verification...")
            max_retries = 3
            retry_delay = 2
            sse_ready = False
            
            for attempt in range(max_retries):
                try:
                    print(f"\nAttempt {attempt + 1}/{max_retries}: Connecting to http://localhost:{vmcp_port}/sse")
                    response = await client.get(f"http://localhost:{vmcp_port}/sse", timeout=5.0)
                    print(f"  Response status: {response.status_code}")
                    if response.status_code in [200, 404]:  # 404 is ok for SSE GET
                        sse_ready = True
                        print("  ✓ SSE endpoint is responsive!")
                        break
                except Exception as e:
                    print(f"  ✗ Failed to connect: {type(e).__name__}: {e}")
                    if attempt < max_retries - 1:
                        print(f"  Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
            
            assert sse_ready or server_running, f"VMCP server not ready: running={server_running}, sse_ready={sse_ready}"

        # Step 4: Create a tool with MCP packaging format
        print("\n" + "="*60)
        print("Step 4: Creating MCP tool...")
        print("="*60)
        mcp_tool_data = {
            "name": tool_name,
            "description": "MCP-based tool for module testing",
            "programming_language": "python",
            "packaging_format": "mcp",
            "mcp_url": vmcp_url,
            "state": "approved"
        }
        
        # Write the tool JSON directly
        tool_json = json.dumps(mcp_tool_data, indent=4)
        from skillberry_store.tools.configure import get_tools_directory
        from skillberry_store.modules.file_handler import FileHandler
        tools_directory = get_tools_directory()
        tool_handler = FileHandler(tools_directory)
        tool_handler.write_file_content(f"{tool_name}.json", tool_json)
        print(f"Created MCP tool JSON file for: {tool_name}")
        
        # Step 5: Get the module content for the MCP tool
        print("\n" + "="*60)
        print("Step 5: Retrieving module content...")
        print("="*60)
        print(f"Requesting module for tool: {tool_name}")
        print(f"MCP URL in tool: {vmcp_url}")
        module_response = await client.get(f"{BASE_URL}/tools/{tool_name}/module")
        print(f"Module retrieval response status: {module_response.status_code}")
        print(f"Module retrieval response body: {module_response.text[:500]}")
        if module_response.status_code != 200:
            print(f"✗ Module retrieval error: {module_response.text}")
        assert module_response.status_code == 200, f"Module retrieval failed: {module_response.text}"
        print("✓ Module retrieved successfully")
        
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