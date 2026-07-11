"""Field-projection helpers for the bulk list endpoints.

The list endpoints (``GET /snippets/``, ``GET /skills/``, ``GET /tools/``) can
return slim, list-view-oriented objects when the caller passes
``?fields=list``, or a caller-defined allowlist via
``?fields=uuid,name,description,...``. When no ``fields`` param is set the
endpoints return the full objects — preserving the current behavior for
every existing consumer (CLI, SDK, MCP).

The three presets below intentionally omit only the payload-heavy fields
(snippet ``content``; tool ``params`` / ``returns`` / ``dependencies`` /
``packaging_params``; skill inlined ``tools`` / ``snippets``). Metadata used
by list-view UIs stays in.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

SNIPPET_LIST_FIELDS: Set[str] = {
    "uuid",
    "name",
    "description",
    "state",
    "tags",
    "version",
    "extra",
    "parent",
    "created_at",
    "modified_at",
    "author",
    "content_type",
}

TOOL_LIST_FIELDS: Set[str] = {
    "uuid",
    "name",
    "description",
    "state",
    "tags",
    "version",
    "extra",
    "parent",
    "created_at",
    "modified_at",
    "author",
    "module_name",
    "programming_language",
    "packaging_format",
}

SKILL_LIST_FIELDS: Set[str] = {
    "uuid",
    "name",
    "description",
    "state",
    "tags",
    "version",
    "extra",
    "parent",
    "created_at",
    "modified_at",
    "author",
    "tool_uuids",
    "snippet_uuids",
}

_LIST_PRESETS: Dict[str, Set[str]] = {
    "snippet": SNIPPET_LIST_FIELDS,
    "tool": TOOL_LIST_FIELDS,
    "skill": SKILL_LIST_FIELDS,
}


def parse_fields_spec(
    fields_spec: Optional[str], object_type: str
) -> Optional[Set[str]]:
    """Resolve a ``fields`` query-param value to a concrete field allowlist.

    Args:
        fields_spec: Raw value from the query string. ``None``, empty, or
            ``"full"`` means "no projection — return every field". ``"list"``
            selects the per-type preset. Any other value is parsed as a
            comma-separated allowlist.
        object_type: Object-type key (``"snippet"``, ``"tool"``, ``"skill"``).
            Only consulted when ``fields_spec == "list"``.

    Returns:
        The set of field names to keep, or ``None`` when no projection
        should be applied.

    Raises:
        ValueError: If ``fields_spec == "list"`` but no preset is registered
            for ``object_type``.
    """
    if not fields_spec or fields_spec == "full":
        return None
    if fields_spec == "list":
        preset = _LIST_PRESETS.get(object_type)
        if preset is None:
            raise ValueError(
                f"No list preset registered for object type '{object_type}'"
            )
        return set(preset)
    allow = {f.strip() for f in fields_spec.split(",") if f.strip()}
    return allow or None


def project_item(
    item: Dict[str, Any], allow: Optional[Set[str]]
) -> Dict[str, Any]:
    """Return a projected view of ``item``.

    When ``allow`` is ``None`` the input dict is returned unchanged (the
    caller must not mutate it — cache values are shared references). When
    ``allow`` is a set, a fresh dict is returned containing only those keys
    that both appear in ``item`` and in ``allow`` — safe to mutate.
    """
    if allow is None:
        return item
    return {k: item[k] for k in item.keys() & allow}


def project_items(
    items: Iterable[Dict[str, Any]], allow: Optional[Set[str]]
) -> List[Dict[str, Any]]:
    """Apply :func:`project_item` to each element; always returns a new list."""
    if allow is None:
        return list(items)
    return [project_item(i, allow) for i in items]
