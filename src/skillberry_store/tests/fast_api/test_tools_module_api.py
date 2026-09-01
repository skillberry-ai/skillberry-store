"""REST coverage for the tool module file endpoints.

``GET /tools/{uuid_or_name}/module`` already existed; ``PUT`` is its write
counterpart. Both are exercised against a real ``ToolsService`` backed by a
mocked ``ObjectHandler``, so the service's error taxonomy (``KeyError`` for a
missing tool, ``ValueError`` for a tool with nothing to write) is checked
together with the status codes it maps to.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from skillberry_store.fast_api.tools_api import register_tools_api
from skillberry_store.services.tools_service import ToolsService


def _make_client(tool=None):
    app = FastAPI()
    handler = MagicMock()
    handler.descriptions = None
    handler.resolve_to_uuid_or_error.return_value = "cccc-3333"
    handler.read_dict.return_value = tool if tool is not None else {
        "uuid": "cccc-3333",
        "name": "t1",
        "module_name": "t1.py",
        "packaging_format": "code",
    }
    handler.read_file.return_value = "def hello(): pass"
    register_tools_api(app, service=ToolsService(handler))
    return TestClient(app), handler


def test_get_module_returns_plain_text():
    client, _ = _make_client()

    response = client.get("/tools/t1/module")

    assert response.status_code == 200
    assert response.text == "def hello(): pass"
    assert response.headers["content-type"].startswith("text/plain")


def test_put_module_writes_resolved_filename():
    """The caller sends only content; the filename comes from the manifest."""
    client, handler = _make_client()

    response = client.put("/tools/t1/module", json={"content": "print('fixed')\n"})

    assert response.status_code == 200
    assert "updated successfully" in response.json()["message"]
    handler.write_file.assert_called_once_with(
        "cccc-3333", "t1.py", "print('fixed')\n"
    )


def test_put_module_missing_tool_is_404():
    client, handler = _make_client()
    handler.resolve_to_uuid_or_error.side_effect = HTTPException(
        status_code=404, detail="not found"
    )

    response = client.put("/tools/nope/module", json={"content": "x"})

    assert response.status_code == 404
    handler.write_file.assert_not_called()


@pytest.mark.parametrize(
    "tool,expected_detail",
    [
        (
            {"uuid": "cccc-3333", "name": "t1", "packaging_format": "mcp"},
            "MCP-packaged",
        ),
        ({"uuid": "cccc-3333", "name": "t1"}, "no module file"),
    ],
    ids=["mcp_packaged", "no_module_name"],
)
def test_put_module_without_writable_module_is_400(tool, expected_detail):
    """A tool that exists but has no stored module is a bad request, not a 404."""
    client, handler = _make_client(tool=tool)

    response = client.put("/tools/t1/module", json={"content": "x"})

    assert response.status_code == 400
    assert expected_detail in response.json()["detail"]
    handler.write_file.assert_not_called()


def test_put_module_requires_content_field():
    """The body is a model, so a missing field is a 422 from validation."""
    client, _ = _make_client()

    assert client.put("/tools/t1/module", json={}).status_code == 422
