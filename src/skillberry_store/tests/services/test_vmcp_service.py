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
    # After Phase 3 (vmcp/vnfs) the wrapper was dropped for parity with the
    # other list endpoints — the service now returns a bare list of enriched
    # server dicts, and the current-page enrichment adds ``running``.
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


# ── Phase 3 (vmcp/vnfs) — pagination / facets / enrichment ──────────────


def _multi_handler(items):
    h = _handler()
    h.list_all_dicts.return_value = items
    return h


def test_list_all_pagination_envelope():
    items = [
        {"uuid": f"u{i}", "name": f"vm{i}", "port": 8000 + i, "modified_at": f"2024-01-{i:02d}"}
        for i in range(1, 6)
    ]
    svc = VmcpService(_multi_handler(items), _manager())
    result = svc.list_all(limit=2, offset=0)
    assert isinstance(result, dict)
    assert result["total"] == 5
    assert result["offset"] == 0
    assert result["limit"] == 2
    assert len(result["items"]) == 2


def test_list_all_enrichment_only_runs_on_the_page():
    """Runtime enrichment must not fan out over discarded pages."""
    items = [
        {"uuid": f"u{i}", "name": f"vm{i}", "port": 8000 + i, "modified_at": f"2024-01-{i:02d}"}
        for i in range(1, 6)
    ]
    mgr = _manager()
    svc = VmcpService(_multi_handler(items), mgr)
    svc.list_all(limit=2, offset=0)
    assert mgr.get_server.call_count == 2


def test_list_all_fields_list_preset_projects_and_still_enriches():
    items = [
        {
            "uuid": "u1",
            "name": "vm1",
            "port": 8100,
            "modified_at": "2024-02-01",
            "extra_disk_field": {"heavy": "x"},
        },
    ]
    svc = VmcpService(_multi_handler(items), _manager())
    result = svc.list_all(fields="narrow")
    assert result[0]["name"] == "vm1"
    assert result[0]["running"] is True  # enrichment survives projection
    assert "extra_disk_field" not in result[0]  # not in the preset


def test_list_all_search_filter():
    items = [
        {"uuid": "u1", "name": "alpha", "description": "d", "modified_at": "2024-03"},
        {"uuid": "u2", "name": "beta", "description": "matchable", "modified_at": "2024-02"},
    ]
    svc = VmcpService(_multi_handler(items), _manager())
    result = svc.list_all(search="MATCH")
    assert [i["name"] for i in result] == ["beta"]


def test_list_all_does_not_mutate_cache_entries():
    """Enrichment must be on fresh copies — cache entries stay clean."""
    original = {"uuid": "u1", "name": "vm1", "port": 8100, "modified_at": "2024-02-01"}
    svc = VmcpService(_multi_handler([original]), _manager())
    svc.list_all()
    assert "running" not in original
    assert "runtime" not in original


def test_facets_returns_tags_namespaces_states():
    items = [
        {"uuid": "u1", "tags": ["prod", "namespace:team-a"], "state": "approved"},
        {"uuid": "u2", "tags": ["dev"], "state": "new"},
    ]
    svc = VmcpService(_multi_handler(items), _manager())
    facets = svc.facets()
    assert set(facets["tags"]) >= {"prod", "dev"}
    assert facets["namespaces"] == ["team-a"]
    assert set(facets["states"]) == {"approved", "new"}
