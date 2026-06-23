"""Business logic for skill CRUD operations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.utils.utils import generate_or_validate_uuid

if TYPE_CHECKING:
    from skillberry_store.modules.description import Description

logger = logging.getLogger(__name__)


class SkillsService:
    """Service layer for skill CRUD operations.
    
    Provides business logic for managing skills, which are high-level compositions
    that group related tools and snippets together.
    
    Attributes:
        handler: ObjectHandler for skill persistence operations.
        tools_handler: ObjectHandler for resolving tool references.
        snippets_handler: ObjectHandler for resolving snippet references.
        descriptions: Optional Description instance for semantic search indexing.
    """
    
    def __init__(
        self,
        handler: ObjectHandler,
        tools_handler: ObjectHandler,
        snippets_handler: ObjectHandler,
        descriptions: Optional[Description] = None,
    ):
        """Initialize the SkillsService.
        
        Args:
            handler: ObjectHandler instance for skill operations.
            tools_handler: ObjectHandler instance for tool operations.
            snippets_handler: ObjectHandler instance for snippet operations.
            descriptions: Optional Description instance for managing skill descriptions.
        """
        self.handler = handler
        self.tools_handler = tools_handler
        self.snippets_handler = snippets_handler
        self.descriptions = descriptions

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        """Resolve a skill identifier to its UUID.
        
        Args:
            uuid_or_name: Skill UUID or name to resolve.
            
        Returns:
            str: The resolved UUID.
            
        Raises:
            KeyError: If skill not found.
        """
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Skill '{uuid_or_name}' not found")
            raise

    def populate_objects(self, skill_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Populate full tool and snippet objects from their UUIDs.
        
        Resolves tool_uuids and snippet_uuids to their complete metadata objects
        and adds them as 'tools' and 'snippets' lists in the skill dictionary.
        
        Args:
            skill_dict: Skill dictionary containing tool_uuids and snippet_uuids.
            
        Returns:
            Dict[str, Any]: The skill dictionary with 'tools' and 'snippets' populated.
            
        Raises:
            RuntimeError: If any referenced tool or snippet is missing or invalid.
        """
        if skill_dict.get("tool_uuids"):
            try:
                skill_dict["tools"] = self.tools_handler.read_dicts(
                    skill_dict["tool_uuids"]
                )
            except Exception as e:
                raise RuntimeError(
                    f"Skill '{skill_dict.get('name')}' references missing tools: {e}"
                )
        else:
            skill_dict["tools"] = []
        if skill_dict.get("snippet_uuids"):
            try:
                skill_dict["snippets"] = self.snippets_handler.read_dicts(
                    skill_dict["snippet_uuids"]
                )
            except Exception as e:
                raise RuntimeError(
                    f"Skill '{skill_dict.get('name')}' references missing snippets: {e}"
                )
        else:
            skill_dict["snippets"] = []
        return skill_dict

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new skill.
        
        Creates a skill entry with metadata and updates caches and indexes.
        Skills reference tools and snippets by their UUIDs.
        
        Args:
            data: Skill metadata dictionary (name, description, tool_uuids, snippet_uuids, etc.).
            
        Returns:
            Dict[str, Any]: The created skill data with UUID and timestamps.
            
        Raises:
            ValueError: If skill with the same UUID already exists.
        """
        data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
        if self.handler.object_exists(data["uuid"]):
            raise ValueError(f"Skill with UUID '{data['uuid']}' already exists")
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
        logger.info(f"Skill '{data.get('name')}' created with UUID {data['uuid']}")
        return data

    def _safe_read(self, uuid: str, label: str) -> Dict[str, Any]:
        """Safely read a skill dictionary with error handling.
        
        Args:
            uuid: Skill UUID to read.
            label: Human-readable label for error messages.
            
        Returns:
            Dict[str, Any]: Skill metadata dictionary.
            
        Raises:
            KeyError: If skill not found.
        """
        try:
            return self.handler.read_dict(uuid)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Skill '{label}' not found")
            raise

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        """Get skill metadata by UUID or name with populated tool and snippet objects.
        
        Args:
            uuid_or_name: Skill UUID or name.
            
        Returns:
            Dict[str, Any]: Skill metadata dictionary with 'tools' and 'snippets' populated.
            
        Raises:
            KeyError: If skill not found.
        """
        uuid = self._resolve_uuid(uuid_or_name)
        skill = self._safe_read(uuid, uuid_or_name)
        try:
            return self.populate_objects(skill)
        except RuntimeError as e:
            logger.warning(str(e))
            skill.setdefault("tools", [])
            skill.setdefault("snippets", [])
            return skill

    def list_all(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """List all skills with optional filtering and populated objects.
        
        Args:
            filters: Optional dictionary of field:value pairs to filter by.
            
        Returns:
            List[Dict[str, Any]]: List of skill metadata dictionaries with tools and snippets populated,
                                  sorted by modified_at descending.
        """
        items = self.handler.list_all_dicts()
        if filters:
            items = [i for i in items if all(i.get(k) == v for k, v in filters.items())]
        for item in items:
            try:
                self.populate_objects(item)
            except RuntimeError as e:
                logger.warning(str(e))
                item.setdefault("tools", [])
                item.setdefault("snippets", [])
        items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
        return items

    def update(self, uuid_or_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing skill's metadata.
        
        Merges new data with existing skill data, updates timestamps, caches,
        and description indexes as needed.
        
        Args:
            uuid_or_name: Skill UUID or name to update.
            data: Dictionary of fields to update.
            
        Returns:
            Dict[str, Any]: The updated skill metadata.
            
        Raises:
            KeyError: If skill not found.
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
        logger.info(f"Skill '{uuid_or_name}' updated")
        return merged

    def delete(self, uuid_or_name: str) -> None:
        """Delete a skill.
        
        Removes the skill metadata, cache entries, and description indexes.
        Does not delete referenced tools or snippets.
        
        Args:
            uuid_or_name: Skill UUID or name to delete.
            
        Raises:
            KeyError: If skill not found.
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
                logger.warning(f"Could not delete skill description for {uuid}: {e}")
        logger.info(f"Skill '{uuid_or_name}' deleted")
