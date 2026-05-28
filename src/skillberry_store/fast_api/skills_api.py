"""Skills API endpoints for the Skillberry Store service."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Annotated, List
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import Response
from prometheus_client import Counter

from skillberry_store.tools.anthropic.importer import import_from_anthropic_skill
from skillberry_store.modules.object_handler import get_object_handler
from skillberry_store.modules.file_executor import detect_tool_dependencies
from skillberry_store.modules.description import Description
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.skill_schema import SkillSchema
from skillberry_store.schemas.manifest_schema import ManifestState
from skillberry_store.tools.anthropic.exporter import export_skill_to_anthropic_format
from skillberry_store.tools.configure import (
    get_files_directory_path,
    get_skills_directory,
    get_tools_directory,
    get_snippets_directory,
    is_auto_detect_dependencies_enabled,
)
from skillberry_store.fast_api.search_filters import apply_search_filters
from skillberry_store.utils.utils import normalize_uuid, generate_or_validate_uuid

logger = logging.getLogger(__name__)

# observability - metrics
prom_prefix = "sts_fastapi_skills_"
create_skill_counter = Counter(
    f"{prom_prefix}create_skill_counter", "Count number of skill create operations"
)
list_skills_counter = Counter(
    f"{prom_prefix}list_skills_counter", "Count number of skill list operations"
)
get_skill_counter = Counter(
    f"{prom_prefix}get_skill_counter", "Count number of skill get operations"
)
delete_skill_counter = Counter(
    f"{prom_prefix}delete_skill_counter", "Count number of skill delete operations"
)
update_skill_counter = Counter(
    f"{prom_prefix}update_skill_counter", "Count number of skill update operations"
)
search_skills_counter = Counter(
    f"{prom_prefix}search_skills_counter", "Count number of skill search operations"
)


def register_skills_api(
    app: FastAPI,
    tags: str = "skills",
    skills_descriptions: Optional[Description] = None,
):
    """Register skills API endpoints with the FastAPI application.

    Args:
        app: The FastAPI application instance.
        tags: FastAPI tags for grouping the endpoints in documentation.
        skills_descriptions: Description instance for managing skill descriptions.
    """
    skill_handler = get_object_handler("skill")
    tools_handler = get_object_handler("tool")
    snippets_handler = get_object_handler("snippet")

    def populate_skill_objects(skill_dict):
        """Populate full tool and snippet objects from UUIDs."""
        # Populate tools - resolve and get resources (will raise 404 if any missing)
        if "tool_uuids" in skill_dict and skill_dict["tool_uuids"]:
            try:
                # This will raise HTTPException if any UUID is invalid or not found
                tools = tools_handler.read_dicts(skill_dict["tool_uuids"])
                skill_dict["tools"] = tools
            except HTTPException as e:
                logger.error(
                    f"Skill '{skill_dict['name']}' references missing or invalid tools"
                )
                raise HTTPException(
                    status_code=505,
                    detail=f"Skill '{skill_dict['name']}' references missing or invalid tools: {e.detail}",
                )
        else:
            skill_dict["tools"] = []

        # Populate snippets - resolve and get resources (will raise 404 if any missing)
        if "snippet_uuids" in skill_dict and skill_dict["snippet_uuids"]:
            try:
                # This will raise HTTPException if any UUID is invalid or not found
                snippets = snippets_handler.read_dicts(skill_dict["snippet_uuids"])
                skill_dict["snippets"] = snippets
            except HTTPException as e:
                logger.error(
                    f"Skill '{skill_dict['name']}' references missing or invalid snippets"
                )
                raise HTTPException(
                    status_code=505,
                    detail=f"Skill '{skill_dict['name']}' references missing or invalid snippets: {e.detail}",
                )
        else:
            skill_dict["snippets"] = []

        return skill_dict

    @app.post("/skills/", tags=[tags])
    def create_skill(skill: Annotated[SkillSchema, Query()]):
        """Create a new skill.

        The form fields are dynamically generated from SkillSchema.
        Any changes to SkillSchema will automatically reflect in this API.

        Args:
            skill: The skill schema with tool_uuids and snippet_uuids (auto-generated from SkillSchema).
                   If uuid is not provided, it will be automatically generated.

        Returns:
            dict: Success message with the skill name and uuid.

        Raises:
            HTTPException: If skill already exists (409) or creation fails (500).
        """
        logger.info(f"Request to create skill: {skill.name}")
        create_skill_counter.inc()

        # Generate or validate UUID
        skill.uuid = generate_or_validate_uuid(skill.uuid)
        logger.info(f"UUID for skill '{skill.name}': {skill.uuid}")

        # Set timestamps
        current_time = datetime.now(timezone.utc).isoformat()
        skill.created_at = current_time
        skill.modified_at = current_time

        # Check if skill with this UUID already exists
        if skill_handler.object_exists(skill.uuid):
            raise HTTPException(
                status_code=409,
                detail=f"Skill with UUID '{skill.uuid}' already exists.",
            )

        try:
            # Determine correct parent for this skill becoming HEAD
            if skill.name:
                skill.parent = skill_handler.get_cache_parent_for_head(
                    skill.uuid, skill.name
                )
                logger.info(
                    f"Setting parent for skill '{skill.name}' to {skill.parent}"
                )

            # Save skill dict to UUID subfolder
            skill_handler.write_dict(skill.uuid, skill.to_dict())

            # Update cache - this becomes new HEAD
            if skill.name:
                skill_handler.update_cache(skill.uuid, new_name=skill.name)

            # Write description for search capability (indexed by UUID)
            if skills_descriptions and skill.description:
                skills_descriptions.write_description(skill.uuid, skill.description)
                logger.info(f"Skill description saved for UUID: {skill.uuid}")

            logger.info(
                f"Skill '{skill.name}' (UUID: {skill.uuid}) created successfully"
            )
            return {
                "message": f"Skill '{skill.name}' created successfully.",
                "name": skill.name,
                "uuid": skill.uuid,
            }
        except Exception as e:
            logger.error(f"Error creating skill '{skill.name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating skill: {str(e)}"
            )

    @app.get("/skills/", tags=[tags])
    def list_skills():
        """List all skills with populated tool and snippet objects.

        Returns:
            list: A list of all skill objects with full tool and snippet details.

        Raises:
            HTTPException: If listing fails (500).
        """
        logger.info("Request to list skills")
        list_skills_counter.inc()

        try:
            # Get all skills using list_all_dicts
            skills = skill_handler.list_all_dicts()

            # Populate full tool and snippet objects for each skill
            for skill_dict in skills:
                populate_skill_objects(skill_dict)

            # Sort by modified_at in descending order (most recent first)
            skills.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

            logger.info(f"Listed {len(skills)} skills")
            return skills
        except Exception as e:
            logger.error(f"Error listing skills: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing skills: {str(e)}"
            )

    @app.get("/skills/{uuid_or_name}", tags=[tags])
    def get_skill(uuid_or_name: str):
        """Get a specific skill by UUID or name with populated tool and snippet objects.

        Args:
            uuid_or_name: The UUID or name of the skill.

        Returns:
            dict: The skill object with full tool and snippet details.

        Raises:
            HTTPException: If skill not found (404) or retrieval fails (500).
        """
        logger.info(f"Request to get skill: {uuid_or_name}")
        get_skill_counter.inc()

        try:
            # Resolve UUID or name to UUID and read manifest
            skill_uuid = skill_handler.resolve_to_uuid_or_error(uuid_or_name)
            skill_dict = skill_handler.read_dict(skill_uuid)
            # Populate full tool and snippet objects
            populate_skill_objects(skill_dict)
            logger.info(f"Retrieved skill: {uuid_or_name}")
            return skill_dict
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving skill '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving skill: {str(e)}"
            )

    @app.delete("/skills/{uuid_or_name}", tags=[tags])
    def delete_skill(uuid_or_name: str):
        """Delete a skill by UUID or name.

        Args:
            uuid_or_name: The UUID or name of the skill to delete.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If skill not found (404) or deletion fails (500).
        """
        logger.info(f"Request to delete skill: {uuid_or_name}")
        delete_skill_counter.inc()

        try:
            # Resolve UUID or name to UUID (raises 404 if not found)
            skill_uuid = skill_handler.resolve_to_uuid_or_error(uuid_or_name)

            # Read skill to get name and parent before deletion
            skill_name = None
            skill_parent = None
            try:
                skill_dict = skill_handler.read_dict(skill_uuid)
                skill_name = skill_dict.get("name")
                skill_parent = skill_dict.get("parent")
            except Exception as e:
                logger.warning(f"Could not read skill before deletion: {e}")

            # Update cache BEFORE deletion (fixes parent chain while object still exists)
            if skill_uuid and skill_name:
                skill_handler.update_cache(
                    skill_uuid,
                    new_name=None,
                    old_name=skill_name,
                    old_parent=skill_parent,
                )

            # Now delete the skill object folder
            result = skill_handler.delete_object(skill_uuid)

            # Delete the description for the skill (indexed by UUID)
            if skills_descriptions:
                try:
                    skills_descriptions.delete_description(skill_uuid)
                    logger.info(f"Skill description deleted for UUID: {skill_uuid}")
                except Exception as e:
                    logger.warning(
                        f"Could not delete skill description for UUID '{skill_uuid}': {e}"
                    )

            logger.info(
                f"Skill with UUID or name '{uuid_or_name}' deleted successfully"
            )
            return {
                "message": f"Skill with UUID or name '{uuid_or_name}' deleted successfully."
            }
        except HTTPException as e:
            # Re-raise HTTPException (like 404) without modification
            raise
        except Exception as e:
            logger.error(f"Error deleting skill '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting skill: {str(e)}"
            )

    @app.put("/skills/{uuid_or_name}", tags=[tags])
    def update_skill(uuid_or_name: str, skill: SkillSchema):
        """Update an existing skill by UUID or name.

        Args:
            uuid_or_name: The UUID or name of the skill to update.
            skill: The updated skill schema.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If skill not found (404) or update fails (500).
        """
        logger.info(f"Request to update skill: {uuid_or_name}")
        update_skill_counter.inc()

        try:
            # Resolve UUID or name to UUID (raises 404 if not found)
            skill_uuid = skill_handler.resolve_to_uuid_or_error(uuid_or_name)

            # Read existing dict to preserve uuid and created_at
            existing_dict = skill_handler.read_dict(skill_uuid)
            old_name = existing_dict.get("name")
            old_parent = existing_dict.get("parent")

            # Convert update data to dict
            update_data = skill.to_dict()

            # Determine new name
            new_name = skill.name if skill.name else old_name

            # Determine correct parent for this skill becoming HEAD
            if new_name:
                new_parent = skill_handler.get_cache_parent_for_head(
                    skill_uuid, new_name
                )
                update_data["parent"] = new_parent
                logger.info(f"Setting parent for skill '{new_name}' to {new_parent}")

            # Merge: preserve uuid and created_at from existing, update modified_at
            merged_dict = {**existing_dict, **update_data}
            merged_dict["uuid"] = existing_dict.get("uuid", skill_uuid)
            merged_dict["created_at"] = existing_dict.get("created_at")
            merged_dict["modified_at"] = datetime.now(timezone.utc).isoformat()

            # Write the merged dict using ObjectHandler
            skill_handler.write_dict(skill_uuid, merged_dict)

            # Update cache - this becomes HEAD for its (possibly new) name
            if new_name:
                skill_handler.update_cache(
                    skill_uuid,
                    new_name=new_name,
                    old_name=old_name,
                    old_parent=old_parent,
                )

            # Update description for search capability (indexed by UUID)
            if skills_descriptions and merged_dict.get("description"):
                skills_descriptions.write_description(
                    skill_uuid, merged_dict["description"]
                )
                logger.info(f"Skill description updated for UUID: {skill_uuid}")

            logger.info(
                f"Skill with UUID or name '{uuid_or_name}' (UUID: {skill_uuid}) updated successfully"
            )
            return {
                "message": f"Skill with UUID or name '{uuid_or_name}' updated successfully."
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating skill '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating skill: {str(e)}"
            )

    @app.get("/search/skills", tags=[tags])
    def search_skills(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ):
        """Return a list of skills that are similar to the given search term.

        Returns skills that are below the similarity threshold and match the filters.

        Args:
            search_term: Search term.
            max_number_of_results: Number of results to return.
            similarity_threshold: Threshold to be used.
            manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
            lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).

        Returns:
            list: A list of matched skill names and similarity scores.
        """
        logger.info(f"Request to search skill descriptions for term: {search_term}")
        search_skills_counter.inc()

        if not skills_descriptions:
            raise HTTPException(
                status_code=503,
                detail="Skill search is not available - descriptions not initialized",
            )

        try:
            matched_entities = skills_descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )

            filtered_matched_entities = [
                matched_entity
                for matched_entity in matched_entities
                if matched_entity["similarity_score"] <= similarity_threshold
            ]

            # Get full skill objects for filtering
            # Descriptions are indexed by UUID, so matched_entity["filename"] contains UUID
            skills_to_filter = []
            for matched_entity in filtered_matched_entities:
                skill_uuid = matched_entity.get("filename")
                if not skill_uuid:
                    logger.warning(
                        f"Matched entity missing 'filename' field: {matched_entity}"
                    )
                    continue
                try:
                    # Read skill manifest by UUID
                    skill_dict = skill_handler.read_dict(skill_uuid)
                    skill_dict["similarity_score"] = matched_entity.get(
                        "similarity_score", 0.0
                    )
                    skills_to_filter.append(skill_dict)
                except Exception as e:
                    logger.warning(
                        f"Could not load skill with UUID {skill_uuid} for filtering: {e}"
                    )

            # Apply manifest and lifecycle filters
            filtered_skills = apply_search_filters(
                skills_to_filter,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )

            # Sort by modified_at in descending order (most recent first)
            filtered_skills.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

            # Return only filename and similarity_score (filename is the skill name)
            result = [
                {
                    "filename": skill.get("name", ""),
                    "similarity_score": skill.get("similarity_score", 0.0),
                }
                for skill in filtered_skills
                if skill.get("name")  # Only include if name exists
            ]

            logger.info(f"Found {len(result)} matching skills after filtering")
            return result
        except Exception as e:
            logger.error(f"Error searching skills: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error searching skills: {str(e)}"
            )

    @app.post("/skills/detect-anthropic-skills", tags=[tags])
    async def detect_anthropic_skills(
        source_type: str = Form(...),
        github_url: Optional[str] = Form(None),
        folder_path: Optional[str] = Form(None),
    ):
        """Detect child skill directories in a parent directory.

        This endpoint scans a parent directory (from GitHub URL or local folder)
        and returns a list of subdirectories that contain SKILL.md files.

        Args:
            source_type: 'url' or 'folder'
            github_url: GitHub repository URL (required if source_type='url')
            folder_path: Local folder path (required if source_type='folder')

        Returns:
            dict: List of skill paths relative to the parent directory

        Raises:
            HTTPException: If detection fails
        """
        logger.info(f"Request to detect Anthropic skills from {source_type}")

        try:
            import os
            import requests
            import re

            skill_paths = []

            if source_type == "url":
                if not github_url:
                    raise HTTPException(
                        status_code=400,
                        detail="github_url is required for source_type='url'",
                    )

                # Convert GitHub URL to API URL
                api_url = github_url.replace("github.com", "api.github.com/repos")
                api_url = re.sub(r"/tree/(main|master)/", r"/contents/", api_url)

                logger.info(f"Fetching directory listing from: {api_url}")

                # Fetch directory contents
                response = requests.get(api_url, timeout=30)
                if not response.ok:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"GitHub API error: {response.text or response.reason}",
                    )

                items = response.json()

                # Check each subdirectory for SKILL.md
                for item in items:
                    if item["type"] == "dir":
                        dir_name = item["name"]
                        # Check if this directory contains SKILL.md
                        dir_api_url = item["url"]
                        try:
                            dir_response = requests.get(dir_api_url, timeout=30)
                            if dir_response.ok:
                                dir_items = dir_response.json()
                                has_skill_md = any(
                                    f["name"].upper() == "SKILL.MD"
                                    and f["type"] == "file"
                                    for f in dir_items
                                )
                                if has_skill_md:
                                    skill_paths.append(dir_name)
                                    logger.info(f"Found skill directory: {dir_name}")
                        except Exception as e:
                            logger.warning(f"Failed to check directory {dir_name}: {e}")

            elif source_type == "folder":
                if not folder_path:
                    raise HTTPException(
                        status_code=400,
                        detail="folder_path is required for source_type='folder'",
                    )

                if not os.path.exists(folder_path):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Folder does not exist: {folder_path}",
                    )

                if not os.path.isdir(folder_path):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Path is not a directory: {folder_path}",
                    )

                # List subdirectories
                try:
                    for entry in os.listdir(folder_path):
                        entry_path = os.path.join(folder_path, entry)
                        if os.path.isdir(entry_path):
                            # Check if this directory contains SKILL.md
                            skill_md_path = os.path.join(entry_path, "SKILL.md")
                            if os.path.isfile(skill_md_path):
                                skill_paths.append(entry)
                                logger.info(f"Found skill directory: {entry}")
                except Exception as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error reading directory: {str(e)}",
                    )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid source_type: {source_type}. Must be 'url' or 'folder'",
                )

            logger.info(f"Detected {len(skill_paths)} skill directories")
            return {
                "success": True,
                "skill_paths": skill_paths,
                "total": len(skill_paths),
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error detecting Anthropic skills: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error detecting skills: {str(e)}",
            )

    @app.post("/skills/import-anthropic", tags=[tags])
    async def import_anthropic_skill(
        source_type: str = Form(...),
        github_url: Optional[str] = Form(None),
        zip_file: Optional[UploadFile] = File(None),
        folder_path: Optional[str] = Form(None),
        snippet_mode: str = Form("file"),
        treat_all_as_documents: bool = Form(False),
        tags: List[str] = Form([]),
    ):
        """Import an Anthropic skill from GitHub URL, ZIP file, or local folder.

        Args:
            source_type: 'url', 'zip', or 'folder'
            github_url: GitHub repository URL (required if source_type='url')
            zip_file: ZIP file upload (required if source_type='zip')
            folder_path: Local folder path (required if source_type='folder')
            snippet_mode: 'file' or 'paragraph' - how to import text files
            tags: List of additional tags to add to all imported objects (skills, tools, snippets)

        Returns:
            dict: Import result with created tools, snippets, and skill info

        Raises:
            HTTPException: If import fails
        """
        logger.info(f"Request to import Anthropic skill from {source_type}")

        try:
            # Prepare source data based on type
            source_data = None
            if source_type == "url":
                if not github_url:
                    raise HTTPException(
                        status_code=400,
                        detail="github_url is required for source_type='url'",
                    )
                source_data = github_url
            elif source_type == "zip":
                if not zip_file:
                    raise HTTPException(
                        status_code=400,
                        detail="zip_file is required for source_type='zip'",
                    )
                source_data = await zip_file.read()
            elif source_type == "folder":
                if not folder_path:
                    raise HTTPException(
                        status_code=400,
                        detail="folder_path is required for source_type='folder'",
                    )
                source_data = folder_path
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid source_type: {source_type}. Must be 'url', 'zip', or 'folder'",
                )

            # Import the skill
            skill_name, skill_description, tools, snippets, ignored_files = (
                import_from_anthropic_skill(
                    source_type=source_type,
                    source_data=source_data,
                    snippet_mode=snippet_mode,
                    treat_all_as_documents=treat_all_as_documents,
                )
            )

            # Create tools
            created_tool_uuids = []
            # First pass: collect all tool names for dependency detection
            all_tool_names = {}

            # Set tool UUIDs prior to creation to avoid failed lookups on tool name
            for tool in tools:
                tool.uuid = generate_or_validate_uuid(None)
                created_tool_uuids.append(tool.uuid)
                all_tool_names[tool.name] = tool.uuid

            # Get list of available tools (existing + being imported)
            existing_tools = tools_handler.get_existing_names()
            available_tools = existing_tools | all_tool_names.keys()

            # Import timestamp
            current_time = datetime.now(timezone.utc).isoformat()

            for tool in tools:
                try:
                    tool_dict = tool.to_dict()
                    tool_uuid = tool.uuid
                    tool_name = tool_dict["name"]

                    # Prepare tool data
                    ext = (
                        ".py" if tool_dict["programmingLanguage"] == "python" else ".sh"
                    )
                    module_filename = f"{tool_name}{ext}"

                    # Add additional tags to tool tags
                    tool_tags = tool_dict["tags"].copy() if tool_dict["tags"] else []
                    for tag in tags:
                        if tag and tag not in tool_tags:
                            tool_tags.append(tag)

                    # Determine correct parent for this tool becoming HEAD
                    tool_parent = tools_handler.get_cache_parent_for_head(
                        tool_uuid, tool_name
                    )
                    logger.info(
                        f"Setting parent for tool '{tool_name}' to {tool_parent}"
                    )

                    tool_data = {
                        "uuid": tool_uuid,
                        "name": tool_name,
                        "version": tool_dict["version"],
                        "description": tool_dict["description"],
                        "tags": tool_tags,
                        "programming_language": tool_dict["programmingLanguage"],
                        "module_name": module_filename,
                        "packaging_format": "code",
                        "state": "approved",
                        "created_at": current_time,
                        "modified_at": current_time,
                        "parent": tool_parent,
                    }

                    if "params" in tool_dict and tool_dict["params"]:
                        tool_data["params"] = tool_dict["params"]
                    if "returns" in tool_dict and tool_dict["returns"]:
                        tool_data["returns"] = tool_dict["returns"]

                    # Auto-detect dependencies for Python tools if enabled
                    if (
                        tool_dict["programmingLanguage"] == "python"
                        and is_auto_detect_dependencies_enabled()
                    ):
                        try:
                            # Detect dependencies from code
                            detected_dep_names = detect_tool_dependencies(
                                tool_dict["moduleContent"], tool_name, available_tools
                            )
                            if detected_dep_names:
                                detected_deps = [
                                    (
                                        all_tool_names.get(m)
                                        if m in all_tool_names
                                        else tools_handler.name_to_uuid(m)
                                    )
                                    for m in detected_dep_names
                                ]
                                tool_data["dependencies"] = detected_deps
                                logger.info(
                                    f"Auto-detected dependencies for '{tool_name}': {detected_deps}"
                                )
                        except Exception as e:
                            logger.warning(
                                f"Failed to auto-detect dependencies for {tool_name}: {e}"
                            )

                    # Save tool dict to UUID subfolder
                    tools_handler.write_dict(tool_uuid, tool_data)

                    # Update cache after create
                    tools_handler.update_cache(tool_uuid, new_name=tool_name)

                    # Save tool module to UUID subfolder
                    tools_handler.write_file(
                        tool_uuid, module_filename, tool_dict["moduleContent"]
                    )

                    logger.info(f"Created tool: {tool_name}")
                except Exception as e:
                    logger.error(f"Failed to create tool {tool.name}: {e}")

            # Create snippets
            created_snippet_uuids = []
            for snippet in snippets:
                try:
                    snippet_dict = snippet.to_dict()
                    snippet_uuid = generate_or_validate_uuid(None)
                    snippet_name = snippet_dict["name"]

                    # Add additional tags to snippet tags
                    snippet_tags = (
                        snippet_dict["tags"].copy() if snippet_dict["tags"] else []
                    )
                    for tag in tags:
                        if tag and tag not in snippet_tags:
                            snippet_tags.append(tag)

                    # Determine correct parent for this snippet becoming HEAD
                    snippet_parent = snippets_handler.get_cache_parent_for_head(
                        snippet_uuid, snippet_name
                    )
                    logger.info(
                        f"Setting parent for snippet '{snippet_name}' to {snippet_parent}"
                    )

                    # Prepare snippet data
                    snippet_data = {
                        "uuid": snippet_uuid,
                        "name": snippet_name,
                        "version": snippet_dict["version"],
                        "description": snippet_dict["description"],
                        "content": snippet_dict["content"],
                        "tags": snippet_tags,
                        "content_type": "text/plain",
                        "state": "approved",
                        "created_at": current_time,
                        "modified_at": current_time,
                        "parent": snippet_parent,
                    }

                    # Save snippet dict to UUID subfolder
                    snippets_handler.write_dict(snippet_uuid, snippet_data)

                    # Update cache after create
                    snippets_handler.update_cache(snippet_uuid, new_name=snippet_name)

                    created_snippet_uuids.append(snippet_uuid)
                    logger.info(f"Created snippet: {snippet_name}")
                except Exception as e:
                    logger.error(f"Failed to create snippet {snippet.name}: {e}")

            skill_tags = ["anthropic", "imported"]
            for tag in tags:
                if tag and tag not in skill_tags:
                    skill_tags.append(tag)

            # Prepare skill schema with UUID (either existing or None for new)
            skill_schema = SkillSchema(
                uuid=None,
                name=skill_name,
                version="1.0.0",
                description=skill_description,
                tags=skill_tags,
                tool_uuids=created_tool_uuids,
                snippet_uuids=created_snippet_uuids,
                state=ManifestState.APPROVED,
                parent=None,  # Will be set by create_skill if name exists
            )

            # Create new skill
            logger.info(f"Creating new skill '{skill_name}'...")
            result = create_skill(skill_schema)
            skill_uuid = result.get("uuid")
            action = "created"

            logger.info(
                f"Successfully imported Anthropic skill: {skill_name} ({action})"
            )

            return {
                "success": True,
                "message": f"Successfully imported Anthropic skill '{skill_name}' ({action})",
                "skill_name": skill_name,
                "skill_uuid": skill_uuid,
                "action": action,
                "tools_created": len(created_tool_uuids),
                "snippets_created": len(created_snippet_uuids),
                "ignored_files": ignored_files,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error importing Anthropic skill: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error importing Anthropic skill: {str(e)}"
            )

    @app.get("/skills/{uuid_or_name}/export-anthropic", tags=[tags])
    async def export_anthropic_skill(uuid_or_name: str):
        """Export a skill to Anthropic format as a ZIP file.

        Args:
            uuid_or_name: The UUID or name of the skill to export

        Returns:
            ZIP file with the skill in Anthropic format

        Raises:
            HTTPException: If skill not found or export fails
        """
        logger.info(f"Request to export skill to Anthropic format: {uuid_or_name}")

        try:
            # Resolve UUID or name to UUID and read manifest
            skill_uuid = skill_handler.resolve_to_uuid_or_error(uuid_or_name)
            skill_dict = skill_handler.read_dict(skill_uuid)

            # Get tools using read_manifests
            tools = []
            tool_modules = {}
            if "tool_uuids" in skill_dict and skill_dict["tool_uuids"]:
                tools = tools_handler.read_dicts(skill_dict["tool_uuids"])
                # Get tool modules
                for tool_dict in tools:
                    tool_uuid = tool_dict.get("uuid")
                    tool_name = tool_dict["name"]
                    module_name = tool_dict.get("module_name")
                    if tool_uuid and module_name:
                        try:
                            module_content = tools_handler.read_file(
                                tool_uuid, module_name, raw_content=True
                            )
                            if isinstance(module_content, str):
                                tool_modules[tool_name] = module_content
                        except Exception as e:
                            logger.warning(
                                f"Could not read module for tool {tool_name}: {e}"
                            )

            # Get snippets using read_manifests
            snippets = []
            if "snippet_uuids" in skill_dict and skill_dict["snippet_uuids"]:
                snippets = snippets_handler.read_dicts(skill_dict["snippet_uuids"])

            # Export to Anthropic format
            zip_content = export_skill_to_anthropic_format(
                skill=skill_dict,
                tools=tools,
                snippets=snippets,
                tool_modules=tool_modules,
            )

            logger.info(
                f"Successfully exported skill '{uuid_or_name}' to Anthropic format"
            )

            # Return as downloadable ZIP file
            return Response(
                content=zip_content,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{uuid_or_name}.zip"'
                },
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error exporting skill '{uuid_or_name}' to Anthropic format: {e}"
            )
            raise HTTPException(
                status_code=500, detail=f"Error exporting skill: {str(e)}"
            )
