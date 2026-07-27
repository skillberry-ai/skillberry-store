"""Unit tests for AuthService — the FastAPI-agnostic auth business logic."""

from __future__ import annotations

import asyncio

import bcrypt
import pytest
from fastapi import HTTPException

from skillberry_store.access_control.config import (
    AccessControlConfig,
    Role,
    RoleBinding,
    Rule,
    Subject as SubjectRef,
    User,
)
from skillberry_store.access_control.sessions import SessionStore
from skillberry_store.services.auth_service import AuthService


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()


def _cfg(mode: str = "standalone") -> AccessControlConfig:
    return AccessControlConfig(
        mode=mode,
        session_ttl_seconds=3600,
        users=[
            User(
                username="alice",
                tenant_id="alice",
                password_hash=_hash("alice-pw"),
                groups=["team-blue"],
            )
        ],
        roles=[
            Role(
                name="reader",
                rules=[Rule(resources=["skills"], verbs=["list"])],
            )
        ],
        bindings=[
            RoleBinding(
                name="alice-reads",
                subjects=[SubjectRef(kind="tenant", name="alice")],
                roles=["reader"],
            )
        ],
    )


def _svc(mode: str = "standalone") -> AuthService:
    return AuthService(cfg=_cfg(mode), sessions=SessionStore())


def test_login_good_credentials_returns_token():
    svc = _svc()
    result = asyncio.run(svc.login("alice", "alice-pw"))
    assert result["tenant_id"] == "alice"
    assert result["token"]
    assert result["expires_at"]


def test_login_bad_password_raises_401():
    svc = _svc()
    with pytest.raises(HTTPException) as ei:
        asyncio.run(svc.login("alice", "wrong"))
    assert ei.value.status_code == 401
    assert ei.value.detail == "invalid_credentials"


def test_login_unknown_user_raises_401_with_same_detail():
    svc = _svc()
    with pytest.raises(HTTPException) as ei:
        asyncio.run(svc.login("ghost", "whatever"))
    assert ei.value.status_code == 401
    assert ei.value.detail == "invalid_credentials"


def test_logout_revokes_token():
    svc = _svc()
    result = asyncio.run(svc.login("alice", "alice-pw"))
    header = f"Bearer {result['token']}"
    assert svc.logout(header) == {"status": "ok"}
    # Whoami must now reject the revoked token.
    with pytest.raises(HTTPException) as ei:
        svc.whoami(header)
    assert ei.value.status_code == 401


def test_logout_is_idempotent_and_accepts_no_header():
    svc = _svc()
    assert svc.logout(None) == {"status": "ok"}
    assert svc.logout("Bearer nonexistent") == {"status": "ok"}


def test_whoami_returns_subject_and_roles():
    svc = _svc()
    result = asyncio.run(svc.login("alice", "alice-pw"))
    info = svc.whoami(f"Bearer {result['token']}")
    assert info["tenant_id"] == "alice"
    assert info["groups"] == ["team-blue"]
    assert info["roles"] == ["reader"]


def test_whoami_missing_header_raises_401():
    svc = _svc()
    with pytest.raises(HTTPException) as ei:
        svc.whoami(None)
    assert ei.value.status_code == 401
    assert ei.value.detail == "missing_authorization"


def test_whoami_malformed_header_raises_401():
    svc = _svc()
    with pytest.raises(HTTPException) as ei:
        svc.whoami("NotBearer abc")
    assert ei.value.status_code == 401


def test_whoami_disabled_mode_returns_empty_payload():
    svc = _svc(mode="disabled")
    result = svc.whoami(None)
    assert result == {"tenant_id": None, "groups": [], "roles": []}
