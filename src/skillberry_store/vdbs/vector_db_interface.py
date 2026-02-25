# vector_db_interface.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from sentence_transformers import SentenceTransformer
encoder = SentenceTransformer('all-MiniLM-L6-v2')

def text_to_vector(text: str) -> List[float]:
    """Convert text to vector embedding"""
    # TODO specify dimension to use for embedding
    return encoder.encode(text).tolist()


class VectorDBInterface(ABC):
    """Abstract base class for vector database operations"""

    @abstractmethod
    def __init__(
            self,
            dimension: int,
            persist_path: str,
    ):
        """
        Initialize the VDB class to handle indexing and searching.

        Args:
            index_file (str): The file to save/load the index.
            dimension (int): The dimensionality of the embeddings.
        """
        pass

    @abstractmethod
    def add_vector(self, id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        """
        Add a new vector to the database

        Args:
            id: Unique identifier for the vector
            vector: Vector embedding as list of floats
            metadata: Dictionary containing metadata
        """
        pass

    @abstractmethod
    def update_vector(self, id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        """
        Update an existing vector

        Args:
            id: Unique identifier for the vector
            vector: Updated vector embedding
            metadata: Updated metadata dictionary
        """
        pass

    @abstractmethod
    def search(self, query_vector: List[float], top_k: int = 5,
               filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for nearest neighbors

        Args:
            query_vector: Query vector for similarity search
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of dictionaries with keys: id, score, metadata
        """
        pass

    @abstractmethod
    def delete_vector(self, id: str) -> None:
        """
        Delete a vector by ID

        Args:
            id: Unique identifier of vector to delete
        """
        pass

    @abstractmethod
    def load_index(self) -> None:
        """
        Load/restore the index from backup

        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection and cleanup resources"""
        pass

    def batch_add_vectors(self, vectors: List[Dict[str, Any]]) -> None:
        """
        Add multiple vectors in batch (default implementation)

        Args:
            vectors: List of dicts with keys: id, vector, metadata
        """
        for item in vectors:
            self.add_vector(item['id'], item['vector'], item['metadata'])

    def search_by_text(self, query_text: str, top_k: int = 5,
                       filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Convenience method to search using text query

        Args:
            query_text: Text query to search for
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of search results
        """
        query_vector = self.text_to_vector(query_text)
        return self.search(query_vector, top_k, filters)

