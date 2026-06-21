"""Tests for Hypothesis-backed input generation (the optional engine)."""

import pytest

from skillberry_plugin_dast.engine.fuzz import (
    GENERATOR_NAME,
    cases_from_signature,
    generate_cases,
    generator_available,
    generator_status,
)

# Generation requires the optional engine; skip those tests if it's absent.
requires_engine = pytest.mark.skipif(
    not generator_available(),
    reason=f"input generator {GENERATOR_NAME!r} not installed",
)


def _labels(cases):
    return [c["label"] for c in cases]


def test_generator_name_is_hypothesis():
    assert GENERATOR_NAME == "hypothesis"


def test_generator_status_reflects_availability():
    status = generator_status()
    if generator_available():
        assert "Ready" in status and GENERATOR_NAME in status
    else:
        assert "Disabled" in status and "pip install" in status


def test_no_params_yields_no_args_case():
    # This path needs no engine (no values to draw).
    assert generate_cases({"properties": {}, "required": []}) == [
        {"label": "no-args", "args": {}}
    ]


@requires_engine
def test_deterministic():
    params = {
        "properties": {"channel": {"type": "string"}, "count": {"type": "integer"}},
        "required": ["channel"],
        "optional": ["count"],
    }
    assert generate_cases(params) == generate_cases(params)


@requires_engine
def test_has_baseline_draws_and_missing_required():
    params = {
        "properties": {"channel": {"type": "string"}},
        "required": ["channel"],
        "optional": [],
    }
    labels = _labels(generate_cases(params))
    assert "baseline" in labels
    assert any(l.startswith("draw:channel:") for l in labels)
    assert "missing-required:channel" in labels


@requires_engine
def test_max_cases_cap():
    params = {
        "properties": {f"p{i}": {"type": "string"} for i in range(10)},
        "required": [f"p{i}" for i in range(10)],
        "optional": [],
    }
    assert len(generate_cases(params, max_cases=12)) == 12


@requires_engine
def test_cases_from_signature():
    cases = cases_from_signature(["a", "b"])
    assert cases
    assert any(c["label"] == "missing-required:a" for c in cases)
