"""Field-selection helpers for the bulk list / search endpoints.

The list endpoints (``GET /snippets/``, ``GET /skills/``, ``GET /tools/``,
``GET /vmcp_servers/``, ``GET /vnfs_servers/``) and the matching search
endpoints accept an optional ``?fields=`` query param:

* Omitted / empty / ``"full"``  — return the full object (default).
* A registered **preset name** (currently only ``"list"``) — return the
  fields tagged with that preset for the object's type.
* A comma-separated allowlist (``"uuid,name,description"``) — return
  exactly those fields.

Presets are declared as *per-field tags* rather than per-preset field
sets: each field of each object type carries zero or more preset labels,
and the preset resolver returns "all fields carrying that label." Adding
a new preset is a matter of labelling fields; no changes to the
resolver are required.

The preset associations live server-side only. Clients (UI, CLI, MCP,
SDK) only ever send the preset *name* — they never need to know which
fields it expands to.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

# ─── field-tag tables ──────────────────────────────────────────────────
#
# ``FieldTags`` is the shape used per object type: a map from a field
# name to the set of preset names that field belongs to. Fields not
# present in the map (or with an empty tag set) are only returned when
# the caller asks for the full object (``fields=None`` / ``"full"``).
#
# The five tables below migrate the legacy ``*_LIST_FIELDS`` sets: every
# field previously in that set is tagged ``{"list"}``, every other
# field carries no tag.

FieldTags = Dict[str, Set[str]]

SNIPPET_FIELD_TAGS: FieldTags = {
    "uuid":         {"list"},
    "name":         {"list"},
    "description":  {"list"},
    "state":        {"list"},
    "tags":         {"list"},
    "version":      {"list"},
    "extra":        {"list"},
    "parent":       {"list"},
    "created_at":   {"list"},
    "modified_at":  {"list"},
    "author":       {"list"},
    "content_type": {"list"},
    # "content" — heavy payload; omitted from the "list" preset.
}

TOOL_FIELD_TAGS: FieldTags = {
    "uuid":                 {"list"},
    "name":                 {"list"},
    "description":          {"list"},
    "state":                {"list"},
    "tags":                 {"list"},
    "version":              {"list"},
    "extra":                {"list"},
    "parent":               {"list"},
    "created_at":           {"list"},
    "modified_at":          {"list"},
    "author":               {"list"},
    "module_name":          {"list"},
    "programming_language": {"list"},
    "packaging_format":     {"list"},
    # "params" / "returns" / "dependencies" / "packaging_params" —
    # heavy; omitted from the "list" preset.
}

SKILL_FIELD_TAGS: FieldTags = {
    "uuid":          {"list"},
    "name":          {"list"},
    "description":   {"list"},
    "state":         {"list"},
    "tags":          {"list"},
    "version":       {"list"},
    "extra":         {"list"},
    "parent":        {"list"},
    "created_at":    {"list"},
    "modified_at":   {"list"},
    "author":        {"list"},
    "tool_uuids":    {"list"},
    "snippet_uuids": {"list"},
    # Populated "tools" / "snippets" arrays are inlined by
    # ``SkillsService.populate_objects`` at get-time; the list preset
    # deliberately omits them so callers use ``tool_uuids`` /
    # ``snippet_uuids``.
}

# vMCP / vNFS list presets include the runtime-status fields
# (``running``, ``runtime`` for vMCP; ``running``, ``export_path`` for
# vNFS) — the list UI depends on them.

VMCP_FIELD_TAGS: FieldTags = {
    "uuid":        {"list"},
    "name":        {"list"},
    "description": {"list"},
    "state":       {"list"},
    "tags":        {"list"},
    "version":     {"list"},
    "extra":       {"list"},
    "parent":      {"list"},
    "created_at":  {"list"},
    "modified_at": {"list"},
    "author":      {"list"},
    "port":        {"list"},
    "skill_uuid":  {"list"},
    "running":     {"list"},
    "runtime":     {"list"},
}

VNFS_FIELD_TAGS: FieldTags = {
    "uuid":        {"list"},
    "name":        {"list"},
    "description": {"list"},
    "state":       {"list"},
    "tags":        {"list"},
    "version":     {"list"},
    "extra":       {"list"},
    "parent":      {"list"},
    "created_at":  {"list"},
    "modified_at": {"list"},
    "author":      {"list"},
    "port":        {"list"},
    "skill_uuid":  {"list"},
    "protocol":    {"list"},
    "running":     {"list"},
    "export_path": {"list"},
}

_FIELD_TAGS_BY_TYPE: Dict[str, FieldTags] = {
    "snippet": SNIPPET_FIELD_TAGS,
    "tool":    TOOL_FIELD_TAGS,
    "skill":   SKILL_FIELD_TAGS,
    "vmcp":    VMCP_FIELD_TAGS,
    "vnfs":    VNFS_FIELD_TAGS,
}


# ─── preset resolution ─────────────────────────────────────────────────


def _fields_with_preset(object_type: str, preset: str) -> Set[str]:
    """Return the set of fields tagged with ``preset`` for ``object_type``.

    Raises:
        ValueError: If ``object_type`` has no registered field-tag table.
    """
    tags = _FIELD_TAGS_BY_TYPE.get(object_type)
    if tags is None:
        raise ValueError(
            f"No field tags registered for object type '{object_type}'"
        )
    return {name for name, presets in tags.items() if preset in presets}


def _all_known_presets() -> Set[str]:
    """Union of every preset name declared anywhere in the tag registry."""
    seen: Set[str] = set()
    for tags in _FIELD_TAGS_BY_TYPE.values():
        for names in tags.values():
            seen |= names
    return seen


# ─── back-compat computed constants ────────────────────────────────────
#
# These retain the pre-refactor names/values so any importer (currently
# only the server-side tests) keeps working. They are *derived* from the
# tag tables — the single source of truth for the "list" preset is now
# the ``{"list"}`` label on each field above.

SNIPPET_LIST_FIELDS: Set[str] = _fields_with_preset("snippet", "list")
TOOL_LIST_FIELDS:    Set[str] = _fields_with_preset("tool",    "list")
SKILL_LIST_FIELDS:   Set[str] = _fields_with_preset("skill",   "list")
VMCP_LIST_FIELDS:    Set[str] = _fields_with_preset("vmcp",    "list")
VNFS_LIST_FIELDS:    Set[str] = _fields_with_preset("vnfs",    "list")


# ─── public API ────────────────────────────────────────────────────────


def parse_fields_spec(
    fields_spec: Optional[str], object_type: str
) -> Optional[Set[str]]:
    """Resolve a ``fields`` query-param value to a concrete field allowlist.

    Args:
        fields_spec: Raw value from the query string. ``None`` / empty /
            ``"full"`` means "no field selection — return every field".
            A registered preset name (matches any tag in the field-tag
            tables) selects the tagged fields for ``object_type``. Any
            other value is parsed as a comma-separated allowlist.
        object_type: Object-type key (``"snippet"``, ``"tool"``,
            ``"skill"``, ``"vmcp"``, ``"vnfs"``).

    Returns:
        The set of field names to keep, or ``None`` when no field
        selection should be applied.

    Raises:
        ValueError: If ``fields_spec`` matches a registered preset name
            but that preset is not declared for ``object_type`` (i.e.
            no field of ``object_type`` carries that tag).
    """
    if not fields_spec or fields_spec == "full":
        return None
    if fields_spec in _all_known_presets():
        allow = _fields_with_preset(object_type, fields_spec)
        if not allow:
            raise ValueError(
                f"No '{fields_spec}' preset registered for object type '{object_type}'"
            )
        return allow
    allow = {f.strip() for f in fields_spec.split(",") if f.strip()}
    return allow or None


def select_item_fields(
    item: Dict[str, Any], allow: Optional[Set[str]]
) -> Dict[str, Any]:
    """Return a field-selected view of ``item``.

    When ``allow`` is ``None`` the input dict is returned unchanged (the
    caller must not mutate it — cache values are shared references). When
    ``allow`` is a set, a fresh dict is returned containing only those keys
    that both appear in ``item`` and in ``allow`` — safe to mutate.
    """
    if allow is None:
        return item
    return {k: item[k] for k in item.keys() & allow}


def select_items_fields(
    items: Iterable[Dict[str, Any]], allow: Optional[Set[str]]
) -> List[Dict[str, Any]]:
    """Apply :func:`select_item_fields` to each element; always returns a new list."""
    if allow is None:
        return list(items)
    return [select_item_fields(i, allow) for i in items]
