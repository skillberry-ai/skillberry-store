"""FastAPI wrapper for /auth/login, /auth/logout, /auth/whoami.

Wire-level concerns only — request/response translation. All business
logic (bcrypt verify, session mint, token resolution, roles computation)
lives in :mod:`skillberry_store.services.auth_service`.

See §7.2 and §10.4 of docs/design/access-control.md.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from skillberry_store.access_control.config import AccessControlConfig
from skillberry_store.access_control.sessions import SessionStore
from skillberry_store.services.auth_service import AuthService

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
    service: Optional[AuthService] = None,
) -> None:
    """Register the /auth/* endpoints on ``app``.

    Args:
        app: The FastAPI application.
        cfg: Access-control config, used by the service.
        sessions: Session store, used by the service.
        tags: FastAPI tag applied to the endpoints.
        service: Optional pre-built ``AuthService``. When ``None``, a new
            one is created from ``cfg`` + ``sessions`` — mirroring how the
            other ``register_*_api`` factories construct their default
            services.
    """
    if service is None:
        service = AuthService(cfg=cfg, sessions=sessions)

    @app.post(
        "/auth/login",
        tags=[tags],
        response_model=LoginResponse,
        openapi_extra={"x-cli-name": "login"},
    )
    async def login(payload: LoginRequest) -> LoginResponse:
        """Authenticate a user and mint a bearer session token.

        Validates the supplied username / password against the bcrypt
        hashes in ``access_control_config.yaml``. On success, returns an
        opaque session token whose lifetime is ``session_ttl_seconds``
        (12h default; see §7.2 of docs/design/access-control.md). The
        client is expected to send this token on subsequent requests as
        ``Authorization: Bearer <token>``.

        Unknown username and bad password both return the same 401 body
        (``invalid_credentials``) — no user enumeration.

        Args:
            payload: JSON body with ``username`` and ``password`` fields.

        Returns:
            LoginResponse: ``token`` (opaque, URL-safe), ``expires_at``
            (ISO-8601 UTC), and the resolved ``tenant_id``.

        Raises:
            HTTPException: 401 ``invalid_credentials`` when the user is
                unknown or the password does not match.
        """
        result = await service.login(payload.username, payload.password)
        return LoginResponse(**result)

    @app.post(
        "/auth/logout",
        tags=[tags],
        openapi_extra={"x-cli-name": "logout"},
    )
    async def logout(request: Request) -> dict:
        """Revoke the bearer token on the request.

        Idempotent: a missing / malformed / unknown token still returns
        200. Client-side sign-out (clearing the stored token) can always
        proceed regardless of the server's view. Listed in the
        unauthenticated allow-list so it works even if the token has
        already expired — the intent is "make sure this token is gone,"
        not "prove you had a live session first."

        Args:
            request: The incoming request; the ``Authorization`` header
                (if present) is consulted for the token to revoke.

        Returns:
            dict: ``{"status": "ok"}``.
        """
        return service.logout(request.headers.get("authorization"))

    @app.get(
        "/auth/whoami",
        tags=[tags],
        response_model=WhoAmIResponse,
        openapi_extra={"x-cli-name": "whoami"},
    )
    async def whoami(request: Request) -> WhoAmIResponse:
        """Return the caller's identity and the roles bound to it.

        Populates the UI's "Signed in as ..." indicator and drives any
        future RBAC-aware UI hiding. Also useful as a CLI diagnostic
        (``sbs whoami``). Roles are recomputed at request time from the
        currently loaded bindings — they are not baked into the session
        at login, so a config reload takes effect without invalidating
        minted sessions (see the ``Subject`` vs ``whoami`` note in §7 of
        docs/design/access-control.md).
        In ``disabled`` mode there is no identity to report; returns an
        empty payload so client code works uniformly across modes.

        Args:
            request: The incoming request; ``Authorization: Bearer`` is
                resolved directly (this endpoint is in the unauth
                allow-list, so the middleware does not populate
                ``request.state.subject`` for it).

        Returns:
            WhoAmIResponse: ``tenant_id``, ``groups``, and ``roles``.

        Raises:
            HTTPException: 401 in ``standalone`` mode when the header is
                missing / malformed, or the token is expired / unknown.
        """
        result = service.whoami(request.headers.get("authorization"))
        return WhoAmIResponse(**result)
