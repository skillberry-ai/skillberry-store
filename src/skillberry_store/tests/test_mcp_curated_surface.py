"""Unit tests for the Control MCP curated-surface derivation.

The Control MCP exposes only endpoints that opt in via
``openapi_extra={"x-mcp-tool": True}``. ``mcp_operations_from_openapi`` derives
that allow-list from the generated OpenAPI schema, so the CLI and the Control
MCP stay in sync without a hand-maintained list.
"""

from fastapi import FastAPI

from skillberry_store.fast_api.server import mcp_operations_from_openapi


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.get(
        "/things",
        operation_id="list_things",
        openapi_extra={"x-cli-name": "list-things", "x-mcp-tool": True},
    )
    def list_things():
        return []

    # Opted out: has a CLI name but no x-mcp-tool marker (e.g. an admin op).
    @app.post(
        "/admin/purge",
        operation_id="purge_things",
        openapi_extra={"x-cli-name": "purge-things"},
    )
    def purge_things():
        return {}

    # No openapi_extra at all.
    @app.get("/health", operation_id="health")
    def health():
        return {"ok": True}

    return app


def test_includes_only_marked_operations():
    ops = mcp_operations_from_openapi(_build_app().openapi())
    assert ops == ["list_things"]


def test_excludes_unmarked_and_unmarked_extra():
    ops = mcp_operations_from_openapi(_build_app().openapi())
    assert "purge_things" not in ops
    assert "health" not in ops


def test_empty_schema_yields_no_operations():
    assert mcp_operations_from_openapi({}) == []
    assert mcp_operations_from_openapi({"paths": {}}) == []
