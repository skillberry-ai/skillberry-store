import logging
import os
from pathlib import Path
from typing import Optional, Any

from fastapi import HTTPException
from skillberry_store.vdbs.vector_db_interface import VectorDBInterface, text_to_vector

logger = logging.getLogger(__name__)

base_dir = Path(__file__).resolve().parent

default_dimension = 384
default_model_search_k = 5

_dimension = os.getenv("EMBEDDING_MODEL_DIMENSION", default_dimension)
_embedding_model_search_k = os.getenv(
    "EMBEDDING_MODEL_SEARCH_K", default_model_search_k
)

INDEX_RELATIVE_DIRECTORY = "/index/"
INDEX_FILE_NAME_BASE = "descriptions_index."


class Description:
    def __init__(
        self, descriptions_directory: str, vector_index: VectorDBInterface, vdb_type: str,
    ):
        """
        Initialize the Descriptions with a directory to store descriptions.
        Initialize the vector index
        """
        self.descriptions_directory = descriptions_directory
        os.makedirs(self.descriptions_directory, exist_ok=True)
        index_directory = descriptions_directory + INDEX_RELATIVE_DIRECTORY
        os.makedirs(index_directory, exist_ok=True)
        index_file_name = INDEX_FILE_NAME_BASE + vdb_type
        self.vector_index = vector_index(
            persist_path=index_directory + index_file_name,
            dimension=_dimension,
        )

        logger.info(
            f"Initialized Descriptions with directory: {self.descriptions_directory}"
        )

    def load_index(self):
        """
        Load the index if exists.
        """
        self.vector_index.load_index()

    def get_description_file_path(self, filename: str) -> str:
        """
        Get the path of the description file associated with the given filename.
        """
        return os.path.join(self.descriptions_directory, f"{filename}.txt")

    def read_description(self, filename: str) -> Optional[str]:
        """
        Read the description for the given file.
        """
        description_file_path = self.get_description_file_path(filename)
        if os.path.exists(description_file_path):
            with open(description_file_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def write_description(self, filename: str, description: str) -> dict:
        """
        Write a description for the given file.
        """
        description_file_path = self.get_description_file_path(filename)
        try:
            with open(description_file_path, "w", encoding="utf-8") as f:
                f.write(description)

            # Add description embedding to the vector index
            embedding = text_to_vector(description)
            self.vector_index.add_vector(
                    id = filename,
                    vector = embedding,
                    metadata = {"placeholder": "default"},
            )

            logger.info(f"Description and embedding saved for file: {filename}")
            return {
                "message": f"Description and embedding saved for file '{filename}'."
            }
        except Exception as e:
            logger.error(f"Error saving description for file '{filename}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error saving description: {str(e)}"
            )

    def update_description(self, filename: str, new_description: str) -> dict:
        """
        Update the description for the given file.
        """
        description_file_path = self.get_description_file_path(filename)
        if not os.path.exists(description_file_path):
            raise HTTPException(
                status_code=404, detail=f"No description found for file '{filename}'"
            )

        try:
            with open(description_file_path, "w", encoding="utf-8") as f:
                f.write(new_description)

            # Update the description in the vector index
            embedding = text_to_vector(new_description)
            self.vector_index.update_vector(
                    id = filename,
                    vector = embedding,
                    metadata = {"placeholder": "default"},
            )
            logger.info(f"Description and embedding updated for file: {filename}")
            return {
                "message": f"Description and embedding updated for file '{filename}'."
            }

        except Exception as e:
            logger.error(f"Error updating description for file '{filename}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating description: {str(e)}"
            )

    def delete_description(self, filename: str) -> dict:
        """
        Delete the description for a given file.
        """
        description_file_path = self.get_description_file_path(filename)
        try:
            if os.path.exists(description_file_path):
                self.vector_index.delete_vector(filename)
                os.remove(description_file_path)
                logger.info(f"Description deleted for file: {filename}")
                return {
                    "message": f"Description for file '{filename}' deleted successfully."
                }
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Description for file '{filename}' not found.",
                )
        except Exception as e:
            logger.error(f"Error deleting description for file '{filename}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting description: {str(e)}"
            )

    def search_description(
        self, search_term: str, k: int = _embedding_model_search_k
    ) -> list[dict[str, str | Any]]:
        embedding = text_to_vector(search_term)
        matched_files = self.vector_index.search(embedding, k)
        logger.info(f"Search results for term '{search_term}': {matched_files}")
        return matched_files
