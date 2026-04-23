# vector_db_interface.py

from enum import Enum

from skillberry_store.vdbs.vector_db_interface import VectorDBInterface
from skillberry_store.vdbs.faiss import FaissDB
from skillberry_store.vdbs.chroma import ChromaVectorDB
from skillberry_store.vdbs.lancedb import LanceDB
import logging

logger = logging.getLogger(__name__)


class VectorDBType(str, Enum):
    """Supported vector database types"""
    FAISS = "faiss"
    CHROMA = "chroma"
    LANCEDB = "lancedb"


def identify_vector_db(db_type: VectorDBType) -> VectorDBInterface:
    """
    Factory function to create vector database instances
    
    Args:
        db_type: Type of vector database (from VectorDBType enum)

    Returns:
        Instance of VectorDBInterface
    """
    db_classes = {
        VectorDBType.FAISS: FaissDB,
        VectorDBType.CHROMA: ChromaVectorDB,
        VectorDBType.LANCEDB: LanceDB,
    }

    logger.info(f"identify_vector_db, db_type = {db_type}")
    if db_type in VectorDBType._value2member_map_:
        db_class = db_classes[db_type]
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
    
    return db_class
