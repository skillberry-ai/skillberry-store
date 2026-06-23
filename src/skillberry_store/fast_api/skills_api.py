"""Skills API endpoints for the Skillberry Store service."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional, Annotated, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Header
from fastapi.responses import Response
from prometheus_client import Counter
from skillberry_store.plugins.events import (
    emit_content_added,
    emit_content_updated,
    emit_content_deleted,
)

from skillberry_store.tools.anthropic.importer import (
    import_from_anthropic_skill,
    parse_github_origin,
)
from skillberry_store.tools.endpoint_auth import (
    resolve_auth_headers,
    ReauthRequired,
)
from skillberry_store.modules.object_handler import get_object_handler
from skillberry_store.modules.file_executor import detect_tool_dependencies
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
from skillberry_store.services.skills_service import SkillsService
from skillberry_store.services.tools_service import ToolsService
from skillberry_store.services.snippets_service import SnippetsService

if TYPE_CHECKING:
    from skillberry_store.modules.description import Description

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


def _auth_exception_to_http(exc: ReauthRequired) -> HTTPException:
    """Translate a forced-reauthentication exception into a 401 HTTPException.

    Returns a structured ``detail`` the client uses to drive interactive login:
    a ``login_url`` to obtain a token. The caller re-runs the request with that
    token in the ``X-Endpoint-Token`` header.
    """
    return HTTPException(
        status_code=401,
        detail={
            "error": "login_required",
            "login_url": exc.login_url,
            "message": (
                "Authentication required. Log in at login_url, then retry this "
                "request with header 'X-Endpoint-Token: <token>'."
            ),
        },
    )


def register_skills_api(
    app: FastAPI,
    tags: str = "skills",
    skills_descriptions: Optional[Description] = None,
    service: Optional[SkillsService] = None,
):
    """Register skills API endpoints with the FastAPI application.

    Args:
        app: The FastAPI application instance.
        tags: FastAPI tags for grouping the endpoints in documentation.
        skills_descriptions: Description instance for managing skill descriptions.
        service: Optional SkillsService instance; created from default handlers if not provided.
    """
    if service is None:
        service = SkillsService(
            handler=get_object_handler("skill"),
            tools_handler=get_object_handler("tool"),
            snippets_handler=get_object_handler("snippet"),
            descriptions=skills_descriptions,
        )
    # expose handlers for Anthropic import/export endpoints below
    skill_handler = service.handler
    tools_handler = service.tools_handler
    snippets_handler = service.snippets_handler
    # descriptions=None: description file cleanup is skipped for cascade-deleted items (best-effort)
    tools_service = ToolsService(handler=tools_handler)
    snippets_service = SnippetsService(handler=snippets_handler)

    def populate_skill_objects(skill_dict):
        """Populate full tool and snippet objects from UUIDs in a skill dictionary.

        Resolves tool_uuids and snippet_uuids to their full manifest objects and
        adds them as 'tools' and 'snippets' lists in the skill dictionary.

        Args:
            skill_dict: Skill dictionary containing tool_uuids and snippet_uuids.

        Returns:
            dict: The same skill_dict with 'tools' and 'snippets' lists populated.

        Raises:
            HTTPException: 505 if any referenced tool or snippet is missing or invalid.
        """
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

    @app.post("/skills/", tags=[tags], openapi_extra={"x-cli-name": "create-skill"})
    async def create_skill(skill: Annotated[SkillSchema, Query()]):
        """Create a new skill in the store.

        Creates a skill manifest that references tools and snippets by their UUIDs.
        Skills are high-level compositions that group related tools and snippets.

        Args:
            skill: Skill metadata conforming to SkillSchema (name, description, tool_uuids, snippet_uuids, etc.).

        Returns:
            dict: Success message with skill name and UUID.

        Raises:
            HTTPException: 409 if skill already exists, 500 for other errors.
        """
        logger.info(f"Request to create skill: {skill.name}")
        create_skill_counter.inc()
        try:
            result = service.create(skill.to_dict())
            emit_content_added("skill", result["uuid"])
            return {
                "message": f"Skill '{result['name']}' created successfully.",
                "name": result["name"],
                "uuid": result["uuid"],
            }
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating skill '{skill.name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating skill: {str(e)}"
            )

    @app.get("/skills/", tags=[tags], openapi_extra={"x-cli-name": "list-skills"})
    def list_skills():
        """List all skills in the store.

        Retrieves metadata for all skills currently stored in the system.

        Args:
            None.

        Returns:
            list: List of dictionaries, each containing skill metadata (name, uuid, description, tool_uuids, snippet_uuids, etc.).

        Raises:
            HTTPException: 500 if listing fails.
        """
        logger.info("Request to list skills")
        list_skills_counter.inc()
        try:
            return service.list_all()
        except Exception as e:
            logger.error(f"Error listing skills: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing skills: {str(e)}"
            )

    @app.get(
        "/skills/{uuid_or_name}", tags=[tags], openapi_extra={"x-cli-name": "get-skill"}
    )
    def get_skill(uuid_or_name: str):
        """Get metadata for a specific skill by UUID or name.

        Retrieves the complete manifest/metadata for a skill identified by either
        its UUID or its unique name.

        Args:
            uuid_or_name: The UUID or name of the skill to retrieve.

        Returns:
            dict: Skill metadata including name, uuid, description, tool_uuids, snippet_uuids, etc.

        Raises:
            HTTPException: 404 if skill not found, 505 if referenced resources are invalid, 500 for other errors.
        """
        logger.info(f"Request to get skill: {uuid_or_name}")
        get_skill_counter.inc()
        try:
            return service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=505, detail=str(e))
        except Exception as e:
            logger.error(f"Error retrieving skill '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving skill: {str(e)}"
            )

    @app.delete(
        "/skills/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "delete-skill"},
    )
    async def delete_skill(
        uuid_or_name: str,
        delete_tools: bool = Query(
            False, description="Delete tools not shared with other skills"
        ),
        delete_snippets: bool = Query(
            False, description="Delete snippets not shared with other skills"
        ),
    ):
        """Delete a skill from the store with optional cascade deletion.

        Removes a skill and optionally its associated tools and snippets if they
        are not referenced by other skills. This operation triggers a content
        deletion event for plugin processing.

        Args:
            uuid_or_name: The UUID or name of the skill to delete.
            delete_tools: If True, delete tools that are not shared with other skills (default: False).
            delete_snippets: If True, delete snippets that are not shared with other skills (default: False).

        Returns:
            dict: Success message with lists of deleted tools and snippets.

        Raises:
            HTTPException: 404 if skill not found, 500 for other errors.
        """
        logger.info(f"Request to delete skill: {uuid_or_name}")
        delete_skill_counter.inc()
        try:
            skill = service.get(uuid_or_name)
            skill_uuid = skill["uuid"]
            deleted_tools: list = []
            deleted_snippets: list = []

            if delete_tools or delete_snippets:
                all_skills = service.handler.list_all_dicts()
                shared_tool_uuids: set = set()
                shared_snippet_uuids: set = set()
                for s in all_skills:
                    if s.get("uuid") != skill_uuid:
                        shared_tool_uuids.update(s.get("tool_uuids") or [])
                        shared_snippet_uuids.update(s.get("snippet_uuids") or [])

                if delete_tools:
                    for tool_uuid in skill.get("tool_uuids") or []:
                        if tool_uuid not in shared_tool_uuids:
                            try:
                                tools_service.delete(tool_uuid)
                                deleted_tools.append(tool_uuid)
                            except Exception as e:
                                logger.warning(
                                    f"Could not cascade-delete tool {tool_uuid}: {e}"
                                )

                if delete_snippets:
                    for snippet_uuid in skill.get("snippet_uuids") or []:
                        if snippet_uuid not in shared_snippet_uuids:
                            try:
                                snippets_service.delete(snippet_uuid)
                                deleted_snippets.append(snippet_uuid)
                            except Exception as e:
                                logger.warning(
                                    f"Could not cascade-delete snippet {snippet_uuid}: {e}"
                                )

            service.delete(uuid_or_name)
            emit_content_deleted("skill", skill_uuid)
            return {
                "message": f"Skill with UUID or name '{uuid_or_name}' deleted successfully.",
                "deleted_tools": deleted_tools,
                "deleted_snippets": deleted_snippets,
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error deleting skill '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting skill: {str(e)}"
            )

    @app.put(
        "/skills/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "update-skill"},
    )
    async def update_skill(uuid_or_name: str, skill: SkillSchema):
        """Update an existing skill's metadata.

        Updates the manifest/metadata for an existing skill. This operation
        triggers a content update event for plugin processing.

        Args:
            uuid_or_name: The UUID or name of the skill to update.
            skill: Updated skill metadata conforming to SkillSchema.

        Returns:
            dict: Success message confirming update.

        Raises:
            HTTPException: 404 if skill not found, 500 for other errors.
        """
        logger.info(f"Request to update skill: {uuid_or_name}")
        update_skill_counter.inc()
        try:
            result = service.update(uuid_or_name, skill.to_dict())
            emit_content_updated("skill", result["uuid"])
            return {
                "message": f"Skill with UUID or name '{uuid_or_name}' updated successfully."
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating skill '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating skill: {str(e)}"
            )

    @app.get(
        "/search/skills", tags=[tags], openapi_extra={"x-cli-name": "search-skills"}
    )
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
                m
                for m in matched_entities
                if float(m["similarity_score"]) <= similarity_threshold
            ]
            skills_to_filter = []
            for matched_entity in filtered_matched_entities:
                skill_uuid = matched_entity.get("filename")
                if not skill_uuid:
                    continue
                try:
                    skill_dict = skill_handler.read_dict(skill_uuid)
                    skill_dict["similarity_score"] = matched_entity.get(
                        "similarity_score", 0.0
                    )
                    skills_to_filter.append(skill_dict)
                except Exception as e:
                    logger.warning(f"Could not load skill {skill_uuid}: {e}")
            filtered_skills = apply_search_filters(
                skills_to_filter,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )
            filtered_skills.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return [
                {
                    "filename": s.get("name", ""),
                    "similarity_score": s.get("similarity_score", 0.0),
                }
                for s in filtered_skills
                if s.get("name")
            ]
        except Exception as e:
            logger.error(f"Error searching skills: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error searching skills: {str(e)}"
            )

    @app.post(
        "/skills/detect-anthropic-skills",
        tags=[tags],
        openapi_extra={"x-cli-name": "detect-anthropic-skills"},
    )
    async def detect_anthropic_skills(
        source_type: str = Form(...),
        github_url: Optional[str] = Form(None),
        folder_path: Optional[str] = Form(None),
        anonymous: bool = Form(True),
        x_endpoint_token: Optional[str] = Header(None),
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

                # Resolve per-endpoint auth once for the requested URL. Raises
                # ReauthRequired -> turned into a 401 below.
                try:
                    auth_headers = resolve_auth_headers(
                        github_url,
                        override_token=x_endpoint_token,
                        anonymous=anonymous,
                    )
                except ReauthRequired as e:
                    raise _auth_exception_to_http(e)

                # Convert GitHub URL to API URL
                api_url = github_url.replace("github.com", "api.github.com/repos")
                api_url = re.sub(r"/tree/(main|master)/", r"/contents/", api_url)

                logger.info(f"Fetching directory listing from: {api_url}")

                # Fetch directory contents
                response = requests.get(api_url, headers=auth_headers, timeout=30)
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
                            dir_response = requests.get(
                                dir_api_url, headers=auth_headers, timeout=30
                            )
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

                # Build safe_root from non-tainted components only.
                # os.path.basename() is CodeQL's recognised py/path-injection
                # sanitiser: each path segment from user input is stripped of
                # directory separators before being joined with the fixed
                # home-dir anchor.  This prevents path traversal and keeps all
                # filesystem operations below free of user-controlled taint.
                home_dir = os.path.realpath(os.path.expanduser("~"))
                abs_input = os.path.realpath(folder_path)
                if not (
                    abs_input == home_dir or abs_input.startswith(home_dir + os.sep)
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "folder_path must be within the current user's"
                            " home directory"
                        ),
                    )
                if abs_input == home_dir:
                    safe_root = home_dir
                else:
                    rel = abs_input[len(home_dir) + len(os.sep) :]
                    clean_parts = [os.path.basename(p) for p in rel.split(os.sep) if p]
                    safe_root = os.path.join(home_dir, *clean_parts)

                if not os.path.exists(safe_root):
                    raise HTTPException(
                        status_code=400,
                        detail="Folder does not exist",
                    )

                if not os.path.isdir(safe_root):
                    raise HTTPException(
                        status_code=400,
                        detail="Path is not a directory",
                    )

                # List subdirectories
                try:
                    for entry in os.listdir(safe_root):  # lgtm[py/path-injection]
                        # Only accept plain directory names (no separators or
                        # traversal) and confine the join to the sanitized root.
                        if entry != os.path.basename(entry):
                            continue
                        entry_path = os.path.join(safe_root, entry)
                        if os.path.realpath(entry_path).startswith(
                            safe_root + os.sep
                        ) and os.path.isdir(entry_path):
                            # Check if this directory contains SKILL.md
                            skill_md_path = os.path.join(entry_path, "SKILL.md")
                            if os.path.isfile(skill_md_path):
                                skill_paths.append(entry)
                                logger.info(f"Found skill directory: {entry}")
                except HTTPException:
                    raise
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

    @app.post(
        "/skills/import-anthropic",
        tags=[tags],
        openapi_extra={"x-cli-name": "import-anthropic-skill"},
    )
    async def import_anthropic_skill(
        source_type: str = Form(...),
        github_url: Optional[str] = Form(None),
        zip_file: Optional[UploadFile] = File(None),
        folder_path: Optional[str] = Form(None),
        snippet_mode: str = Form("file"),
        treat_all_as_documents: bool = Form(False),
        tags: List[str] = Form([]),
        anonymous: bool = Form(True),
        x_endpoint_token: Optional[str] = Header(None),
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
            try:
                skill_name, skill_description, tools, snippets, ignored_files = (
                    import_from_anthropic_skill(
                        source_type=source_type,
                        source_data=source_data,
                        snippet_mode=snippet_mode,
                        treat_all_as_documents=treat_all_as_documents,
                        override_token=x_endpoint_token,
                        anonymous=anonymous,
                    )
                )
            except ReauthRequired as e:
                # Endpoint needs interactive auth: surface login details as 401.
                raise _auth_exception_to_http(e)

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

            # Record the skill's origin so it can be looked up / re-checked later
            # by the provenance plugin (drift detection needs this baseline).
            # Only URL imports have a remote origin; zip/folder imports do not.
            skill_extra: Dict[str, Any] = {}
            if source_type == "url" and github_url:
                origin = parse_github_origin(github_url)
                skill_extra["origin"] = {
                    "type": "github" if origin else "url",
                    "url": github_url,
                    **(origin or {}),
                }

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
                extra=skill_extra,
            )

            # Create new skill
            logger.info(f"Creating new skill '{skill_name}'...")
            result = await create_skill(skill_schema)
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

    @app.get(
        "/skills/{uuid_or_name}/export-anthropic",
        tags=[tags],
        openapi_extra={"x-cli-name": "export-anthropic-skill"},
    )
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
