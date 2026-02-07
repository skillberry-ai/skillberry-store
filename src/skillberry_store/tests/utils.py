import os
import shutil
import asyncio
import httpx
import json
from urllib.parse import quote


def clean_test_tmp_dir():
    """Removes temporary directories used by the tools service."""

    paths = [
        "/tmp/manifest",
        "/tmp/descriptions",
        "/tmp/files",
        "/tmp/snippets",
        "/tmp/tools",
        "/tmp/skills",
        "/tmp/vmcp",
        "/tmp/metadata",
        "/tmp/tools_descriptions",
        "/tmp/snippets_descriptions",
        "/tmp/skills_descriptions",
        "/tmp/vmcp_descriptions"
    ]
    
    for path in paths:
        if os.path.exists(path):
            print(f"Removing: {path}")
            shutil.rmtree(path, ignore_errors=False)


async def wait_until_server_ready(url="http://127.0.0.1:8000/manifests/", timeout=15):
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
    """Registers a tool manifest with the tools service via HTTP POST."""

    manifest = {
        "programming_language": "python",
        "packaging_format": "mcp",
        "version": "0.0.1",
        "mcp_url": mcp_url,
        "name": name,
        "state": "approved",
    }

    manifest_str = json.dumps(manifest)
    file_manifest_url = quote(manifest_str)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8000/manifests/add?file_manifest={file_manifest_url}",
            headers={"accept": "application/json"},
        )
        assert response.status_code == 200, f"Add manifest failed: {response.text}"
        return response.json()
