"""Identity providers. See §7 of the design doc."""

from __future__ import annotations

from typing import Protocol

from fastapi import Request

from skillberry_store.access_control.pdp import Subject
from skillberry_store.access_control.sessions import SessionStore


class UnauthenticatedError(Exception):
    """Raised when the caller cannot be authenticated (→ HTTP 401)."""

    def __init__(self, detail: str = "unauthenticated"):
        self.detail = detail
        super().__init__(detail)


class IdentityProvider(Protocol):
    def identify(self, request: Request) -> Subject: ...


class DisabledIdentityProvider:
    """No authentication; returns an anonymous Subject."""

    def identify(self, request: Request) -> Subject:  # noqa: ARG002
        return Subject(tenant_id=None, groups=[])


class StandaloneIdentityProvider:
    """Reads ``Authorization: Bearer <token>`` and resolves via a SessionStore."""

    def __init__(self, sessions: SessionStore) -> None:
        self._sessions = sessions

    def identify(self, request: Request) -> Subject:
        header = request.headers.get("authorization") or request.headers.get(
            "Authorization"
        )
        if not header:
            raise UnauthenticatedError("missing_authorization")
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
            raise UnauthenticatedError("invalid_authorization")
        session = self._sessions.resolve(parts[1])
        if session is None:
            raise UnauthenticatedError("invalid_or_expired_token")
        return Subject(tenant_id=session.tenant_id, groups=list(session.groups))
