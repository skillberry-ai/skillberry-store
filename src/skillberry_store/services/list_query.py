"""Server-side filter / sort / paginate for the list endpoints.

The list endpoints previously handed the entire cache to the client and let
it filter and sort in memory. This helper pushes those steps down to the
server so the wire payload can be bounded to a single page.

All three axes are optional and additive. When none of ``search``, ``tags``,
``state``, ``sort``, ``limit``, and ``offset`` is provided the caller sees
exactly the previous behavior — a bare list sorted by ``modified_at`` desc.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_DEFAULT_SORT: Tuple[str, str] = ("modified_at", "desc")


def _matches_substring(item: Dict[str, Any], needle: str) -> bool:
    """Case-insensitive substring test over ``name`` and ``description``."""
    if not needle:
        return True
    lo = needle.lower()
    name = (item.get("name") or "")
    desc = (item.get("description") or "")
    return lo in name.lower() or lo in desc.lower()


def _matches_tags(item: Dict[str, Any], required: Sequence[str]) -> bool:
    """AND semantics: every required tag must be present on the item.

    Namespace tags (``namespace:xyz``) are ordinary tags — callers just
    include them in ``required`` to filter by namespace.
    """
    if not required:
        return True
    have = set(item.get("tags") or [])
    return all(t in have for t in required)


def _matches_state(item: Dict[str, Any], state: Optional[str]) -> bool:
    if state is None:
        return True
    return (item.get("state") or "") == state


def parse_sort(sort: Optional[str]) -> Tuple[str, str]:
    """Parse a ``field:direction`` spec (or bare ``field``) into a tuple.

    - ``None`` / empty → default ``("modified_at", "desc")``.
    - ``"name"`` → ``("name", "asc")``.
    - ``"modified_at:desc"`` → ``("modified_at", "desc")``.
    - Unknown direction falls back to ``"asc"``.
    """
    if not sort:
        return _DEFAULT_SORT
    if ":" in sort:
        field, direction = sort.split(":", 1)
        field = field.strip()
        direction = direction.strip().lower()
    else:
        field = sort.strip()
        direction = "asc"
    if direction not in ("asc", "desc"):
        direction = "asc"
    return field or _DEFAULT_SORT[0], direction


def apply_filters(
    items: Iterable[Dict[str, Any]],
    search: Optional[str] = None,
    tags: Optional[Sequence[str]] = None,
    state: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Filter ``items`` by substring / tags / state. Order preserved."""
    return [
        i
        for i in items
        if _matches_substring(i, search or "")
        and _matches_tags(i, tags or [])
        and _matches_state(i, state)
    ]


def apply_sort(
    items: List[Dict[str, Any]], sort: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Sort ``items`` per :func:`parse_sort`. Missing keys sort last."""
    field, direction = parse_sort(sort)
    reverse = direction == "desc"
    return sorted(items, key=lambda x: x.get(field) or "", reverse=reverse)


def apply_pagination(
    items: List[Dict[str, Any]],
    limit: Optional[int],
    offset: Optional[int],
) -> Tuple[List[Dict[str, Any]], int]:
    """Return the requested page along with the pre-slice ``total``.

    ``offset`` defaults to 0 when omitted. A ``None`` ``limit`` means "no
    slicing — return everything from ``offset``".
    """
    total = len(items)
    start = offset or 0
    if start < 0:
        start = 0
    if limit is None:
        return items[start:], total
    if limit < 0:
        limit = 0
    return items[start : start + limit], total


def is_paginated(limit: Optional[int], offset: Optional[int]) -> bool:
    """True when either ``limit`` or ``offset`` was set by the caller.

    Used to decide between the bare-array response (100% back-compat) and
    the ``{items, total, offset, limit}`` envelope.
    """
    return limit is not None or offset is not None
