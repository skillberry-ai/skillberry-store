"""Business logic for authentication and session management.

FastAPI-agnostic; only ``HTTPException`` is used to signal error conditions
to the API layer (same convention as ``admin_service``, ``skills_service``).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import bcrypt
from fastapi import HTTPException

from skillberry_store.access_control.config import AccessControlConfig
from skillberry_store.access_control.pdp import Subject
from skillberry_store.access_control.sessions import SessionStore

logger = logging.getLogger(__name__)

# Pre-computed bcrypt hash used to keep the "unknown user" branch's timing
# close to the "known user with wrong password" branch (mitigates trivial
# user-enumeration timing attacks). The plaintext is unknowable — we never
# accept it as a real password because we only reach this hash when the
# user lookup already failed.
_DUMMY_HASH = b"$2b$12$CBWfQZ3zX0Iu9d5R0v6ekOx3Xk9nu1qXKZM7YtM/y8bkuJHkE8DKa"


def _bearer(header: Optional[str]) -> Optional[str]:
    """Extract the token from an ``Authorization: Bearer <token>`` header."""
    if not header:
        return None
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1] or None


class AuthService:
    """Service layer for /auth/* endpoints.

    Owns the bcrypt verify + session-mint flow (``login``), token revocation
    (``logout``), and identity introspection (``whoami``). The FastAPI layer
    only extracts request data (JSON body, ``Authorization`` header) and
    formats the response.

    Attributes:
        cfg: Loaded access-control config (users, roles, bindings, TTL).
        sessions: In-memory session store.
    """

    def __init__(self, cfg: AccessControlConfig, sessions: SessionStore) -> None:
        self.cfg = cfg
        self.sessions = sessions

    # ------------------------------------------------------------------ #
    # Login
    # ------------------------------------------------------------------ #

    async def login(self, username: str, password: str) -> Dict[str, str]:
        """Validate credentials and mint a new session token.

        Args:
            username: Login name from the request body.
            password: Plaintext password.

        Returns:
            Dict with ``token`` (opaque), ``expires_at`` (ISO 8601 UTC), and
            ``tenant_id``.

        Raises:
            HTTPException: 401 ``invalid_credentials`` when the user is
                unknown or the password does not match. Both branches use
                the same detail string (no user enumeration).
        """
        user = self.cfg.user(username)
        password_bytes = password.encode("utf-8")

        # bcrypt.checkpw at cost=12 is ~250-500ms on modern hardware and
        # must run off the event loop.
        if user is None:
            # Dummy hash keeps timing close to the wrong-password branch.
            try:
                await asyncio.to_thread(bcrypt.checkpw, password_bytes, _DUMMY_HASH)
            except Exception:  # noqa: BLE001 - best-effort timing equalizer
                pass
            raise HTTPException(status_code=401, detail="invalid_credentials")

        try:
            ok = await asyncio.to_thread(
                bcrypt.checkpw,
                password_bytes,
                user.password_hash.encode("utf-8"),
            )
        except ValueError:
            # Malformed stored hash — treat as an invalid credential.
            ok = False
        if not ok:
            raise HTTPException(status_code=401, detail="invalid_credentials")

        token, expires_at = self.sessions.mint(
            tenant_id=user.tenant_id,
            groups=list(user.groups or []),
            ttl_seconds=self.cfg.session_ttl_seconds,
        )
        return {
            "token": token,
            "expires_at": datetime.fromtimestamp(
                expires_at, tz=timezone.utc
            ).isoformat(),
            "tenant_id": user.tenant_id,
        }

    # ------------------------------------------------------------------ #
    # Logout
    # ------------------------------------------------------------------ #

    def logout(self, authorization_header: Optional[str]) -> Dict[str, str]:
        """Revoke the bearer token on the request. Idempotent."""
        token = _bearer(authorization_header)
        if token:
            self.sessions.revoke(token)
        return {"status": "ok"}

    # ------------------------------------------------------------------ #
    # Whoami
    # ------------------------------------------------------------------ #

    def whoami(self, authorization_header: Optional[str]) -> Dict[str, Any]:
        """Resolve the caller's identity and effective roles.

        In ``disabled`` mode there is no identity to report; returns an
        empty payload so the same client code works in either mode.

        Args:
            authorization_header: Raw ``Authorization`` header, if any.

        Returns:
            ``{"tenant_id": str|None, "groups": [...], "roles": [...]}``.

        Raises:
            HTTPException: 401 in standalone mode when the header is
                missing / malformed / points at an expired or unknown
                session.
        """
        if self.cfg.mode == "disabled":
            return {"tenant_id": None, "groups": [], "roles": []}

        token = _bearer(authorization_header)
        if not token:
            raise HTTPException(status_code=401, detail="missing_authorization")
        session = self.sessions.resolve(token)
        if session is None:
            raise HTTPException(
                status_code=401, detail="invalid_or_expired_token"
            )
        subject = Subject(tenant_id=session.tenant_id, groups=list(session.groups))
        return {
            "tenant_id": subject.tenant_id,
            "groups": list(subject.groups or []),
            "roles": self.cfg.roles_for(subject),
        }

    # ------------------------------------------------------------------ #
    # Convenience for callers who already have a Subject on request.state
    # (used by MCP or future middleware refinements).
    # ------------------------------------------------------------------ #

    def roles_for(self, subject: Subject) -> List[str]:
        return self.cfg.roles_for(subject)
