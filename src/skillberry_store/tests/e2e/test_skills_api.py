"""
E2E tests for skill API endpoints.
Tests the full lifecycle of skill operations: create, list, get, update, and delete.
"""

import asyncio
import os
import pytest
import httpx

from skillberry_store.tests.utils import clean_test_tmp_dir, wait_until_server_ready

BASE_URL = "http://localhost:8000"


async def create_tool_helper(client, name, description="A test tool"):
    """Helper function to create a tool and return its UUID."""
    
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
    """Test that creating a skill with a duplicate UUID fails."""
    async with httpx.AsyncClient() as client:
        # First get the existing skill to obtain its UUID
        get_response = await client.get(f"{BASE_URL}/skills/test_skill")
        assert get_response.status_code == 200, "test_skill should exist from previous test"
        skill_data = get_response.json()
        existing_uuid = skill_data.get("uuid")
        assert existing_uuid is not None, "Skill UUID should be present"
        
        # Try to create a new skill with the same UUID
        duplicate_skill_data = {
            "name": "different_name_skill",
            "description": "A skill with duplicate UUID",
            "tool_uuids": [],
            "snippet_uuids": [],
            "uuid": existing_uuid  # Using the same UUID
        }
        
        response = await client.post(f"{BASE_URL}/skills/", params=duplicate_skill_data)
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
    """Test deleting a skill by UUID."""
    async with httpx.AsyncClient() as client:
        # First get the skill by name to obtain its UUID
        get_response = await client.get(f"{BASE_URL}/skills/test_skill")
        assert get_response.status_code == 200
        skill_data = get_response.json()
        skill_uuid = skill_data.get("uuid")
        assert skill_uuid is not None, "Skill UUID should be present"
        
        # Delete by UUID
        response = await client.delete(f"{BASE_URL}/skills/{skill_uuid}")
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data.get("message", "")

        # Verify deletion by UUID
        verify_response = await client.get(f"{BASE_URL}/skills/{skill_uuid}")
        assert verify_response.status_code == 404


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


@pytest.mark.asyncio
async def test_import_anthropic_skill_with_complex_dependencies(run_sbs):
    """Test importing an Anthropic skill from ZIP with complex tool dependencies.
    
    This test verifies:
    1. Successful import of a skill from ZIP file
    2. The skill appears in list_skills
    3. Tools have correct UUIDs and dependencies
    4. Tool execution works correctly with dependencies
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get the path to the ZIP file
        zip_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'resources',
            'anthropic',
            'sample_skill_complex_dep.zip'
        )
        zip_path = os.path.abspath(zip_path)
        
        # Verify ZIP file exists
        assert os.path.exists(zip_path), f"Test ZIP file does not exist: {zip_path}"
        
        # Import the skill from ZIP
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        files = {
            'zip_file': ('sample_skill_complex_dep.zip', zip_content, 'application/zip')
        }
        
        response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            data={
                "source_type": "zip",
                "snippet_mode": "file",
            },
            files=files,
        )
        
        # 1. Verify import was successful
        assert response.status_code == 200, f"Import failed: {response.text}"
        
        result = response.json()
        assert result["success"] is True, "Import should be successful"
        assert "skill_name" in result, "Result should contain skill_name"
        assert result["tools_created"] == 5, f"Expected 5 tools created, got {result['tools_created']}"
        
        skill_name = result["skill_name"]
        assert skill_name == "sample_skill_complex_dep", f"Expected skill name 'sample_skill_complex_dep', got '{skill_name}'"
        
        # 2. Verify the skill appears in list_skills
        list_response = await client.get(f"{BASE_URL}/skills/")
        assert list_response.status_code == 200
        skills = list_response.json()
        skill_names = [s.get("name") for s in skills]
        assert skill_name in skill_names, f"Skill '{skill_name}' should be in list_skills"
        
        # 3. Get the skill details - this will populate full tool and snippet objects
        get_response = await client.get(f"{BASE_URL}/skills/{skill_name}")
        assert get_response.status_code == 200
        skill = get_response.json()
        
        assert skill["name"] == skill_name
        assert "anthropic" in skill["tags"]
        assert "imported" in skill["tags"]
        
        # Verify we have 5 tools (populated as full objects)
        tools = skill.get("tools", [])
        assert len(tools) == 5, f"Expected 5 tools, got {len(tools)}"
        
        # Create a mapping of tool names to their data
        tool_map = {tool["name"]: tool for tool in tools}
        
        # Verify all expected tools are present
        expected_tools = ["add", "subtract", "multiply", "calc_add_subtract", "calc"]
        for tool_name in expected_tools:
            assert tool_name in tool_map, f"Tool '{tool_name}' should be present"
            assert "uuid" in tool_map[tool_name], f"Tool '{tool_name}' should have a UUID"
        
        # Verify SKILL snippet was imported (populated as full objects)
        # Note: File suffixes are dropped in naming convention, so SKILL.md becomes SKILL
        snippets = skill.get("snippets", [])
        assert len(snippets) > 0, "Should have at least one snippet (SKILL)"
        skill_snippet = next((s for s in snippets if "SKILL" in s.get("name", "")), None)
        assert skill_snippet is not None, "SKILL snippet should be present"
        
        # 4. Verify tool dependencies
        # calc depends on calc_add_subtract and multiply
        calc_tool = tool_map["calc"]
        calc_deps = calc_tool.get("dependencies", [])
        assert len(calc_deps) == 2, f"calc should have 2 dependencies, got {len(calc_deps)}"
        
        calc_dep_uuids = set(calc_deps)
        expected_calc_deps = {tool_map["calc_add_subtract"]["uuid"], tool_map["multiply"]["uuid"]}
        assert calc_dep_uuids == expected_calc_deps, \
            f"calc dependencies should be calc_add_subtract and multiply UUIDs"
        
        # calc_add_subtract depends on add and subtract
        calc_add_subtract_tool = tool_map["calc_add_subtract"]
        calc_add_subtract_deps = calc_add_subtract_tool.get("dependencies", [])
        assert len(calc_add_subtract_deps) == 2, \
            f"calc_add_subtract should have 2 dependencies, got {len(calc_add_subtract_deps)}"
        
        calc_add_subtract_dep_uuids = set(calc_add_subtract_deps)
        expected_calc_add_subtract_deps = {tool_map["add"]["uuid"], tool_map["subtract"]["uuid"]}
        assert calc_add_subtract_dep_uuids == expected_calc_add_subtract_deps, \
            f"calc_add_subtract dependencies should be add and subtract UUIDs"
        
        # multiply depends on add and subtract
        multiply_tool = tool_map["multiply"]
        multiply_deps = multiply_tool.get("dependencies", [])
        assert len(multiply_deps) == 2, f"multiply should have 2 dependencies, got {len(multiply_deps)}"
        
        multiply_dep_uuids = set(multiply_deps)
        expected_multiply_deps = {tool_map["add"]["uuid"], tool_map["subtract"]["uuid"]}
        assert multiply_dep_uuids == expected_multiply_deps, \
            f"multiply dependencies should be add and subtract UUIDs"
        
        # add and subtract should have no dependencies
        assert len(tool_map["add"].get("dependencies", [])) == 0, "add should have no dependencies"
        assert len(tool_map["subtract"].get("dependencies", [])) == 0, "subtract should have no dependencies"
        
        # 5. Execute the calc tool with parameters "*", 3, 5
        # Expected: 3 * 5 = 15
        calc_uuid = calc_tool["uuid"]
        execute_params = {
            "operation": "*",
            "num1": 3,
            "num2": 5
        }
        exec_response = await client.post(
            f"{BASE_URL}/tools/{calc_uuid}/execute",
            json=execute_params
        )
        
        assert exec_response.status_code == 200, f"Tool execution failed: {exec_response.text}"
        result = exec_response.json()
        
        # Verify the result is 15 (3 * 5)
        assert result is not None
        assert isinstance(result, dict), f"Expected dict result, got {type(result)}"
        return_value = result.get("return value")
        assert return_value is not None, "Expected return value to be present"
        # The result might be a string or float
        if isinstance(return_value, str):
            assert return_value == "15.0" or return_value == "15", f"Expected '15' or '15.0', got '{return_value}'"
        else:
            assert float(return_value) == 15.0, f"Expected 15.0, got {return_value}"
       
        # Clean up - delete the skill
        delete_response = await client.delete(f"{BASE_URL}/skills/{skill_name}")
        assert delete_response.status_code == 200, f"Failed to delete skill: {delete_response.text}"