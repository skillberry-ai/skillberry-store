import pytest

from skillberry_store.modules.dict_cache import DictCache


@pytest.fixture
def cache():
    """Create a fresh DictCache instance for each test."""
    return DictCache()


@pytest.fixture
def sample_manifest():
    """Create a sample manifest for testing."""
    return {
        "uuid": "uuid-123",
        "name": "mytool",
        "description": "A test tool",
        "version": "1.0.0",
    }


@pytest.fixture
def another_manifest():
    """Create another sample manifest for testing."""
    return {
        "uuid": "uuid-456",
        "name": "anothertool",
        "description": "Another test tool",
        "version": "2.0.0",
    }


def test_get_returns_none_for_nonexistent_uuid(cache):
    """Test that getting a non-existent UUID returns None."""
    result = cache.get("nonexistent-uuid")
    assert result is None


def test_set_and_get(cache, sample_manifest):
    """Test setting and getting a manifest."""
    cache.set("uuid-123", sample_manifest)
    result = cache.get("uuid-123")
    assert result == sample_manifest


def test_set_updates_existing_uuid(cache, sample_manifest):
    """Test that setting a UUID that exists updates it."""
    cache.set("uuid-123", sample_manifest)

    updated_manifest = sample_manifest.copy()
    updated_manifest["version"] = "2.0.0"
    cache.set("uuid-123", updated_manifest)

    result = cache.get("uuid-123")
    assert result == updated_manifest
    assert result["version"] == "2.0.0"


def test_remove(cache, sample_manifest):
    """Test removing a manifest from the cache."""
    cache.set("uuid-123", sample_manifest)
    assert cache.has("uuid-123")

    cache.remove("uuid-123")
    assert not cache.has("uuid-123")
    assert cache.get("uuid-123") is None


def test_remove_nonexistent(cache):
    """Test that removing a non-existent UUID doesn't raise an error."""
    cache.remove("nonexistent-uuid")  # Should not raise


def test_has(cache, sample_manifest):
    """Test checking if a UUID exists in the cache."""
    assert not cache.has("uuid-123")

    cache.set("uuid-123", sample_manifest)
    assert cache.has("uuid-123")

    cache.remove("uuid-123")
    assert not cache.has("uuid-123")


def test_get_all_uuids_empty_cache(cache):
    """Test getting all UUIDs from an empty cache."""
    uuids = cache.get_all_uuids()
    assert uuids == set()


def test_get_all_uuids_with_entries(cache, sample_manifest, another_manifest):
    """Test getting all UUIDs from a cache with entries."""
    cache.set("uuid-123", sample_manifest)
    cache.set("uuid-456", another_manifest)
    cache.set("uuid-789", {"uuid": "uuid-789", "name": "third"})

    uuids = cache.get_all_uuids()
    assert uuids == {"uuid-123", "uuid-456", "uuid-789"}


def test_get_all_manifests(cache, sample_manifest, another_manifest):
    """Test getting all manifests from the cache."""
    cache.set("uuid-123", sample_manifest)
    cache.set("uuid-456", another_manifest)

    manifests = cache.get_all_dicts()
    assert len(manifests) == 2
    assert manifests["uuid-123"] == sample_manifest
    assert manifests["uuid-456"] == another_manifest


def test_get_all_manifests_returns_copy(cache, sample_manifest):
    """Test that get_all_dicts returns a copy, not the original dict."""
    cache.set("uuid-123", sample_manifest)

    manifests = cache.get_all_dicts()
    manifests["uuid-999"] = {"uuid": "uuid-999", "name": "new"}

    # Original cache should not be affected
    assert not cache.has("uuid-999")
    assert cache.size() == 1


def test_clear(cache, sample_manifest, another_manifest):
    """Test clearing all entries from the cache."""
    cache.set("uuid-123", sample_manifest)
    cache.set("uuid-456", another_manifest)
    cache.set("uuid-789", {"uuid": "uuid-789", "name": "third"})

    assert cache.size() == 3

    cache.clear()
    assert cache.size() == 0
    assert cache.get("uuid-123") is None
    assert len(cache.get_all_uuids()) == 0


def test_size(cache, sample_manifest, another_manifest):
    """Test getting the size of the cache."""
    assert cache.size() == 0

    cache.set("uuid-123", sample_manifest)
    assert cache.size() == 1

    cache.set("uuid-456", another_manifest)
    assert cache.size() == 2

    cache.remove("uuid-123")
    assert cache.size() == 1

    cache.clear()
    assert cache.size() == 0


def test_multiple_resources_scenario(cache):
    """Test managing multiple resources with different types."""
    tool_manifest = {"uuid": "tool-uuid", "name": "mytool", "type": "tool"}
    snippet_manifest = {"uuid": "snippet-uuid", "name": "mysnippet", "type": "snippet"}
    skill_manifest = {"uuid": "skill-uuid", "name": "myskill", "type": "skill"}

    cache.set("tool-uuid", tool_manifest)
    cache.set("snippet-uuid", snippet_manifest)
    cache.set("skill-uuid", skill_manifest)

    assert cache.get("tool-uuid") == tool_manifest
    assert cache.get("snippet-uuid") == snippet_manifest
    assert cache.get("skill-uuid") == skill_manifest

    uuids = cache.get_all_uuids()
    assert uuids == {"tool-uuid", "snippet-uuid", "skill-uuid"}


def test_version_chain_scenario(cache):
    """Test caching multiple versions of the same object."""
    v1_manifest = {
        "uuid": "uuid-v1",
        "name": "mytool",
        "version": "1.0.0",
        "parent": None,
    }
    v2_manifest = {
        "uuid": "uuid-v2",
        "name": "mytool",
        "version": "2.0.0",
        "parent": "uuid-v1",
    }
    v3_manifest = {
        "uuid": "uuid-v3",
        "name": "mytool",
        "version": "3.0.0",
        "parent": "uuid-v2",
    }

    cache.set("uuid-v1", v1_manifest)
    cache.set("uuid-v2", v2_manifest)
    cache.set("uuid-v3", v3_manifest)

    assert cache.size() == 3
    assert cache.get("uuid-v1")["version"] == "1.0.0"
    assert cache.get("uuid-v2")["version"] == "2.0.0"
    assert cache.get("uuid-v3")["version"] == "3.0.0"


def test_update_manifest_scenario(cache, sample_manifest):
    """Test updating a manifest in the cache."""
    cache.set("uuid-123", sample_manifest)

    # Simulate an update
    updated_manifest = cache.get("uuid-123").copy()
    updated_manifest["description"] = "Updated description"
    updated_manifest["version"] = "2.0.0"
    cache.set("uuid-123", updated_manifest)

    result = cache.get("uuid-123")
    assert result["description"] == "Updated description"
    assert result["version"] == "2.0.0"


def test_delete_scenario(cache, sample_manifest, another_manifest):
    """Test deleting resources from the cache."""
    cache.set("uuid-123", sample_manifest)
    cache.set("uuid-456", another_manifest)

    assert cache.size() == 2

    cache.remove("uuid-123")
    assert cache.size() == 1
    assert not cache.has("uuid-123")
    assert cache.has("uuid-456")

    cache.remove("uuid-456")
    assert cache.size() == 0


def test_large_manifest(cache):
    """Test caching a large manifest with many fields."""
    large_manifest = {
        "uuid": "uuid-large",
        "name": "large-tool",
        "description": "A tool with many fields",
        "version": "1.0.0",
        "params": {
            "param1": {"type": "string", "description": "First param"},
            "param2": {"type": "integer", "description": "Second param"},
            "param3": {"type": "boolean", "description": "Third param"},
        },
        "returns": {
            "type": "object",
            "properties": {"result": {"type": "string"}, "status": {"type": "integer"}},
        },
        "tags": ["tag1", "tag2", "tag3"],
        "metadata": {
            "author": "test",
            "created": "2024-01-01",
            "modified": "2024-01-02",
        },
    }

    cache.set("uuid-large", large_manifest)
    result = cache.get("uuid-large")
    assert result == large_manifest
    assert len(result["params"]) == 3
    assert len(result["tags"]) == 3


def test_manifest_isolation(cache):
    """Test that manifests are isolated and modifying one doesn't affect others."""
    manifest1 = {"uuid": "uuid-1", "name": "tool1", "tags": ["tag1"]}
    manifest2 = {"uuid": "uuid-2", "name": "tool2", "tags": ["tag2"]}

    cache.set("uuid-1", manifest1)
    cache.set("uuid-2", manifest2)

    # Get and modify manifest1
    retrieved1 = cache.get("uuid-1")
    retrieved1["tags"].append("newtag")

    # manifest2 should not be affected
    retrieved2 = cache.get("uuid-2")
    assert "newtag" not in retrieved2["tags"]
    assert retrieved2["tags"] == ["tag2"]


# Made with Bob
