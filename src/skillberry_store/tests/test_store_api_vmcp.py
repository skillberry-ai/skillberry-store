from unittest.mock import MagicMock

from skillberry_store.plugins.store_api import StoreAPI


def _store_with_vmcp():
    vmcp_service = MagicMock()
    vmcp_service.create.return_value = {"uuid": "v1", "port": 10001}
    vmcp_service.get.return_value = {"uuid": "v1", "port": 10001, "running": True}
    vmcp_service.list_all.return_value = {"virtual_mcp_servers": {"v1": {"uuid": "v1"}}}
    return StoreAPI({"vmcp": vmcp_service}), vmcp_service


def test_create_vmcp_delegates():
    store, svc = _store_with_vmcp()
    result = store.create_vmcp({"name": "n", "skill_uuid": "s1"}, env_id="e1")
    svc.create.assert_called_once_with({"name": "n", "skill_uuid": "s1"}, env_id="e1")
    assert result["uuid"] == "v1"


def test_get_vmcp_returns_none_on_keyerror():
    store, svc = _store_with_vmcp()
    svc.get.side_effect = KeyError("missing")
    assert store.get_vmcp("nope") is None


def test_list_vmcps_returns_list():
    store, svc = _store_with_vmcp()
    assert store.list_vmcps() == [{"uuid": "v1"}]


def test_start_and_delete_vmcp_delegate():
    store, svc = _store_with_vmcp()
    store.start_vmcp("v1")
    svc.server_manager.add_server.assert_not_called()  # start goes via service helper
    store.delete_vmcp("v1")
    svc.delete.assert_called_once_with("v1")


def test_vmcp_methods_safe_without_service():
    store = StoreAPI({})
    assert store.get_vmcp("x") is None
    assert store.list_vmcps() == []
    assert store.delete_vmcp("x") is False
