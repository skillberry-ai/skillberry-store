"""Integration tests for the delete-protection mechanism.

These tests verify that:
1. Service-layer ``delete()`` raises ``ObjectInUseError`` when dependents exist.
2. API-layer delete endpoints translate ``ObjectInUseError`` to HTTP 409.

The pattern mirrors ``test_cascade_delete.py``: a real service instance is backed
by a ``MagicMock`` handler, with a real ``DependencyManager`` attached so that
guard logic executes without touching the filesystem.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from skillberry_store.modules.dependency_manager import DependencyManager
from skillberry_store.services.exceptions import ObjectInUseError
from skillberry_store.services.tools_service import ToolsService
from skillberry_store.services.snippets_service import SnippetsService
from skillberry_store.services.skills_service import SkillsService

from skillberry_store.fast_api.tools_api import register_tools_api
from skillberry_store.fast_api.snippets_api import register_snippets_api
from skillberry_store.fast_api.skills_api import register_skills_api


# ─── helpers ─────────────────────────────────────────────────────────────────

def _make_handler(uuid: str, name: str, extra: dict | None = None) -> MagicMock:
    """Create a handler mock with a real DependencyManager embedded."""
    h = MagicMock()
    h.dependency_manager = DependencyManager()
    h.resolve_to_uuid_or_error.return_value = uuid
    obj = {"uuid": uuid, "name": name, "parent": None, **(extra or {})}
    h.read_dict.return_value = obj
    h.list_all_dicts.return_value = [obj]
    return h


@contextmanager
def _patched_registry(**service_map):
    """Patch ``get_service`` to return mock services by type name."""
    def _fake(service_type: str):
        return service_map[service_type]

    with patch(
        "skillberry_store.services.registry.get_service",
        side_effect=_fake,
    ):
        yield


# ─── ToolsService ─────────────────────────────────────────────────────────────

class TestToolsServiceDeleteProtection:
    def test_delete_succeeds_when_no_dependents(self):
        h = _make_handler("t-1", "my_tool")
        svc = ToolsService(h)
        result = svc.delete("t-1")
        assert result["uuid"] == "t-1"

    def test_delete_raises_when_skill_depends_on_tool(self):
        h = _make_handler("t-1", "my_tool")
        h.dependency_manager.add("skill", "sk-1", ["t-1"])
        svc = ToolsService(h)
        with pytest.raises(ObjectInUseError) as exc_info:
            svc.delete("t-1")
        msg = str(exc_info.value)
        assert "tool" in msg
        assert "t-1" in msg
        assert "sk-1" in msg

    def test_delete_raises_when_tool_depends_on_tool(self):
        h = _make_handler("t-base", "base_tool")
        h.dependency_manager.add("tool", "t-child", ["t-base"])
        svc = ToolsService(h)
        with pytest.raises(ObjectInUseError):
            svc.delete("t-base")

    def test_delete_allowed_after_dependent_removed(self):
        h = _make_handler("t-1", "my_tool")
        h.dependency_manager.add("skill", "sk-1", ["t-1"])
        h.dependency_manager.remove_referencing("skill", "sk-1")
        svc = ToolsService(h)
        result = svc.delete("t-1")  # must not raise
        assert result["uuid"] == "t-1"


class TestToolsApiDeleteProtection:
    def _client(self, tool_uuid: str, tool_name: str):
        app = FastAPI()
        h = _make_handler(tool_uuid, tool_name)
        svc = ToolsService(h)
        register_tools_api(app, service=svc)
        return TestClient(app), h

    def test_api_returns_409_when_tool_in_use(self):
        client, h = self._client("t-1", "my_tool")
        h.dependency_manager.add("skill", "sk-1", ["t-1"])
        resp = client.delete("/tools/t-1")
        assert resp.status_code == 409
        assert "sk-1" in resp.json()["detail"]

    def test_api_returns_200_when_tool_free(self):
        client, h = self._client("t-1", "my_tool")
        resp = client.delete("/tools/t-1")
        assert resp.status_code == 200


# ─── SnippetsService ──────────────────────────────────────────────────────────

class TestSnippetsServiceDeleteProtection:
    def test_delete_succeeds_when_no_dependents(self):
        h = _make_handler("sn-1", "my_snippet")
        svc = SnippetsService(h)
        result = svc.delete("sn-1")
        assert result["uuid"] == "sn-1"

    def test_delete_raises_when_skill_depends_on_snippet(self):
        h = _make_handler("sn-1", "my_snippet")
        h.dependency_manager.add("skill", "sk-1", ["sn-1"])
        svc = SnippetsService(h)
        with pytest.raises(ObjectInUseError) as exc_info:
            svc.delete("sn-1")
        msg = str(exc_info.value)
        assert "snippet" in msg
        assert "sn-1" in msg
        assert "sk-1" in msg


class TestSnippetsApiDeleteProtection:
    def _client(self, snip_uuid: str, snip_name: str):
        app = FastAPI()
        h = _make_handler(snip_uuid, snip_name)
        svc = SnippetsService(h)
        register_snippets_api(app, service=svc)
        return TestClient(app), h

    def test_api_returns_409_when_snippet_in_use(self):
        client, h = self._client("sn-1", "my_snippet")
        h.dependency_manager.add("skill", "sk-1", ["sn-1"])
        resp = client.delete("/snippets/sn-1")
        assert resp.status_code == 409
        assert "sk-1" in resp.json()["detail"]

    def test_api_returns_200_when_snippet_free(self):
        client, h = self._client("sn-1", "my_snippet")
        resp = client.delete("/snippets/sn-1")
        assert resp.status_code == 200


# ─── SkillsService ────────────────────────────────────────────────────────────

class TestSkillsServiceDeleteProtection:
    def _svc(self, skill_uuid: str, extra: dict | None = None):
        base = {"tool_uuids": [], "snippet_uuids": []}
        base.update(extra or {})
        h = _make_handler(skill_uuid, "my_skill", base)
        return SkillsService(h, descriptions=None), h

    def test_delete_succeeds_when_no_dependents(self):
        svc, _ = self._svc("sk-1")
        with _patched_registry(tool=MagicMock(), snippet=MagicMock()):
            result = svc.delete("sk-1")
        assert result["uuid"] == "sk-1"

    def test_delete_raises_when_vmcp_depends_on_skill(self):
        svc, h = self._svc("sk-1")
        h.dependency_manager.add("vmcp", "v-1", ["sk-1"])
        with _patched_registry(tool=MagicMock(), snippet=MagicMock()):
            with pytest.raises(ObjectInUseError) as exc_info:
                svc.delete("sk-1")
        msg = str(exc_info.value)
        assert "skill" in msg
        assert "sk-1" in msg
        assert "v-1" in msg

    def test_delete_raises_when_vnfs_depends_on_skill(self):
        svc, h = self._svc("sk-1")
        h.dependency_manager.add("vnfs", "nfs-1", ["sk-1"])
        with _patched_registry(tool=MagicMock(), snippet=MagicMock()):
            with pytest.raises(ObjectInUseError):
                svc.delete("sk-1")


class TestSkillsApiDeleteProtection:
    def _client(self, skill_uuid: str):
        app = FastAPI()
        h = _make_handler(skill_uuid, "my_skill", {"tool_uuids": [], "snippet_uuids": []})
        svc = SkillsService(h, descriptions=None)
        register_skills_api(app, service=svc)
        return TestClient(app), h

    def test_api_returns_409_when_skill_in_use(self):
        client, h = self._client("sk-1")
        h.dependency_manager.add("vmcp", "v-1", ["sk-1"])
        with _patched_registry(tool=MagicMock(), snippet=MagicMock()):
            resp = client.delete("/skills/sk-1")
        assert resp.status_code == 409
        assert "v-1" in resp.json()["detail"]

    def test_api_returns_200_when_skill_free(self):
        client, h = self._client("sk-1")
        with _patched_registry(tool=MagicMock(), snippet=MagicMock()):
            resp = client.delete("/skills/sk-1")
        assert resp.status_code == 200


# ─── Error message format ─────────────────────────────────────────────────────

class TestObjectInUseErrorMessage:
    def test_message_lists_all_dependents(self):
        err = ObjectInUseError("tool", "t-1", [("skill", "sk-1"), ("skill", "sk-2")])
        msg = str(err)
        assert "tool" in msg
        assert "t-1" in msg
        assert "sk-1" in msg
        assert "sk-2" in msg

    def test_message_format_single_dependent(self):
        err = ObjectInUseError("snippet", "sn-1", [("skill", "sk-A")])
        msg = str(err)
        assert "cannot be deleted" in msg
        assert "depend" in msg
