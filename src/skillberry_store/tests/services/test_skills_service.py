import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from skillberry_store.services.skills_service import SkillsService


def _handler(exists=False):
    h = MagicMock()
    h.object_exists.return_value = exists
    h.get_cache_parent_for_head.return_value = None
    h.resolve_to_uuid_or_error.return_value = "bbbb-2222"
    h.read_dict.return_value = {
        "uuid": "bbbb-2222", "name": "sk1",
        "tool_uuids": [], "snippet_uuids": [],
        "created_at": "2024-01-01T00:00:00+00:00", "parent": None,
    }
    h.list_all_dicts.return_value = [
        {"name": "a", "modified_at": "2024-02-01", "tool_uuids": [], "snippet_uuids": []},
    ]
    return h


def test_create_generates_uuid():
    svc = SkillsService(_handler(), tools_handler=MagicMock(), snippets_handler=MagicMock())
    result = svc.create({"name": "sk1"})
    assert "uuid" in result


def test_create_raises_on_duplicate():
    svc = SkillsService(_handler(exists=True), tools_handler=MagicMock(), snippets_handler=MagicMock())
    with pytest.raises(ValueError, match="already exists"):
        svc.create({"name": "sk1"})


def test_populate_objects_adds_tools_and_snippets():
    tools_h = MagicMock()
    tools_h.read_dicts.return_value = [{"uuid": "t1", "name": "tool1"}]
    snippets_h = MagicMock()
    snippets_h.read_dicts.return_value = []
    svc = SkillsService(_handler(), tools_handler=tools_h, snippets_handler=snippets_h)
    skill = {"name": "sk1", "tool_uuids": ["t1"], "snippet_uuids": []}
    result = svc.populate_objects(skill)
    assert result["tools"] == [{"uuid": "t1", "name": "tool1"}]
    assert result["snippets"] == []


def test_list_all_returns_sorted_and_populated():
    th, sh = MagicMock(), MagicMock()
    th.read_dicts.return_value = []
    sh.read_dicts.return_value = []
    svc = SkillsService(_handler(), tools_handler=th, snippets_handler=sh)
    result = svc.list_all()
    assert len(result) == 1


def test_delete_updates_cache_then_deletes():
    h = _handler()
    svc = SkillsService(h, tools_handler=MagicMock(), snippets_handler=MagicMock())
    svc.delete("sk1")
    calls = [str(c) for c in h.mock_calls]
    assert any("update_cache" in c for c in calls)
    assert any("delete_object" in c for c in calls)
