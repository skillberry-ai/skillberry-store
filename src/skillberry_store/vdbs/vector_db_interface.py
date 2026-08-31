# vector_db_interface.py

import logging
import os
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

# Same 384-dim weights that ``SentenceTransformer('all-MiniLM-L6-v2')`` used,
# served through onnxruntime instead of torch. Both produce L2-normalized
# vectors that agree to ~1e-7, so indices built by either remain valid.
_ENCODER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Explicit override for the ONNX weight cache.
ENCODER_CACHE_DIR_ENV = "SBS_ENCODER_CACHE_DIR"

# Maximum sequence length, in tokens, before the input is truncated.
#
# ``SentenceTransformer('all-MiniLM-L6-v2')`` caps this model at
# ``max_seq_length=256``; fastembed instead applies whatever limit ships in the
# tokenizer config, which for the qdrant ONNX conversion of these weights is
# **128** — half as much. Anything longer therefore truncated at a different
# point than the vectors already in a faiss index, changing the vector and its
# ranking (PR #308 review issue #10; measured cosine similarity 0.928 between the
# two limits for a ~600-token description, against ~1e-7 agreement for short
# text). Pinning the value restores the "existing indices remain valid" property
# the migration claimed, and makes the limit explicit rather than an artefact of
# whatever a future fastembed release ships.
#
# Override only to match an index that was already built at a different limit.
ENCODER_MAX_LENGTH_ENV = "SBS_ENCODER_MAX_LENGTH"
ENCODER_MAX_LENGTH = 256

_encoder = None
_encoder_lock = threading.Lock()


def encoder_cache_dir() -> Path:
    """Directory fastembed caches the ~80 MB ONNX model in.

    fastembed does NOT honour HF_HOME / TRANSFORMERS_CACHE / XDG_CACHE_HOME: left
    to itself it caches into a fresh temp directory, so the download repeats on
    every pod restart where /tmp is an ephemeral emptyDir — and ``/health/ready``
    gates on ``encoder_warmup``, putting an ~11.5 s HuggingFace round-trip on the
    readiness critical path (PR #308 review issue #9). Pinning it to a stable,
    group-writable path lets the image ship the weights pre-seeded and start
    without reaching HuggingFace at all.

    Resolution order:
      1. ``SBS_ENCODER_CACHE_DIR`` — explicit override.
      2. ``$APP_HOME/.cache/fastembed`` — the container layout. The Dockerfile
         seeds this at build time and applies ``chgrp 0`` / ``chmod g=u`` to
         $APP_HOME, so the arbitrary UID OpenShift assigns can read it.
      3. ``$XDG_CACHE_HOME/fastembed``, else ``~/.cache/fastembed`` — a dev
         checkout, where the point is simply to survive a /tmp cleanup.
    """
    explicit = os.environ.get(ENCODER_CACHE_DIR_ENV)
    if explicit:
        return Path(explicit)
    app_home = os.environ.get("APP_HOME")
    if app_home:
        return Path(app_home) / ".cache" / "fastembed"
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg_cache) if xdg_cache else Path.home() / ".cache"
    return base / "fastembed"


def encoder_max_length() -> int:
    """Token limit to truncate at — see ENCODER_MAX_LENGTH."""
    raw = os.environ.get(ENCODER_MAX_LENGTH_ENV)
    if not raw:
        return ENCODER_MAX_LENGTH
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if value <= 0:
        logger.warning(
            "%s=%r is not a positive integer; using the default %d",
            ENCODER_MAX_LENGTH_ENV,
            raw,
            ENCODER_MAX_LENGTH,
        )
        return ENCODER_MAX_LENGTH
    return value


def _pin_max_length(encoder: TextEmbedding, max_length: int) -> None:
    """Force the tokenizer's truncation limit.

    fastembed accepts (and silently ignores) a ``max_length`` constructor kwarg,
    so the limit has to be set on the loaded tokenizer. Reaching through
    ``.model.tokenizer`` is internal API, hence best-effort: a fastembed release
    that moves it degrades to that release's default rather than failing to
    embed at all.
    """
    tokenizer = getattr(getattr(encoder, "model", None), "tokenizer", None)
    enable_truncation = getattr(tokenizer, "enable_truncation", None)
    if enable_truncation is None:
        logger.warning(
            "Could not pin the encoder truncation limit to %d tokens: this "
            "fastembed release does not expose model.tokenizer.enable_truncation. "
            "Long descriptions may embed differently from existing indices.",
            max_length,
        )
        return
    enable_truncation(max_length=max_length)


def _get_encoder() -> TextEmbedding:
    global _encoder
    if _encoder is None:
        # Locked so concurrent first-callers can't each build an onnx session.
        with _encoder_lock:
            if _encoder is None:
                cache_dir = encoder_cache_dir()
                try:
                    cache_dir.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                    # An unwritable cache must not take the service down: fall
                    # back to fastembed's own temp-dir cache (the old behaviour).
                    logger.warning(
                        "Encoder cache dir %s is unusable (%s); "
                        "falling back to fastembed's default temp cache",
                        cache_dir,
                        exc,
                    )
                    _encoder = TextEmbedding(model_name=_ENCODER_MODEL)
                    _pin_max_length(_encoder, encoder_max_length())
                    return _encoder
                _encoder = TextEmbedding(
                    model_name=_ENCODER_MODEL, cache_dir=str(cache_dir)
                )
                _pin_max_length(_encoder, encoder_max_length())
    return _encoder

def text_to_vector(text: str) -> List[float]:
    """Convert text to vector embedding"""
    # TODO specify dimension to use for embedding
    return next(iter(_get_encoder().embed([text]))).tolist()


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

