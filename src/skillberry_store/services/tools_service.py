"""Business logic for tool CRUD and execution operations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from skillberry_store.modules.object_handler import ObjectHandler
from skillberry_store.modules.file_executor import detect_tool_dependencies
from skillberry_store.utils.utils import generate_or_validate_uuid
from skillberry_store.tools.configure import is_auto_detect_dependencies_enabled

if TYPE_CHECKING:
    from skillberry_store.modules.description import Description

logger = logging.getLogger(__name__)


class ToolsService:
    """Service layer for tool CRUD and execution operations.
    
    Provides business logic for managing tools including creation, retrieval,
    update, deletion, and dependency resolution. Handles both tool metadata
    and module files.
    
    Attributes:
        handler: ObjectHandler for tool persistence operations.
        descriptions: Optional Description instance for semantic search indexing.
    """
    
    def __init__(
        self, handler: ObjectHandler, descriptions: Optional[Description] = None
    ):
        """Initialize the ToolsService.
        
        Args:
            handler: ObjectHandler instance for tool operations.
            descriptions: Optional Description instance for managing tool descriptions.
        """
        self.handler = handler
        self.descriptions = descriptions

    def _resolve_uuid(self, uuid_or_name: str) -> str:
        """Resolve a tool identifier to its UUID.
        
        Args:
            uuid_or_name: Tool UUID or name to resolve.
            
        Returns:
            str: The resolved UUID.
            
        Raises:
            KeyError: If tool not found.
        """
        try:
            return self.handler.resolve_to_uuid_or_error(uuid_or_name)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Tool '{uuid_or_name}' not found")
            raise

    def find_dependencies(self, dependencies: List[str], tool_uuid: str) -> Set[str]:
        """Recursively resolve all transitive dependency UUIDs.
        
        Traverses the dependency tree to find all direct and indirect dependencies
        of a tool, avoiding circular dependencies.
        
        Args:
            dependencies: List of direct dependency UUIDs.
            tool_uuid: UUID of the tool being analyzed (for logging).
            
        Returns:
            Set[str]: Set of all dependency UUIDs (transitive closure).
        """
        found: Set[str] = set()
        if not dependencies:
            return found
        for dep_uuid in dependencies:
            if dep_uuid in found:
                continue
            found.add(dep_uuid)
            dep_dict = self.handler.read_dict(dep_uuid)
            nested = dep_dict.get("dependencies", [])
            if nested:
                found.update(self.find_dependencies(nested, dep_uuid))
        return found

    def create(
        self, data: Dict[str, Any], module_content: bytes, module_filename: str
    ) -> Dict[str, Any]:
        """Create a new tool with its module file.
        
        Creates a tool entry with metadata and saves the associated module file.
        Automatically detects dependencies if enabled and updates caches and indexes.
        
        Args:
            data: Tool metadata dictionary (name, description, params, etc.).
            module_content: Binary content of the tool's module file.
            module_filename: Filename for the module (e.g., "tool.py").
            
        Returns:
            Dict[str, Any]: The created tool data with UUID and timestamps.
            
        Raises:
            ValueError: If tool with the same UUID already exists.
        """
        data["uuid"] = generate_or_validate_uuid(data.get("uuid"))
        if self.handler.object_exists(data["uuid"]):
            raise ValueError(f"Tool with UUID '{data['uuid']}' already exists")
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data["modified_at"] = now
        if data.get("name"):
            data["parent"] = self.handler.get_cache_parent_for_head(
                data["uuid"], data["name"]
            )
        self.handler.write_file(data["uuid"], module_filename, module_content)
        data["module_name"] = module_filename
        if not data.get("dependencies") and is_auto_detect_dependencies_enabled():
            try:
                content_str = (
                    module_content.decode("utf-8")
                    if isinstance(module_content, bytes)
                    else module_content
                )
                available = self.handler.get_existing_names()
                detected_names = detect_tool_dependencies(
                    content_str, data["name"], available
                )
                if detected_names:
                    data["dependencies"] = [
                        self.handler.name_to_uuid(n) for n in detected_names
                    ]
            except Exception as e:
                logger.warning(f"Failed to auto-detect dependencies: {e}")
        self.handler.write_dict(data["uuid"], data)
        self.handler.update_cache(data["uuid"], new_name=data["name"])
        if self.descriptions and data.get("description"):
            self.descriptions.write_description(data["uuid"], data["description"])
        logger.info(f"Tool '{data.get('name')}' created with UUID {data['uuid']}")
        return data

    def _safe_read(self, uuid: str, label: str) -> Dict[str, Any]:
        """Safely read a tool dictionary with error handling.
        
        Args:
            uuid: Tool UUID to read.
            label: Human-readable label for error messages.
            
        Returns:
            Dict[str, Any]: Tool metadata dictionary.
            
        Raises:
            KeyError: If tool not found.
        """
        try:
            return self.handler.read_dict(uuid)
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code == 404:
                raise KeyError(f"Tool '{label}' not found")
            raise

    def get(self, uuid_or_name: str) -> Dict[str, Any]:
        """Get tool metadata by UUID or name.
        
        Args:
            uuid_or_name: Tool UUID or name.
            
        Returns:
            Dict[str, Any]: Tool metadata dictionary.
            
        Raises:
            KeyError: If tool not found.
        """
        uuid = self._resolve_uuid(uuid_or_name)
        return self._safe_read(uuid, uuid_or_name)

    def get_module(self, uuid_or_name: str) -> str:
        """Get the module file content for a tool.
        
        Args:
            uuid_or_name: Tool UUID or name.
            
        Returns:
            str: Module file content as string.
            
        Raises:
            KeyError: If tool not found or has no module file.
            RuntimeError: If module content type is invalid.
        """
        uuid = self._resolve_uuid(uuid_or_name)
        tool = self.handler.read_dict(uuid)
        module_name = tool.get("module_name")
        if not module_name:
            raise KeyError(f"Tool '{uuid_or_name}' has no module file")
        content = self.handler.read_file(uuid, module_name, raw_content=True)
        if not isinstance(content, str):
            raise RuntimeError(f"Invalid module content type for tool '{uuid_or_name}'")
        return content

    def list_all(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """List all tools with optional filtering.
        
        Args:
            filters: Optional dictionary of field:value pairs to filter by.
            
        Returns:
            List[Dict[str, Any]]: List of tool metadata dictionaries, sorted by modified_at descending.
        """
        items = self.handler.list_all_dicts()
        if filters:
            items = [i for i in items if all(i.get(k) == v for k, v in filters.items())]
        items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
        return items

    def update(self, uuid_or_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing tool's metadata.
        
        Merges new data with existing tool data, updates timestamps, caches,
        and description indexes as needed.
        
        Args:
            uuid_or_name: Tool UUID or name to update.
            data: Dictionary of fields to update.
            
        Returns:
            Dict[str, Any]: The updated tool metadata.
            
        Raises:
            KeyError: If tool not found.
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
        if self.descriptions and data.get("description"):
            old_desc = existing.get("description")
            if old_desc != data["description"]:
                try:
                    self.descriptions.delete_description(uuid)
                except Exception:
                    pass
                self.descriptions.write_description(uuid, data["description"])
        logger.info(f"Tool '{uuid_or_name}' updated")
        return merged

    def delete(self, uuid_or_name: str) -> None:
        """Delete a tool and its associated files.
        
        Removes the tool metadata, module files, cache entries, and description indexes.
        
        Args:
            uuid_or_name: Tool UUID or name to delete.
            
        Raises:
            KeyError: If tool not found.
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
                logger.warning(f"Could not delete tool description for {uuid}: {e}")
        logger.info(f"Tool '{uuid_or_name}' deleted")
