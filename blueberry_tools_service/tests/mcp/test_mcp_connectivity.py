import asyncio
import httpx
import pytest
import socket

from blueberry_tools_service.tests.utils import clean_test_tmp_dir, wait_until_server_ready, add_tool_manifest


def get_free_port():
    """Get a free port number."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


@pytest.mark.asyncio
async def test_mcp_mode():
    """Test the BTS server running in MCP mode via subprocess."""

    clean_test_tmp_dir()
    
    mcp_port = get_free_port()
    
    mcp_server_code = f"""
from mcp.server.fastmcp import FastMCP
mcp = FastMCP(name='MathServer', port={mcp_port})

@mcp.tool()
def multiply(a: float, b: float) -> float:
    return a * b

if __name__ == '__main__':
    mcp.run(transport='sse')
"""
    
    mcp_server_proc = await asyncio.create_subprocess_exec(
        "python",
        "-c",
        mcp_server_code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Check if the BTS server is already running, if so, exit with an error
    try:
        await wait_until_server_ready(url="http://127.0.0.1:8000/manifests/", timeout=1)
        raise SystemExit(
            "BTS Server is already running, stop it and re-run the test. exiting !!!"
        )
        return
    except TimeoutError:
        pass

    main_proc = await asyncio.create_subprocess_exec(
        "python", "-m", "blueberry_tools_service.main",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        await wait_until_server_ready()
        await add_tool_manifest(name="multiply", mcp_url=f"http://localhost:{mcp_port}/sse")
        # Add manifest via tools service
        async with httpx.AsyncClient() as client:
            # Execute the tool
            execute_response = await client.post(
                "http://localhost:8000/manifests/execute/multiply",
                json={"a": 5, "b": 5},
                headers={"accept": "application/json"},
            )
            assert (
                execute_response.status_code == 200
            ), f"Execution failed: {execute_response.text}"
            result = execute_response.json()
            print("Execution result:", result)
            numeric_result = float(result["return value"])
            print("Numeric result:", numeric_result)
            assert numeric_result == float(25.0), f"Expected 25.0, got {numeric_result}"

    finally:
        # Cleanup: kill server process
        main_proc.kill()
        # Read to avoid transport issues
        if main_proc.stdout:
            await main_proc.stdout.read()
        if main_proc.stderr:
            await main_proc.stderr.read()
        # Cleanup: kill server process
        mcp_server_proc.kill()
        # Read to avoid transport issues
        if mcp_server_proc.stdout:
            await mcp_server_proc.stdout.read()
        if mcp_server_proc.stderr:
            await mcp_server_proc.stderr.read()

