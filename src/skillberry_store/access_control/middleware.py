"""Policy Enforcement Point — FastAPI middleware. See §8 of the design doc."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from skillberry_store.access_control.config import AccessControlConfig
from skillberry_store.access_control.idp import IdentityProvider, UnauthenticatedError
from skillberry_store.access_control.mapper import try_map_request
from skillberry_store.access_control.pdp import authorize

logger = logging.getLogger(__name__)


class AccessControlMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, cfg: AccessControlConfig, idp: IdentityProvider) -> None:
        super().__init__(app)
        self._cfg = cfg
        self._idp = idp

    async def dispatch(self, request: Request, call_next):
        # 1. Unauthenticated allow-list.
        if self._cfg.is_unauthenticated(request.method, request.url.path):
            return await call_next(request)

        # 2. Identify the caller.
        try:
            subject = self._idp.identify(request)
        except UnauthenticatedError as e:
            return _json_error(
                401,
                e.detail,
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 3. Route → (resource, verb).
        mapped = try_map_request(request)
        if mapped is None:
            # Unknown route: let FastAPI produce its normal 404.
            return await call_next(request)
        resource, verb, _route = mapped

        # 4. Decision.
        decision = authorize(subject, resource, verb, self._cfg)
        if not decision.allowed:
            logger.info(
                "access_denied tenant=%s resource=%s verb=%s reason=%s",
                subject.tenant_id,
                resource,
                verb,
                decision.reason,
            )
            return _json_error(403, decision.reason)

        request.state.subject = subject
        return await call_next(request)


def _json_error(status: int, detail: str, *, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail}, headers=headers or {})
