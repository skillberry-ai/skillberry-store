import asyncio
import os
import pytest
import requests
from mcp import ClientSession
from mcp.client.sse import sse_client
from skillberry_store.tests.utils import clean_test_tmp_dir, wait_until_server_ready, add_tool_manifest
from skillberry_store.modules.tool_type import ToolType


@pytest.mark.asyncio
async def test_virtual_mcp_servers():
    """Test the SBS server virtual MCP server"""
    clean_test_tmp_dir()
    
    # Clean up old virtual MCP servers file
    vmcp_file = "/tmp/vmcp_servers.json"
    if os.path.exists(vmcp_file):
        os.remove(vmcp_file)

    env = os.environ.copy()

    env["MCP_MODE"] = "true"
    main_proc = await asyncio.create_subprocess_exec(
        "python", "-m", "skillberry_store.main",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=os.path.dirname(
            os.path.abspath(__file__).rstrip("/tests/e2e/test_virtual_mcp_servers.py"))
    )

    try:
        await wait_until_server_ready(url="http://127.0.0.1:8000/manifests/", timeout=60)
                
        # Step 1: Add a simple tool that adds two numbers using the manifest API
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
        response = requests.post(
            "http://127.0.0.1:8000/tools/add",
            params={"tool_type": tool_type, "update": "true"},
            files={"tool": (f"{tool_name}.py", tool_code, "text/x-python")}
        )
        assert response.status_code == 200

        # Step 2: Create an MCP virtual server from search term against the tool name
        search_term = f"name:{tool_name}"
        response = requests.post(
            "http://localhost:8000/vmcp_servers/add_server_from_search_term",
            params={"search_term": search_term},
        )
        assert response.status_code == 200

        # Step 3: List the MCP virtual servers to see that the virtual server exists
        response = requests.get("http://localhost:8000/vmcp_servers/")
        assert response.status_code == 200
        vmcp_servers = response.json()["virtual_mcp_servers"]
        assert f"Search Term Server - {search_term}" in vmcp_servers

        # Step 4: Get virtual MCP server details and invoke function
        vmcp_server_name = f"Search Term Server - {search_term}"
        response = requests.get(f"http://localhost:8000/vmcp_servers/{vmcp_server_name}")
        assert response.status_code == 200
        vmcp_server_details = response.json()
        vmcp_server_port = vmcp_server_details["port"]
        print (f"Virtual MCP server port: {vmcp_server_port}")
        
        # Test tool execution through the virtual MCP server using MCP client
        async with sse_client(f"http://localhost:{vmcp_server_port}/sse") as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()    
                result = await session.call_tool(tool_name, {"a": 2, "b": 3})
                assert result.content[0].text == "5"
        
        # Step 5: Delete virtual MCP server and verify cleanup
        response = requests.delete(f"http://localhost:8000/vmcp_servers/{vmcp_server_name}")
        assert response.status_code == 200
        
        # Verify the server is no longer in the list
        response = requests.get("http://localhost:8000/vmcp_servers/")
        assert response.status_code == 200
        vmcp_servers_after_delete = response.json()["virtual_mcp_servers"]
        assert vmcp_server_name not in vmcp_servers_after_delete
    
    finally:
        # Cleanup: kill server process
        main_proc.kill()
        # Read and display server output
        if main_proc.stdout:
            stdout_data = await main_proc.stdout.read()
            if stdout_data:
                print("\n=== SERVER STDOUT ===")
                print(stdout_data.decode())
        if main_proc.stderr:
            stderr_data = await main_proc.stderr.read()
            if stderr_data:
                print("\n=== SERVER STDERR ===")
                print(stderr_data.decode())
