import json
import logging
import os
from typing import List, Optional, Dict, Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)


INDEX_RELATIVE_DIRECTORY = "/index/"
INDEX_FILE_NAME = "metadatas_index.faiss"


class Metadata:
    def __init__(self, metadata_directory: str):
        """
        Initialize the Metadatas with a directory to store metadatas.
        Initialize the vector index
        """
        self.metadata_directory = metadata_directory
        os.makedirs(self.metadata_directory, exist_ok=True)

        logger.info(
            f"Initialized Metadatas with directory: {self.metadata_directory}")

    def get_metadata_file_path(self, filename: str) -> str:
        """
        Get the path of the metadata file associated with the given filename.
        """
        return os.path.join(self.metadata_directory, f"{filename}.json")

    def read_metadata(self, filename: str) -> Optional[str]:
        """
        Read the metadata for the given file.
        """
        data = None

        metadata_file_path = self.get_metadata_file_path(filename)
        if os.path.exists(metadata_file_path):
            with open(metadata_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        return data

    def write_metadata(self, filename: str, metadata: Dict[str, Any]) -> dict:
        """
        Write a metadata for the given file.
        """
        metadata_file_path = self.get_metadata_file_path(filename)
        try:
            with open(metadata_file_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=4)
            logger.info(f"Metadata saved for file: {filename}")
            return {"message": f"Metadata saved for file '{filename}'."}
        except Exception as e:
            logger.error(
                f"Error saving metadata for file '{filename}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error saving metadata: {str(e)}")

    def update_metadata(self, filename: str, new_metadata: Dict[str, Any]) -> dict:
        """
        Update the metadata for the given file.
        """
        metadata_file_path = self.get_metadata_file_path(filename)
        if not os.path.exists(metadata_file_path):
            raise HTTPException(
                status_code=404, detail=f"No metadata found for file '{filename}'")

        try:
            with open(metadata_file_path, "w", encoding="utf-8") as f:
                json.dump(new_metadata, f, indent=4, default=str)
            logger.info(f"Metadata updated for file: {filename}")
            return {"message": f"Metadata updated for file '{filename}'."}

        except Exception as e:
            logger.error(
                f"Error updating metadata for file '{filename}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating metadata: {str(e)}")

    def delete_metadata(self, filename: str) -> dict:
        """
        Delete the metadata for a given file.
        """
        metadata_file_path = self.get_metadata_file_path(filename)
        try:
            if os.path.exists(metadata_file_path):
                os.remove(metadata_file_path)

                logger.info(f"Metadata deleted for file: {filename}")
                return {"message": f"Metadata for file '{filename}' deleted successfully."}
            else:
                raise HTTPException(
                    status_code=404, detail=f"Metadata for file '{filename}' not found.")
        except Exception as e:
            logger.error(
                f"Error deleting metadata for file '{filename}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting metadata: {str(e)}")

