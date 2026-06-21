"""Dependency-report shapes + constants for the resolver engine.

The engine discovers an object's external Python dependencies and assembles a
``DependencyReport``, which serializes to the hierarchical ``extra["dependencies"]``
block the plugin persists. Everything here is pure and JSON-friendly so the engine
can be unit-tested offline; ``generated_at`` is injected by the plugin (not computed
here) to keep serialized output deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = 1
RESOLVER_NAME = "hybrid"

OBJECT_TYPES = ("skill", "tool", "snippet")

# Languages the resolver can inspect. Anything else is recorded in
# ``skipped_files`` with reason ``unsupported_language``.
LANG_PYTHON = "python"
LANG_SHELL = "shell"
SUPPORTED_LANGUAGES = (LANG_PYTHON, LANG_SHELL)

# Sentinel "from" node for direct (depth-0) edges in the dependency tree.
ROOT = "<root>"

# package source / pypi status vocabularies
SOURCE_LOCAL = "local"  # python dist resolved from the local environment
SOURCE_PYPI = "pypi"
SOURCE_SYSTEM = "system"  # shell command / external executable (no version/hash)
SOURCE_UNRESOLVED = "unresolved"

PYPI_OK = "ok"
PYPI_ERROR = "error"
PYPI_TIMEOUT = "timeout"
PYPI_NOT_FOUND = "not_found"
PYPI_SKIPPED = "skipped"

# Why an import could not be resolved to an installed external distribution.
REASON_NOT_INSTALLED = "not_installed"  # real external pkg, just absent here
REASON_NO_DISTRIBUTION = "no_distribution"  # nothing installed provides it
REASON_LOCAL_MODULE = "local_module"  # first-party module bundled in the object
# Reasons that are NOT a missing external dependency (so excluded from the
# actionable "missing" count).
NON_MISSING_REASONS = (REASON_LOCAL_MODULE,)


@dataclass
class PackageDep:
    """One resolved distribution in the dependency graph."""

    name: str
    version: Optional[str] = None  # local installed version = source of truth
    source: str = SOURCE_LOCAL
    language: str = LANG_PYTHON  # which ecosystem this dependency belongs to
    direct: bool = False  # imported directly by the object's own code
    depth: int = 0  # 0 = direct; min BFS distance from a root otherwise
    local_hashes: List[Dict[str, str]] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)  # child dist names
    pypi: Optional[Dict[str, Any]] = None  # None until/unless enriched

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "language": self.language,
            "direct": self.direct,
            "depth": self.depth,
            "local_hashes": sorted(self.local_hashes, key=lambda h: h.get("file", "")),
            "requires": sorted(self.requires),
            "pypi": self.pypi,
        }


@dataclass
class DependencyReport:
    """Full resolved graph for an object, plus anything that couldn't be mapped."""

    packages: Dict[str, PackageDep] = field(default_factory=dict)
    edges: List[Tuple[str, str, int]] = field(default_factory=list)
    unresolved: List[Dict[str, str]] = field(default_factory=list)
    # Files we could not inspect because their language is unsupported (or the
    # content was unidentifiable). Each: {file, language, reason}.
    skipped_files: List[Dict[str, str]] = field(default_factory=list)
    # Languages actually inspected (e.g. {"python", "shell"}).
    languages_seen: set = field(default_factory=set)

    # ── assembly helpers (used by the engine while resolving) ────────────────

    def add_edge(self, src: str, dst: str, depth: int) -> None:
        edge = (src, dst, depth)
        if edge not in self.edges:
            self.edges.append(edge)

    def add_unresolved(self, import_name: str, reason: str) -> None:
        entry = {"import_name": import_name, "reason": reason}
        if entry not in self.unresolved:
            self.unresolved.append(entry)

    def add_skipped(self, file: str, language: str, reason: str) -> None:
        entry = {"file": file, "language": language, "reason": reason}
        if entry not in self.skipped_files:
            self.skipped_files.append(entry)

    # ── serialization ────────────────────────────────────────────────────────

    def _pypi_status(self) -> str:
        """Roll per-package pypi.status up into ok | partial | skipped."""
        statuses = [
            (p.pypi or {}).get("status")
            for p in self.packages.values()
            if p.pypi is not None
        ]
        if not statuses:
            return PYPI_SKIPPED
        if all(s == PYPI_OK for s in statuses):
            return PYPI_OK
        if any(s == PYPI_OK for s in statuses):
            return "partial"
        return PYPI_SKIPPED

    def _update_available_count(self) -> int:
        return sum(
            1 for p in self.packages.values() if (p.pypi or {}).get("update_available")
        )

    def _missing_count(self) -> int:
        """Unresolved imports that are genuinely missing EXTERNAL deps.

        Excludes first-party bundled modules (``local_module``), which are not
        dependencies at all — only actionable "this package isn't available"
        cases are counted.
        """
        return sum(
            1 for u in self.unresolved if u.get("reason") not in NON_MISSING_REASONS
        )

    def _local_module_count(self) -> int:
        return sum(1 for u in self.unresolved if u.get("reason") == REASON_LOCAL_MODULE)

    def to_extra_block(
        self,
        *,
        generated_at: str,
        plugin_version: str,
        python_version: str,
    ) -> Dict[str, Any]:
        """Assemble the deterministic ``extra["dependencies"]`` block."""
        direct = sorted(n for n, p in self.packages.items() if p.direct)
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
            "supported_languages": list(SUPPORTED_LANGUAGES),
            "languages_inspected": sorted(self.languages_seen),
            "scanner": {
                "plugin_version": plugin_version,
                "resolver": RESOLVER_NAME,
                "python_version": python_version,
            },
            "summary": {
                "direct_count": len(direct),
                "total_count": len(self.packages),
                "unresolved_count": len(self.unresolved),
                "missing_count": self._missing_count(),
                "local_module_count": self._local_module_count(),
                "skipped_count": len(self.skipped_files),
                "update_available_count": self._update_available_count(),
                "pypi_status": self._pypi_status(),
            },
            "packages": {
                name: self.packages[name].to_dict() for name in sorted(self.packages)
            },
            "tree": [
                {"from": s, "to": d, "depth": dep} for s, d, dep in sorted(self.edges)
            ],
            "unresolved_imports": sorted(
                self.unresolved, key=lambda u: u.get("import_name", "")
            ),
            "skipped_files": sorted(
                self.skipped_files, key=lambda s: s.get("file", "")
            ),
        }

    def summary_tags(self) -> List[str]:
        """Short, scannable tags for the generic plugin UI / search."""
        tags = [
            f"dep:count:{len(self.packages)}",
            f"dep:unresolved:{len(self.unresolved)}",
        ]
        missing = self._missing_count()
        if missing:
            tags.append(f"dep:missing:{missing}")
        if self.skipped_files:
            tags.append(f"dep:skipped:{len(self.skipped_files)}")
        for lang in sorted(self.languages_seen):
            tags.append(f"dep:lang:{lang}")
        if self._update_available_count():
            tags.append("dep:update-available")
        return tags
