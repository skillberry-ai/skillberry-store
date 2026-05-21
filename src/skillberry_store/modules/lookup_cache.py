import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class LookupCache:
    """In-memory cache for efficient name-to-UUID lookups with version chains.
    
    This cache only stores name-to-UUID mappings (HEAD pointers) for fast lookups.
    Resource data is still read from disk when needed.
    """
    
    # Name to HEAD UUID mapping (e.g., "mytool" -> "uuid-c")
    name_to_head: Dict[str, str] = field(default_factory=dict)
    
    def lookup_by_name(self, name: str) -> Optional[str]:
        """Get the HEAD UUID for a given resource name.
        
        Args:
            name: Resource name to look up
            
        Returns:
            UUID string if found, None if no resource with that name exists
        """
        return self.name_to_head.get(name)
    
    def get_all_names(self) -> Set[str]:
        """Get all resource names in the cache.
        
        Returns:
            Set of all resource names
        """
        return set(self.name_to_head.keys())
    
    def set_head(self, name: str, uuid: str):
        """Set the HEAD UUID for a resource name.
        
        Args:
            name: Resource name
            uuid: UUID to set as HEAD for this name
        """
        self.name_to_head[name] = uuid
        logger.debug(f"Cache: set HEAD for '{name}' -> {uuid}")
    
    def remove_name(self, name: str):
        """Remove a name from the cache (when last resource with that name is deleted).
        
        Args:
            name: Resource name to remove
        """
        if name in self.name_to_head:
            self.name_to_head.pop(name)
            logger.debug(f"Cache: removed name '{name}'")
    
    def has_name(self, name: str) -> bool:
        """Check if a name exists in the cache.
        
        Args:
            name: Resource name to check
            
        Returns:
            True if name exists in cache, False otherwise
        """
        return name in self.name_to_head
    
    def clear(self):
        """Clear all cached mappings."""
        self.name_to_head.clear()
        logger.debug("Cache: cleared all mappings")


# Made with Bob
