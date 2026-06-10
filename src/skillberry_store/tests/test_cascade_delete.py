from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from skillberry_store.fast_api.skills_api import register_skills_api


def _make_client(skill, all_skills, mock_tools_svc, mock_snippets_svc):
    """Register a test app with fully mocked services."""
    app = FastAPI()
    svc = MagicMock()
    svc.get.return_value = skill
    svc.delete.return_value = None
    svc.handler.list_all_dicts.return_value = all_skills
    svc.tools_handler = MagicMock()
    svc.snippets_handler = MagicMock()
    with patch("skillberry_store.fast_api.skills_api.ToolsService", return_value=mock_tools_svc), \
         patch("skillberry_store.fast_api.skills_api.SnippetsService", return_value=mock_snippets_svc):
        register_skills_api(app, service=svc)
    return TestClient(app), svc


def test_cascade_delete_exclusive_tool_is_deleted():
    skill = {"uuid": "sk1", "name": "myskill", "tool_uuids": ["t1"], "snippet_uuids": []}
    other = {"uuid": "sk2", "tool_uuids": [], "snippet_uuids": []}
    mock_tools, mock_snippets = MagicMock(), MagicMock()
    client, _ = _make_client(skill, [skill, other], mock_tools, mock_snippets)

    resp = client.delete("/skills/sk1?delete_tools=true")

    assert resp.status_code == 200
    mock_tools.delete.assert_called_once_with("t1")
    mock_snippets.delete.assert_not_called()


def test_cascade_delete_shared_tool_is_skipped():
    skill = {"uuid": "sk1", "name": "myskill", "tool_uuids": ["t1"], "snippet_uuids": []}
    other = {"uuid": "sk2", "tool_uuids": ["t1"], "snippet_uuids": []}
    mock_tools, mock_snippets = MagicMock(), MagicMock()
    client, _ = _make_client(skill, [skill, other], mock_tools, mock_snippets)

    resp = client.delete("/skills/sk1?delete_tools=true")

    assert resp.status_code == 200
    mock_tools.delete.assert_not_called()


def test_cascade_delete_exclusive_snippet_is_deleted():
    skill = {"uuid": "sk1", "name": "myskill", "tool_uuids": [], "snippet_uuids": ["sn1"]}
    other = {"uuid": "sk2", "tool_uuids": [], "snippet_uuids": []}
    mock_tools, mock_snippets = MagicMock(), MagicMock()
    client, _ = _make_client(skill, [skill, other], mock_tools, mock_snippets)

    resp = client.delete("/skills/sk1?delete_snippets=true")

    assert resp.status_code == 200
    mock_snippets.delete.assert_called_once_with("sn1")
    mock_tools.delete.assert_not_called()


def test_no_flags_skips_cascade():
    skill = {"uuid": "sk1", "name": "myskill", "tool_uuids": ["t1"], "snippet_uuids": ["sn1"]}
    mock_tools, mock_snippets = MagicMock(), MagicMock()
    client, _ = _make_client(skill, [skill], mock_tools, mock_snippets)

    resp = client.delete("/skills/sk1")

    assert resp.status_code == 200
    mock_tools.delete.assert_not_called()
    mock_snippets.delete.assert_not_called()


def test_response_includes_deleted_lists():
    skill = {"uuid": "sk1", "name": "myskill", "tool_uuids": ["t1"], "snippet_uuids": ["sn1"]}
    other = {"uuid": "sk2", "tool_uuids": [], "snippet_uuids": []}
    mock_tools, mock_snippets = MagicMock(), MagicMock()
    client, _ = _make_client(skill, [skill, other], mock_tools, mock_snippets)

    resp = client.delete("/skills/sk1?delete_tools=true&delete_snippets=true")

    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted_tools"] == ["t1"]
    assert data["deleted_snippets"] == ["sn1"]


def test_cascade_tool_failure_does_not_abort_skill_delete():
    skill = {"uuid": "sk1", "name": "myskill", "tool_uuids": ["t1"], "snippet_uuids": []}
    mock_tools, mock_snippets = MagicMock(), MagicMock()
    mock_tools.delete.side_effect = Exception("storage error")
    client, svc = _make_client(skill, [skill], mock_tools, mock_snippets)

    resp = client.delete("/skills/sk1?delete_tools=true")

    assert resp.status_code == 200
    svc.delete.assert_called_once()  # skill still deleted
