# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""Exporter for converting Skillberry skills to Anthropic skill format."""

import io
import json
import zipfile
from typing import Dict, List, Optional, Any

from .naming import validate_skill_slug


WELLKNOWN_PRIMARY_PREFIX = ".well-known/agent-skills"
WELLKNOWN_LEGACY_PREFIX = ".well-known/skills"


class InvalidSkillNameError(ValueError):
    """Raised when a skill's name is not a valid slug and strict mode is on.

    Carries a suggested slug so callers (API, UI) can offer a rename shortcut.
    """

    def __init__(self, name: str, reason: str, suggested: str):
        super().__init__(
            f"Skill name '{name}' is not a valid slug: {reason} "
            f"Suggested: '{suggested}'."
        )
        self.name = name
        self.reason = reason
        self.suggested = suggested


def _enforce_skill_name(skill: Dict[str, Any], allow_invalid_name: bool) -> None:
    """Validate ``skill['name']`` unless the caller opted out.

    Raises:
        InvalidSkillNameError: When the name is not slug-safe and
            ``allow_invalid_name`` is False.
    """
    if allow_invalid_name:
        return
    result = validate_skill_slug(skill.get("name"))
    if not result.ok:
        raise InvalidSkillNameError(
            name=skill.get("name") or "",
            reason=result.reason,
            suggested=result.suggested,
        )


def extract_file_path_from_tags(tags: Optional[List[str]]) -> Optional[str]:
    """Extract file path from tags.

    Looks for tags in format "file:path/to/file.ext"

    Args:
        tags: List of tags

    Returns:
        File path or None
    """
    if not tags:
        return None

    for tag in tags:
        if tag.startswith("file:"):
            return tag[5:]  # Remove "file:" prefix

    return None


def normalize_file_path(file_path: str, skill_name: str) -> str:
    """Normalize file path by removing skill name prefix if present.

    Args:
        file_path: The file path
        skill_name: The skill name

    Returns:
        Normalized file path
    """
    # Remove leading skill name directory if present
    skill_prefix = f"{skill_name}/"
    if file_path.startswith(skill_prefix):
        return file_path[len(skill_prefix) :]
    return file_path


def generate_skill_md(
    skill: Dict[str, Any], has_file_structure: bool, snippets: List[Dict[str, Any]]
) -> str:
    """Generate SKILL.md content with frontmatter.

    Args:
        skill: The skill dictionary
        has_file_structure: Whether there's a file structure
        snippets: List of snippet dictionaries

    Returns:
        SKILL.md content
    """
    content = "---\n"
    content += f"name: {skill['name']}\n"
    content += f"description: {skill.get('description', 'No description provided')}\n"

    # Check if there's a LICENSE.txt file in snippets
    license_snippet = None
    for snippet in snippets:
        file_path = extract_file_path_from_tags(snippet.get("tags"))
        if file_path and "license" in file_path.lower():
            license_snippet = snippet
            break

    if license_snippet:
        content += "license: Proprietary. LICENSE.txt has complete terms\n"

    content += "---\n\n"

    if not has_file_structure:
        content += f"# {skill['name']}\n\n"
        content += f"{skill.get('description', 'No description provided')}\n\n"

    return content


def get_tool_language(tool: Dict[str, Any]) -> str:
    """Determine programming language from tool.

    Args:
        tool: The tool dictionary

    Returns:
        Language: 'python', 'bash', or 'other'
    """
    lang = tool.get("programming_language", "").lower()
    if lang in ("python", "py"):
        return "python"
    if lang in ("bash", "sh", "shell"):
        return "bash"
    return "other"


def get_tool_extension(tool: Dict[str, Any]) -> str:
    """Get file extension for tool based on language.

    Args:
        tool: The tool dictionary

    Returns:
        File extension
    """
    lang = get_tool_language(tool)
    if lang == "python":
        return ".py"
    if lang == "bash":
        return ".sh"
    return ".txt"


def build_file_structure_from_snippets(
    snippets: List[Dict[str, Any]], skill_name: str
) -> Dict[str, str]:
    """Build file structure from snippets with file: tags.

    Args:
        snippets: List of snippet dictionaries
        skill_name: The skill name

    Returns:
        Dictionary mapping file paths to content
    """
    files: Dict[str, str] = {}

    for snippet in snippets:
        file_path = extract_file_path_from_tags(snippet.get("tags"))
        if file_path:
            # Normalize the file path to remove skill name prefix
            normalized_path = normalize_file_path(file_path, skill_name)

            # Group snippets by file path
            if normalized_path in files:
                files[normalized_path] += "\n\n" + snippet["content"]
            else:
                files[normalized_path] = snippet["content"]

    return files


def build_file_structure_from_tools(
    tools: List[Dict[str, Any]],
    skill_name: str,
    tool_modules: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Build file structure from tools with file: tags.

    Args:
        tools: List of tool dictionaries
        skill_name: The skill name
        tool_modules: Dictionary mapping tool names to module content

    Returns:
        Dictionary mapping file paths to content
    """
    files: Dict[str, str] = {}

    for tool in tools:
        file_path = extract_file_path_from_tags(tool.get("tags"))
        if file_path:
            # Normalize the file path to remove skill name prefix
            normalized_path = normalize_file_path(file_path, skill_name)

            # Only write each file once (first tool wins)
            # This prevents duplicates since module_content already contains the complete file
            if normalized_path not in files:
                # Get module content
                content = ""
                if tool_modules and tool["name"] in tool_modules:
                    content = tool_modules[tool["name"]]

                files[normalized_path] = content

    return files


def export_snippets_to_skill_md(snippets: List[Dict[str, Any]]) -> str:
    """Export snippets without file: tags to SKILL.md.

    Args:
        snippets: List of snippet dictionaries

    Returns:
        Content to append to SKILL.md
    """
    content = ""

    for snippet in snippets:
        file_path = extract_file_path_from_tags(snippet.get("tags"))
        if not file_path:
            # No file path, add to SKILL.md
            content += "\n\n" + snippet["content"]

    return content


def export_tools_to_scripts(
    tools: List[Dict[str, Any]],
    skill_name: str,
    tool_modules: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Export tools without file: tags to scripts folder.

    Args:
        tools: List of tool dictionaries
        skill_name: The skill name
        tool_modules: Dictionary mapping tool names to module content

    Returns:
        Dictionary mapping file paths to content
    """
    files: Dict[str, str] = {}

    for tool in tools:
        file_path = extract_file_path_from_tags(tool.get("tags"))
        if not file_path:
            # No file path, create in scripts folder
            ext = get_tool_extension(tool)
            file_name = f"scripts/{tool['name']}{ext}"

            # Get module content
            content = ""
            if tool_modules and tool["name"] in tool_modules:
                content = tool_modules[tool["name"]]

            files[file_name] = content

    return files


def merge_file_structures(*structures: Dict[str, str]) -> Dict[str, str]:
    """Merge file structures.

    Args:
        *structures: Variable number of file structure dictionaries

    Returns:
        Merged file structure
    """
    merged: Dict[str, str] = {}

    for structure in structures:
        for path, content in structure.items():
            if path in merged:
                merged[path] += "\n\n" + content
            else:
                merged[path] = content

    return merged


def _build_file_structure(
    skill: Dict[str, Any],
    tools: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
    tool_modules: Optional[Dict[str, str]] = None,
) -> Dict[str, bytes]:
    """Build the complete file structure for a skill export.

    Returns {relative_path_under_skill_name: file_content_bytes}.
    Shared by both export variants (ZIP and directory).
    """
    skill_name = skill["name"]

    snippet_files = build_file_structure_from_snippets(snippets, skill_name)
    tool_files = build_file_structure_from_tools(tools, skill_name, tool_modules)
    script_files = export_tools_to_scripts(tools, skill_name, tool_modules)

    all_files = merge_file_structures(snippet_files, tool_files, script_files)

    has_file_structure = len(all_files) > 0
    skill_md_content = generate_skill_md(skill, has_file_structure, snippets)

    additional_snippets = export_snippets_to_skill_md(snippets)
    if additional_snippets:
        skill_md_content += additional_snippets

    has_skill_md_in_files = any(
        path.upper() == "SKILL.MD" or path.upper().endswith("/SKILL.MD")
        for path in all_files.keys()
    )

    if not has_skill_md_in_files:
        all_files["SKILL.md"] = skill_md_content
    else:
        for path in list(all_files.keys()):
            if path.upper() == "SKILL.MD" or path.upper().endswith("/SKILL.MD"):
                all_files[path] = skill_md_content + all_files[path]
                break

    result: Dict[str, bytes] = {}
    for file_path, content in all_files.items():
        normalized = content if content.endswith("\n") else content + "\n"
        result[f"{skill_name}/{file_path}"] = normalized.encode("utf-8")

    return result


def _extract_frontmatter_description(skill_md: bytes) -> str:
    """Return the ``description`` field from a SKILL.md frontmatter block.

    Falls back to an empty string when the field is not present. Kept
    intentionally small — the writer of the frontmatter is our own
    :func:`generate_skill_md`, so we do not need a full YAML parser.
    """
    try:
        text = skill_md.decode("utf-8", errors="replace")
    except Exception:
        return ""
    if not text.startswith("---"):
        return ""
    # Slice between the first and second '---' fence.
    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    for line in parts[1].splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    return ""


def build_wellknown_index(
    slug: str, description: str, relative_files: List[str]
) -> bytes:
    """Build the ``index.json`` payload for the well-known agent-skills provider.

    Args:
        slug: The skill slug (matches the folder name under
            ``.well-known/agent-skills/``).
        description: Description to advertise, sourced from the same SKILL.md
            frontmatter that lands in the export.
        relative_files: Sorted list of file paths inside ``<slug>/``. Each
            entry must be fetchable at
            ``/.well-known/agent-skills/<slug>/<entry>``.

    Returns:
        UTF-8 JSON bytes ready to be written to
        ``.well-known/agent-skills/index.json``.
    """
    payload = {
        "version": 1,
        "skills": [
            {
                "name": slug,
                "description": description,
                "files": list(relative_files),
            }
        ],
    }
    # sort_keys is deliberate: manifest bytes are stable across restarts.
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _augment_with_wellknown_layout(files: Dict[str, bytes]) -> Dict[str, bytes]:
    """Return ``files`` extended with the well-known layout.

    Given the canonical export layout produced by
    :func:`_build_file_structure` — every path prefixed by ``<skill>/`` —
    this returns a superset dict that additionally contains:

    - The same files under ``.well-known/agent-skills/<skill>/``.
    - The same files under ``.well-known/skills/<skill>/`` (legacy alias).
    - ``.well-known/agent-skills/index.json`` listing every file.
    - ``.well-known/skills/index.json`` (byte-identical copy).

    The input dict is not mutated.
    """
    if not files:
        return dict(files)

    # Discover the skill folder (all keys share the same first segment by
    # construction).
    first_key = next(iter(files))
    slug = first_key.split("/", 1)[0]

    result: Dict[str, bytes] = dict(files)
    relative_files: List[str] = []
    skill_md_bytes = b""

    for path, content in files.items():
        rel = path[len(slug) + 1 :]
        relative_files.append(rel)
        result[f"{WELLKNOWN_PRIMARY_PREFIX}/{slug}/{rel}"] = content
        result[f"{WELLKNOWN_LEGACY_PREFIX}/{slug}/{rel}"] = content
        if rel == "SKILL.md":
            skill_md_bytes = content

    relative_files.sort()
    description = _extract_frontmatter_description(skill_md_bytes)
    index_bytes = build_wellknown_index(slug, description, relative_files)
    result[f"{WELLKNOWN_PRIMARY_PREFIX}/index.json"] = index_bytes
    result[f"{WELLKNOWN_LEGACY_PREFIX}/index.json"] = index_bytes

    return result


def export_skill_to_anthropic_format(
    skill: Dict[str, Any],
    tools: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
    tool_modules: Optional[Dict[str, str]] = None,
    allow_invalid_name: bool = False,
) -> bytes:
    """Export skill to Anthropic format as a ZIP file.

    Args:
        skill: The skill dictionary
        tools: List of tool dictionaries
        snippets: List of snippet dictionaries
        tool_modules: Dictionary mapping tool names to module content
        allow_invalid_name: When True, skip the slug validation performed by
            default. Anthropic conventions and downstream tooling expect the
            skill name to be a slug (see
            :mod:`skillberry_store.tools.anthropic.naming`); leave the default
            unless you deliberately want a permissive export.

    Returns:
        ZIP file content as bytes

    Raises:
        InvalidSkillNameError: If ``allow_invalid_name`` is False and the
            skill's ``name`` is not a valid slug.
    """
    _enforce_skill_name(skill, allow_invalid_name)
    files = _build_file_structure(skill, tools, snippets, tool_modules)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path, content in files.items():
            zip_file.writestr(file_path, content)

    zip_buffer.seek(0)
    return zip_buffer.read()


def export_skill_to_directory(
    skill: Dict[str, Any],
    tools: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
    output_dir: str,
    tool_modules: Optional[Dict[str, str]] = None,
    allow_invalid_name: bool = False,
    npx_compat: bool = False,
) -> None:
    """Export skill to a directory on disk.

    Writes the same file structure as export_skill_to_anthropic_format, but
    to real files instead of a ZIP archive. Used by vNFS backends.

    Args:
        skill: The skill dictionary
        tools: List of tool dictionaries
        snippets: List of snippet dictionaries
        output_dir: Destination directory path (created if absent)
        tool_modules: Dictionary mapping tool names to module content
        allow_invalid_name: See :func:`export_skill_to_anthropic_format`.
        npx_compat: When True, additionally materialize a well-known
            agent-skills layout at ``.well-known/agent-skills/`` (plus the
            legacy ``.well-known/skills/`` alias) so ``npx skills add
            http://host:port`` can discover and install the skill. The skill's
            name is validated as a slug regardless of ``allow_invalid_name``
            when this flag is set, because ``npx skills`` and the well-known
            provider require slug-safe folder names.

    Raises:
        InvalidSkillNameError: If ``allow_invalid_name`` is False and the
            skill's ``name`` is not a valid slug. Also raised, regardless of
            ``allow_invalid_name``, when ``npx_compat`` is True and the name
            is not a valid slug.
    """
    from pathlib import Path

    if npx_compat:
        _enforce_skill_name(skill, allow_invalid_name=False)
    else:
        _enforce_skill_name(skill, allow_invalid_name)
    files = _build_file_structure(skill, tools, snippets, tool_modules)
    if npx_compat:
        files = _augment_with_wellknown_layout(files)
    for rel_path, content in files.items():
        dest = Path(output_dir) / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
