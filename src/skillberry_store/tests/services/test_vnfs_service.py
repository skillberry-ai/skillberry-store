import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from skillberry_store.services.vnfs_service import VnfsService


def _handler(exists=False):
    h = MagicMock()
    h.object_exists.return_value = exists
    h.get_cache_parent_for_head.return_value = None
    h.resolve_to_uuid_or_error.return_value = "dddd-4444"
    h.read_dict.return_value = {
        "uuid": "dddd-4444", "name": "v1", "port": 9000,
        "created_at": "2024-01-01T00:00:00+00:00", "parent": None,
    }
    h.list_all_dicts.return_value = [{"uuid": "dddd-4444", "name": "v1", "port": 9000, "modified_at": "2024-02-01"}]
    return h


def _manager():
    m = MagicMock()
    runtime = MagicMock()
    runtime.port = 9000
    runtime.running = True
    runtime.export_path = "/tmp/export"
    m.add_server.return_value = runtime
    m.get_server.return_value = runtime
    return m


def test_create_returns_dict_with_port():
    svc = VnfsService(_handler(), _manager())
    result = svc.create({"name": "v1", "uuid": None})
    assert "uuid" in result
    assert result["port"] == 9000


def test_create_raises_on_duplicate():
    svc = VnfsService(_handler(exists=True), _manager())
    with pytest.raises(ValueError, match="already exists"):
        svc.create({"name": "v1", "uuid": None})


def test_list_includes_running_status():
    svc = VnfsService(_handler(), _manager())
    result = svc.list_all()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["running"] is True


def test_delete_stops_runtime_then_removes_persistent():
    h = _handler()
    mgr = _manager()
    svc = VnfsService(h, mgr)
    with patch("skillberry_store.services.registry.get_service", return_value=MagicMock()):
        svc.delete("v1")
    mgr.remove_server.assert_called_once()
    h.delete_object.assert_called_once()
