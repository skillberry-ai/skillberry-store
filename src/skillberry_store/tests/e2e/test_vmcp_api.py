"""
E2E tests for VMCP API endpoints.
Tests the full lifecycle of VMCP server operations: create, list, get, update, and delete.
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
async def test_create_vmcp_server(run_sbs):
    """Test creating a new VMCP server."""
    # Using params for Query() parameters - FastAPI will handle the nested structure
    vmcp_data = {
        "name": "test_vmcp_server",
        "description": "A test VMCP server for demonstration",
        "port": 9001,
        "skill.name": "test_skill",
        "skill.description": "Test skill",
        "skill.tool_uuids": ["tool1", "tool2"]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/vmcp_servers/", params=vmcp_data)
        assert response.status_code == 200
        data = response.json()
        assert data.get("name") == "test_vmcp_server"
        assert "created successfully" in data.get("message", "")
        # Verify UUID was generated
        assert "uuid" in data
        assert data.get("uuid") is not None
        assert len(data.get("uuid")) == 36  # UUID4 format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        # Verify port was assigned
        assert "port" in data
        assert data.get("port") is not None


@pytest.mark.asyncio
async def test_create_duplicate_vmcp_server(run_sbs):
    """Test that creating a duplicate VMCP server fails."""
    vmcp_data = {
        "name": "test_vmcp_server",
        "description": "A test VMCP server for demonstration",
        "port": 9001,
        "skill.name": "test_skill",
        "skill.description": "Test skill",
        "skill.tool_uuids": ["tool1", "tool2"]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/vmcp_servers/", params=vmcp_data)
        # Should fail with 409 Conflict
        assert response.status_code == 409
        assert "already exists" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_list_vmcp_servers(run_sbs):
    """Test listing all VMCP servers."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/vmcp_servers/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "virtual_mcp_servers" in data
        vmcp_servers = data["virtual_mcp_servers"]
        # API returns a dict of server objects keyed by server name
        assert isinstance(vmcp_servers, dict)
        assert len(vmcp_servers) > 0
        
        # Check that our test VMCP server is in the dict keys
        assert "test_vmcp_server" in vmcp_servers


@pytest.mark.asyncio
async def test_get_vmcp_server(run_sbs):
    """Test getting a specific VMCP server by name."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/vmcp_servers/test_vmcp_server")
        assert response.status_code == 200
        vmcp = response.json()
        assert vmcp.get("name") == "test_vmcp_server"
        assert vmcp.get("description") == "A test VMCP server for demonstration"
        assert "port" in vmcp
        assert "running" in vmcp
        # Check skill_uuid - may be None if not provided
        assert "skill_uuid" in vmcp


@pytest.mark.asyncio
async def test_get_nonexistent_vmcp_server(run_sbs):
    """Test that getting a non-existent VMCP server fails."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/vmcp_servers/nonexistent_vmcp_server")
        assert response.status_code == 404  # File not found results in 404


@pytest.mark.asyncio
async def test_update_vmcp_server(run_sbs):
    """Test updating an existing VMCP server."""
    updated_data = {
        "name": "test_vmcp_server",
        "description": "Updated test VMCP server description",
        "port": 9002,
        "skill.name": "updated_skill",
        "skill.description": "Updated test skill",
        "skill.tool_uuids": ["tool3", "tool4"]
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(f"{BASE_URL}/vmcp_servers/test_vmcp_server", params=updated_data)
        assert response.status_code == 200
        data = response.json()
        assert "updated successfully" in data.get("message", "")
        assert "port" in data

        # Verify the update
        get_response = await client.get(f"{BASE_URL}/vmcp_servers/test_vmcp_server")
        assert get_response.status_code == 200
        vmcp = get_response.json()
        assert vmcp.get("description") == "Updated test VMCP server description"
        if vmcp.get("skill") is not None:
            assert vmcp.get("skill").get("name") == "updated_skill"


@pytest.mark.asyncio
async def test_update_nonexistent_vmcp_server(run_sbs):
    """Test that updating a non-existent VMCP server fails."""
    updated_data = {
        "name": "nonexistent_vmcp_server",
        "description": "This should fail",
        "port": 9003,
        "skill.name": "test_skill",
        "skill.description": "Test skill",
        "skill.tool_uuids": ["tool1"]
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(f"{BASE_URL}/vmcp_servers/nonexistent_vmcp_server", params=updated_data)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_vmcp_server(run_sbs):
    """Test deleting a VMCP server."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/vmcp_servers/test_vmcp_server")
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data.get("message", "")

        # Verify deletion
        get_response = await client.get(f"{BASE_URL}/vmcp_servers/test_vmcp_server")
        assert get_response.status_code == 404  # File not found results in 404


@pytest.mark.asyncio
async def test_delete_nonexistent_vmcp_server(run_sbs):
    """Test that deleting a non-existent VMCP server fails."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/vmcp_servers/nonexistent_vmcp_server")
        assert response.status_code == 404  # File not found results in 404


@pytest.mark.asyncio
async def test_vmcp_server_lifecycle(run_sbs):
    """Test the complete lifecycle of a VMCP server: create, read, update, delete."""
    vmcp_name = "lifecycle_test_vmcp_server"
    
    async with httpx.AsyncClient() as client:
        # Clean up if exists from previous run
        try:
            await client.delete(f"{BASE_URL}/vmcp_servers/{vmcp_name}")
            # Wait a moment for cleanup
            await asyncio.sleep(0.5)
        except:
            pass  # Ignore if doesn't exist
        
        # 1. Create
        create_data = {
            "name": vmcp_name,
            "description": "Lifecycle test VMCP server",
            "port": 9100,
            "skill.name": "lifecycle_skill",
            "skill.description": "Lifecycle test skill",
            "skill.tool_uuids": ["tool1"]
        }
        create_response = await client.post(f"{BASE_URL}/vmcp_servers/", params=create_data)
        assert create_response.status_code == 200
        assert create_response.json().get("name") == vmcp_name

        # 2. Read
        get_response = await client.get(f"{BASE_URL}/vmcp_servers/{vmcp_name}")
        assert get_response.status_code == 200
        vmcp = get_response.json()
        assert vmcp.get("name") == vmcp_name
        assert vmcp.get("description") == "Lifecycle test VMCP server"
        assert vmcp.get("running") == True

        # 3. Update
        update_data = {
            "name": vmcp_name,
            "description": "Updated lifecycle test VMCP server",
            "port": 9101,
            "skill.name": "updated_lifecycle_skill",
            "skill.description": "Updated lifecycle test skill",
            "skill.tool_uuids": ["tool2", "tool3"]
        }
        update_response = await client.put(f"{BASE_URL}/vmcp_servers/{vmcp_name}", params=update_data)
        assert update_response.status_code == 200
        assert "updated successfully" in update_response.json().get("message", "")

        # 4. Verify update
        get_updated_response = await client.get(f"{BASE_URL}/vmcp_servers/{vmcp_name}")
        assert get_updated_response.status_code == 200
        updated_vmcp = get_updated_response.json()
        assert updated_vmcp.get("description") == "Updated lifecycle test VMCP server"
        if updated_vmcp.get("skill") is not None:
            assert updated_vmcp.get("skill").get("name") == "updated_lifecycle_skill"

        # 5. Delete
        delete_response = await client.delete(f"{BASE_URL}/vmcp_servers/{vmcp_name}")
        assert delete_response.status_code == 200
        assert "deleted successfully" in delete_response.json().get("message", "")

        # 6. Verify deletion
        get_deleted_response = await client.get(f"{BASE_URL}/vmcp_servers/{vmcp_name}")
        assert get_deleted_response.status_code == 404  # File not found results in 404


@pytest.mark.asyncio
async def test_search_vmcp_servers(run_sbs):
    """Test searching for VMCP servers using the /search/vmcp_servers endpoint."""
    
    # Create test VMCP servers with different descriptions
    test_vmcp_servers = [
        {
            "name": "python_vmcp_server",
            "description": "A Python MCP server for executing Python code and scripts with logging capabilities",
            "port": 9020,
            "skill.name": "python_skill",
            "skill.description": "Python execution skill",
            "skill.tool_uuids": ["python_tool"]
        },
        {
            "name": "javascript_vmcp_server",
            "description": "JavaScript MCP server for running Node.js scripts and handling HTTP requests",
            "port": 9021,
            "skill.name": "javascript_skill",
            "skill.description": "JavaScript execution skill",
            "skill.tool_uuids": ["js_tool"]
        },
        {
            "name": "database_vmcp_server",
            "description": "Database MCP server for SQL queries and database operations with connection pooling",
            "port": 9022,
            "skill.name": "database_skill",
            "skill.description": "Database operations skill",
            "skill.tool_uuids": ["db_tool"]
        }
    ]
    
    async with httpx.AsyncClient() as client:
        # Create the test VMCP servers
        for vmcp_data in test_vmcp_servers:
            response = await client.post(f"{BASE_URL}/vmcp_servers/", params=vmcp_data)
            assert response.status_code == 200, f"Failed to create VMCP server {vmcp_data['name']}: {response.text}"
        
        # Wait a moment for indexing
        await asyncio.sleep(1)
        
        # Test search for "Python logging"
        search_response = await client.get(
            f"{BASE_URL}/search/vmcp_servers",
            params={
                "search_term": "Python logging capabilities",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200, f"Search failed: {search_response.text}"
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching VMCP server"
        
        # Verify python_vmcp_server is in results
        filenames = [r.get("filename") for r in results]
        assert "python_vmcp_server" in filenames, f"python_vmcp_server should be in search results, got: {filenames}"
        
        # Test search for "HTTP requests"
        search_response = await client.get(
            f"{BASE_URL}/search/vmcp_servers",
            params={
                "search_term": "HTTP requests Node.js",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching VMCP server"
        
        # Test search for "SQL database"
        search_response = await client.get(
            f"{BASE_URL}/search/vmcp_servers",
            params={
                "search_term": "SQL database queries",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching VMCP server"
        
        # Test with strict similarity threshold
        search_response = await client.get(
            f"{BASE_URL}/search/vmcp_servers",
            params={
                "search_term": "Python",
                "max_number_of_results": 5,
                "similarity_threshold": 0.5  # Stricter threshold
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        # Results should be filtered by similarity threshold
        for result in results:
            assert result.get("similarity_score", 1.0) <= 0.5, "All results should meet similarity threshold"
        
        # Clean up - delete test VMCP servers
        for vmcp_data in test_vmcp_servers:
            delete_response = await client.delete(f"{BASE_URL}/vmcp_servers/{vmcp_data['name']}")
            assert delete_response.status_code == 200, f"Failed to delete VMCP server {vmcp_data['name']}"