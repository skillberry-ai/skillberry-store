"""Shared name validation for store entities that are exposed as MCP servers
or become positional-argument tokens (skills, VMCPs, external MCP servers).

We enforce Anthropic's Agent Skills SKILL.md `name` format — the same slug
shape the upstream `claude mcp add <name> …` CLI and URL segments expect:

  ^[a-z0-9-]{1,64}$

Lowercase letters, digits, and hyphens only; 1 to 64 characters. This rules
out spaces, uppercase, underscores, dots, slashes, and every other punctuation
that would either break a positional CLI arg or fail a URL-segment parse.

Source: https://code.claude.com/docs/en/skills — Frontmatter reference
("Lowercase letters, numbers, and hyphens only (max 64 characters).")

Callers typically:

    from skillberry_store.schemas.name_validation import validate_store_name
    validate_store_name(name, kind="skill")   # raises HTTPException(400, …) on invalid
"""

from __future__ import annotations

import re
from typing import Any, Dict

from fastapi import HTTPException

# Anthropic Agent Skills naming spec.
STORE_NAME_PATTERN = r"^[a-z0-9-]{1,64}$"
STORE_NAME_RE = re.compile(STORE_NAME_PATTERN)


def is_valid_store_name(name: str) -> bool:
    return isinstance(name, str) and bool(STORE_NAME_RE.fullmatch(name))


def format_hint(kind: str) -> str:
    return (
        f"{kind} names must match the Anthropic Agent Skills format: "
        f"lowercase letters, digits, and hyphens (-) only; 1 to 64 characters. "
        f"No spaces, underscores, uppercase, dots, or other punctuation. "
        f"Examples: 'docs-research', 'context7', 'pdf-to-markdown'."
    )


def validate_store_name(name: Any, kind: str = "name") -> None:
    """Validate a name used as an MCP/CLI identifier; raise HTTP 400 otherwise.

    `kind` is a human label used in the error ("skill", "VMCP server",
    "external MCP", "tool", ...).
    """
    if not isinstance(name, str) or not name:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_name",
                "kind": kind,
                "name": name,
                "hint": format_hint(kind),
            },
        )
    if not STORE_NAME_RE.fullmatch(name):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_name",
                "kind": kind,
                "name": name,
                "hint": format_hint(kind),
                "pattern": STORE_NAME_PATTERN,
            },
        )


def slugify_store_name(name: Any) -> str | None:
    """Best-effort conversion of an arbitrary name to the Anthropic slug format.

    Lowercases, replaces runs of underscores/whitespace/dots with a single
    hyphen, and strips every character that is not a lowercase letter, digit,
    or hyphen. Collapses repeat hyphens and trims leading/trailing ones, then
    truncates to 64 characters.

    Returns the slug if it is a valid store name, otherwise None. This is for
    external sources where we cannot ask the user to correct the name (e.g.
    Anthropic skill importer pulling a SKILL.md `name` field).
    """
    if not isinstance(name, str):
        return None
    slug = name.strip().lower()
    slug = re.sub(r"[\s._]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    slug = slug[:64]
    return slug if is_valid_store_name(slug) else None


def validate_store_name_message(name: Any, kind: str = "name") -> str | None:
    """Non-raising variant. Returns None if valid, or a message string if not.

    Convenient for curated MCP tools that return JSON error strings instead
    of HTTP responses.
    """
    if not isinstance(name, str) or not name or not STORE_NAME_RE.fullmatch(name):
        return (
            f"Invalid {kind} name {name!r}. {format_hint(kind)} "
            f"(pattern: {STORE_NAME_PATTERN})"
        )
    return None
