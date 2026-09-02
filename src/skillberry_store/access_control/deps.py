"""FastAPI dependencies for access control.

Policy Enforcement Point implemented as a single FastAPI dependency
that gates every route on the app. See §8 of
``docs/design/access-control.md``.

Design points:

* Bearer extraction uses FastAPI's ``HTTPBearer`` security scheme. When
  the ``enforce`` dependency is installed, FastAPI auto-registers the
  scheme under ``components.securitySchemes`` in the generated OpenAPI
  and adds ``security: [{HTTPBearer: []}]`` to every route it protects
  — ``/docs`` renders the "Authorize" button and per-route lock icons
  without any extra wiring.
* ``auto_error=False`` lets ``enforce`` shape the 401 response (detail
  and ``WWW-Authenticate`` header) instead of accepting FastAPI's
  default 403 with no header.
* Routes in the unauth allow-list (``/auth/*``, ``/health*``,
  ``/admin/metrics``) opt out of the derived OpenAPI security requirement
  by declaring ``openapi_extra={"security": []}`` where they are
  registered. The dep still runs on them and short-circuits via
  ``cfg.is_unauthenticated(...)``. SSE mounts (``/control_sse*``) are
  Starlette ``Mount`` objects, not ``APIRoute``s — the FastAPI dep chain
  does not apply to them, matching the "SSE handshake is open,
  re-dispatched tool calls are gated" contract in §10.2.
* In ``mode: disabled`` the dep is not installed at all, so the OpenAPI
  schema publishes no security requirements — identical to the
  pre-ACL baseline.
* A matched route with no ``@requires`` marker is **denied with a 403 and
  an audit line**, never allowed and never a 500 (plugin-identity §10
  step 2). The startup coverage audit should make this unreachable; a
  route registered after startup is the case that can still get here, and
  fail-safe is the only defensible answer for one — there is no declared
  intent to decide against.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from skillberry_store.access_control.config import AccessControlConfig
from skillberry_store.access_control.mapper import UnmarkedRouteError, try_map_request
from skillberry_store.access_control.pdp import Subject, authorize
from skillberry_store.access_control.sessions import SessionStore

logger = logging.getLogger(__name__)


bearer_scheme = HTTPBearer(
    bearerFormat="opaque",
    description=(
        "Opaque session token minted by POST /auth/login. "
        "Send as `Authorization: Bearer <token>`."
    ),
    auto_error=False,
)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def make_enforce_dependency(
    cfg: AccessControlConfig, sessions: SessionStore
) -> Callable:
    """Build the global ``Depends(...)`` gate for ``mode: standalone``.

    Returns an async callable installed via ``FastAPI(dependencies=[...])``
    so it fires on every route registered on the app (including plugin
    sub-routers). Steps:

      1. Short-circuit the unauth allow-list.
      2. Resolve the bearer token to a ``Subject``.
      3. Map the matched route to ``(resource, verb)``.
      4. Call the PDP and raise 403 on deny.
      5. Stash the ``Subject`` on ``request.state`` for handlers.
    """

    async def enforce(
        request: Request,
        creds: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    ) -> None:
        if cfg.is_unauthenticated(request.method, request.url.path):
            return

        if (
            creds is None
            or (creds.scheme or "").lower() != "bearer"
            or not creds.credentials
        ):
            raise _unauthorized("missing_authorization")
        session = sessions.resolve(creds.credentials)
        if session is None:
            raise _unauthorized("invalid_or_expired_token")
        subject = Subject(
            tenant_id=session.tenant_id, groups=list(session.groups)
        )

        try:
            mapped = try_map_request(request)
        except UnmarkedRouteError as e:
            # Fail-safe, not fail-crash: an unmarked route declares no intent,
            # so there is nothing the PDP could decide. Deny and say so in the
            # log — a 500 here previously leaked the defect to the caller as a
            # server error while telling the operator nothing actionable.
            logger.error(
                "access_denied_unmarked_route tenant=%s method=%s path=%s "
                "detail=%s (apply @requires above the route, or allow-list it)",
                subject.tenant_id,
                request.method,
                request.url.path,
                e,
            )
            raise HTTPException(
                status_code=403, detail="route_missing_access_control_marker"
            )
        if mapped is None:
            request.state.subject = subject
            return
        resource, verb, _route = mapped

        decision = authorize(subject, resource, verb, cfg)
        if not decision.allowed:
            logger.info(
                "access_denied tenant=%s resource=%s verb=%s reason=%s",
                subject.tenant_id,
                resource,
                verb,
                decision.reason,
            )
            raise HTTPException(status_code=403, detail=decision.reason)

        request.state.subject = subject

    return enforce
