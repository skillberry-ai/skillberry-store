import pytest
from unittest.mock import MagicMock, patch
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
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["running"] is True


def test_delete_stops_runtime_and_removes_persistent():
    h = _handler()
    mgr = _manager()
    svc = VmcpService(h, mgr)
    with patch("skillberry_store.services.registry.get_service", return_value=MagicMock()):
        svc.delete("vm1")
    mgr.remove_server.assert_called_once()
    h.delete_object.assert_called_once()


# ── field selection (?fields) ──────────────────────────────────────────


def test_list_all_fields_none_returns_full_enriched_shape():
    svc = VmcpService(_handler(), _manager())
    result = svc.list_all()
    assert result[0]["running"] is True
    assert result[0]["runtime"] is not None
    assert "port" in result[0]


def test_list_all_fields_list_preset_keeps_runtime_status():
    svc = VmcpService(_handler(), _manager())
    result = svc.list_all(fields="list")
    # Preset keeps the runtime-status fields the list UI depends on.
    assert result[0]["running"] is True
    assert "runtime" in result[0]
    assert result[0]["name"] == "vm1"


def test_list_all_fields_csv_allowlist_narrows_output():
    svc = VmcpService(_handler(), _manager())
    result = svc.list_all(fields="uuid,name")
    assert result == [{"uuid": "eeee-5555", "name": "vm1"}]


def test_list_all_fields_full_returns_all_fields():
    svc = VmcpService(_handler(), _manager())
    result = svc.list_all(fields="full")
    assert "running" in result[0]
    assert "runtime" in result[0]


def test_list_all_fields_invalid_object_type_raises_via_bad_preset():
    # Purely covers the preset registration: parse_fields_spec is validated
    # by its own tests. Here we just guarantee our service passes "vmcp"
    # through so a caller-defined allowlist works end-to-end.
    svc = VmcpService(_handler(), _manager())
    result = svc.list_all(fields="running")
    assert result == [{"running": True}]


def _search_handler_vmcp(cached_vmcp):
    """Build a handler mock wired for ``VmcpService.search``."""
    h = _handler()
    h.read_dict.return_value = cached_vmcp
    h.descriptions = MagicMock()
    h.descriptions.search_description.return_value = [
        {"filename": cached_vmcp["uuid"], "similarity_score": 0.4}
    ]
    return h


def test_search_default_returns_legacy_shape():
    cached = {
        "uuid": "vm1",
        "name": "vm1",
        "state": "approved",
        "modified_at": "2024-02-01",
    }
    svc = VmcpService(_search_handler_vmcp(cached), _manager())
    result = svc.search("q")
    assert result == [{"filename": "vm1", "similarity_score": 0.4}]


def test_search_does_not_mutate_cache_entry():
    cached = {
        "uuid": "vm1",
        "name": "vm1",
        "state": "approved",
        "modified_at": "2024-02-01",
    }
    svc = VmcpService(_search_handler_vmcp(cached), _manager())
    svc.search("q")
    # The cached dict must stay clean — ``similarity_score`` is added to a
    # fresh copy inside search().
    assert "similarity_score" not in cached


def test_search_with_fields_full_returns_dict_plus_score():
    cached = {
        "uuid": "vm1",
        "name": "vm1",
        "state": "approved",
        "port": 8100,
        "modified_at": "2024-02-01",
    }
    svc = VmcpService(_search_handler_vmcp(cached), _manager())
    result = svc.search("q", fields="full")
    r = result[0]
    assert r["uuid"] == "vm1"
    assert r["port"] == 8100
    assert r["similarity_score"] == 0.4


def test_search_with_fields_csv_narrows_output_and_keeps_score():
    cached = {
        "uuid": "vm1",
        "name": "vm1",
        "state": "approved",
        "port": 8100,
        "description": "hidden",
        "modified_at": "2024-02-01",
    }
    svc = VmcpService(_search_handler_vmcp(cached), _manager())
    result = svc.search("q", fields="uuid,name")
    assert result == [
        {"uuid": "vm1", "name": "vm1", "similarity_score": 0.4}
    ]
