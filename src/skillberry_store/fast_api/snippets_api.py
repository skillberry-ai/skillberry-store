"""Snippets API endpoints for the Skillberry Store service."""

from __future__ import annotations

from typing import List, Optional, Annotated
from fastapi import FastAPI, HTTPException, Query, File, UploadFile

from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.snippet_schema import SnippetSchema
from skillberry_store.services.exceptions import ObjectInUseError
from skillberry_store.services.snippets_service import SnippetsService


def register_snippets_api(
    app: FastAPI,
    tags: str = "snippets",
    service: Optional[SnippetsService] = None,
):
    """Register all snippets-related API endpoints with the FastAPI application.

    This function sets up all REST API endpoints for managing snippets including
    create, read, update, delete, and search operations.

    Args:
        app: The FastAPI application instance to register routes with.
        tags: OpenAPI tag for grouping these endpoints (default: "snippets").
        service: Optional SnippetsService instance. When ``None``, the singleton
            from :func:`skillberry_store.services.registry.get_service` is used.

    Returns:
        None. Endpoints are registered directly on the app instance.
    """
    if service is None:
        from skillberry_store.services.registry import get_service

        service = get_service("snippet")
    assert service is not None  # narrowed for type checker

    @app.post(
        "/snippets/",
        tags=[tags],
        openapi_extra={"x-cli-name": "create-snippet", "x-mcp-tool": True},
    )
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
            return {
                "message": f"Snippet '{result['name']}' created successfully.",
                "name": result["name"],
                "uuid": result["uuid"],
            }
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error creating snippet: {str(e)}"
            )

    @app.get(
        "/snippets/",
        tags=[tags],
        openapi_extra={"x-cli-name": "list-snippets", "x-mcp-tool": True},
    )
    def list_snippets(
        fields: Optional[str] = Query(
            "narrow",
            description=(
                "Field selection. 'minimal' returns uuid only. Omit or "
                "'narrow' for the UI listing set (default). 'wide' "
                "returns every persisted manifest field. 'full' returns "
                "the complete object, including flag fields that "
                "trigger bundling mechanisms. Or supply a comma-"
                "separated allowlist of field names."
            ),
        ),
        search: Optional[str] = Query(
            None,
            description="Case-insensitive substring over name + description.",
        ),
        tags_filter: Optional[List[str]] = Query(
            None,
            alias="tags",
            description=(
                "Repeat to filter by multiple tags (AND semantics). Namespace "
                "tags are ordinary tags — pass ``namespace:xyz`` to filter by "
                "namespace."
            ),
        ),
        state: Optional[str] = Query(
            None, description="Exact-match lifecycle state filter."
        ),
        sort: Optional[str] = Query(
            None,
            description=(
                "``field:direction`` (e.g. ``name:asc``). Defaults to "
                "``modified_at:desc``."
            ),
        ),
        limit: Optional[int] = Query(
            None,
            ge=0,
            description=(
                "Max items to return. Setting ``limit`` (or ``offset``) "
                "switches the response to a ``{items, total, offset, limit}`` "
                "envelope. Omit both for the legacy bare array."
            ),
        ),
        offset: Optional[int] = Query(None, ge=0, description="Page offset."),
    ):
        """List snippets with optional filter / sort / paginate / project.

        See query-param descriptions for behavior. When neither ``limit``
        nor ``offset`` is set, returns a bare list (100% back-compat).
        Otherwise returns ``{items, total, offset, limit}``.

        Raises:
            HTTPException: 400 if ``fields`` is invalid, 500 if listing fails.
        """
        try:
            return service.list_all(
                fields=fields,
                search=search,
                tags=tags_filter,
                state=state,
                sort=sort,
                limit=limit,
                offset=offset,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error listing snippets: {str(e)}"
            )

    @app.get(
        "/snippets/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "get-snippet", "x-mcp-tool": True},
    )
    def get_snippet(
        uuid_or_name: str,
        fields: Optional[str] = Query(
            "narrow",
            description=(
                "Field selection. 'minimal' returns uuid only. Omit or "
                "'narrow' for the UI listing set (default). 'wide' "
                "returns every persisted manifest field (including "
                "``content``). 'full' returns the complete object. Or "
                "supply a comma-separated allowlist of field names."
            ),
        ),
    ):
        """Get metadata for a specific snippet by UUID or name.

        Retrieves the manifest/metadata for a snippet identified by
        either its UUID or its unique name.

        Args:
            uuid_or_name: The UUID or name of the snippet to retrieve.
            fields: Optional field-selection spec (see query-param description).

        Returns:
            dict: Snippet metadata (subset when ``fields`` narrows the
                field selection).

        Raises:
            HTTPException: 400 if ``fields`` is invalid, 404 if snippet
                not found, 500 for other errors.
        """
        try:
            return service.get(uuid_or_name, fields=fields)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error retrieving snippet: {str(e)}"
            )

    @app.delete(
        "/snippets/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "delete-snippet", "x-mcp-tool": True},
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
        try:
            service.delete(uuid_or_name)
            return {
                "message": f"Snippet with UUID or name '{uuid_or_name}' deleted successfully."
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ObjectInUseError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error deleting snippet: {str(e)}"
            )

    @app.put(
        "/snippets/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "update-snippet", "x-mcp-tool": True},
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
        try:
            service.update(uuid_or_name, snippet.to_dict())
            return {
                "message": f"Snippet with UUID or name '{uuid_or_name}' updated successfully."
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error updating snippet: {str(e)}"
            )

    @app.get(
        "/facets/snippets",
        tags=[tags],
        openapi_extra={"x-cli-name": "snippet-facets", "x-mcp-tool": True},
    )
    def snippet_facets():
        """Return the unique tags / namespaces / states over all snippets.

        Powers filter-picker widgets so callers can enumerate every
        available value without fetching every snippet.

        Returns:
            dict: ``{"tags": [...], "namespaces": [...], "states": [...]}``.
        """
        try:
            return service.facets()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error computing snippet facets: {str(e)}"
            )

    @app.get(
        "/search/snippets",
        tags=[tags],
        openapi_extra={"x-cli-name": "search-snippets", "x-mcp-tool": True},
    )
    def search_snippets(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
        fields: Optional[str] = Query(
            "narrow",
            description=(
                "Field selection over each match. Same grammar as the "
                "list endpoint ('minimal' for uuid-only search "
                "results that cross-reference a loaded listing; omit "
                "or 'narrow' for the UI listing set — default; 'wide' "
                "for every persisted manifest field; 'full' for the "
                "complete object; CSV allowlist). Each match is a "
                "field-selected snippet dict with 'similarity_score' "
                "merged in."
            ),
        ),
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
            fields: Optional field-selection spec (see query-param description).

        Returns:
            list: Field-selected snippet dicts with ``similarity_score``
                merged in.

        Raises:
            HTTPException: 400 if ``fields`` is invalid, 503 if search is not
                available, 500 for other errors.
        """
        try:
            return service.search(
                search_term=search_term,
                max_number_of_results=max_number_of_results,
                similarity_threshold=similarity_threshold,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
                fields=fields,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error searching snippets: {str(e)}"
            )
