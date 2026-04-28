import faiss
import numpy as np
import pickle
import os
from typing import List, Dict, Any, Optional
from skillberry_store.vdbs.vector_db_interface import VectorDBInterface
import logging
logger = logging.getLogger(__name__)


class FaissDB(VectorDBInterface):
    """
    FAISS (Facebook AI Similarity Search) implementation
    
    Note: FAISS is an in-memory library, so persistence requires manual save/load.
    This implementation uses IndexIDMap2 for ID management and stores metadata separately.
    """
    
    def __init__(self, dimension: int = 384, index_type: str = "Flat", 
                 metric: str = "l2", persist_path: str = "./faiss_db"):
        """
        Initialize FAISS index
        
        Args:
            dimension: Vector dimension (default 384 for all-MiniLM-L6-v2)
            index_type: FAISS index type - "Flat", "IVFFlat", "HNSW"
            metric: Distance metric - "cosine", "l2", "ip" (inner product)
            persist_path: Directory for saving index and metadata
        """
        self.dimension = dimension
        self.index_type = index_type
        self.metric = metric
        self.persist_path = persist_path

        # Create persist directory if it doesn't exist
        logger.info(f"persist_path: {persist_path}")
        os.makedirs(persist_path, exist_ok=True)

        # Initialize index
        self.index = self._create_index()
        
        # Store metadata separately (FAISS doesn't store metadata)
        self.metadata_store: Dict[str, Dict[str, Any]] = {}
        
        # Map string IDs to integer IDs for FAISS
        self.id_to_int: Dict[str, int] = {}
        self.int_to_id: Dict[int, str] = {}
        self.next_id = 0
        self.load_index()

    def _create_index(self) -> faiss.Index:
        """Create FAISS index based on configuration"""
        # Normalize for cosine similarity
        if self.metric == "cosine":
            if self.index_type == "Flat":
                index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type == "IVFFlat":
                quantizer = faiss.IndexFlatIP(self.dimension)
                index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
            elif self.index_type == "HNSW":
                index = faiss.IndexHNSWFlat(self.dimension, 32)
                index.metric_type = faiss.METRIC_INNER_PRODUCT
            else:
                raise ValueError(f"Unsupported index type: {self.index_type}")
        
        elif self.metric == "l2":
            if self.index_type == "Flat":
                index = faiss.IndexFlatL2(self.dimension)
            elif self.index_type == "IVFFlat":
                quantizer = faiss.IndexFlatL2(self.dimension)
                index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
            elif self.index_type == "HNSW":
                index = faiss.IndexHNSWFlat(self.dimension, 32)
            else:
                raise ValueError(f"Unsupported index type: {self.index_type}")
        
        elif self.metric == "ip":
            if self.index_type == "Flat":
                index = faiss.IndexFlatIP(self.dimension)
            elif self.index_type == "IVFFlat":
                quantizer = faiss.IndexFlatIP(self.dimension)
                index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
            elif self.index_type == "HNSW":
                index = faiss.IndexHNSWFlat(self.dimension, 32)
                index.metric_type = faiss.METRIC_INNER_PRODUCT
            else:
                raise ValueError(f"Unsupported index type: {self.index_type}")
        else:
            raise ValueError(f"Unsupported metric: {self.metric}")
        
        # Wrap with IDMap2 for ID management
        index_with_ids = faiss.IndexIDMap2(index)
        
        # Train index if needed (for IVF indices)
        if self.index_type == "IVFFlat" and not index.is_trained:
            # Generate random training data
            training_data = np.random.random((1000, self.dimension)).astype('float32')
            if self.metric == "cosine":
                faiss.normalize_L2(training_data)
            index.train(training_data)
        
        return index_with_ids
    
    def _get_int_id(self, str_id: str) -> int:
        """Get or create integer ID for string ID"""
        if str_id not in self.id_to_int:
            self.id_to_int[str_id] = self.next_id
            self.int_to_id[self.next_id] = str_id
            self.next_id += 1
        return self.id_to_int[str_id]
    
    def add_vector(self, id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        """Add a vector with metadata"""
        logger.info(f"faiss add_vector")
        int_id = self._get_int_id(id)
        
        # Convert to numpy array and normalize if using cosine
        vec = np.array([vector], dtype='float32')
        if self.metric == "cosine":
            faiss.normalize_L2(vec)
        
        # Add to FAISS index
        ids = np.array([int_id], dtype='int64')
        self.index.add_with_ids(vec, ids)
        
        # Store metadata
        self.metadata_store[id] = metadata
        self.save_index()

    def update_vector(self, id: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        """Update existing vector (remove and re-add)"""
        if id in self.id_to_int:
            self.delete_vector(id)
        self.add_vector(id, vector, metadata)
    
    def search(self, query_vector: List[float], top_k: int = 5, 
               filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for nearest neighbors"""
        # Convert to numpy and normalize if using cosine
        logger.info(f"faiss search")
        query = np.array([query_vector], dtype='float32')
        if self.metric == "cosine":
            faiss.normalize_L2(query)
        
        # Search
        distances, indices = self.index.search(query, top_k)
        
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx == -1:  # No result found
                continue
            
            str_id = self.int_to_id.get(int(idx))
            if str_id is None:
                continue
            
            metadata = self.metadata_store.get(str_id, {})
            
            # Apply filters if provided
            if filters:
                match = all(metadata.get(k) == v for k, v in filters.items())
                if not match:
                    continue

            # Convert distance to similarity score
            if self.metric == "cosine" or self.metric == "ip":
                score = float(dist)  # Already similarity for IP
            else:  # L2 distance
                score = 1.0 / (1.0 + float(dist))

            results.append({
                "filename": str_id,
                "id": str_id,
                "score": score,
                "similarity_score": float(dist),
                "metadata": metadata
            })
        
        return results
    
    def delete_vector(self, id: str) -> None:
        """
        Delete a vector by ID
        
        Note: FAISS doesn't support efficient deletion. This implementation
        removes from metadata but the vector remains in the index.
        For true deletion, rebuild the index without the deleted vector.
        """
        if id in self.metadata_store:
            del self.metadata_store[id]
        
        if id in self.id_to_int:
            int_id = self.id_to_int[id]
            # Remove ID mappings
            del self.id_to_int[id]
            del self.int_to_id[int_id]
            
            # Note: FAISS IndexIDMap2 doesn't support remove_ids efficiently
            # For production, consider rebuilding index periodically
            try:
                ids_to_remove = np.array([int_id], dtype='int64')
                self.index.remove_ids(ids_to_remove)
            except Exception:
                pass  # Some index types don't support removal
    
    def save_index(self) -> None:
        """Save FAISS index and metadata to disk"""

        # Ensure  directory for index exists
        os.makedirs(self.persist_path, exist_ok=True)

        # Save FAISS index
        index_path = os.path.join(self.persist_path, "faiss.index")
        faiss.write_index(self.index, index_path)

        # Save metadata and ID mappings
        metadata_path = os.path.join(self.persist_path, "metadata.pkl")
        with open(metadata_path, 'wb') as f:
            pickle.dump({
                'metadata_store': self.metadata_store,
                'id_to_int': self.id_to_int,
                'int_to_id': self.int_to_id,
                'next_id': self.next_id,
                'dimension': self.dimension,
                'index_type': self.index_type,
                'metric': self.metric
            }, f)
        
        logger.info(f"Index saved to {index_path}")
    
    def load_index(self) -> None:
        """Load FAISS index and metadata from disk"""
        # Load FAISS index
        index_path = os.path.join(self.persist_path, "faiss.index")
        if os.path.exists(index_path):
            self.index = faiss.read_index(index_path)
        else:
            logger.info("No existing FAISS index found. Starting with an empty index.")

        # Load metadata and ID mappings
        metadata_path = os.path.join(self.persist_path, "metadata.pkl")
        if os.path.exists(metadata_path):
            with open(metadata_path, 'rb') as f:
                data = pickle.load(f)
                self.metadata_store = data['metadata_store']
                self.id_to_int = data['id_to_int']
                self.int_to_id = data['int_to_id']
                self.next_id = data['next_id']
                self.dimension = data['dimension']
                self.index_type = data['index_type']
                self.metric = data['metric']
        else:
            logger.info("No existing FAISS metadata found.")

        logger.info(f"Index loaded from {index_path}")
    
    def close(self) -> None:
        """Cleanup resources"""
        # Auto-save on close
        self.save_index()
    
    def rebuild_index(self) -> None:
        """
        Rebuild index from scratch (useful after many deletions)
        This creates a clean index with only active vectors
        """
        # Collect all active vectors
        vectors = []
        ids = []
        
        for str_id, metadata in self.metadata_store.items():
            if str_id in self.id_to_int:
                int_id = self.id_to_int[str_id]
                # Reconstruct vector from index
                vec = self.index.reconstruct(int_id)
                vectors.append(vec)
                ids.append(int_id)
        
        # Create new index
        self.index = self._create_index()
        
        # Re-add all vectors
        if vectors:
            vectors_array = np.array(vectors, dtype='float32')
            ids_array = np.array(ids, dtype='int64')
            self.index.add_with_ids(vectors_array, ids_array)
        
        logger.info(f"Index rebuilt with {len(vectors)} vectors")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "index_type": self.index_type,
            "metric": self.metric,
            "metadata_count": len(self.metadata_store)
        }

