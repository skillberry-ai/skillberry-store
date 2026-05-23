import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class DictCache:
    """In-memory cache for resource manifests (dicts).
    
    This cache stores complete resource manifests in memory, mapping UUID to dict.
    It provides fast access to resource data without disk I/O.
    
    Memory cost: Significantly higher than LookupCache as it stores full manifest
    dictionaries (~2-10 KB per resource) instead of just name-UUID mappings.
    """
    
    # UUID to manifest dict mapping (e.g., "uuid-123" -> {"uuid": "uuid-123", "name": "mytool", ...})
    uuid_to_dict: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def get(self, uuid: str) -> Optional[Dict[str, Any]]:
        """Get a resource manifest by UUID.
        
        Args:
            uuid: Resource UUID to look up
            
        Returns:
            Resource manifest dict if found, None if not in cache
        """
        return self.uuid_to_dict.get(uuid)
    
    def set(self, uuid: str, manifest: Dict[str, Any]):
        """Store a resource manifest in the cache.
        
        Args:
            uuid: Resource UUID
            manifest: Complete resource manifest dictionary
        """
        self.uuid_to_dict[uuid] = manifest
        logger.debug(f"DictCache: cached manifest for UUID {uuid}")
    
    def remove(self, uuid: str):
        """Remove a resource manifest from the cache.
        
        Args:
            uuid: Resource UUID to remove
        """
        if uuid in self.uuid_to_dict:
            self.uuid_to_dict.pop(uuid)
            logger.debug(f"DictCache: removed UUID {uuid}")
    
    def has(self, uuid: str) -> bool:
        """Check if a UUID exists in the cache.
        
        Args:
            uuid: Resource UUID to check
            
        Returns:
            True if UUID exists in cache, False otherwise
        """
        return uuid in self.uuid_to_dict
    
    def get_all_uuids(self) -> Set[str]:
        """Get all UUIDs in the cache.
        
        Returns:
            Set of all cached UUIDs
        """
        return set(self.uuid_to_dict.keys())
    
    def get_all_manifests(self) -> Dict[str, Dict[str, Any]]:
        """Get all cached manifests.
        
        Returns:
            Dictionary mapping UUID to manifest dict
        """
        return self.uuid_to_dict.copy()
    
    def clear(self):
        """Clear all cached manifests."""
        self.uuid_to_dict.clear()
        logger.debug("DictCache: cleared all manifests")
    
    def size(self) -> int:
        """Get the number of cached manifests.
        
        Returns:
            Number of manifests in cache
        """
        return len(self.uuid_to_dict)


# Made with Bob