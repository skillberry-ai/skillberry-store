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
        result = await service.login(payload.username, payload.password)
        return LoginResponse(**result)

    @app.post(
        "/auth/logout",
        tags=[tags],
        openapi_extra={"x-cli-name": "logout"},
    )
    async def logout(request: Request) -> dict:
        return service.logout(request.headers.get("authorization"))

    @app.get(
        "/auth/whoami",
        tags=[tags],
        response_model=WhoAmIResponse,
        openapi_extra={"x-cli-name": "whoami"},
    )
    async def whoami(request: Request) -> WhoAmIResponse:
        result = service.whoami(request.headers.get("authorization"))
        return WhoAmIResponse(**result)
