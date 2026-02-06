import logging
import os

import faiss
import numpy as np
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)


class DescriptionVectorIndex:
    def __init__(
        self,
        index_file: str = "description_index.faiss",
        dimension: int = 384,
    ):
        """
        Initialize the DescriptionVectorIndex class to handle FAISS indexing and searching.

        Args:
            index_file (str): The file to save/load the FAISS index.
            dimension (int): The dimensionality of the embeddings.
        """
        self.index_file = index_file
        self.dimension = dimension
        self.model = TextEmbedding()

        # Initialize FAISS index
        # L2 (Euclidean) distance-based index
        self.index = faiss.IndexFlatL2(self.dimension)

        # Initialize the files to FAISS index map
        self.files_to_faiss_index_map = []

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

        # Load the files to FAISS index map
        if os.path.exists(f"{self.index_file}.files_index.npy"):
            self.files_to_faiss_index_map = np.load(
                f"{self.index_file}.files_index.npy", allow_pickle=True
            )
            self.files_to_faiss_index_map = self.files_to_faiss_index_map.tolist()
            logger.info("Loaded files to FAISS index map.")

    def save_index(self):
        """
        Save the FAISS index to a file.
        """
        # Ensure the directory exists before writing
        index_dir = os.path.dirname(self.index_file)
        if index_dir:
            os.makedirs(index_dir, exist_ok=True)
        
        faiss.write_index(self.index, self.index_file)

        # persist the files to FAISS index map
        np.save(
            f"{self.index_file}.files_index.npy",
            self.files_to_faiss_index_map,
            allow_pickle=True,
        )

        logger.info(f"FAISS index saved to {self.index_file}")

    def add_description(self, description: str, filename: str):
        """
        Add a new description to the FAISS index.

        Args:
            description (str): The description text to be added.
            filename (str): the filename of the description
        """

        if filename in self.files_to_faiss_index_map:
            # if  filename exists in the index, update instead of adding
            self.update_description(description, filename)
        else:
            embedding = list(self.model.embed([description]))[0]
            self.index.add(np.array([embedding], dtype=np.float32))
            self.files_to_faiss_index_map.append(filename)
            self.save_index()
            logger.info("Description embedding added and index saved.")

    def update_description(self, new_description: str, filename: str):
        """
        Update the description at a specific index.

        Args:
            new_description (str): The updated description text.
            filename (str): The filename to be updated.
        """

        # search for the filename index in the files_to_faiss_index_map
        index = list(self.files_to_faiss_index_map).index(filename)
        if index == -1:
            raise ValueError(f"Filename '{filename}' not found in the index.")

        embedding = list(self.model.embed([new_description]))[0]

        # FAISS does not support updating a single vector, so we rebuild the index after removal
        embeddings = [
            embedding for embedding in self.index.reconstruct_n(0, self.index.ntotal)
        ]
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
        query_embedding = list(self.model.embed([query]))[0]
        query_embedding = np.array([query_embedding], dtype=np.float32)

        distances, indices = self.index.search(query_embedding, k)
        results = [(idx, dist) for idx, dist in zip(indices[0], distances[0])]

        matched_files = []
        for idx, dist in results:
            if idx != -1:
                filename = self.files_to_faiss_index_map[idx]
                matched_files.append(
                    {"filename": filename, "similarity_score": float(dist)}
                )

        return matched_files

    def delete_description(self, filename: str):
        """
        Delete the description at a specific index.

        Args:
            filename (str): The filename to be deleted.
        """

        # search for the filename index in the files_to_faiss_index_map
        index = list(self.files_to_faiss_index_map).index(filename)
        if index == -1:
            raise ValueError(f"Filename '{filename}' not found in the index.")

        embeddings = [
            embedding for embedding in self.index.reconstruct_n(0, self.index.ntotal)
        ]
        del embeddings[index]
        del self.files_to_faiss_index_map[index]

        # Rebuild the FAISS index after deletion
        new_index = faiss.IndexFlatL2(self.dimension)
        if len(embeddings) > 0:
            new_index.add(np.array(embeddings, dtype=np.float32))
        self.index = new_index

        self.save_index()
        logger.info(f"Description at index {index} deleted.")
