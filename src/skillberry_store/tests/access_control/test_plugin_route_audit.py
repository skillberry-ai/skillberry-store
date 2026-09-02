"""Route walking, marker stamping and coverage audit for plugin routers.

Covers plugin-identity §6.1 (one walker repairs marker stamping and the
coverage audit), §6.1a (which route shapes the audit covers) and §6.3
(fail in ``standalone``, warn in ``disabled`` for plugin offenders).

Synthetic apps rather than a full ``SBS()`` — these assertions are about
route-table shape, and a FastAPI app with one included router reproduces
the exact nesting a mounted plugin produces.
"""

from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route as StarletteRoute

from skillberry_store.access_control.audit import (
    audit_rbac_coverage,
    stamp_rbac_markers,
    walk_api_routes,
    walk_foreign_plugin_routes,
)
from skillberry_store.access_control.config import (
    AccessControlConfig,
    AccessControlConfigError,
)
from skillberry_store.access_control.decorator import requires


def _cfg(mode: str = "standalone") -> AccessControlConfig:
    return AccessControlConfig(mode=mode, unauthenticated_paths=["GET /health"])


def _app_with_plugin_router(mark: bool = True) -> FastAPI:
    app = FastAPI()
    router = APIRouter()

    if mark:

        @requires("skills", "update")
        @router.post("/scan")
        async def scan():  # pragma: no cover - never invoked
            return {}

    else:

        @router.post("/scan")
        async def scan():  # pragma: no cover - never invoked
            return {}

    app.include_router(router, prefix="/plugins/demo")
    return app


# ── the walker ──────────────────────────────────────────────────────────── #


def test_walker_descends_included_routers_with_full_paths():
    app = _app_with_plugin_router()
    walked = {w.path: w for w in walk_api_routes(app)}
    assert "/plugins/demo/scan" in walked
    entry = walked["/plugins/demo/scan"]
    assert entry.plugin is True
    # The nested APIRoute still carries its unprefixed path — the walker is
    # what re-assembles the path a client actually calls.
    assert entry.route.path == "/scan"


def test_walker_descends_nested_include_router():
    app = FastAPI()
    inner = APIRouter()

    @requires("plugins", "get")
    @inner.get("/deep")
    async def deep():  # pragma: no cover
        return {}

    outer = APIRouter()
    outer.include_router(inner, prefix="/n")
    app.include_router(outer, prefix="/plugins/demo")

    paths = {w.path: w.plugin for w in walk_api_routes(app)}
    assert paths.get("/plugins/demo/n/deep") is True


def test_walker_marks_core_routes_as_non_plugin():
    app = FastAPI()

    @requires("skills", "list")
    @app.get("/skills/")
    async def skills():  # pragma: no cover
        return []

    walked = {w.path: w for w in walk_api_routes(app)}
    assert walked["/skills/"].plugin is False


# ── stamping ────────────────────────────────────────────────────────────── #


def test_stamp_reaches_plugin_routes_and_openapi():
    app = _app_with_plugin_router()
    assert stamp_rbac_markers(app) == 1
    route = next(w.route for w in walk_api_routes(app) if w.plugin)
    assert route.openapi_extra["x-rbac-resource"] == "skills"
    assert route.openapi_extra["x-rbac-verb"] == "update"
    # The generated schema publishes the marker too, which is what lets a UI
    # evaluate an action against the requesting subject (§6.2).
    operation = app.openapi()["paths"]["/plugins/demo/scan"]["post"]
    assert operation["x-rbac-resource"] == "skills"
    assert operation["x-rbac-verb"] == "update"


def test_stamp_is_idempotent():
    app = _app_with_plugin_router()
    assert stamp_rbac_markers(app) == 1
    assert stamp_rbac_markers(app) == 0


# ── the audit ───────────────────────────────────────────────────────────── #


def test_marked_plugin_route_passes_audit_in_every_mode():
    for mode in ("disabled", "standalone"):
        app = _app_with_plugin_router()
        stamp_rbac_markers(app)
        audit_rbac_coverage(app, _cfg(mode))


def test_unmarked_plugin_route_fails_standalone():
    app = _app_with_plugin_router(mark=False)
    stamp_rbac_markers(app)
    with pytest.raises(AccessControlConfigError) as exc:
        audit_rbac_coverage(app, _cfg("standalone"))
    assert "/plugins/demo/scan" in str(exc.value)


def test_unmarked_plugin_route_only_warns_when_disabled(caplog):
    """Third-party plugin routes are outside this repo, and a deployment in
    ``mode: disabled`` skips no decision — so it must still boot (§6.3)."""
    app = _app_with_plugin_router(mark=False)
    stamp_rbac_markers(app)
    with caplog.at_level("WARNING"):
        audit_rbac_coverage(app, _cfg("disabled"))
    assert "/plugins/demo/scan" in caplog.text


def test_unmarked_core_route_fails_even_when_disabled():
    """Core coverage stays a code-correctness property in every mode."""
    app = FastAPI()

    @app.get("/skills/")
    async def skills():  # pragma: no cover
        return []

    stamp_rbac_markers(app)
    with pytest.raises(AccessControlConfigError) as exc:
        audit_rbac_coverage(app, _cfg("disabled"))
    assert "/skills/" in str(exc.value)


def test_allowlisted_route_needs_no_marker():
    app = FastAPI()

    @app.get("/health")
    async def health():  # pragma: no cover
        return {}

    stamp_rbac_markers(app)
    audit_rbac_coverage(app, _cfg("standalone"))


# ── shapes the PEP cannot guard (§6.1a) ─────────────────────────────────── #


def _app_with_plugin_mount() -> FastAPI:
    app = FastAPI()
    router = APIRouter()
    sub = Starlette(
        routes=[StarletteRoute("/inner", lambda request: PlainTextResponse("hi"))]
    )
    router.mount("/subapp", sub)
    app.include_router(router, prefix="/plugins/demo")
    return app


def test_mount_inside_plugin_router_is_reported():
    app = _app_with_plugin_mount()
    foreign = list(walk_foreign_plugin_routes(app))
    assert len(foreign) == 1
    assert foreign[0].kind == "Mount"
    assert foreign[0].path == "/plugins/demo/subapp"


def test_mount_inside_plugin_router_fails_standalone():
    app = _app_with_plugin_mount()
    with pytest.raises(AccessControlConfigError) as exc:
        audit_rbac_coverage(app, _cfg("standalone"))
    assert "not an APIRoute" in str(exc.value)


def test_websocket_inside_plugin_router_is_reported():
    app = FastAPI()
    router = APIRouter()

    @router.websocket("/ws")
    async def ws(websocket):  # pragma: no cover
        await websocket.accept()

    app.include_router(router, prefix="/plugins/demo")
    kinds = {f.kind for f in walk_foreign_plugin_routes(app)}
    assert kinds == {"APIWebSocketRoute"}


def test_core_mounts_are_not_reported():
    """``/control_sse`` is a deliberate, allow-listed core mount."""
    app = FastAPI()
    app.mount("/control_sse", Starlette(routes=[]))
    assert list(walk_foreign_plugin_routes(app)) == []
    audit_rbac_coverage(app, _cfg("standalone"))
