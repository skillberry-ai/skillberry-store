"""
E2E test: import MCP tools via the plugin, create a VMCP server, invoke a tool.

Flow:
  1. POST /plugins/mcp-importer/import-tools  →  echo tool created in store
  2. POST /skills/                             →  skill with that tool UUID
  3. POST /vmcp_servers/                       →  VMCP server on dynamic port
  4. Wait for VMCP server to report running=True
  5. Connect via SSE to VMCP server, call echo("hello"), assert response == "hello"
"""

import asyncio
import uuid

import httpx
import pytest
from mcp import ClientSession
from mcp.client.sse import sse_client

from tests.e2e.conftest import BASE_URL

VMCP_PORT = 9600


async def _wait_for_vmcp(client: httpx.AsyncClient, vmcp_name: str, timeout: int = 30) -> None:
    """Poll GET /vmcp_servers/{name} until running == True."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        r = await client.get(f"{BASE_URL}/vmcp_servers/{vmcp_name}")
        if r.status_code == 200 and r.json().get("running"):
            return
        await asyncio.sleep(1.0)
    raise TimeoutError(f"VMCP server '{vmcp_name}' did not become running within {timeout}s")


@pytest.mark.asyncio
async def test_mcp_import_then_vmcp_tunnel_executes_tool(run_sbs, mock_mcp_backend):
    """
    Full tunnel test:
      plugin imports echo from mock MCP backend
      → VMCP server wraps it
      → calling echo via VMCP SSE returns the correct result
    """
    vmcp_name = f"test_tunnel_vmcp_{uuid.uuid4().hex[:8]}"

    async with httpx.AsyncClient() as client:

        # ── Step 1: import tools from mock MCP backend ────────────────────────
        import_response = await client.post(
            f"{BASE_URL}/plugins/mcp-importer/import-tools",
            json={"mcp_url": mock_mcp_backend},
        )
        assert import_response.status_code == 200, import_response.text
        import_data = import_response.json()
        assert import_data["imported"] >= 1, f"Expected at least 1 tool, got: {import_data}"

        echo_entry = next(
            (t for t in import_data["tools"] if t["name"] == "echo"), None
        )
        assert echo_entry is not None, f"'echo' tool not found in: {import_data['tools']}"
        echo_uuid = echo_entry["uuid"]

        # ── Step 2: create a skill containing the echo tool ───────────────────
        skill_response = await client.post(
            f"{BASE_URL}/skills/",
            params={
                "name": f"test_mcp_skill_{uuid.uuid4().hex[:8]}",
                "description": "Test skill for MCP tunnel e2e",
                "tool_uuids": [echo_uuid],
            },
        )
        assert skill_response.status_code == 200, skill_response.text
        skill_uuid = skill_response.json()["uuid"]

        # ── Step 3: create VMCP server from the skill ─────────────────────────
        vmcp_response = await client.post(
            f"{BASE_URL}/vmcp_servers/",
            params={
                "name": vmcp_name,
                "description": "E2E tunnel test VMCP server",
                "port": VMCP_PORT,
                "skill_uuid": skill_uuid,
            },
        )
        assert vmcp_response.status_code == 200, vmcp_response.text
        vmcp_port = vmcp_response.json()["port"]

        # ── Step 4: wait for VMCP server to be running ────────────────────────
        await _wait_for_vmcp(client, vmcp_name)

        # ── Step 5: call echo via VMCP SSE — verify tunnel works ──────────────
        vmcp_sse_url = f"http://localhost:{vmcp_port}/sse"
        async with sse_client(vmcp_sse_url, sse_read_timeout=30) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=10.0)
                result = await asyncio.wait_for(
                    session.call_tool("echo", {"message": "hello"}),
                    timeout=15.0,
                )

        assert result is not None
        # result.content is a list of content blocks; extract the text
        content_texts = [
            block.text for block in result.content
            if hasattr(block, "text")
        ]
        assert "hello" in " ".join(content_texts), (
            f"Expected 'hello' in VMCP response, got: {result.content}"
        )

        # ── Cleanup ───────────────────────────────────────────────────────────
        await client.delete(f"{BASE_URL}/vmcp_servers/{vmcp_name}")
