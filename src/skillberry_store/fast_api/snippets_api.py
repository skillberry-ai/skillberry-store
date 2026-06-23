"""Snippets API endpoints for the Skillberry Store service."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional, Annotated
from fastapi import FastAPI, HTTPException, Query, File, UploadFile
from prometheus_client import Counter
from skillberry_store.plugins.events import (
    emit_content_added,
    emit_content_updated,
    emit_content_deleted,
)
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.snippet_schema import SnippetSchema
from skillberry_store.fast_api.search_filters import apply_search_filters
from skillberry_store.services.snippets_service import SnippetsService

if TYPE_CHECKING:
    from skillberry_store.modules.description import Description

logger = logging.getLogger(__name__)

prom_prefix = "sts_fastapi_snippets_"
create_snippet_counter = Counter(
    f"{prom_prefix}create_snippet_counter", "Count number of snippet create operations"
)
list_snippets_counter = Counter(
    f"{prom_prefix}list_snippets_counter", "Count number of snippet list operations"
)
get_snippet_counter = Counter(
    f"{prom_prefix}get_snippet_counter", "Count number of snippet get operations"
)
delete_snippet_counter = Counter(
    f"{prom_prefix}delete_snippet_counter", "Count number of snippet delete operations"
)
update_snippet_counter = Counter(
    f"{prom_prefix}update_snippet_counter", "Count number of snippet update operations"
)
search_snippets_counter = Counter(
    f"{prom_prefix}search_snippets_counter", "Count number of snippet search operations"
)


def register_snippets_api(
    app: FastAPI,
    tags: str = "snippets",
    snippets_descriptions: Optional[Description] = None,
    service: Optional[SnippetsService] = None,
):
    """Register all snippets-related API endpoints with the FastAPI application.

    This function sets up all REST API endpoints for managing snippets including
    create, read, update, delete, and search operations.

    Args:
        app: The FastAPI application instance to register routes with.
        tags: OpenAPI tag for grouping these endpoints (default: "snippets").
        snippets_descriptions: Optional Description instance for semantic search functionality.
        service: Optional SnippetsService instance. If None, a new instance will be created.

    Returns:
        None. Endpoints are registered directly on the app instance.
    """
    if service is None:
        from skillberry_store.modules.object_handler import get_object_handler

        service = SnippetsService(get_object_handler("snippet"), snippets_descriptions)

    @app.post("/snippets/", tags=[tags], openapi_extra={"x-cli-name": "create-snippet"})
    async def create_snippet(
        snippet: Annotated[SnippetSchema, Query()],
        file: Optional[UploadFile] = File(None),
    ):
        """Create a new snippet in the store.

        Creates a snippet with text content. Content can be provided either in the
        snippet schema or uploaded as a file. Snippets are reusable text blocks
        that can be referenced by skills.

        Args:
            snippet: Snippet metadata conforming to SnippetSchema (name, description, content, etc.).
            file: Optional file upload containing snippet content. If provided, overrides snippet.content.

        Returns:
            dict: Success message with snippet name and UUID.

        Raises:
            HTTPException: 400 if file reading fails, 409 if snippet already exists, 500 for other errors.
        """
        logger.info(f"Request to create snippet: {snippet.name}")
        create_snippet_counter.inc()
        if file:
            try:
                content_bytes = await file.read()
                snippet.content = content_bytes.decode("utf-8")
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Error reading uploaded file: {str(e)}"
                )
        try:
            result = service.create(snippet.to_dict())
            emit_content_added("snippet", result["uuid"])
            return {
                "message": f"Snippet '{result['name']}' created successfully.",
                "name": result["name"],
                "uuid": result["uuid"],
            }
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating snippet '{snippet.name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating snippet: {str(e)}"
            )

    @app.get("/snippets/", tags=[tags], openapi_extra={"x-cli-name": "list-snippets"})
    def list_snippets():
        """List all snippets in the store.

        Retrieves metadata for all snippets currently stored in the system.

        Args:
            None.

        Returns:
            list: List of dictionaries, each containing snippet metadata (name, uuid, description, content, etc.).

        Raises:
            HTTPException: 500 if listing fails.
        """
        logger.info("Request to list snippets")
        list_snippets_counter.inc()
        try:
            return service.list_all()
        except Exception as e:
            logger.error(f"Error listing snippets: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing snippets: {str(e)}"
            )

    @app.get(
        "/snippets/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "get-snippet"},
    )
    def get_snippet(uuid_or_name: str):
        """Get metadata for a specific snippet by UUID or name.

        Retrieves the complete manifest/metadata for a snippet identified by either
        its UUID or its unique name.

        Args:
            uuid_or_name: The UUID or name of the snippet to retrieve.

        Returns:
            dict: Snippet metadata including name, uuid, description, content, etc.

        Raises:
            HTTPException: 404 if snippet not found, 500 for other errors.
        """
        logger.info(f"Request to get snippet: {uuid_or_name}")
        get_snippet_counter.inc()
        try:
            return service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error retrieving snippet '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving snippet: {str(e)}"
            )

    @app.delete(
        "/snippets/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "delete-snippet"},
    )
    async def delete_snippet(uuid_or_name: str):
        """Delete a snippet from the store.

        Removes a snippet from the store. This operation triggers a content
        deletion event for plugin processing.

        Args:
            uuid_or_name: The UUID or name of the snippet to delete.

        Returns:
            dict: Success message confirming deletion.

        Raises:
            HTTPException: 404 if snippet not found, 500 for other errors.
        """
        logger.info(f"Request to delete snippet: {uuid_or_name}")
        delete_snippet_counter.inc()
        try:
            snippet = service.get(uuid_or_name)
            snippet_uuid = snippet["uuid"]
            service.delete(uuid_or_name)
            emit_content_deleted("snippet", snippet_uuid)
            return {
                "message": f"Snippet with UUID or name '{uuid_or_name}' deleted successfully."
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.exception(f"Error deleting snippet '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting snippet: {str(e)}"
            )

    @app.put(
        "/snippets/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "update-snippet"},
    )
    async def update_snippet(uuid_or_name: str, snippet: SnippetSchema):
        """Update an existing snippet's metadata and content.

        Updates the manifest/metadata and content for an existing snippet.
        This operation triggers a content update event for plugin processing.

        Args:
            uuid_or_name: The UUID or name of the snippet to update.
            snippet: Updated snippet metadata conforming to SnippetSchema.

        Returns:
            dict: Success message confirming update.

        Raises:
            HTTPException: 404 if snippet not found, 500 for other errors.
        """
        logger.info(f"Request to update snippet: {uuid_or_name}")
        update_snippet_counter.inc()
        try:
            result = service.update(uuid_or_name, snippet.to_dict())
            emit_content_updated("snippet", result["uuid"])
            return {
                "message": f"Snippet with UUID or name '{uuid_or_name}' updated successfully."
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating snippet '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating snippet: {str(e)}"
            )

    @app.get(
        "/search/snippets", tags=[tags], openapi_extra={"x-cli-name": "search-snippets"}
    )
    def search_snippets(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ):
        """Search for snippets using semantic similarity.

        Returns snippets that are semantically similar to the search term and
        match the specified filters.

        Args:
            search_term: Search term to find similar snippets.
            max_number_of_results: Maximum number of results to return (default: 5).
            similarity_threshold: Maximum similarity score threshold (default: 1, lower is more similar).
            manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
            lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).

        Returns:
            list: List of matched snippet names and similarity scores.

        Raises:
            HTTPException: 503 if search is not available, 500 for other errors.
        """
        logger.info(f"Request to search snippets for term: {search_term}")
        search_snippets_counter.inc()
        if not snippets_descriptions:
            raise HTTPException(
                status_code=503, detail="Snippet search is not available"
            )
        try:
            matched = snippets_descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )
            filtered = [
                m
                for m in matched
                if float(m["similarity_score"]) <= similarity_threshold
            ]
            snippets_to_filter = []
            for m in filtered:
                name = m.get("filename") or m.get("name")
                if not name:
                    continue
                try:
                    d = service.get(name)
                    d["similarity_score"] = m.get("similarity_score", 0.0)
                    snippets_to_filter.append(d)
                except Exception:
                    pass
            result_snippets = apply_search_filters(
                snippets_to_filter,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )
            result_snippets.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return [
                {
                    "filename": s.get("name", ""),
                    "similarity_score": s.get("similarity_score", 0.0),
                }
                for s in result_snippets
                if s.get("name")
            ]
        except Exception as e:
            logger.error(f"Error searching snippets: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error searching snippets: {str(e)}"
            )
