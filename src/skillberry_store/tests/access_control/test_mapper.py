"""Unit tests for the route→(resource, verb) mapper.

Routes carry their (resource, verb) explicitly on ``openapi_extra`` —
what the ``@requires(...)`` decorator stamps in real code (see
r13 in docs/design/access-control.md). The mapper reads those keys and
raises ``UnmarkedRouteError`` when they are missing.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from skillberry_store.access_control.mapper import (
    UnmappedRouteError,
    UnmarkedRouteError,
    map_request,
    resource_for,
    resolve_route,
    verb_for_route,
)


def _rbac(resource: str, verb: str, extra: dict | None = None) -> dict:
    """Build an ``openapi_extra`` dict with the RBAC markers.

    Mirrors what @requires stamps at runtime — used directly here to
    keep the mapper unit tests independent of the decorator wiring in
    SBS.__init__.
    """
    d: dict = {"x-rbac-resource": resource, "x-rbac-verb": verb}
    if extra:
        d.update(extra)
    return d


def _app_with_routes() -> FastAPI:
    app = FastAPI()

    @app.get("/skills/", tags=["skills"], openapi_extra=_rbac("skills", "list"))
    def list_skills():
        return []

    @app.get(
        "/skills/{uuid_or_name}",
        tags=["skills"],
        openapi_extra=_rbac("skills", "get"),
    )
    def get_skill(uuid_or_name: str):
        return {}

    @app.post("/skills/", tags=["skills"], openapi_extra=_rbac("skills", "create"))
    def create_skill():
        return {}

    @app.put(
        "/skills/{uuid_or_name}",
        tags=["skills"],
        openapi_extra=_rbac("skills", "update"),
    )
    def update_skill(uuid_or_name: str):
        return {}

    @app.delete(
        "/skills/{uuid_or_name}",
        tags=["skills"],
        openapi_extra=_rbac("skills", "delete"),
    )
    def delete_skill(uuid_or_name: str):
        return {}

    @app.post(
        "/skills/import-anthropic",
        tags=["skills"],
        openapi_extra=_rbac("skills", "create"),
    )
    def import_skill():
        return {}

    @app.get(
        "/skills/{uuid_or_name}/export-anthropic",
        tags=["skills"],
        openapi_extra=_rbac("skills", "get"),
    )
    def export_skill(uuid_or_name: str):
        return {}

    @app.get(
        "/search/skills", tags=["skills"], openapi_extra=_rbac("skills", "search")
    )
    def search_skills():
        return []

    @app.post(
        "/tools/{uuid_or_name}/execute",
        tags=["tools"],
        openapi_extra=_rbac("tools", "execute"),
    )
    def execute_tool(uuid_or_name: str):
        return {}

    @app.post("/tools/add", tags=["tools"], openapi_extra=_rbac("tools", "create"))
    def add_tool():
        return {}

    @app.post(
        "/vmcp/{uuid_or_name}/start",
        tags=["vmcp_servers"],
        openapi_extra=_rbac("vmcp_servers", "execute"),
    )
    def start_vmcp(uuid_or_name: str):
        return {}

    @app.delete(
        "/admin/purge-all", tags=["admin"], openapi_extra=_rbac("admin", "admin")
    )
    def purge_all():
        return {}

    @app.get(
        "/admin/backup", tags=["admin"], openapi_extra=_rbac("admin", "admin")
    )
    def backup():
        return {}

    @app.get(
        "/facets/skills", tags=["skills"], openapi_extra=_rbac("skills", "list")
    )
    def facets():
        return {}

    # Unmarked route — exercises the fail-safe error path in the mapper.
    @app.get("/legacy/unmarked", tags=["plugins"])
    def unmarked():
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
def test_mapping_reads_declared_markers(method, path, expected):
    app = _app_with_routes()
    request = _fake_request(app, method, path)
    resource, verb, _ = map_request(request)
    assert (resource, verb) == expected


def test_unmarked_route_raises():
    """A route without ``x-rbac-*`` markers must fail — fail-safe defaults."""
    app = _app_with_routes()
    request = _fake_request(app, "GET", "/legacy/unmarked")
    with pytest.raises(UnmarkedRouteError):
        map_request(request)


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
    assert verb_for_route(route) == "get"


def test_integration_with_test_client_smoke():
    # Sanity: the app itself still serves the routes we mapped above.
    app = _app_with_routes()
    client = TestClient(app)
    assert client.get("/skills/").status_code == 200


def test_map_request_uses_scope_route_fast_path():
    """When ``scope['route']`` is populated (as it is on the production
    request path, because the enforce dep runs after routing), the mapper
    must use it directly rather than walking the app's route table.

    Simulated with an app whose route table is empty: a walk would raise
    ``UnmappedRouteError``. If the mapper honors ``scope['route']``, the
    call succeeds and returns the pre-stamped route's ``(resource, verb)``.
    """
    from fastapi.routing import APIRoute

    donor_app = _app_with_routes()
    donor_route = next(
        r
        for r in donor_app.routes
        if isinstance(r, APIRoute) and r.path == "/tools/{uuid_or_name}/execute"
    )

    empty_app = FastAPI()
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/tools/abc/execute",
        "raw_path": b"/tools/abc/execute",
        "query_string": b"",
        "headers": [],
        "app": empty_app,       # walk against this would fail — no routes
        "route": donor_route,   # what Starlette stamps after routing
    }
    request = Request(scope)

    resource, verb, route = map_request(request)
    assert (resource, verb) == ("tools", "execute")
    assert route is donor_route
