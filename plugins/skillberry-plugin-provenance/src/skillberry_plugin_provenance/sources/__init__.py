"""Provenance source registry and resolution."""

from typing import Any, Dict, List, Optional

from .base import Background, ProvenanceSource, license_category
from .github_source import GitHubSource, parse_github_origin

# Ordered list of source classes. Resolution returns the first that matches.
SOURCE_CLASSES = [GitHubSource]


def resolve_source(origin: Dict[str, Any]) -> Optional[ProvenanceSource]:
    """Return an instantiated source that can handle ``origin``, or None."""
    for cls in SOURCE_CLASSES:
        src = cls()
        if src.matches(origin):
            return src
    return None


__all__ = [
    "Background",
    "ProvenanceSource",
    "GitHubSource",
    "parse_github_origin",
    "license_category",
    "resolve_source",
    "SOURCE_CLASSES",
]
