from unittest.mock import MagicMock

from skillberry_store.access_control.config import AccessControlConfig
from skillberry_store.plugins.store_api import StoreAPI

# Enforcement point 2 is inert in ``disabled`` mode, which is what lets these
# tests exercise StoreAPI's delegation without standing up an ACL config, a
# session or an ambient subject. Admission control itself is covered in
# test_store_api_admit.py.
ACL_DISABLED = AccessControlConfig(mode="disabled")


def _store_with_vmcp():
    vmcp_service = MagicMock()
    vmcp_service.create.return_value = {"uuid": "v1", "port": 10001}
    vmcp_service.get.return_value = {"uuid": "v1", "port": 10001, "running": True}
    # Phase 3 (vmcp/vnfs): ``list_all`` now returns a bare list.
    vmcp_service.list_all.return_value = [{"uuid": "v1"}]
    return StoreAPI({"vmcp": vmcp_service}, ACL_DISABLED), vmcp_service


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
    store = StoreAPI({}, ACL_DISABLED)
    assert store.get_vmcp("x") is None
    assert store.list_vmcps() == []
    assert store.delete_vmcp("x") is False


def test_delete_tool_delegates():
    tools_service = MagicMock()
    store = StoreAPI({"tools": tools_service}, ACL_DISABLED)
    store.delete_tool("t1")
    tools_service.delete.assert_called_once_with("t1")


def test_delete_skill_delegates():
    skills_service = MagicMock()
    store = StoreAPI({"skills": skills_service}, ACL_DISABLED)
    store.delete_skill("s1")
    skills_service.delete.assert_called_once_with("s1")
