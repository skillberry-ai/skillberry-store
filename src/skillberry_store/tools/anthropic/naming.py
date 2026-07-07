"""Shared naming rules for Anthropic / `npx skills` compatible skill slugs.

Both the Anthropic on-disk skill convention (folder name == frontmatter `name`)
and the `skills` CLI expect the skill's directory / entry name to be a slug
matching ``[a-z0-9]+(-[a-z0-9]+)*``. Skillberry skill names are free text,
so we validate rather than silently rewrite: callers that opt into a strict
export must fix the name upstream, or explicitly pass ``allow_invalid_name``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SLUG_MAX_LEN = 64


@dataclass(frozen=True)
class SlugValidation:
    """Result of validating a skill name against the slug rules.

    Attributes:
        ok: True when the name is a valid slug.
        suggested: A best-effort slugified version of the input, suitable for
            surfacing to a user as a rename suggestion. Empty when no
            reasonable slug can be derived.
        reason: Human-readable explanation of why the name failed validation,
            or an empty string when ``ok`` is True.
    """

    ok: bool
    suggested: str
    reason: str


def suggest_slug(name: str) -> str:
    """Return a best-effort slug for ``name``.

    Lower-cases, replaces runs of non-alphanumerics with a single hyphen, and
    trims leading/trailing hyphens. Returns an empty string when nothing
    remains (e.g. ``"---"`` or ``""``).
    """
    if not name:
        return ""
    lowered = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if len(slug) > SLUG_MAX_LEN:
        slug = slug[:SLUG_MAX_LEN].rstrip("-")
    return slug


def validate_skill_slug(name: Optional[str]) -> SlugValidation:
    """Validate ``name`` against the slug rules.

    Args:
        name: Candidate skill name.

    Returns:
        SlugValidation: See dataclass docstring.
    """
    if name is None or name == "":
        return SlugValidation(
            ok=False,
            suggested="",
            reason="Skill name is empty.",
        )
    if len(name) > SLUG_MAX_LEN:
        return SlugValidation(
            ok=False,
            suggested=suggest_slug(name),
            reason=f"Skill name exceeds {SLUG_MAX_LEN} characters.",
        )
    if not SLUG_RE.match(name):
        return SlugValidation(
            ok=False,
            suggested=suggest_slug(name),
            reason=(
                "Skill name must match [a-z0-9]+(-[a-z0-9]+)* "
                "(lowercase letters, digits, and single hyphens between them)."
            ),
        )
    return SlugValidation(ok=True, suggested=name, reason="")
