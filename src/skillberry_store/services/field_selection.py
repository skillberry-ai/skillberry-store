"""Field-selection helpers for the list / search / get endpoints.

The list endpoints (``GET /snippets/``, ``GET /skills/``, ``GET /tools/``,
``GET /vmcp_servers/``, ``GET /vnfs_servers/``), the matching search
endpoints, and the per-object get endpoints
(``GET /snippets/{uuid_or_name}``, ``GET /skills/{uuid_or_name}``,
``GET /tools/{uuid_or_name}``, ``GET /vmcp_servers/{uuid_or_name}``,
``GET /vnfs_servers/{uuid_or_name}``) all accept an optional
``?fields=`` query param:

* ``"minimal"`` — return only the identifier field (``uuid``).
  Intended for search responses whose consumers already hold the
  listing view and cross-reference by ``uuid``.
* Omitted / empty / ``"narrow"`` — return the minimal set required by
  the UI listing page for that type (default).
* ``"wide"`` — return every persisted manifest field for that type,
  plus any enrichment already present at the ``narrow`` level.
* ``"full"`` — return every field of the object, including the
  underscore-prefixed flag fields that trigger bundling mechanisms.
* A comma-separated allowlist (``"uuid,name,description"``) — return
  exactly those keys.

The default (``"narrow"``) is applied at :func:`parse_fields_spec`: a
missing / empty ``fields_spec`` resolves to the narrow allowlist, so
every caller — HTTP, plugin, direct service invocation — that doesn't
name a preset gets narrow. Callers that need the complete object
(populated skills, tool packaging params, vMCP runtime bundle) must
opt in with ``fields="full"``.

Presets are declared as *per-field tags* rather than per-preset field
sets: each field of each object type carries zero or more preset labels,
and the preset resolver returns "all fields carrying that label."

**Preset ordering invariant.** The four named presets form a chain
``minimal ⊆ narrow ⊆ wide ⊆ full``: every field tagged with a smaller
preset is also tagged with every larger preset. Concretely, ``uuid``
carries every tag; a flag field tagged ``"narrow"`` must also carry
``"wide"`` and ``"full"``. The invariant is enforced by unit tests in
``test_field_selection.py``.

Boolean flag fields — names prefixed with ``"_"`` — do not represent
persisted data. Instead they activate a bundling mechanism inside the
owning service (skill population, vmcp/vnfs runtime enhancement).
The service consults the resolved allowlist and triggers the
mechanism iff the flag is in the allowlist. Because of the ordering
invariant, once a flag is tagged for narrow, wide and full inherit
it: the mechanism will run for those presets too. Sub-fields of the
bundled payload that are not in the allowlist are skipped where cheap
to do so.

The preset associations live server-side only. Clients (UI, CLI, MCP,
SDK) only ever send the preset *name* — they never need to know which
fields it expands to.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set

# ─── field-tag tables ──────────────────────────────────────────────────
#
# ``FieldTags`` is the shape used per object type: a map from a field
# name to the set of preset names that field belongs to.

FieldTags = Dict[str, Set[str]]

# Common manifest fields — every persisted-schema field appears in
# ``wide`` and ``full``; ``narrow`` only names the ones the UI listing
# page actually renders/filters/sorts on.

SNIPPET_FIELD_TAGS: FieldTags = {
    # Identifier — carries every preset tag (``minimal`` is the
    # uuid-only preset used by search-response cross-referencing).
    "uuid":         {"minimal", "narrow", "wide", "full"},
    # UI-facing (narrow) — rendered by the Snippets listing page.
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
    "uuid":                 {"minimal", "narrow", "wide", "full"},
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
    "uuid":          {"minimal", "narrow", "wide", "full"},
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
# By the preset-ordering invariant, ``_enhance`` (and the bundled
# outputs it produces) must also be tagged ``"wide"`` — so wide
# requests also carry runtime status.

VMCP_FIELD_TAGS: FieldTags = {
    "uuid":        {"minimal", "narrow", "wide", "full"},
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
    "_enhance":    {"narrow", "wide", "full"},
    "running":     {"narrow", "wide", "full"},
    "runtime":     {"narrow", "wide", "full"},
}

VNFS_FIELD_TAGS: FieldTags = {
    "uuid":        {"minimal", "narrow", "wide", "full"},
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
    "_enhance":    {"narrow", "wide", "full"},
    "running":     {"narrow", "wide", "full"},
    "export_path": {"narrow", "wide", "full"},
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
_PRESET_NAMES: Set[str] = {"minimal", "narrow", "wide", "full"}

# Preset ordering (smallest → largest). Any field tagged with a
# preset in this list must also be tagged with every preset that
# comes after it. Consumed by both the docstring / mental model and
# by the ordering-invariant tests in ``test_field_selection.py``.
_PRESET_ORDER: List[str] = ["minimal", "narrow", "wide", "full"]


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
    fields_spec: str | None, object_type: str
) -> Set[str]:
    """Resolve a ``fields`` query-param value to a concrete field allowlist.

    Args:
        fields_spec: Raw value from the query string. ``None`` / empty
            means "use the default preset" — currently ``"narrow"``, the
            minimal set required by the UI listing page for that type.
            ``"minimal"`` / ``"narrow"`` / ``"wide"`` / ``"full"``
            selects the tagged fields for ``object_type``. Any other
            value is parsed as a comma-separated allowlist.
        object_type: Object-type key (``"snippet"``, ``"tool"``,
            ``"skill"``, ``"vmcp"``, ``"vnfs"``).

    Returns:
        The set of field names to keep. Every preset  resolves through 
        the FieldTags table for ``object_type``, so what each preset 
        covers is controlled entirely by those declarations.

    Raises:
        ValueError: If ``object_type`` is unknown, or if ``fields_spec``
            names a registered preset but no field of ``object_type``
            carries that tag.
    """
    # Validate the type is known up front so that a bogus ``object_type``
    # fails loudly on every path.
    if object_type not in _FIELD_TAGS_BY_TYPE:
        raise ValueError(
            f"No field tags registered for object type '{object_type}'"
        )
    if not fields_spec:
        fields_spec = "narrow"
    if fields_spec in _PRESET_NAMES:
        allow = _fields_with_preset(object_type, fields_spec)
        if not allow:
            raise ValueError(
                f"No '{fields_spec}' preset registered for object type '{object_type}'"
            )
        return allow
    allow = {f.strip() for f in fields_spec.split(",") if f.strip()}
    if not allow:
        allow = _fields_with_preset(object_type, "narrow")
    return allow


def should_run_mechanism(allow: Set[str], flag: str) -> bool:
    """Return whether the mechanism gated by ``flag`` should run.

    Args:
        allow: The resolved allowlist from :func:`parse_fields_spec`.
        flag: The underscore-prefixed flag field name (e.g. ``"_populate"``,
            ``"_enhance"``).

    Returns:
        True iff ``flag`` is in ``allow`` — which happens when the
        selected preset tags the flag (``"full"`` tags every flag;
        ``"narrow"`` tags the flags whose bundled output the UI needs)
        or when an explicit CSV allowlist names it.
    """
    return flag in allow


def select_item_fields(
    item: Dict[str, Any], allow: Set[str]
) -> Dict[str, Any]:
    """Return a field-selected view of ``item``.

    A fresh dict is returned containing only those keys that both
    appear in ``item`` and in ``allow`` — safe to mutate.
    """
    return {k: item[k] for k in item.keys() & allow}


def select_items_fields(
    items: Iterable[Dict[str, Any]], allow: Set[str]
) -> List[Dict[str, Any]]:
    """Apply :func:`select_item_fields` to each element; always returns a new list."""
    return [select_item_fields(i, allow) for i in items]
