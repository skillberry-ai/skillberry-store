"""Generic object handler for managing objects (tools, snippets, skills, vmcp servers).

This module provides a unified interface for managing all object types in the
skillberry-store system. Each object is stored in a UUID-based subfolder with
a type-specific dict file.
"""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Union

from fastapi import HTTPException

from skillberry_store.fast_api.changes import bump
from skillberry_store.modules.dict_cache import DictCache
from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.lookup_cache import LookupCache
from skillberry_store.utils.utils import normalize_uuid

logger = logging.getLogger(__name__)

# Global dictionary to store singleton ObjectHandler instances
_object_handlers: Dict[str, "ObjectHandler"] = {}
_initialized = False


def initialize_object_handlers() -> None:
    """
    Initialize all object handlers. Should be called once during server startup.

    This function is idempotent - calling it multiple times is safe and will only
    initialize once. All object handlers are created and stored in a global
    dictionary for reuse throughout the application lifecycle.
    """
    global _initialized
    if _initialized:
        logger.warning("Object handlers already initialized, skipping")
        return

    # Import here to avoid circular dependencies
    from skillberry_store.tools.configure import (
        get_tools_directory,
        get_snippets_directory,
        get_skills_directory,
        get_vmcp_directory,
        get_vnfs_directory,
    )

    _object_handlers["tool"] = ObjectHandler(get_tools_directory(), "tool")
    _object_handlers["snippet"] = ObjectHandler(get_snippets_directory(), "snippet")
    _object_handlers["skill"] = ObjectHandler(get_skills_directory(), "skill")
    _object_handlers["vmcp"] = ObjectHandler(get_vmcp_directory(), "vmcp")
    _object_handlers["vnfs"] = ObjectHandler(get_vnfs_directory(), "vnfs")

    _initialized = True
    logger.info(
        f"Initialized {len(_object_handlers)} object handlers: {list(_object_handlers.keys())}"
    )


def get_object_handler(object_type: str) -> "ObjectHandler":
    """
    Get the singleton ObjectHandler for a given object type.

    Args:
        object_type: The type of object ('tool', 'snippet', 'skill', 'vmcp', 'vnfs').

    Returns:
        ObjectHandler: The singleton ObjectHandler instance for the specified type.

    Raises:
        RuntimeError: If object handlers have not been initialized.
        ValueError: If the object type is not recognized.
    """
    if not _initialized:
        raise RuntimeError(
            "Object handlers not initialized. Call initialize_object_handlers() first."
        )

    if object_type not in _object_handlers:
        raise ValueError(
            f"Unknown object type: '{object_type}'. "
            f"Valid types: {list(_object_handlers.keys())}"
        )

    return _object_handlers[object_type]


def clear_object_handlers() -> None:
    """
    Clear all object handlers. Useful for testing.

    This function resets the global state, allowing object handlers to be
    reinitialized. Should primarily be used in test cleanup.
    """
    global _initialized
    _object_handlers.clear()
    _initialized = False
    logger.debug("Cleared all object handlers")


class ObjectHandler:
    """
    Generic handler for managing objects (tools, snippets, skills, vmcp servers).

    Each object is stored in a UUID-based subfolder with:
    - A dict file named {object_type}.json (e.g., tool.json, snippet.json)
    - Optional additional files (e.g., module files for tools)

    The handler supports ID resolution, allowing objects to be accessed by either
    their UUID or their name.
    """

    def __init__(
        self, base_directory: str, object_type: str, use_dict_cache: bool = True
    ):
        """
        Initialize ObjectHandler.

        Args:
            base_directory: Base directory for objects (e.g., /tmp/tools)
            object_type: Type of object ('tool', 'snippet', 'skill', 'vmcp')
            use_dict_cache: If True, use in-memory dict cache for dicts (default: True)
        """
        self.base_directory = base_directory
        self.object_type = object_type
        self.file_handler = FileHandler(base_directory)
        self.dict_filename = f"{object_type}.json"

        # If enabled, use in-memory dict cache for dicts
        self.dict_cache = None
        if use_dict_cache:
            self.dict_cache = DictCache()
            self._initialize_dict_cache()

        # Initialize name lookup cache
        self.name_cache = LookupCache()
        self._initialize_name_cache()

        logger.info(
            f"Initialized ObjectHandler for {object_type} at {base_directory} (dict_cache={'enabled' if use_dict_cache else 'disabled'})"
        )

    # ==================== Cache Management Methods ====================

    def _initialize_name_cache(self):
        """Load all object names and their HEAD UUIDs into the cache.

        This scans all objects once during initialization to build the cache.
        For each name, only the latest version (HEAD) is cached.
        """
        # Build a temporary map: name -> list of (uuid, parent) tuples
        name_to_objects: Dict[str, List[Tuple[str, Optional[str]]]] = {}

        for object_dict in self.iter_dicts():
            uuid_val = object_dict.get("uuid")
            name = object_dict.get("name")
            parent = object_dict.get("parent")

            if uuid_val and name:
                if name not in name_to_objects:
                    name_to_objects[name] = []
                name_to_objects[name].append((uuid_val, parent))

        # For each name, find the HEAD (object with no children)
        for name, objects in name_to_objects.items():
            head_uuid = self._find_head_uuid(objects)
            if head_uuid:
                self.name_cache.set_head(name, head_uuid)

        logger.info(
            f"Initialized name cache for {self.object_type} with {len(self.name_cache.get_all_names())} names"
        )

    def _find_head_uuid(
        self, objects: List[Tuple[str, Optional[str]]]
    ) -> Optional[str]:
        """Find the HEAD UUID from a list of (uuid, parent) tuples.

        The HEAD is the object that is not a parent of any other object.

        Args:
            objects: List of (uuid, parent) tuples

        Returns:
            UUID of the HEAD object, or None if not found
        """
        # Build set of all parent UUIDs
        parent_uuids = {parent for _, parent in objects if parent}

        # Find UUID that is not anyone's parent
        for uuid_val, _ in objects:
            if uuid_val not in parent_uuids:
                return uuid_val

        # Fallback: if no clear HEAD, return first UUID
        return objects[0][0] if objects else None

    def _initialize_dict_cache(self):
        """Load all object dicts into the dict cache.

        This scans all objects once during initialization to build the cache.
        All dicts are loaded into memory for fast access.

        Note: This uses direct disk I/O (not iter_objects) to avoid circular dependency.
        """

        assert self.dict_cache is not None
        self.dict_cache.clear()

        if not os.path.exists(self.base_directory):
            logger.info(
                f"Base directory {self.base_directory} does not exist, dict cache initialized empty"
            )
            return

        for entry in os.listdir(self.base_directory):
            entry_path = os.path.join(self.base_directory, entry)

            # Skip if not a directory or not a valid UUID
            if not os.path.isdir(entry_path) or not self.is_valid_uuid(entry):
                continue

            # Read dict from UUID folder directly (bypass cache)
            try:
                dict_content = self.file_handler.read_file(
                    self.dict_filename, raw_content=True, subdirectory=entry
                )
                if isinstance(dict_content, str):
                    object_dict = json.loads(dict_content)
                    uuid_val = object_dict.get("uuid")
                    if uuid_val:
                        self.dict_cache.set(uuid_val, object_dict)
            except Exception as e:
                logger.warning(
                    f"Could not read {self.object_type} dict for UUID {entry} during cache init: {e}"
                )

        logger.info(
            f"Initialized dict cache for {self.object_type} with {self.dict_cache.size()} dicts"
        )

    def get_cache_parent_for_head(self, uuid_val: str, name: str) -> Optional[str]:
        """Determine the correct parent for an object that will become HEAD.

        This method looks up the current HEAD for the given name and determines
        what the parent should be for the object that will become the new HEAD.

        Args:
            uuid_val: UUID of the object that will become HEAD
            name: Name of the object

        Returns:
            Optional[str]: The UUID that should be set as parent:
                - If no HEAD exists: None (first object with this name)
                - If HEAD exists and HEAD != uuid_val: HEAD UUID (new object replaces HEAD)
                - If HEAD == uuid_val: HEAD's current parent (object is already HEAD)
        """
        current_head = self.name_cache.get_head(name)

        if not current_head:
            # No existing HEAD - this is the first object with this name
            logger.debug(f"No existing HEAD for '{name}', parent will be None")
            return None

        if current_head != uuid_val:
            # Different object is HEAD - it becomes the parent
            logger.debug(
                f"Current HEAD for '{name}' is {current_head}, will become parent"
            )
            return current_head

        # This object is already HEAD - preserve its current parent
        try:
            current_dict = self.read_dict(uuid_val)
            current_parent = current_dict.get("parent")
            logger.debug(
                f"Object {uuid_val} is already HEAD for '{name}', preserving parent {current_parent}"
            )
            return current_parent
        except Exception as e:
            logger.warning(f"Could not read dict for {uuid_val} to get parent: {e}")
            return None

    def update_cache(
        self,
        uuid_val: str,
        new_name: Optional[str] = None,
        old_name: Optional[str] = None,
        old_parent: Optional[str] = None,
    ):
        """Update cache after any object operation (create/update/delete).

        This unified method handles cache updates for all operations using a two-step approach:
        1. If old_name is provided: Detach uuid from old_name chain
        2. If new_name is provided: Attach uuid as HEAD for new_name chain

        Args:
            uuid_val: UUID of the object (mandatory)
            new_name: New name for the object (None for delete operations)
            old_name: Old name of the object (None for create operations)
            old_parent: Old parent UUID (used when detaching from old chain)

        Usage:
            - CREATE: update_cache(uuid, new_name="tool1", old_name=None, old_parent=None)
            - UPDATE (same name): update_cache(uuid, new_name="tool1", old_name="tool1", old_parent="uuid-b")
            - UPDATE (name change): update_cache(uuid, new_name="tool2", old_name="tool1", old_parent="uuid-b")
            - DELETE: update_cache(uuid, new_name=None, old_name="tool1", old_parent="uuid-b")
        """
        # STEP 1: Detach from old chain (if old_name provided)
        if old_name:
            # Fix parent chains in dicts: find objects pointing to uuid and update them
            self._fix_parent_chain_after_delete(uuid_val, old_parent, old_name)

            # Update cache HEAD pointer for old_name
            if self.name_cache.get_head(old_name) == uuid_val:
                # This object was HEAD for old_name
                if old_parent:
                    self.name_cache.set_head(old_name, old_parent)
                    logger.debug(
                        f"Cache: detached {uuid_val} from '{old_name}', new HEAD is {old_parent}"
                    )
                else:
                    self.name_cache.remove_name(old_name)
                    logger.debug(f"Cache: removed '{old_name}' (no more objects)")

        # STEP 2: Attach to new chain (if new_name provided)
        if new_name:
            self.name_cache.set_head(new_name, uuid_val)
            logger.debug(f"Cache: set {uuid_val} as HEAD for '{new_name}'")

    def _fix_parent_chain_after_delete(
        self, deleted_uuid: str, deleted_parent: Optional[str], name: str
    ):
        """Fix parent chain when an object is deleted.

        Efficiently walks the chain from HEAD to find the object that points
        to the deleted object as its parent, and updates it.

        Args:
            deleted_uuid: UUID of the deleted object
            deleted_parent: Parent of the deleted object
            name: Name of the deleted object

        Raises:
            HTTPException: If unable to read an object in the chain (500).
        """
        # Start from HEAD
        head_uuid = self.name_cache.get_head(name)
        if not head_uuid:
            return

        # Walk the chain from HEAD
        current_uuid = head_uuid
        while current_uuid:
            # Read current object - if this fails, it's a data integrity error
            try:
                current_object = self.read_dict(current_uuid)
            except Exception as e:
                error_msg = f"Data integrity error: Could not read {self.object_type} {current_uuid} while fixing parent chain for '{name}': {e}"
                logger.error(error_msg)
                raise HTTPException(
                    status_code=500,
                    detail=f"Internal error while updating {self.object_type} chain: {str(e)}",
                )

            # Check if this object points to the deleted object
            current_parent = current_object.get("parent")
            if current_parent == deleted_uuid:
                # Found it! Update this object to point to deleted object's parent
                current_object["parent"] = deleted_parent
                self.write_dict(current_uuid, current_object)
                logger.info(
                    f"Fixed parent chain: {current_uuid} now points to {deleted_parent} (was {deleted_uuid})"
                )
                return  # Done, only one object can point to deleted object

            # Move to next in chain
            current_uuid = current_parent

    # ==================== Core ID Resolution Methods ====================

    def is_valid_uuid(self, uuid_or_name: str) -> bool:
        """
        Check if a string is a valid UUID.

        Args:
            uuid_or_name: String to validate as UUID.

        Returns:
            bool: True if the string is a valid UUID, False otherwise.
        """
        return normalize_uuid(uuid_or_name) is not None

    def name_to_uuid(self, name: str) -> Optional[str]:
        """
        Translate an object name to its UUID using the cache.

        This is a fast O(1) lookup that returns only the UUID without loading
        the full dict from disk.

        Args:
            name: Object name to search for.

        Returns:
            Optional[str]: The UUID of the HEAD object with this name, or None if not found.
        """
        head_uuid = self.name_cache.get_head(name)
        if head_uuid:
            logger.debug(f"Resolved name '{name}' to UUID '{head_uuid}'")
        else:
            logger.debug(f"No {self.object_type} found with name '{name}'")
        return head_uuid

    def lookup_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Look up an object by its name using the cache.

        Args:
            name: Object name to search for.

        Returns:
            Optional[Dict[str, Any]]: Object dictionary if found, None otherwise.
        """
        # Fast O(1) lookup in cache
        head_uuid = self.name_cache.get_head(name)

        if not head_uuid:
            logger.debug(f"No {self.object_type} found with name '{name}'")
            return None

        # Read the object from disk
        try:
            object_dict = self.read_dict(head_uuid)
            logger.debug(
                f"Found {self.object_type} with name '{name}' (UUID: {head_uuid})"
            )
            return object_dict
        except Exception as e:
            logger.error(
                f"Cache had UUID {head_uuid} for name '{name}' but failed to read: {e}"
            )
            raise

    def resolve_to_uuid(self, uuid_or_name: str) -> Optional[str]:
        """
        Resolve an ID string to a UUID.

        If the ID is already a valid UUID, return it as-is (lowercased).
        If the ID is a name, look it up and return the object's UUID.

        Args:
            uuid_or_name: Either a UUID or an object name.

        Returns:
            Optional[str]: The resolved UUID if found, None otherwise.
        """
        # Check if it's already a valid UUID
        normalized = normalize_uuid(uuid_or_name)
        if normalized:
            return normalized

        # Try to resolve as a name using the cache (efficient, no disk I/O)
        object_uuid = self.name_to_uuid(uuid_or_name)
        if object_uuid:
            return normalize_uuid(object_uuid)

        # Could not resolve
        logger.warning(f"Could not resolve ID '{uuid_or_name}' to a UUID")
        return None

    def resolve_to_uuid_or_error(self, uuid_or_name: str) -> str:
        """
        Resolve an ID string to a UUID, raising an error if not found.

        If the ID is already a valid UUID, return it as-is (lowercased).
        If the ID is a name, look it up and return the object's UUID.
        If the ID cannot be resolved, raise HTTPException with 404.

        Args:
            uuid_or_name: Either a UUID or an object name.

        Returns:
            str: The resolved UUID.

        Raises:
            HTTPException: If the ID cannot be resolved (404).
        """
        resolved_uuid = self.resolve_to_uuid(uuid_or_name)
        if not resolved_uuid:
            raise HTTPException(
                status_code=404,
                detail=f"{self.object_type.capitalize()} with ID '{uuid_or_name}' not found",
            )
        return resolved_uuid

    def resolve_to_uuids_or_error(self, uuids_or_names: List[str]) -> List[str]:
        """
        Resolve a list of ID strings to UUIDs, raising an error if any cannot be resolved.

        This is a bulk version of resolve_to_uuid_or_error that fails fast if any
        ID cannot be resolved. All IDs must be resolvable for the operation to succeed.

        Args:
            uuids_or_names: List of UUIDs or object names.

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
                    detail=f"{self.object_type.capitalize()} with ID '{uuid_or_name}' not found",
                )
            resolved_uuids.append(resolved_uuid)
        return resolved_uuids

    # ==================== Path Management Methods ====================

    def get_object_path(self, uuid: str) -> str:
        """
        Get the path to an object's UUID-based sub-folder.

        All object artifacts are stored in /{base_directory}/{uuid}/.

        Args:
            uuid: The object's UUID.

        Returns:
            str: Full path to the object's sub-folder.
        """
        normalized = normalize_uuid(uuid)
        if not normalized:
            raise ValueError(f"Invalid UUID: {uuid}")
        return os.path.join(self.base_directory, normalized)

    def ensure_object_path(self, uuid: str) -> str:
        """
        Ensure an object's UUID-based sub-folder exists.

        Args:
            uuid: The object's UUID.

        Returns:
            str: Full path to the object's sub-folder.
        """
        subfolder_path = self.get_object_path(uuid)
        os.makedirs(subfolder_path, exist_ok=True)
        return subfolder_path

    def get_dict_path(self, uuid: str) -> str:
        """
        Get the full path to an object's dict file.

        Args:
            uuid: The object's UUID.

        Returns:
            str: Full path to the object dict file.
        """
        return os.path.join(self.get_object_path(uuid), self.dict_filename)

    def get_file_path(self, uuid: str, filename: str) -> str:
        """
        Get the full path to a file in the object's sub-folder.

        Args:
            uuid: The object's UUID.
            filename: The filename.

        Returns:
            str: Full path to the file.
        """
        return os.path.join(self.get_object_path(uuid), filename)

    # ==================== Dict Operations ====================

    def read_dict(self, uuid: str) -> Dict[str, Any]:
        """
        Read an object's dict file.

        Uses dict cache if enabled, otherwise reads from disk.

        Args:
            uuid: The object's UUID.

        Returns:
            Dict[str, Any]: The dict data as a dictionary.

        Raises:
            HTTPException: If dict not found (404) or read fails (500).
        """
        # Try cache first if enabled
        if self.dict_cache:
            cached_dict = self.dict_cache.get(uuid)
            if cached_dict is not None:
                logger.debug(f"Cache hit for {self.object_type} UUID {uuid}")
                return cached_dict
            else:
                # Cache is authoritative - if not in cache, object doesn't exist
                logger.debug(
                    f"Cache miss for {self.object_type} UUID {uuid} - object does not exist"
                )
                raise HTTPException(
                    status_code=404,
                    detail=f"{self.object_type.capitalize()} with UUID '{uuid}' not found",
                )

        # Cache disabled - read from disk
        try:
            normalized = normalize_uuid(uuid)
            if not normalized:
                raise ValueError(f"Invalid UUID: {uuid}")
            dict_content = self.file_handler.read_file(
                self.dict_filename, raw_content=True, subdirectory=normalized
            )
            if not isinstance(dict_content, str):
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid dict content type for {self.object_type}",
                )
            return json.loads(dict_content)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reading dict for {self.object_type} UUID {uuid}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error reading {self.object_type} dict: {str(e)}",
            )

    def write_dict(self, uuid: str, dict_data: Dict[str, Any]) -> Dict:
        """
        Write an object's dict file.

        Updates dict cache if enabled.

        Args:
            uuid: The object's UUID.
            dict_data: The dict data to write.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If write fails (500).
        """
        try:
            normalized = normalize_uuid(uuid)
            if not normalized:
                raise ValueError(f"Invalid UUID: {uuid}")
            dict_json = json.dumps(dict_data, indent=4)
            result = self.file_handler.write_file_content(
                self.dict_filename, dict_json, subdirectory=normalized
            )

            # Update cache if enabled
            if self.dict_cache:
                self.dict_cache.set(uuid, dict_data)
                logger.debug(f"Updated dict cache for {self.object_type} UUID {uuid}")

            bump()
            return result
        except Exception as e:
            logger.error(f"Error writing dict for {self.object_type} UUID {uuid}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error writing {self.object_type} dict: {str(e)}",
            )

    def delete_object(self, uuid: str) -> Dict:
        """
        Delete an object's entire subfolder (including dict and all files).

        Removes from dict cache if enabled.

        Args:
            uuid: The object's UUID.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If deletion fails (404 or 500).
        """
        try:
            normalized = normalize_uuid(uuid)
            if not normalized:
                raise ValueError(f"Invalid UUID: {uuid}")
            # Delete the entire UUID subfolder (contains dict and any other files)
            result = self.file_handler.delete_subdirectory(normalized)

            # Remove from cache if enabled
            if self.dict_cache:
                self.dict_cache.remove(uuid)
                logger.debug(f"Removed from dict cache: {self.object_type} UUID {uuid}")

            bump()
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting {self.object_type} UUID {uuid}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting {self.object_type}: {str(e)}"
            )

    # ==================== Object File Operations ====================

    def read_file(self, uuid: str, filename: str, raw_content: bool = False):
        """
        Read a file from the object's sub-folder.

        Args:
            uuid: The object's UUID.
            filename: The name of the file to read.
            raw_content: If True, return raw content as string. If False, return FileResponse.

        Returns:
            str or FileResponse: File content.

        Raises:
            HTTPException: If file not found (404) or read fails (500).
        """
        normalized = normalize_uuid(uuid)
        if not normalized:
            raise ValueError(f"Invalid UUID: {uuid}")
        return self.file_handler.read_file(
            filename, raw_content=raw_content, subdirectory=normalized
        )

    def write_file(self, uuid: str, filename: str, content: Union[str, bytes]) -> Dict:
        """
        Write a file to the object's sub-folder.

        Args:
            uuid: The object's UUID.
            filename: The name of the file to write.
            content: The file content (string or bytes).

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If write fails (500).
        """
        normalized = normalize_uuid(uuid)
        if not normalized:
            raise ValueError(f"Invalid UUID: {uuid}")
        if isinstance(content, str):
            return self.file_handler.write_file_content(
                filename, content, subdirectory=normalized
            )
        else:
            return self.file_handler.write_file(
                content, filename, subdirectory=normalized
            )

    def delete_file(self, uuid: str, filename: str) -> Dict:
        """
        Delete a file from the object's sub-folder.

        Args:
            uuid: The object's UUID.
            filename: The name of the file to delete.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If file not found (404) or deletion fails (500).
        """
        normalized = normalize_uuid(uuid)
        if not normalized:
            raise ValueError(f"Invalid UUID: {uuid}")
        return self.file_handler.delete_file(filename, subdirectory=normalized)

    # ==================== Object Management ====================

    def list_all_dicts(self) -> List[Dict[str, Any]]:
        """
        List all objects of this type.

        Uses dict cache if enabled, otherwise reads from disk.

        Returns:
            List[Dict[str, Any]]: List of all object dict dictionaries.

        Raises:
            HTTPException: If listing fails (500).
        """
        try:
            # Use cache if enabled
            if self.dict_cache:
                return list(self.dict_cache.get_all_dicts().values())

            # Cache disabled - read from disk
            objects = []

            # Scan UUID folders in base directory
            if os.path.exists(self.base_directory):
                for entry in os.listdir(self.base_directory):
                    entry_path = os.path.join(self.base_directory, entry)

                    # Skip if not a directory or not a valid UUID
                    if not os.path.isdir(entry_path) or not self.is_valid_uuid(entry):
                        continue

                    # Read dict from UUID folder
                    try:
                        dict_content = self.file_handler.read_file(
                            self.dict_filename, raw_content=True, subdirectory=entry
                        )
                        if isinstance(dict_content, str):
                            object_dict = json.loads(dict_content)
                            objects.append(object_dict)
                    except Exception as e:
                        logger.warning(
                            f"Could not read {self.object_type} dict for UUID {entry}: {e}"
                        )

            return objects
        except Exception as e:
            logger.error(f"Error listing {self.object_type}s: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing {self.object_type}s: {str(e)}"
            )

    def get_existing_names(self) -> Set[str]:
        """
        Get a set of all existing object names using the cache.

        Returns:
            Set[str]: Set of object names.
        """
        return self.name_cache.get_all_names()

    # ==================== Iterator Support ====================

    def iter_dicts(self) -> Iterator[Dict[str, Any]]:
        """
        Iterate over all objects of this type, yielding dict dictionaries.

        Uses dict cache if enabled, otherwise reads from disk.

        Yields:
            Dict[str, Any]: Object dict dictionary.
        """
        # Use cache if enabled
        if self.dict_cache:
            for dict_data in self.dict_cache.get_all_dicts().values():
                yield dict_data
            return

        # Cache disabled - read from disk
        if not os.path.exists(self.base_directory):
            return

        for entry in os.listdir(self.base_directory):
            entry_path = os.path.join(self.base_directory, entry)

            # Skip if not a directory or not a valid UUID
            if not os.path.isdir(entry_path) or not self.is_valid_uuid(entry):
                continue

            # Read dict from UUID folder
            try:
                dict_content = self.file_handler.read_file(
                    self.dict_filename, raw_content=True, subdirectory=entry
                )
                if isinstance(dict_content, str):
                    object_dict = json.loads(dict_content)
                    yield object_dict
            except Exception as e:
                logger.warning(
                    f"Could not read {self.object_type} dict for UUID {entry}: {e}"
                )

    def read_dicts(self, uuids: List[str]) -> List[Dict[str, Any]]:
        """
        Read multiple object dicts by their UUIDs in a single operation.

        This is useful for batch operations, such as loading all tools for a VMCP server.
        All UUIDs must be valid and exist, otherwise an HTTPException is raised.

        Args:
            uuids: List of object UUIDs.

        Returns:
            List[Dict[str, Any]]: List of object dict dictionaries.

        Raises:
            HTTPException: If any UUID is invalid or object not found (404).
        """
        objects = []

        for uuid_val in uuids:
            # Validate UUID and read dict (raises 404 if not found)
            normalized = normalize_uuid(uuid_val)
            if not normalized:
                raise HTTPException(status_code=404, detail=f"Invalid UUID: {uuid_val}")
            object_data = self.read_dict(normalized)
            objects.append(object_data)

        return objects

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """
        Make ObjectHandler itself iterable.

        Yields:
            Dict[str, Any]: Object dict dictionary.
        """
        return self.iter_dicts()

    # ==================== Utility Methods ====================

    def object_exists(self, uuid_or_name: str) -> bool:
        """
        Check if an object exists by ID (name or UUID).

        Args:
            uuid_or_name: The ID of the object (can be either name or UUID).

        Returns:
            bool: True if the object exists, False otherwise.
        """
        object_uuid = self.resolve_to_uuid(uuid_or_name)
        if not object_uuid:
            return False

        dict_path = self.get_dict_path(object_uuid)
        return os.path.exists(dict_path)

    def get_dict_filename(self) -> str:
        """
        Get the dict filename for this object type.

        Returns:
            str: The dict filename (e.g., 'tool.json', 'snippet.json').
        """
        return self.dict_filename


# Made with Bob
