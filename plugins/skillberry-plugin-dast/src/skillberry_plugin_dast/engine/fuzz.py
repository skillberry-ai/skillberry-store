"""Adversarial input generation — delegates to a pluggable, optional engine.

This module is a thin facade over the generator registry in ``generators/``. The
actual fuzzing/input-generation is done by whichever :class:`InputGenerator`
engine is registered + available (Hypothesis ships as the first one). A different
fuzzer is plugged in by adding an engine to ``GENERATOR_REGISTRY`` — nothing here
or in the plugin core changes.

If no engine is available the scanner is disabled (the plugin gates on
``generator_available()``); there is no proprietary fallback generator.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .generators import (
    any_generator_available,
    registered_generator_names,
    resolve_generator,
    status_message,
)

# Kept for back-compat / status display: the set of engines the build knows of.
GENERATOR_NAMES = registered_generator_names()
# Historic single-name constant (first registered engine).
GENERATOR_NAME = GENERATOR_NAMES[0] if GENERATOR_NAMES else ""


def generator_available() -> bool:
    """True iff some registered input-generator engine is installed/usable."""
    return any_generator_available()


def generator_status() -> str:
    """Human-readable engine status for the plugin's status message."""
    return status_message()


def generate_cases(
    params: Dict[str, Any], *, seed: int = 1729, max_cases: int = 24
) -> List[Dict[str, Any]]:
    """Generate adversarial input cases via the resolved engine.

    Callers gate on :func:`generator_available`. The no-parameter case needs no
    engine, so it is handled here to keep that path engine-free.
    """
    if not (params.get("properties") or {}):
        return [{"label": "no-args", "args": {}}]
    engine = resolve_generator()
    if engine is None:
        raise RuntimeError("no input-generator engine available")
    return engine.generate_cases(params, seed=seed, max_cases=max_cases)


def cases_from_signature(
    signature: List[str], *, seed: int = 1729, max_cases: int = 24
) -> List[Dict[str, Any]]:
    """Generate cases from a bare signature (Tier-2 callables) via the engine."""
    if not signature:
        return [{"label": "no-args", "args": {}}]
    engine = resolve_generator()
    if engine is None:
        raise RuntimeError("no input-generator engine available")
    return engine.cases_from_signature(signature, seed=seed, max_cases=max_cases)
