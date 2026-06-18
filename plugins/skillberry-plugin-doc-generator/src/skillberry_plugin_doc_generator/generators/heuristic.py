"""Deterministic, dependency-free documentation generator.

This is the plugin's default backend. It synthesizes a consistent
``Documentation`` from the information the store already holds — name, tags,
parameter schemas, referenced tools/snippets, and lightweight signals read out
of the object's own code — with no network and no LLM. That makes the plugin
useful out of the box and every result reproducible in a unit test.

It is intentionally modest: it produces clear, correct, skeletal docs and is
honest (via ``notes``) about what it could not infer. A richer LLM backend can
be injected by the host to replace it; both satisfy the same ``DocGenerator``
interface, so the plugin code is identical either way.
"""

from __future__ import annotations

import re
from typing import List, Optional

from .base import (
    Documentation,
    MODE_ENRICHED,
    MODE_GENERATED,
    MODE_KEPT,
    OBJECT_SKILL,
    OBJECT_SNIPPET,
    OBJECT_TOOL,
    ObjectDoc,
    ParamDoc,
)

# A description shorter than this is treated as "thin" and eligible for enrich.
_THIN_DESCRIPTION_CHARS = 40

_VERB_HINTS = {
    "network": re.compile(r"\b(requests|urllib|httpx|aiohttp|socket)\b"),
    "filesystem": re.compile(
        r"\b(open\s*\(|pathlib|shutil|os\.(remove|rename|mkdir))\b"
    ),
    "subprocess": re.compile(r"\b(subprocess|os\.system|os\.popen)\b"),
    "parsing": re.compile(r"\b(json|csv|yaml|re\.|BeautifulSoup|lxml)\b"),
    "data": re.compile(r"\b(pandas|numpy|sqlite3|sqlalchemy)\b"),
}


def _humanize(name: str) -> str:
    """``send_slack_message`` / ``send-slack-message`` -> ``Send slack message``."""
    words = re.split(r"[_\-\s]+", name.strip())
    words = [w for w in words if w]
    if not words:
        return name
    phrase = " ".join(words)
    return phrase[0].upper() + phrase[1:]


def _is_thin(text: Optional[str]) -> bool:
    return not text or len(text.strip()) < _THIN_DESCRIPTION_CHARS


def _behavior_signals(code_blobs: List[str]) -> List[str]:
    """Coarse capability tags inferred from code (e.g. 'network', 'parsing')."""
    found: List[str] = []
    joined = "\n".join(code_blobs)
    for label, pat in _VERB_HINTS.items():
        if pat.search(joined):
            found.append(label)
    return found


class HeuristicGenerator:
    """Deterministic generator — the dependency-free default backend."""

    name = "heuristic"

    def generate(
        self, obj: ObjectDoc, existing: Optional[Documentation]
    ) -> Documentation:
        author_desc = (obj.description or "").strip()
        doc = Documentation()

        # ── description ──────────────────────────────────────────────────────
        if not _is_thin(author_desc):
            # Good author content: keep it verbatim (non-destructive).
            doc.description = author_desc
            doc.mode = MODE_KEPT
        elif author_desc:
            # Thin author content: enrich rather than discard.
            doc.description = self._enrich_description(obj, author_desc)
            doc.mode = MODE_ENRICHED
        else:
            doc.description = self._synthesize_description(obj)
            doc.mode = MODE_GENERATED

        # ── when-to-use ──────────────────────────────────────────────────────
        doc.when_to_use = self._when_to_use(obj)

        # ── parameters ───────────────────────────────────────────────────────
        doc.parameters = self._document_parameters(obj)

        # ── examples ─────────────────────────────────────────────────────────
        doc.examples = self._examples(obj)

        # ── honesty notes ────────────────────────────────────────────────────
        if obj.object_type == OBJECT_TOOL and not obj.parameters:
            doc.notes.append("No parameter schema found; parameter docs omitted.")
        if not obj.code_blobs and obj.object_type != OBJECT_SKILL:
            doc.notes.append(
                "No code/content available to inspect; docs are metadata-only."
            )
        return doc

    # ── description helpers ───────────────────────────────────────────────────

    def _synthesize_description(self, obj: ObjectDoc) -> str:
        base = _humanize(obj.name)
        signals = _behavior_signals(obj.code_blobs)
        if obj.object_type == OBJECT_SKILL:
            ref_note = (
                f" Orchestrates {len(obj.references)} referenced object(s)."
                if obj.references
                else ""
            )
            return f"{base}. A skill packaging instructions and resources.{ref_note}".strip()
        if obj.object_type == OBJECT_TOOL:
            cap = f" Involves: {', '.join(signals)}." if signals else ""
            return f"{base}. A callable tool.{cap}".strip()
        # snippet
        cap = f" Involves: {', '.join(signals)}." if signals else ""
        return f"{base}. A reusable content snippet.{cap}".strip()

    def _enrich_description(self, obj: ObjectDoc, author_desc: str) -> str:
        """Keep the author's words; append inferred capability context."""
        signals = _behavior_signals(obj.code_blobs)
        suffix = f" Involves: {', '.join(signals)}." if signals else ""
        text = author_desc.rstrip(".")
        return f"{text}.{suffix}".strip()

    # ── section helpers ───────────────────────────────────────────────────────

    def _when_to_use(self, obj: ObjectDoc) -> str:
        subject = _humanize(obj.name).lower()
        tag_hint = ""
        if obj.tags:
            visible = [t for t in obj.tags if ":" not in t][:3]
            if visible:
                tag_hint = f" Relevant for: {', '.join(visible)}."
        kind = {
            OBJECT_SKILL: "perform this workflow",
            OBJECT_TOOL: "invoke this capability",
            OBJECT_SNIPPET: "reuse this content",
        }.get(obj.object_type, "use this object")
        return f"Use when you need to {kind} ({subject}).{tag_hint}".strip()

    def _document_parameters(self, obj: ObjectDoc) -> List[ParamDoc]:
        out: List[ParamDoc] = []
        for p in obj.parameters:
            desc = p.description.strip() if p.description else ""
            if not desc:
                req = "Required" if p.required else "Optional"
                typ = f" {p.type}" if p.type else ""
                desc = f"{req}{typ} parameter '{p.name}'."
            out.append(
                ParamDoc(
                    name=p.name,
                    type=p.type,
                    required=p.required,
                    description=desc,
                )
            )
        return out

    def _examples(self, obj: ObjectDoc) -> List[str]:
        if obj.object_type == OBJECT_TOOL:
            args = (
                ", ".join(f"{p.name}=..." for p in obj.parameters if p.required)
                or "..."
            )
            return [f"{obj.name}({args})"]
        if obj.object_type == OBJECT_SKILL:
            return [f"Load the '{obj.name}' skill and follow its instructions."]
        return [f"Reuse the '{obj.name}' snippet inline where its content is needed."]
