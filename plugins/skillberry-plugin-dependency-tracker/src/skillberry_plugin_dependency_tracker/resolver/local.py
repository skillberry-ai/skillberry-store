"""Local dependency resolution via ``importlib.metadata`` (the source of truth).

This resolves what the object *actually runs against* in the current
environment: the installed version of each distribution, the per-file hashes
recorded in its ``RECORD``, and its transitive ``Requires-Dist`` graph walked at
**maximum depth** with cycle/diamond protection.

It is deliberately decoupled from the store and from the network so it is
trivially unit-testable. PyPI enrichment is layered on separately in ``pypi.py``.
"""

from __future__ import annotations

import re
from importlib import metadata as importlib_metadata
from typing import Dict, List, Optional, Set

from .base import (
    REASON_LOCAL_MODULE,
    REASON_NO_DISTRIBUTION,
    REASON_NOT_INSTALLED,
    ROOT,
    SOURCE_LOCAL,
    SOURCE_UNRESOLVED,
    DependencyReport,
    PackageDep,
)

# A Requires-Dist line looks like e.g.:
#   "urllib3 (>=1.21.1,<3)"
#   "PySocks (>=1.5.6,!=1.5.7) ; extra == 'socks'"
#   "charset-normalizer<4,>=2"
# We want just the bare distribution name at the start of the line.
_DIST_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def _canonical(name: str) -> str:
    """PEP 503 normalization so 'Charset_Normalizer' == 'charset-normalizer'."""
    return re.sub(r"[-_.]+", "-", name or "").lower()


def import_to_distributions(import_name: str) -> List[str]:
    """Map a top-level import name to the distribution(s) that provide it.

    Uses ``packages_distributions()`` (top-level module -> [dist names]). Returns
    an empty list when nothing installed provides the import.
    """
    try:
        mapping = importlib_metadata.packages_distributions()
    except Exception:
        return []
    return list(mapping.get(import_name, []))


def local_version(dist: str) -> Optional[str]:
    try:
        return importlib_metadata.version(dist)
    except importlib_metadata.PackageNotFoundError:
        return None
    except Exception:
        return None


def local_record_hashes(dist: str) -> List[Dict[str, str]]:
    """Per-file hashes from the distribution's RECORD (base64 sha256).

    Returns ``[]`` when the install records no hashes (editable installs, some
    wheels, ``--no-binary`` builds) — the package entry is still valid without them.
    """
    try:
        d = importlib_metadata.distribution(dist)
        files = d.files or []
    except Exception:
        return []
    out: List[Dict[str, str]] = []
    for f in files:
        h = getattr(f, "hash", None)
        if h is None:
            continue
        mode = getattr(h, "mode", None) or "sha256"
        value = getattr(h, "value", None)
        if not value:
            continue
        out.append({"file": str(f), "algorithm": mode, "hash": value})
    return out


# Matches an `extra == '...'` clause anywhere in a marker (regex fallback path).
_EXTRA_MARKER_RE = re.compile(r"extra\s*==")


def _requirement_applies(line: str) -> bool:
    """True if a ``Requires-Dist`` line is a DEFAULT runtime dependency.

    Excludes optional ``extra``-gated requirements (e.g. ``PySocks; extra ==
    'socks'``) and requirements whose environment marker is not satisfied here
    (e.g. ``; python_version < '3.8'``). These are not dependencies of an object
    that merely imports the package — reporting them as "missing" is wrong.

    Uses ``packaging`` when available for correct marker evaluation; otherwise
    falls back to: keep the line unless it carries an ``extra ==`` clause.
    """
    if ";" not in line:
        return True  # no marker -> always a runtime dep
    marker_text = line.split(";", 1)[1].strip()
    if not marker_text:
        return True
    try:
        from packaging.markers import Marker

        marker = Marker(marker_text)
        # Evaluate with NO extras active -> default install profile. `extra` is
        # supplied as empty so any `extra == '...'` clause is False.
        return bool(marker.evaluate({"extra": ""}))
    except Exception:
        # Fallback: only filter the most common over-inclusion (extras).
        return not _EXTRA_MARKER_RE.search(marker_text)


def local_requires(dist: str) -> List[str]:
    """Default runtime dependency distribution names from ``Requires-Dist``.

    Only DEFAULT dependencies are returned: extra-gated and unsatisfied-marker
    requirements are excluded (see ``_requirement_applies``), so optional extras
    of transitive packages are not mistaken for missing dependencies.
    """
    try:
        reqs = importlib_metadata.requires(dist) or []
    except Exception:
        return []
    names: List[str] = []
    for line in reqs:
        if not line or not _requirement_applies(line):
            continue
        m = _DIST_NAME_RE.match(line)
        if m:
            names.append(m.group(1))
    # de-dup, preserve first-seen order
    seen: Set[str] = set()
    ordered: List[str] = []
    for n in names:
        key = _canonical(n)
        if key not in seen:
            seen.add(key)
            ordered.append(n)
    return ordered


def resolve_local(
    import_names: Set[str], local_modules: Optional[Set[str]] = None
) -> DependencyReport:
    """Resolve direct imports + their transitive deps at maximum depth.

    BFS from the direct imports; a ``visited`` set guarantees each distribution is
    expanded once (cycle/diamond safe). Depth is the minimum distance from a root.
    Imports that map to no installed distribution are recorded in
    ``report.unresolved`` rather than dropped.

    ``local_modules`` is the set of top-level module names that are bundled with
    the object itself (first-party code, e.g. a skill's ``helpers``/``office``
    packages). An unmapped import matching one of these is classified
    ``local_module`` — it is NOT a missing external dependency.
    """
    local_modules = {_canonical(m) for m in (local_modules or set())}
    report = DependencyReport()

    def _unresolved_reason(name: str) -> str:
        if _canonical(name) in local_modules:
            return REASON_LOCAL_MODULE
        # known to the env (importable metadata) but not provided as a dist, vs
        # nothing at all installed under that name.
        return (
            REASON_NOT_INSTALLED
            if local_version(name) is not None
            else REASON_NO_DISTRIBUTION
        )

    # Seed the queue with directly-imported distributions.
    # queue items: (dist_name, parent_node, depth, is_direct)
    queue: List = []
    for import_name in sorted(import_names):
        dists = import_to_distributions(import_name)
        if not dists:
            report.add_unresolved(import_name, _unresolved_reason(import_name))
            continue
        for dist in dists:
            queue.append((dist, ROOT, 0, True))

    visited: Set[str] = set()
    while queue:
        dist, parent, depth, direct = queue.pop(0)
        canon = _canonical(dist)

        # Always record the edge (captures diamonds/cycles in the tree).
        report.add_edge(parent, dist, depth)

        if canon in visited:
            # Already expanded; if newly seen as direct, upgrade the flag, and
            # keep the shallowest depth.
            existing = report.packages.get(dist)
            if existing is not None:
                if direct:
                    existing.direct = True
                existing.depth = min(existing.depth, depth)
            continue
        visited.add(canon)

        version = local_version(dist)
        pkg = PackageDep(
            name=dist,
            version=version,
            source=SOURCE_LOCAL if version is not None else SOURCE_UNRESOLVED,
            direct=direct,
            depth=depth,
            local_hashes=local_record_hashes(dist) if version is not None else [],
            requires=local_requires(dist) if version is not None else [],
        )
        report.packages[dist] = pkg

        for child in pkg.requires:
            # Only descend into children that are actually installed; an
            # uninstalled optional dep is noted but not expanded.
            if local_version(child) is None:
                # A declared (non-extra) runtime dep that isn't installed: a
                # genuinely missing external package.
                report.add_unresolved(child, REASON_NOT_INSTALLED)
                report.add_edge(dist, child, depth + 1)
                continue
            queue.append((child, dist, depth + 1, False))

    return report
