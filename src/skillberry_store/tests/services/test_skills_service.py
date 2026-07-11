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


def test_list_all_full_tolerates_skill_with_missing_tool():
    """``fields="full"`` triggers ``_populate`` — a missing tool UUID
    resolves to an empty populated list rather than raising."""
    h = _handler()
    h.list_all_dicts.return_value = [
        {"name": "get_time", "modified_at": "2024-02-01", "tool_uuids": ["missing-uuid"], "snippet_uuids": []},
        {"name": "other", "modified_at": "2024-01-01", "tool_uuids": [], "snippet_uuids": []},
    ]
    svc = SkillsService(h)
    result = svc.list_all(fields="full")
    assert len(result) == 2
    broken = next(r for r in result if r["name"] == "get_time")
    assert broken["tools"] == []
    assert broken["snippets"] == []


def test_list_all_default_is_narrow_skips_populate():
    """Default (no ``fields``) is ``narrow``; the ``_populate`` mechanism
    does NOT run — no ``tools`` / ``snippets`` inlining. Callers read
    counts from ``tool_uuids`` / ``snippet_uuids``. This runs without a
    registry: a bug that reaches ``populate_objects`` would raise."""
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
    assert result[0]["tool_uuids"] == ["t1"]
    assert result[0]["snippet_uuids"] == ["s1"]
    assert "tools" not in result[0]
    assert "snippets" not in result[0]
    # Regression: the cached dict must not have grown 'tools' / 'snippets'.
    assert "tools" not in original
    assert "snippets" not in original


def test_list_all_fields_full_populates_but_does_not_mutate_cache_entry(monkeypatch):
    """``fields="full"`` triggers ``_populate``: ``tools`` / ``snippets``
    are inlined on the result but not written back to the cache."""
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
    result = svc.list_all(fields="full")
    assert result[0]["tools"] == [{"uuid": "t1", "name": "tool1"}]
    assert result[0]["snippets"] == [{"uuid": "s1", "name": "snip1"}]
    # Regression: the cached dict must not have grown 'tools' / 'snippets'.
    assert "tools" not in original
    assert "snippets" not in original


def test_list_all_narrow_preset_skips_populate_and_keeps_uuid_arrays():
    """``narrow`` does not tag ``_populate``, so ``populate_objects`` must
    not run — callers read counts from ``tool_uuids`` / ``snippet_uuids``."""
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
    result = svc.list_all(fields="narrow")
    assert result[0]["tool_uuids"] == ["t1", "t2"]
    assert result[0]["snippet_uuids"] == ["s1"]
    assert "tools" not in result[0]
    assert "snippets" not in result[0]


def test_list_all_wide_preset_skips_populate():
    """``wide`` is manifest data only — no flag fields, no bundling."""
    h = _handler()
    h.list_all_dicts.return_value = [
        {
            "uuid": "sk1",
            "name": "sk1",
            "tool_uuids": ["t1"],
            "snippet_uuids": ["s1"],
            "modified_at": "2024-02-01",
        },
    ]
    svc = SkillsService(h)
    result = svc.list_all(fields="wide")
    assert result[0]["tool_uuids"] == ["t1"]
    assert "tools" not in result[0]
    assert "snippets" not in result[0]


def test_list_all_populate_flag_in_csv_triggers_populate(monkeypatch):
    """Explicit CSV allowlist containing ``_populate`` must run the
    populate mechanism."""
    from skillberry_store.services import registry

    tools_svc = MagicMock()
    tools_svc.get.side_effect = lambda u, fields=None: {"uuid": u, "name": f"tool-{u}"}
    snippets_svc = MagicMock()
    snippets_svc.get.side_effect = lambda u, fields=None: {"uuid": u, "name": f"snip-{u}"}
    monkeypatch.setattr(registry, "_initialized", True)
    monkeypatch.setattr(
        registry, "_services", {"tool": tools_svc, "snippet": snippets_svc}
    )
    h = _handler()
    h.list_all_dicts.return_value = [
        {
            "uuid": "sk1",
            "name": "sk1",
            "tool_uuids": ["t1"],
            "snippet_uuids": ["s1"],
            "modified_at": "2024-02-01",
        },
    ]
    svc = SkillsService(h)
    result = svc.list_all(fields="uuid,tools,snippets,_populate")
    assert result[0]["tools"] == [{"uuid": "t1", "name": "tool-t1"}]
    assert result[0]["snippets"] == [{"uuid": "s1", "name": "snip-s1"}]


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


def _search_handler_skills(cached_skill):
    """Search relies on ``handler.read_dict(uuid)`` directly (unlike snippets/tools)."""
    h = _handler()
    h.read_dict.return_value = cached_skill
    h.descriptions = MagicMock()
    h.descriptions.search_description.return_value = [
        {"filename": cached_skill["uuid"], "similarity_score": 0.4}
    ]
    return h


def test_search_default_is_narrow_skips_populate():
    """Default ``fields=None`` resolves to ``narrow`` — ``_populate``
    does NOT run and the response omits the inlined ``tools`` /
    ``snippets`` (callers use ``tool_uuids`` / ``snippet_uuids``). This
    runs without a registry: a bug reaching ``populate_objects`` would
    raise."""
    cached = {
        "uuid": "sk1",
        "name": "sk1",
        "state": "approved",
        "tool_uuids": ["t1"],
        "snippet_uuids": ["s1"],
        "modified_at": "2024-02-01",
    }
    svc = SkillsService(_search_handler_skills(cached))
    result = svc.search("q")
    assert len(result) == 1
    r = result[0]
    assert r["name"] == "sk1"
    assert r["tool_uuids"] == ["t1"]
    assert r["snippet_uuids"] == ["s1"]
    assert "tools" not in r
    assert "snippets" not in r
    assert r["similarity_score"] == 0.4


def test_search_fields_full_runs_populate_and_returns_full_object(monkeypatch):
    """Explicit ``fields="full"`` triggers ``_populate`` — the response
    includes inlined ``tools`` / ``snippets``."""
    from skillberry_store.services import registry

    tools_svc = MagicMock()
    tools_svc.get.side_effect = lambda u, fields=None: {"uuid": u, "name": f"tool-{u}"}
    snippets_svc = MagicMock()
    snippets_svc.get.side_effect = lambda u, fields=None: {"uuid": u, "name": f"snip-{u}"}
    monkeypatch.setattr(registry, "_initialized", True)
    monkeypatch.setattr(
        registry, "_services", {"tool": tools_svc, "snippet": snippets_svc}
    )
    cached = {
        "uuid": "sk1",
        "name": "sk1",
        "state": "approved",
        "tool_uuids": ["t1"],
        "snippet_uuids": ["s1"],
        "modified_at": "2024-02-01",
    }
    svc = SkillsService(_search_handler_skills(cached))
    result = svc.search("q", fields="full")
    assert len(result) == 1
    r = result[0]
    assert r["name"] == "sk1"
    assert r["tools"] == [{"uuid": "t1", "name": "tool-t1"}]
    assert r["snippets"] == [{"uuid": "s1", "name": "snip-s1"}]
    assert r["similarity_score"] == 0.4


def test_search_does_not_mutate_cache_entry():
    """Search must not attach ``similarity_score`` (or bundled outputs)
    onto the shared cache dict — the field is only merged into the
    per-match projected copy."""
    cached = {
        "uuid": "sk1",
        "name": "sk1",
        "state": "approved",
        "tool_uuids": ["t1"],
        "snippet_uuids": [],
        "modified_at": "2024-02-01",
    }
    svc = SkillsService(_search_handler_skills(cached))
    svc.search("q", fields="narrow")
    assert "similarity_score" not in cached
    assert "tools" not in cached
    assert "snippets" not in cached


def test_search_with_fields_narrow_skips_populate_and_keeps_uuid_arrays():
    cached = {
        "uuid": "sk1",
        "name": "sk1",
        "state": "approved",
        "tool_uuids": ["t1", "t2"],
        "snippet_uuids": ["s1"],
        "modified_at": "2024-02-01",
    }
    svc = SkillsService(_search_handler_skills(cached))
    # No registry patching — reaching populate_objects would raise.
    result = svc.search("q", fields="narrow")
    r = result[0]
    assert r["tool_uuids"] == ["t1", "t2"]
    assert r["snippet_uuids"] == ["s1"]
    assert r["similarity_score"] == 0.4
    assert "tools" not in r
    assert "snippets" not in r


# ── Phase 2 — list_all filter / sort / paginate ─────────────────────────


def _list_handler_skills(items):
    h = _handler()
    h.list_all_dicts.return_value = items
    return h


def test_list_all_pagination_envelope_with_fields_list_skips_populate():
    items = [
        {
            "uuid": f"sk{i}",
            "name": f"sk{i}",
            "tool_uuids": [f"t{i}"],
            "snippet_uuids": [],
            "modified_at": f"2024-01-{i:02d}",
        }
        for i in range(1, 6)
    ]
    svc = SkillsService(_list_handler_skills(items))
    # No registry patching; populate would raise if it ran.
    result = svc.list_all(fields="list", limit=2, offset=0)
    assert isinstance(result, dict)
    assert result["total"] == 5
    for it in result["items"]:
        assert "tools" not in it
        assert "tool_uuids" in it


def test_list_all_search_filters_before_pagination():
    items = [
        {"uuid": f"sk{i}", "name": f"foo{i}", "description": "d",
         "tool_uuids": [], "snippet_uuids": [], "modified_at": f"2024-01-{i:02d}"}
        for i in range(1, 4)
    ] + [
        {"uuid": "sk9", "name": "bar", "description": "d",
         "tool_uuids": [], "snippet_uuids": [], "modified_at": "2024-01-10"},
    ]
    svc = SkillsService(_list_handler_skills(items))
    result = svc.list_all(fields="list", search="foo", limit=2, offset=0)
    assert result["total"] == 3
    assert len(result["items"]) == 2


def test_list_all_populate_only_runs_on_the_page(monkeypatch):
    """When fields is omitted, populate should run on the returned page —
    not on the entire cache — so paginating a huge store does not fan out
    thousands of tool/snippet reads."""
    import skillberry_store.services.registry as registry

    tools_svc = MagicMock()
    tools_svc.get.side_effect = lambda uuid: {"uuid": uuid, "name": uuid}
    snippets_svc = MagicMock()
    snippets_svc.get.side_effect = lambda uuid: {"uuid": uuid, "name": uuid}
    monkeypatch.setattr(registry, "_initialized", True)
    monkeypatch.setattr(
        registry, "_services", {"tool": tools_svc, "snippet": snippets_svc}
    )

    items = [
        {
            "uuid": f"sk{i}",
            "name": f"sk{i}",
            "tool_uuids": [f"t{i}"],
            "snippet_uuids": [f"s{i}"],
            "modified_at": f"2024-01-{i:02d}",
        }
        for i in range(1, 6)
    ]
    svc = SkillsService(_list_handler_skills(items))
    result = svc.list_all(limit=2, offset=0)
    assert result["total"] == 5
    assert len(result["items"]) == 2
    # Only the two skills on the page should have triggered populate.
    assert tools_svc.get.call_count == 2
    assert snippets_svc.get.call_count == 2
