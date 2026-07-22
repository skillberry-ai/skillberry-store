import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException
from skillberry_store.services.tools_service import ToolsService


def _handler(exists=False):
    h = MagicMock()
    h.dependency_manager.get_dependents.return_value = []
    h.object_exists.return_value = exists
    h.get_cache_parent_for_head.return_value = None
    h.resolve_to_uuid_or_error.return_value = "cccc-3333"
    h.read_dict.return_value = {
        "uuid": "cccc-3333", "name": "t1", "module_name": "t1.py",
        "created_at": "2024-01-01T00:00:00+00:00", "parent": None,
        "dependencies": [],
    }
    h.list_all_dicts.return_value = [{"name": "a", "modified_at": "2024-02-01"}]
    h.read_file.return_value = "def hello(): pass"
    h.read_dicts.return_value = []
    h.get_existing_names.return_value = []
    h.descriptions = None
    return h


def test_create_generates_uuid_and_timestamps():
    svc = ToolsService(_handler())
    result = svc.create({"name": "t1"}, module_content=b"def f(): pass", module_filename="t1.py")
    assert "uuid" in result
    assert result["module_name"] == "t1.py"


def test_create_raises_on_duplicate():
    svc = ToolsService(_handler(exists=True))
    with pytest.raises(ValueError, match="already exists"):
        svc.create({"name": "t1"}, module_content=b"def f(): pass", module_filename="t1.py")


def test_get_returns_tool_dict():
    svc = ToolsService(_handler())
    result = svc.get("t1")
    assert result["name"] == "t1"


def test_get_raises_key_error_when_not_found():
    h = _handler()
    h.resolve_to_uuid_or_error.side_effect = HTTPException(status_code=404, detail="not found")
    svc = ToolsService(h)
    with pytest.raises(KeyError):
        svc.get("missing")


def test_list_all_sorted():
    svc = ToolsService(_handler())
    result = svc.list_all()
    assert len(result) == 1


def test_list_all_default_is_narrow():
    """Default (no ``fields``) is the ``narrow`` preset — the heavy
    tool fields (params/returns/deps/packaging_*) are dropped."""
    h = _handler()
    heavy = {
        "type": "object",
        "properties": {"x": {"type": "int"}},
        "required": [],
        "optional": [],
    }
    h.list_all_dicts.return_value = [
        {
            "uuid": "u1",
            "name": "a",
            "modified_at": "2024-02-01",
            "module_name": "a.py",
            "params": heavy,
            "returns": {"type": "int"},
            "dependencies": ["dep1"],
            "packaging_params": {"foo": "bar"},
        },
    ]
    svc = ToolsService(h)
    result = svc.list_all()
    assert result[0]["module_name"] == "a.py"
    for k in ("params", "returns", "dependencies", "packaging_params"):
        assert k not in result[0]


def test_list_all_fields_full_keeps_heavy_fields():
    """Explicit ``fields="full"`` opts into the complete tool dict."""
    h = _handler()
    heavy = {
        "type": "object",
        "properties": {"x": {"type": "int"}},
        "required": [],
        "optional": [],
    }
    h.list_all_dicts.return_value = [
        {
            "uuid": "u1",
            "name": "a",
            "modified_at": "2024-02-01",
            "params": heavy,
            "returns": {"type": "int"},
            "dependencies": ["dep1"],
            "packaging_params": {"foo": "bar"},
        },
    ]
    svc = ToolsService(h)
    result = svc.list_all(fields="full")
    assert result[0]["params"] == heavy
    assert result[0]["dependencies"] == ["dep1"]


def test_list_all_narrow_preset_drops_heavy_fields():
    h = _handler()
    h.list_all_dicts.return_value = [
        {
            "uuid": "u1",
            "name": "a",
            "modified_at": "2024-02-01",
            "params": {"type": "object"},
            "returns": {"type": "int"},
            "dependencies": ["dep1"],
            "packaging_params": {"foo": "bar"},
            "programming_language": "python",
            "packaging_format": "code",
            "module_name": "a.py",
        },
    ]
    svc = ToolsService(h)
    result = svc.list_all(fields="narrow")
    assert result[0]["name"] == "a"
    assert result[0]["module_name"] == "a.py"
    for k in (
        "params",
        "returns",
        "dependencies",
        "packaging_params",
        "programming_language",
        "packaging_format",
    ):
        assert k not in result[0], f"narrow unexpectedly contains {k}"


def test_list_all_wide_preset_keeps_persisted_fields():
    """``wide`` returns every persisted manifest field — the heavy ones
    that ``narrow`` drops (params/returns/deps/etc) come back."""
    h = _handler()
    h.list_all_dicts.return_value = [
        {
            "uuid": "u1",
            "name": "a",
            "modified_at": "2024-02-01",
            "params": {"type": "object"},
            "returns": {"type": "int"},
            "dependencies": ["dep1"],
            "packaging_params": {"foo": "bar"},
            "programming_language": "python",
            "module_name": "a.py",
        },
    ]
    svc = ToolsService(h)
    result = svc.list_all(fields="wide")
    r = result[0]
    assert r["params"] == {"type": "object"}
    assert r["dependencies"] == ["dep1"]
    assert r["programming_language"] == "python"


def test_list_all_custom_allowlist():
    h = _handler()
    h.list_all_dicts.return_value = [
        {"uuid": "u1", "name": "a", "modified_at": "2024-02-01", "params": {}},
    ]
    svc = ToolsService(h)
    result = svc.list_all(fields="uuid,name")
    assert result == [{"uuid": "u1", "name": "a"}]


def test_list_all_field_selection_does_not_mutate_cache_entries():
    original = {
        "uuid": "u1",
        "name": "a",
        "modified_at": "2024-02-01",
        "params": {"type": "object"},
    }
    h = _handler()
    h.list_all_dicts.return_value = [original]
    svc = ToolsService(h)
    svc.list_all(fields="narrow")
    assert original["params"] == {"type": "object"}


def test_get_module_returns_file_content():
    svc = ToolsService(_handler())
    content = svc.get_module("t1")
    assert "def hello" in content


def _search_handler_tools(cached_tool):
    h = _handler()
    h.read_dict.return_value = cached_tool
    h.resolve_to_uuid_or_error.return_value = cached_tool["uuid"]
    h.descriptions = MagicMock()
    h.descriptions.search_description.return_value = [
        {"filename": cached_tool["name"], "similarity_score": 0.3}
    ]
    return h


def test_search_default_returns_narrow_object_with_score():
    """Default ``fields=None`` resolves to ``narrow`` — a slim tool
    dict with ``similarity_score`` merged in (no ``params``)."""
    cached = {
        "uuid": "u1",
        "name": "t1",
        "state": "approved",
        "module_name": "t1.py",
        "params": {"type": "object"},
        "modified_at": "2024-02-01",
    }
    svc = ToolsService(_search_handler_tools(cached))
    result = svc.search("q")
    assert len(result) == 1
    r = result[0]
    assert r["name"] == "t1"
    assert r["module_name"] == "t1.py"
    assert "params" not in r
    assert r["similarity_score"] == 0.3


def test_search_fields_full_returns_full_object_with_score():
    """Explicit ``fields="full"`` returns the complete tool dict."""
    cached = {
        "uuid": "u1",
        "name": "t1",
        "state": "approved",
        "params": {"type": "object"},
        "modified_at": "2024-02-01",
    }
    svc = ToolsService(_search_handler_tools(cached))
    result = svc.search("q", fields="full")
    assert len(result) == 1
    r = result[0]
    assert r["params"] == {"type": "object"}
    assert r["similarity_score"] == 0.3


def test_search_does_not_mutate_cache_entry():
    cached = {
        "uuid": "u1",
        "name": "t1",
        "state": "approved",
        "params": {"type": "object"},
        "modified_at": "2024-02-01",
    }
    svc = ToolsService(_search_handler_tools(cached))
    svc.search("q")
    assert "similarity_score" not in cached


def test_search_with_fields_narrow_drops_heavy_fields():
    cached = {
        "uuid": "u1",
        "name": "t1",
        "state": "approved",
        "params": {"type": "object"},
        "returns": {"type": "int"},
        "dependencies": ["d1"],
        "packaging_params": {"foo": "bar"},
        "module_name": "t1.py",
        "modified_at": "2024-02-01",
    }
    svc = ToolsService(_search_handler_tools(cached))
    result = svc.search("q", fields="narrow")
    r = result[0]
    assert r["name"] == "t1"
    assert r["module_name"] == "t1.py"
    assert r["similarity_score"] == 0.3
    for k in ("params", "returns", "dependencies", "packaging_params"):
        assert k not in r


# ── Phase 2 — list_all filter / sort / paginate ─────────────────────────


def _list_handler_tools(items):
    h = _handler()
    h.list_all_dicts.return_value = items
    return h


def test_list_all_pagination_envelope():
    items = [
        {"uuid": f"u{i}", "name": f"t{i}", "modified_at": f"2024-01-{i:02d}"}
        for i in range(1, 6)
    ]
    svc = ToolsService(_list_handler_tools(items))
    result = svc.list_all(limit=2, offset=0)
    assert isinstance(result, dict)
    assert result["total"] == 5
    assert len(result["items"]) == 2


def test_list_all_search_and_state_filters():
    items = [
        {"uuid": "u1", "name": "http_get", "description": "d", "state": "approved", "modified_at": "2024-03"},
        {"uuid": "u2", "name": "http_post", "description": "d", "state": "new", "modified_at": "2024-02"},
        {"uuid": "u3", "name": "sort", "description": "d", "state": "approved", "modified_at": "2024-01"},
    ]
    svc = ToolsService(_list_handler_tools(items))
    result = svc.list_all(search="http", state="approved")
    assert [i["name"] for i in result] == ["http_get"]


def test_delete_updates_cache_then_deletes():
    h = _handler()
    svc = ToolsService(h)
    svc.delete("t1")
    calls = [str(c) for c in h.mock_calls]
    update_idx = next(i for i, c in enumerate(calls) if "update_cache" in c)
    delete_idx = next(i for i, c in enumerate(calls) if "delete_object" in c)
    assert update_idx < delete_idx


def test_find_dependencies_returns_empty_for_no_deps():
    svc = ToolsService(_handler())
    result = svc.find_dependencies([], "t1")
    assert result == set()
