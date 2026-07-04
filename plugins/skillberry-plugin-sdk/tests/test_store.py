import os

import httpx
import pytest

from skillberry_plugin_sdk.store import StoreClient, get_store_client


@pytest.mark.asyncio
async def test_get_store_client_from_env(monkeypatch) -> None:
    monkeypatch.setenv("SKILLBERRY_STORE_URL", "http://example:9000")
    monkeypatch.setenv("SKILLBERRY_STORE_TOKEN", "secret")
    c = get_store_client()
    assert c.base_url == "http://example:9000"
    assert c.token == "secret"


@pytest.mark.asyncio
async def test_get_skill_returns_none_on_404(monkeypatch) -> None:
    async def handler(request):
        return httpx.Response(404, json={"detail": "no"})

    transport = httpx.MockTransport(handler)

    class TestClientPatched(StoreClient):
        async def _request(self, method, path, *, params=None, json=None):
            async with httpx.AsyncClient(transport=transport) as client:
                r = await client.request(method, f"{self.base_url}{path}", params=params, json=json)
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                return r.json() if r.content else None

    c = TestClientPatched("http://x")
    assert await c.get_skill("nope") is None
