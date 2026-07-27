"""Unit tests for the route→(resource, verb) mapper."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from skillberry_store.access_control.mapper import (
    UnmappedRouteError,
    map_request,
    resource_for,
    resolve_route,
    verb_for,
)


def _app_with_routes() -> FastAPI:
    app = FastAPI()

    @app.get("/skills/", tags=["skills"])
    def list_skills():
        return []

    @app.get("/skills/{uuid_or_name}", tags=["skills"])
    def get_skill(uuid_or_name: str):
        return {}

    @app.post("/skills/", tags=["skills"])
    def create_skill():
        return {}

    @app.put("/skills/{uuid_or_name}", tags=["skills"])
    def update_skill(uuid_or_name: str):
        return {}

    @app.delete("/skills/{uuid_or_name}", tags=["skills"])
    def delete_skill(uuid_or_name: str):
        return {}

    @app.post("/skills/import-anthropic", tags=["skills"])
    def import_skill():
        return {}

    @app.get("/skills/{uuid_or_name}/export-anthropic", tags=["skills"])
    def export_skill(uuid_or_name: str):
        return {}

    @app.get("/search/skills", tags=["skills"])
    def search_skills():
        return []

    @app.post("/tools/{uuid_or_name}/execute", tags=["tools"])
    def execute_tool(uuid_or_name: str):
        return {}

    @app.post("/tools/add", tags=["tools"])
    def add_tool():
        return {}

    @app.post("/vmcp/{uuid_or_name}/start", tags=["vmcp_servers"])
    def start_vmcp(uuid_or_name: str):
        return {}

    @app.delete("/admin/purge-all", tags=["admin"])
    def purge_all():
        return {}

    @app.get("/admin/backup", tags=["admin"])
    def backup():
        return {}

    @app.get("/facets/skills", tags=["skills"])
    def facets():
        return {}

    @app.get(
        "/custom/thing",
        tags=["plugins"],
        openapi_extra={"x-rbac-resource": "system", "x-rbac-verb": "admin"},
    )
    def custom():
        return {}

    return app


def _fake_request(app: FastAPI, method: str, path: str) -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "app": app,
    }
    return Request(scope)


@pytest.mark.parametrize(
    "method,path,expected",
    [
        ("GET", "/skills/", ("skills", "list")),
        ("GET", "/skills/abc", ("skills", "get")),
        ("POST", "/skills/", ("skills", "create")),
        ("PUT", "/skills/abc", ("skills", "update")),
        ("DELETE", "/skills/abc", ("skills", "delete")),
        ("POST", "/skills/import-anthropic", ("skills", "create")),
        ("GET", "/skills/abc/export-anthropic", ("skills", "get")),
        ("GET", "/search/skills", ("skills", "search")),
        ("POST", "/tools/abc/execute", ("tools", "execute")),
        ("POST", "/tools/add", ("tools", "create")),
        ("POST", "/vmcp/abc/start", ("vmcp_servers", "execute")),
        ("DELETE", "/admin/purge-all", ("admin", "admin")),
        ("GET", "/admin/backup", ("admin", "admin")),
        ("GET", "/facets/skills", ("skills", "list")),
    ],
)
def test_mapping_rules(method, path, expected):
    app = _app_with_routes()
    request = _fake_request(app, method, path)
    resource, verb, _ = map_request(request)
    assert (resource, verb) == expected


def test_openapi_extra_overrides():
    app = _app_with_routes()
    request = _fake_request(app, "GET", "/custom/thing")
    resource, verb, _ = map_request(request)
    assert resource == "system"
    assert verb == "admin"


def test_unmapped_route_raises():
    app = _app_with_routes()
    request = _fake_request(app, "GET", "/does/not/exist")
    with pytest.raises(UnmappedRouteError):
        map_request(request)


def test_route_helpers_are_reusable():
    app = _app_with_routes()
    request = _fake_request(app, "GET", "/skills/abc")
    route = resolve_route(request)
    assert resource_for(route) == "skills"
    assert verb_for(request, route) == "get"


def test_integration_with_test_client_smoke():
    # Sanity: the app itself still serves the routes we mapped above.
    app = _app_with_routes()
    client = TestClient(app)
    assert client.get("/skills/").status_code == 200
