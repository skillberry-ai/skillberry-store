"""Plugins under access control — end-to-end against a real ``SBS()`` app.

Companion to ``test_access_control.py``, which covers the core surface.
This module covers what ``docs/design/plugin-identity.md`` adds: plugin
routes that the PEP can decide on (§6), the ambient subject a plugin's
work runs under (§4), the owner tenant behind trigger-driven work (§5),
and enforcement point 2 inside ``StoreAPI`` (§2).
"""

from __future__ import annotations

import textwrap

import bcrypt
import pytest
from fastapi.testclient import TestClient

from skillberry_store.access_control import config as acl_config
from skillberry_store.access_control.audit import walk_api_routes
from skillberry_store.tests.utils import clean_test_tmp_dir


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()


STANDALONE_YAML = """
mode: standalone
standalone:
  session_ttl_seconds: 3600
  users:
    - username: reader
      tenant_id: reader
      password_hash: "__READER_HASH__"
      groups: []
    - username: root
      tenant_id: root
      password_hash: "__ROOT_HASH__"
      groups: [admins]
roles:
  - name: base-user
    rules:
      - resources: [skills, tools, snippets, vmcp_servers, vnfs_servers, facets, plugins, system]
        verbs: [list, get, search, execute]
  - name: admin
    rules:
      - resources: ["*"]
        verbs: ["*"]
bindings:
  - name: reader-base
    subjects: [{kind: tenant, name: reader}]
    roles: [base-user]
  - name: root-admin
    subjects: [{kind: group, name: admins}]
    roles: [admin]
"""


def standalone_yaml() -> str:
    return (
        STANDALONE_YAML
        .replace("__READER_HASH__", _hash("reader-pw"))
        .replace("__ROOT_HASH__", _hash("root-pw"))
    )


@pytest.fixture
def sbs_factory(tmp_path, monkeypatch):
    """Build an ``SBS()`` from a caller-supplied access-control YAML."""
    from skillberry_store.modules import object_handler
    from skillberry_store.services import registry
    from skillberry_store.fast_api.server import SBS

    def build(yaml_text: str) -> TestClient:
        path = tmp_path / "acl.yaml"
        path.write_text(textwrap.dedent(yaml_text))
        monkeypatch.setenv("SBS_ACCESS_CONTROL_CONFIG", str(path))
        monkeypatch.setenv(
            "SKILLBERRY_PLUGIN_CONFIG", str(tmp_path / "plugins.json")
        )
        acl_config.reset_config_cache()
        clean_test_tmp_dir()
        object_handler.clear_object_handlers()
        registry.clear_services()
        return TestClient(SBS())

    yield build
    object_handler.clear_object_handlers()
    registry.clear_services()
    acl_config.reset_config_cache()


def _token(client: TestClient, username: str, password: str) -> dict:
    r = client.post(
        "/auth/login", json={"username": username, "password": password}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ── §6: every bundled plugin route is marked and decidable ──────────────── #


def test_every_bundled_plugin_route_declares_a_marker(sbs_factory):
    client = sbs_factory("mode: disabled\n")
    plugin_routes = [w for w in walk_api_routes(client.app) if w.plugin]
    assert plugin_routes, "no plugin routes mounted — plugins not installed?"
    unmarked = [
        w.path
        for w in plugin_routes
        if not (w.route.openapi_extra or {}).get("x-rbac-resource")
        or not (w.route.openapi_extra or {}).get("x-rbac-verb")
    ]
    assert unmarked == []


def test_plugin_routes_are_visible_to_the_walker(sbs_factory):
    """Defect A's root cause: ``include_router`` nesting hid these routes."""
    client = sbs_factory("mode: disabled\n")
    paths = {w.path for w in walk_api_routes(client.app)}
    assert "/plugins/provenance/check" in paths
    assert "/plugins/sast/scan" in paths


def test_plugin_call_without_token_is_401_not_500(sbs_factory):
    client = sbs_factory(standalone_yaml())
    r = client.post("/plugins/provenance/check", json={"github_url": "x"})
    assert r.status_code == 401


def test_plugin_call_denied_at_the_door_is_403_not_500(sbs_factory):
    """``/plugins/provenance/check`` declares ``("skills", "update")``; a
    base-user holds only list/get/search/execute, so the PEP refuses it."""
    client = sbs_factory(standalone_yaml())
    h = _token(client, "reader", "reader-pw")
    r = client.post("/plugins/provenance/check", json={"github_url": "x"}, headers=h)
    assert r.status_code == 403, r.text


def test_plugin_call_admitted_at_the_door_never_500s(sbs_factory):
    """An admin clears the PEP and reaches the plugin's own router guard.

    The plugin may still be inactive (404) or reject the payload (4xx) — the
    point is that the request is decided, not aborted with an
    ``UnmarkedRouteError``.
    """
    client = sbs_factory(standalone_yaml())
    h = _token(client, "root", "root-pw")
    r = client.post("/plugins/provenance/check", json={"github_url": "x"}, headers=h)
    assert r.status_code != 500, r.text


def test_read_only_plugin_route_allowed_for_base_user(sbs_factory):
    """``/plugins/dast/scan-status`` declares ``("plugins", "get")``, which a
    base-user does hold — so the door admits it (the plugin guard may 404)."""
    client = sbs_factory(standalone_yaml())
    h = _token(client, "reader", "reader-pw")
    r = client.get(
        "/plugins/dast/scan-status", params={"uuid": "nope"}, headers=h
    )
    assert r.status_code in (200, 404), r.text


# ── §10 step 2: the mapper is fail-safe, not fail-crash ─────────────────── #


def test_route_added_after_startup_without_marker_is_403(sbs_factory, caplog):
    """The startup audit makes this unreachable for routes registered before
    boot. A route added afterwards is the case the backstop exists for, and an
    unmarked route must deny rather than 500 — there is no declared intent for
    the PDP to decide against."""
    client = sbs_factory(standalone_yaml())

    @client.app.get("/late-unmarked")
    async def late():  # pragma: no cover - reached, but through the PEP
        return {"reached": True}

    h = _token(client, "root", "root-pw")
    with caplog.at_level("ERROR"):
        r = client.get("/late-unmarked", headers=h)
    assert r.status_code == 403, r.text
    assert r.json()["detail"] == "route_missing_access_control_marker"
    assert "access_denied_unmarked_route" in caplog.text


def test_unmarked_route_still_requires_a_token(sbs_factory):
    """Authentication comes first: an unmarked route must not become a way to
    skip the 401."""
    client = sbs_factory(standalone_yaml())

    @client.app.get("/late-unmarked-anon")
    async def late():  # pragma: no cover
        return {}

    assert client.get("/late-unmarked-anon").status_code == 401


# ── §4: the ambient subject ─────────────────────────────────────────────── #

def _ambient_yaml() -> str:
    """The standalone config plus one extra allow-listed path for the probe.

    Spelling out ``unauthenticated_paths`` replaces the built-in default list
    rather than extending it, so the defaults are repeated here — omitting them
    would leave ``/docs``, ``/openapi.json`` and friends unmarked and fail the
    startup audit.
    """
    from skillberry_store.access_control.config import _DEFAULT_UNAUTH_PATHS

    entries = list(_DEFAULT_UNAUTH_PATHS) + ["GET /probe-open"]
    allow_list = "unauthenticated_paths:\n" + "".join(
        f"  - {e}\n" for e in entries
    )
    return standalone_yaml() + "\n" + allow_list


def _install_ambient_probes(app) -> None:
    """Register two probes that report the ambient subject back to the test.

    Registered after boot (and re-stamped) rather than shipped as real
    endpoints: the assertion is about what the PEP publishes, and a probe is
    the only way to observe a context variable from outside the process.
    """
    from skillberry_store.access_control.audit import stamp_rbac_markers
    from skillberry_store.access_control.context import current_subject
    from skillberry_store.access_control.decorator import requires

    @requires("skills", "get")
    @app.get("/probe-ambient")
    async def probe_ambient():
        s = current_subject()
        return {"tenant": s.tenant_id if s else None}

    @app.get("/probe-open")
    async def probe_open():
        s = current_subject()
        return {"tenant": s.tenant_id if s else None}

    stamp_rbac_markers(app)


def test_authenticated_request_publishes_the_calling_tenant(sbs_factory):
    client = sbs_factory(_ambient_yaml())
    _install_ambient_probes(client.app)
    h = _token(client, "reader", "reader-pw")
    r = client.get("/probe-ambient", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["tenant"] == "reader"


def test_allowlisted_request_observes_no_ambient_subject(sbs_factory):
    """P5 depends on an empty context reading as ``None``: a leaked value would
    let an autonomous operation silently inherit an earlier caller's identity
    instead of failing."""
    client = sbs_factory(_ambient_yaml())
    _install_ambient_probes(client.app)
    # Authenticate first, so a leak would have something to leak.
    h = _token(client, "root", "root-pw")
    assert client.get("/probe-ambient", headers=h).json()["tenant"] == "root"
    assert client.get("/probe-open").json()["tenant"] is None


def test_ambient_subject_does_not_leak_across_tenants(sbs_factory):
    client = sbs_factory(_ambient_yaml())
    _install_ambient_probes(client.app)
    reader = _token(client, "reader", "reader-pw")
    root = _token(client, "root", "root-pw")
    assert client.get("/probe-ambient", headers=reader).json()["tenant"] == "reader"
    assert client.get("/probe-ambient", headers=root).json()["tenant"] == "root"
    assert client.get("/probe-ambient", headers=reader).json()["tenant"] == "reader"


def test_disabled_mode_leaves_the_ambient_subject_unset(sbs_factory):
    """No PEP is installed, so nothing sets it — and ``_admit`` returns on its
    first line rather than tripping P5 (§2.5)."""
    client = sbs_factory("mode: disabled\n")
    _install_ambient_probes(client.app)
    assert client.get("/probe-ambient").json()["tenant"] is None
