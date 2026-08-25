# identify_vdb.py

from enum import Enum
from typing import Type

from skillberry_store.vdbs.vector_db_interface import VectorDBInterface
import logging

logger = logging.getLogger(__name__)


class VectorDBType(str, Enum):
    """Supported vector database types"""
    FAISS = "faiss"
    CHROMA = "chroma"
    LANCEDB = "lancedb"


def identify_vector_db(db_type: VectorDBType) -> Type[VectorDBInterface]:
    """
    Factory function to create vector database instances

    Args:
        db_type: Type of vector database (from VectorDBType enum)

    Returns:
        Instance of VectorDBInterface
    """
    logger.info(f"identify_vector_db, db_type = {db_type}")

    # Backends are imported on demand rather than at module scope: chroma
    # pulls in onnxruntime, opentelemetry, hnswlib and pypika, and lancedb
    # pulls in pyarrow and pandas. faiss is the default backend, so importing
    # all three up front charged every deployment for backends it never uses.
    if db_type == VectorDBType.FAISS:
        from skillberry_store.vdbs.faiss import FaissDB

        return FaissDB
    if db_type == VectorDBType.CHROMA:
        from skillberry_store.vdbs.chroma import ChromaVectorDB

        return ChromaVectorDB
    if db_type == VectorDBType.LANCEDB:
        from skillberry_store.vdbs.lancedb import LanceDB

        return LanceDB

    raise ValueError(f"Unsupported database type: {db_type}")
