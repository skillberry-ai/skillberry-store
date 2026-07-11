import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from skillberry_store.services.skills_service import SkillsService


def _handler(exists=False):
    h = MagicMock()
    h.dependency_manager.get_dependents.return_value = []
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
    h.descriptions = None
    return h


def test_create_generates_uuid():
    mock_svc = MagicMock()
    with patch("skillberry_store.services.registry.get_service", return_value=mock_svc):
        svc = SkillsService(_handler())
        result = svc.create({"name": "sk1"})
    assert "uuid" in result


def test_create_raises_on_duplicate():
    svc = SkillsService(_handler(exists=True))
    with pytest.raises(ValueError, match="already exists"):
        svc.create({"name": "sk1"})


def test_populate_objects_adds_tools_and_snippets(monkeypatch):
    import skillberry_store.services.registry as registry
    tools_svc = MagicMock()
    tools_svc.get.return_value = {"uuid": "t1", "name": "tool1"}
    monkeypatch.setattr(registry, "_initialized", True)
    monkeypatch.setattr(
        registry, "_services", {"tool": tools_svc, "snippet": MagicMock()}
    )
    svc = SkillsService(_handler())
    skill = {"name": "sk1", "tool_uuids": ["t1"], "snippet_uuids": []}
    result = svc.populate_objects(skill)
    assert result["tools"] == [{"uuid": "t1", "name": "tool1"}]
    assert result["snippets"] == []


def test_list_all_returns_sorted_and_populated():
    svc = SkillsService(_handler())
    result = svc.list_all()
    assert len(result) == 1


def test_list_all_tolerates_skill_with_missing_tool():
    h = _handler()
    h.list_all_dicts.return_value = [
        {"name": "get_time", "modified_at": "2024-02-01", "tool_uuids": ["missing-uuid"], "snippet_uuids": []},
        {"name": "other", "modified_at": "2024-01-01", "tool_uuids": [], "snippet_uuids": []},
    ]
    svc = SkillsService(h)
    result = svc.list_all()
    assert len(result) == 2
    broken = next(r for r in result if r["name"] == "get_time")
    assert broken["tools"] == []
    assert broken["snippets"] == []


def test_list_all_default_populates_but_does_not_mutate_cache_entry(monkeypatch):
    import skillberry_store.services.registry as registry
    tools_svc = MagicMock()
    tools_svc.get.return_value = {"uuid": "t1", "name": "tool1"}
    snippets_svc = MagicMock()
    snippets_svc.get.return_value = {"uuid": "s1", "name": "snip1"}
    monkeypatch.setattr(registry, "_initialized", True)
    monkeypatch.setattr(
        registry, "_services", {"tool": tools_svc, "snippet": snippets_svc}
    )
    h = _handler()
    original = {
        "uuid": "sk1",
        "name": "sk1",
        "tool_uuids": ["t1"],
        "snippet_uuids": ["s1"],
        "modified_at": "2024-02-01",
    }
    h.list_all_dicts.return_value = [original]
    svc = SkillsService(h)
    result = svc.list_all()
    assert result[0]["tools"] == [{"uuid": "t1", "name": "tool1"}]
    assert result[0]["snippets"] == [{"uuid": "s1", "name": "snip1"}]
    # Regression: the cached dict must not have grown 'tools' / 'snippets'.
    assert "tools" not in original
    assert "snippets" not in original


def test_list_all_list_preset_skips_populate_and_keeps_uuid_arrays():
    h = _handler()
    h.list_all_dicts.return_value = [
        {
            "uuid": "sk1",
            "name": "sk1",
            "tool_uuids": ["t1", "t2"],
            "snippet_uuids": ["s1"],
            "modified_at": "2024-02-01",
        },
    ]
    svc = SkillsService(h)
    # No registry patching — a bug that reaches populate_objects would raise.
    result = svc.list_all(fields="list")
    assert result[0]["tool_uuids"] == ["t1", "t2"]
    assert result[0]["snippet_uuids"] == ["s1"]
    assert "tools" not in result[0]
    assert "snippets" not in result[0]


def test_list_all_custom_allowlist():
    h = _handler()
    h.list_all_dicts.return_value = [
        {
            "uuid": "sk1",
            "name": "sk1",
            "tool_uuids": ["t1"],
            "snippet_uuids": [],
            "modified_at": "2024-02-01",
        },
    ]
    svc = SkillsService(h)
    result = svc.list_all(fields="uuid,name")
    assert result == [{"uuid": "sk1", "name": "sk1"}]


def test_delete_updates_cache_then_deletes():
    h = _handler()
    mock_svc = MagicMock()
    with patch("skillberry_store.services.registry.get_service", return_value=mock_svc):
        svc = SkillsService(h)
        svc.delete("sk1")
    calls = [str(c) for c in h.mock_calls]
    assert any("update_cache" in c for c in calls)
    assert any("delete_object" in c for c in calls)
