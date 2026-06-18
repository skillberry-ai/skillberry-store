"""Dependency resolution engine (Python + shell).

``build_resolver()`` returns a facade that runs the full pipeline over a set of
``(filename, code)`` blobs:

  - detect each blob's language (python / shell / unsupported)
  - python  -> extract imports -> resolve locally (transitive, max depth) ->
               best-effort PyPI enrichment
  - shell   -> extract external command names (system deps; no version/hash)
  - unsupported -> recorded in ``report.skipped_files``

Each stage lives in its own module and is independently unit-testable.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

from .base import (
    LANG_PYTHON,
    LANG_SHELL,
    ROOT,
    SOURCE_SYSTEM,
    DependencyReport,
    PackageDep,
)
from .imports import extract_top_level_imports
from .languages import detect_language
from .local import resolve_local
from .pypi import DEFAULT_TIMEOUT, enrich_report, pypi_enabled_from_env
from .shell import extract_shell_commands

__all__ = [
    "DependencyReport",
    "PackageDep",
    "extract_top_level_imports",
    "extract_shell_commands",
    "detect_language",
    "resolve_local",
    "enrich_report",
    "Resolver",
    "build_resolver",
]

# A code blob the plugin hands to the engine: its source filename (for language
# detection + skipped-file reporting) and the source text.
Blob = Tuple[str, str]  # (filename, code)


class Resolver:
    """Runs language detection -> per-language extraction -> enrichment."""

    def __init__(self, pypi_enabled: bool = True, timeout: float = DEFAULT_TIMEOUT):
        self.pypi_enabled = pypi_enabled
        self.timeout = timeout

    def scan(
        self, blobs: Iterable[Blob], local_modules: Optional[set] = None
    ) -> DependencyReport:
        """Resolve dependencies across ``(filename, code)`` blobs.

        ``local_modules`` is the set of top-level module names bundled with the
        object itself (first-party code); imports matching them are classified
        ``local_module`` rather than reported as missing external deps.

        Synchronous (PyPI uses blocking ``requests``); the plugin offloads this to
        a thread so it never blocks the event loop.
        """
        py_imports: set = set()
        shell_cmds: set = set()
        report = DependencyReport()

        for filename, code in blobs:
            lang = detect_language(filename, code or "")
            if lang == LANG_PYTHON:
                report.languages_seen.add(LANG_PYTHON)
                py_imports |= extract_top_level_imports(code or "")
            elif lang == LANG_SHELL:
                report.languages_seen.add(LANG_SHELL)
                shell_cmds |= extract_shell_commands(code or "")
            else:
                report.add_skipped(
                    filename or "<unknown>",
                    "unknown",
                    "unsupported_language",
                )

        # Python: resolve locally into a fresh report, then fold into ours.
        if py_imports:
            py_report = resolve_local(py_imports, local_modules=local_modules)
            enrich_report(py_report, enabled=self.pypi_enabled, timeout=self.timeout)
            self._merge(report, py_report)

        # Shell: each external command is a direct, system-source dependency.
        for cmd in sorted(shell_cmds):
            if cmd in report.packages:
                report.packages[cmd].direct = True
            else:
                report.packages[cmd] = PackageDep(
                    name=cmd,
                    version=None,
                    source=SOURCE_SYSTEM,
                    language=LANG_SHELL,
                    direct=True,
                    depth=0,
                )
            report.add_edge(ROOT, cmd, 0)

        return report

    @staticmethod
    def _merge(into: DependencyReport, other: DependencyReport) -> None:
        into.packages.update(other.packages)
        for e in other.edges:
            into.add_edge(*e)
        for u in other.unresolved:
            into.add_unresolved(u["import_name"], u["reason"])


def build_resolver(
    pypi_enabled: Optional[bool] = None, timeout: float = DEFAULT_TIMEOUT
) -> Resolver:
    """Construct a Resolver. ``pypi_enabled=None`` consults the environment."""
    if pypi_enabled is None:
        pypi_enabled = pypi_enabled_from_env()
    return Resolver(pypi_enabled=pypi_enabled, timeout=timeout)
