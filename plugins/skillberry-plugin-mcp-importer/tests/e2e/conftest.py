"""
E2E fixtures for MCP importer plugin tests.

Starts two servers for the session:
  - SBS (skillberry store) on port 8000
  - Mock MCP backend on port 9500  (exposes a single 'echo' tool)

The mock MCP backend runs in a SUBPROCESS to avoid the sse_starlette
AppStatus.should_exit_event singleton being shared between two uvicorn
servers running in different threads with different event loops.
"""

import asyncio
import logging
import os
import socket
import subprocess
import sys
import textwrap
import threading
import time

import httpx
import pytest

logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
MOCK_MCP_PORT = 9500
MOCK_MCP_URL = f"http://localhost:{MOCK_MCP_PORT}/sse"


# ── SBS server ────────────────────────────────────────────────────────────────

async def _wait_for_http(url: str, timeout: int = 60) -> None:
    """Poll url until it returns a non-5xx response or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    async with httpx.AsyncClient() as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                r = await client.get(url, timeout=2.0)
                if r.status_code < 500:
                    return
            except Exception:
                pass
            await asyncio.sleep(0.5)
    raise TimeoutError(f"{url} did not become ready within {timeout}s")


@pytest.fixture(scope="session")
def run_sbs():
    """Start the SBS server in a daemon thread, wait until it is ready."""
    from skillberry_store.fast_api.server import SBS
    from skillberry_store.tests.utils import clean_test_tmp_dir

    clean_test_tmp_dir()
    os.environ["ENABLE_UI"] = "false"
    os.environ["PROMETHEUS_METRICS_PORT"] = "0"

    def _start():
        try:
            SBS().run()
        except Exception as exc:
            logger.error(f"SBS failed: {exc}")

    thread = threading.Thread(target=_start, daemon=True)
    thread.start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_wait_for_http(f"{BASE_URL}/tools/", timeout=60))
    finally:
        loop.close()

    yield

    clean_test_tmp_dir()


# ── Socket readiness check ────────────────────────────────────────────────────

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


# ── Mock MCP backend (subprocess) ────────────────────────────────────────────

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


# ── httpx timeout ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def configure_httpx_defaults():
    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = httpx.Timeout(120.0, connect=10.0)
        original_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = patched_init
    yield
    httpx.AsyncClient.__init__ = original_init
