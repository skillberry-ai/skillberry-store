"""In-memory session store for the standalone-mode IdP.

Per §7.2 of the design doc, session tokens are opaque, module-level, and
lost on process restart. The time source is injectable so tests can advance
the clock without real sleeps.
"""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class Session:
    tenant_id: str
    groups: List[str]
    expires_at: float  # seconds since epoch


class SessionStore:
    def __init__(self, now: Callable[[], float] = time.time) -> None:
        self._now = now
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()

    def mint(self, tenant_id: str, groups: List[str], ttl_seconds: int) -> tuple[str, float]:
        """Create a new session; return ``(token, expires_at_epoch)``."""
        token = secrets.token_urlsafe(32)
        expires_at = self._now() + ttl_seconds
        with self._lock:
            self._sessions[token] = Session(
                tenant_id=tenant_id,
                groups=list(groups),
                expires_at=expires_at,
            )
        return token, expires_at

    def resolve(self, token: str) -> Optional[Session]:
        """Return a live session for ``token`` or ``None``.

        Expired sessions are pruned on lookup.
        """
        if not token:
            return None
        with self._lock:
            session = self._sessions.get(token)
            if session is None:
                return None
            if session.expires_at <= self._now():
                self._sessions.pop(token, None)
                return None
            return session

    def revoke(self, token: str) -> bool:
        """Remove ``token``. Returns ``True`` if it was present."""
        if not token:
            return False
        with self._lock:
            return self._sessions.pop(token, None) is not None

    def prune(self) -> int:
        """Drop every expired session; return count removed."""
        now = self._now()
        with self._lock:
            expired = [t for t, s in self._sessions.items() if s.expires_at <= now]
            for t in expired:
                self._sessions.pop(t, None)
            return len(expired)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)
