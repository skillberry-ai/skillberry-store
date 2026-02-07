import asyncio
import os
import pytest
import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client
from skillberry_store.tests.e2e.fixtures import run_sbs
from skillberry_store.modules.tool_type import ToolType

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_virtual_mcp_servers(run_sbs):
    """Test the SBS server virtual MCP server"""
    async with httpx.AsyncClient() as client:
        # Step 1: Add a simple tool that adds two numbers using the manifest API
        skill_name = "test_skill_for_vmcp"
        tool_name = "add_numbers"
        tool_type = "code/python"
        tool_code = """def add_numbers(a, b):
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
            params={"tool_type": tool_type, "update": "true"},
            files={"tool": (f"{tool_name}.py", tool_code, "text/x-python")}
        )
        if response.status_code != 200:
            print(f"Tool creation failed with status {response.status_code}")
            print(f"Response: {response.text}")
        assert response.status_code == 200, f"Tool creation failed: {response.text}"
        tool_response = response.json()
        tool_uuid = tool_response.get("uuid")

        # Step 1b: Create a snippet for testing prompts
        snippet_name = "test_snippet_for_vmcp"
        snippet_data = {
            "name": snippet_name,
            "description": "Test snippet for VMCP server prompts",
            "content": "This is a test snippet content for MCP prompts",
            "content_type": "text/plain"
        }
        response = await client.post(
            f"{BASE_URL}/snippets/",
            params=snippet_data
        )
        assert response.status_code == 200, f"Snippet creation failed: {response.text}"
        snippet_response = response.json()
        snippet_uuid = snippet_response.get("uuid")
        print(f"Created snippet with UUID: {snippet_uuid}")

        # Step 2: Create a skill with the tool and snippet
        skill_data = {
            "name": skill_name,
            "description": "Test skill for VMCP server with tools and snippets",
            "tool_uuids": tool_uuid,  # Pass as single value, FastAPI will handle the list
            "snippet_uuids": snippet_uuid
        }
        response = await client.post(
            f"{BASE_URL}/skills/",
            params=skill_data
        )
        assert response.status_code == 200
        skill_response = response.json()
        skill_uuid = skill_response.get("uuid")
        print(f"Created skill with UUID: {skill_uuid}")
        print(f"Skill response: {skill_response}")
        
        # Verify the skill was created with the tool
        response = await client.get(f"{BASE_URL}/skills/{skill_name}")
        assert response.status_code == 200
        skill_details = response.json()
        print(f"Skill details: {skill_details}")
        assert len(skill_details.get("tools", [])) > 0, "Skill should have at least one tool"

        # Step 3: Create an MCP virtual server with the skill
        vmcp_server_name = f"test_vmcp_server_{tool_name}"
        vmcp_data = {
            "name": vmcp_server_name,
            "description": "Test VMCP server for e2e testing",
            # Don't specify port - let the server auto-assign one
            "skill_uuid": skill_uuid
        }
        response = await client.post(
            f"{BASE_URL}/vmcp_servers/",
            params=vmcp_data
        )
        if response.status_code != 200:
            print(f"VMCP server creation failed with status {response.status_code}")
            print(f"Response: {response.text}")
        assert response.status_code == 200, f"VMCP creation failed: {response.text}"
        
        # Wait for the VMCP server to fully start - give it more time for SSE endpoint
        print("Waiting for VMCP server SSE endpoint to be ready...")
        await asyncio.sleep(5)

        # Step 4: List the MCP virtual servers to see that the virtual server exists
        response = await client.get(f"{BASE_URL}/vmcp_servers/")
        assert response.status_code == 200
        vmcp_servers = response.json()["virtual_mcp_servers"]
        assert vmcp_server_name in vmcp_servers

        # Step 5: Get virtual MCP server details and invoke function
        response = await client.get(f"{BASE_URL}/vmcp_servers/{vmcp_server_name}")
        assert response.status_code == 200
        vmcp_server_details = response.json()
        vmcp_server_port = vmcp_server_details["port"]
        print(f"Virtual MCP server port: {vmcp_server_port}")
        print(f"VMCP server details: {vmcp_server_details}")

        # Test tool execution through the virtual MCP server using MCP client
        print(f"Attempting to connect to MCP server at http://localhost:{vmcp_server_port}/sse")
        
        # Retry logic for SSE endpoint - it may take time to start
        max_retries = 5
        retry_delay = 2
        sse_ready = False
        
        for attempt in range(max_retries):
            try:
                response = await client.get(f"http://localhost:{vmcp_server_port}/sse")
                print(f"SSE endpoint status: {response.status_code}")
                if response.status_code in [200, 404]:  # 404 is ok for SSE GET
                    sse_ready = True
                    break
            except Exception as e:
                print(f"Attempt {attempt + 1}/{max_retries}: Failed to connect to SSE endpoint: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
        
        assert sse_ready, f"SSE endpoint not ready after {max_retries} attempts"
        
        # Connect via MCP client
        async with asyncio.timeout(15):  # 15 second timeout
            async with sse_client(f"http://localhost:{vmcp_server_port}/sse") as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # List available tools
                    tools_list = await session.list_tools()
                    print(f"Available tools: {[t.name for t in tools_list.tools]}")
                    assert len(tools_list.tools) > 0, "No tools found"
                    assert tool_name in [t.name for t in tools_list.tools], f"Tool '{tool_name}' not found"
                    
                    # Call the tool with string arguments (as defined in the tool schema)
                    result = await session.call_tool(tool_name, {"a": "2", "b": "3"})
                    print(f"Tool execution result: {result}")
                    assert len(result.content) > 0, "No content in result"
                    assert result.content[0].text == "5", f"Expected '5', got '{result.content[0].text}'"
                    
                    # List available prompts
                    prompts_list = await session.list_prompts()
                    print(f"Available prompts: {[p.name for p in prompts_list.prompts]}")
                    assert len(prompts_list.prompts) > 0, "No prompts found"
                    assert snippet_name in [p.name for p in prompts_list.prompts], f"Prompt '{snippet_name}' not found"
                    
                    # Get the prompt
                    prompt_result = await session.get_prompt(snippet_name)
                    print(f"Prompt result: {prompt_result}")
                    assert len(prompt_result.messages) > 0, "No messages in prompt result"
        
        # Step 6: Delete virtual MCP server and verify cleanup
        response = await client.delete(f"{BASE_URL}/vmcp_servers/{vmcp_server_name}")
        assert response.status_code == 200
        
        # Step 7: Verify the server is no longer in the list
        response = await client.get(f"{BASE_URL}/vmcp_servers/")
        assert response.status_code == 200
        vmcp_servers_after_delete = response.json()["virtual_mcp_servers"]
        assert vmcp_server_name not in vmcp_servers_after_delete
        
        # Step 8: Clean up skill and snippet
        response = await client.delete(f"{BASE_URL}/skills/{skill_name}")
        assert response.status_code == 200
        
        response = await client.delete(f"{BASE_URL}/snippets/{snippet_name}")
        assert response.status_code == 200
