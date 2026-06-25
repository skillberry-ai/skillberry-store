import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from skillberry_store.services.vmcp_service import VmcpService


def _handler(exists=False):
    h = MagicMock()
    h.object_exists.return_value = exists
    h.get_cache_parent_for_head.return_value = None
    h.resolve_to_uuid_or_error.return_value = "eeee-5555"
    h.read_dict.return_value = {
        "uuid": "eeee-5555", "name": "vm1", "port": 8100,
        "created_at": "2024-01-01T00:00:00+00:00", "parent": None,
        "skill_uuid": None,
    }
    h.list_all_dicts.return_value = [{"uuid": "eeee-5555", "name": "vm1", "port": 8100, "modified_at": "2024-02-01"}]
    return h


def _manager():
    m = MagicMock()
    runtime = MagicMock()
    runtime.port = 8100
    runtime.name = "vm1"
    runtime.description = ""
    runtime.tool_uuids = []
    m.add_server.return_value = runtime
    m.get_server.return_value = runtime
    m.get_server_details.return_value = {"port": 8100}
    return m


def test_create_returns_dict_with_port():
    svc = VmcpService(_handler(), _manager())
    result = svc.create({"name": "vm1", "uuid": None}, env_id="")
    assert "uuid" in result
    assert result["port"] == 8100


def test_create_raises_on_duplicate():
    svc = VmcpService(_handler(exists=True), _manager())
    with pytest.raises(ValueError, match="already exists"):
        svc.create({"name": "vm1", "uuid": None}, env_id="")


def test_list_includes_running_status():
    svc = VmcpService(_handler(), _manager())
    result = svc.list_all()
    assert "virtual_mcp_servers" in result


def test_delete_stops_runtime_and_removes_persistent():
    h = _handler()
    mgr = _manager()
    svc = VmcpService(h, mgr)
    svc.delete("vm1")
    mgr.remove_server.assert_called_once()
    h.delete_object.assert_called_once()
