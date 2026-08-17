"""Unit tests for the in-memory session store."""

from skillberry_store.access_control.sessions import SessionStore


def _clock():
    """Return a mutable clock fixture."""

    class Clock:
        t = 1_000.0

        def __call__(self):
            return self.t

    return Clock()


def test_mint_returns_urlsafe_token_and_expiry():
    clock = _clock()
    store = SessionStore(now=clock)
    token, expires_at = store.mint("alice", ["team-blue"], ttl_seconds=60)
    assert token
    assert len(token) >= 32
    assert "+" not in token and "/" not in token  # url-safe base64
    assert expires_at == 1_060.0


def test_resolve_returns_session_before_expiry():
    clock = _clock()
    store = SessionStore(now=clock)
    token, _ = store.mint("alice", ["g"], ttl_seconds=60)
    session = store.resolve(token)
    assert session is not None
    assert session.tenant_id == "alice"
    assert session.groups == ["g"]


def test_resolve_returns_none_for_expired_and_prunes():
    clock = _clock()
    store = SessionStore(now=clock)
    token, _ = store.mint("alice", [], ttl_seconds=60)
    clock.t = 2_000.0
    assert store.resolve(token) is None
    # Expired session pruned on lookup.
    assert len(store) == 0


def test_resolve_returns_none_for_unknown_token():
    store = SessionStore()
    assert store.resolve("nope") is None
    assert store.resolve("") is None


def test_revoke_is_idempotent():
    store = SessionStore()
    token, _ = store.mint("alice", [], ttl_seconds=60)
    assert store.revoke(token) is True
    assert store.revoke(token) is False
    assert store.resolve(token) is None


def test_mint_yields_distinct_tokens():
    store = SessionStore()
    seen = set()
    for _ in range(20):
        token, _ = store.mint("a", [], ttl_seconds=60)
        assert token not in seen
        seen.add(token)


def test_prune_removes_expired_entries():
    clock = _clock()
    store = SessionStore(now=clock)
    t1, _ = store.mint("a", [], ttl_seconds=10)
    t2, _ = store.mint("b", [], ttl_seconds=100)
    clock.t = 1_050.0
    dropped = store.prune()
    assert dropped == 1
    assert store.resolve(t1) is None
    assert store.resolve(t2) is not None
