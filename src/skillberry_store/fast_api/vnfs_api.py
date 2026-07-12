"""Virtual NFS Server API endpoints for the Skillberry Store service."""

from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request

from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.vnfs_schema import VnfsSchema
from skillberry_store.services.exceptions import ObjectInUseError
from skillberry_store.services.vnfs_service import VnfsService


def register_vnfs_api(
    app: FastAPI,
    tags: str = "vnfs_servers",
    service: Optional[VnfsService] = None,
):
    """Register all Virtual NFS Server API endpoints with the FastAPI application.

    This function sets up all REST API endpoints for managing virtual NFS servers,
    which expose snippets as network file system endpoints.

    Args:
        app: The FastAPI application instance to register routes with.
        tags: OpenAPI tag for grouping these endpoints (default: "vnfs_servers").
        service: Optional VnfsService instance. When ``None``, the singleton
            from :func:`skillberry_store.services.registry.get_service` is used.

    Returns:
        None. Endpoints are registered directly on the app instance.
    """
    if service is None:
        from skillberry_store.services.registry import get_service

        service = get_service("vnfs")
    assert service is not None  # narrowed for type checker
    app.state.vnfs_server_manager = service.server_manager

    @app.post(
        "/vnfs_servers/",
        tags=[tags],
        openapi_extra={"x-cli-name": "create-vnfs-server", "x-mcp-tool": True},
    )
    def create_vnfs_server(vnfs: Annotated[VnfsSchema, Query()], request: Request):
        """Create a new virtual NFS server.

        Creates a virtual NFS server that exposes snippets through a network
        file system interface on a specified port.

        Args:
            vnfs: Virtual NFS server metadata conforming to VnfsSchema (name, skill_uuid, port, etc.).
            request: FastAPI request object for extracting environment context.

        Returns:
            dict: Success message with server name, UUID, and assigned port.

        Raises:
            HTTPException: 409 if server already exists or port conflict, 500 for other errors.
        """
        from skillberry_store.services.exceptions import (
            ObjectAlreadyExistsError,
            PortConflictError,
        )

        try:
            result = service.create(vnfs.to_dict())
            return {
                "message": f"vNFS server '{result['name']}' created successfully.",
                "name": result["name"],
                "uuid": result["uuid"],
                "port": result["port"],
            }
        except ObjectAlreadyExistsError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except PortConflictError as e:
            raise HTTPException(status_code=409, detail=f"Port conflict: {e}")
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Error creating vNFS server: {exc}"
            )

    @app.get(
        "/facets/vnfs_servers",
        tags=[tags],
        openapi_extra={"x-cli-name": "vnfs-server-facets", "x-mcp-tool": True},
    )
    def vnfs_server_facets():
        """Return the unique tags / namespaces / states over all vNFS servers.

        Powers filter-picker widgets so callers can enumerate every
        available value without fetching every server.
        """
        try:
            return service.facets()
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Error computing vNFS server facets: {exc}",
            )

    @app.get(
        "/vnfs_servers/",
        tags=[tags],
        openapi_extra={"x-cli-name": "list-vnfs-servers", "x-mcp-tool": True},
    )
    def list_vnfs_servers(
        skill_uuid: Optional[str] = None,
        fields: Optional[str] = Query(
            None,
            description=(
                "Field projection. Omit for the full enriched shape. Use "
                "'list' for the slim list-view preset (persistent metadata "
                "+ runtime status), 'full' for every field, or a "
                "comma-separated allowlist."
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
                "envelope. Omit both for a bare array."
            ),
        ),
        offset: Optional[int] = Query(None, ge=0, description="Page offset."),
    ):
        """List vNFS servers with optional filter / sort / paginate / project.

        Response shape: bare array when neither ``limit`` nor ``offset`` is
        set (a breaking change vs. the pre-Phase-2 ``{virtual_nfs_servers:
        {...}}`` wrapper); envelope ``{items, total, offset, limit}``
        otherwise. Runtime enrichment runs only on the current page.
        """
        try:
            return service.list_all(
                skill_uuid=skill_uuid,
                fields=fields,
                search=search,
                tags=tags_filter,
                state=state,
                sort=sort,
                limit=limit,
                offset=offset,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Error listing vNFS servers: {exc}"
            )

    @app.get(
        "/vnfs_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "get-vnfs-server", "x-mcp-tool": True},
    )
    def get_vnfs_server(uuid_or_name: str):
        """Get metadata for a specific virtual NFS server by UUID or name.

        Retrieves the complete manifest/metadata for a virtual NFS server identified
        by either its UUID or its unique name.

        Args:
            uuid_or_name: The UUID or name of the virtual NFS server to retrieve.

        Returns:
            dict: Virtual NFS server metadata including name, uuid, skill_uuid, port, etc.

        Raises:
            HTTPException: 404 if server not found, 500 for other errors.
        """
        try:
            return service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Error retrieving vNFS server: {exc}"
            )

    @app.delete(
        "/vnfs_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "delete-vnfs-server", "x-mcp-tool": True},
    )
    def delete_vnfs_server(uuid_or_name: str):
        """Delete a virtual NFS server from the store.

        Removes a virtual NFS server and stops it if running.

        Args:
            uuid_or_name: The UUID or name of the virtual NFS server to delete.

        Returns:
            dict: Success message confirming deletion.

        Raises:
            HTTPException: 404 if server not found, 500 for other errors.
        """
        try:
            service.delete(uuid_or_name)
            return {"message": f"vNFS server '{uuid_or_name}' deleted successfully."}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ObjectInUseError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Error deleting vNFS server: {exc}"
            )

    @app.put(
        "/vnfs_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "update-vnfs-server", "x-mcp-tool": True},
    )
    def update_vnfs_server(
        uuid_or_name: str, vnfs: Annotated[VnfsSchema, Query()], request: Request
    ):
        """Update an existing virtual NFS server's metadata.

        Updates the manifest/metadata for an existing virtual NFS server. If the
        server is running, it will be restarted with the new configuration.

        Args:
            uuid_or_name: The UUID or name of the virtual NFS server to update.
            vnfs: Updated virtual NFS server metadata conforming to VnfsSchema.
            request: FastAPI request object for extracting environment context.

        Returns:
            dict: Success message with server name and port.

        Raises:
            HTTPException: 404 if server not found, 500 for other errors.
        """
        try:
            result = service.update(uuid_or_name, vnfs.to_dict())
            return {
                "message": f"vNFS server '{result.get('name')}' updated successfully.",
                "port": result["port"],
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Error updating vNFS server: {exc}"
            )

    @app.post(
        "/vnfs_servers/{uuid_or_name}/start",
        tags=[tags],
        openapi_extra={"x-cli-name": "start-vnfs-server", "x-mcp-tool": True},
    )
    def start_vnfs_server(uuid_or_name: str, request: Request):
        """Start or restart a virtual NFS server.

        Starts a virtual NFS server process that exposes the associated skill's
        snippets via a network file system interface. If already running, returns
        the existing server information.

        Args:
            uuid_or_name: The UUID or name of the virtual NFS server to start.
            request: FastAPI request object (kept for OpenAPI shape compatibility;
                ``VnfsService.start`` does not need request context).

        Returns:
            dict: Success message with server name and port.

        Raises:
            HTTPException: 404 if server or skill not found, 500 for other errors.
        """
        try:
            server, already_running = service.start(uuid_or_name)
            message = (
                f"vNFS server '{server.name}' is already running."
                if already_running
                else f"vNFS server '{server.name}' started successfully."
            )
            return {"message": message, "port": server.port}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Error starting vNFS server: {exc}"
            )

    @app.get(
        "/search/vnfs_servers",
        tags=[tags],
        openapi_extra={"x-cli-name": "search-vnfs-servers", "x-mcp-tool": True},
    )
    def search_vnfs_servers(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
        fields: Optional[str] = Query(
            None,
            description=(
                "Optional projection over each matched server. Omit for the "
                "legacy '{filename, similarity_score}' shape. Otherwise the "
                "same grammar as list projection applies."
            ),
        ),
    ):
        """Search for virtual NFS servers using semantic similarity.

        Args:
            search_term: Search term to find similar virtual NFS servers.
            max_number_of_results: Maximum number of results to return.
            similarity_threshold: Maximum similarity score threshold.
            manifest_filter: Manifest properties to filter.
            lifecycle_state: State to filter by.
            fields: Optional projection spec (see query-param description).

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
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Error searching vNFS servers: {exc}"
            )
