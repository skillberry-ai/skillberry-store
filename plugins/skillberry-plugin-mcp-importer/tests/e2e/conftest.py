"""
E2E fixtures for MCP importer plugin tests.

Starts two servers for the session:
  - SBS (skillberry store) on port 8000
  - Mock MCP backend on port 9500  (exposes a single 'echo' tool)
"""

import asyncio
import logging
import os
import threading

import httpx
import pytest
import uvicorn
from mcp.server.fastmcp import FastMCP

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


# ── Mock MCP backend ──────────────────────────────────────────────────────────

def _build_mock_mcp_app() -> FastMCP:
    mock = FastMCP("test-mcp-backend")

    @mock.tool()
    def echo(message: str) -> str:
        """Echo a message back."""
        return message

    return mock


@pytest.fixture(scope="session")
def mock_mcp_backend():
    """Start a minimal FastMCP SSE server exposing an 'echo' tool on port 9500."""
    mock_app = _build_mock_mcp_app()
    starlette_app = mock_app.sse_app()

    def _start():
        uvicorn.run(
            starlette_app,
            host="127.0.0.1",
            port=MOCK_MCP_PORT,
            log_level="error",
        )

    thread = threading.Thread(target=_start, daemon=True)
    thread.start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_wait_for_http(MOCK_MCP_URL, timeout=30))
    finally:
        loop.close()

    yield MOCK_MCP_URL


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
