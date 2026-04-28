# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""Exporter for converting Skillberry skills to Anthropic skill format."""

import io
import zipfile
from typing import Dict, List, Optional, Any


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


def export_skill_to_anthropic_format(
    skill: Dict[str, Any],
    tools: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
    tool_modules: Optional[Dict[str, str]] = None,
) -> bytes:
    """Export skill to Anthropic format as a ZIP file.

    Args:
        skill: The skill dictionary
        tools: List of tool dictionaries
        snippets: List of snippet dictionaries
        tool_modules: Dictionary mapping tool names to module content

    Returns:
        ZIP file content as bytes
    """
    # Create in-memory ZIP file
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        skill_name = skill["name"]

        # Build file structures from tags
        snippet_files = build_file_structure_from_snippets(snippets, skill_name)
        tool_files = build_file_structure_from_tools(tools, skill_name, tool_modules)
        script_files = export_tools_to_scripts(tools, skill_name, tool_modules)

        # Merge all file structures
        all_files = merge_file_structures(snippet_files, tool_files, script_files)

        # Check if we have any file structure
        has_file_structure = len(all_files) > 0

        # Generate SKILL.md
        skill_md_content = generate_skill_md(skill, has_file_structure, snippets)

        # Add snippets without file: tags to SKILL.md
        additional_snippets = export_snippets_to_skill_md(snippets)
        if additional_snippets:
            skill_md_content += additional_snippets

        # Check if SKILL.md already exists in allFiles
        has_skill_md_in_files = any(
            path.upper() == "SKILL.MD" or path.upper().endswith("/SKILL.MD")
            for path in all_files.keys()
        )

        # Only add SKILL.md if it doesn't already exist in the file structure
        if not has_skill_md_in_files:
            zip_file.writestr(f"{skill_name}/SKILL.md", skill_md_content)
        else:
            # If SKILL.md exists, prepend frontmatter to it
            for path in list(all_files.keys()):
                if path.upper() == "SKILL.MD" or path.upper().endswith("/SKILL.MD"):
                    all_files[path] = skill_md_content + all_files[path]
                    break

        # Add all files to the zip with trailing newline
        for file_path, content in all_files.items():
            # Ensure content ends with a single newline (standard for text files)
            normalized_content = content if content.endswith("\n") else content + "\n"
            zip_file.writestr(f"{skill_name}/{file_path}", normalized_content)

    # Get the ZIP content
    zip_buffer.seek(0)
    return zip_buffer.read()
