import asyncio
import httpx
import pytest

from tests.utils import clean_test_tmp_dir,wait_until_server_ready, add_tool_manifest



@pytest.mark.asyncio
async def test_mcp_mode():
    """Test the BSP server running in MCP mode via subprocess."""

    clean_test_tmp_dir()

    mcp_server_proc = await asyncio.create_subprocess_exec(
    "python", "contrib/mcp/server/server.py",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)


    main_proc  = await asyncio.create_subprocess_exec(
        "python", "main.py",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        await wait_until_server_ready()
        await add_tool_manifest()
        # Add manifest via tools service
        async with httpx.AsyncClient() as client:
            # Execute the tool
            execute_response = await client.post(
                "http://localhost:8000/manifests/execute/multiply",
                json={"a": 5, "b": 5},
                headers={"accept": "application/json"}
            )
            assert execute_response.status_code == 200, f"Execution failed: {execute_response.text}"
            result = execute_response.json()
            print("Execution result:", result)

            # 🔍 Assert expected result
            assert "return value" in result
            assert result["return value"] in ("25", "25.0", 25), "Unexpected execution result"


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
