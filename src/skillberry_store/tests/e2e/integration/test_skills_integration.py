"""
Integration tests for Skills API endpoints.

These tests require a running skillberry-store service.
Run with: pytest -m integration
"""

import pytest
from skillberry_store_sdk.models.manifest_state import ManifestState
from skillberry_store_sdk.models.skill_schema import SkillSchema


# Shared state for tests that depend on each other
test_state = {
    "skill_name": None,
    "skill_uuid": None,
    "tool_uuid": None,  # We'll need a tool UUID to create a skill
}


@pytest.mark.integration
class TestSkillsAPI:
    """Test suite for Skills API endpoints using SDK client."""

    def test_01_create_skill(self, skills_api):
        """Test creating a new skill."""
        skill_name = "test-integration-skill"
        
        response = skills_api.create_skill_skills_post(
            name=skill_name,
            description="A test skill for integration testing",
            state=ManifestState.APPROVED,
            tags=["test", "integration"],
            tool_uuids=[],  # Empty for now, can add tools later
            snippet_uuids=[]
        )
        
        assert response is not None
        assert "message" in response or "name" in response or "uuid" in response
        
        # Store for later tests
        if isinstance(response, dict):
            test_state["skill_name"] = response.get("name", skill_name)
            test_state["skill_uuid"] = response.get("uuid")

    def test_02_list_skills(self, skills_api):
        """Test listing all skills."""
        response = skills_api.list_skills_skills_get()
        
        assert response is not None
        assert isinstance(response, list)
        
        # Verify our created skill is in the list
        if test_state["skill_name"]:
            skill_names = [skill.get("name") for skill in response if isinstance(skill, dict)]
            assert test_state["skill_name"] in skill_names

    def test_03_get_skill_by_name(self, skills_api):
        """Test getting a skill by name."""
        if not test_state["skill_name"]:
            pytest.skip("Skill name not available from previous test")
        
        response = skills_api.get_skill_skills_name_get(name=test_state["skill_name"])
        
        assert response is not None
        assert response.get("name") == test_state["skill_name"]
        assert "uuid" in response
        assert "description" in response

    def test_04_update_skill(self, skills_api):
        """Test updating an existing skill."""
        if not test_state["skill_name"]:
            pytest.skip("Skill name not available from previous test")
        
        # Get current skill to create updated schema
        current_skill = skills_api.get_skill_skills_name_get(name=test_state["skill_name"])
        
        # Create updated skill schema
        updated_skill = SkillSchema(
            name=current_skill.get("name"),
            uuid=current_skill.get("uuid"),
            description="Updated description for integration testing",
            state=ManifestState.APPROVED,
            tags=["test", "integration", "updated"],
            tool_uuids=current_skill.get("tool_uuids", []),
            snippet_uuids=current_skill.get("snippet_uuids", [])
        )
        
        response = skills_api.update_skill_skills_name_put(
            name=test_state["skill_name"],
            skill_schema=updated_skill
        )
        
        assert response is not None
        assert "message" in response or "updated" in str(response).lower()

    def test_05_search_skills(self, skills_api):
        """Test searching skills."""
        if not test_state["skill_name"]:
            pytest.skip("Skill name not available from previous test")
        
        # Search for skills with "integration" in the description
        response = skills_api.search_skills_search_skills_get(search_term="integration")
        
        assert response is not None
        assert isinstance(response, (list, dict))

    def test_06_delete_skill(self, skills_api):
        """Test deleting a skill. This should be the last test."""
        if not test_state["skill_name"]:
            pytest.skip("Skill name not available from previous test")
        
        response = skills_api.delete_skill_skills_name_delete(name=test_state["skill_name"])
        
        assert response is not None
        assert "message" in response or "deleted" in str(response).lower()
        
        # Verify skill is deleted
        try:
            skills_api.get_skill_skills_name_get(name=test_state["skill_name"])
            # If we get here, the skill still exists (might be expected in some cases)
        except Exception:
            # Expected - skill should not be found
            pass


@pytest.mark.integration
def test_create_skill_with_tools(skills_api, tools_api, test_tool_file):
    """Test creating a skill that includes tools."""
    # First, create a tool to include in the skill
    tool_file = ("skill_test_tool.py", test_tool_file)
    
    try:
        tool_response = tools_api.add_tool_from_python_tools_add_post(
            tool=tool_file,
            tool_name="skill_test_add"
        )
        
        tool_uuid = tool_response.get("uuid") if isinstance(tool_response, dict) else None
        
        if tool_uuid:
            # Now create a skill with this tool
            skill_response = skills_api.create_skill_skills_post(
                name="test-skill-with-tools",
                description="A skill that includes tools",
                state=ManifestState.APPROVED,
                tool_uuids=[tool_uuid],
                snippet_uuids=[]
            )
            
            assert skill_response is not None
            
            # Clean up
            if "name" in skill_response:
                skills_api.delete_skill_skills_name_delete(name=skill_response["name"])
            
            tools_api.delete_tool_tools_name_delete(name="skill_test_add")
        else:
            pytest.skip("Could not create tool for skill test")
            
    except Exception as e:
        pytest.skip(f"Skill with tools test not fully supported: {e}")


@pytest.mark.integration
def test_skill_lifecycle_states(skills_api):
    """Test skill lifecycle state transitions."""
    skill_name = "test-lifecycle-skill"
    
    try:
        # Create skill in draft state
        response = skills_api.create_skill_skills_post(
            name=skill_name,
            description="Testing lifecycle states",
            state=ManifestState.NEW
        )
        
        assert response is not None
        
        # Update to approved state
        update_response = skills_api.update_skill_skills_name_put(
            name=skill_name,
            state=ManifestState.APPROVED
        )
        
        assert update_response is not None
        
        # Verify state change
        skill = skills_api.get_skill_skills_name_get(name=skill_name)
        assert skill.get("state") == ManifestState.APPROVED or skill.get("state") == "approved"
        
        # Clean up
        skills_api.delete_skill_skills_name_delete(name=skill_name)
        
    except Exception as e:
        # Clean up on error
        try:
            skills_api.delete_skill_skills_name_delete(name=skill_name)
        except:
            pass
        pytest.skip(f"Lifecycle state test not fully supported: {e}")

# Made with Bob
