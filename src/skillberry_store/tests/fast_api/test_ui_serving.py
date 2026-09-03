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


def test_bare_ui_prefix_redirects_to_the_bundle_root(ui_client):
    """issue #15: this was the only path the (now removed) StaticFiles mount served.

    The `{path:path}` route needs the trailing slash, so without an explicit
    route `/ui` would 404.
    """
    resp = ui_client.get("/ui", follow_redirects=False)

    assert resp.status_code in (307, 308)
    assert resp.headers["location"] == "/ui/"


def test_bare_ui_prefix_redirect_also_answers_head(ui_client):
    resp = ui_client.head("/ui", follow_redirects=False)

    assert resp.status_code in (307, 308)


def test_no_staticfiles_mount_is_registered(ui_client):
    """The mount was unreachable behind the catch-all route; keep it gone.

    Starlette walks routes in registration order with no Mount precedence, so a
    re-added mount under /ui would be dead code again — and the comment claiming
    otherwise is what hid the loss of StaticFiles' own hardening.
    """
    from starlette.routing import Mount

    ui_mounts = [
        route
        for route in ui_client.app.routes
        if isinstance(route, Mount) and route.path.startswith("/ui")
    ]

    assert not ui_mounts, f"unreachable StaticFiles mount(s) under /ui: {ui_mounts}"


def test_assets_are_served_with_byte_range_support(ui_client):
    """Dropping the mount must not cost Range support — FileResponse handles it."""
    resp = ui_client.get(
        "/ui/assets/index-abc12345.js", headers={"Range": "bytes=0-6"}
    )

    assert resp.status_code == 206, "byte-range requests must be honoured"
    assert resp.headers["content-range"].startswith("bytes 0-6/")
    assert resp.text == "console"

    full = ui_client.get("/ui/assets/index-abc12345.js")
    assert full.headers.get("accept-ranges") == "bytes"


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
    ui_paths = {"/", "/ui", "/ui/{path:path}"}
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


# --------------------------------------------------------------------------- #
# Serve-time injection of the login-information message
# --------------------------------------------------------------------------- #
# docs/design/login-info.md §6. The message is NOT a Vite build input — it is
# injected into index.html as it is served — so these tests drive the real
# route rather than inspecting the bundle.

LOGIN_INFO_MESSAGE = "Shared eval box — do not store secrets."
META_RE = re.compile(
    r'<meta name="sbs-login-info" content="(?P<content>[^"]*)">'
)


def _login_info_content(html_text: str) -> str | None:
    """The raw (still HTML-escaped) content attribute, or None if absent."""
    match = META_RE.search(html_text)
    return match.group("content") if match else None


@pytest.fixture
def ui_client_factory(tmp_path, monkeypatch):
    """Build a /ui-serving app with a caller-chosen login message.

    ``build(message=None, index_html=INDEX_HTML)`` returns a TestClient. The
    message travels through the access-control config, which is where the
    single resolved value lives (§5), so these tests exercise the same path an
    operator's YAML takes.
    """
    from skillberry_store.access_control import config as acl_config
    from skillberry_store.modules import object_handler
    from skillberry_store.services import registry

    clients = []

    def build(message: str | None = None, index_html: str = INDEX_HTML) -> TestClient:
        dist = tmp_path / f"dist-{len(clients)}"
        (dist / "assets").mkdir(parents=True)
        (dist / "index.html").write_text(index_html)
        (dist / "assets" / "index-abc12345.js").write_text("console.log('bundle')")
        monkeypatch.setattr(server_module, "ui_dist_dir", lambda d=dist: d)

        acl_yaml = "mode: standalone\nstandalone:\n  users: []\n"
        if message is not None:
            acl_yaml += f'  login_info:\n    enabled: true\n    message: "{message}"\n'
        cfg_path = tmp_path / f"acl-{len(clients)}.yaml"
        cfg_path.write_text(acl_yaml)
        monkeypatch.setenv("SBS_ACCESS_CONTROL_CONFIG", str(cfg_path))
        acl_config.reset_config_cache()

        clean_test_tmp_dir()
        object_handler.clear_object_handlers()
        registry.clear_services()
        client = TestClient(SBS())
        clients.append(client)
        return client

    yield build
    object_handler.clear_object_handlers()
    registry.clear_services()
    acl_config.reset_config_cache()


@pytest.mark.parametrize("path", ["/ui/", "/ui/index.html", "/ui/login"])
def test_login_message_is_injected_on_every_html_path(ui_client_factory, path):
    """The two-branch trap: the on-disk hit and the SPA fallback must agree.

    ``/ui/index.html`` takes the asset branch, ``/ui/`` and ``/ui/login`` take
    the SPA fallback. Injecting in only one would show the banner on the login
    deep-link and not on the entry point requested by name.
    """
    client = ui_client_factory(message=LOGIN_INFO_MESSAGE)
    resp = client.get(path)

    assert resp.status_code == 200
    assert _login_info_content(resp.text) == LOGIN_INFO_MESSAGE
    assert resp.text.index("sbs-login-info") < resp.text.lower().index("</head>")
    assert "id='root'" in resp.text, "the real entry point must still be served"


def test_no_meta_tag_and_an_untouched_fileresponse_when_off(ui_client_factory):
    """Feature off is strictly additive-free: still a FileResponse, as before."""
    client = ui_client_factory(message=None)

    for path in ("/ui/", "/ui/index.html"):
        resp = client.get(path)
        assert resp.status_code == 200
        assert "sbs-login-info" not in resp.text
        # FileResponse's own headers, absent from a plain Response — proof the
        # route was not switched to generated bytes.
        assert "etag" in resp.headers, path
        assert "last-modified" in resp.headers, path


@pytest.mark.parametrize("message", [None, LOGIN_INFO_MESSAGE])
def test_index_cache_control_is_unchanged_in_both_states(ui_client_factory, message):
    """`no-cache, must-revalidate` is load-bearing: a restart must reach users."""
    client = ui_client_factory(message=message)

    for path in ("/ui/", "/ui/index.html"):
        assert client.get(path).headers["cache-control"] == INDEX_CACHE, path


def test_message_is_html_escaped_into_the_attribute(ui_client_factory):
    """Escaped in the raw bytes, and an HTML parse recovers the original."""
    from html import unescape

    raw = "quote \" angle < > amp & apos '"
    client = ui_client_factory(message=raw.replace('"', '\\"'))
    resp = client.get("/ui/")

    escaped = _login_info_content(resp.text)
    assert escaped is not None
    # The attribute value must not carry a raw quote, `<` or `&`; if it did,
    # the tag (and the surrounding document) could be broken out of.
    assert '"' not in escaped
    assert "<" not in escaped
    assert ">" not in escaped
    assert re.fullmatch(r"[^&]*(&[a-zA-Z0-9#]+;[^&]*)*", escaped)
    assert unescape(escaped) == raw


def test_line_breaks_survive_into_the_attribute(ui_client_factory):
    client = ui_client_factory(message="First line.\\nSecond line.")
    content = _login_info_content(client.get("/ui/").text)

    assert content == "First line.\nSecond line."


def test_head_on_the_injected_index_reports_the_length_without_a_body(
    ui_client_factory,
):
    """A plain Response sends its body for HEAD; this route serves GET and HEAD."""
    client = ui_client_factory(message=LOGIN_INFO_MESSAGE)
    get = client.get("/ui/index.html")
    head = client.head("/ui/index.html")

    assert head.status_code == 200
    assert head.content == b""
    assert head.headers["content-length"] == str(len(get.content))
    assert head.headers["cache-control"] == INDEX_CACHE


def test_hashed_assets_still_byte_range_with_the_feature_on(ui_client_factory):
    """Only index.html leaves FileResponse; assets keep Range support."""
    client = ui_client_factory(message=LOGIN_INFO_MESSAGE)
    resp = client.get(
        "/ui/assets/index-abc12345.js", headers={"Range": "bytes=0-6"}
    )

    assert resp.status_code == 206
    assert resp.text == "console"
    assert (
        client.get("/ui/assets/index-abc12345.js").headers["accept-ranges"] == "bytes"
    )


def test_missing_head_close_tag_warns_and_still_serves(ui_client_factory, caplog):
    """A banner is not worth failing a page load over."""
    import logging

    with caplog.at_level(logging.WARNING):
        client = ui_client_factory(
            message=LOGIN_INFO_MESSAGE,
            index_html="<!doctype html><html><body><div id='root'></div></body></html>",
        )
    resp = client.get("/ui/")

    assert resp.status_code == 200
    assert "id='root'" in resp.text
    assert "sbs-login-info" not in resp.text
    assert "</head>" in caplog.text


# --------------------------------------------------------------------------- #
# End-to-end: the real bundle, the real injection, the real meta name
# --------------------------------------------------------------------------- #

@requires_built_bundle
def test_the_built_bundle_reads_the_meta_name_the_server_writes():
    """Server and SPA must agree on the tag name, or the banner silently vanishes.

    The name is a string literal on both sides — `LOGIN_INFO_META_NAME` in
    server.py and the `querySelector` in LoginPage.tsx — with nothing to keep
    them in step. This asserts the built JS actually contains it.
    """
    from skillberry_store.fast_api.server import LOGIN_INFO_META_NAME

    bundled_js = "".join(
        p.read_text(errors="replace") for p in (REAL_DIST / "assets").glob("*.js")
    )

    assert bundled_js, "no JS in the built bundle"
    assert LOGIN_INFO_META_NAME in bundled_js, (
        f"the SPA never looks for meta[name={LOGIN_INFO_META_NAME!r}]; the "
        "server's injected tag would be dead HTML"
    )


@requires_built_bundle
def test_the_real_bundle_entry_point_gets_the_message_injected(tmp_path, monkeypatch):
    """The whole serving path against the bundle `make ui-build` produced."""
    from skillberry_store.access_control import config as acl_config
    from skillberry_store.modules import object_handler
    from skillberry_store.services import registry

    message = "Shared eval box — do not store secrets."
    cfg_path = tmp_path / "acl.yaml"
    cfg_path.write_text(
        "mode: standalone\n"
        "standalone:\n"
        "  users: []\n"
        f'  login_info:\n    enabled: true\n    message: "{message}"\n'
    )
    monkeypatch.setenv("SBS_ACCESS_CONTROL_CONFIG", str(cfg_path))
    acl_config.reset_config_cache()

    clean_test_tmp_dir()
    object_handler.clear_object_handlers()
    registry.clear_services()
    try:
        with TestClient(SBS()) as client:
            for path in ("/ui/", "/ui/index.html", "/ui/login"):
                resp = client.get(path)
                assert resp.status_code == 200, path
                assert _login_info_content(resp.text) == message, path
                assert resp.headers["cache-control"] == INDEX_CACHE, path
                assert '<div id="root"></div>' in resp.text, path
    finally:
        object_handler.clear_object_handlers()
        registry.clear_services()
        acl_config.reset_config_cache()
