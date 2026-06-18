"""Documentation shape + generator interface.

The store curates three object types (skills, tools, snippets) whose docs today
drift and have no common shape (issue #201). This module defines:

  - ``Documentation``: the single, consistent documentation shape produced for
    every object type — description, when-to-use, parameter docs, examples.
  - ``ObjectDoc``: the normalized view of a store object the generators read
    from, so a generator never has to know skill-vs-tool-vs-snippet plumbing.
  - ``DocGenerator``: the interface a generation backend implements. The plugin
    ships a deterministic, dependency-free default (``heuristic``); an LLM
    backend can be injected by the host without changing the plugin.

The shape is intentionally JSON-friendly (``to_dict``) so it can be persisted in
``extra["documentation"]`` and rendered uniformly in the UI.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Object types this plugin documents.
OBJECT_SKILL = "skill"
OBJECT_TOOL = "tool"
OBJECT_SNIPPET = "snippet"
OBJECT_TYPES = (OBJECT_SKILL, OBJECT_TOOL, OBJECT_SNIPPET)

# How a doc was produced relative to any author-written content.
MODE_GENERATED = "generated"  # nothing usable existed; created from scratch
MODE_ENRICHED = "enriched"  # thin author content expanded, not discarded
MODE_KEPT = "kept"  # author content already sufficient; left as-is


@dataclass
class ParamDoc:
    """Documentation for a single input/parameter of an object."""

    name: str
    type: Optional[str] = None
    required: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "description": self.description,
        }


@dataclass
class Documentation:
    """The consistent documentation shape produced for any object type."""

    description: str = ""
    when_to_use: str = ""
    parameters: List[ParamDoc] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    # How this doc relates to pre-existing author content (see MODE_* above).
    mode: str = MODE_GENERATED
    # Free-form notes the generator wants to surface (e.g. "no params found").
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "when_to_use": self.when_to_use,
            "parameters": [p.to_dict() for p in self.parameters],
            "examples": list(self.examples),
            "mode": self.mode,
            "notes": list(self.notes),
        }

    def is_empty(self) -> bool:
        """True when the generator could not produce anything meaningful."""
        return not (
            self.description or self.when_to_use or self.parameters or self.examples
        )


@dataclass
class ObjectDoc:
    """Normalized, type-agnostic view of a store object for the generators.

    The plugin builds this from a raw store object so generators stay decoupled
    from how skills/tools/snippets are stored. ``source_fingerprint`` is a hash
    of the inputs that documentation is derived from — when it changes, existing
    docs are stale (drift).
    """

    object_type: str
    uuid: str
    name: str
    description: str = ""  # author-written description, if any
    tags: List[str] = field(default_factory=list)
    parameters: List[ParamDoc] = field(default_factory=list)
    # Raw code / inline content blobs that describe behavior.
    code_blobs: List[str] = field(default_factory=list)
    # For skills: short summaries of referenced tools/snippets.
    references: List[str] = field(default_factory=list)

    def source_fingerprint(self) -> str:
        """Stable hash over the inputs documentation is derived from.

        Deliberately excludes the author description so that *enriching* docs
        does not by itself look like source drift; it tracks code, parameters,
        and references — the things that make docs go *wrong* when they change.
        """
        h = hashlib.sha256()
        h.update(self.object_type.encode())
        h.update(b"\x00")
        h.update(self.name.encode("utf-8", "replace"))
        for p in self.parameters:
            h.update(b"\x00param\x00")
            h.update(f"{p.name}:{p.type}:{p.required}".encode("utf-8", "replace"))
        for blob in self.code_blobs:
            h.update(b"\x00code\x00")
            h.update(blob.encode("utf-8", "replace"))
        for ref in self.references:
            h.update(b"\x00ref\x00")
            h.update(ref.encode("utf-8", "replace"))
        return h.hexdigest()


class DocGenerator:
    """Interface a documentation backend implements.

    Backends must be pure with respect to the store: they receive a fully
    materialized ``ObjectDoc`` and return a ``Documentation``. They never read
    or write the store themselves — the plugin owns all persistence — which
    keeps every backend trivially unit-testable.
    """

    name = "base"

    def generate(
        self, obj: ObjectDoc, existing: Optional[Documentation]
    ) -> Documentation:
        """Produce documentation for ``obj``.

        ``existing`` is the previously stored Documentation when enriching/
        refreshing (else ``None``). Implementations should preserve good
        author-written content from ``obj.description`` / ``existing`` rather
        than discarding it (non-destructive — issue #201, item 5).
        """
        raise NotImplementedError
