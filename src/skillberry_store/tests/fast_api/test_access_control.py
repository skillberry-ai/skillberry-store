"""Integration tests for the access-control layer.

Each test spins up a fresh SBS() app with a temp access_control_config.yaml
pointed at via ``SBS_ACCESS_CONTROL_CONFIG``. Uses FastAPI's TestClient for
in-process ASGI dispatch — no server subprocess.
"""

from __future__ import annotations

import textwrap
import time

import bcrypt
import pytest
from fastapi.testclient import TestClient

from skillberry_store.access_control import config as acl_config
from skillberry_store.tests.utils import clean_test_tmp_dir


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()


def _write_cfg(tmp_path, contents: str) -> str:
    path = tmp_path / "acl.yaml"
    path.write_text(textwrap.dedent(contents))
    return str(path)


@pytest.fixture
def fresh_sbs_factory(tmp_path, monkeypatch):
    """Build an SBS() with a caller-supplied access-control YAML.

    Returns a callable ``build(yaml_text)`` that writes the config, resets
    singletons, and returns a ``TestClient``.
    """
    from skillberry_store.modules import object_handler
    from skillberry_store.services import registry
    from skillberry_store.fast_api.server import SBS

    def build(yaml_text: str) -> TestClient:
        path = _write_cfg(tmp_path, yaml_text)
        monkeypatch.setenv("SBS_ACCESS_CONTROL_CONFIG", path)
        acl_config.reset_config_cache()
        clean_test_tmp_dir()
        object_handler.clear_object_handlers()
        registry.clear_services()
        app = SBS()
        return TestClient(app)

    yield build
    object_handler.clear_object_handlers()
    registry.clear_services()
    acl_config.reset_config_cache()


DEFAULT_STANDALONE_YAML = """
mode: standalone
standalone:
  session_ttl_seconds: 3600
  users:
    - username: alice
      tenant_id: alice
      password_hash: "__ALICE_HASH__"
      groups: []
    - username: bob
      tenant_id: bob
      password_hash: "__BOB_HASH__"
      groups: []
    - username: root
      tenant_id: root
      password_hash: "__ROOT_HASH__"
      groups: [admins]
roles:
  - name: reader
    rules:
      - resources: [skills, tools, snippets, vmcp_servers, vnfs_servers, facets, plugins, system]
        verbs: [list, get, search]
  - name: content-author
    rules:
      - resources: [skills, tools, snippets]
        verbs: [list, get, search, create, update, delete]
  - name: tool-runner
    rules:
      - resources: [tools, vmcp_servers, vnfs_servers]
        verbs: [execute]
  - name: admin
    rules:
      - resources: ["*"]
        verbs: ["*"]
bindings:
  - name: alice-reader
    subjects: [{kind: tenant, name: alice}]
    roles: [reader]
  - name: bob-author
    subjects: [{kind: tenant, name: bob}]
    roles: [content-author, tool-runner]
  - name: root-admin
    subjects: [{kind: group, name: admins}]
    roles: [admin]
"""


def _standalone_yaml() -> str:
    return (
        DEFAULT_STANDALONE_YAML
        .replace("__ALICE_HASH__", _hash("alice-pw"))
        .replace("__BOB_HASH__", _hash("bob-pw"))
        .replace("__ROOT_HASH__", _hash("root-pw"))
    )


# ------------------ disabled mode ---------------------------------------- #

def test_disabled_mode_all_endpoints_open(fresh_sbs_factory):
    client = fresh_sbs_factory("mode: disabled\n")
    # Health and unauth endpoints work.
    assert client.get("/health").status_code == 200
    # Regular content endpoints also work without any Authorization header.
    r = client.get("/skills/")
    assert r.status_code == 200


def test_disabled_mode_auth_endpoints_return_503(fresh_sbs_factory):
    client = fresh_sbs_factory("mode: disabled\n")
    login = client.post(
        "/auth/login", json={"username": "alice", "password": "x"}
    )
    assert login.status_code == 503
    assert login.json()["detail"] == "auth_disabled"

    logout = client.post("/auth/logout")
    assert logout.status_code == 503
    assert logout.json()["detail"] == "auth_disabled"

    whoami = client.get("/auth/whoami")
    assert whoami.status_code == 503
    assert whoami.json()["detail"] == "auth_disabled"


def test_disabled_mode_ignores_bearer_on_auth_endpoints(fresh_sbs_factory):
    """A bearer token on any /auth/* call must be ignored — the endpoint
    short-circuits to 503 without touching the header."""
    client = fresh_sbs_factory("mode: disabled\n")
    h = {"Authorization": "Bearer any-token-shape"}
    assert client.post("/auth/logout", headers=h).status_code == 503
    assert client.get("/auth/whoami", headers=h).status_code == 503


def test_repo_root_config_yaml_does_not_leak_into_tests(tmp_path, monkeypatch):
    """The user-managed access_control_config.yaml at the repo root must
    never be consumed by the test suite. Simulate a locally-flipped file
    (mode: standalone with real users) and prove that the session-level
    isolation fixture in conftest.py shields tests from it — a fresh
    ``SBS()`` still comes up in disabled mode.

    Two things are being verified together:
      * the env-var default is a non-existent path (loader → defaults);
      * ``load_config`` on a missing file returns ``mode: disabled``.
    """
    import os

    from skillberry_store.access_control import config as acl_config
    from skillberry_store.fast_api.server import SBS
    from skillberry_store.modules import object_handler
    from skillberry_store.services import registry
    from skillberry_store.tests.utils import clean_test_tmp_dir

    # Sanity: the session-autouse fixture must have pointed us at a
    # non-existent path (not the repo-root file).
    pinned = os.environ.get("SBS_ACCESS_CONTROL_CONFIG")
    assert pinned is not None
    assert not os.path.isfile(pinned)

    # Now write a "malicious" repo-root-style YAML at some real path and
    # verify that just having such a file on disk does NOT cause the
    # loader to pick it up — the env var is what matters.
    (tmp_path / "leak.yaml").write_text(
        "mode: standalone\n"
        "standalone:\n"
        "  users:\n"
        "    - username: attacker\n"
        "      password_hash: '$2b$12$x'\n"
    )
    clean_test_tmp_dir()
    object_handler.clear_object_handlers()
    registry.clear_services()
    acl_config.reset_config_cache()
    app = SBS()
    assert app.state.acl_cfg.mode == "disabled"
    object_handler.clear_object_handlers()
    registry.clear_services()


def test_disabled_mode_ignores_bearer_on_normal_endpoints(fresh_sbs_factory):
    """A bearer token on a regular endpoint must also be ignored — the
    middleware isn't installed in disabled mode, so the request behaves
    identically whether or not an Authorization header is sent."""
    client = fresh_sbs_factory("mode: disabled\n")
    no_auth = client.get("/skills/")
    with_auth = client.get(
        "/skills/", headers={"Authorization": "Bearer whatever"}
    )
    assert no_auth.status_code == 200
    assert with_auth.status_code == 200


# ------------------ standalone: identity & allow-list -------------------- #

def test_standalone_missing_auth_returns_401(fresh_sbs_factory):
    client = fresh_sbs_factory(_standalone_yaml())
    r = client.get("/skills/")
    assert r.status_code == 401
    assert r.headers.get("www-authenticate", "").lower() == "bearer"


def test_standalone_unauth_allowlist_reachable(fresh_sbs_factory):
    client = fresh_sbs_factory(_standalone_yaml())
    assert client.get("/health").status_code == 200
    assert client.get("/health/ready").status_code in (200, 500)
    assert client.get("/openapi.json").status_code == 200
    # Login endpoint reachable without any token.
    r = client.post(
        "/auth/login", json={"username": "alice", "password": "alice-pw"}
    )
    assert r.status_code == 200


# ------------------ login / logout / whoami ------------------------------ #

def test_login_good_and_bad_creds(fresh_sbs_factory):
    client = fresh_sbs_factory(_standalone_yaml())
    good = client.post(
        "/auth/login", json={"username": "alice", "password": "alice-pw"}
    )
    assert good.status_code == 200
    body = good.json()
    assert body["tenant_id"] == "alice"
    assert body["token"]
    assert body["expires_at"]

    bad_pw = client.post(
        "/auth/login", json={"username": "alice", "password": "wrong"}
    )
    assert bad_pw.status_code == 401
    assert bad_pw.json()["detail"] == "invalid_credentials"

    unknown = client.post(
        "/auth/login", json={"username": "ghost", "password": "x"}
    )
    assert unknown.status_code == 401
    assert unknown.json() == bad_pw.json()  # identical body (no enumeration)


def test_logout_revokes_token(fresh_sbs_factory):
    client = fresh_sbs_factory(_standalone_yaml())
    token = client.post(
        "/auth/login", json={"username": "alice", "password": "alice-pw"}
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/skills/", headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 200
    r = client.get("/skills/", headers=headers)
    assert r.status_code == 401


def test_whoami_returns_subject(fresh_sbs_factory):
    client = fresh_sbs_factory(_standalone_yaml())
    token = client.post(
        "/auth/login", json={"username": "bob", "password": "bob-pw"}
    ).json()["token"]
    r = client.get("/auth/whoami", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == "bob"
    assert set(body["roles"]) == {"content-author", "tool-runner"}


def test_whoami_missing_token_returns_401(fresh_sbs_factory):
    client = fresh_sbs_factory(_standalone_yaml())
    r = client.get("/auth/whoami")
    assert r.status_code == 401


def test_expired_token_rejected(fresh_sbs_factory):
    client = fresh_sbs_factory(
        _standalone_yaml().replace("session_ttl_seconds: 3600", "session_ttl_seconds: 1")
    )
    token = client.post(
        "/auth/login", json={"username": "alice", "password": "alice-pw"}
    ).json()["token"]
    time.sleep(1.5)
    r = client.get("/skills/", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


# ------------------ RBAC grant/deny -------------------------------------- #

def test_reader_can_list_but_cannot_create(fresh_sbs_factory):
    client = fresh_sbs_factory(_standalone_yaml())
    token = client.post(
        "/auth/login", json={"username": "alice", "password": "alice-pw"}
    ).json()["token"]
    h = {"Authorization": f"Bearer {token}"}

    assert client.get("/skills/", headers=h).status_code == 200
    # Reader has no 'create' verb on skills → 403.
    r = client.post(
        "/snippets/",
        params={
            "name": "denied",
            "description": "d",
            "content": "c",
            "version": "1.0.0",
            "content_type": "text/plain",
            "state": "approved",
        },
        headers=h,
    )
    assert r.status_code == 403


def test_content_author_can_create_snippet(fresh_sbs_factory):
    client = fresh_sbs_factory(_standalone_yaml())
    token = client.post(
        "/auth/login", json={"username": "bob", "password": "bob-pw"}
    ).json()["token"]
    h = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/snippets/",
        params={
            "name": "authored",
            "description": "d",
            "content": "c",
            "version": "1.0.0",
            "content_type": "text/plain",
            "state": "approved",
        },
        headers=h,
    )
    assert r.status_code == 200, r.text


def test_admin_verb_gated(fresh_sbs_factory):
    client = fresh_sbs_factory(_standalone_yaml())
    # bob is content-author + tool-runner, not admin.
    bob = client.post(
        "/auth/login", json={"username": "bob", "password": "bob-pw"}
    ).json()["token"]
    r = client.delete(
        "/admin/purge-all", headers={"Authorization": f"Bearer {bob}"}
    )
    assert r.status_code == 403

    # root is bound to the admin role via the 'admins' group.
    root = client.post(
        "/auth/login", json={"username": "root", "password": "root-pw"}
    ).json()["token"]
    r = client.delete(
        "/admin/purge-all", headers={"Authorization": f"Bearer {root}"}
    )
    assert r.status_code == 200


def test_delegated_mode_rejected_at_startup(fresh_sbs_factory):
    with pytest.raises(Exception):  # AccessControlConfigError, wrapped by SBS init
        fresh_sbs_factory("mode: delegated\n")


# ------------------ per-tenant MCP surface (option 2, §16.6) ------------- #


def _mcp_mount_paths(client: TestClient) -> set[str]:
    """Extract all mounted /control_sse* SSE endpoints from the app's routes."""
    paths: set[str] = set()
    for route in client.app.routes:
        p = getattr(route, "path", "")
        if p.startswith("/control_sse") and not p.endswith("/messages/"):
            paths.add(p)
    return paths


def test_standalone_mode_mounts_one_mcp_per_user(fresh_sbs_factory):
    client = fresh_sbs_factory(_standalone_yaml())
    mounts = _mcp_mount_paths(client)
    # One SSE endpoint per configured user, no shared /control_sse fallback.
    assert "/control_sse/alice" in mounts
    assert "/control_sse/bob" in mounts
    assert "/control_sse/root" in mounts
    assert "/control_sse" not in mounts


def test_disabled_mode_mounts_shared_control_sse(fresh_sbs_factory):
    client = fresh_sbs_factory("mode: disabled\n")
    mounts = _mcp_mount_paths(client)
    assert "/control_sse" in mounts
    # No per-user paths in disabled mode.
    assert not any(m.startswith("/control_sse/") for m in mounts)


def test_reader_mcp_surface_excludes_writes(fresh_sbs_factory):
    """alice is bound to `reader` — her MCP surface must not list writes.

    We inspect the FastApiMCP's tool table directly rather than driving a
    live SSE handshake (protocol-level plumbing that's out of scope for
    unit tests). The tool table drives what any MCP client would see.
    """
    from skillberry_store.access_control.mcp_plan import operations_for_user

    client = fresh_sbs_factory(_standalone_yaml())
    cfg = client.app.state.acl_cfg
    alice_ops = set(operations_for_user(client.app, cfg.user("alice"), cfg))
    bob_ops = set(operations_for_user(client.app, cfg.user("bob"), cfg))
    root_ops = set(operations_for_user(client.app, cfg.user("root"), cfg))

    # alice is a reader — she gets list/get/search operations and no writes.
    assert "list_skills" in alice_ops
    assert "get_skill" in alice_ops
    assert "search_skills" in alice_ops
    assert "create_skill" not in alice_ops
    assert "delete_skill" not in alice_ops
    assert "execute_tool" not in alice_ops
    assert "update_skill" not in alice_ops

    # bob has content-author + tool-runner: writes on content + tool exec.
    assert "create_skill" in bob_ops
    assert "delete_skill" in bob_ops
    assert "execute_tool" in bob_ops

    # root has admin: full surface, everything alice has and everything bob has.
    assert alice_ops.issubset(root_ops)
    assert bob_ops.issubset(root_ops)


def test_per_user_mcp_paths_are_unauth_allowlisted(fresh_sbs_factory):
    """The middleware must let /control_sse/<user>* through without a
    token — the tool invocations that traverse the SSE transport are
    each gated separately when the ASGI stack re-dispatches them. We
    check the config directly rather than driving a live SSE handshake
    (which would deadlock the TestClient)."""
    client = fresh_sbs_factory(_standalone_yaml())
    cfg = client.app.state.acl_cfg
    assert cfg.is_unauthenticated("GET", "/control_sse/alice")
    assert cfg.is_unauthenticated("POST", "/control_sse/alice/messages/")
    assert cfg.is_unauthenticated("GET", "/control_sse/root")
