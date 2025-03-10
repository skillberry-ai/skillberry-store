import json
import logging
import os
from typing import List, Optional, Dict, Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)

class Manifest:
    def __init__(self, manifest_directory: str):
        """
        Initialize the manifests with a directory to store manifests.
        """
        self.manifest_directory = manifest_directory
        os.makedirs(self.manifest_directory, exist_ok=True)

        logger.info(
            f"Initialized Manifests with directory: {self.manifest_directory}")

    def get_manifest_file_path(self, filename: str) -> str:
        """
        Get the path of the manifest file associated with the given filename.
        """
        return os.path.join(self.manifest_directory, f"{filename}")

    def read_manifest(self, filename: str) -> Optional[str]:
        """
        Read the manifest for the given filename.

        Returns:
            str: The manifest, or None if not found.

        """
        data = None

        manifest_file_path = self.get_manifest_file_path(filename)
        if os.path.exists(manifest_file_path):
            with open(manifest_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        return data

    def write_manifest(self, filename: str, manifest: Dict[str, Any]) -> dict:
        """
        Write a manifest for the given file.
        """
        manifest_file_path = self.get_manifest_file_path(filename)
        try:
            with open(manifest_file_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=4)
            logger.info(f"manifest saved for file: {filename}")
            return {"message": f"manifest saved for file '{filename}'."}
        except Exception as e:
            logger.error(
                f"Error saving manifest for file '{filename}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error saving manifest: {str(e)}")

    def update_manifest(self, filename: str, new_manifest: Dict[str, Any]) -> dict:
        """
        Update the manifest for the given file.
        """
        manifest_file_path = self.get_manifest_file_path(filename)
        if not os.path.exists(manifest_file_path):
            raise HTTPException(
                status_code=404, detail=f"No manifest found for file '{filename}'")

        try:
            with open(manifest_file_path, "w", encoding="utf-8") as f:
                json.dump(new_manifest, f, indent=4, default=str)
            logger.info(f"manifest updated for file: {filename}")
            return {"message": f"manifest updated for file '{filename}'."}

        except Exception as e:
            logger.error(
                f"Error updating manifest for file '{filename}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating manifest: {str(e)}")

    def list_manifests(self) -> List[str]:
        """
        List all manifests in the directory.

        Returns:
            List[Dict]: A list of manifests (json) present in the directory.

        Raises:
            HTTPException: If there is an error accessing the directory.
        """
        try:
            manifest_files = os.listdir(self.manifest_directory)
            return [self.read_manifest(f) for f in manifest_files
                        if self.read_manifest(f) is not None]
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise HTTPException(status_code=500, detail=f"Error listing manifests: {str(e)}")

    def delete_manifest(self, filename: str) -> dict:
        """
        Delete the manifest for a given file.
        """
        manifest_file_path = self.get_manifest_file_path(filename)
        try:
            if os.path.exists(manifest_file_path):
                os.remove(manifest_file_path)

                logger.info(f"manifest deleted for file: {filename}")
                return {"message": f"manifest for file '{filename}' deleted successfully."}
            else:
                raise HTTPException(
                    status_code=404, detail=f"manifest for file '{filename}' not found.")
        except Exception as e:
            logger.error(
                f"Error deleting manifest for file '{filename}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting manifest: {str(e)}")

