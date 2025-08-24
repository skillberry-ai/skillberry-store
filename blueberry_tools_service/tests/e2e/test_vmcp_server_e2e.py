import asyncio
import os
import pytest
import requests
from blueberry_tools_service.tests.utils import clean_test_tmp_dir, wait_until_server_ready, add_tool_manifest


@pytest.mark.asyncio
async def test_virtual_mcp_servers():
    """Test the BTS server virtual MCP server"""
    clean_test_tmp_dir()

    env = os.environ.copy()

    env["MCP_MODE"] = "true"
    main_proc = await asyncio.create_subprocess_exec(
        "python", "-m", "blueberry_tools_service.main",
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
        tool_code = """
    def add_numbers(a, b):
        return a + b
    """
        response = requests.post(
            "http://localhost:8000/tools/add",
            files={"tool": (f"{tool_name}.py", tool_code)},
            data={"tool_type": tool_type, "tool_name": tool_name},
        )
        assert response.status_code == 200

        # Step 2: Create an MCP virtual server from search term against the tool name
        search_term = tool_name
        response = requests.post(
            "http://localhost:8000/vmcp_servers/add_server_from_search_term",
            json={"search_term": search_term},
        )
        assert response.status_code == 200

        # Step 3: List the MCP virtual servers to see that the virtual server exists
        response = requests.get("http://localhost:8000/vmcp_servers/")
        assert response.status_code == 200
        vmcp_servers = response.json()["vmcp_servers"]
        assert f"Search Term Server - {search_term}" in vmcp_servers

        # Step 4: Invoke the tool with parameters using the MCP server invoke API
        vmcp_server_name = f"Search Term Server - {search_term}"
        response = requests.get(f"http://localhost:8000/vmcp_servers/{vmcp_server_name}")
        assert response.status_code == 200
        vmcp_server_details = response.json()
        vmcp_server_port = vmcp_server_details["port"]
        response = requests.post(
            f"http://localhost:{vmcp_server_port}/tools/invoke/{tool_name}",
            json={"parameters": {"a": 2, "b": 3}},
        )
        assert response.status_code == 200
        assert response.json() == 5

        # Step 5: Cleanup
        response = requests.delete(f"http://localhost:8000/vmcp_servers/{vmcp_server_name}")
        assert response.status_code == 200
    
    finally:
        # Cleanup: kill server process
        main_proc.kill()
        # Read to avoid transport issues
        if main_proc.stdout:
            await main_proc.stdout.read()
        if main_proc.stderr:
            await main_proc.stderr.read()
