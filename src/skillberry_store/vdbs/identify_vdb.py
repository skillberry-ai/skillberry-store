# identify_vdb.py

from enum import Enum
from typing import Optional, Type

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


def check_backend_available(db_type: str) -> Optional[str]:
    """Resolve a backend without using it; return a problem description or None.

    The on-demand imports above mean a misconfiguration only surfaces at the first
    embedding call — ``SBS_VDB=chroma`` on a core-only image fails on a search, not
    at boot, which is a needlessly obscure failure point (PR #308 review issue #18).
    Calling this at startup makes it visible in the boot log while deliberately not
    introducing a new crash mode: a deployment that currently starts and serves its
    non-search endpoints keeps doing so.

    Accepts the raw string form, since that is what ``SBS_VDB`` provides.
    """
    try:
        resolved = VectorDBType(db_type)
    except ValueError:
        supported = ", ".join(t.value for t in VectorDBType)
        return f"unsupported vector DB type {db_type!r} (supported: {supported})"

    try:
        identify_vector_db(resolved)
    except ImportError as exc:
        return (
            f"vector DB backend {resolved.value!r} is configured but not "
            f"installed ({exc}). Install the matching extra, or use a variant "
            "image that bundles it"
        )
    return None
