import pytest
from unittest.mock import MagicMock, call
from skillberry_store.services.snippets_service import SnippetsService


def _handler(exists=False):
    h = MagicMock()
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
    desc = MagicMock()
    svc = SnippetsService(h, descriptions=desc)
    svc.create({"name": "s1", "content": "x", "description": "about it"})
    desc.write_description.assert_called_once()


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
    desc = MagicMock()
    svc = SnippetsService(h, descriptions=desc)
    svc.delete("s1")
    desc.delete_description.assert_called_once_with("aaaa-1111")
