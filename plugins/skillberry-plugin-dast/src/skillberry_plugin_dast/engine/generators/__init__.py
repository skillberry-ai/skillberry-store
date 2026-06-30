"""Input-generator engine registry (pluggable, optional — cf. SAST engines).

The DAST scanner is generator-agnostic: it consumes the neutral ``{label, args}``
case shape and never imports a specific fuzzer. Engines register here; a
different fuzzer is added by implementing :class:`InputGenerator` and adding it
to ``GENERATOR_REGISTRY`` — no change to the plugin core.

Selection:
  - ``DAST_GENERATOR`` env var picks an engine by name when set.
  - Otherwise the first *available* (installed) registered engine is used.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Type

from .base import InputGenerator
from .hypothesis_generator import HypothesisGenerator

# Add new engines here, e.g. SchemathesisGenerator.name: SchemathesisGenerator
GENERATOR_REGISTRY: Dict[str, Type[InputGenerator]] = {
    HypothesisGenerator.name: HypothesisGenerator,
}

_ENV_SELECT = "DAST_GENERATOR"

__all__ = [
    "InputGenerator",
    "HypothesisGenerator",
    "GENERATOR_REGISTRY",
    "registered_generator_names",
    "available_generators",
    "resolve_generator",
    "any_generator_available",
    "status_message",
]


def registered_generator_names() -> List[str]:
    """All engine names known to the registry (installed or not)."""
    return list(GENERATOR_REGISTRY.keys())


def _instantiate(name: str) -> Optional[InputGenerator]:
    cls = GENERATOR_REGISTRY.get(name)
    return cls() if cls is not None else None


def available_generators() -> List[InputGenerator]:
    """Registered engines whose dependency is actually installed."""
    out: List[InputGenerator] = []
    for name in GENERATOR_REGISTRY:
        eng = _instantiate(name)
        if eng is not None and eng.is_available():
            out.append(eng)
    return out


def resolve_generator(name: Optional[str] = None) -> Optional[InputGenerator]:
    """Return the engine to use, or ``None`` if none is available.

    ``name`` (or the ``DAST_GENERATOR`` env var) selects a specific engine; it
    must be registered AND available. With no selection, the first available
    registered engine is returned.
    """
    selected = name or os.getenv(_ENV_SELECT)
    if selected:
        eng = _instantiate(selected)
        if eng is not None and eng.is_available():
            return eng
        return None
    avail = available_generators()
    return avail[0] if avail else None


def any_generator_available() -> bool:
    """True if a generator can be resolved (respecting DAST_GENERATOR)."""
    return resolve_generator() is not None


def status_message() -> str:
    """Status string for the plugin: which engine is active, or how to enable one."""
    eng = resolve_generator()
    if eng is not None:
        return f"Ready (input generator: {eng.name})"
    selected = os.getenv(_ENV_SELECT)
    known = registered_generator_names()
    if selected and selected not in GENERATOR_REGISTRY:
        return (
            f"Disabled: {_ENV_SELECT}={selected!r} is not a registered generator "
            f"(known: {known})"
        )
    hint = ""
    # Offer the install hint of the (selected or first) known engine.
    target = (
        selected if selected in GENERATOR_REGISTRY else (known[0] if known else None)
    )
    if target:
        eng_cls = GENERATOR_REGISTRY.get(target)
        if eng_cls is not None:
            hint = "; " + eng_cls().install_hint()
    return f"Disabled: no input-generator engine installed{hint}"
