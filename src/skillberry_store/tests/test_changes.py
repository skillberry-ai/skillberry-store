"""Unit tests for the global mutation counter."""

import importlib
import pytest
from unittest.mock import patch, MagicMock
import skillberry_store.fast_api.changes as changes_module


def _reset():
    """Reset the counter between tests."""
    changes_module._count = 0


def test_get_returns_zero_initially():
    _reset()
    assert changes_module.get() == 0


def test_bump_increments_count():
    _reset()
    changes_module.bump()
    assert changes_module.get() == 1


def test_bump_multiple_times():
    _reset()
    for _ in range(5):
        changes_module.bump()
    assert changes_module.get() == 5


def test_get_does_not_change_count():
    _reset()
    changes_module.bump()
    changes_module.get()
    changes_module.get()
    assert changes_module.get() == 1


def test_write_dict_calls_bump_on_success():
    """write_dict must call bump() after a successful write."""
    from skillberry_store.modules.object_handler import ObjectHandler

    handler = ObjectHandler.__new__(ObjectHandler)
    handler.object_type = "skill"
    handler.dict_filename = "skill.json"
    handler.dict_cache = None

    mock_file_handler = MagicMock()
    mock_file_handler.write_file_content.return_value = {"status": "ok"}
    handler.file_handler = mock_file_handler

    with patch("skillberry_store.modules.object_handler.bump") as mock_bump:
        handler.write_dict("aaaaaaaa-0000-0000-0000-000000000000", {"name": "x"})
        mock_bump.assert_called_once()


def test_write_dict_does_not_call_bump_on_failure():
    """write_dict must NOT call bump() when the write raises an exception."""
    from skillberry_store.modules.object_handler import ObjectHandler
    from fastapi import HTTPException

    handler = ObjectHandler.__new__(ObjectHandler)
    handler.object_type = "skill"
    handler.dict_filename = "skill.json"
    handler.dict_cache = None

    mock_file_handler = MagicMock()
    mock_file_handler.write_file_content.side_effect = RuntimeError("disk full")
    handler.file_handler = mock_file_handler

    with patch("skillberry_store.modules.object_handler.bump") as mock_bump:
        with pytest.raises(HTTPException):
            handler.write_dict("aaaaaaaa-0000-0000-0000-000000000000", {"name": "x"})
        mock_bump.assert_not_called()


def test_delete_object_calls_bump_on_success():
    """delete_object must call bump() after a successful delete."""
    from skillberry_store.modules.object_handler import ObjectHandler

    handler = ObjectHandler.__new__(ObjectHandler)
    handler.object_type = "skill"
    handler.dict_cache = None

    mock_file_handler = MagicMock()
    mock_file_handler.delete_subdirectory.return_value = {"status": "ok"}
    handler.file_handler = mock_file_handler

    with patch("skillberry_store.modules.object_handler.bump") as mock_bump:
        handler.delete_object("aaaaaaaa-0000-0000-0000-000000000000")
        mock_bump.assert_called_once()


def test_delete_object_does_not_call_bump_on_failure():
    """delete_object must NOT call bump() when deletion raises an exception."""
    from skillberry_store.modules.object_handler import ObjectHandler
    from fastapi import HTTPException

    handler = ObjectHandler.__new__(ObjectHandler)
    handler.object_type = "skill"
    handler.dict_cache = None

    mock_file_handler = MagicMock()
    mock_file_handler.delete_subdirectory.side_effect = RuntimeError("not found")
    handler.file_handler = mock_file_handler

    with patch("skillberry_store.modules.object_handler.bump") as mock_bump:
        with pytest.raises(HTTPException):
            handler.delete_object("aaaaaaaa-0000-0000-0000-000000000000")
        mock_bump.assert_not_called()


def test_changes_endpoint_returns_count():
    """GET /changes returns {"count": N} matching the current counter value."""
    import skillberry_store.fast_api.changes as changes_module
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    changes_module._count = 0
    app = FastAPI()

    @app.get("/changes")
    def _changes():
        return {"count": changes_module.get()}

    client = TestClient(app)

    response = client.get("/changes")
    assert response.status_code == 200
    assert response.json() == {"count": 0}

    changes_module.bump()
    changes_module.bump()

    response = client.get("/changes")
    assert response.json() == {"count": 2}
