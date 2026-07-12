"""Compute filter-picker facets (tags / namespaces / states) from a set of items.

The UI's tag and namespace pickers need to enumerate every unique value in
the store so users can filter without having every item loaded. This
module drives the ``GET /facets/{snippets,skills,tools}`` endpoints so the
UI can fetch the picker options in one small round trip and paginate the
main list separately.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

_NAMESPACE_PREFIX = "namespace:"


def compute_facets(items: Iterable[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Return sorted unique ``tags`` / ``namespaces`` / ``states`` over ``items``.

    A tag like ``namespace:prod`` is split into the ``namespaces`` list
    (with the prefix stripped). Bare tags go into ``tags``.
    """
    tags: set = set()
    namespaces: set = set()
    states: set = set()
    for item in items:
        for tag in item.get("tags") or []:
            if not isinstance(tag, str) or not tag:
                continue
            if tag.startswith(_NAMESPACE_PREFIX):
                stripped = tag[len(_NAMESPACE_PREFIX):]
                if stripped:
                    namespaces.add(stripped)
            else:
                tags.add(tag)
        state = item.get("state")
        if state:
            states.add(state)
    return {
        "tags": sorted(tags),
        "namespaces": sorted(namespaces),
        "states": sorted(states),
    }
