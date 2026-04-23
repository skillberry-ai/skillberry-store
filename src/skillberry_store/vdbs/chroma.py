import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import shutil
import os
from pathlib import Path
import logging
from skillberry_store.vdbs.vector_db_interface import VectorDBInterface
logger = logging.getLogger(__name__)


class ChromaVectorDB(VectorDBInterface):
    def __init__(self, dimension: int = 384, persist_path: str = "./chroma_db", collection_name: str = "my_collection"):
        """Initialize Chroma client"""
        self.persist_path = persist_path
        self.persist_directory = Path(persist_path).parent
        self.client = chromadb.PersistentClient(path=persist_path)
        self.collection_name = collection_name
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "l2"}
        )

    def add_vector(self, id: str, vector: List[float], metadata: Dict[str, Any]):
        """Add a vector with metadata"""
        logger.info(f"chroma add_vector")
        self.collection.add(
            ids=[id],
            embeddings=[vector],
            metadatas=[metadata]
        )

    def update_vector(self, id: str, vector: List[float], metadata: Dict[str, Any]):
        """Update existing vector"""
        self.collection.update(
            ids=[id],
            embeddings=[vector],
            metadatas=[metadata]
        )
    
    def search(self, query_vector: List[float], top_k: int = 5, where: Dict = None) -> List[Dict]:
        """Search for nearest neighbors"""
        logger.info(f"chroma search")
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where
        )

        output = []
        for i in range(len(results['ids'][0])):
            output.append({
                "filename": results['ids'][0][i],
                "id": results['ids'][0][i],
                "score": 1 / (1 + results['distances'][0][i]),  # Convert distance to similarity
                "similarity_score": results['distances'][0][i],
                "metadata": results['metadatas'][0][i] if results['metadatas'] else {}
            })
        return output
    
    def delete_vector(self, id: str):
        """Delete a vector by ID"""
        self.collection.delete(ids=[id])
    
    def load_index(self):
        """Restore from backup"""
        if os.path.exists(self.persist_directory):
            shutil.rmtree(self.persist_directory)
        shutil.copytree(backup_path, self.persist_directory)
        # Reinitialize client
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_collection(name=self.collection_name)
        logger.info(f"Restored from {backup_path}")
    
    def get_count(self) -> int:
        """Get number of vectors in collection"""
        return self.collection.count()

    def close(self) -> None:
        pass
