import lancedb
from typing import List, Dict, Any, Optional
import pandas as pd
import shutil
import os
from skillberry_store.vdbs.vector_db_interface import VectorDBInterface, text_to_vector
import logging
logger = logging.getLogger(__name__)


class LanceDB(VectorDBInterface):
    """LanceDB implementation"""
    
    def __init__(self, dimension: int = 384, persist_path: str = "./lancedb", table_name: str = "vectors"):

        self.db_path = persist_path
        self.db = lancedb.connect(self.db_path)
        self.table_name = table_name
        self._create_table()
    
    def _create_table(self):
        try:
            self.table = self.db.open_table(self.table_name)
        except Exception:
            sample_data = pd.DataFrame({
                "uuid": ["init"],
                "vector": [text_to_vector("initialization")],
                "text": [""],
                "metadata": [{}]
            })
            self.table = self.db.create_table(self.table_name, data=sample_data, mode="overwrite")
    
    def add_vector(self, uuid: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        logger.info(f"lancedb add_vector")
        data = pd.DataFrame({
            "uuid": [uuid],
            "vector": [vector],
            #"text": [metadata.get("text", "")],
            #"metadata": [metadata]
        })
        self.table.add(data)

    def update_vector(self, uuid: str, vector: List[float], metadata: Dict[str, Any]) -> None:
        self.delete_vector(uuid)
        self.add_vector(uuid, vector, metadata)
    
    def search(self, query_vector: List[float], top_k: int = 5, 
               filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        logger.info(f"lancedb search")
        query = self.table.search(query_vector).limit(top_k)
        results = query.to_pandas()
        
        return [
            {
                "filename": row["uuid"],
                "uuid": row["uuid"],
                "score": 1 / (1 + row["_distance"]),
                "similarity_score": row["_distance"],
                "metadata": row["metadata"]
            }
            for _, row in results.iterrows()
        ]
    
    def delete_vector(self, uuid: str) -> None:
        self.table.delete(f'uuid = "{uuid}"')
    
    def load_index(self) -> None:
        if os.path.exists(self.db_path):
            shutil.rmtree(self.db_path)
        shutil.copytree(backup_path, self.db_path)
        self.db = lancedb.connect(self.db_path)
        self.table = self.db.open_table(self.table_name)
    
    def close(self) -> None:
        pass
