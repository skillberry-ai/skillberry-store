import asyncio
import json
import os
import shutil
from urllib.parse import quote

import httpx

from skillberry_store.tools.configure import _default_sbs_dir


def clean_test_tmp_dir():
    """Removes temporary directories used by the tools service."""

    paths = [
        _default_sbs_dir("files"),
        _default_sbs_dir("snippets"),
        _default_sbs_dir("tools"),
        _default_sbs_dir("skills"),
        _default_sbs_dir("vmcp"),
        _default_sbs_dir("metadata"),
        _default_sbs_dir("tools_descriptions"),
        _default_sbs_dir("snippets_descriptions"),
        _default_sbs_dir("skills_descriptions"),
        _default_sbs_dir("vmcp_descriptions"),
    ]

    for path in paths:
        if os.path.exists(path):
            print(f"Removing: {path}")
            shutil.rmtree(path, ignore_errors=False)


async def wait_until_server_ready(url="http://127.0.0.1:8000/health/ready", timeout=60):
    """Waits until the server at the given URL responds with HTTP 200 or times out."""

    start = asyncio.get_event_loop().time()
    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if response.status_code == 200:
                    print("Server is ready")
                    return
        except httpx.RequestError:
            pass  # server not up yet

        if asyncio.get_event_loop().time() - start > timeout:
            raise TimeoutError(f"Server did not become ready within {timeout} seconds")

        await asyncio.sleep(0.5)


async def add_tool_manifest(
    name: str = "multiply", mcp_url: str = "http://localhost:8080/sse"
):
    """Registers a tool with the tools service via HTTP POST.

    Note: This function is deprecated and should use the /tools/ endpoint instead.
    """

    tool = {
        "programming_language": "python",
        "packaging_format": "mcp",
        "version": "0.0.1",
        "mcp_url": mcp_url,
        "name": name,
        "state": "approved",
    }

    tool_str = json.dumps(tool)
    file_tool_url = quote(tool_str)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8000/tools/?tool={file_tool_url}",
            headers={"accept": "application/json"},
        )
        assert response.status_code == 200, f"Add tool failed: {response.text}"
        return response.json()
