"""Skills API endpoints for the Skillberry Store service."""

from __future__ import annotations

import logging
from typing import Optional, Annotated, List, Any
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Header
from fastapi.responses import Response
from prometheus_client import Counter
from skillberry_store.plugins.events import (
    emit_content_added,
    emit_content_updated,
    emit_content_deleted,
)

from skillberry_store.tools.endpoint_auth import ReauthRequired
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.skill_schema import SkillSchema
from skillberry_store.services.skills_service import SkillsService

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
    service: Optional[SkillsService] = None,
):
    """Register skills API endpoints with the FastAPI application.

    Args:
        app: The FastAPI application instance.
        tags: FastAPI tags for grouping the endpoints in documentation.
        service: Optional SkillsService instance. When ``None``, the singleton
            from :func:`skillberry_store.services.registry.get_service` is used.
    """
    if service is None:
        from skillberry_store.services.registry import get_service

        service = get_service("skill")
    assert service is not None  # narrowed for type checker

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
            cascade = service.delete(
                uuid_or_name,
                delete_tools=delete_tools,
                delete_snippets=delete_snippets,
            )
            emit_content_deleted("skill", skill_uuid)
            return {
                "message": f"Skill with UUID or name '{uuid_or_name}' deleted successfully.",
                "deleted_tools": cascade.get("deleted_tools", []),
                "deleted_snippets": cascade.get("deleted_snippets", []),
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
        try:
            return service.search(
                search_term=search_term,
                max_number_of_results=max_number_of_results,
                similarity_threshold=similarity_threshold,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
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
        from skillberry_store.services.skills_service import GithubApiError

        logger.info(f"Request to detect Anthropic skills from {source_type}")
        try:
            skill_paths = service.detect_anthropic_skills(
                source_type=source_type,
                github_url=github_url,
                folder_path=folder_path,
                override_token=x_endpoint_token,
                anonymous=anonymous,
            )
            return {
                "success": True,
                "skill_paths": skill_paths,
                "total": len(skill_paths),
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ReauthRequired as e:
            raise _auth_exception_to_http(e)
        except GithubApiError as e:
            raise HTTPException(status_code=e.status_code, detail=e.message)
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
        # Validate inputs and convert UploadFile to bytes at the API boundary.
        if source_type == "url":
            if not github_url:
                raise HTTPException(
                    status_code=400,
                    detail="github_url is required for source_type='url'",
                )
            source_data: Any = github_url
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

        try:
            result = service.import_anthropic(
                source_type=source_type,
                source_data=source_data,
                snippet_mode=snippet_mode,
                treat_all_as_documents=treat_all_as_documents,
                tags=tags,
                override_token=x_endpoint_token,
                anonymous=anonymous,
                github_url=github_url,
            )
        except ReauthRequired as e:
            raise _auth_exception_to_http(e)
        except Exception as e:
            logger.error(f"Error importing Anthropic skill: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error importing Anthropic skill: {str(e)}"
            )

        skill_uuid = result.get("skill_uuid")
        if skill_uuid:
            emit_content_added("skill", skill_uuid)
        skill_name = result.get("skill_name")
        logger.info(f"Successfully imported Anthropic skill: {skill_name}")
        return {
            "success": True,
            "message": f"Successfully imported Anthropic skill '{skill_name}' (created)",
            "skill_name": skill_name,
            "skill_uuid": skill_uuid,
            "action": "created",
            "tools_created": result.get("tools_created", 0),
            "snippets_created": result.get("snippets_created", 0),
            "ignored_files": result.get("ignored_files", []),
        }

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
            zip_content = service.export_anthropic(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(
                f"Error exporting skill '{uuid_or_name}' to Anthropic format: {e}"
            )
            raise HTTPException(
                status_code=500, detail=f"Error exporting skill: {str(e)}"
            )
        logger.info(
            f"Successfully exported skill '{uuid_or_name}' to Anthropic format"
        )
        return Response(
            content=zip_content,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{uuid_or_name}.zip"'
            },
        )
