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


# ── §5: owner tenant, end to end ────────────────────────────────────────── #

OWNER_YAML = """
mode: standalone
standalone:
  session_ttl_seconds: 3600
  users:
    - username: root
      tenant_id: root
      password_hash: "__ROOT_HASH__"
      groups: [admins]
plugins:
  owner_tenant: plugin-user
  token_ttl_seconds: 60
roles:
  - name: admin
    rules:
      - resources: ["*"]
        verbs: ["*"]
  - name: plugin-agent
    rules:
      - resources: [skills, tools, snippets]
        verbs: [list, get, search, create, update, delete]
      - resources: [tools]
        verbs: [execute]
      - resources: [facets, plugins]
        verbs: [list, get, search]
bindings:
  - name: root-admin
    subjects: [{kind: group, name: admins}]
    roles: [admin]
  - name: plugin-agent-binding
    subjects: [{kind: tenant, name: plugin-user}]
    roles: [plugin-agent]
"""


def _owner_yaml() -> str:
    return OWNER_YAML.replace("__ROOT_HASH__", _hash("root-pw"))


def test_deployment_default_owner_is_loaded(sbs_factory):
    client = sbs_factory(_owner_yaml())
    cfg = client.app.state.acl_cfg
    assert cfg.plugin_owner_tenant == "plugin-user"
    assert cfg.plugin_token_ttl_seconds == 60
    loader = client.app.state.plugin_loader
    assert loader.owner_tenant("sast") == "plugin-user"


def test_virtual_plugin_user_cannot_log_in(sbs_factory):
    """``plugin-user`` appears in roles and bindings but has no
    ``standalone.users`` entry, so no credential for it exists anywhere (§5.3)."""
    client = sbs_factory(_owner_yaml())
    r = client.post(
        "/auth/login", json={"username": "plugin-user", "password": "plugin-user"}
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_credentials"


def test_minted_plugin_user_token_can_create_but_not_administer(sbs_factory):
    """The identity is unforgeable from outside, but the store can mint a
    session for it in-process — which is how §4.5 hands an out-of-process agent
    the owner tenant's identity with no stored secret."""
    client = sbs_factory(_owner_yaml())
    cfg = client.app.state.acl_cfg
    sessions = client.app.state.acl_sessions
    token, _ = sessions.mint("plugin-user", cfg.plugin_owner_groups, 60)
    h = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/snippets/",
        params={
            "name": "owned",
            "description": "d",
            "content": "c",
            "version": "1.0.0",
            "content_type": "text/plain",
            "state": "approved",
        },
        headers=h,
    )
    assert created.status_code == 200, created.text
    # plugin-agent never mentions the admin resource.
    assert client.get("/admin/backup", headers=h).status_code == 403


def test_enabling_a_plugin_records_the_acting_tenant_as_owner(sbs_factory):
    client = sbs_factory(_owner_yaml())
    loader = client.app.state.plugin_loader
    slug = next(iter(loader.plugins))
    assert loader.config.get_owner(slug) is None

    h = _token(client, "root", "root-pw")
    r = client.patch(f"/plugins/{slug}", json={"enabled": True}, headers=h)
    assert r.status_code == 200, r.text
    assert loader.config.get_owner(slug) == "root"
    assert r.json()["owner_tenant"] == "root"
    # …and the per-plugin record outranks the deployment-wide default.
    assert loader.owner_tenant(slug) == "root"


def test_disabling_a_plugin_does_not_record_an_owner(sbs_factory):
    client = sbs_factory(_owner_yaml())
    loader = client.app.state.plugin_loader
    slug = next(iter(loader.plugins))
    h = _token(client, "root", "root-pw")
    assert (
        client.patch(f"/plugins/{slug}", json={"enabled": False}, headers=h).status_code
        == 200
    )
    assert loader.config.get_owner(slug) is None


def test_disabled_mode_records_no_owner_on_enable(sbs_factory):
    """No subject on the request, so there is nothing to record (§2.5)."""
    client = sbs_factory("mode: disabled\n")
    loader = client.app.state.plugin_loader
    slug = next(iter(loader.plugins))
    r = client.patch(f"/plugins/{slug}", json={"enabled": True})
    assert r.status_code == 200, r.text
    assert loader.config.get_owner(slug) is None
    assert r.json()["owner_tenant"] is None


def test_plugin_status_names_a_missing_owner_under_acl(sbs_factory):
    """P5 should be observable before the first trigger fails silently (§8)."""
    client = sbs_factory(_owner_yaml().replace("  owner_tenant: plugin-user\n", ""))
    h = _token(client, "root", "root-pw")
    infos = client.get("/plugins/", headers=h).json()
    assert infos
    assert all(i["owner_tenant"] is None for i in infos)
    assert all("no owner tenant assigned" in i["status"] for i in infos)


def test_plugin_status_is_unchanged_when_disabled(sbs_factory):
    client = sbs_factory("mode: disabled\n")
    infos = client.get("/plugins/").json()
    assert infos
    assert all("no owner tenant assigned" not in i["status"] for i in infos)


# ── §2.2: enforcement point 2, through a real request ───────────────────── #

FANOUT_YAML = """
mode: standalone
standalone:
  session_ttl_seconds: 3600
  users:
    - username: author
      tenant_id: author
      password_hash: "__AUTHOR_HASH__"
      groups: []
    - username: root
      tenant_id: root
      password_hash: "__ROOT_HASH__"
      groups: [admins]
roles:
  - name: skill-author
    rules:
      - resources: [skills]
        verbs: [list, get, search, create, update]
  - name: admin
    rules:
      - resources: ["*"]
        verbs: ["*"]
bindings:
  - name: author-binding
    subjects: [{kind: tenant, name: author}]
    roles: [skill-author]
  - name: root-admin
    subjects: [{kind: group, name: admins}]
    roles: [admin]
"""


def _fanout_yaml() -> str:
    from skillberry_store.access_control.config import _DEFAULT_UNAUTH_PATHS

    entries = list(_DEFAULT_UNAUTH_PATHS) + ["POST /probe-open-fanout"]
    allow_list = "unauthenticated_paths:\n" + "".join(f"  - {e}\n" for e in entries)
    return (
        FANOUT_YAML
        .replace("__AUTHOR_HASH__", _hash("author-pw"))
        .replace("__ROOT_HASH__", _hash("root-pw"))
        + "\n"
        + allow_list
    )


def _install_fanout_probes(app) -> None:
    """A stand-in plugin route whose work fans out past what it declared.

    Registered on the app rather than shipped in a plugin because the assertion
    is about the framework: the door decides the pair the route declared, and
    ``_admit`` decides each object the work actually reaches.
    """
    from skillberry_store.access_control.audit import stamp_rbac_markers
    from skillberry_store.access_control.decorator import requires

    store = app.state.plugin_loader.store_api.for_plugin("probe")

    @requires("skills", "update")
    @app.post("/probe-fanout")
    async def probe_fanout(uuid: str):
        # Declares skills:update at the door; actually touches a snippet.
        return {"wrote": store.update_snippet_tags(uuid, ["probe:touched"])}

    @app.post("/probe-open-fanout")
    async def probe_open_fanout(uuid: str):
        # Allow-listed, so no PEP runs and no ambient subject exists.
        return {"wrote": store.update_snippet_tags(uuid, ["probe:touched"])}

    stamp_rbac_markers(app)


def _make_snippet(client: TestClient, headers: dict, name: str) -> str:
    r = client.post(
        "/snippets/",
        params={
            "name": name,
            "description": "d",
            "content": "c",
            "version": "1.0.0",
            "content_type": "text/plain",
            "state": "approved",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return r.json()["uuid"]


def test_fanout_past_the_declared_pair_is_denied_by_admit(sbs_factory):
    """The case only ``_admit`` catches: the caller holds the pair the door
    declared, so it is admitted — then denied on the object that exceeds its
    grant, with the outcome recorded on that object (§9.1)."""
    client = sbs_factory(_fanout_yaml())
    _install_fanout_probes(client.app)
    root = _token(client, "root", "root-pw")
    uuid = _make_snippet(client, root, "fanout-target")

    author = _token(client, "author", "author-pw")
    r = client.post("/probe-fanout", params={"uuid": uuid}, headers=author)
    assert r.status_code == 403, r.text
    assert "snippets" in r.json()["detail"]

    # The refusal is visible on the object, not only in the log.
    obj = client.get(
        f"/snippets/{uuid}", params={"fields": "full"}, headers=root
    ).json()
    assert "probe:error" in obj["tags"]
    assert obj["extra"]["probe"]["outcome"]["state"] == "error"
    assert "no role grants" in obj["extra"]["probe"]["outcome"]["reason"]


def test_the_declared_pair_alone_is_admitted_at_the_door(sbs_factory):
    """An admin clears both layers — the door and every object reached."""
    client = sbs_factory(_fanout_yaml())
    _install_fanout_probes(client.app)
    root = _token(client, "root", "root-pw")
    uuid = _make_snippet(client, root, "fanout-allowed")

    r = client.post("/probe-fanout", params={"uuid": uuid}, headers=root)
    assert r.status_code == 200, r.text
    assert r.json()["wrote"] is True
    obj = client.get(f"/snippets/{uuid}", headers=root).json()
    assert "probe:touched" in obj["tags"]
    assert "probe:error" not in obj["tags"]


def test_no_ambient_identity_is_a_500_not_a_403(sbs_factory):
    """P5 on a path the PEP never ran on. Nobody did anything wrong — an owner
    tenant was never assigned — so it must not send the caller looking at their
    own permissions."""
    client = sbs_factory(_fanout_yaml())
    _install_fanout_probes(client.app)
    root = _token(client, "root", "root-pw")
    uuid = _make_snippet(client, root, "fanout-anon")

    r = client.post("/probe-open-fanout", params={"uuid": uuid})
    assert r.status_code == 500, r.text
    assert "no tenant in context" in r.json()["detail"]


def test_disabled_mode_admits_the_same_plugin_work(sbs_factory):
    """The whole mechanism is inert without ACL: identical code path, no PDP
    call, no P5 failure (§2.5)."""
    client = sbs_factory("mode: disabled\n")
    _install_fanout_probes(client.app)
    uuid = _make_snippet(client, {}, "fanout-disabled")
    r = client.post("/probe-fanout", params={"uuid": uuid})
    assert r.status_code == 200, r.text
    assert r.json()["wrote"] is True


# ── §4.5: the per-subject MCP mount ─────────────────────────────────────── #


def _mcp_mounts(client: TestClient) -> set:
    return {
        getattr(r, "path", "")
        for r in client.app.routes
        if getattr(r, "path", "").startswith("/control_sse")
        and not getattr(r, "path", "").endswith("/messages/")
    }


def test_the_plugin_owner_tenant_gets_its_own_mcp_mount(sbs_factory):
    """Defect C's second half: the mount loop was driven by ``cfg.users``, and a
    virtual owner tenant has no users entry by design — so the URL a plugin
    handed an agent was not mounted at all."""
    client = sbs_factory(_owner_yaml())
    mounts = _mcp_mounts(client)
    assert "/control_sse/root" in mounts
    assert "/control_sse/plugin-user" in mounts
    assert "/control_sse" not in mounts


def test_a_per_plugin_owner_also_gets_a_mount(sbs_factory):
    client = sbs_factory(_owner_yaml())
    loader = client.app.state.plugin_loader
    slug = next(iter(loader.plugins))
    loader.record_owner(slug, "team-blue")
    # Mounts are computed at startup, so rebuild to pick the new owner up.
    client = sbs_factory(_owner_yaml())
    assert "/control_sse/team-blue" in _mcp_mounts(client)


def test_the_owner_mount_surface_matches_its_role(sbs_factory):
    """``operations_for_subject`` works on any subject, not only a config user —
    only the iteration source widened."""
    from skillberry_store.access_control.mcp_plan import operations_for_subject
    from skillberry_store.access_control.pdp import Subject

    client = sbs_factory(_owner_yaml())
    cfg = client.app.state.acl_cfg
    ops = set(
        operations_for_subject(
            client.app, Subject(tenant_id="plugin-user"), cfg
        )
    )
    # plugin-agent grants content authorship and tool execution…
    assert {"create_skill", "update_skill", "execute_tool"} <= ops
    # …and never mentions the admin resource.
    assert not any(o.startswith("purge") or "backup" in o for o in ops)


def test_a_plugin_resolves_its_own_mount_and_token(sbs_factory):
    """What ask-runspace hands an out-of-process agent: a mounted per-subject
    URL plus a short-lived token minted for the ambient identity — no password,
    no stored secret."""
    client = sbs_factory(_owner_yaml())
    store = client.app.state.plugin_loader.store_api.for_plugin("ask-runspace")

    from skillberry_store.access_control.context import set_current_subject
    from skillberry_store.access_control.pdp import Subject

    set_current_subject(Subject(tenant_id="root", groups=["admins"]))
    try:
        entry = store.mcp_sse_config("http://localhost:8000")
    finally:
        set_current_subject(None)

    assert entry["url"] == "http://localhost:8000/control_sse/root"
    token = entry["headers"]["Authorization"].removeprefix("Bearer ")
    # The token is a real session on this store, for that tenant.
    whoami = client.get(
        "/auth/whoami", headers={"Authorization": f"Bearer {token}"}
    )
    assert whoami.status_code == 200
    assert whoami.json()["tenant_id"] == "root"


def test_disabled_mode_still_mounts_the_shared_control_sse(sbs_factory):
    client = sbs_factory("mode: disabled\n")
    assert "/control_sse" in _mcp_mounts(client)
    store = client.app.state.plugin_loader.store_api
    assert store.mcp_mount_path() == "/control_sse"
    assert store.internal_token() is None
