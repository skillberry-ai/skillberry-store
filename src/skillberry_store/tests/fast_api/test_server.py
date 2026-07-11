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
