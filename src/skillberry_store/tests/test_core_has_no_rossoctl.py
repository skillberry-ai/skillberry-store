"""Core never knows rossoctl.

Everything rossoctl-specific lives in the optional ``rossoctl-tools`` plugin
(docs/design/rossoctl-skills.md §4.0, D3); core only defines rossoctl-agnostic
extension points. This guard fails on any mention in core source outside
tests and contrib.
"""

from pathlib import Path

CORE = Path(__file__).resolve().parents[1]  # src/skillberry_store
FORBIDDEN = ("rossoctl", "svc.cluster.local")
SKIP_DIRS = {"tests", "contrib", "node_modules", "dist", "__pycache__"}
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".json", ".yaml", ".yml", ".md", ".toml"}


def _core_files():
    for path in CORE.rglob("*"):
        rel = path.relative_to(CORE)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            yield path


def test_core_has_no_rossoctl_reference():
    hits = []
    for path in _core_files():
        try:
            text = path.read_text(encoding="utf-8").lower()
        except UnicodeDecodeError:
            continue
        for needle in FORBIDDEN:
            if needle in text:
                hits.append(f"{path.relative_to(CORE)}: {needle}")
    assert not hits, "core must not reference rossoctl:\n" + "\n".join(hits)
