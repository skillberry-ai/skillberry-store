import pytest
from fastapi.testclient import TestClient

from skillberry_store.fast_api.server import SBS
from skillberry_store.tests.utils import clean_test_tmp_dir


@pytest.fixture
def fresh_sbs():
    """Give each test a clean disk + freshly initialised singletons.

    The SBS module maintains process-lifetime caches (object handlers,
    service registry); without resetting them a second call to ``SBS()``
    reuses stale in-memory state pointing at a wiped directory.
    """
    from skillberry_store.modules import object_handler
    from skillberry_store.services import registry

    clean_test_tmp_dir()
    object_handler.clear_object_handlers()
    registry.clear_services()
    app = SBS()
    yield app
    object_handler.clear_object_handlers()
    registry.clear_services()


def test_health_endpoint(fresh_sbs):
    """Test that the health endpoint returns the expected response."""
    client = TestClient(fresh_sbs)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def _create_snippet(client: TestClient, name: str, content: str) -> None:
    resp = client.post(
        "/snippets/",
        params={
            "name": name,
            "description": f"desc for {name}",
            "content": content,
            "version": "1.0.0",
            "content_type": "text/plain",
            "state": "approved",
        },
    )
    assert resp.status_code == 200, resp.text


def test_list_snippets_default_returns_bare_array_with_content(fresh_sbs):
    """Default listing (no fields param) preserves the current wire shape."""
    client = TestClient(fresh_sbs)

    _create_snippet(client, "phase1_full_a", "hello world")

    resp = client.get("/snippets/")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    entry = next(s for s in body if s["name"] == "phase1_full_a")
    assert entry["content"] == "hello world"


def test_list_snippets_fields_list_drops_content(fresh_sbs):
    """?fields=list returns the slim preset (no heavy `content` field)."""
    client = TestClient(fresh_sbs)

    _create_snippet(client, "phase1_slim_a", "body-a")
    _create_snippet(client, "phase1_slim_b", "body-b")

    resp = client.get("/snippets/", params={"fields": "list"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 2
    names = {s["name"] for s in body}
    assert {"phase1_slim_a", "phase1_slim_b"}.issubset(names)
    for s in body:
        assert "content" not in s
        assert "uuid" in s


def test_list_snippets_custom_allowlist(fresh_sbs):
    """?fields=uuid,name returns only those keys per item."""
    client = TestClient(fresh_sbs)

    _create_snippet(client, "phase1_csv_a", "body-a")

    resp = client.get("/snippets/", params={"fields": "uuid,name"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    for entry in body:
        assert set(entry.keys()) == {"uuid", "name"}


def _search_snippets_via_mocked_vector(client: TestClient, matched_name: str, **params):
    """Patch the snippet handler's vector index to force ``matched_name`` as
    the only search hit; issue a search request with the extra ``params``.

    Search vectorization is stochastic and slow in tests; the field-selection
    layer under test is orthogonal to how the vector search ranks things,
    so we stub the index and verify field selection.
    """
    from unittest.mock import patch
    from skillberry_store.modules.object_handler import get_object_handler

    handler = get_object_handler("snippet")
    with patch.object(
        handler.descriptions,
        "search_description",
        return_value=[{"filename": matched_name, "similarity_score": 0.1}],
    ):
        return client.get("/search/snippets", params={"search_term": "q", **params})


def test_search_snippets_default_returns_legacy_shape(fresh_sbs):
    """Default search shape must remain ``{filename, similarity_score}``."""
    client = TestClient(fresh_sbs)
    _create_snippet(client, "phase1_search_legacy", "body-a")

    resp = _search_snippets_via_mocked_vector(client, "phase1_search_legacy")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list) and len(body) == 1
    assert set(body[0].keys()) == {"filename", "similarity_score"}
    assert body[0]["filename"] == "phase1_search_legacy"


def test_search_snippets_fields_list_returns_projected_with_score(fresh_sbs):
    """``?fields=list`` returns slim snippet dicts with score merged in."""
    client = TestClient(fresh_sbs)
    _create_snippet(client, "phase1_search_slim", "long body content")

    resp = _search_snippets_via_mocked_vector(
        client, "phase1_search_slim", fields="list"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list) and len(body) == 1
    r = body[0]
    assert r["name"] == "phase1_search_slim"
    assert r["similarity_score"] == 0.1
    assert "uuid" in r
    assert "content" not in r
