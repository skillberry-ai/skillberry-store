# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""
Unit tests for the /admin/list-subdirectories endpoint.

This endpoint is used by the frontend batch import feature to detect
skill directories in a local folder.
"""

import os
import tempfile
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from skillberry_store.fast_api.server import create_app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def temp_skill_dir():
    """Create a temporary directory with test skill subdirectories."""
    temp_dir = tempfile.mkdtemp(prefix="test_batch_import_")
    
    # Create skill directories with SKILL.md
    skill1_dir = Path(temp_dir) / "calculator"
    skill1_dir.mkdir()
    (skill1_dir / "SKILL.md").write_text(
        "---\nname: calculator\ndescription: Calculator skill\n---\n# Calculator"
    )
    (skill1_dir / "add.py").write_text("def add(a, b):\n    return a + b")
    
    skill2_dir = Path(temp_dir) / "text_processor"
    skill2_dir.mkdir()
    (skill2_dir / "SKILL.md").write_text(
        "---\nname: text_processor\ndescription: Text processor\n---\n# Text"
    )
    
    # Create a directory without SKILL.md
    empty_dir = Path(temp_dir) / "empty_folder"
    empty_dir.mkdir()
    
    # Create a directory with lowercase skill.md
    skill3_dir = Path(temp_dir) / "lowercase_skill"
    skill3_dir.mkdir()
    (skill3_dir / "skill.md").write_text(
        "---\nname: lowercase\ndescription: Lowercase skill\n---\n# Lowercase"
    )
    
    # Create a file (not a directory)
    (Path(temp_dir) / "readme.txt").write_text("This is a file")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_list_subdirectories_success(client, temp_skill_dir):
    """Test successful listing of subdirectories with SKILL.md detection."""
    response = client.post(
        "/api/admin/list-subdirectories",
        json={"path": temp_skill_dir}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "subdirectories" in data
    subdirs = data["subdirectories"]
    
    # Should have 4 directories (3 with skills, 1 empty)
    assert len(subdirs) == 4
    
    # Check that skill directories are correctly identified
    skill_names = {d["name"]: d["has_skill_md"] for d in subdirs}
    
    assert skill_names["calculator"] is True
    assert skill_names["text_processor"] is True
    assert skill_names["lowercase_skill"] is True  # lowercase skill.md should be detected
    assert skill_names["empty_folder"] is False
    
    # Verify paths are absolute
    for subdir in subdirs:
        assert os.path.isabs(subdir["path"])
        assert subdir["path"].startswith(temp_skill_dir)


def test_list_subdirectories_nonexistent_path(client):
    """Test error handling for non-existent path."""
    response = client.post(
        "/api/admin/list-subdirectories",
        json={"path": "/nonexistent/path/that/does/not/exist"}
    )
    
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"].lower()


def test_list_subdirectories_file_not_directory(client, temp_skill_dir):
    """Test error handling when path is a file, not a directory."""
    file_path = os.path.join(temp_skill_dir, "readme.txt")
    
    response = client.post(
        "/api/admin/list-subdirectories",
        json={"path": file_path}
    )
    
    assert response.status_code == 400
    assert "not a directory" in response.json()["detail"].lower()


def test_list_subdirectories_missing_path_parameter(client):
    """Test error handling for missing path parameter."""
    response = client.post(
        "/api/admin/list-subdirectories",
        json={}
    )
    
    assert response.status_code == 400
    assert "invalid request" in response.json()["detail"].lower()


def test_list_subdirectories_invalid_json(client):
    """Test error handling for invalid JSON payload."""
    response = client.post(
        "/api/admin/list-subdirectories",
        data="not valid json",
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 422  # Unprocessable Entity


def test_list_subdirectories_empty_directory(client):
    """Test listing subdirectories in an empty directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        response = client.post(
            "/api/admin/list-subdirectories",
            json={"path": temp_dir}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["subdirectories"] == []


def test_list_subdirectories_case_insensitive_skill_md(client):
    """Test that both SKILL.md and skill.md are detected."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create directory with uppercase SKILL.md
        upper_dir = Path(temp_dir) / "upper"
        upper_dir.mkdir()
        (upper_dir / "SKILL.md").write_text("# Upper")
        
        # Create directory with lowercase skill.md
        lower_dir = Path(temp_dir) / "lower"
        lower_dir.mkdir()
        (lower_dir / "skill.md").write_text("# Lower")
        
        response = client.post(
            "/api/admin/list-subdirectories",
            json={"path": temp_dir}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        skill_names = {d["name"]: d["has_skill_md"] for d in data["subdirectories"]}
        assert skill_names["upper"] is True
        assert skill_names["lower"] is True


def test_list_subdirectories_nested_structure(client):
    """Test that only immediate subdirectories are listed, not nested ones."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create nested structure
        parent_dir = Path(temp_dir) / "parent"
        parent_dir.mkdir()
        (parent_dir / "SKILL.md").write_text("# Parent")
        
        # Create nested child (should not be listed)
        child_dir = parent_dir / "child"
        child_dir.mkdir()
        (child_dir / "SKILL.md").write_text("# Child")
        
        response = client.post(
            "/api/admin/list-subdirectories",
            json={"path": temp_dir}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only list "parent", not "child"
        assert len(data["subdirectories"]) == 1
        assert data["subdirectories"][0]["name"] == "parent"


def test_list_subdirectories_special_characters_in_path(client):
    """Test handling of special characters in directory names."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create directory with special characters
        special_dir = Path(temp_dir) / "skill-with-dashes_and_underscores"
        special_dir.mkdir()
        (special_dir / "SKILL.md").write_text("# Special")
        
        response = client.post(
            "/api/admin/list-subdirectories",
            json={"path": temp_dir}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["subdirectories"]) == 1
        assert data["subdirectories"][0]["name"] == "skill-with-dashes_and_underscores"
        assert data["subdirectories"][0]["has_skill_md"] is True


def test_list_subdirectories_permission_error(client, monkeypatch):
    """Test error handling for permission errors."""
    def mock_listdir(path):
        raise PermissionError("Permission denied")
    
    monkeypatch.setattr(os, "listdir", mock_listdir)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        response = client.post(
            "/api/admin/list-subdirectories",
            json={"path": temp_dir}
        )
        
        assert response.status_code == 500
        assert "error listing subdirectories" in response.json()["detail"].lower()
