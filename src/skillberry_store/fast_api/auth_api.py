"""Auth endpoints: /auth/login, /auth/logout, /auth/whoami.

See §7.2 and §10.4 of docs/design/access-control.md.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

import bcrypt
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from skillberry_store.access_control.config import AccessControlConfig
from skillberry_store.access_control.pdp import Subject
from skillberry_store.access_control.sessions import SessionStore

logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    token: str
    expires_at: str
    tenant_id: str


class WhoAmIResponse(BaseModel):
    tenant_id: Optional[str] = None
    groups: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)


def register_auth_api(
    app: FastAPI,
    cfg: AccessControlConfig,
    sessions: SessionStore,
    tags: str = "auth",
) -> None:
    """Register the /auth/* endpoints on ``app``."""

    @app.post(
        "/auth/login",
        tags=[tags],
        response_model=LoginResponse,
        openapi_extra={"x-cli-name": "login"},
    )
    async def login(payload: LoginRequest) -> LoginResponse:
        user = cfg.user(payload.username)
        # Constant-time bcrypt check must run off the event loop.
        password_bytes = payload.password.encode("utf-8")
        if user is None:
            # Perform a dummy bcrypt to keep response time similar to the
            # good-user path (mitigates trivial user-enumeration timing).
            dummy_hash = (
                b"$2b$12$CBWfQZ3zX0Iu9d5R0v6ekOx3Xk9nu1qXKZM7YtM/y8bkuJHkE8DKa"
            )
            try:
                await asyncio.to_thread(bcrypt.checkpw, password_bytes, dummy_hash)
            except Exception:  # noqa: BLE001
                pass
            raise HTTPException(status_code=401, detail="invalid_credentials")
        try:
            ok = await asyncio.to_thread(
                bcrypt.checkpw, password_bytes, user.password_hash.encode("utf-8")
            )
        except ValueError:
            # Malformed stored hash; treat as invalid.
            ok = False
        if not ok:
            raise HTTPException(status_code=401, detail="invalid_credentials")

        token, expires_at = sessions.mint(
            tenant_id=user.tenant_id,
            groups=list(user.groups or []),
            ttl_seconds=cfg.session_ttl_seconds,
        )
        return LoginResponse(
            token=token,
            expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
            tenant_id=user.tenant_id,
        )

    @app.post(
        "/auth/logout",
        tags=[tags],
        openapi_extra={"x-cli-name": "logout"},
    )
    async def logout(request: Request) -> dict:
        header = request.headers.get("authorization") or ""
        parts = header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            sessions.revoke(parts[1])
        return {"status": "ok"}

    @app.get(
        "/auth/whoami",
        tags=[tags],
        response_model=WhoAmIResponse,
        openapi_extra={"x-cli-name": "whoami"},
    )
    async def whoami(request: Request) -> WhoAmIResponse:
        # In 'disabled' mode there is no identity to report.
        if cfg.mode == "disabled":
            return WhoAmIResponse(tenant_id=None, groups=[], roles=[])
        # /auth/whoami is unauth-listed (so it never returns 403); resolve the
        # bearer ourselves so any signed-in user can call it.
        header = request.headers.get("authorization") or ""
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="missing_authorization")
        session = sessions.resolve(parts[1])
        if session is None:
            raise HTTPException(status_code=401, detail="invalid_or_expired_token")
        subject = Subject(tenant_id=session.tenant_id, groups=list(session.groups))
        roles = cfg.roles_for(subject)
        return WhoAmIResponse(
            tenant_id=subject.tenant_id,
            groups=list(subject.groups or []),
            roles=roles,
        )
