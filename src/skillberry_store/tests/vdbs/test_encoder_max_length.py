# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Coverage for the pinned encoder truncation limit.

Background (PR #308 review, issue #10): ``SentenceTransformer('all-MiniLM-L6-v2')``
caps this model at ``max_seq_length=256`` while fastembed applies whatever limit
ships in the tokenizer config — 128 for the qdrant ONNX conversion of these
weights. Longer descriptions therefore truncated at a different point than the
vectors already in a faiss index, silently changing their ranking and undermining
the "existing indices remain valid" claim of the migration.
"""

from __future__ import annotations

import numpy as np
import pytest

from skillberry_store.vdbs import vector_db_interface as vdb
from skillberry_store.vdbs.vector_db_interface import (
    ENCODER_MAX_LENGTH,
    ENCODER_MAX_LENGTH_ENV,
    _ENCODER_MODEL,
    encoder_max_length,
    text_to_vector,
)

# ~600 tokens: well past both the fastembed default (128) and our pin (256).
LONG_TEXT = " ".join(f"step{i} does something useful" for i in range(120))
SHORT_TEXT = "A tool that resizes images."


def test_default_matches_sentence_transformers():
    """256 is `SentenceTransformer('all-MiniLM-L6-v2').max_seq_length`."""
    assert ENCODER_MAX_LENGTH == 256
    assert encoder_max_length() == 256


def test_override_is_honoured(monkeypatch):
    monkeypatch.setenv(ENCODER_MAX_LENGTH_ENV, "128")
    assert encoder_max_length() == 128


@pytest.mark.parametrize("bad", ["", "0", "-4", "not-a-number"])
def test_invalid_override_falls_back_to_the_default(monkeypatch, bad):
    monkeypatch.setenv(ENCODER_MAX_LENGTH_ENV, bad)
    assert encoder_max_length() == ENCODER_MAX_LENGTH


def test_live_encoder_truncates_at_the_pinned_limit():
    """The pin must reach the tokenizer — fastembed ignores a max_length kwarg."""
    encoder = vdb._get_encoder()

    truncation = encoder.model.tokenizer.truncation
    assert truncation is not None, "truncation must be configured explicitly"
    assert truncation["max_length"] == ENCODER_MAX_LENGTH, (
        "the tokenizer still uses fastembed's own limit; long descriptions will "
        "embed differently from the vectors already in a faiss index"
    )


def test_pin_is_best_effort_when_fastembed_moves_the_tokenizer(caplog):
    """A fastembed release that relocates the tokenizer must not break embedding."""

    class Opaque:
        pass

    with caplog.at_level("WARNING"):
        vdb._pin_max_length(Opaque(), 256)

    assert "Could not pin the encoder truncation limit" in caplog.text


def test_long_text_embedding_differs_between_limits():
    """Pins the finding: the limit genuinely changes the vector for long input.

    Guards against a future "harmless cleanup" that drops the pin on the
    assumption that the two limits agree. Short text is unaffected, which is why
    the divergence went unnoticed.
    """
    from fastembed import TextEmbedding

    encoder = TextEmbedding(
        model_name=_ENCODER_MODEL, cache_dir=str(vdb.encoder_cache_dir())
    )

    vdb._pin_max_length(encoder, 128)
    short_128 = next(iter(encoder.embed([SHORT_TEXT])))
    long_128 = next(iter(encoder.embed([LONG_TEXT])))

    vdb._pin_max_length(encoder, 256)
    short_256 = next(iter(encoder.embed([SHORT_TEXT])))
    long_256 = next(iter(encoder.embed([LONG_TEXT])))

    assert np.allclose(short_128, short_256, atol=1e-6), (
        "short text must be limit-independent"
    )
    cosine = float(np.dot(long_128, long_256))
    assert cosine < 0.99, (
        "expected the two limits to produce materially different vectors for "
        f"long input, got cosine {cosine:.4f}"
    )


def test_text_to_vector_still_returns_the_expected_shape():
    vector = text_to_vector(LONG_TEXT)

    assert len(vector) == 384
    assert abs(float(np.linalg.norm(vector)) - 1.0) < 1e-5, "vectors are L2-normalized"
