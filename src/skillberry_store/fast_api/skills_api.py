"""Skills API endpoints for the Skillberry Store service."""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Annotated
from fastapi import Body, FastAPI, HTTPException, Query, Request, UploadFile, File, Form
from fastapi.responses import Response
from prometheus_client import Counter

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.file_executor import detect_tool_dependencies
from skillberry_store.modules.description import Description
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.skill_schema import SkillSchema
from skillberry_store.tools.configure import (
    get_skills_directory,
    get_tools_directory,
    get_snippets_directory,
    is_auto_detect_dependencies_enabled,
)
from skillberry_store.fast_api.search_filters import apply_search_filters
from skillberry_store.fast_api.skill_export_utils import get_skill_export_data
from skillberry_store.schemas.name_validation import validate_store_name

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
    skill_handler = FileHandler(skills_directory)
    tools_handler = FileHandler(get_tools_directory())
    snippets_handler = FileHandler(get_snippets_directory())
    
    def populate_skill_objects(skill_dict):
        """Populate full tool and snippet objects from UUIDs."""
        # Populate tools
        if "tool_uuids" in skill_dict and skill_dict["tool_uuids"]:
            tools = []
            for tool_uuid in skill_dict["tool_uuids"]:
                # Find tool by UUID
                for filename in tools_handler.list_files():
                    if filename.endswith(".json"):
                        try:
                            content = tools_handler.read_file(filename, raw_content=True)
                            if isinstance(content, str):
                                tool_dict = json.loads(content)
                                if tool_dict.get("uuid") == tool_uuid:
                                    tools.append(tool_dict)
                                    break
                        except Exception as e:
                            logger.warning(f"Error reading tool file {filename}: {e}")
            skill_dict["tools"] = tools
        else:
            skill_dict["tools"] = []
            
        # Populate snippets
        if "snippet_uuids" in skill_dict and skill_dict["snippet_uuids"]:
            snippets = []
            for snippet_uuid in skill_dict["snippet_uuids"]:
                # Find snippet by UUID
                for filename in snippets_handler.list_files():
                    if filename.endswith(".json"):
                        try:
                            content = snippets_handler.read_file(filename, raw_content=True)
                            if isinstance(content, str):
                                snippet_dict = json.loads(content)
                                if snippet_dict.get("uuid") == snippet_uuid:
                                    snippets.append(snippet_dict)
                                    break
                        except Exception as e:
                            logger.warning(f"Error reading snippet file {filename}: {e}")
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

        # Validate the skill name as an MCP-safe slug — spaces / uppercase
        # would break `claude mcp add <name>` and URL-segment usage.
        validate_store_name(skill.name, kind="skill")

        # Generate UUID if not provided
        if not skill.uuid:
            skill.uuid = str(uuid.uuid4())
            logger.info(f"Generated UUID for skill '{skill.name}': {skill.uuid}")

        # Set timestamps
        current_time = datetime.now(timezone.utc).isoformat()
        skill.created_at = current_time
        skill.modified_at = current_time

        # Check if skill already exists
        existing_skills = skill_handler.list_files()
        skill_filename = f"{skill.name}.json"

        if skill_filename in existing_skills:
            raise HTTPException(
                status_code=409, detail=f"Skill '{skill.name}' already exists."
            )

        try:
            # Convert skill to JSON and save
            skill_json = json.dumps(skill.to_dict(), indent=4)
            skill_handler.write_file_content(skill_filename, skill_json)

            # Write description for search capability
            if skills_descriptions and skill.description:
                skills_descriptions.write_description(skill.name, skill.description)
                logger.info(f"Skill description saved for: {skill.name}")

            logger.info(f"Skill '{skill.name}' created successfully")
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
            skill_files = skill_handler.list_files()
            skills = []

            for filename in skill_files:
                if filename.endswith(".json"):
                    content = skill_handler.read_file(filename, raw_content=True)
                    if isinstance(content, str):
                        skill_dict = json.loads(content)
                        # Populate full tool and snippet objects
                        skill_dict = populate_skill_objects(skill_dict)
                    else:
                        continue
                    skills.append(skill_dict)

            # Sort by modified_at in descending order (most recent first)
            skills.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

            logger.info(f"Listed {len(skills)} skills")
            return skills
        except Exception as e:
            logger.error(f"Error listing skills: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing skills: {str(e)}"
            )

    @app.get("/skills/{name}", tags=[tags])
    def get_skill(name: str):
        """Get a specific skill by name with populated tool and snippet objects.

        Args:
            name: The name of the skill.

        Returns:
            dict: The skill object with full tool and snippet details.

        Raises:
            HTTPException: If skill not found (404) or retrieval fails (500).
        """
        logger.info(f"Request to get skill: {name}")
        get_skill_counter.inc()

        try:
            skill_filename = f"{name}.json"
            content = skill_handler.read_file(skill_filename, raw_content=True)
            if not isinstance(content, str):
                raise HTTPException(
                    status_code=500, detail=f"Invalid content type for skill '{name}'"
                )
            skill_dict = json.loads(content)
            # Populate full tool and snippet objects
            skill_dict = populate_skill_objects(skill_dict)
            logger.info(f"Retrieved skill: {name}")
            return skill_dict
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving skill '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving skill: {str(e)}"
            )

    @app.delete("/skills/{name}", tags=[tags])
    def delete_skill(name: str):
        """Delete a skill by name.

        Args:
            name: The name of the skill to delete.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If skill not found (404) or deletion fails (500).
        """
        logger.info(f"Request to delete skill: {name}")
        delete_skill_counter.inc()

        try:
            skill_filename = f"{name}.json"
            result = skill_handler.delete_file(skill_filename)

            # Delete the description for the skill
            if skills_descriptions:
                try:
                    skills_descriptions.delete_description(name)
                    logger.info(f"Skill description deleted for: {name}")
                except Exception as e:
                    logger.warning(
                        f"Could not delete skill description for '{name}': {e}"
                    )

            logger.info(f"Skill '{name}' deleted successfully")
            return {"message": f"Skill '{name}' deleted successfully."}
        except HTTPException as e:
            # Re-raise HTTPException (like 404) without modification
            raise
        except Exception as e:
            logger.error(f"Error deleting skill '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting skill: {str(e)}"
            )

    @app.put("/skills/{name}", tags=[tags])
    def update_skill(name: str, skill: SkillSchema):
        """Update an existing skill.

        Args:
            name: The name of the skill to update.
            skill: The updated skill schema.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If skill not found (404) or update fails (500).
        """
        logger.info(f"Request to update skill: {name}")
        update_skill_counter.inc()

        try:
            skill_filename = f"{name}.json"

            # Check if skill exists
            existing_skills = skill_handler.list_files()
            if skill_filename not in existing_skills:
                raise HTTPException(
                    status_code=404, detail=f"Skill '{name}' not found."
                )

            # Update modified timestamp
            skill.modified_at = datetime.now(timezone.utc).isoformat()

            # Update the skill
            skill_json = json.dumps(skill.to_dict(), indent=4)
            skill_handler.write_file_content(skill_filename, skill_json)
            logger.info(f"Skill '{name}' updated successfully")
            return {"message": f"Skill '{name}' updated successfully."}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating skill '{name}': {e}")
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
            skills_to_filter = []
            for matched_entity in filtered_matched_entities:
                skill_name = matched_entity.get("filename") or matched_entity.get("name")
                if not skill_name:
                    logger.warning(f"Matched entity missing 'filename' or 'name' field: {matched_entity}")
                    continue
                try:
                    skill_filename = f"{skill_name}.json"
                    content = skill_handler.read_file(skill_filename, raw_content=True)
                    if isinstance(content, str):
                        skill_dict = json.loads(content)
                        skill_dict["similarity_score"] = matched_entity.get("similarity_score", 0.0)
                        skills_to_filter.append(skill_dict)
                except Exception as e:
                    logger.warning(f"Could not load skill {skill_name} for filtering: {e}")

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
                {"filename": skill.get("name", ""), "similarity_score": skill.get("similarity_score", 0.0)}
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
        request: Request,
        source_type: str = Form(...),
        github_url: Optional[str] = Form(None),
        zip_file: Optional[UploadFile] = File(None),
        folder_path: Optional[str] = Form(None),
        snippet_mode: str = Form("file"),
    ):
        """Import an Anthropic skill from GitHub URL, ZIP file, or local folder.
        
        Args:
            source_type: 'url', 'zip', or 'folder'
            github_url: GitHub repository URL (required if source_type='url')
            zip_file: ZIP file upload (required if source_type='zip')
            folder_path: Local folder path (required if source_type='folder')
            snippet_mode: 'file' or 'paragraph' - how to import text files
            
        Returns:
            dict: Import result with created tools, snippets, and skill info
            
        Raises:
            HTTPException: If import fails
        """
        logger.info(f"Request to import Anthropic skill from {source_type}")
        
        try:
            from skillberry_store.tools.anthropic.importer import import_anthropic_skill
            
            # Prepare source data based on type
            source_data = None
            if source_type == 'url':
                if not github_url:
                    raise HTTPException(status_code=400, detail="github_url is required for source_type='url'")
                source_data = github_url
            elif source_type == 'zip':
                if not zip_file:
                    raise HTTPException(status_code=400, detail="zip_file is required for source_type='zip'")
                source_data = await zip_file.read()
            elif source_type == 'folder':
                if not folder_path:
                    raise HTTPException(status_code=400, detail="folder_path is required for source_type='folder'")
                source_data = folder_path
            else:
                raise HTTPException(status_code=400, detail=f"Invalid source_type: {source_type}. Must be 'url', 'zip', or 'folder'")
            
            # Import the skill (6-tuple now — the last element is an optional
            # external-MCP config payload bundled as `mcp-servers.json`).
            skill_name, skill_description, tools, snippets, ignored_files, mcp_servers_payload = import_anthropic_skill(
                source_type=source_type,
                source_data=source_data,
                snippet_mode=snippet_mode
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
                    ext = '.py' if tool_dict['programmingLanguage'] == 'python' else '.sh'
                    module_filename = f"{tool_dict['name']}{ext}"
                    
                    tool_data = {
                        'uuid': tool_uuid,
                        'name': tool_dict['name'],
                        'version': tool_dict['version'],
                        'description': tool_dict['description'],
                        'tags': tool_dict['tags'],
                        'programming_language': tool_dict['programmingLanguage'],
                        'module_name': module_filename,
                        'packaging_format': 'code',
                        'state': 'approved',
                    }
                    
                    if 'params' in tool_dict and tool_dict['params']:
                        tool_data['params'] = tool_dict['params']
                    if 'returns' in tool_dict and tool_dict['returns']:
                        tool_data['returns'] = tool_dict['returns']
                    
                    # Auto-detect dependencies for Python tools if enabled
                    if tool_dict['programmingLanguage'] == 'python' and is_auto_detect_dependencies_enabled():
                        try:
                            # Get list of available tools (existing + being imported)
                            existing_tools = [f.replace('.json', '') for f in tools_handler.list_files()]
                            available_tools = list(set(existing_tools + all_tool_names))
                            # Detect dependencies from code
                            detected_deps = detect_tool_dependencies(
                                tool_dict['moduleContent'],
                                tool_dict['name'],
                                available_tools
                            )
                            if detected_deps:
                                tool_data['dependencies'] = detected_deps
                                logger.info(f"Auto-detected dependencies for '{tool_dict['name']}': {detected_deps}")
                        except Exception as e:
                            logger.warning(f"Failed to auto-detect dependencies for {tool_dict['name']}: {e}")
                    
                    # Save tool JSON
                    tool_filename = f"{tool_dict['name']}.json"
                    tool_json = json.dumps(tool_data, indent=4)
                    tools_handler.write_file_content(tool_filename, tool_json)
                    
                    # Save tool module
                    from skillberry_store.tools.configure import get_files_directory_path
                    from skillberry_store.modules.file_handler import FileHandler
                    files_handler = FileHandler(get_files_directory_path())
                    files_handler.write_file_content(module_filename, tool_dict['moduleContent'])
                    
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
                    
                    # Prepare snippet data
                    snippet_data = {
                        'uuid': snippet_uuid,
                        'name': snippet_dict['name'],
                        'version': snippet_dict['version'],
                        'description': snippet_dict['description'],
                        'content': snippet_dict['content'],
                        'tags': snippet_dict['tags'],
                        'content_type': 'text/plain',
                        'state': 'approved',
                    }
                    
                    # Save snippet JSON
                    snippet_filename = f"{snippet_dict['name']}.json"
                    snippet_json = json.dumps(snippet_data, indent=4)
                    snippets_handler.write_file_content(snippet_filename, snippet_json)
                    
                    created_snippet_uuids.append(snippet_uuid)
                    logger.info(f"Created snippet: {snippet_dict['name']}")
                except Exception as e:
                    logger.error(f"Failed to create snippet {snippet.name}: {e}")
            
            # Create skill
            skill_uuid = str(uuid.uuid4())
            skill_data = {
                'uuid': skill_uuid,
                'name': skill_name,
                'version': '1.0.0',
                'description': skill_description,
                'tags': ['anthropic', 'imported'],
                'tool_uuids': created_tool_uuids,
                'snippet_uuids': created_snippet_uuids,
                'state': 'approved',
            }
            
            skill_filename = f"{skill_name}.json"
            skill_json = json.dumps(skill_data, indent=4)
            skill_handler.write_file_content(skill_filename, skill_json)
            
            # Write description for search capability
            if skills_descriptions and skill_description:
                skills_descriptions.write_description(skill_name, skill_description)
            
            # Auto-register any external MCP servers bundled with the skill.
            # Duplicates (name already registered) are skipped — we never
            # overwrite a live server's config on import.
            mcp_results = []
            if mcp_servers_payload:
                try:
                    from skillberry_store.modules.external_mcp_manager import normalize_mcp_input
                    mgr = getattr(request.app.state, "external_mcp_manager", None)
                    if mgr is None:
                        logger.warning("Skill bundles an mcp-servers.json but the external MCP manager is not available.")
                    else:
                        try:
                            entries = normalize_mcp_input(mcp_servers_payload)
                        except ValueError as e:
                            logger.warning(f"Skill mcp-servers.json could not be parsed: {e}")
                            entries = []
                        existing = {s["name"] for s in mgr.list_servers()}
                        for entry in entries:
                            name = entry.get("name")
                            if name in existing:
                                mcp_results.append({"name": name, "status": "skipped_duplicate"})
                                continue
                            try:
                                res = await mgr.start(entry, persist=True)
                                mcp_results.append(res)
                            except Exception as e:  # noqa: BLE001
                                logger.error(f"Failed to auto-register MCP '{name}' from skill: {e}")
                                mcp_results.append({"name": name, "status": "error", "error": str(e)})
                except Exception as e:
                    logger.warning(f"mcp-servers.json auto-registration skipped: {e}")

            logger.info(f"Successfully imported Anthropic skill: {skill_name}")

            return {
                'success': True,
                'message': f"Successfully imported Anthropic skill '{skill_name}'",
                'skill_name': skill_name,
                'skill_uuid': skill_uuid,
                'tools_created': len(created_tool_uuids),
                'snippets_created': len(created_snippet_uuids),
                'ignored_files': ignored_files,
                'mcp_servers': mcp_results,
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error importing Anthropic skill: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error importing Anthropic skill: {str(e)}"
            )

    def _get_skill_export_data(name: str):
        """Gather skill dict, tools, snippets, and tool modules for export."""
        return get_skill_export_data(name)

    @app.post("/skills/{name}/bulk-add-tools-from-mcps", tags=[tags])
    def bulk_add_tools_from_mcps(
        name: str,
        body: Dict[str, Any] = Body(
            ...,
            example={"mcps": ["context7"], "mode": "bundled_related"},
        ),
    ) -> Dict[str, Any]:
        """Add tools to a skill in bulk based on which external MCP(s) they
        touch.

        Body fields:
          - `mcps`: list of external MCP server names (required, non-empty)
          - `mode`: one of
              * `"primitives"`       — MCP primitives whose `mcp_server` is in `mcps`
              * `"related"`          — primitives + every composite whose
                `mcp_dependencies` intersects `mcps` (the transitive closure).
                Ignores the `bundled_with_mcps` flag entirely.
              * `"bundled_related"`  — same as `related`, but skips any tool
                whose `bundled_with_mcps` is explicitly `False`. (If you want
                those included, use `related` instead.)

        Tools already in the skill are skipped. Broken tools are skipped and
        reported in the response.

        Returns: `{ skill, mode, requested_mcps, added, skipped_duplicate,
        skipped_broken, skipped_unbundled }`.
        """
        mcps_in = body.get("mcps")
        mode = (body.get("mode") or "").strip()
        if not isinstance(mcps_in, list) or not mcps_in:
            raise HTTPException(400, "`mcps` must be a non-empty list of server names.")
        if mode not in ("primitives", "related", "bundled_related"):
            raise HTTPException(
                400,
                "`mode` must be one of: primitives, related, bundled_related",
            )
        mcp_set = set(mcps_in)

        skill_filename = f"{name}.json"
        try:
            skill_raw = skill_handler.read_file(skill_filename, raw_content=True)
        except Exception:
            raise HTTPException(404, f"Skill '{name}' not found.")
        if not isinstance(skill_raw, str):
            raise HTTPException(500, f"Invalid content for skill '{name}'")
        skill_dict = json.loads(skill_raw)
        existing_uuids = set(skill_dict.get("tool_uuids") or [])

        added: List[Dict[str, str]] = []
        skipped_duplicate: List[str] = []
        skipped_broken: List[Dict[str, str]] = []
        skipped_unbundled: List[str] = []

        for fname in tools_handler.list_files():
            if not fname.endswith(".json"):
                continue
            try:
                d = json.loads(tools_handler.read_file(fname, raw_content=True))
            except Exception:
                continue

            tool_mcp = d.get("mcp_server")
            tool_deps = set(d.get("mcp_dependencies") or [])
            touches_requested = (tool_mcp in mcp_set) or bool(tool_deps & mcp_set)
            if not touches_requested:
                continue

            if mode == "primitives" and tool_mcp not in mcp_set:
                continue  # composites excluded
            if mode == "bundled_related" and d.get("bundled_with_mcps") is False:
                skipped_unbundled.append(d.get("name") or fname[:-5])
                continue
            if d.get("state") == "broken":
                skipped_broken.append({
                    "name": d.get("name"),
                    "reason": d.get("broken_reason") or "broken",
                })
                continue
            if d.get("uuid") in existing_uuids:
                skipped_duplicate.append(d.get("name") or fname[:-5])
                continue

            existing_uuids.add(d["uuid"])
            added.append({"name": d["name"], "uuid": d["uuid"]})

        if added:
            skill_dict["tool_uuids"] = sorted(existing_uuids)
            skill_dict["modified_at"] = datetime.now(timezone.utc).isoformat()
            skill_handler.write_file_content(skill_filename, json.dumps(skill_dict, indent=4))

        return {
            "skill": name,
            "mode": mode,
            "requested_mcps": sorted(mcp_set),
            "added": added,
            "skipped_duplicate": skipped_duplicate,
            "skipped_broken": skipped_broken,
            "skipped_unbundled": skipped_unbundled,
        }

    @app.get("/skills/{name}/export-anthropic", tags=[tags])
    async def export_anthropic_skill(name: str):
        """Export a skill to Anthropic format as a ZIP file.

        Args:
            name: The name of the skill to export

        Returns:
            ZIP file with the skill in Anthropic format

        Raises:
            HTTPException: If skill not found or export fails
        """
        logger.info(f"Request to export skill to Anthropic format: {name}")

        try:
            from skillberry_store.tools.anthropic.exporter import export_skill_to_anthropic_format

            skill_dict, tools, snippets, tool_modules, mcp_servers = _get_skill_export_data(name)

            zip_content = export_skill_to_anthropic_format(
                skill=skill_dict,
                tools=tools,
                snippets=snippets,
                tool_modules=tool_modules,
                mcp_servers=mcp_servers,
            )

            logger.info(f"Successfully exported skill '{name}' to Anthropic format")

            return Response(
                content=zip_content,
                media_type='application/zip',
                headers={
                    'Content-Disposition': f'attachment; filename="{name}.zip"'
                }
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error exporting skill '{name}' to Anthropic format: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error exporting skill: {str(e)}"
            )

