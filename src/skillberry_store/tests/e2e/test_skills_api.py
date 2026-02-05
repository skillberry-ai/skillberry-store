"""
E2E tests for skill API endpoints.
Tests the full lifecycle of skill operations: create, list, get, update, and delete.
"""

import asyncio
import os
import pytest
import pytest_asyncio
import httpx

from skillberry_store.tests.e2e.fixtures import run_sbs
from skillberry_store.tests.utils import clean_test_tmp_dir, wait_until_server_ready

BASE_URL = "http://localhost:8000"



@pytest.mark.asyncio
async def test_create_skill(run_sbs):
    """Test creating a new skill."""
    skill_data = {
        "name": "test_skill",
        "description": "A test skill for demonstration",
        "tools": [
            {
                "name": "test_tool",
                "description": "A test tool",
                "module_name": "test_tool_module",
                "programming_language": "python",
                "packaging_format": "code",
                "params": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string"}
                    },
                    "required": [],
                    "optional": []
                }
            }
        ],
        "snippets": [
            {
                "name": "test_snippet",
                "description": "A test snippet",
                "content": "Test content",
                "content_type": "text/plain"
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/skills/", json=skill_data)
        assert response.status_code == 200
        data = response.json()
        assert data.get("name") == "test_skill"
        assert "created successfully" in data.get("message", "")
        # Verify UUID was generated
        assert "uuid" in data
        assert data.get("uuid") is not None
        assert len(data.get("uuid")) == 36  # UUID4 format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx


@pytest.mark.asyncio
async def test_create_duplicate_skill(run_sbs):
    """Test that creating a duplicate skill fails."""
    skill_data = {
        "name": "test_skill",
        "description": "A test skill for demonstration",
        "tools": [],
        "snippets": []
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/skills/", json=skill_data)
        # Should fail with 409 Conflict
        assert response.status_code == 409
        assert "already exists" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_list_skills(run_sbs):
    """Test listing all skills."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/skills/")
        assert response.status_code == 200
        skills = response.json()
        assert isinstance(skills, list)
        assert len(skills) > 0
        
        # Check that our test skill is in the list
        skill_names = [s.get("name") for s in skills]
        assert "test_skill" in skill_names


@pytest.mark.asyncio
async def test_get_skill(run_sbs):
    """Test getting a specific skill by name."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/skills/test_skill")
        assert response.status_code == 200
        skill = response.json()
        assert skill.get("name") == "test_skill"
        assert skill.get("description") == "A test skill for demonstration"
        assert "tools" in skill
        assert "snippets" in skill
        assert isinstance(skill.get("tools"), list)
        assert isinstance(skill.get("snippets"), list)


@pytest.mark.asyncio
async def test_get_nonexistent_skill(run_sbs):
    """Test that getting a non-existent skill fails."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/skills/nonexistent_skill")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_skill(run_sbs):
    """Test updating an existing skill."""
    updated_data = {
        "name": "test_skill",
        "description": "Updated test skill description",
        "tools": [
            {
                "name": "updated_tool",
                "description": "An updated tool",
                "module_name": "updated_tool_module",
                "programming_language": "python",
                "packaging_format": "code",
                "params": {
                    "type": "object",
                    "properties": {
                        "param2": {"type": "number"}
                    },
                    "required": [],
                    "optional": []
                }
            }
        ],
        "snippets": [
            {
                "name": "updated_snippet",
                "description": "An updated snippet",
                "content": "Updated content",
                "content_type": "text/markdown"
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(f"{BASE_URL}/skills/test_skill", json=updated_data)
        assert response.status_code == 200
        data = response.json()
        assert "updated successfully" in data.get("message", "")

        # Verify the update
        get_response = await client.get(f"{BASE_URL}/skills/test_skill")
        assert get_response.status_code == 200
        skill = get_response.json()
        assert skill.get("description") == "Updated test skill description"
        assert len(skill.get("tools", [])) == 1
        assert skill.get("tools")[0].get("name") == "updated_tool"
        assert len(skill.get("snippets", [])) == 1
        assert skill.get("snippets")[0].get("name") == "updated_snippet"


@pytest.mark.asyncio
async def test_update_nonexistent_skill(run_sbs):
    """Test that updating a non-existent skill fails."""
    updated_data = {
        "name": "nonexistent_skill",
        "description": "This should fail",
        "tools": [],
        "snippets": []
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(f"{BASE_URL}/skills/nonexistent_skill", json=updated_data)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_skill(run_sbs):
    """Test deleting a skill."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/skills/test_skill")
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data.get("message", "")

        # Verify deletion
        get_response = await client.get(f"{BASE_URL}/skills/test_skill")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_skill(run_sbs):
    """Test that deleting a non-existent skill fails."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/skills/nonexistent_skill")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_skill_lifecycle(run_sbs):
    """Test the complete lifecycle of a skill: create, read, update, delete."""
    skill_name = "lifecycle_test_skill"
    
    async with httpx.AsyncClient() as client:
        # 1. Create
        create_data = {
            "name": skill_name,
            "description": "Lifecycle test skill",
            "tools": [
                {
                    "name": "initial_tool",
                    "description": "Initial tool",
                    "module_name": "initial_tool_module",
                    "programming_language": "python",
                    "packaging_format": "code",
                    "params": {
                        "type": "object",
                        "properties": {
                            "input": {"type": "string"}
                        },
                        "required": [],
                        "optional": []
                    }
                }
            ],
            "snippets": [
                {
                    "name": "initial_snippet",
                    "description": "Initial snippet",
                    "content": "Initial content",
                    "content_type": "text/plain"
                }
            ]
        }
        create_response = await client.post(f"{BASE_URL}/skills/", json=create_data)
        assert create_response.status_code == 200
        assert create_response.json().get("name") == skill_name

        # 2. Read
        get_response = await client.get(f"{BASE_URL}/skills/{skill_name}")
        assert get_response.status_code == 200
        skill = get_response.json()
        assert skill.get("name") == skill_name
        assert len(skill.get("tools", [])) == 1
        assert skill.get("tools")[0].get("name") == "initial_tool"

        # 3. Update
        update_data = {
            "name": skill_name,
            "description": "Updated lifecycle test skill",
            "tools": [
                {
                    "name": "updated_tool",
                    "description": "Updated tool",
                    "module_name": "updated_tool_module",
                    "programming_language": "python",
                    "packaging_format": "code",
                    "params": {
                        "type": "object",
                        "properties": {
                            "output": {"type": "number"}
                        },
                        "required": [],
                        "optional": []
                    }
                }
            ],
            "snippets": [
                {
                    "name": "updated_snippet",
                    "description": "Updated snippet",
                    "content": "Updated content",
                    "content_type": "text/markdown"
                }
            ]
        }
        update_response = await client.put(f"{BASE_URL}/skills/{skill_name}", json=update_data)
        assert update_response.status_code == 200
        assert "updated successfully" in update_response.json().get("message", "")

        # 4. Verify update
        get_updated_response = await client.get(f"{BASE_URL}/skills/{skill_name}")
        assert get_updated_response.status_code == 200
        updated_skill = get_updated_response.json()
        assert updated_skill.get("description") == "Updated lifecycle test skill"
        assert updated_skill.get("tools")[0].get("name") == "updated_tool"
        assert updated_skill.get("snippets")[0].get("content") == "Updated content"

        # 5. Delete
        delete_response = await client.delete(f"{BASE_URL}/skills/{skill_name}")
        assert delete_response.status_code == 200
        assert "deleted successfully" in delete_response.json().get("message", "")

        # 6. Verify deletion
        get_deleted_response = await client.get(f"{BASE_URL}/skills/{skill_name}")
        assert get_deleted_response.status_code == 404


@pytest.mark.asyncio
async def test_search_skills(run_sbs):
    """Test searching for skills using the /search/skills endpoint."""
    
    # Create test skills with different descriptions
    test_skills = [
        {
            "name": "data_analysis_skill",
            "description": "A comprehensive skill for data analysis including statistical methods and visualization techniques",
            "tools": [
                {
                    "name": "pandas_tool",
                    "description": "Data manipulation tool",
                    "module_name": "pandas_module",
                    "programming_language": "python",
                    "packaging_format": "code",
                    "params": {"type": "object", "properties": {}, "required": [], "optional": []}
                }
            ],
            "snippets": [
                {
                    "name": "data_cleaning",
                    "description": "Data cleaning snippet",
                    "content": "# Clean data",
                    "content_type": "text/plain"
                }
            ]
        },
        {
            "name": "web_development_skill",
            "description": "Full-stack web development skill covering frontend frameworks and backend APIs",
            "tools": [
                {
                    "name": "react_tool",
                    "description": "React framework tool",
                    "module_name": "react_module",
                    "programming_language": "javascript",
                    "packaging_format": "code",
                    "params": {"type": "object", "properties": {}, "required": [], "optional": []}
                }
            ],
            "snippets": [
                {
                    "name": "api_endpoint",
                    "description": "API endpoint snippet",
                    "content": "// API code",
                    "content_type": "text/plain"
                }
            ]
        },
        {
            "name": "machine_learning_skill",
            "description": "Machine learning and AI skill with deep learning models and neural networks",
            "tools": [
                {
                    "name": "tensorflow_tool",
                    "description": "TensorFlow ML tool",
                    "module_name": "tensorflow_module",
                    "programming_language": "python",
                    "packaging_format": "code",
                    "params": {"type": "object", "properties": {}, "required": [], "optional": []}
                }
            ],
            "snippets": [
                {
                    "name": "model_training",
                    "description": "Model training snippet",
                    "content": "# Train model",
                    "content_type": "text/plain"
                }
            ]
        }
    ]
    
    async with httpx.AsyncClient() as client:
        # Create the test skills
        for skill_data in test_skills:
            response = await client.post(f"{BASE_URL}/skills/", json=skill_data)
            assert response.status_code == 200, f"Failed to create skill {skill_data['name']}: {response.text}"
        
        # Wait a moment for indexing
        import asyncio
        await asyncio.sleep(1)
        
        # Test search for "data analysis"
        search_response = await client.get(
            f"{BASE_URL}/search/skills",
            params={
                "search_term": "data analysis statistical",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200, f"Search failed: {search_response.text}"
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching skill"
        
        # Verify data_analysis_skill is in results
        filenames = [r.get("filename") for r in results]
        assert "data_analysis_skill" in filenames, f"data_analysis_skill should be in search results, got: {filenames}"
        
        # Test search for "web development"
        search_response = await client.get(
            f"{BASE_URL}/search/skills",
            params={
                "search_term": "web development frontend backend",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching skill"
        
        # Test search for "machine learning"
        search_response = await client.get(
            f"{BASE_URL}/search/skills",
            params={
                "search_term": "machine learning neural networks",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching skill"
        
        # Test with strict similarity threshold
        search_response = await client.get(
            f"{BASE_URL}/search/skills",
            params={
                "search_term": "data analysis",
                "max_number_of_results": 5,
                "similarity_threshold": 0.5  # Stricter threshold
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        # Results should be filtered by similarity threshold
        for result in results:
            assert result.get("similarity_score", 1.0) <= 0.5, "All results should meet similarity threshold"
        
        # Clean up - delete test skills
        for skill_data in test_skills:
            delete_response = await client.delete(f"{BASE_URL}/skills/{skill_data['name']}")
            assert delete_response.status_code == 200, f"Failed to delete skill {skill_data['name']}"