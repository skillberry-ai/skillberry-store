"""
E2E tests for VNFS API endpoints.
Tests the full lifecycle of VNFS server operations: create, list, get, update, delete, and start.
"""

import asyncio
import pytest
import httpx

from skillberry_store.tests.utils import clean_test_tmp_dir, wait_until_server_ready

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_create_vnfs_server(run_sbs):
    """Test creating a new VNFS server."""
    vnfs_data = {
        "name": "test_vnfs_server",
        "description": "A test VNFS server for demonstration",
        "port": 11001,
        "protocol": "webdav",
        "skill_uuid": "test-skill-uuid-123"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/vnfs_servers/", params=vnfs_data)
        assert response.status_code == 200
        data = response.json()
        assert data.get("name") == "test_vnfs_server"
        assert "created successfully" in data.get("message", "")
        # Verify UUID was generated
        assert "uuid" in data
        assert data.get("uuid") is not None
        assert len(data.get("uuid")) == 36  # UUID4 format
        # Verify port was assigned
        assert "port" in data
        assert data.get("port") is not None


@pytest.mark.asyncio
async def test_create_duplicate_vnfs_server(run_sbs):
    """Test that creating a duplicate VNFS server with same UUID fails."""
    vnfs_data = {
        "name": "test_vnfs_server",
        "description": "A test VNFS server for demonstration",
        "port": 11001,
        "protocol": "webdav",
        "skill_uuid": "test-skill-uuid-123"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/vnfs_servers/", params=vnfs_data)
        # Should fail with 409 Conflict
        assert response.status_code == 409
        assert "already exists" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_list_vnfs_servers(run_sbs):
    """Test listing all VNFS servers."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/vnfs_servers/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "virtual_nfs_servers" in data
        vnfs_servers = data["virtual_nfs_servers"]
        # API returns a dict of server objects keyed by server name
        assert isinstance(vnfs_servers, dict)
        assert len(vnfs_servers) > 0
        
        # Check that our test VNFS server is in the dict keys
        assert "test_vnfs_server" in vnfs_servers


@pytest.mark.asyncio
async def test_get_vnfs_server(run_sbs):
    """Test getting a specific VNFS server by name."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/vnfs_servers/test_vnfs_server")
        assert response.status_code == 200
        vnfs = response.json()
        assert vnfs.get("name") == "test_vnfs_server"
        assert vnfs.get("description") == "A test VNFS server for demonstration"
        assert "port" in vnfs
        assert "running" in vnfs
        assert "protocol" in vnfs
        assert vnfs.get("protocol") == "webdav"
        # Check skill_uuid
        assert "skill_uuid" in vnfs


@pytest.mark.asyncio
async def test_get_nonexistent_vnfs_server(run_sbs):
    """Test that getting a non-existent VNFS server fails."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/vnfs_servers/nonexistent_vnfs_server")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_vnfs_server(run_sbs):
    """Test updating an existing VNFS server."""
    updated_data = {
        "name": "test_vnfs_server",
        "description": "Updated test VNFS server description",
        "port": 11002,
        "protocol": "webdav",
        "skill_uuid": "updated-skill-uuid-456"
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(f"{BASE_URL}/vnfs_servers/test_vnfs_server", params=updated_data)
        assert response.status_code == 200
        data = response.json()
        assert "updated successfully" in data.get("message", "")
        assert "port" in data

        # Verify the update
        get_response = await client.get(f"{BASE_URL}/vnfs_servers/test_vnfs_server")
        assert get_response.status_code == 200
        vnfs = get_response.json()
        assert vnfs.get("description") == "Updated test VNFS server description"
        assert vnfs.get("skill_uuid") == "updated-skill-uuid-456"


@pytest.mark.asyncio
async def test_update_nonexistent_vnfs_server(run_sbs):
    """Test that updating a non-existent VNFS server fails."""
    updated_data = {
        "name": "nonexistent_vnfs_server",
        "description": "This should fail",
        "port": 11003,
        "protocol": "webdav",
        "skill_uuid": "test-skill-uuid"
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(f"{BASE_URL}/vnfs_servers/nonexistent_vnfs_server", params=updated_data)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_start_vnfs_server(run_sbs):
    """Test starting a VNFS server."""
    async with httpx.AsyncClient() as client:
        # First, ensure the server exists
        get_response = await client.get(f"{BASE_URL}/vnfs_servers/test_vnfs_server")
        assert get_response.status_code == 200
        
        # Try to start the server
        response = await client.post(f"{BASE_URL}/vnfs_servers/test_vnfs_server/start")
        assert response.status_code == 200
        data = response.json()
        assert "port" in data
        # Message could be "started" or "already running"
        assert "started" in data.get("message", "").lower() or "running" in data.get("message", "").lower()


@pytest.mark.asyncio
async def test_delete_vnfs_server(run_sbs):
    """Test deleting a VNFS server."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/vnfs_servers/test_vnfs_server")
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data.get("message", "")

        # Verify deletion
        get_response = await client.get(f"{BASE_URL}/vnfs_servers/test_vnfs_server")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_vnfs_server(run_sbs):
    """Test that deleting a non-existent VNFS server fails."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/vnfs_servers/nonexistent_vnfs_server")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_vnfs_server_lifecycle(run_sbs):
    """Test the complete lifecycle of a VNFS server: create, read, update, start, delete."""
    vnfs_name = "lifecycle_test_vnfs_server"
    
    async with httpx.AsyncClient() as client:
        # Clean up if exists from previous run
        try:
            await client.delete(f"{BASE_URL}/vnfs_servers/{vnfs_name}")
            # Wait a moment for cleanup
            await asyncio.sleep(0.5)
        except:
            pass  # Ignore if doesn't exist
        
        # 1. Create
        create_data = {
            "name": vnfs_name,
            "description": "Lifecycle test VNFS server",
            "port": 11100,
            "protocol": "webdav",
            "skill_uuid": "lifecycle-skill-uuid"
        }
        create_response = await client.post(f"{BASE_URL}/vnfs_servers/", params=create_data)
        assert create_response.status_code == 200
        assert create_response.json().get("name") == vnfs_name

        # 2. Read
        get_response = await client.get(f"{BASE_URL}/vnfs_servers/{vnfs_name}")
        assert get_response.status_code == 200
        vnfs = get_response.json()
        assert vnfs.get("name") == vnfs_name
        assert vnfs.get("description") == "Lifecycle test VNFS server"
        assert vnfs.get("protocol") == "webdav"

        # 3. Update
        update_data = {
            "name": vnfs_name,
            "description": "Updated lifecycle test VNFS server",
            "port": 11101,
            "protocol": "webdav",
            "skill_uuid": "updated-lifecycle-skill-uuid"
        }
        update_response = await client.put(f"{BASE_URL}/vnfs_servers/{vnfs_name}", params=update_data)
        assert update_response.status_code == 200
        assert "updated successfully" in update_response.json().get("message", "")

        # 4. Verify update
        get_updated_response = await client.get(f"{BASE_URL}/vnfs_servers/{vnfs_name}")
        assert get_updated_response.status_code == 200
        updated_vnfs = get_updated_response.json()
        assert updated_vnfs.get("description") == "Updated lifecycle test VNFS server"
        assert updated_vnfs.get("skill_uuid") == "updated-lifecycle-skill-uuid"

        # 5. Start
        start_response = await client.post(f"{BASE_URL}/vnfs_servers/{vnfs_name}/start")
        assert start_response.status_code == 200

        # 6. Delete
        delete_response = await client.delete(f"{BASE_URL}/vnfs_servers/{vnfs_name}")
        assert delete_response.status_code == 200
        assert "deleted successfully" in delete_response.json().get("message", "")

        # 7. Verify deletion
        get_deleted_response = await client.get(f"{BASE_URL}/vnfs_servers/{vnfs_name}")
        assert get_deleted_response.status_code == 404


@pytest.mark.asyncio
async def test_search_vnfs_servers(run_sbs):
    """Test searching for VNFS servers using the /search/vnfs_servers endpoint."""
    
    # Create test VNFS servers with different descriptions
    test_vnfs_servers = [
        {
            "name": "python_vnfs_server",
            "description": "A Python NFS server for sharing Python code and scripts with file access capabilities",
            "port": 11020,
            "protocol": "webdav",
            "skill_uuid": "python-skill-uuid"
        },
        {
            "name": "javascript_vnfs_server",
            "description": "JavaScript NFS server for sharing Node.js scripts and handling file transfers",
            "port": 11021,
            "protocol": "webdav",
            "skill_uuid": "js-skill-uuid"
        },
        {
            "name": "database_vnfs_server",
            "description": "Database NFS server for SQL scripts and database backup files with secure access",
            "port": 11022,
            "protocol": "webdav",
            "skill_uuid": "db-skill-uuid"
        }
    ]
    
    async with httpx.AsyncClient() as client:
        # Create the test VNFS servers
        for vnfs_data in test_vnfs_servers:
            response = await client.post(f"{BASE_URL}/vnfs_servers/", params=vnfs_data)
            assert response.status_code == 200, f"Failed to create VNFS server {vnfs_data['name']}: {response.text}"
        
        # Wait a moment for indexing
        await asyncio.sleep(1)
        
        # Test search for "Python file access"
        search_response = await client.get(
            f"{BASE_URL}/search/vnfs_servers",
            params={
                "search_term": "Python file access capabilities",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200, f"Search failed: {search_response.text}"
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching VNFS server"
        
        # Verify python_vnfs_server is in results
        filenames = [r.get("filename") for r in results]
        assert "python_vnfs_server" in filenames, f"python_vnfs_server should be in search results, got: {filenames}"
        
        # Test search for "file transfers"
        search_response = await client.get(
            f"{BASE_URL}/search/vnfs_servers",
            params={
                "search_term": "file transfers Node.js",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching VNFS server"
        
        # Test search for "SQL database"
        search_response = await client.get(
            f"{BASE_URL}/search/vnfs_servers",
            params={
                "search_term": "SQL database backup files",
                "max_number_of_results": 5,
                "similarity_threshold": 1.5
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching VNFS server"
        
        # Test with strict similarity threshold
        search_response = await client.get(
            f"{BASE_URL}/search/vnfs_servers",
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
        
        # Clean up - delete test VNFS servers
        for vnfs_data in test_vnfs_servers:
            delete_response = await client.delete(f"{BASE_URL}/vnfs_servers/{vnfs_data['name']}")
            assert delete_response.status_code == 200, f"Failed to delete VNFS server {vnfs_data['name']}"


@pytest.mark.asyncio
async def test_create_vnfs_server_with_nfs_protocol(run_sbs):
    """Test creating a VNFS server with NFS protocol."""
    vnfs_data = {
        "name": "test_nfs_protocol_server",
        "description": "A test VNFS server using NFS protocol",
        "port": 11030,
        "protocol": "nfs",
        "skill_uuid": "nfs-test-skill-uuid"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/vnfs_servers/", params=vnfs_data)
        assert response.status_code == 200
        data = response.json()
        assert data.get("name") == "test_nfs_protocol_server"
        
        # Verify the server was created with NFS protocol
        get_response = await client.get(f"{BASE_URL}/vnfs_servers/test_nfs_protocol_server")
        assert get_response.status_code == 200
        vnfs = get_response.json()
        assert vnfs.get("protocol") == "nfs"
        
        # Clean up
        await client.delete(f"{BASE_URL}/vnfs_servers/test_nfs_protocol_server")


@pytest.mark.asyncio
async def test_multiple_vnfs_servers_same_name_different_uuid(run_sbs):
    """Test that multiple VNFS servers with the same name but different UUIDs can coexist."""
    server_name = "duplicate_name_server"
    
    async with httpx.AsyncClient() as client:
        # Create first server with explicit UUID
        vnfs_data_1 = {
            "name": server_name,
            "description": "First server with this name",
            "port": 11040,
            "protocol": "webdav",
            "skill_uuid": "skill-uuid-1",
            "uuid": "uuid-server-1"
        }
        response1 = await client.post(f"{BASE_URL}/vnfs_servers/", params=vnfs_data_1)
        assert response1.status_code == 200
        data1 = response1.json()
        uuid1 = data1.get("uuid")
        assert uuid1 == "uuid-server-1"
        
        # Create second server with same name but different UUID
        vnfs_data_2 = {
            "name": server_name,
            "description": "Second server with this name",
            "port": 11041,
            "protocol": "webdav",
            "skill_uuid": "skill-uuid-2",
            "uuid": "uuid-server-2"
        }
        response2 = await client.post(f"{BASE_URL}/vnfs_servers/", params=vnfs_data_2)
        assert response2.status_code == 200
        data2 = response2.json()
        uuid2 = data2.get("uuid")
        assert uuid2 == "uuid-server-2"
        
        # Verify both servers exist and can be retrieved by UUID
        get_response1 = await client.get(f"{BASE_URL}/vnfs_servers/{uuid1}")
        assert get_response1.status_code == 200
        server1 = get_response1.json()
        assert server1.get("uuid") == uuid1
        assert server1.get("description") == "First server with this name"
        
        get_response2 = await client.get(f"{BASE_URL}/vnfs_servers/{uuid2}")
        assert get_response2.status_code == 200
        server2 = get_response2.json()
        assert server2.get("uuid") == uuid2
        assert server2.get("description") == "Second server with this name"
        
        # Clean up both servers
        await client.delete(f"{BASE_URL}/vnfs_servers/{uuid1}")
        await client.delete(f"{BASE_URL}/vnfs_servers/{uuid2}")


@pytest.mark.asyncio
async def test_vnfs_server_webdav_accessibility(run_sbs):
    """Test that a VNFS server with WebDAV protocol is accessible."""
    vnfs_name = "webdav_access_test_server"
    
    async with httpx.AsyncClient() as client:
        # Create a VNFS server with WebDAV
        vnfs_data = {
            "name": vnfs_name,
            "description": "WebDAV accessibility test server",
            "port": 11050,
            "protocol": "webdav",
            "skill_uuid": "webdav-test-skill-uuid"
        }
        create_response = await client.post(f"{BASE_URL}/vnfs_servers/", params=vnfs_data)
        assert create_response.status_code == 200
        port = create_response.json().get("port")
        
        # Start the server
        start_response = await client.post(f"{BASE_URL}/vnfs_servers/{vnfs_name}/start")
        assert start_response.status_code == 200
        
        # Wait for server to be fully started
        await asyncio.sleep(2)
        
        # Try to access the WebDAV endpoint (should respond to OPTIONS or GET)
        try:
            webdav_response = await client.request(
                "OPTIONS",
                f"http://localhost:{port}/",
                timeout=5.0
            )
            # WebDAV server should respond (200, 204, or other success codes)
            assert webdav_response.status_code < 500, f"WebDAV server should be accessible, got {webdav_response.status_code}"
        except Exception as e:
            # If OPTIONS fails, try GET
            try:
                webdav_response = await client.get(
                    f"http://localhost:{port}/",
                    timeout=5.0
                )
                assert webdav_response.status_code < 500, f"WebDAV server should be accessible, got {webdav_response.status_code}"
            except Exception as e2:
                pytest.fail(f"WebDAV server not accessible: OPTIONS failed with {e}, GET failed with {e2}")
        
        # Clean up
        await client.delete(f"{BASE_URL}/vnfs_servers/{vnfs_name}")

# Made with Bob
