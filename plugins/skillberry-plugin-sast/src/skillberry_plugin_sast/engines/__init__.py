"""SAST engine registry.

Adding a new engine is a single entry here plus its module — the plugin and the
API surface (selectable engine names) are driven off this registry.
"""

from typing import Dict, List, Tuple, Type

from .base import Finding, SastEngine
from .bandit_engine import BanditEngine

# name -> engine class. The keys are the values accepted in `engines: [...]`
# requests and in the SBS_SAST_ENGINES env var.
ENGINE_REGISTRY: Dict[str, Type[SastEngine]] = {
    BanditEngine.name: BanditEngine,
    # Future engines slot in here, e.g.:
    #   SemgrepEngine.name: SemgrepEngine,
}


def available_engine_names() -> List[str]:
    """All engine names known to the registry (installed or not)."""
    return list(ENGINE_REGISTRY.keys())


def get_engines(names: List[str]) -> Tuple[List[SastEngine], List[str]]:
    """Resolve engine names to instances.

    Returns ``(resolved, unknown)`` where ``resolved`` are instantiated engines
    for names present in the registry, and ``unknown`` are names with no
    registered engine. Availability (whether the tool is installed) is NOT
    checked here — the caller reports per-engine status so a missing tool is
    skipped-and-reported rather than fatal.
    """
    resolved: List[SastEngine] = []
    unknown: List[str] = []
    for name in names:
        cls = ENGINE_REGISTRY.get(name)
        if cls is None:
            unknown.append(name)
        else:
            resolved.append(cls())
    return resolved, unknown


__all__ = [
    "Finding",
    "SastEngine",
    "BanditEngine",
    "ENGINE_REGISTRY",
    "available_engine_names",
    "get_engines",
]
