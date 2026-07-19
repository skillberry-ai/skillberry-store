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


# ── field selection (?fields) ──────────────────────────────────────────


def test_list_all_fields_none_returns_narrow_enriched_shape():
    """Default (no ``fields``) is ``narrow``. For vNFS, narrow includes
    ``_enhance`` so enhancement still runs and ``running`` /
    ``export_path`` are merged in."""
    svc = VnfsService(_handler(), _manager())
    result = svc.list_all()
    assert result[0]["running"] is True
    assert result[0]["export_path"] == "/tmp/export"
    assert "port" in result[0]


def test_list_all_fields_narrow_preset_runs_enhance():
    """``narrow`` includes ``_enhance``, so enhancement runs and
    ``running`` / ``export_path`` are merged in."""
    svc = VnfsService(_handler(), _manager())
    result = svc.list_all(fields="narrow")
    assert result[0]["running"] is True
    assert result[0]["export_path"] == "/tmp/export"
    assert result[0]["name"] == "v1"


def test_list_all_fields_wide_preset_skips_enhance():
    """``wide`` is manifest data only — enhancement does NOT run."""
    svc = VnfsService(_handler(), _manager())
    result = svc.list_all(fields="wide")
    assert "running" not in result[0]
    assert "export_path" not in result[0]
    assert result[0]["name"] == "v1"


def test_list_all_fields_csv_allowlist_narrows_output():
    """A CSV allowlist without ``_enhance`` does not activate enhancement."""
    svc = VnfsService(_handler(), _manager())
    result = svc.list_all(fields="uuid,name")
    assert result == [{"uuid": "dddd-4444", "name": "v1"}]


def test_list_all_fields_csv_with_enhance_flag_runs_enhance():
    svc = VnfsService(_handler(), _manager())
    result = svc.list_all(fields="uuid,name,running,_enhance")
    assert result[0]["running"] is True
    assert result[0]["uuid"] == "dddd-4444"


def test_list_all_fields_full_returns_all_fields():
    svc = VnfsService(_handler(), _manager())
    result = svc.list_all(fields="full")
    assert "running" in result[0]
    assert "export_path" in result[0]


def _search_handler_vnfs(cached_vnfs):
    """Build a handler mock wired for ``VnfsService.search``."""
    h = _handler()
    h.read_dict.return_value = cached_vnfs
    h.descriptions = MagicMock()
    h.descriptions.search_description.return_value = [
        {"filename": cached_vnfs["uuid"], "similarity_score": 0.4}
    ]
    return h


def test_search_default_returns_narrow_enhanced_object_with_score():
    """Default ``fields=None`` resolves to ``narrow``. For vNFS,
    narrow tags ``_enhance``, so enhancement runs and the response
    carries ``running`` / ``export_path`` alongside
    ``similarity_score``."""
    cached = {
        "uuid": "v1",
        "name": "v1",
        "state": "approved",
        "modified_at": "2024-02-01",
    }
    svc = VnfsService(_search_handler_vnfs(cached), _manager())
    result = svc.search("q")
    assert len(result) == 1
    r = result[0]
    assert r["name"] == "v1"
    assert r["running"] is True
    assert r["export_path"] == "/tmp/export"
    assert r["similarity_score"] == 0.4


def test_search_does_not_mutate_cache_entry():
    cached = {
        "uuid": "v1",
        "name": "v1",
        "state": "approved",
        "modified_at": "2024-02-01",
    }
    svc = VnfsService(_search_handler_vnfs(cached), _manager())
    svc.search("q")
    assert "similarity_score" not in cached


def test_search_with_fields_full_returns_dict_plus_score():
    cached = {
        "uuid": "v1",
        "name": "v1",
        "state": "approved",
        "port": 9000,
        "modified_at": "2024-02-01",
    }
    svc = VnfsService(_search_handler_vnfs(cached), _manager())
    result = svc.search("q", fields="full")
    r = result[0]
    assert r["uuid"] == "v1"
    assert r["port"] == 9000
    assert r["similarity_score"] == 0.4


def test_search_with_fields_csv_narrows_output_and_keeps_score():
    cached = {
        "uuid": "v1",
        "name": "v1",
        "state": "approved",
        "port": 9000,
        "description": "hidden",
        "modified_at": "2024-02-01",
    }
    svc = VnfsService(_search_handler_vnfs(cached), _manager())
    result = svc.search("q", fields="uuid,name")
    assert result == [
        {"uuid": "v1", "name": "v1", "similarity_score": 0.4}
    ]
