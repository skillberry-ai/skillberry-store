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


def test_list_all_default_shape_is_unchanged():
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
    result = svc.list_all()
    assert result[0]["params"] == heavy
    assert result[0]["dependencies"] == ["dep1"]


def test_list_all_list_preset_drops_heavy_fields():
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
            "module_name": "a.py",
        },
    ]
    svc = ToolsService(h)
    result = svc.list_all(fields="list")
    assert result[0]["name"] == "a"
    assert result[0]["module_name"] == "a.py"
    for k in ("params", "returns", "dependencies", "packaging_params"):
        assert k not in result[0]


def test_list_all_custom_allowlist():
    h = _handler()
    h.list_all_dicts.return_value = [
        {"uuid": "u1", "name": "a", "modified_at": "2024-02-01", "params": {}},
    ]
    svc = ToolsService(h)
    result = svc.list_all(fields="uuid,name")
    assert result == [{"uuid": "u1", "name": "a"}]


def test_list_all_projection_does_not_mutate_cache_entries():
    original = {
        "uuid": "u1",
        "name": "a",
        "modified_at": "2024-02-01",
        "params": {"type": "object"},
    }
    h = _handler()
    h.list_all_dicts.return_value = [original]
    svc = ToolsService(h)
    svc.list_all(fields="list")
    assert original["params"] == {"type": "object"}


def test_get_module_returns_file_content():
    svc = ToolsService(_handler())
    content = svc.get_module("t1")
    assert "def hello" in content


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
