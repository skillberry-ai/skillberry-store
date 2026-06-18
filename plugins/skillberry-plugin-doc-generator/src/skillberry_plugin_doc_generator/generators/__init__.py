"""Documentation generation backends.

The plugin resolves a backend by name. The dependency-free ``heuristic`` backend
is always available; a host can register/inject an LLM-backed generator under a
different name without touching the plugin.
"""

from typing import Optional

from .base import (
    DocGenerator,
    Documentation,
    ObjectDoc,
    ParamDoc,
)
from .heuristic import HeuristicGenerator

__all__ = [
    "DocGenerator",
    "Documentation",
    "ObjectDoc",
    "ParamDoc",
    "HeuristicGenerator",
    "resolve_generator",
]


def resolve_generator(name: Optional[str] = None) -> DocGenerator:
    """Return a generator backend.

    Policy (no UI, env-driven — matches the security evaluator plugin):
      - ``name="heuristic"``  -> always the deterministic backend.
      - ``name="llm"``        -> the LLM backend, or heuristic if unavailable.
      - ``name`` unset/auto   -> use the LLM backend **iff** an LLM is configured
        (``llm-switchboard`` installed and the provider's API key present),
        otherwise the deterministic heuristic. This keeps the default behavior
        unchanged unless a key exists.
    """
    if name in ("heuristic", "default"):
        return HeuristicGenerator()

    if name in (None, "", "llm", "auto"):
        # Lazy import so the plugin never hard-depends on switchboard.
        try:
            from .llm import LLMGenerator, build_llm_client
        except Exception:
            return HeuristicGenerator()
        built = build_llm_client()
        if built is not None:
            client, label = built
            return LLMGenerator(client, label)
        return HeuristicGenerator()

    # Unknown name: degrade to the always-available default rather than raise.
    return HeuristicGenerator()
