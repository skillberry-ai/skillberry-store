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


def test_list_all_fields_none_returns_narrow_enriched_shape():
    """Default (no ``fields``) is ``narrow``. For vMCP, narrow includes
    ``_enhance`` so enhancement still runs and ``running`` / ``runtime``
    are merged in."""
    svc = VmcpService(_handler(), _manager())
    result = svc.list_all()
    assert result[0]["running"] is True
    assert result[0]["runtime"] is not None
    assert "port" in result[0]


def test_list_all_fields_narrow_preset_runs_enhance():
    """``narrow`` includes ``_enhance``, so the enhancement mechanism
    runs and ``running`` / ``runtime`` are merged in."""
    svc = VmcpService(_handler(), _manager())
    result = svc.list_all(fields="narrow")
    assert result[0]["running"] is True
    assert "runtime" in result[0]
    assert result[0]["name"] == "vm1"


def test_list_all_fields_wide_preset_skips_enhance():
    """``wide`` is manifest data only — enhancement does NOT run, so
    ``running`` and ``runtime`` are absent."""
    svc = VmcpService(_handler(), _manager())
    result = svc.list_all(fields="wide")
    assert "running" not in result[0]
    assert "runtime" not in result[0]
    assert result[0]["name"] == "vm1"
    assert result[0]["port"] is not None or "port" in result[0]


def test_list_all_fields_csv_allowlist_narrows_output():
    """A CSV allowlist without ``_enhance`` does not activate enhancement."""
    svc = VmcpService(_handler(), _manager())
    result = svc.list_all(fields="uuid,name")
    assert result == [{"uuid": "eeee-5555", "name": "vm1"}]


def test_list_all_fields_csv_with_enhance_flag_runs_enhance():
    """Explicit CSV allowlist naming ``_enhance`` runs the mechanism."""
    svc = VmcpService(_handler(), _manager())
    result = svc.list_all(fields="uuid,name,running,_enhance")
    assert result[0]["running"] is True
    assert result[0]["uuid"] == "eeee-5555"


def test_list_all_fields_full_returns_all_fields():
    svc = VmcpService(_handler(), _manager())
    result = svc.list_all(fields="full")
    assert "running" in result[0]
    assert "runtime" in result[0]


def test_list_all_running_only_csv_needs_enhance_flag_to_populate():
    """A CSV allowlist naming ``running`` alone won't populate the
    field — enhancement is gated on ``_enhance``, not on ``running``."""
    svc = VmcpService(_handler(), _manager())
    result = svc.list_all(fields="running")
    # Enhancement did not run → 'running' was never set, so the
    # projection drops it.
    assert result == [{}]


def _search_handler_vmcp(cached_vmcp):
    """Build a handler mock wired for ``VmcpService.search``."""
    h = _handler()
    h.read_dict.return_value = cached_vmcp
    h.descriptions = MagicMock()
    h.descriptions.search_description.return_value = [
        {"filename": cached_vmcp["uuid"], "similarity_score": 0.4}
    ]
    return h


def test_search_default_returns_narrow_enhanced_object_with_score():
    """Default ``fields=None`` resolves to ``narrow``. For vMCP,
    narrow tags ``_enhance``, so enhancement runs and the response
    carries ``running`` / ``runtime`` alongside ``similarity_score``."""
    cached = {
        "uuid": "vm1",
        "name": "vm1",
        "state": "approved",
        "modified_at": "2024-02-01",
    }
    svc = VmcpService(_search_handler_vmcp(cached), _manager())
    result = svc.search("q")
    assert len(result) == 1
    r = result[0]
    assert r["name"] == "vm1"
    assert r["running"] is True
    assert "runtime" in r
    assert r["similarity_score"] == 0.4


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
