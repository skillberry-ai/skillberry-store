# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Coverage for the in-process /ui bundle serving.

Background (PR #308 review):

* issue #3 — the asset branch matched ``index.html`` by filename, so requesting
  the un-hashed entry point by its real name (a bookmark, a doc link, or an
  ingress rewriting ``/ui/`` -> ``/ui/index.html``) answered
  ``max-age=31536000, immutable``: a permanently pinned stale SPA bundle that no
  reload ever recovers — the exact bug the change set out to fix.
* issue #7 — ``dist`` is gitignored and no test target runs ``make ui-build``, so
  ``ui_dist.exists()`` is always false under pytest and the mount, redirect, SPA
  fallback, cache headers and traversal guard were all dead code during tests.

These tests therefore synthesise a minimal bundle in a tmp dir and point
``ui_dist_dir()`` at it, so the routes exist regardless of whether the real
bundle has been built.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from skillberry_store.access_control.config import get_config as get_acl_config
from skillberry_store.fast_api import server as server_module
from skillberry_store.fast_api.server import SBS, ui_dist_dir
from skillberry_store.tests.utils import clean_test_tmp_dir

ASSET_CACHE = "public, max-age=31536000, immutable"
INDEX_CACHE = "no-cache, must-revalidate"

INDEX_HTML = (
    '<!doctype html><html><head><script type="module" '
    'src="/ui/assets/index-abc12345.js"></script></head>'
    "<body><div id='root'></div></body></html>"
)


@pytest.fixture
def ui_client(tmp_path, monkeypatch):
    """An SBS app whose /ui mount serves a synthetic, content-hashed bundle."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX_HTML)
    (dist / "assets" / "index-abc12345.js").write_text("console.log('bundle')")
    (dist / "assets" / "index-abc12345.css").write_text(":root{}")
    (dist / "favicon.svg").write_text("<svg/>")
    # A file outside the bundle, to prove the traversal guard blocks it.
    (tmp_path / "secret.txt").write_text("do not serve me")

    monkeypatch.setattr(server_module, "ui_dist_dir", lambda: dist)

    from skillberry_store.modules import object_handler
    from skillberry_store.services import registry

    clean_test_tmp_dir()
    object_handler.clear_object_handlers()
    registry.clear_services()
    with TestClient(SBS()) as client:
        yield client
    object_handler.clear_object_handlers()
    registry.clear_services()


def test_index_html_by_name_is_not_cached_immutably(ui_client):
    """issue #3: the un-hashed entry point must never be immutably cached."""
    resp = ui_client.get("/ui/index.html")

    assert resp.status_code == 200
    assert resp.headers["cache-control"] == INDEX_CACHE
    assert "immutable" not in resp.headers["cache-control"]
    # It is still the real entry point, not an empty body.
    assert "id='root'" in resp.text


def test_index_html_by_name_is_served_for_head_too(ui_client):
    """HEAD is registered on the same route, so it carries the same directive."""
    resp = ui_client.head("/ui/index.html")

    assert resp.status_code == 200
    assert resp.headers["cache-control"] == INDEX_CACHE


@pytest.mark.parametrize(
    "path",
    ["/ui/assets/index-abc12345.js", "/ui/assets/index-abc12345.css", "/ui/favicon.svg"],
)
def test_content_hashed_assets_are_cached_forever(ui_client, path):
    """The immutable directive must survive the fix — it is correct for hashed names."""
    resp = ui_client.get(path)

    assert resp.status_code == 200
    assert resp.headers["cache-control"] == ASSET_CACHE


def test_bundle_root_serves_index_with_revalidation(ui_client):
    resp = ui_client.get("/ui/")

    assert resp.status_code == 200
    assert resp.headers["cache-control"] == INDEX_CACHE
    assert "id='root'" in resp.text


@pytest.mark.parametrize("path", ["/ui/skills", "/ui/tools/some-uuid", "/ui/does/not/exist"])
def test_spa_deep_links_fall_back_to_index(ui_client, path):
    """React Router owns client-side routes: unknown paths get index.html, not 404."""
    resp = ui_client.get(path)

    assert resp.status_code == 200
    assert "id='root'" in resp.text
    assert resp.headers["cache-control"] == INDEX_CACHE


def test_root_redirects_to_the_bundle(ui_client):
    resp = ui_client.get("/", follow_redirects=False)

    assert resp.status_code in (307, 308)
    assert resp.headers["location"] == "/ui/"


@pytest.mark.parametrize(
    "path",
    [
        "/ui/%2e%2e%2fsecret.txt",
        "/ui/%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "/ui/..%2fsecret.txt",
    ],
)
def test_percent_encoded_traversal_is_blocked(ui_client, path):
    """Percent-encoded traversal survives client-side normalisation; it must not escape.

    The guard resolves the joined path and rejects anything outside the bundle,
    so these degrade to the SPA fallback (index.html) rather than leaking a file.
    """
    resp = ui_client.get(path)

    assert resp.status_code == 200
    assert "do not serve me" not in resp.text
    assert "id='root'" in resp.text


def test_ui_routes_absent_when_bundle_is_not_built(tmp_path, monkeypatch):
    """A bare checkout (no dist) must still start: /ui is simply not mounted."""
    monkeypatch.setattr(server_module, "ui_dist_dir", lambda: tmp_path / "missing-dist")

    from skillberry_store.modules import object_handler
    from skillberry_store.services import registry

    clean_test_tmp_dir()
    object_handler.clear_object_handlers()
    registry.clear_services()
    try:
        with TestClient(SBS()) as client:
            assert client.get("/health").status_code == 200
            assert client.get("/ui/index.html").status_code == 404
    finally:
        object_handler.clear_object_handlers()
        registry.clear_services()


# --------------------------------------------------------------------------- #
# The real, built bundle
# --------------------------------------------------------------------------- #
# `make test` / `make test-e2e` build it via ui-build-optional, which is a no-op
# when no node toolchain is present — hence the skips rather than hard failures.
REAL_DIST = ui_dist_dir()
requires_built_bundle = pytest.mark.skipif(
    not (REAL_DIST / "index.html").is_file(),
    reason="UI bundle not built (run `make ui-build`)",
)


def _local_asset_refs(index_html: str) -> list[str]:
    """src=/href= values in index.html that point at our own bundle."""
    refs = re.findall(r'(?:src|href)="([^"]+)"', index_html)
    return [r for r in refs if not r.startswith(("http://", "https://", "data:", "#"))]


@pytest.fixture
def real_bundle_client():
    """An SBS app serving the bundle that `make ui-build` actually produced."""
    from skillberry_store.modules import object_handler
    from skillberry_store.services import registry

    clean_test_tmp_dir()
    object_handler.clear_object_handlers()
    registry.clear_services()
    with TestClient(SBS()) as client:
        yield client
    object_handler.clear_object_handlers()
    registry.clear_services()


@requires_built_bundle
def test_real_bundle_is_built_with_the_ui_basename():
    """`base: '/ui/'` in vite.config.ts — every asset reference must be /ui/-rooted.

    A wrong basename is invisible to the synthetic-bundle tests above and breaks
    the deployed SPA on its first asset request.
    """
    refs = _local_asset_refs((REAL_DIST / "index.html").read_text())

    assert refs, "index.html references no local assets — is the bundle complete?"
    offenders = [r for r in refs if not r.startswith("/ui/")]
    assert not offenders, f"asset references are not rooted at /ui/: {offenders}"


@requires_built_bundle
def test_real_bundle_assets_resolve_with_the_right_cache_headers(real_bundle_client):
    """Fetch what index.html actually asks for, through the real route table."""
    refs = _local_asset_refs((REAL_DIST / "index.html").read_text())

    for ref in refs:
        resp = real_bundle_client.get(ref)
        assert resp.status_code == 200, f"{ref} did not resolve"
        expected = INDEX_CACHE if ref.endswith(".html") else ASSET_CACHE
        assert resp.headers["cache-control"] == expected, f"wrong directive for {ref}"


@requires_built_bundle
def test_real_bundle_entry_point_and_deep_link(real_bundle_client):
    for path in ("/ui/", "/ui/index.html", "/ui/skills"):
        resp = real_bundle_client.get(path)
        assert resp.status_code == 200, path
        assert resp.headers["cache-control"] == INDEX_CACHE, path
        assert "<div id=\"root\"></div>" in resp.text, path


@pytest.mark.parametrize("method,path", [("GET", "/"), ("GET", "/ui*"), ("HEAD", "/ui*")])
def test_ui_paths_are_on_the_unauthenticated_allow_list(method, path):
    """The bundle must load before login, so /ui and the root redirect bypass ACL.

    Asserted independently of whether the bundle happens to be built, since the
    allow-list is what makes the RBAC startup audit pass for these routes.
    """
    cfg = get_acl_config()
    assert f"{method} {path}" in cfg.unauthenticated_paths, (
        f"{method} {path} is not allow-listed; the SPA would 401 before login"
    )


def test_every_ui_route_is_allow_listed_for_all_its_methods(ui_client):
    """The RBAC audit requires *every* method on a route to be allow-listed.

    With the bundle present the app registers extra routes, which is why a dev
    machine that had built it audited differently from CI (issue #7).
    """
    cfg = get_acl_config()
    ui_paths = {"/", "/ui/{path:path}"}
    ui_routes = [
        route
        for route in ui_client.app.routes
        if getattr(route, "path", None) in ui_paths and getattr(route, "methods", None)
    ]
    assert ui_routes, "no /ui routes registered even though a bundle is mounted"
    for route in ui_routes:
        for method in sorted(route.methods):
            assert cfg.is_unauthenticated(method, route.path), (
                f"{method} {route.path} requires auth: the SPA cannot load before login"
            )
