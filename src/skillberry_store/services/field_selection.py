"""Field-selection helpers for the bulk list / search endpoints.

The list endpoints (``GET /snippets/``, ``GET /skills/``, ``GET /tools/``,
``GET /vmcp_servers/``, ``GET /vnfs_servers/``) and the matching search
endpoints accept an optional ``?fields=`` query param:

* Omitted / empty / ``"narrow"`` — return the minimal set required by
  the UI listing page for that type (default).
* ``"wide"`` — return every persisted manifest field for that type,
  but skip the flag fields (and therefore skip the bundling mechanisms
  those flags gate).
* ``"full"`` — return every field of the object, including the
  underscore-prefixed flag fields that trigger bundling mechanisms.
* A comma-separated allowlist (``"uuid,name,description"``) — return
  exactly those keys.

The HTTP layer applies the ``narrow`` default via the FastAPI ``Query``
default on each endpoint; at the service layer, an omitted ``fields``
argument (``None``) is still the "no filtering" sentinel (equivalent
to ``full``) so internal Python callers keep their previous behavior.

Presets are declared as *per-field tags* rather than per-preset field
sets: each field of each object type carries zero or more preset labels,
and the preset resolver returns "all fields carrying that label."

Boolean flag fields — names prefixed with ``"_"`` — do not represent
persisted data. Instead they activate a bundling mechanism inside the
owning service (skill population, vmcp/vnfs runtime enhancement).
Convention:

* A flag field carries ``"full"`` (always) and ``"narrow"`` when the
  listing page needs the mechanism's output.
* A flag field is **never** tagged ``"wide"`` — ``"wide"`` is manifest
  data only.
* The service consults the resolved allowlist: it triggers the
  mechanism iff the flag is in the allowlist (or the allowlist is
  ``None``, i.e. full/default). Sub-fields of the bundled payload that
  are not in the allowlist are skipped where cheap to do so.

The preset associations live server-side only. Clients (UI, CLI, MCP,
SDK) only ever send the preset *name* — they never need to know which
fields it expands to.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

# ─── field-tag tables ──────────────────────────────────────────────────
#
# ``FieldTags`` is the shape used per object type: a map from a field
# name to the set of preset names that field belongs to.

FieldTags = Dict[str, Set[str]]

# Common manifest fields — every persisted-schema field appears in
# ``wide`` and ``full``; ``narrow`` only names the ones the UI listing
# page actually renders/filters/sorts on.

SNIPPET_FIELD_TAGS: FieldTags = {
    # UI-facing (narrow) — rendered by the Snippets listing page.
    "uuid":         {"narrow", "wide", "full"},
    "name":         {"narrow", "wide", "full"},
    "description":  {"narrow", "wide", "full"},
    "state":        {"narrow", "wide", "full"},
    "tags":         {"narrow", "wide", "full"},
    "version":      {"narrow", "wide", "full"},
    "content_type": {"narrow", "wide", "full"},
    # Persisted but not UI-facing — wide/full only.
    "extra":        {"wide", "full"},
    "parent":       {"wide", "full"},
    "created_at":   {"wide", "full"},
    "modified_at":  {"wide", "full"},
    "content":      {"wide", "full"},
}

TOOL_FIELD_TAGS: FieldTags = {
    "uuid":                 {"narrow", "wide", "full"},
    "name":                 {"narrow", "wide", "full"},
    "description":          {"narrow", "wide", "full"},
    "state":                {"narrow", "wide", "full"},
    "tags":                 {"narrow", "wide", "full"},
    "version":              {"narrow", "wide", "full"},
    "module_name":          {"narrow", "wide", "full"},
    "extra":                {"wide", "full"},
    "parent":               {"wide", "full"},
    "created_at":           {"wide", "full"},
    "modified_at":          {"wide", "full"},
    "programming_language": {"wide", "full"},
    "packaging_format":     {"wide", "full"},
    "packaging_params":     {"wide", "full"},
    "params":               {"wide", "full"},
    "returns":              {"wide", "full"},
    "dependencies":         {"wide", "full"},
}

SKILL_FIELD_TAGS: FieldTags = {
    "uuid":          {"narrow", "wide", "full"},
    "name":          {"narrow", "wide", "full"},
    "description":   {"narrow", "wide", "full"},
    "state":         {"narrow", "wide", "full"},
    "tags":          {"narrow", "wide", "full"},
    "version":       {"narrow", "wide", "full"},
    "tool_uuids":    {"narrow", "wide", "full"},
    "snippet_uuids": {"narrow", "wide", "full"},
    "extra":         {"wide", "full"},
    "parent":        {"wide", "full"},
    "created_at":    {"wide", "full"},
    "modified_at":   {"wide", "full"},
    # Flag + bundled outputs (only in ``full``): the ``_populate`` flag
    # triggers ``SkillsService.populate_objects`` which inlines the full
    # tool/snippet objects into ``tools`` / ``snippets``.
    "_populate":     {"full"},
    "tools":         {"full"},
    "snippets":      {"full"},
}

# vMCP: the list UI shows a Status column (Running/Stopped) that reads
# ``running``. To produce ``running`` the service must run its
# enhancement mechanism, gated by ``_enhance``. Once enhancement is on,
# the whole bundled payload (``running`` + ``runtime``) comes with it —
# the list view ignores ``runtime`` but it costs nothing to include it
# in the narrow preset and keeps the mechanism simple.

VMCP_FIELD_TAGS: FieldTags = {
    "uuid":        {"narrow", "wide", "full"},
    "name":        {"narrow", "wide", "full"},
    "description": {"narrow", "wide", "full"},
    "state":       {"narrow", "wide", "full"},
    "tags":        {"narrow", "wide", "full"},
    "version":     {"narrow", "wide", "full"},
    "port":        {"narrow", "wide", "full"},
    "skill_uuid":  {"wide", "full"},
    "extra":       {"wide", "full"},
    "parent":      {"wide", "full"},
    "created_at":  {"wide", "full"},
    "modified_at": {"wide", "full"},
    "_enhance":    {"narrow", "full"},
    "running":     {"narrow", "full"},
    "runtime":     {"narrow", "full"},
}

VNFS_FIELD_TAGS: FieldTags = {
    "uuid":        {"narrow", "wide", "full"},
    "name":        {"narrow", "wide", "full"},
    "description": {"narrow", "wide", "full"},
    "state":       {"narrow", "wide", "full"},
    "tags":        {"narrow", "wide", "full"},
    "version":     {"narrow", "wide", "full"},
    "port":        {"narrow", "wide", "full"},
    "protocol":    {"narrow", "wide", "full"},
    "skill_uuid":  {"wide", "full"},
    "extra":       {"wide", "full"},
    "parent":      {"wide", "full"},
    "created_at":  {"wide", "full"},
    "modified_at": {"wide", "full"},
    "_enhance":    {"narrow", "full"},
    "running":     {"narrow", "full"},
    "export_path": {"narrow", "full"},
}

_FIELD_TAGS_BY_TYPE: Dict[str, FieldTags] = {
    "snippet": SNIPPET_FIELD_TAGS,
    "tool":    TOOL_FIELD_TAGS,
    "skill":   SKILL_FIELD_TAGS,
    "vmcp":    VMCP_FIELD_TAGS,
    "vnfs":    VNFS_FIELD_TAGS,
}

# Fixed set of preset names the resolver recognizes as such (as
# opposed to a comma-separated allowlist). Adding a new preset name
# means adding it here AND tagging fields with it.
_PRESET_NAMES: Set[str] = {"narrow", "wide", "full"}


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


# ─── public API ────────────────────────────────────────────────────────


def parse_fields_spec(
    fields_spec: Optional[str], object_type: str
) -> Optional[Set[str]]:
    """Resolve a ``fields`` query-param value to a concrete field allowlist.

    Args:
        fields_spec: Raw value from the query string. ``None`` / empty /
            ``"full"`` means "no field selection — return every field,
            including flag fields that trigger bundling mechanisms".
            ``"narrow"`` / ``"wide"`` selects the tagged fields for
            ``object_type``. Any other value is parsed as a
            comma-separated allowlist.
        object_type: Object-type key (``"snippet"``, ``"tool"``,
            ``"skill"``, ``"vmcp"``, ``"vnfs"``).

    Returns:
        The set of field names to keep, or ``None`` when no field
        selection should be applied (default / ``"full"``). Callers use
        the ``None`` sentinel to short-circuit both field filtering and
        the "should the flag mechanism run" check (``None`` implies all
        mechanisms run).

    Raises:
        ValueError: If ``object_type`` is unknown, or if ``fields_spec``
            names a registered preset but no field of ``object_type``
            carries that tag.
    """
    if not fields_spec or fields_spec == "full":
        # Validate the type is known even in the default path so that
        # a bogus ``object_type`` fails loudly.
        if object_type not in _FIELD_TAGS_BY_TYPE:
            raise ValueError(
                f"No field tags registered for object type '{object_type}'"
            )
        return None
    if fields_spec in _PRESET_NAMES:
        allow = _fields_with_preset(object_type, fields_spec)
        if not allow:
            raise ValueError(
                f"No '{fields_spec}' preset registered for object type '{object_type}'"
            )
        return allow
    allow = {f.strip() for f in fields_spec.split(",") if f.strip()}
    return allow or None


def should_run_mechanism(allow: Optional[Set[str]], flag: str) -> bool:
    """Return whether the mechanism gated by ``flag`` should run.

    Args:
        allow: The resolved allowlist from :func:`parse_fields_spec`.
            ``None`` means "no filtering / full preset" — every
            mechanism runs.
        flag: The underscore-prefixed flag field name (e.g. ``"_populate"``,
            ``"_enhance"``).

    Returns:
        True iff the mechanism should run: either ``allow`` is ``None``
        (default/full) or ``flag`` is explicitly in ``allow`` (narrow
        preset for vmcp/vnfs; explicit CSV request; etc.).
    """
    return allow is None or flag in allow


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
