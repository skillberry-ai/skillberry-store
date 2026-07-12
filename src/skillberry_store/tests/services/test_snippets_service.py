import pytest
from unittest.mock import MagicMock, call
from skillberry_store.services.snippets_service import SnippetsService


def _handler(exists=False):
    h = MagicMock()
    h.dependency_manager.get_dependents.return_value = []
    h.object_exists.return_value = exists
    h.get_cache_parent_for_head.return_value = "some-parent"
    h.resolve_to_uuid_or_error.return_value = "aaaa-1111"
    h.read_dict.return_value = {
        "uuid": "aaaa-1111", "name": "s1", "content": "x",
        "created_at": "2024-01-01T00:00:00+00:00", "parent": None,
    }
    h.list_all_dicts.return_value = [
        {"name": "a", "modified_at": "2024-02-01"},
        {"name": "b", "modified_at": "2024-01-01"},
    ]
    h.descriptions = None
    return h


def test_create_generates_uuid_and_timestamps():
    svc = SnippetsService(_handler())
    result = svc.create({"name": "s1", "content": "hello"})
    assert "uuid" in result
    assert "created_at" in result
    assert "modified_at" in result


def test_create_writes_and_updates_cache():
    h = _handler()
    svc = SnippetsService(h)
    svc.create({"name": "s1", "content": "hello"})
    h.write_dict.assert_called_once()
    h.update_cache.assert_called_once()


def test_create_raises_on_duplicate_uuid():
    svc = SnippetsService(_handler(exists=True))
    with pytest.raises(ValueError, match="already exists"):
        svc.create({"name": "s1", "content": "x"})


def test_create_writes_description_when_provided():
    h = _handler()
    h.descriptions = MagicMock()
    svc = SnippetsService(h)
    svc.create({"name": "s1", "content": "x", "description": "about it"})
    h.descriptions.write_description.assert_called_once()


def test_get_returns_dict():
    h = _handler()
    svc = SnippetsService(h)
    result = svc.get("s1")
    assert result["name"] == "s1"


def test_get_raises_key_error_when_not_found():
    h = _handler()
    from fastapi import HTTPException
    h.resolve_to_uuid_or_error.side_effect = HTTPException(status_code=404, detail="not found")
    svc = SnippetsService(h)
    with pytest.raises(KeyError):
        svc.get("missing")


def test_list_all_returns_sorted():
    svc = SnippetsService(_handler())
    result = svc.list_all()
    assert result[0]["name"] == "a"  # most recent first


def test_list_all_default_is_narrow():
    """Default (no ``fields`` argument) is the ``narrow`` preset — heavy
    fields like ``content`` are dropped."""
    h = _handler()
    h.list_all_dicts.return_value = [
        {"uuid": "u1", "name": "a", "content": "body", "modified_at": "2024-02-01"},
    ]
    svc = SnippetsService(h)
    result = svc.list_all()
    assert "content" not in result[0]
    assert result[0]["uuid"] == "u1"


def test_list_all_fields_full_keeps_content():
    """Explicit ``fields="full"`` opts back into the complete object."""
    h = _handler()
    h.list_all_dicts.return_value = [
        {"uuid": "u1", "name": "a", "content": "body", "modified_at": "2024-02-01"},
    ]
    svc = SnippetsService(h)
    result = svc.list_all(fields="full")
    assert result[0].get("content") == "body"


def test_list_all_narrow_preset_drops_content():
    h = _handler()
    h.list_all_dicts.return_value = [
        {"uuid": "u1", "name": "a", "content": "body", "modified_at": "2024-02-01"},
        {"uuid": "u2", "name": "b", "content": "big", "modified_at": "2024-01-01"},
    ]
    svc = SnippetsService(h)
    result = svc.list_all(fields="narrow")
    assert [r["name"] for r in result] == ["a", "b"]
    assert all("content" not in r for r in result)
    assert all("uuid" in r for r in result)


def test_list_all_wide_preset_keeps_content():
    """``wide`` is every persisted manifest field — including ``content``."""
    h = _handler()
    h.list_all_dicts.return_value = [
        {"uuid": "u1", "name": "a", "content": "body", "modified_at": "2024-02-01"},
    ]
    svc = SnippetsService(h)
    result = svc.list_all(fields="wide")
    assert result[0]["content"] == "body"


def test_list_all_custom_allowlist():
    h = _handler()
    h.list_all_dicts.return_value = [
        {"uuid": "u1", "name": "a", "content": "body", "modified_at": "2024-02-01"},
    ]
    svc = SnippetsService(h)
    result = svc.list_all(fields="uuid,name")
    assert result == [{"uuid": "u1", "name": "a"}]


def test_list_all_field_selection_does_not_mutate_cache_entries():
    original = {"uuid": "u1", "name": "a", "content": "body", "modified_at": "2024-02-01"}
    h = _handler()
    h.list_all_dicts.return_value = [original]
    svc = SnippetsService(h)
    svc.list_all(fields="narrow")
    assert "content" in original
    assert original == {
        "uuid": "u1",
        "name": "a",
        "content": "body",
        "modified_at": "2024-02-01",
    }




def test_update_merges_and_preserves_created_at():
    h = _handler()
    svc = SnippetsService(h)
    result = svc.update("s1", {"name": "s1", "content": "new"})
    assert result["created_at"] == "2024-01-01T00:00:00+00:00"
    assert result["content"] == "new"


def test_delete_updates_cache_before_delete():
    h = _handler()
    svc = SnippetsService(h)
    svc.delete("s1")
    # cache updated before object deleted
    cache_call_order = [str(c) for c in h.mock_calls]
    update_idx = next(i for i, c in enumerate(cache_call_order) if "update_cache" in c)
    delete_idx = next(i for i, c in enumerate(cache_call_order) if "delete_object" in c)
    assert update_idx < delete_idx


def test_delete_cleans_up_description():
    h = _handler()
    h.descriptions = MagicMock()
    svc = SnippetsService(h)
    svc.delete("s1")
    h.descriptions.delete_description.assert_called_once_with("aaaa-1111")


def _search_handler(cached_snippet):
    """Handler mock wired for search tests. Returns ``cached_snippet`` from
    ``read_dict`` and drives one vector match for ``search_term`` == 's1'."""
    h = _handler()
    h.read_dict.return_value = cached_snippet
    h.resolve_to_uuid_or_error.return_value = cached_snippet["uuid"]
    h.descriptions = MagicMock()
    h.descriptions.search_description.return_value = [
        {"filename": cached_snippet["name"], "similarity_score": 0.2}
    ]
    return h


def test_search_default_returns_narrow_object_with_score():
    """Default ``fields=None`` resolves to ``narrow`` — each match is a
    slim snippet dict with ``similarity_score`` merged in (no
    ``content``)."""
    cached = {
        "uuid": "u1",
        "name": "s1",
        "description": "d",
        "content": "big body",
        "state": "approved",
        "tags": ["a"],
        "modified_at": "2024-02-01",
    }
    svc = SnippetsService(_search_handler(cached))
    result = svc.search("q")
    assert len(result) == 1
    r = result[0]
    assert r["uuid"] == "u1"
    assert r["name"] == "s1"
    assert "content" not in r
    assert r["similarity_score"] == 0.2


def test_search_fields_full_returns_full_object_with_score():
    """Explicit ``fields="full"`` returns the complete snippet dict
    with ``similarity_score`` merged in."""
    cached = {
        "uuid": "u1",
        "name": "s1",
        "content": "big body",
        "state": "approved",
        "modified_at": "2024-02-01",
    }
    svc = SnippetsService(_search_handler(cached))
    result = svc.search("q", fields="full")
    assert len(result) == 1
    r = result[0]
    assert r["content"] == "big body"
    assert r["similarity_score"] == 0.2


def test_search_does_not_mutate_cache_entry():
    """Regression: previously the service assigned similarity_score onto
    the dereferenced dict, polluting the DictCache."""
    cached = {
        "uuid": "u1",
        "name": "s1",
        "content": "body",
        "state": "approved",
        "modified_at": "2024-02-01",
    }
    svc = SnippetsService(_search_handler(cached))
    svc.search("q")
    assert "similarity_score" not in cached


def test_search_with_fields_narrow_returns_projected_plus_score():
    cached = {
        "uuid": "u1",
        "name": "s1",
        "description": "d",
        "content": "big body",
        "state": "approved",
        "tags": ["a"],
        "modified_at": "2024-02-01",
    }
    svc = SnippetsService(_search_handler(cached))
    result = svc.search("q", fields="narrow")
    assert len(result) == 1
    r = result[0]
    assert r["name"] == "s1"
    assert r["similarity_score"] == 0.2
    assert "content" not in r


def test_search_with_custom_fields_allowlist():
    cached = {
        "uuid": "u1",
        "name": "s1",
        "content": "body",
        "state": "approved",
        "modified_at": "2024-02-01",
    }
    svc = SnippetsService(_search_handler(cached))
    result = svc.search("q", fields="uuid,name")
    assert result == [{"uuid": "u1", "name": "s1", "similarity_score": 0.2}]


# ── Phase 2 — list_all filter / sort / paginate ─────────────────────────


def _list_handler(items):
    h = _handler()
    h.list_all_dicts.return_value = items
    return h


def test_list_all_search_filters_by_name_and_description():
    items = [
        {"uuid": "u1", "name": "alpha", "description": "one", "modified_at": "2024-03"},
        {"uuid": "u2", "name": "beta", "description": "matchable", "modified_at": "2024-02"},
        {"uuid": "u3", "name": "gamma", "description": "zzz", "modified_at": "2024-01"},
    ]
    svc = SnippetsService(_list_handler(items))
    result = svc.list_all(search="MATCH")
    assert [i["name"] for i in result] == ["beta"]


def test_list_all_tags_filter_and_semantics():
    items = [
        {"uuid": "u1", "name": "a", "tags": ["red"], "modified_at": "2024-03"},
        {"uuid": "u2", "name": "b", "tags": ["red", "blue"], "modified_at": "2024-02"},
    ]
    svc = SnippetsService(_list_handler(items))
    result = svc.list_all(tags=["red", "blue"])
    assert [i["name"] for i in result] == ["b"]


def test_list_all_state_filter():
    items = [
        {"uuid": "u1", "name": "a", "state": "approved", "modified_at": "2024-03"},
        {"uuid": "u2", "name": "b", "state": "new", "modified_at": "2024-02"},
    ]
    svc = SnippetsService(_list_handler(items))
    result = svc.list_all(state="new")
    assert [i["name"] for i in result] == ["b"]


def test_list_all_sort_name_asc():
    items = [
        {"uuid": "u1", "name": "b", "modified_at": "2024-03"},
        {"uuid": "u2", "name": "a", "modified_at": "2024-02"},
    ]
    svc = SnippetsService(_list_handler(items))
    result = svc.list_all(sort="name:asc")
    assert [i["name"] for i in result] == ["a", "b"]


def test_list_all_pagination_envelope():
    items = [
        {"uuid": f"u{i}", "name": f"n{i}", "modified_at": f"2024-01-{i:02d}"}
        for i in range(1, 6)
    ]
    svc = SnippetsService(_list_handler(items))
    result = svc.list_all(limit=2, offset=1)
    assert isinstance(result, dict)
    assert result["total"] == 5
    assert result["offset"] == 1
    assert result["limit"] == 2
    assert len(result["items"]) == 2


def test_list_all_no_pagination_returns_bare_list():
    items = [{"uuid": "u1", "name": "a", "modified_at": "2024-02-01"}]
    svc = SnippetsService(_list_handler(items))
    result = svc.list_all()
    assert isinstance(result, list)


def test_list_all_envelope_total_is_pre_slice_post_filter():
    items = [
        {"uuid": f"u{i}", "name": f"foo{i}", "modified_at": f"2024-01-{i:02d}"}
        for i in range(1, 6)
    ] + [
        {"uuid": "u9", "name": "bar", "modified_at": "2024-01-10"},
    ]
    svc = SnippetsService(_list_handler(items))
    result = svc.list_all(search="foo", limit=2, offset=0)
    assert result["total"] == 5
    assert len(result["items"]) == 2


def test_list_all_paginated_with_fields_list_projects_only_the_page():
    items = [
        {"uuid": f"u{i}", "name": f"n{i}", "content": "heavy" * 100, "modified_at": f"2024-01-{i:02d}"}
        for i in range(1, 6)
    ]
    svc = SnippetsService(_list_handler(items))
    result = svc.list_all(fields="narrow", limit=2, offset=0)
    assert result["total"] == 5
    for it in result["items"]:
        assert "content" not in it
