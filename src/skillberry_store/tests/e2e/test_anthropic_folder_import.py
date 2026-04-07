# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""E2E tests for Anthropic skill import from local folder."""

import pytest
import os
import httpx


BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_import_anthropic_skill_from_folder(run_sbs):
    """Test importing an Anthropic skill from a local folder."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Use the test resources folder
        folder_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'resources',
            'anthropic',
            'sample_skill'
        )
        folder_path = os.path.abspath(folder_path)
        
        # Verify folder exists
        assert os.path.exists(folder_path), f"Test folder does not exist: {folder_path}"
        
        # Import from folder
        response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            data={
                "source_type": "folder",
                "folder_path": folder_path,
                "snippet_mode": "file",
            },
        )
        
        assert response.status_code == 200, f"Import failed: {response.text}"
        
        result = response.json()
        assert result["success"] is True
        assert "skill_name" in result
        assert result["tools_created"] > 0
        assert result["snippets_created"] > 0
        
        skill_name = result["skill_name"]
        
        # Verify the skill was created
        response = await client.get(f"{BASE_URL}/skills/{skill_name}")
        assert response.status_code == 200
        
        skill = response.json()
        assert skill["name"] == skill_name
        assert "anthropic" in skill["tags"]
        assert "imported" in skill["tags"]
        
        # Clean up - delete the skill
        await client.delete(f"{BASE_URL}/skills/{skill_name}")


@pytest.mark.asyncio
async def test_import_from_nonexistent_folder(run_sbs):
    """Test importing from a folder that doesn't exist."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            data={
                "source_type": "folder",
                "folder_path": "/nonexistent/folder/path",
                "snippet_mode": "file",
            },
        )
        
        assert response.status_code == 500
        assert "does not exist" in response.text.lower()


@pytest.mark.asyncio
async def test_import_folder_missing_path(run_sbs):
    """Test importing with folder source type but no folder_path."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            data={
                "source_type": "folder",
                "snippet_mode": "file",
            },
        )
        
        assert response.status_code == 400
        assert "folder_path is required" in response.text


@pytest.mark.asyncio
async def test_import_folder_paragraph_mode(run_sbs):
    """Test importing from folder with paragraph mode."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        folder_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'resources',
            'anthropic',
            'sample_skill'
        )
        folder_path = os.path.abspath(folder_path)
        
        response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            data={
                "source_type": "folder",
                "folder_path": folder_path,
                "snippet_mode": "paragraph",
            },
        )
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is True
        skill_name = result["skill_name"]
        
        # Clean up
        await client.delete(f"{BASE_URL}/skills/{skill_name}")