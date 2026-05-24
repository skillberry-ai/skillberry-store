import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class DictCache:
    """In-memory cache for object dicts.
    
    This cache stores complete object dicts in memory, mapping UUID to dict.
    It provides fast access to object data without disk I/O.
    
    Memory cost: Significantly higher than LookupCache as it stores full dict
    dictionaries (~2-10 KB per object) instead of just name-UUID mappings.
    """
    
    # UUID to dict mapping (e.g., "uuid-123" -> {"uuid": "uuid-123", "name": "mytool", ...})
    uuid_to_dict: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def get(self, uuid: str) -> Optional[Dict[str, Any]]:
        """Get an object dict by UUID.
        
        Args:
            uuid: Object UUID to look up
            
        Returns:
            Object dict if found, None if not in cache
        """
        return self.uuid_to_dict.get(uuid)
    
    def set(self, uuid: str, dict_data: Dict[str, Any]):
        """Store an object dict in the cache.
        
        Args:
            uuid: Object UUID
            dict_data: Complete object dict dictionary
        """
        self.uuid_to_dict[uuid] = dict_data
        logger.debug(f"DictCache: cached dict for UUID {uuid}")
    
    def remove(self, uuid: str):
        """Remove an object dict from the cache.
        
        Args:
            uuid: Object UUID to remove
        """
        if uuid in self.uuid_to_dict:
            self.uuid_to_dict.pop(uuid)
            logger.debug(f"DictCache: removed UUID {uuid}")
    
    def has(self, uuid: str) -> bool:
        """Check if a UUID exists in the cache.
        
        Args:
            uuid: Object UUID to check
            
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
    
    def get_all_dicts(self) -> Dict[str, Dict[str, Any]]:
        """Get all cached dicts.
        
        Returns:
            Dictionary mapping UUID to dict
        """
        return self.uuid_to_dict.copy()
    
    def clear(self):
        """Clear all cached dicts."""
        self.uuid_to_dict.clear()
        logger.debug("DictCache: cleared all dicts")
    
    def size(self) -> int:
        """Get the number of cached dicts.
        
        Returns:
            Number of dicts in cache
        """
        return len(self.uuid_to_dict)


# Made with Bob