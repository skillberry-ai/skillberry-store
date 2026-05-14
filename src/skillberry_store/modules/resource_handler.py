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
from typing import Any, Dict, Iterator, List, Optional, Set, Union

from fastapi import HTTPException

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.utils.utils import normalize_uuid

logger = logging.getLogger(__name__)


class ResourceHandler:
    """
    Generic handler for managing resources (tools, snippets, skills, vmcp servers).
    
    Each resource is stored in a UUID-based subfolder with:
    - A manifest file named {resource_type}.json (e.g., tool.json, snippet.json)
    - Optional additional files (e.g., module files for tools)
    
    The handler supports ID resolution, allowing resources to be accessed by either
    their UUID or their name.
    """
    
    def __init__(self, base_directory: str, resource_type: str):
        """
        Initialize ResourceHandler.
        
        Args:
            base_directory: Base directory for resources (e.g., /tmp/tools)
            resource_type: Type of resource ('tool', 'snippet', 'skill', 'vmcp')
        """
        self.base_directory = base_directory
        self.resource_type = resource_type
        self.file_handler = FileHandler(base_directory)
        self.manifest_filename = f"{resource_type}.json"
        logger.info(f"Initialized ResourceHandler for {resource_type} at {base_directory}")
    
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
    
    def lookup_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Look up a resource by its name.
        
        Searches through all UUID folders and returns the first resource whose name matches.
        
        Args:
            name: Resource name to search for.
            
        Returns:
            Optional[Dict[str, Any]]: Resource dictionary if found, None otherwise.
        """
        base_path = Path(self.base_directory)
        
        if not base_path.exists():
            return None
        
        for entry_path in base_path.iterdir():
            # Skip if not a directory or not a valid UUID
            if not entry_path.is_dir() or not self.is_valid_uuid(entry_path.name):
                continue
            
            manifest_path = entry_path / self.manifest_filename
            if not manifest_path.exists():
                continue
            
            try:
                with manifest_path.open('r') as f:
                    resource_dict = json.load(f)
                
                if resource_dict.get("name") == name:
                    logger.debug(f"Found {self.resource_type} with name '{name}' in UUID folder {entry_path.name}")
                    return resource_dict
                    
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON in {manifest_path}")
            except Exception as e:
                logger.warning(f"Error reading {manifest_path}: {e}")
        
        logger.debug(f"No {self.resource_type} found with name '{name}'")
        return None
    
    def resolve_id(self, id_str: str) -> Optional[str]:
        """
        Resolve an ID string to a UUID.
        
        If the ID is already a valid UUID, return it as-is (lowercased).
        If the ID is a name, look it up and return the resource's UUID.
        
        Args:
            id_str: Either a UUID or a resource name.
            
        Returns:
            Optional[str]: The resolved UUID if found, None otherwise.
        """
        # Check if it's already a valid UUID
        normalized = normalize_uuid(id_str)
        if normalized:
            return normalized
        
        # Try to resolve as a name
        resource = self.lookup_by_name(id_str)
        if resource and resource.get("uuid"):
            resource_uuid = resource["uuid"]
            logger.debug(f"Resolved name '{id_str}' to UUID '{resource_uuid}'")
            return normalize_uuid(resource_uuid)
        
        # Could not resolve
        logger.warning(f"Could not resolve ID '{id_str}' to a UUID")
        return None
    
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
        
        Args:
            resource_uuid: The resource's UUID.
            
        Returns:
            Dict[str, Any]: The manifest data as a dictionary.
            
        Raises:
            HTTPException: If manifest not found (404) or read fails (500).
        """
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
            return self.file_handler.write_file_content(
                self.manifest_filename,
                manifest_json,
                subdirectory=normalized
            )
        except Exception as e:
            logger.error(f"Error writing manifest for {self.resource_type} UUID {resource_uuid}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error writing {self.resource_type} manifest: {str(e)}"
            )
    
    def delete_resource_folder(self, resource_uuid: str) -> Dict:
        """
        Delete a resource's entire subfolder (including manifest and all files).
        
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
            return self.file_handler.delete_subdirectory(normalized)
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
        
        Returns:
            List[Dict[str, Any]]: List of all resource manifest dictionaries.
            
        Raises:
            HTTPException: If listing fails (500).
        """
        try:
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
    
    def get_resource_by_id(self, id_str: str) -> Dict[str, Any]:
        """
        Get a specific resource by ID (name or UUID).
        
        Args:
            id_str: The ID of the resource (can be either name or UUID).
            
        Returns:
            Dict[str, Any]: The resource manifest dictionary.
            
        Raises:
            HTTPException: If resource not found (404) or retrieval fails (500).
        """
        # Resolve ID to UUID
        resource_uuid = self.resolve_id(id_str)
        if not resource_uuid:
            raise HTTPException(
                status_code=404,
                detail=f"{self.resource_type.capitalize()} with ID '{id_str}' not found"
            )
        
        # Read and return the manifest
        return self.read_manifest(resource_uuid)
    
    def delete_resource_by_id(self, id_str: str) -> Dict:
        """
        Delete a resource by ID (name or UUID).
        
        Args:
            id_str: The ID of the resource to delete (can be either name or UUID).
            
        Returns:
            dict: Success message.
            
        Raises:
            HTTPException: If resource not found (404) or deletion fails (500).
        """
        # Resolve ID to UUID
        resource_uuid = self.resolve_id(id_str)
        if not resource_uuid:
            raise HTTPException(
                status_code=404,
                detail=f"{self.resource_type.capitalize()} with ID '{id_str}' not found"
            )
        
        # Delete the resource folder
        return self.delete_resource_folder(resource_uuid)
    
    def get_available_resource_names(self) -> Set[str]:
        """
        Get a set of all available resource names by scanning UUID folders.
        
        Returns:
            Set[str]: Set of resource names.
        """
        available_names = set()
        
        if not os.path.exists(self.base_directory):
            return available_names
        
        try:
            for entry in os.listdir(self.base_directory):
                entry_path = os.path.join(self.base_directory, entry)
                
                # Skip if not a directory or not a valid UUID
                if not os.path.isdir(entry_path) or not self.is_valid_uuid(entry):
                    continue
                
                try:
                    manifest_content = self.file_handler.read_file(
                        self.manifest_filename,
                        raw_content=True,
                        subdirectory=entry
                    )
                    if isinstance(manifest_content, str):
                        resource_dict = json.loads(manifest_content)
                        if resource_dict.get('name'):
                            available_names.add(resource_dict['name'])
                except Exception as e:
                    logger.warning(f"Could not read {self.resource_type} name from UUID {entry}: {e}")
                    
        except Exception as e:
            logger.error(f"Error getting available {self.resource_type} names: {e}")
        
        return available_names
    
    # ==================== Iterator Support ====================
    
    def iter_resources(self) -> Iterator[Dict[str, Any]]:
        """
        Iterate over all resources of this type, yielding manifest dictionaries.
        
        Yields:
            Dict[str, Any]: Resource manifest dictionary.
        """
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
    
    def get_resources_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple resources by their names or UUIDs in a single operation.
        
        This is useful for batch operations, such as loading all tools for a VMCP server.
        Resources that cannot be found are skipped (not included in the result).
        
        Args:
            ids: List of resource names or UUIDs.
            
        Returns:
            List[Dict[str, Any]]: List of resource manifest dictionaries.
        """
        resources = []
        
        for id_str in ids:
            try:
                resource = self.get_resource_by_id(id_str)
                resources.append(resource)
            except HTTPException as e:
                if e.status_code == 404:
                    logger.warning(f"{self.resource_type.capitalize()} with ID '{id_str}' not found, skipping")
                else:
                    logger.error(f"Error loading {self.resource_type} with ID '{id_str}': {e.detail}")
            except Exception as e:
                logger.error(f"Unexpected error loading {self.resource_type} with ID '{id_str}': {e}")
        
        return resources
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """
        Make ResourceHandler itself iterable.
        
        Yields:
            Dict[str, Any]: Resource manifest dictionary.
        """
        return self.iter_resources()
    
    # ==================== Utility Methods ====================
    
    def resource_exists(self, id_str: str) -> bool:
        """
        Check if a resource exists by ID (name or UUID).
        
        Args:
            id_str: The ID of the resource (can be either name or UUID).
            
        Returns:
            bool: True if the resource exists, False otherwise.
        """
        resource_uuid = self.resolve_id(id_str)
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