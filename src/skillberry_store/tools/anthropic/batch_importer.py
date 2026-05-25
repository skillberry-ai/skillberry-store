# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""Batch importer for converting multiple Anthropic skills to Skillberry format."""

import os
import re
import logging
from typing import List, Dict, Any, Tuple

from .importer import (
    fetch_from_github,
    extract_from_zip,
    read_from_folder,
    import_anthropic_skill,
)

logger = logging.getLogger(__name__)


def detect_skill_directories(files: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Detect subdirectories containing SKILL.md files.

    Args:
        files: List of file dictionaries with 'name', 'path', and 'content' keys

    Returns:
        List of skill directory info with 'path', 'name', and 'files' keys
    """
    # Group files by their parent directory
    directories: Dict[str, List[Dict[str, str]]] = {}

    for file in files:
        # Get the directory path (everything before the last /)
        if "/" in file["path"]:
            dir_path = "/".join(file["path"].split("/")[:-1])
        else:
            dir_path = "."

        if dir_path not in directories:
            directories[dir_path] = []
        directories[dir_path].append(file)

    # Find directories containing SKILL.md
    skill_directories = []

    for dir_path, dir_files in directories.items():
        # Check if this directory has a SKILL.md file
        has_skill_md = any(
            f["name"].upper() == "SKILL.MD" for f in dir_files
        )

        if has_skill_md:
            # Extract directory name (last part of path)
            dir_name = dir_path.split("/")[-1] if "/" in dir_path else dir_path

            skill_directories.append(
                {
                    "path": dir_path,
                    "name": dir_name,
                    "files": dir_files,
                }
            )

    return skill_directories


def detect_local_skill_directories(parent_path: str) -> List[Dict[str, Any]]:
    """Detect subdirectories containing SKILL.md files in a local folder.

    Args:
        parent_path: Path to the parent directory

    Returns:
        List of skill directory info with 'path', 'name', and 'files' keys
    """
    if not os.path.exists(parent_path):
        raise Exception(f"Folder does not exist: {parent_path}")

    if not os.path.isdir(parent_path):
        raise Exception(f"Path is not a directory: {parent_path}")

    skill_directories = []

    # Walk through immediate subdirectories
    for entry in os.listdir(parent_path):
        entry_path = os.path.join(parent_path, entry)

        if os.path.isdir(entry_path):
            # Check if this directory contains SKILL.md
            skill_md_path = os.path.join(entry_path, "SKILL.md")
            skill_md_lower_path = os.path.join(entry_path, "skill.md")

            if os.path.exists(skill_md_path) or os.path.exists(skill_md_lower_path):
                # Read all files in this directory
                files = read_from_folder(entry_path)

                skill_directories.append(
                    {
                        "path": entry_path,
                        "name": entry,
                        "files": files,
                    }
                )

    return skill_directories


def batch_import_anthropic_skills(
    source_type: str,
    source_data: Any,
    snippet_mode: str = "file",
    treat_all_as_documents: bool = False,
) -> List[Dict[str, Any]]:
    """Import multiple Anthropic skills from a parent directory or repository.

    Args:
        source_type: 'url', 'zip', or 'folder'
        source_data: URL string, ZIP bytes, or folder path string
        snippet_mode: 'file' or 'paragraph'
        treat_all_as_documents: If True, treat all files (including code) as document snippets

    Returns:
        List of import results, each containing:
        - success: bool
        - skill_name: str
        - skill_description: str
        - tools_created: int
        - snippets_created: int
        - ignored_files: List[str]
        - error: str (if failed)

    Raises:
        Exception: If batch import fails
    """
    results = []

    # Step 1: Detect skill directories based on source type
    skill_directories = []

    if source_type == "url":
        if not isinstance(source_data, str):
            raise ValueError("source_data must be a URL string for 'url' source_type")

        # Fetch all files from GitHub
        logger.info(f"Fetching files from GitHub URL: {source_data}")
        all_files = fetch_from_github(source_data)

        # Detect skill directories
        skill_directories = detect_skill_directories(all_files)

    elif source_type == "zip":
        if not isinstance(source_data, bytes):
            raise ValueError("source_data must be bytes for 'zip' source_type")

        # Extract all files from ZIP
        logger.info("Extracting files from ZIP")
        all_files = extract_from_zip(source_data)

        # Detect skill directories
        skill_directories = detect_skill_directories(all_files)

    elif source_type == "folder":
        if not isinstance(source_data, str):
            raise ValueError(
                "source_data must be a folder path string for 'folder' source_type"
            )

        # Detect skill directories in local folder
        logger.info(f"Scanning local folder: {source_data}")
        skill_directories = detect_local_skill_directories(source_data)

    else:
        raise ValueError(f"Invalid source_type: {source_type}")

    if not skill_directories:
        raise Exception(
            "No skill directories found. Each skill must be in a subdirectory containing a SKILL.md file."
        )

    logger.info(f"Found {len(skill_directories)} skill directories to import")

    # Step 2: Import each skill directory
    for skill_dir in skill_directories:
        try:
            logger.info(f"Importing skill from directory: {skill_dir['name']}")

            # For each skill directory, we need to create a temporary structure
            # that import_anthropic_skill can process
            skill_files = skill_dir["files"]

            # Import the skill using the existing single-skill importer
            # We pass the files directly as if they came from a single source
            skill_name, skill_description, tools, snippets, ignored_files = (
                import_anthropic_skill(
                    source_type="files",  # Special internal type
                    source_data=skill_files,  # Pass files directly
                    snippet_mode=snippet_mode,
                    treat_all_as_documents=treat_all_as_documents,
                )
            )

            results.append(
                {
                    "success": True,
                    "skill_name": skill_name,
                    "skill_description": skill_description,
                    "tools": tools,
                    "snippets": snippets,
                    "tools_created": len(tools),
                    "snippets_created": len(snippets),
                    "ignored_files": ignored_files,
                }
            )

            logger.info(
                f"Successfully imported skill '{skill_name}' with {len(tools)} tools and {len(snippets)} snippets"
            )

        except Exception as e:
            error_msg = f"Failed to import skill from {skill_dir['name']}: {str(e)}"
            logger.error(error_msg)
            results.append(
                {
                    "success": False,
                    "skill_name": skill_dir["name"],
                    "error": str(e),
                }
            )

    return results
