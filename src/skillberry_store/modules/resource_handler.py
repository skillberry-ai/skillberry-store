"""Generic resource handler for managing resources (tools, snippets, skills, vmcp servers).

This module provides a unified interface for managing all resource types in the
skillberry-store system. Each resource is stored in a UUID-based subfolder with
a type-specific manifest file.
"""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Union

from fastapi import HTTPException

from skillberry_store.modules.dict_cache import DictCache
from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.lookup_cache import LookupCache
from skillberry_store.utils.utils import normalize_uuid

logger = logging.getLogger(__name__)

# Global dictionary to store singleton ResourceHandler instances
_resource_handlers: Dict[str, "ResourceHandler"] = {}
_initialized = False


def initialize_resource_handlers() -> None:
    """
    Initialize all resource handlers. Should be called once during server startup.
    
    This function is idempotent - calling it multiple times is safe and will only
    initialize once. All resource handlers are created and stored in a global
    dictionary for reuse throughout the application lifecycle.
    """
    global _initialized
    if _initialized:
        logger.warning("Resource handlers already initialized, skipping")
        return
    
    # Import here to avoid circular dependencies
    from skillberry_store.tools.configure import (
        get_tools_directory,
        get_snippets_directory,
        get_skills_directory,
        get_vmcp_directory,
        get_vnfs_directory,
    )
    
    _resource_handlers["tool"] = ResourceHandler(get_tools_directory(), "tool")
    _resource_handlers["snippet"] = ResourceHandler(get_snippets_directory(), "snippet")
    _resource_handlers["skill"] = ResourceHandler(get_skills_directory(), "skill")
    _resource_handlers["vmcp"] = ResourceHandler(get_vmcp_directory(), "vmcp")
    _resource_handlers["vnfs"] = ResourceHandler(get_vnfs_directory(), "vnfs")
    
    _initialized = True
    logger.info(f"Initialized {len(_resource_handlers)} resource handlers: {list(_resource_handlers.keys())}")


def get_resource_handler(resource_type: str) -> "ResourceHandler":
    """
    Get the singleton ResourceHandler for a given resource type.
    
    Args:
        resource_type: The type of resource ('tool', 'snippet', 'skill', 'vmcp', 'vnfs').
        
    Returns:
        ResourceHandler: The singleton ResourceHandler instance for the specified type.
        
    Raises:
        RuntimeError: If resource handlers have not been initialized.
        ValueError: If the resource type is not recognized.
    """
    if not _initialized:
        raise RuntimeError(
            "Resource handlers not initialized. Call initialize_resource_handlers() first."
        )
    
    if resource_type not in _resource_handlers:
        raise ValueError(
            f"Unknown resource type: '{resource_type}'. "
            f"Valid types: {list(_resource_handlers.keys())}"
        )
    
    return _resource_handlers[resource_type]


def clear_resource_handlers() -> None:
    """
    Clear all resource handlers. Useful for testing.
    
    This function resets the global state, allowing resource handlers to be
    reinitialized. Should primarily be used in test cleanup.
    """
    global _initialized
    _resource_handlers.clear()
    _initialized = False
    logger.debug("Cleared all resource handlers")



class ResourceHandler:
    """
    Generic handler for managing resources (tools, snippets, skills, vmcp servers).
    
    Each resource is stored in a UUID-based subfolder with:
    - A manifest file named {resource_type}.json (e.g., tool.json, snippet.json)
    - Optional additional files (e.g., module files for tools)
    
    The handler supports ID resolution, allowing resources to be accessed by either
    their UUID or their name.
    """
    
    def __init__(self, base_directory: str, resource_type: str, use_dict_cache: bool = True):
        """
        Initialize ResourceHandler.
        
        Args:
            base_directory: Base directory for resources (e.g., /tmp/tools)
            resource_type: Type of resource ('tool', 'snippet', 'skill', 'vmcp')
            use_dict_cache: If True, use in-memory dict cache for manifests (default: True)
        """
        self.base_directory = base_directory
        self.resource_type = resource_type
        self.file_handler = FileHandler(base_directory)
        self.manifest_filename = f"{resource_type}.json"
        
        # If enabled, use in-memory dict cache for manifests
        self.dict_cache = None
        if use_dict_cache:
            self.dict_cache = DictCache()
            self._initialize_dict_cache()

        # Initialize name lookup cache
        self.name_cache = LookupCache()
        self._initialize_name_cache()
      
        logger.info(f"Initialized ResourceHandler for {resource_type} at {base_directory} (dict_cache={'enabled' if use_dict_cache else 'disabled'})")
    
    # ==================== Cache Management Methods ====================
    
    def _initialize_name_cache(self):
        """Load all resource names and their HEAD UUIDs into the cache.
        
        This scans all resources once during initialization to build the cache.
        For each name, only the latest version (HEAD) is cached.
        """
        # Build a temporary map: name -> list of (uuid, parent) tuples
        name_to_resources: Dict[str, List[Tuple[str, Optional[str]]]] = {}
        
        for resource_dict in self.iter_manifests():
            uuid_val = resource_dict.get("uuid")
            name = resource_dict.get("name")
            parent = resource_dict.get("parent")
            
            if uuid_val and name:
                if name not in name_to_resources:
                    name_to_resources[name] = []
                name_to_resources[name].append((uuid_val, parent))
        
        # For each name, find the HEAD (resource with no children)
        for name, resources in name_to_resources.items():
            head_uuid = self._find_head_uuid(resources)
            if head_uuid:
                self.name_cache.set_head(name, head_uuid)
        
        logger.info(f"Initialized name cache for {self.resource_type} with {len(self.name_cache.get_all_names())} names")
    
    def _find_head_uuid(self, resources: List[Tuple[str, Optional[str]]]) -> Optional[str]:
        """Find the HEAD UUID from a list of (uuid, parent) tuples.
        
        The HEAD is the resource that is not a parent of any other resource.
        
        Args:
            resources: List of (uuid, parent) tuples
            
        Returns:
            UUID of the HEAD resource, or None if not found
        """
        # Build set of all parent UUIDs
        parent_uuids = {parent for _, parent in resources if parent}
        
        # Find UUID that is not anyone's parent
        for uuid_val, _ in resources:
            if uuid_val not in parent_uuids:
                return uuid_val
        
        # Fallback: if no clear HEAD, return first UUID
        return resources[0][0] if resources else None
    
    def _initialize_dict_cache(self):
        """Load all resource manifests into the dict cache.
        
        This scans all resources once during initialization to build the cache.
        All manifests are loaded into memory for fast access.
        
        Note: This uses direct disk I/O (not iter_resources) to avoid circular dependency.
        """

        assert self.dict_cache is not None
        self.dict_cache.clear()

        if not os.path.exists(self.base_directory):
            logger.info(f"Base directory {self.base_directory} does not exist, dict cache initialized empty")
            return
        
        for entry in os.listdir(self.base_directory):
            entry_path = os.path.join(self.base_directory, entry)
            
            # Skip if not a directory or not a valid UUID
            if not os.path.isdir(entry_path) or not self.is_valid_uuid(entry):
                continue
            
            # Read manifest from UUID folder directly (bypass cache)
            try:
                manifest_content = self.file_handler.read_file(
                    self.manifest_filename,
                    raw_content=True,
                    subdirectory=entry
                )
                if isinstance(manifest_content, str):
                    resource_dict = json.loads(manifest_content)
                    uuid_val = resource_dict.get("uuid")
                    if uuid_val:
                        self.dict_cache.set(uuid_val, resource_dict)
            except Exception as e:
                logger.warning(f"Could not read {self.resource_type} manifest for UUID {entry} during cache init: {e}")
        
        logger.info(f"Initialized dict cache for {self.resource_type} with {self.dict_cache.size()} manifests")
    
    def update_cache_after_create(self, uuid_val: str, name: str, parent: Optional[str]):
        """Update cache after creating a new resource.
        
        Args:
            uuid_val: UUID of the new resource
            name: Name of the new resource
            parent: Parent UUID (previous HEAD for this name)
        """
        # New resource becomes HEAD for its name
        self.name_cache.set_head(name, uuid_val)
        logger.debug(f"Cache updated after create: '{name}' -> {uuid_val}")
    
    def update_cache_after_update(self, uuid_val: str, new_name: str, old_name: Optional[str], old_parent: Optional[str]):
        """Update cache after updating a resource.
        
        Args:
            uuid_val: UUID of the updated resource
            new_name: New name of the resource
            old_name: Old name (if name changed)
            old_parent: Old parent UUID (for updating old name's HEAD if needed)
        """
        # Updated resource becomes HEAD for its (possibly new) name
        self.name_cache.set_head(new_name, uuid_val)
        
        # If name changed and this was HEAD for old name, update old name's HEAD
        if old_name and old_name != new_name:
            if self.name_cache.lookup_by_name(old_name) == uuid_val:
                # This was HEAD for old name, update to parent or remove
                if old_parent:
                    self.name_cache.set_head(old_name, old_parent)
                else:
                    self.name_cache.remove_name(old_name)
        
        logger.debug(f"Cache updated after update: '{new_name}' -> {uuid_val}")
    
    def update_cache_after_delete(self, uuid_val: str, name: str, parent: Optional[str]):
        """Update cache after deleting a resource and fix parent chains.
        
        When deleting a resource, we need to:
        1. Fix any resources that pointed to this resource as their parent
        2. Update the cache HEAD pointer if this was HEAD
        
        Args:
            uuid_val: UUID of the deleted resource
            name: Name of the deleted resource
            parent: Parent UUID (becomes new HEAD if this was HEAD)
        """
        # Fix parent chains: find the resource that points to deleted resource as parent
        # and update it to point to the deleted resource's parent instead
        self._fix_parent_chain_after_delete(uuid_val, parent, name)
        
        # If this was HEAD, update to parent or remove
        if self.name_cache.lookup_by_name(name) == uuid_val:
            if parent:
                self.name_cache.set_head(name, parent)
                logger.debug(f"Cache updated after delete: '{name}' -> {parent}")
            else:
                self.name_cache.remove_name(name)
                logger.debug(f"Cache removed after delete: '{name}' (no more resources)")
    
    def _fix_parent_chain_after_delete(self, deleted_uuid: str, deleted_parent: Optional[str], name: str):
        """Fix parent chain when a resource is deleted.
        
        Efficiently walks the chain from HEAD to find the resource that points
        to the deleted resource as its parent, and updates it.
        
        Args:
            deleted_uuid: UUID of the deleted resource
            deleted_parent: Parent of the deleted resource
            name: Name of the deleted resource
        """
        try:
            # Start from HEAD
            head_uuid = self.name_cache.lookup_by_name(name)
            if not head_uuid:
                return
            
            # Walk the chain from HEAD
            current_uuid = head_uuid
            while current_uuid:
                # Read current resource
                try:
                    current_resource = self.read_manifest(current_uuid)
                except Exception as e:
                    logger.warning(f"Could not read resource {current_uuid} while fixing chain: {e}")
                    break
                
                # Check if this resource points to the deleted resource
                current_parent = current_resource.get("parent")
                if current_parent == deleted_uuid:
                    # Found it! Update this resource to point to deleted resource's parent
                    current_resource["parent"] = deleted_parent
                    self.write_manifest(current_uuid, current_resource)
                    logger.info(f"Fixed parent chain: {current_uuid} now points to {deleted_parent} (was {deleted_uuid})")
                    return  # Done, only one resource can point to deleted resource
                
                # Move to next in chain
                current_uuid = current_parent
                
        except Exception as e:
            logger.warning(f"Error fixing parent chain after delete: {e}")
    
    # ==================== Core ID Resolution Methods ====================
    
    def is_valid_uuid(self, id_str: str) -> bool:
        """
        Check if a string is a valid UUID.
        
        Args:
            id_str: String to validate as UUID.
            
        Returns:
            bool: True if the string is a valid UUID, False otherwise.
        """
        return normalize_uuid(id_str) is not None
    
    def name_to_uuid(self, name: str) -> Optional[str]:
        """
        Translate a resource name to its UUID using the cache.
        
        This is a fast O(1) lookup that returns only the UUID without loading
        the full manifest from disk.
        
        Args:
            name: Resource name to search for.
            
        Returns:
            Optional[str]: The UUID of the HEAD resource with this name, or None if not found.
        """
        head_uuid = self.name_cache.lookup_by_name(name)
        if head_uuid:
            logger.debug(f"Resolved name '{name}' to UUID '{head_uuid}'")
        else:
            logger.debug(f"No {self.resource_type} found with name '{name}'")
        return head_uuid
    
    def lookup_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Look up a resource by its name using the cache.
        
        Args:
            name: Resource name to search for.
            
        Returns:
            Optional[Dict[str, Any]]: Resource dictionary if found, None otherwise.
        """
        # Fast O(1) lookup in cache
        head_uuid = self.name_cache.lookup_by_name(name)
        
        if not head_uuid:
            logger.debug(f"No {self.resource_type} found with name '{name}'")
            return None
        
        # Read the resource from disk
        try:
            resource_dict = self.read_manifest(head_uuid)
            logger.debug(f"Found {self.resource_type} with name '{name}' (UUID: {head_uuid})")
            return resource_dict
        except Exception as e:
            logger.error(f"Cache had UUID {head_uuid} for name '{name}' but failed to read: {e}")
            raise
    
    def resolve_to_uuid(self, uuid_or_name: str) -> Optional[str]:
        """
        Resolve an ID string to a UUID.
        
        If the ID is already a valid UUID, return it as-is (lowercased).
        If the ID is a name, look it up and return the resource's UUID.
        
        Args:
            uuid_or_name: Either a UUID or a resource name.
            
        Returns:
            Optional[str]: The resolved UUID if found, None otherwise.
        """
        # Check if it's already a valid UUID
        normalized = normalize_uuid(uuid_or_name)
        if normalized:
            return normalized
        
        # Try to resolve as a name using the cache (efficient, no disk I/O)
        resource_uuid = self.name_to_uuid(uuid_or_name)
        if resource_uuid:
            return normalize_uuid(resource_uuid)
        
        # Could not resolve
        logger.warning(f"Could not resolve ID '{uuid_or_name}' to a UUID")
        return None
    
    def resolve_to_uuid_or_error(self, uuid_or_name: str) -> str:
        """
        Resolve an ID string to a UUID, raising an error if not found.
        
        If the ID is already a valid UUID, return it as-is (lowercased).
        If the ID is a name, look it up and return the resource's UUID.
        If the ID cannot be resolved, raise HTTPException with 404.
        
        Args:
            uuid_or_name: Either a UUID or a resource name.
            
        Returns:
            str: The resolved UUID.
            
        Raises:
            HTTPException: If the ID cannot be resolved (404).
        """
        resolved_uuid = self.resolve_to_uuid(uuid_or_name)
        if not resolved_uuid:
            raise HTTPException(
                status_code=404,
                detail=f"{self.resource_type.capitalize()} with ID '{uuid_or_name}' not found"
            )
        return resolved_uuid
    
    def resolve_to_uuids_or_error(self, uuids_or_names: List[str]) -> List[str]:
        """
        Resolve a list of ID strings to UUIDs, raising an error if any cannot be resolved.
        
        This is a bulk version of resolve_to_uuid_or_error that fails fast if any
        ID cannot be resolved. All IDs must be resolvable for the operation to succeed.
        
        Args:
            uuids_or_names: List of UUIDs or resource names.
            
        Returns:
            List[str]: List of resolved UUIDs in the same order as input.
            
        Raises:
            HTTPException: If any ID cannot be resolved (404).
        """
        resolved_uuids = []
        for uuid_or_name in uuids_or_names:
            resolved_uuid = self.resolve_to_uuid(uuid_or_name)
            if not resolved_uuid:
                raise HTTPException(
                    status_code=404,
                    detail=f"{self.resource_type.capitalize()} with ID '{uuid_or_name}' not found"
                )
            resolved_uuids.append(resolved_uuid)
        return resolved_uuids
    
    # ==================== Path Management Methods ====================
    
    def get_resource_subfolder_path(self, resource_uuid: str) -> str:
        """
        Get the path to a resource's UUID-based sub-folder.
        
        All resource artifacts are stored in /{base_directory}/{uuid}/.
        
        Args:
            resource_uuid: The resource's UUID.
            
        Returns:
            str: Full path to the resource's sub-folder.
        """
        normalized = normalize_uuid(resource_uuid)
        if not normalized:
            raise ValueError(f"Invalid UUID: {resource_uuid}")
        return os.path.join(self.base_directory, normalized)
    
    def ensure_resource_subfolder(self, resource_uuid: str) -> str:
        """
        Ensure a resource's UUID-based sub-folder exists.
        
        Args:
            resource_uuid: The resource's UUID.
            
        Returns:
            str: Full path to the resource's sub-folder.
        """
        subfolder_path = self.get_resource_subfolder_path(resource_uuid)
        os.makedirs(subfolder_path, exist_ok=True)
        return subfolder_path
    
    def get_manifest_path(self, resource_uuid: str) -> str:
        """
        Get the full path to a resource's manifest file.
        
        Args:
            resource_uuid: The resource's UUID.
            
        Returns:
            str: Full path to the resource manifest file.
        """
        return os.path.join(
            self.get_resource_subfolder_path(resource_uuid),
            self.manifest_filename
        )
    
    def get_resource_file_path(self, resource_uuid: str, filename: str) -> str:
        """
        Get the full path to a file in the resource's sub-folder.
        
        Args:
            resource_uuid: The resource's UUID.
            filename: The filename.
            
        Returns:
            str: Full path to the file.
        """
        return os.path.join(
            self.get_resource_subfolder_path(resource_uuid),
            filename
        )
    
    # ==================== Manifest Operations ====================
    
    def read_manifest(self, resource_uuid: str) -> Dict[str, Any]:
        """
        Read a resource's manifest file.
        
        Uses dict cache if enabled, otherwise reads from disk.
        
        Args:
            resource_uuid: The resource's UUID.
            
        Returns:
            Dict[str, Any]: The manifest data as a dictionary.
            
        Raises:
            HTTPException: If manifest not found (404) or read fails (500).
        """
        # Try cache first if enabled
        if self.dict_cache:
            cached_manifest = self.dict_cache.get(resource_uuid)
            if cached_manifest is not None:
                logger.debug(f"Cache hit for {self.resource_type} UUID {resource_uuid}")
                return cached_manifest
            else:
                # Cache is authoritative - if not in cache, resource doesn't exist
                logger.debug(f"Cache miss for {self.resource_type} UUID {resource_uuid} - resource does not exist")
                raise HTTPException(
                    status_code=404,
                    detail=f"{self.resource_type.capitalize()} with UUID '{resource_uuid}' not found"
                )
        
        # Cache disabled - read from disk
        try:
            normalized = normalize_uuid(resource_uuid)
            if not normalized:
                raise ValueError(f"Invalid UUID: {resource_uuid}")
            manifest_content = self.file_handler.read_file(
                self.manifest_filename,
                raw_content=True,
                subdirectory=normalized
            )
            if not isinstance(manifest_content, str):
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid manifest content type for {self.resource_type}"
                )
            return json.loads(manifest_content)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reading manifest for {self.resource_type} UUID {resource_uuid}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error reading {self.resource_type} manifest: {str(e)}"
            )
    
    def write_manifest(self, resource_uuid: str, manifest_data: Dict[str, Any]) -> Dict:
        """
        Write a resource's manifest file.
        
        Updates dict cache if enabled.
        
        Args:
            resource_uuid: The resource's UUID.
            manifest_data: The manifest data to write.
            
        Returns:
            dict: Success message.
            
        Raises:
            HTTPException: If write fails (500).
        """
        try:
            normalized = normalize_uuid(resource_uuid)
            if not normalized:
                raise ValueError(f"Invalid UUID: {resource_uuid}")
            manifest_json = json.dumps(manifest_data, indent=4)
            result = self.file_handler.write_file_content(
                self.manifest_filename,
                manifest_json,
                subdirectory=normalized
            )
            
            # Update cache if enabled
            if self.dict_cache:
                self.dict_cache.set(resource_uuid, manifest_data)
                logger.debug(f"Updated dict cache for {self.resource_type} UUID {resource_uuid}")
            
            return result
        except Exception as e:
            logger.error(f"Error writing manifest for {self.resource_type} UUID {resource_uuid}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error writing {self.resource_type} manifest: {str(e)}"
            )
    
    def delete_resource_folder(self, resource_uuid: str) -> Dict:
        """
        Delete a resource's entire subfolder (including manifest and all files).
        
        Removes from dict cache if enabled.
        
        Args:
            resource_uuid: The resource's UUID.
            
        Returns:
            dict: Success message.
            
        Raises:
            HTTPException: If deletion fails (404 or 500).
        """
        try:
            normalized = normalize_uuid(resource_uuid)
            if not normalized:
                raise ValueError(f"Invalid UUID: {resource_uuid}")
            # Delete the entire UUID subfolder (contains manifest and any other files)
            result = self.file_handler.delete_subdirectory(normalized)
            
            # Remove from cache if enabled
            if self.dict_cache:
                self.dict_cache.remove(resource_uuid)
                logger.debug(f"Removed from dict cache: {self.resource_type} UUID {resource_uuid}")
            
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting {self.resource_type} UUID {resource_uuid}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting {self.resource_type}: {str(e)}"
            )
    
    # ==================== Resource File Operations ====================
    
    def read_resource_file(
        self,
        resource_uuid: str,
        filename: str,
        raw_content: bool = False
    ):
        """
        Read a file from the resource's sub-folder.
        
        Args:
            resource_uuid: The resource's UUID.
            filename: The name of the file to read.
            raw_content: If True, return raw content as string. If False, return FileResponse.
            
        Returns:
            str or FileResponse: File content.
            
        Raises:
            HTTPException: If file not found (404) or read fails (500).
        """
        normalized = normalize_uuid(resource_uuid)
        if not normalized:
            raise ValueError(f"Invalid UUID: {resource_uuid}")
        return self.file_handler.read_file(
            filename,
            raw_content=raw_content,
            subdirectory=normalized
        )
    
    def write_resource_file(
        self,
        resource_uuid: str,
        filename: str,
        content: Union[str, bytes]
    ) -> Dict:
        """
        Write a file to the resource's sub-folder.
        
        Args:
            resource_uuid: The resource's UUID.
            filename: The name of the file to write.
            content: The file content (string or bytes).
            
        Returns:
            dict: Success message.
            
        Raises:
            HTTPException: If write fails (500).
        """
        normalized = normalize_uuid(resource_uuid)
        if not normalized:
            raise ValueError(f"Invalid UUID: {resource_uuid}")
        if isinstance(content, str):
            return self.file_handler.write_file_content(
                filename,
                content,
                subdirectory=normalized
            )
        else:
            return self.file_handler.write_file(
                content,
                filename,
                subdirectory=normalized
            )
    
    def delete_resource_file(self, resource_uuid: str, filename: str) -> Dict:
        """
        Delete a file from the resource's sub-folder.
        
        Args:
            resource_uuid: The resource's UUID.
            filename: The name of the file to delete.
            
        Returns:
            dict: Success message.
            
        Raises:
            HTTPException: If file not found (404) or deletion fails (500).
        """
        normalized = normalize_uuid(resource_uuid)
        if not normalized:
            raise ValueError(f"Invalid UUID: {resource_uuid}")
        return self.file_handler.delete_file(
            filename,
            subdirectory=normalized
        )
    
    # ==================== Resource Management ====================
    
    def list_all_resources(self) -> List[Dict[str, Any]]:
        """
        List all resources of this type.
        
        Uses dict cache if enabled, otherwise reads from disk.
        
        Returns:
            List[Dict[str, Any]]: List of all resource manifest dictionaries.
            
        Raises:
            HTTPException: If listing fails (500).
        """
        try:
            # Use cache if enabled
            if self.dict_cache:
                return list(self.dict_cache.get_all_manifests().values())
            
            # Cache disabled - read from disk
            resources = []
            
            # Scan UUID folders in base directory
            if os.path.exists(self.base_directory):
                for entry in os.listdir(self.base_directory):
                    entry_path = os.path.join(self.base_directory, entry)
                    
                    # Skip if not a directory or not a valid UUID
                    if not os.path.isdir(entry_path) or not self.is_valid_uuid(entry):
                        continue
                    
                    # Read manifest from UUID folder
                    try:
                        manifest_content = self.file_handler.read_file(
                            self.manifest_filename,
                            raw_content=True,
                            subdirectory=entry
                        )
                        if isinstance(manifest_content, str):
                            resource_dict = json.loads(manifest_content)
                            resources.append(resource_dict)
                    except Exception as e:
                        logger.warning(f"Could not read {self.resource_type} manifest for UUID {entry}: {e}")
            
            return resources
        except Exception as e:
            logger.error(f"Error listing {self.resource_type}s: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error listing {self.resource_type}s: {str(e)}"
            )
    
    
    def get_available_resource_names(self) -> Set[str]:
        """
        Get a set of all available resource names using the cache.
        
        Returns:
            Set[str]: Set of resource names.
        """
        return self.name_cache.get_all_names()
    
    # ==================== Iterator Support ====================
    
    def iter_manifests(self) -> Iterator[Dict[str, Any]]:
        """
        Iterate over all resources of this type, yielding manifest dictionaries.
        
        Uses dict cache if enabled, otherwise reads from disk.
        
        Yields:
            Dict[str, Any]: Resource manifest dictionary.
        """
        # Use cache if enabled
        if self.dict_cache:
            for manifest in self.dict_cache.get_all_manifests().values():
                yield manifest
            return
        
        # Cache disabled - read from disk
        if not os.path.exists(self.base_directory):
            return
        
        for entry in os.listdir(self.base_directory):
            entry_path = os.path.join(self.base_directory, entry)
            
            # Skip if not a directory or not a valid UUID
            if not os.path.isdir(entry_path) or not self.is_valid_uuid(entry):
                continue
            
            # Read manifest from UUID folder
            try:
                manifest_content = self.file_handler.read_file(
                    self.manifest_filename,
                    raw_content=True,
                    subdirectory=entry
                )
                if isinstance(manifest_content, str):
                    resource_dict = json.loads(manifest_content)
                    yield resource_dict
            except Exception as e:
                logger.warning(f"Could not read {self.resource_type} manifest for UUID {entry}: {e}")
    
    def read_manifests(self, uuids: List[str]) -> List[Dict[str, Any]]:
        """
        Read multiple resource manifests by their UUIDs in a single operation.
        
        This is useful for batch operations, such as loading all tools for a VMCP server.
        All UUIDs must be valid and exist, otherwise an HTTPException is raised.
        
        Args:
            uuids: List of resource UUIDs.
            
        Returns:
            List[Dict[str, Any]]: List of resource manifest dictionaries.
            
        Raises:
            HTTPException: If any UUID is invalid or resource not found (404).
        """
        resources = []
        
        for uuid_val in uuids:
            # Validate UUID and read manifest (raises 404 if not found)
            normalized = normalize_uuid(uuid_val)
            if not normalized:
                raise HTTPException(
                    status_code=404,
                    detail=f"Invalid UUID: {uuid_val}"
                )
            resource = self.read_manifest(normalized)
            resources.append(resource)
        
        return resources
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """
        Make ResourceHandler itself iterable.
        
        Yields:
            Dict[str, Any]: Resource manifest dictionary.
        """
        return self.iter_manifests()
    
    # ==================== Utility Methods ====================
    
    def resource_exists(self, id_str: str) -> bool:
        """
        Check if a resource exists by ID (name or UUID).
        
        Args:
            id_str: The ID of the resource (can be either name or UUID).
            
        Returns:
            bool: True if the resource exists, False otherwise.
        """
        resource_uuid = self.resolve_to_uuid(id_str)
        if not resource_uuid:
            return False
        
        manifest_path = self.get_manifest_path(resource_uuid)
        return os.path.exists(manifest_path)
    
    def get_manifest_filename(self) -> str:
        """
        Get the manifest filename for this resource type.
        
        Returns:
            str: The manifest filename (e.g., 'tool.json', 'snippet.json').
        """
        return self.manifest_filename


# Made with Bob