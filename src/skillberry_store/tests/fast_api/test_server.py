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


def test_list_snippets_default_is_narrow(fresh_sbs):
    """Default listing (no fields param) is the ``narrow`` preset — the
    minimal UI listing set, so heavy fields like ``content`` are dropped."""
    client = TestClient(fresh_sbs)

    _create_snippet(client, "phase1_full_a", "hello world")

    resp = client.get("/snippets/")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    entry = next(s for s in body if s["name"] == "phase1_full_a")
    assert "content" not in entry
    assert "uuid" in entry


def test_list_snippets_fields_full_keeps_content(fresh_sbs):
    """Explicit ``?fields=full`` opts back into the complete object."""
    client = TestClient(fresh_sbs)

    _create_snippet(client, "phase1_full_b", "hello world")

    resp = client.get("/snippets/", params={"fields": "full"})
    assert resp.status_code == 200
    body = resp.json()
    entry = next(s for s in body if s["name"] == "phase1_full_b")
    assert entry["content"] == "hello world"


def test_list_snippets_fields_narrow_drops_content(fresh_sbs):
    """?fields=narrow returns the minimal listing-page set (no `content`)."""
    client = TestClient(fresh_sbs)

    _create_snippet(client, "phase1_slim_a", "body-a")
    _create_snippet(client, "phase1_slim_b", "body-b")

    resp = client.get("/snippets/", params={"fields": "narrow"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 2
    names = {s["name"] for s in body}
    assert {"phase1_slim_a", "phase1_slim_b"}.issubset(names)
    for s in body:
        assert "content" not in s
        assert "uuid" in s


def test_list_snippets_fields_wide_keeps_content(fresh_sbs):
    """``wide`` returns every persisted manifest field, including `content`."""
    client = TestClient(fresh_sbs)

    _create_snippet(client, "phase1_wide_a", "body-wide")

    resp = client.get("/snippets/", params={"fields": "wide"})
    assert resp.status_code == 200
    body = resp.json()
    entry = next(s for s in body if s["name"] == "phase1_wide_a")
    assert entry["content"] == "body-wide"


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


def test_search_snippets_default_is_narrow_with_score(fresh_sbs):
    """Default (no ``fields``) is equivalent to ``narrow`` — a slim
    snippet dict with ``similarity_score`` merged in, no ``content``."""
    client = TestClient(fresh_sbs)
    _create_snippet(client, "phase1_search_full", "body-a")

    resp = _search_snippets_via_mocked_vector(client, "phase1_search_full")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list) and len(body) == 1
    r = body[0]
    assert r["name"] == "phase1_search_full"
    assert "content" not in r
    assert r["similarity_score"] == 0.1


def test_search_snippets_fields_full_returns_full_with_score(fresh_sbs):
    """Explicit ``?fields=full`` opts back into the complete snippet
    dict with ``similarity_score`` merged in."""
    client = TestClient(fresh_sbs)
    _create_snippet(client, "phase1_search_explicit_full", "body-a")

    resp = _search_snippets_via_mocked_vector(
        client, "phase1_search_explicit_full", fields="full"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list) and len(body) == 1
    r = body[0]
    assert r["name"] == "phase1_search_explicit_full"
    assert r["content"] == "body-a"
    assert r["similarity_score"] == 0.1


def test_search_snippets_fields_narrow_returns_projected_with_score(fresh_sbs):
    """``?fields=narrow`` returns slim snippet dicts with score merged in."""
    client = TestClient(fresh_sbs)
    _create_snippet(client, "phase1_search_slim", "long body content")

    resp = _search_snippets_via_mocked_vector(
        client, "phase1_search_slim", fields="narrow"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list) and len(body) == 1
    r = body[0]
    assert r["name"] == "phase1_search_slim"
    assert r["similarity_score"] == 0.1
    assert "uuid" in r
    assert "content" not in r


# ── Phase 2 — list pagination / filter / sort ───────────────────────────


def test_list_snippets_pagination_returns_envelope(fresh_sbs):
    """Setting ``limit`` switches the response to the envelope shape."""
    client = TestClient(fresh_sbs)
    for i in range(5):
        _create_snippet(client, f"phase2_page_{i}", f"body {i}")

    resp = client.get("/snippets/", params={"limit": 2, "offset": 0, "fields": "list"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, dict)
    assert body["total"] >= 5
    assert body["offset"] == 0
    assert body["limit"] == 2
    assert len(body["items"]) == 2
    for it in body["items"]:
        assert "content" not in it


def test_list_snippets_bare_array_when_no_pagination(fresh_sbs):
    """Back-compat: no ``limit``/``offset`` → bare array."""
    client = TestClient(fresh_sbs)
    _create_snippet(client, "phase2_bare", "body")

    resp = client.get("/snippets/")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


def test_list_snippets_search_filter(fresh_sbs):
    """``search`` filters server-side over name + description."""
    client = TestClient(fresh_sbs)
    _create_snippet(client, "phase2_alpha_match", "aaa")
    _create_snippet(client, "phase2_beta_match", "bbb")
    _create_snippet(client, "phase2_gamma", "ccc")

    resp = client.get(
        "/snippets/",
        params={"search": "beta", "limit": 10, "offset": 0, "fields": "list"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    names = {i["name"] for i in body["items"]}
    assert names == {"phase2_beta_match"}


def test_facets_snippets_returns_tags_namespaces_states(fresh_sbs):
    """``GET /facets/snippets`` returns deduped/sorted picker options."""
    client = TestClient(fresh_sbs)

    for name, tags in [
        ("phase3_facet_a", ["python", "namespace:prod"]),
        ("phase3_facet_b", ["python", "namespace:dev"]),
        ("phase3_facet_c", ["docs"]),
    ]:
        params = {
            "name": name,
            "description": "d",
            "content": "x",
            "version": "1.0.0",
            "content_type": "text/plain",
            "state": "approved",
        }
        # httpx doesn't let dict values be lists; append tags via manual URL.
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        for t in tags:
            query += f"&tags={t}"
        resp = client.post(f"/snippets/?{query}")
        assert resp.status_code == 200, resp.text

    resp = client.get("/facets/snippets")
    assert resp.status_code == 200
    body = resp.json()
    assert "docs" in body["tags"] and "python" in body["tags"]
    assert "namespace:prod" not in body["tags"]  # namespace tags peeled off
    assert set(body["namespaces"]) >= {"prod", "dev"}
    assert "approved" in body["states"]


def test_list_snippets_sort_name_asc(fresh_sbs):
    """``sort=name:asc`` overrides the default modified_at desc."""
    client = TestClient(fresh_sbs)
    _create_snippet(client, "phase2_sortC", "x")
    _create_snippet(client, "phase2_sortA", "x")
    _create_snippet(client, "phase2_sortB", "x")

    resp = client.get(
        "/snippets/",
        params={
            "sort": "name:asc",
            "limit": 10,
            "offset": 0,
            "fields": "list",
            "search": "phase2_sort",
        },
    )
    assert resp.status_code == 200, resp.text
    names = [i["name"] for i in resp.json()["items"]]
    assert names == ["phase2_sortA", "phase2_sortB", "phase2_sortC"]
