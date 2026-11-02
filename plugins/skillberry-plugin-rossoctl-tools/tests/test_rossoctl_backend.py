"""RossoctlBackend against the fake rossoctl backend."""

import asyncio

import pytest

from rossoctl_fake_backend import BACKEND, FakeRossoctl
from skillberry_plugin_rossoctl_tools.backend import (
    RossoctlBackend,
    RossoctlForbidden,
    RossoctlNotFound,
    RossoctlUnavailable,
    service_port,
)


def run(coro):
    return asyncio.run(coro)


def test_bearer_from_client_credentials_is_sent_and_cached(backend, fake):
    run(backend.list_tools("team1"))
    run(backend.get_tool("team1", "weather-tool"))
    token_calls = [r for r in fake.requests if r["host"] == "keycloak.test"]
    api_calls = [r for r in fake.requests if r["host"] == "rossoctl-backend.test"]
    assert len(token_calls) == 1
    assert {r["auth"] for r in api_calls} == {"Bearer tok-1"}


def test_token_refreshed_once_on_401(backend, fake):
    run(backend.list_tools("team1"))
    fake.reject_next_with_401 = True
    items = run(backend.list_tools("team1"))
    assert items
    assert fake.tokens_issued == 2
    assert fake.requests[-1]["auth"] == "Bearer tok-2"


def test_persistent_401_is_forbidden(fake):
    b = RossoctlBackend(
        base_url=BACKEND,
        client_id="",
        client_secret="",
        token_endpoint="",
        allowed_namespaces=[],
        transport=fake.transport(),
    )
    with pytest.raises(RossoctlForbidden):
        run(b.list_tools("team1"))


def test_no_credentials_sends_no_auth_header():
    fake = FakeRossoctl(require_auth=False)
    b = RossoctlBackend(
        base_url=BACKEND,
        client_id="",
        client_secret="",
        token_endpoint="",
        allowed_namespaces=[],
        transport=fake.transport(),
    )
    assert run(b.list_tools("team1"))
    assert fake.requests[0]["auth"] is None
    assert {r["host"] for r in fake.requests} == {"rossoctl-backend.test"}


def test_caller_bearer_overrides_service_token(backend, fake):
    fake.valid_tokens.add("user-tok")
    run(backend.list_tools("team1", bearer="user-tok"))
    assert fake.requests[-1]["auth"] == "Bearer user-tok"
    assert fake.tokens_issued == 0


def test_errors_are_mapped(backend):
    with pytest.raises(RossoctlNotFound):
        run(backend.get_tool("team1", "missing-tool"))
    with pytest.raises(RossoctlUnavailable):
        run(backend.connect("team1", "unreachable-tool"))


def test_names_are_validated_before_any_call(backend, fake):
    for bad in ("Team1", "a/b", "../x", "x" * 64, ""):
        with pytest.raises(ValueError):
            run(backend.list_tools(bad))
    with pytest.raises(ValueError):
        run(backend.get_tool("team1", "../etc"))
    assert fake.requests == []


def test_allowed_namespaces(fake):
    b = RossoctlBackend(
        base_url=BACKEND,
        client_id="",
        client_secret="",
        token_endpoint="",
        allowed_namespaces=["team2"],
        transport=fake.transport(),
    )
    with pytest.raises(ValueError, match="not allowed"):
        run(b.list_tools("team1"))
    assert fake.requests == []


def test_unconfigured_backend():
    b = RossoctlBackend(base_url="", allowed_namespaces=[])
    assert not b.configured
    with pytest.raises(RossoctlUnavailable):
        run(b.list_tools("team1"))


def test_invoke_returns_result(backend):
    result = run(
        backend.invoke("team1", "weather-tool", "get_weather", {"city": "Boston"})
    )
    assert result["isError"] is False
    assert "52" in result["content"][0]["text"]


def test_service_port():
    assert service_port({"service": {"ports": [{"port": 9090}]}}) == 9090
    assert service_port({"service": None}) == 8000
    assert service_port({}) == 8000
