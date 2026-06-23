"""Business logic for snippet CRUD operations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.utils.utils import generate_or_validate_uuid

if TYPE_CHECKING:
    from skillberry_store.modules.description import Description

logger = logging.getLogger(__name__)


class SnippetsService:
    """Service layer for snippet CRUD operations.
    
    Provides business logic for managing snippets, which are reusable text blocks
    that can be referenced by skills.
    
    Attributes:
        handler: ObjectHandler for snippet persistence operations.
        descriptions: Optional Description instance for semantic search indexing.
    """
    
    def __init__(
        self, handler: ObjectHandler, descriptions: Optional[Description] = None
    ):
        """Initialize the SnippetsService.
        
        Args:
            handler: ObjectHandler instance for snippet operations.
            descriptions: Optional Description instance for managing snippet descriptions.
        """
        self.handler = handler
        self.descriptions = descriptions

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        """Resolve a snippet identifier to its UUID.
        
        Args:
            uuid_or_name: Snippet UUID or name to resolve.
            
        Returns:
            str: The resolved UUID.
            
        Raises:
            KeyError: If snippet not found.
        """
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Snippet '{uuid_or_name}' not found")
            raise

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new snippet.
        
        Creates a snippet entry with text content and updates caches and indexes.
        
        Args:
            data: Snippet metadata dictionary (name, description, content, etc.).
            
        Returns:
            Dict[str, Any]: The created snippet data with UUID and timestamps.
            
        Raises:
            ValueError: If snippet with the same UUID already exists.
        """
        data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
        if self.handler.object_exists(data["uuid"]):
            raise ValueError(f"Snippet with UUID '{data['uuid']}' already exists")
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data["modified_at"] = now
        if data.get("name"):
            data["parent"] = self.handler.get_cache_parent_for_head(
                data["uuid"], data["name"]
            )
        self.handler.write_dict(data["uuid"], data)
        if data.get("name"):
            self.handler.update_cache(data["uuid"], new_name=data["name"])
        if self.descriptions and data.get("description"):
            self.descriptions.write_description(data["uuid"], data["description"])
        logger.info(f"Snippet '{data.get('name')}' created with UUID {data['uuid']}")
        return data

    def _safe_read(self, uuid: str, label: str) -> Dict[str, Any]:
        """Safely read a snippet dictionary with error handling.
        
        Args:
            uuid: Snippet UUID to read.
            label: Human-readable label for error messages.
            
        Returns:
            Dict[str, Any]: Snippet metadata dictionary.
            
        Raises:
            KeyError: If snippet not found.
        """
        try:
            return self.handler.read_dict(uuid)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Snippet '{label}' not found")
            raise

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        """Get snippet metadata by UUID or name.
        
        Args:
            uuid_or_name: Snippet UUID or name.
            
        Returns:
            Dict[str, Any]: Snippet metadata dictionary.
            
        Raises:
            KeyError: If snippet not found.
        """
        uuid = self._resolve_uuid(uuid_or_name)
        return self._safe_read(uuid, uuid_or_name)

    def list_all(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """List all snippets with optional filtering.
        
        Args:
            filters: Optional dictionary of field:value pairs to filter by.
            
        Returns:
            List[Dict[str, Any]]: List of snippet metadata dictionaries, sorted by modified_at descending.
        """
        items = self.handler.list_all_dicts()
        if filters:
            items = [i for i in items if all(i.get(k) == v for k, v in filters.items())]
        items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
        return items

    def update(self, uuid_or_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing snippet's metadata and content.
        
        Merges new data with existing snippet data, updates timestamps, caches,
        and description indexes as needed.
        
        Args:
            uuid_or_name: Snippet UUID or name to update.
            data: Dictionary of fields to update.
            
        Returns:
            Dict[str, Any]: The updated snippet metadata.
            
        Raises:
            KeyError: If snippet not found.
        """
        uuid = self._resolve_uuid(uuid_or_name)
        existing = self.handler.read_dict(uuid)
        old_name = existing.get("name")
        old_parent = existing.get("parent")
        new_name = data.get("name") or old_name
        if new_name:
            data["parent"] = self.handler.get_cache_parent_for_head(uuid, new_name)
        merged = {**existing, **data}
        merged["uuid"] = existing.get("uuid", uuid)
        merged["created_at"] = existing.get("created_at")
        merged["modified_at"] = datetime.now(timezone.utc).isoformat()
        self.handler.write_dict(uuid, merged)
        if new_name:
            self.handler.update_cache(
                uuid, new_name=new_name, old_name=old_name, old_parent=old_parent
            )
        if self.descriptions and merged.get("description"):
            self.descriptions.write_description(uuid, merged["description"])
        logger.info(f"Snippet '{uuid_or_name}' updated")
        return merged

    def delete(self, uuid_or_name: str) -> None:
        """Delete a snippet.
        
        Removes the snippet metadata, cache entries, and description indexes.
        
        Args:
            uuid_or_name: Snippet UUID or name to delete.
            
        Raises:
            KeyError: If snippet not found.
        """
        uuid = self._resolve_uuid(uuid_or_name)
        try:
            d = self.handler.read_dict(uuid)
            name, parent = d.get("name"), d.get("parent")
        except Exception:
            name, parent = None, None
        if uuid and name:
            self.handler.update_cache(
                uuid, new_name=None, old_name=name, old_parent=parent
            )
        self.handler.delete_object(uuid)
        if self.descriptions:
            try:
                self.descriptions.delete_description(uuid)
            except Exception as e:
                logger.warning(f"Could not delete snippet description for {uuid}: {e}")
        logger.info(f"Snippet '{uuid_or_name}' deleted")
