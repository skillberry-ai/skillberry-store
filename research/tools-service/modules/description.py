import os
import logging
from fastapi import HTTPException
from typing import List, Optional
from modules.description_vector_index import DescriptionVectorIndex

logger = logging.getLogger(__name__)

EMBEDDING_MODEL='sentence-transformers/all-MiniLM-L6-v2'
EMBEDDING_MODEL_FILE_NAME="descriptions_index.faiss"
EMBEDDING_MODEL_DIMENSION=384
EMBEDDING_MODEL_SEARCH_K=5

class Description:
    def __init__(self, descriptions_directory: str,
                 vector_index: DescriptionVectorIndex,
                 index_file: str = EMBEDDING_MODEL_FILE_NAME):
        """
        Initialize the Descriptions with a directory to store descriptions.
        Initialize the vector index
        """
        self.descriptions_directory = descriptions_directory
        os.makedirs(self.descriptions_directory, exist_ok=True)
        self.vector_index = vector_index(index_file=self.get_description_file_path(index_file),
                                         dimension=EMBEDDING_MODEL_DIMENSION,
                                         model=EMBEDDING_MODEL)

        logger.info(f"Initialized Descriptions with directory: {self.descriptions_directory}")

    def load_index(self):
        """
        Load the existing FAISS index from the file if it exists.
        """
        if os.path.exists(self.index_file):
            logger.info(f"Loading existing FAISS index from {self.index_file}")
            self.index = faiss.read_index(self.index_file)
        else:
            logger.info("No existing FAISS index found. Starting with an empty index.")

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
            self.vector_index.add_description(description)

            logger.info(f"Description and embedding saved for file: {filename}")
            return {"message": f"Description and embedding saved for file '{filename}'."}
        except Exception as e:
            logger.error(f"Error saving description for file '{filename}': {e}")
            raise HTTPException(status_code=500, detail=f"Error saving description: {str(e)}")

    def update_description(self, filename: str, new_description: str) -> dict:
        """
        Update the description for the given file.
        """
        description_file_path = self.get_description_file_path(filename)
        if not os.path.exists(description_file_path):
            raise HTTPException(status_code=404, detail=f"No description found for file '{filename}'")

        try:
            with open(description_file_path, "w", encoding="utf-8") as f:
                f.write(new_description)

            # Update the description in the vector index
            index = list(os.listdir(self.descriptions_directory)).index(f"{filename}.txt")
            self.vector_index.update_description(new_description, index)

            logger.info(f"Description and embedding updated for file: {filename}")
            return {"message": f"Description and embedding updated for file '{filename}'."}

        except Exception as e:
            logger.error(f"Error updating description for file '{filename}': {e}")
            raise HTTPException(status_code=500, detail=f"Error updating description: {str(e)}")

    def delete_description(self, filename: str) -> dict:
        """
        Delete the description for a given file.
        """
        description_file_path = self.get_description_file_path(filename)
        try:
            if os.path.exists(description_file_path):
                os.remove(description_file_path)

                # Find the index of the description in the vector index and delete it
                index = list(os.listdir(self.descriptions_directory)).index(f"{filename}.txt")
                self.vector_index.delete_description(index)

                logger.info(f"Description deleted for file: {filename}")
                return {"message": f"Description for file '{filename}' deleted successfully."}
            else:
                raise HTTPException(status_code=404, detail=f"Description for file '{filename}' not found.")
        except Exception as e:
            logger.error(f"Error deleting description for file '{filename}': {e}")
            raise HTTPException(status_code=500, detail=f"Error deleting description: {str(e)}")

    def search_description(self, search_term: str, k: int = EMBEDDING_MODEL_SEARCH_K) -> List[str]:
        results = self.vector_index.search(search_term, k)
        return results