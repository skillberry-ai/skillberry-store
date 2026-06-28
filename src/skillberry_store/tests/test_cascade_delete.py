from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from skillberry_store.fast_api.skills_api import register_skills_api
from skillberry_store.services.skills_service import SkillsService


def _make_client(skill, all_skills):
    """Wire a real SkillsService backed by a mocked ObjectHandler.

    Cascade-delete logic now lives in SkillsService.delete; the only thing the
    test layer needs to fake is the persistence handler. Sibling-service
    lookups (``get_service("tool"|"snippet")``) are patched per request via
    ``_patched_registry``.
    """
    app = FastAPI()
    handler = MagicMock()
    handler.dependency_manager.get_dependents.return_value = []
    handler.descriptions = None
    handler.resolve_to_uuid_or_error.return_value = skill["uuid"]
    handler.read_dict.return_value = skill
    handler.list_all_dicts.return_value = all_skills
    svc = SkillsService(handler)
    register_skills_api(app, service=svc)
    return TestClient(app), handler


@contextmanager
def _patched_registry(mock_tools_svc, mock_snippets_svc):
    """Route SkillsService.delete's ``get_service`` lookups to the mocks."""
    def _fake_get_service(service_type: str):
        return {"tool": mock_tools_svc, "snippet": mock_snippets_svc}[service_type]

    with patch(
        "skillberry_store.services.registry.get_service",
        side_effect=_fake_get_service,
    ):
        yield


def test_cascade_delete_exclusive_tool_is_deleted():
    skill = {"uuid": "sk1", "name": "myskill", "tool_uuids": ["t1"], "snippet_uuids": []}
    other = {"uuid": "sk2", "tool_uuids": [], "snippet_uuids": []}
    mock_tools, mock_snippets = MagicMock(), MagicMock()
    client, _ = _make_client(skill, [skill, other])

    with _patched_registry(mock_tools, mock_snippets):
        resp = client.delete("/skills/sk1?delete_tools=true")

    assert resp.status_code == 200
    mock_tools.delete.assert_called_once_with("t1")
    mock_snippets.delete.assert_not_called()


def test_cascade_delete_shared_tool_is_skipped():
    skill = {"uuid": "sk1", "name": "myskill", "tool_uuids": ["t1"], "snippet_uuids": []}
    other = {"uuid": "sk2", "tool_uuids": ["t1"], "snippet_uuids": []}
    mock_tools, mock_snippets = MagicMock(), MagicMock()
    client, _ = _make_client(skill, [skill, other])

    with _patched_registry(mock_tools, mock_snippets):
        resp = client.delete("/skills/sk1?delete_tools=true")

    assert resp.status_code == 200
    mock_tools.delete.assert_not_called()


def test_cascade_delete_exclusive_snippet_is_deleted():
    skill = {"uuid": "sk1", "name": "myskill", "tool_uuids": [], "snippet_uuids": ["sn1"]}
    other = {"uuid": "sk2", "tool_uuids": [], "snippet_uuids": []}
    mock_tools, mock_snippets = MagicMock(), MagicMock()
    client, _ = _make_client(skill, [skill, other])

    with _patched_registry(mock_tools, mock_snippets):
        resp = client.delete("/skills/sk1?delete_snippets=true")

    assert resp.status_code == 200
    mock_snippets.delete.assert_called_once_with("sn1")
    mock_tools.delete.assert_not_called()


def test_no_flags_skips_cascade():
    skill = {"uuid": "sk1", "name": "myskill", "tool_uuids": ["t1"], "snippet_uuids": ["sn1"]}
    mock_tools, mock_snippets = MagicMock(), MagicMock()
    client, _ = _make_client(skill, [skill])

    with _patched_registry(mock_tools, mock_snippets):
        resp = client.delete("/skills/sk1")

    assert resp.status_code == 200
    mock_tools.delete.assert_not_called()
    mock_snippets.delete.assert_not_called()


def test_response_includes_deleted_lists():
    skill = {"uuid": "sk1", "name": "myskill", "tool_uuids": ["t1"], "snippet_uuids": ["sn1"]}
    other = {"uuid": "sk2", "tool_uuids": [], "snippet_uuids": []}
    mock_tools, mock_snippets = MagicMock(), MagicMock()
    client, _ = _make_client(skill, [skill, other])

    with _patched_registry(mock_tools, mock_snippets):
        resp = client.delete("/skills/sk1?delete_tools=true&delete_snippets=true")

    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted_tools"] == ["t1"]
    assert data["deleted_snippets"] == ["sn1"]


def test_cascade_tool_failure_does_not_abort_skill_delete():
    skill = {"uuid": "sk1", "name": "myskill", "tool_uuids": ["t1"], "snippet_uuids": []}
    mock_tools, mock_snippets = MagicMock(), MagicMock()
    mock_tools.delete.side_effect = Exception("storage error")
    client, handler = _make_client(skill, [skill])

    with _patched_registry(mock_tools, mock_snippets):
        resp = client.delete("/skills/sk1?delete_tools=true")

    assert resp.status_code == 200
    handler.delete_object.assert_called_once_with("sk1")  # skill still deleted
