"""
E2E tests for skill API endpoints.
Tests the full lifecycle of skill operations: create, list, get, update, and delete.
"""

import asyncio
import os
import pytest
import pytest_asyncio
import httpx

from skillberry_store.tests.utils import clean_test_tmp_dir, wait_until_server_ready

BASE_URL = "http://localhost:8000"


async def create_tool_helper(client, name, description="A test tool"):
    """Helper function to create a tool and return its UUID."""
    import json
    
    tool_data = {
        "name": name,
        "description": description,
        "programming_language": "python",
        "packaging_format": "code"
    }
    
    # Create a simple Python module content
    module_content = f"""
def {name}(param1):
    '''Test tool function'''
    return param1
"""
    
    files = {
        "module": (f"{name}.py", module_content.encode(), "text/x-python")
    }
    
    response = await client.post(
        f"{BASE_URL}/tools/",
        params=tool_data,
        files=files
    )
    
    if response.status_code == 200:
        return response.json().get("uuid")
    else:
        print(f"Tool creation failed: {response.status_code} - {response.text}")
    return None


async def create_snippet_helper(client, name, content="Test content", description="A test snippet"):
    """Helper function to create a snippet and return its UUID."""
    snippet_data = {
        "name": name,
        "description": description,
        "content": content,  # Required field
        "content_type": "text/plain"
    }
    
    files = {
        "file": ("snippet.txt", content.encode(), "text/plain")
    }
    
    response = await client.post(
        f"{BASE_URL}/snippets/",
        params=snippet_data,
        files=files
    )
    
    if response.status_code == 200:
        return response.json().get("uuid")
    return None


@pytest.mark.asyncio
async def test_create_skill(run_sbs):
    """Test creating a new skill."""
    async with httpx.AsyncClient() as client:
        # First create a tool and snippet
        tool_uuid = await create_tool_helper(client, "test_tool", "A test tool")
        assert tool_uuid is not None, "Failed to create test tool"
        
        snippet_uuid = await create_snippet_helper(client, "test_snippet", "Test content", "A test snippet")
        assert snippet_uuid is not None, "Failed to create test snippet"
        
        # Now create the skill with the UUIDs
        skill_data = {
            "name": "test_skill",
            "description": "A test skill for demonstration",
            "tool_uuids": [tool_uuid],
            "snippet_uuids": [snippet_uuid]
        }

        response = await client.post(f"{BASE_URL}/skills/", params=skill_data)
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
        "tool_uuids": [],
        "snippet_uuids": []
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/skills/", params=skill_data)
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
    async with httpx.AsyncClient() as client:
        # First create a skill to update with a unique name
        initial_tool_uuid = await create_tool_helper(client, "initial_update_tool", "Initial tool")
        assert initial_tool_uuid is not None
        
        initial_snippet_uuid = await create_snippet_helper(client, "initial_update_snippet", "Initial content", "Initial snippet")
        assert initial_snippet_uuid is not None
        
        create_data = {
            "name": "skill_for_update_test",
            "description": "A test skill for update",
            "tool_uuids": [initial_tool_uuid],
            "snippet_uuids": [initial_snippet_uuid]
        }
        create_response = await client.post(f"{BASE_URL}/skills/", params=create_data)
        assert create_response.status_code == 200
        
        # Now create new tool and snippet for update
        updated_tool_uuid = await create_tool_helper(client, "updated_tool", "An updated tool")
        assert updated_tool_uuid is not None
        
        updated_snippet_uuid = await create_snippet_helper(client, "updated_snippet", "Updated content", "An updated snippet")
        assert updated_snippet_uuid is not None
        
        updated_data = {
            "name": "skill_for_update_test",
            "description": "Updated test skill description",
            "tool_uuids": [updated_tool_uuid],
            "snippet_uuids": [updated_snippet_uuid]
        }

        response = await client.put(f"{BASE_URL}/skills/skill_for_update_test", json=updated_data)
        assert response.status_code == 200
        data = response.json()
        assert "updated successfully" in data.get("message", "")

        # Verify the update
        get_response = await client.get(f"{BASE_URL}/skills/skill_for_update_test")
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
        "tool_uuids": [],
        "snippet_uuids": []
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
        # Create initial tool and snippet
        initial_tool_uuid = await create_tool_helper(client, "initial_tool", "Initial tool")
        assert initial_tool_uuid is not None
        
        initial_snippet_uuid = await create_snippet_helper(client, "initial_snippet", "Initial content", "Initial snippet")
        assert initial_snippet_uuid is not None
        
        # 1. Create
        create_data = {
            "name": skill_name,
            "description": "Lifecycle test skill",
            "tool_uuids": [initial_tool_uuid],
            "snippet_uuids": [initial_snippet_uuid]
        }
        create_response = await client.post(f"{BASE_URL}/skills/", params=create_data)
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
        updated_tool_uuid = await create_tool_helper(client, "updated_lifecycle_tool", "Updated tool")
        assert updated_tool_uuid is not None
        
        updated_snippet_uuid = await create_snippet_helper(client, "updated_lifecycle_snippet", "Updated content", "Updated snippet")
        assert updated_snippet_uuid is not None
        
        update_data = {
            "name": skill_name,
            "description": "Updated lifecycle test skill",
            "tool_uuids": [updated_tool_uuid],
            "snippet_uuids": [updated_snippet_uuid]
        }
        update_response = await client.put(f"{BASE_URL}/skills/{skill_name}", json=update_data)
        assert update_response.status_code == 200
        assert "updated successfully" in update_response.json().get("message", "")

        # 4. Verify update
        get_updated_response = await client.get(f"{BASE_URL}/skills/{skill_name}")
        assert get_updated_response.status_code == 200
        updated_skill = get_updated_response.json()
        assert updated_skill.get("description") == "Updated lifecycle test skill"
        assert updated_skill.get("tools")[0].get("name") == "updated_lifecycle_tool"
        assert updated_skill.get("snippets")[0].get("name") == "updated_lifecycle_snippet"

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
    
    async with httpx.AsyncClient() as client:
        # Create tools and snippets for test skills
        pandas_tool_uuid = await create_tool_helper(client, "pandas_tool", "Data manipulation tool")
        data_cleaning_snippet_uuid = await create_snippet_helper(client, "data_cleaning", "# Clean data", "Data cleaning snippet")
        
        react_tool_uuid = await create_tool_helper(client, "react_tool", "React framework tool")
        api_endpoint_snippet_uuid = await create_snippet_helper(client, "api_endpoint", "// API code", "API endpoint snippet")
        
        tensorflow_tool_uuid = await create_tool_helper(client, "tensorflow_tool", "TensorFlow ML tool")
        model_training_snippet_uuid = await create_snippet_helper(client, "model_training", "# Train model", "Model training snippet")
        
        # Create test skills with different descriptions
        test_skills = [
            {
                "name": "data_analysis_skill",
                "description": "A comprehensive skill for data analysis including statistical methods and visualization techniques",
                "tool_uuids": [pandas_tool_uuid],
                "snippet_uuids": [data_cleaning_snippet_uuid]
            },
            {
                "name": "web_development_skill",
                "description": "Full-stack web development skill covering frontend frameworks and backend APIs",
                "tool_uuids": [react_tool_uuid],
                "snippet_uuids": [api_endpoint_snippet_uuid]
            },
            {
                "name": "machine_learning_skill",
                "description": "Machine learning and AI skill with deep learning models and neural networks",
                "tool_uuids": [tensorflow_tool_uuid],
                "snippet_uuids": [model_training_snippet_uuid]
            }
        ]
        
        # Create the test skills
        for skill_data in test_skills:
            response = await client.post(f"{BASE_URL}/skills/", params=skill_data)
            assert response.status_code == 200, f"Failed to create skill {skill_data['name']}: {response.text}"
        
        # Wait a moment for indexing
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