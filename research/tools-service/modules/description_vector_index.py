import logging
import os

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class DescriptionVectorIndex:
    def __init__(self, index_file: str = "description_index.faiss",
                 dimension: int = 384,
                 model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the DescriptionVectorIndex class to handle FAISS indexing and searching.

        Args:
            index_file (str): The file to save/load the FAISS index.
            dimension (int): The dimensionality of the embeddings.
        """
        self.index_file = index_file
        self.dimension = dimension
        self.model = SentenceTransformer(model)

        # Initialize FAISS index
        self.index = faiss.IndexFlatL2(self.dimension)  # L2 (Euclidean) distance-based index

        # Load the existing index if it exists
        self.load_index()

    def load_index(self):
        """
        Load the existing FAISS index from the file if it exists.
        """
        if os.path.exists(self.index_file):
            logger.info(f"Loading existing FAISS index from {self.index_file}")
            self.index = faiss.read_index(self.index_file)
        else:
            logger.info("No existing FAISS index found. Starting with an empty index.")

    def save_index(self):
        """
        Save the FAISS index to a file.
        """
        faiss.write_index(self.index, self.index_file)
        logger.info(f"FAISS index saved to {self.index_file}")

    def add_description(self, description: str):
        """
        Add a new description to the FAISS index.

        Args:
            description (str): The description text to be added.
        """
        embedding = self.model.encode([description])[0]
        self.index.add(np.array([embedding], dtype=np.float32))
        self.save_index()
        logger.info("Description embedding added and index saved.")

    def update_description(self, new_description: str, index: int):
        """
        Update the description at a specific index.

        Args:
            new_description (str): The updated description text.
            index (int): The index of the description to be updated.
        """
        embedding = self.model.encode([new_description])[0]

        # FAISS does not support updating a single vector, so we rebuild the index after removal
        embeddings = [embedding for embedding in self.index.reconstruct_n(0, self.index.ntotal)]
        embeddings[index] = embedding

        new_index = faiss.IndexFlatL2(self.dimension)
        new_index.add(np.array(embeddings, dtype=np.float32))
        self.index = new_index

        self.save_index()
        logger.info(f"Description at index {index} updated.")

    def search(self, query: str, k: int = 5) -> list:
        """
        Search for descriptions in the index similar to the given query.

        Args:
            query (str): The query text to search for.
            k (int): The number of top similar descriptions to return.

        Returns:
            list: A list of tuples containing indices and similarity scores.
        """
        query_embedding = self.model.encode([query])[0]
        query_embedding = np.array([query_embedding], dtype=np.float32)

        distances, indices = self.index.search(query_embedding, k)
        results = [(idx, dist) for idx, dist in zip(indices[0], distances[0])]

        return results

    def delete_description(self, index: int):
        """
        Delete the description at a specific index.

        Args:
            index (int): The index of the description to be deleted.
        """
        embeddings = [embedding for embedding in self.index.reconstruct_n(0, self.index.ntotal)]
        del embeddings[index]

        # Rebuild the FAISS index after deletion
        new_index = faiss.IndexFlatL2(self.dimension)
        if len(embeddings) > 0:
            new_index.add(np.array(embeddings, dtype=np.float32))
        self.index = new_index

        self.save_index()
        logger.info(f"Description at index {index} deleted.")
