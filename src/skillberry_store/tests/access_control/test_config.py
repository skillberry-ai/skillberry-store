"""Unit tests for access-control config loading."""

import os
import textwrap

import pytest

from skillberry_store.access_control.config import (
    AccessControlConfigError,
    load_config,
)


def _write(tmp_path, contents: str) -> str:
    path = tmp_path / "acl.yaml"
    path.write_text(textwrap.dedent(contents))
    return str(path)


def test_valid_standalone_config(tmp_path, monkeypatch):
    monkeypatch.delenv("SBS_SESSION_TTL", raising=False)
    path = _write(
        tmp_path,
        """
        mode: standalone
        standalone:
          session_ttl_seconds: 3600
          users:
            - username: alice
              tenant_id: alice
              password_hash: "$2b$12$hash"
              groups: [team-blue]
        roles:
          - name: reader
            rules:
              - resources: [skills]
                verbs: [list, get]
        bindings:
          - name: b1
            subjects: [{kind: tenant, name: alice}]
            roles: [reader]
        """,
    )
    cfg = load_config(path)
    assert cfg.mode == "standalone"
    assert cfg.session_ttl_seconds == 3600
    assert len(cfg.users) == 1
    assert cfg.users[0].tenant_id == "alice"
    assert cfg.role("reader") is not None
    assert cfg.bindings[0].roles == ["reader"]


def test_missing_file_defaults_to_disabled(tmp_path):
    path = str(tmp_path / "does-not-exist.yaml")
    cfg = load_config(path)
    assert cfg.mode == "disabled"
    assert "GET /health" in cfg.unauthenticated_paths


def test_delegated_mode_rejected(tmp_path):
    path = _write(tmp_path, "mode: delegated\n")
    with pytest.raises(AccessControlConfigError):
        load_config(path)


def test_unknown_mode_rejected(tmp_path):
    path = _write(tmp_path, "mode: bogus\n")
    with pytest.raises(AccessControlConfigError):
        load_config(path)


def test_malformed_yaml_fails_hard(tmp_path):
    path = _write(tmp_path, "mode: [unbalanced\n")
    with pytest.raises(AccessControlConfigError):
        load_config(path)


def test_unknown_resource_verb_dropped(tmp_path, caplog):
    path = _write(
        tmp_path,
        """
        mode: standalone
        standalone:
          users:
            - username: alice
              password_hash: "$2b$12$x"
        roles:
          - name: r
            rules:
              - resources: [skills, bogus]
                verbs: [list, teleport]
        bindings:
          - name: b
            subjects: [{kind: tenant, name: alice}]
            roles: [r]
        """,
    )
    cfg = load_config(path)
    role = cfg.role("r")
    assert role is not None
    assert role.rules[0].resources == ["skills"]
    assert role.rules[0].verbs == ["list"]


def test_binding_scope_parsed_but_ignored(tmp_path):
    path = _write(
        tmp_path,
        """
        mode: standalone
        standalone:
          users:
            - username: alice
              password_hash: "$2b$12$x"
        roles:
          - name: r
            rules:
              - resources: [skills]
                verbs: [list]
        bindings:
          - name: b
            subjects: [{kind: tenant, name: alice}]
            roles: [r]
            scope:
              namespaces: [prod]
        """,
    )
    cfg = load_config(path)
    assert cfg.bindings[0].scope == {"namespaces": ["prod"]}


def test_env_session_ttl_overrides_yaml(tmp_path, monkeypatch):
    monkeypatch.setenv("SBS_SESSION_TTL", "77")
    path = _write(
        tmp_path,
        """
        mode: standalone
        standalone:
          session_ttl_seconds: 1000
          users:
            - username: alice
              password_hash: "$2b$12$x"
        """,
    )
    cfg = load_config(path)
    assert cfg.session_ttl_seconds == 77


def test_binding_referencing_missing_role_fails_in_standalone(tmp_path):
    path = _write(
        tmp_path,
        """
        mode: standalone
        standalone:
          users:
            - username: alice
              password_hash: "$2b$12$x"
        bindings:
          - name: b
            subjects: [{kind: tenant, name: alice}]
            roles: [ghost]
        """,
    )
    with pytest.raises(AccessControlConfigError):
        load_config(path)
