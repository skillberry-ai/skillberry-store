"""Unit tests for the MCP-friendly /tools/add_code endpoint.

Mirrors /tools/add (add_tool_from_python) but takes the Python source as a JSON
string instead of a file upload, so it works over the MCP bridge (which cannot
transmit multipart/octet-stream file bodies). The endpoint normalizes the
module name and forwards the request to ``ToolsService.add_from_python``.
"""

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from skillberry_store.fast_api.tools_api import register_tools_api

CODE = (
    "def add_two_nums(a: float, b: float) -> float:\n"
    '    """Add two numbers together.\n'
    "\n"
    "    Args:\n"
    "        a: The first number.\n"
    "        b: The second number.\n"
    "\n"
    "    Returns:\n"
    "        The sum a + b.\n"
    '    """\n'
    "    return a + b\n"
)


def _client():
    service = MagicMock()

    def _add_from_python(
        file_bytes, file_name=None, selected_func=None, update_existing=False
    ):
        return {
            "message": "ok",
            "name": "add_two_nums",
            "uuid": "u1",
            "module_name": file_name,
        }

    service.add_from_python.side_effect = _add_from_python

    app = FastAPI()
    register_tools_api(app, service=service)
    return TestClient(app), service


def test_add_tool_from_code_encodes_source_and_forwards():
    client, service = _client()

    resp = client.post("/tools/add_code", json={"code": CODE})

    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "add_two_nums"
    # The string source is forwarded to the service as UTF-8 bytes.
    kwargs = service.add_from_python.call_args.kwargs
    assert kwargs["file_bytes"] == CODE.encode("utf-8")
    assert kwargs["file_name"].endswith(".py")
    assert kwargs["update_existing"] is False


def test_add_tool_from_code_honors_module_name():
    client, service = _client()

    resp = client.post(
        "/tools/add_code", json={"code": CODE, "module_name": "math_utils"}
    )

    assert resp.status_code == 200, resp.text
    # A name without .py is normalized to a .py module file.
    assert service.add_from_python.call_args.kwargs["file_name"] == "math_utils.py"


def test_add_tool_from_code_requires_code():
    client, _ = _client()

    # Missing required `code` field → 422 from request-body validation.
    assert client.post("/tools/add_code", json={}).status_code == 422
