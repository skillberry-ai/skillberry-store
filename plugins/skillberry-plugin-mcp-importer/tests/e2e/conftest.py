"""
E2E fixtures for MCP importer plugin tests.

The SBS server fixture (`run_sbs`) and the httpx-timeout fixture are provided
by the repo-root conftest.py. This module only owns the mock MCP backend.

The mock MCP backend runs in a SUBPROCESS to avoid the sse_starlette
AppStatus.should_exit_event singleton being shared between two uvicorn
servers running in different threads with different event loops.
"""

import socket
import subprocess
import sys
import textwrap
import time

import pytest

BASE_URL = "http://localhost:8000"
MOCK_MCP_PORT = 9500
MOCK_MCP_URL = f"http://localhost:{MOCK_MCP_PORT}/sse"


def _wait_for_port(host: str, port: int, timeout: int = 30) -> None:
    """Block until the TCP port accepts connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except (socket.error, ConnectionRefusedError):
            time.sleep(0.2)
    raise TimeoutError(f"{host}:{port} not ready within {timeout}s")


_MOCK_MCP_SCRIPT = textwrap.dedent("""
    import uvicorn
    from mcp.server.fastmcp import FastMCP

    mock = FastMCP("test-mcp-backend")

    @mock.tool()
    def echo(message: str) -> str:
        \"\"\"Echo a message back.\"\"\"
        return message

    uvicorn.run(mock.sse_app(), host="127.0.0.1", port={port}, log_level="error")
""")


@pytest.fixture(scope="session")
def mock_mcp_backend():
    """
    Start a minimal FastMCP SSE server exposing an 'echo' tool on port 9500.

    Runs in a subprocess so that sse_starlette's AppStatus singleton is
    isolated from the SBS process, avoiding event-loop binding conflicts.
    """
    script = _MOCK_MCP_SCRIPT.format(port=MOCK_MCP_PORT)
    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_for_port("127.0.0.1", MOCK_MCP_PORT, timeout=30)
        yield MOCK_MCP_URL
    finally:
        proc.terminate()
        proc.wait(timeout=5)
