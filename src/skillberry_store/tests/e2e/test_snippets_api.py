"""
E2E tests for snippet API endpoints.
Tests the full lifecycle of snippet operations: create, list, get, update, and delete.
"""

import pytest
import httpx

from skillberry_store.tests.utils import clean_test_tmp_dir, wait_until_server_ready

BASE_URL = "http://localhost:8000"



@pytest.mark.asyncio
async def test_create_snippet(run_sbs):
    """Test creating a new snippet."""
    content = "This is the content of my test snippet.\nIt can have multiple lines."
    snippet_data = {
        "name": "test_another_snippet",
        "description": "A test snippet for demonstration",
        "content": content,  # Required field, will be overridden by file if provided
        "content_type": "text/plain"
    }
    
    files = {
        "file": ("snippet.txt", content.encode(), "text/plain")
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/snippets/", params=snippet_data, files=files)
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert data.get("name") == "test_another_snippet"
        assert "created successfully" in data.get("message", "")
        # Verify UUID was generated
        assert "uuid" in data
        assert data.get("uuid") is not None
        assert len(data.get("uuid")) == 36  # UUID4 format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx


@pytest.mark.asyncio
async def test_create_duplicate_snippet(run_sbs):
    """Test that creating a duplicate snippet fails."""
    content = "This is the content of my test snippet."
    snippet_data = {
        "name": "test_snippet_duplicate",
        "description": "A test snippet for demonstration",
        "content": content,  # Required field
        "content_type": "text/plain"
    }
    
    files = {
        "file": ("snippet.txt", content.encode(), "text/plain")
    }

    async with httpx.AsyncClient() as client:
        # First, create the snippet
        response = await client.post(f"{BASE_URL}/snippets/", params=snippet_data, files=files)
        assert response.status_code == 200
        data = response.json()
        created_uuid = data.get("uuid")
        assert created_uuid is not None
        
        # Now try to create a duplicate with the same UUID - should fail with 409 Conflict
        snippet_data["uuid"] = created_uuid
        response = await client.post(f"{BASE_URL}/snippets/", params=snippet_data, files=files)
        assert response.status_code == 409
        assert "already exists" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_list_snippets(run_sbs):
    """Test listing all snippets."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/snippets/")
        assert response.status_code == 200
        snippets = response.json()
        assert isinstance(snippets, list)
        assert len(snippets) > 0
        
        # Check that our test snippet is in the list
        snippet_names = [s.get("name") for s in snippets]
        assert "test_another_snippet" in snippet_names


@pytest.mark.asyncio
async def test_get_snippet(run_sbs):
    """Test getting a specific snippet by name."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/snippets/test_another_snippet")
        assert response.status_code == 200
        snippet = response.json()
        assert snippet.get("name") == "test_another_snippet"
        assert snippet.get("description") == "A test snippet for demonstration"
        assert snippet.get("content_type") == "text/plain"
        assert "test snippet" in snippet.get("content", "")


@pytest.mark.asyncio
async def test_get_nonexistent_snippet(run_sbs):
    """Test that getting a non-existent snippet fails."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/snippets/nonexistent_snippet")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_snippet(run_sbs):
    """Test updating an existing snippet."""
    updated_data = {
        "name": "test_another_snippet",
        "description": "Updated test snippet description",
        "content": "This is the UPDATED content of my test snippet.",
        "content_type": "text/markdown"
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(f"{BASE_URL}/snippets/test_another_snippet", json=updated_data)
        assert response.status_code == 200
        data = response.json()
        assert "updated successfully" in data.get("message", "")

        # Verify the update
        get_response = await client.get(f"{BASE_URL}/snippets/test_another_snippet")
        assert get_response.status_code == 200
        snippet = get_response.json()
        assert snippet.get("description") == "Updated test snippet description"
        assert snippet.get("content_type") == "text/markdown"
        assert "UPDATED" in snippet.get("content", "")


@pytest.mark.asyncio
async def test_update_nonexistent_snippet(run_sbs):
    """Test that updating a non-existent snippet fails."""
    updated_data = {
        "name": "nonexistent_snippet",
        "description": "This should fail",
        "content": "Content",
        "content_type": "text/plain"
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(f"{BASE_URL}/snippets/nonexistent_snippet", json=updated_data)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_snippet(run_sbs):
    """Test deleting a snippet."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/snippets/test_another_snippet")
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data.get("message", "")

        # Verify deletion
        get_response = await client.get(f"{BASE_URL}/snippets/test_another_snippet")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_snippet(run_sbs):
    """Test that deleting a non-existent snippet fails."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/snippets/nonexistent_snippet")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_snippet_lifecycle(run_sbs):
    """Test the complete lifecycle of a snippet: create, read, update, delete."""
    snippet_name = "lifecycle_test_snippet"
    
    async with httpx.AsyncClient() as client:
        # 1. Create
        content = "Initial content"
        create_data = {
            "name": snippet_name,
            "description": "Lifecycle test snippet",
            "content": content,  # Required field
            "content_type": "text/plain"
        }
        files = {"file": ("snippet.txt", content.encode(), "text/plain")}
        create_response = await client.post(f"{BASE_URL}/snippets/", params=create_data, files=files)
        assert create_response.status_code == 200
        assert create_response.json().get("name") == snippet_name

        # 2. Read
        get_response = await client.get(f"{BASE_URL}/snippets/{snippet_name}")
        assert get_response.status_code == 200
        snippet = get_response.json()
        assert snippet.get("name") == snippet_name
        assert snippet.get("content") == "Initial content"

        # 3. Update
        update_data = {
            "name": snippet_name,
            "description": "Updated lifecycle test snippet",
            "content": "Updated content",
            "content_type": "text/markdown"
        }
        update_response = await client.put(f"{BASE_URL}/snippets/{snippet_name}", json=update_data)
        assert update_response.status_code == 200
        assert "updated successfully" in update_response.json().get("message", "")

        # 4. Verify update
        get_updated_response = await client.get(f"{BASE_URL}/snippets/{snippet_name}")
        assert get_updated_response.status_code == 200
        updated_snippet = get_updated_response.json()
        assert updated_snippet.get("content") == "Updated content"
        assert updated_snippet.get("content_type") == "text/markdown"

        # 5. Delete
        delete_response = await client.delete(f"{BASE_URL}/snippets/{snippet_name}")
        assert delete_response.status_code == 200
        assert "deleted successfully" in delete_response.json().get("message", "")

        # 6. Verify deletion
        get_deleted_response = await client.get(f"{BASE_URL}/snippets/{snippet_name}")
        assert get_deleted_response.status_code == 404


@pytest.mark.asyncio
async def test_search_snippets(run_sbs):
    """Test searching for snippets using the /search/snippets endpoint."""
    
    # Create test snippets with different descriptions
    test_snippets = [
        {
            "name": "python_logging_snippet",
            "description": "A Python code snippet for setting up logging configuration with file and console handlers",
            "content": "import logging\nlogging.basicConfig(level=logging.INFO)",
            "content_type": "text/plain"
        },
        {
            "name": "javascript_fetch_snippet",
            "description": "JavaScript snippet for making HTTP requests using the fetch API with error handling",
            "content": "fetch(url).then(response => response.json())",
            "content_type": "text/plain"
        },
        {
            "name": "sql_query_snippet",
            "description": "SQL query snippet for joining tables and filtering data with WHERE clause",
            "content": "SELECT * FROM users WHERE active = true",
            "content_type": "text/plain"
        }
    ]
    
    async with httpx.AsyncClient() as client:
        # Create the test snippets
        for snippet_data in test_snippets:
            content = snippet_data["content"]  # Keep content in params
            files = {"file": ("snippet.txt", content.encode(), "text/plain")}
            response = await client.post(f"{BASE_URL}/snippets/", params=snippet_data, files=files)
            assert response.status_code == 200, f"Failed to create snippet {snippet_data['name']}: {response.text}"
        
        # Wait a moment for indexing
        import asyncio
        await asyncio.sleep(1)
        
        # Test search for "logging"
        search_response = await client.get(
            f"{BASE_URL}/search/snippets",
            params={
                "search_term": "logging configuration",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200, f"Search failed: {search_response.text}"
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching snippet"
        
        # Verify python_logging_snippet is in results
        filenames = [r.get("filename") for r in results]
        assert "python_logging_snippet" in filenames, f"python_logging_snippet should be in search results, got: {filenames}"
        
        # Test search for "HTTP requests"
        search_response = await client.get(
            f"{BASE_URL}/search/snippets",
            params={
                "search_term": "HTTP requests fetch",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching snippet"
        
        # Test search for "SQL database"
        search_response = await client.get(
            f"{BASE_URL}/search/snippets",
            params={
                "search_term": "SQL database query",
                "max_number_of_results": 5,
                "similarity_threshold": 1.0
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) > 0, "Should find at least one matching snippet"
        
        # Test with strict similarity threshold
        search_response = await client.get(
            f"{BASE_URL}/search/snippets",
            params={
                "search_term": "logging",
                "max_number_of_results": 5,
                "similarity_threshold": 0.5  # Stricter threshold
            }
        )
        assert search_response.status_code == 200
        results = search_response.json()
        # Results should be filtered by similarity threshold
        for result in results:
            assert result.get("similarity_score", 1.0) <= 0.5, "All results should meet similarity threshold"
        
        # Clean up - delete test snippets
        for snippet_data in test_snippets:
            delete_response = await client.delete(f"{BASE_URL}/snippets/{snippet_data['name']}")
            assert delete_response.status_code == 200, f"Failed to delete snippet {snippet_data['name']}"