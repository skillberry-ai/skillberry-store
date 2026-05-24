import pytest

from skillberry_store.modules.lookup_cache import LookupCache


@pytest.fixture
def cache():
    """Create a fresh LookupCache instance for each test."""
    return LookupCache()


def test_lookup_by_name_returns_none_for_nonexistent_name(cache):
    """Test that looking up a non-existent name returns None."""
    result = cache.get_head("nonexistent")
    assert result is None


def test_set_head_and_lookup_by_name(cache):
    """Test setting a HEAD and looking it up."""
    cache.set_head("mytool", "uuid-1")
    result = cache.get_head("mytool")
    assert result == "uuid-1"


def test_set_head_updates_existing_name(cache):
    """Test that setting HEAD for an existing name updates it."""
    cache.set_head("mytool", "uuid-1")
    cache.set_head("mytool", "uuid-2")
    result = cache.get_head("mytool")
    assert result == "uuid-2"


def test_get_all_names_empty_cache(cache):
    """Test getting all names from an empty cache."""
    names = cache.get_all_names()
    assert names == set()


def test_get_all_names_with_entries(cache):
    """Test getting all names from a cache with entries."""
    cache.set_head("tool1", "uuid-1")
    cache.set_head("tool2", "uuid-2")
    cache.set_head("snippet1", "uuid-3")
    
    names = cache.get_all_names()
    assert names == {"tool1", "tool2", "snippet1"}


def test_remove_name(cache):
    """Test removing a name from the cache."""
    cache.set_head("mytool", "uuid-1")
    assert cache.has_name("mytool")
    
    cache.remove_name("mytool")
    assert not cache.has_name("mytool")
    assert cache.get_head("mytool") is None


def test_remove_name_nonexistent(cache):
    """Test that removing a non-existent name doesn't raise an error."""
    cache.remove_name("nonexistent")  # Should not raise


def test_has_name(cache):
    """Test checking if a name exists in the cache."""
    assert not cache.has_name("mytool")
    
    cache.set_head("mytool", "uuid-1")
    assert cache.has_name("mytool")
    
    cache.remove_name("mytool")
    assert not cache.has_name("mytool")


def test_clear(cache):
    """Test clearing all entries from the cache."""
    cache.set_head("tool1", "uuid-1")
    cache.set_head("tool2", "uuid-2")
    cache.set_head("snippet1", "uuid-3")
    
    assert len(cache.get_all_names()) == 3
    
    cache.clear()
    assert len(cache.get_all_names()) == 0
    assert cache.get_head("tool1") is None


def test_version_chain_scenario(cache):
    """Test a git-like version chain scenario."""
    # Create version 1 of "mytool"
    cache.set_head("mytool", "uuid-v1")
    assert cache.get_head("mytool") == "uuid-v1"
    
    # Create version 2 of "mytool" (becomes new HEAD)
    cache.set_head("mytool", "uuid-v2")
    assert cache.get_head("mytool") == "uuid-v2"
    
    # Create version 3 of "mytool" (becomes new HEAD)
    cache.set_head("mytool", "uuid-v3")
    assert cache.get_head("mytool") == "uuid-v3"


def test_multiple_resources_different_names(cache):
    """Test managing multiple resources with different names."""
    cache.set_head("tool1", "tool1-uuid")
    cache.set_head("tool2", "tool2-uuid")
    cache.set_head("snippet1", "snippet1-uuid")
    
    assert cache.get_head("tool1") == "tool1-uuid"
    assert cache.get_head("tool2") == "tool2-uuid"
    assert cache.get_head("snippet1") == "snippet1-uuid"
    
    names = cache.get_all_names()
    assert names == {"tool1", "tool2", "snippet1"}


def test_name_change_scenario(cache):
    """Test scenario where an object name changes."""
    # Original object
    cache.set_head("oldname", "uuid-1")
    assert cache.get_head("oldname") == "uuid-1"
    
    # Resource renamed - becomes HEAD for new name
    cache.set_head("newname", "uuid-1")
    assert cache.get_head("newname") == "uuid-1"
    
    # Old name should be removed separately (done by update_cache_after_update)
    cache.remove_name("oldname")
    assert cache.get_head("oldname") is None


def test_delete_head_scenario(cache):
    """Test scenario where HEAD object is deleted."""
    # Create version chain: v1 -> v2 -> v3 (HEAD)
    cache.set_head("mytool", "uuid-v3")
    
    # Delete v3, v2 becomes HEAD
    cache.set_head("mytool", "uuid-v2")
    assert cache.get_head("mytool") == "uuid-v2"
    
    # Delete v2, v1 becomes HEAD
    cache.set_head("mytool", "uuid-v1")
    assert cache.get_head("mytool") == "uuid-v1"
    
    # Delete v1, no more resources with this name
    cache.remove_name("mytool")
    assert cache.get_head("mytool") is None


# Made with Bob
