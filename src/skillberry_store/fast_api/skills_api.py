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
from skillberry_store.modules.resource_handler import ResourceHandler
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
from skillberry_store.utils.utils import normalize_uuid

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
    skills_directory = get_skills_directory()
    skill_handler = ResourceHandler(skills_directory, "skill")
    tools_handler = ResourceHandler(get_tools_directory(), "tool")
    snippets_handler = ResourceHandler(get_snippets_directory(), "snippet")
    
    def populate_skill_objects(skill_dict):
        """Populate full tool and snippet objects from UUIDs."""
        # Populate tools using get_resources_by_ids
        if "tool_uuids" in skill_dict and skill_dict["tool_uuids"]:
            requested_count = len(skill_dict['tool_uuids'])
            tools = tools_handler.get_resources_by_ids(skill_dict['tool_uuids'])
            if len(tools) < requested_count:
                missing = set(skill_dict['tool_uuids']) - {t['uuid'] for t in tools}
                logger.error(f"Skill '{skill_dict['name']}' references missing tools: {missing}")
                raise HTTPException(
                    status_code=505,
                    detail=f"Skill '{skill_dict['name']}' references missing tools: {missing}"
                )
            skill_dict["tools"] = tools
        else:
            skill_dict["tools"] = []
            
        # Populate snippets using get_resources_by_ids
        if "snippet_uuids" in skill_dict and skill_dict["snippet_uuids"]:
            requested_count = len(skill_dict['snippet_uuids'])
            snippets = snippets_handler.get_resources_by_ids(skill_dict["snippet_uuids"])
            if len(snippets) < requested_count:
                missing = set(skill_dict['snippet_uuids']) - {s['uuid'] for s in snippets}
                logger.error(f"Skill '{skill_dict['name']}' references missing snippets: {missing}")
                raise HTTPException(
                    status_code=505,
                    detail=f"Skill '{skill_dict['name']}' references missing snippets: {missing}"
                )
            skill_dict["snippets"] = snippets
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

        # Generate UUID if not provided
        if not skill.uuid:
            skill.uuid = str(uuid.uuid4())
            logger.info(f"Generated UUID for skill '{skill.name}': {skill.uuid}")

        # Set timestamps
        current_time = datetime.now(timezone.utc).isoformat()
        skill.created_at = current_time
        skill.modified_at = current_time

        # Generate UUID if not provided
        if not skill.uuid:
            skill.uuid = str(uuid.uuid4())
            logger.info(f"Generated UUID for skill '{skill.name}': {skill.uuid}")
        
        # Check if skill with this UUID already exists
        skill_uuid_normalized = normalize_uuid(skill.uuid)
        if not skill_uuid_normalized:
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {skill.uuid}")
        if skill_handler.resource_exists(skill_uuid_normalized):
            raise HTTPException(
                status_code=409, detail=f"Skill with UUID '{skill.uuid}' already exists."
            )

        try:
            # Save skill manifest to UUID subfolder
            skill_handler.write_manifest(skill_uuid_normalized, skill.to_dict())

            # Write description for search capability (indexed by UUID)
            if skills_descriptions and skill.description:
                skills_descriptions.write_description(skill_uuid_normalized, skill.description)
                logger.info(f"Skill description saved for UUID: {skill.uuid}")

            logger.info(f"Skill '{skill.name}' (UUID: {skill.uuid}) created successfully")
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
            # Get all skills using list_all_resources
            skills = skill_handler.list_all_resources()
            
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

    @app.get("/skills/{id}", tags=[tags])
    def get_skill(id: str):
        """Get a specific skill by ID (name or UUID) with populated tool and snippet objects.

        Args:
            id: The ID of the skill (can be either name or UUID).

        Returns:
            dict: The skill object with full tool and snippet details.

        Raises:
            HTTPException: If skill not found (404) or retrieval fails (500).
        """
        logger.info(f"Request to get skill: {id}")
        get_skill_counter.inc()

        try:
            # Get skill by ID (name or UUID)
            skill_dict = skill_handler.get_resource_by_id(id)
            # Populate full tool and snippet objects
            populate_skill_objects(skill_dict)
            logger.info(f"Retrieved skill: {id}")
            return skill_dict
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving skill '{id}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving skill: {str(e)}"
            )

    @app.delete("/skills/{id}", tags=[tags])
    def delete_skill(id: str):
        """Delete a skill by ID (name or UUID).

        Args:
            id: The ID of the skill to delete (can be either name or UUID).

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If skill not found (404) or deletion fails (500).
        """
        logger.info(f"Request to delete skill: {id}")
        delete_skill_counter.inc()

        try:
            # Resolve ID to UUID first to delete description
            skill_uuid = skill_handler.resolve_id(id)
            if not skill_uuid:
                raise HTTPException(
                    status_code=404,
                    detail=f"Skill with ID '{id}' not found"
                )
            
            # Delete the skill resource folder
            result = skill_handler.delete_resource_by_id(id)

            # Delete the description for the skill (indexed by UUID)
            if skills_descriptions:
                try:
                    skills_descriptions.delete_description(skill_uuid)
                    logger.info(f"Skill description deleted for UUID: {skill_uuid}")
                except Exception as e:
                    logger.warning(
                        f"Could not delete skill description for UUID '{skill_uuid}': {e}"
                    )

            logger.info(f"Skill with ID '{id}' deleted successfully")
            return {"message": f"Skill with ID '{id}' deleted successfully."}
        except HTTPException as e:
            # Re-raise HTTPException (like 404) without modification
            raise
        except Exception as e:
            logger.error(f"Error deleting skill '{id}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting skill: {str(e)}"
            )

    @app.put("/skills/{id}", tags=[tags])
    def update_skill(id: str, skill: SkillSchema):
        """Update an existing skill by ID (name or UUID).

        Args:
            id: The ID of the skill to update (can be either name or UUID).
            skill: The updated skill schema.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If skill not found (404) or update fails (500).
        """
        logger.info(f"Request to update skill: {id}")
        update_skill_counter.inc()

        try:
            # Resolve ID to UUID
            skill_uuid = skill_handler.resolve_id(id)
            if not skill_uuid:
                raise HTTPException(
                    status_code=404, detail=f"Skill with ID '{id}' not found."
                )

            # Read existing manifest to preserve uuid and created_at
            existing_manifest = skill_handler.read_manifest(skill_uuid)
            
            # Convert update data to dict
            update_data = skill.to_dict()
            
            # Merge: preserve uuid and created_at from existing, update modified_at
            merged_manifest = {**existing_manifest, **update_data}
            merged_manifest["uuid"] = existing_manifest.get("uuid", skill_uuid)
            merged_manifest["created_at"] = existing_manifest.get("created_at")
            merged_manifest["modified_at"] = datetime.now(timezone.utc).isoformat()

            # Write the merged manifest using ResourceHandler
            skill_uuid_normalized = normalize_uuid(skill_uuid)
            if not skill_uuid_normalized:
                raise HTTPException(status_code=400, detail=f"Invalid UUID format: {skill_uuid}")
            skill_handler.write_manifest(skill_uuid_normalized, merged_manifest)
            
            # Update description for search capability (indexed by UUID)
            if skills_descriptions and merged_manifest.get("description"):
                skills_descriptions.write_description(skill_uuid, merged_manifest["description"])
                logger.info(f"Skill description updated for UUID: {skill_uuid}")
            
            logger.info(f"Skill with ID '{id}' (UUID: {skill_uuid}) updated successfully")
            return {"message": f"Skill with ID '{id}' updated successfully."}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating skill '{id}': {e}")
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
                    logger.warning(f"Matched entity missing 'filename' field: {matched_entity}")
                    continue
                try:
                    # Get skill by UUID
                    skill_dict = skill_handler.get_resource_by_id(skill_uuid)
                    skill_dict["similarity_score"] = matched_entity.get("similarity_score", 0.0)
                    skills_to_filter.append(skill_dict)
                except Exception as e:
                    logger.warning(f"Could not load skill with UUID {skill_uuid} for filtering: {e}")

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
            all_tool_names = [t.name for t in tools]

            for tool in tools:
                try:
                    tool_dict = tool.to_dict()
                    tool_uuid = str(uuid.uuid4())

                    # Prepare tool data
                    ext = (
                        ".py" if tool_dict["programmingLanguage"] == "python" else ".sh"
                    )
                    module_filename = f"{tool_dict['name']}{ext}"

                    # Add additional tags to tool tags
                    tool_tags = tool_dict["tags"].copy() if tool_dict["tags"] else []
                    for tag in tags:
                        if tag and tag not in tool_tags:
                            tool_tags.append(tag)

                    tool_data = {
                        "uuid": tool_uuid,
                        "name": tool_dict["name"],
                        "version": tool_dict["version"],
                        "description": tool_dict["description"],
                        "tags": tool_tags,
                        "programming_language": tool_dict["programmingLanguage"],
                        "module_name": module_filename,
                        "packaging_format": "code",
                        "state": "approved",
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
                            # Get list of available tools (existing + being imported)
                            existing_tools = tools_handler.get_available_resource_names()
                            available_tools = list(set(existing_tools + all_tool_names))
                            # Detect dependencies from code
                            detected_deps = detect_tool_dependencies(
                                tool_dict["moduleContent"],
                                tool_dict["name"],
                                available_tools,
                            )
                            if detected_deps:
                                tool_data["dependencies"] = detected_deps
                                logger.info(
                                    f"Auto-detected dependencies for '{tool_dict['name']}': {detected_deps}"
                                )
                        except Exception as e:
                            logger.warning(f"Failed to auto-detect dependencies for {tool_dict['name']}: {e}")
                    
                    # Save tool manifest to UUID subfolder
                    tool_uuid_normalized = normalize_uuid(tool_uuid)
                    if not tool_uuid_normalized:
                        raise HTTPException(status_code=400, detail=f"Invalid UUID format: {tool_uuid}")
                    tools_handler.write_manifest(tool_uuid_normalized, tool_data)

                    # Save tool module to UUID subfolder
                    tools_handler.write_resource_file(tool_uuid_normalized, module_filename, tool_dict['moduleContent'])
                    
                    created_tool_uuids.append(tool_uuid)
                    logger.info(f"Created tool: {tool_dict['name']}")
                except Exception as e:
                    logger.error(f"Failed to create tool {tool.name}: {e}")

            # Create snippets
            created_snippet_uuids = []
            for snippet in snippets:
                try:
                    snippet_dict = snippet.to_dict()
                    snippet_uuid = str(uuid.uuid4())

                    # Add additional tags to snippet tags
                    snippet_tags = (
                        snippet_dict["tags"].copy() if snippet_dict["tags"] else []
                    )
                    for tag in tags:
                        if tag and tag not in snippet_tags:
                            snippet_tags.append(tag)

                    # Prepare snippet data
                    snippet_data = {
                        "uuid": snippet_uuid,
                        "name": snippet_dict["name"],
                        "version": snippet_dict["version"],
                        "description": snippet_dict["description"],
                        "content": snippet_dict["content"],
                        "tags": snippet_tags,
                        "content_type": "text/plain",
                        "state": "approved",
                    }
                    
                    # Save snippet manifest to UUID subfolder
                    snippet_uuid_normalized = normalize_uuid(snippet_uuid)
                    if not snippet_uuid_normalized:
                        raise HTTPException(status_code=400, detail=f"Invalid UUID format: {snippet_uuid}")
                    snippets_handler.write_manifest(snippet_uuid_normalized, snippet_data)
                    
                    created_snippet_uuids.append(snippet_uuid)
                    logger.info(f"Created snippet: {snippet_dict['name']}")
                except Exception as e:
                    logger.error(f"Failed to create snippet {snippet.name}: {e}")

            # Prepare skill schema with UUID (either existing or None for new)
            skill_schema = SkillSchema(
                uuid=None,
                name=skill_name,
                version="1.0.0",
                description=skill_description,
                tags=["anthropic", "imported"],
                tool_uuids=created_tool_uuids,
                snippet_uuids=created_snippet_uuids,
                state=ManifestState.APPROVED,
            )
            
            # Create new skill
            logger.info(f"Creating new skill '{skill_name}'...")
            result = create_skill(skill_schema)
            skill_uuid = result.get("uuid")
            action = "created"
            
            logger.info(f"Successfully imported Anthropic skill: {skill_name} ({action})")

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

    @app.get("/skills/{id}/export-anthropic", tags=[tags])
    async def export_anthropic_skill(id: str):
        """Export a skill to Anthropic format as a ZIP file.

        Args:
            id: The ID of the skill to export (can be either name or UUID)
            
        Returns:
            ZIP file with the skill in Anthropic format

        Raises:
            HTTPException: If skill not found or export fails
        """
        logger.info(f"Request to export skill to Anthropic format: {id}")
        
        try:
            # Get skill by ID (name or UUID)
            skill_dict = skill_handler.get_resource_by_id(id)
            
            # Get tools using get_resources_by_ids
            tools = []
            tool_modules = {}
            if 'tool_uuids' in skill_dict and skill_dict['tool_uuids']:
                tools = tools_handler.get_resources_by_ids(skill_dict['tool_uuids'])
                # Get tool modules
                for tool_dict in tools:
                    tool_uuid = tool_dict.get('uuid')
                    tool_name = tool_dict['name']
                    module_name = tool_dict.get('module_name')
                    if tool_uuid and module_name:
                        try:
                            module_content = tools_handler.read_resource_file(tool_uuid, module_name, raw_content=True)
                            if isinstance(module_content, str):
                                tool_modules[tool_name] = module_content
                        except Exception as e:
                            logger.warning(f"Could not read module for tool {tool_name}: {e}")
            
            # Get snippets using get_resources_by_ids
            snippets = []
            if 'snippet_uuids' in skill_dict and skill_dict['snippet_uuids']:
                snippets = snippets_handler.get_resources_by_ids(skill_dict['snippet_uuids'])
            
            # Export to Anthropic format
            zip_content = export_skill_to_anthropic_format(
                skill=skill_dict,
                tools=tools,
                snippets=snippets,
                tool_modules=tool_modules,
            )
            
            logger.info(f"Successfully exported skill '{id}' to Anthropic format")
            
            # Return as downloadable ZIP file
            return Response(
                content=zip_content,
                media_type='application/zip',
                headers={
                    'Content-Disposition': f'attachment; filename="{id}.zip"'
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error exporting skill '{id}' to Anthropic format: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error exporting skill: {str(e)}"
            )
