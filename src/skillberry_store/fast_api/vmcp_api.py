"""Virtual MCP Server API endpoints for the Skillberry Store service."""

from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request

from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.vmcp_schema import VmcpSchema
from skillberry_store.utils.utils import SKILLBERRY_CONTEXT, unflatten_keys
from skillberry_store.services.exceptions import ObjectInUseError
from skillberry_store.services.vmcp_service import VmcpService


def register_vmcp_api(
    app: FastAPI,
    tags: str = "vmcp_servers",
    service: Optional[VmcpService] = None,
):
    """Register all Virtual MCP Server API endpoints with the FastAPI application.

    This function sets up all REST API endpoints for managing virtual MCP servers,
    which expose skills as MCP-compatible servers.

    Args:
        app: The FastAPI application instance to register routes with.
        tags: OpenAPI tag for grouping these endpoints (default: "vmcp_servers").
        service: Optional VmcpService instance. When ``None``, the singleton
            from :func:`skillberry_store.services.registry.get_service` is used.

    Returns:
        None. Endpoints are registered directly on the app instance.
    """
    if service is None:
        from skillberry_store.services.registry import get_service

        service = get_service("vmcp")
    assert service is not None  # narrowed for type checker
    app.state.vmcp_server_manager = service.server_manager

    def _extract_env_id(request: Request) -> str:
        """Extract environment ID from request headers.

        Args:
            request: FastAPI request object.

        Returns:
            str: Environment ID from Skillberry context header, or empty string if not present.
        """
        ctx = unflatten_keys(dict(request.headers)).get(SKILLBERRY_CONTEXT.lower())
        return ctx.get("env_id") if ctx else ""

    @app.post(
        "/vmcp_servers/",
        tags=[tags],
        openapi_extra={"x-cli-name": "create-vmcp-server", "x-mcp-tool": True},
    )
    def create_vmcp_server(vmcp: Annotated[VmcpSchema, Query()], request: Request):
        """Create a new virtual MCP server.

        Creates a virtual MCP server that exposes a skill's tools and snippets
        through the MCP protocol on a specified port.

        Args:
            vmcp: Virtual MCP server metadata conforming to VmcpSchema (name, skill_uuid, port, etc.).
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
            result = service.create(vmcp.to_dict(), env_id=_extract_env_id(request))
            return {
                "message": f"VMCP server '{result['name']}' created successfully.",
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
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error creating vmcp server: {str(e)}"
            )

    @app.get(
        "/facets/vmcp_servers",
        tags=[tags],
        openapi_extra={"x-cli-name": "vmcp-server-facets", "x-mcp-tool": True},
    )
    def vmcp_server_facets():
        """Return the unique tags / namespaces / states over all VMCP servers.

        Powers filter-picker widgets so callers can enumerate every
        available value without fetching every server.
        """
        try:
            return service.facets()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error computing vmcp server facets: {str(e)}",
            )

    @app.get(
        "/vmcp_servers/",
        tags=[tags],
        openapi_extra={"x-cli-name": "list-vmcp-servers", "x-mcp-tool": True},
    )
    def list_vmcp_servers(
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
        """List VMCP servers with optional filter / sort / paginate / project.

        Response shape: bare array when neither ``limit`` nor ``offset`` is
        set (a breaking change vs. the pre-Phase-2 ``{virtual_mcp_servers:
        {...}}`` wrapper); envelope ``{items, total, offset, limit}``
        otherwise. Runtime enrichment runs only on the current page.

        Raises:
            HTTPException: 400 if ``fields`` is invalid, 500 if listing fails.
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
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error listing vmcp servers: {str(e)}"
            )

    @app.get(
        "/vmcp_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "get-vmcp-server", "x-mcp-tool": True},
    )
    def get_vmcp_server(uuid_or_name: str):
        """Get metadata for a specific virtual MCP server by UUID or name.

        Retrieves the complete manifest/metadata for a virtual MCP server identified
        by either its UUID or its unique name.

        Args:
            uuid_or_name: The UUID or name of the virtual MCP server to retrieve.

        Returns:
            dict: Virtual MCP server metadata including name, uuid, skill_uuid, port, etc.

        Raises:
            HTTPException: 404 if server not found, 500 for other errors.
        """
        try:
            return service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error retrieving vmcp server: {str(e)}"
            )

    @app.delete(
        "/vmcp_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "delete-vmcp-server", "x-mcp-tool": True},
    )
    def delete_vmcp_server(uuid_or_name: str):
        """Delete a virtual MCP server from the store.

        Removes a virtual MCP server and stops it if running.

        Args:
            uuid_or_name: The UUID or name of the virtual MCP server to delete.

        Returns:
            dict: Success message confirming deletion.

        Raises:
            HTTPException: 404 if server not found, 500 for other errors.
        """
        try:
            service.delete(uuid_or_name)
            return {"message": f"VMCP server '{uuid_or_name}' deleted successfully."}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ObjectInUseError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error deleting vmcp server: {str(e)}"
            )

    @app.put(
        "/vmcp_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "update-vmcp-server", "x-mcp-tool": True},
    )
    def update_vmcp_server(
        uuid_or_name: str, vmcp: Annotated[VmcpSchema, Query()], request: Request
    ):
        """Update an existing virtual MCP server's metadata.

        Updates the manifest/metadata for an existing virtual MCP server. If the
        server is running, it will be restarted with the new configuration.

        Args:
            uuid_or_name: The UUID or name of the virtual MCP server to update.
            vmcp: Updated virtual MCP server metadata conforming to VmcpSchema.
            request: FastAPI request object for extracting environment context.

        Returns:
            dict: Success message with server name and port.

        Raises:
            HTTPException: 404 if server not found, 500 for other errors.
        """
        try:
            result = service.update(
                uuid_or_name, vmcp.to_dict(), env_id=_extract_env_id(request)
            )
            return {
                "message": f"VMCP server '{result.get('name')}' updated successfully.",
                "port": result["port"],
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error updating vmcp server: {str(e)}"
            )

    @app.post(
        "/vmcp_servers/{uuid_or_name}/start",
        tags=[tags],
        openapi_extra={"x-cli-name": "start-vmcp-server", "x-mcp-tool": True},
    )
    def start_vmcp_server(uuid_or_name: str, request: Request):
        """Start or restart a virtual MCP server.

        Starts a virtual MCP server process that exposes the associated skill's
        tools and snippets via the MCP protocol. If already running, returns
        the existing server information.

        Args:
            uuid_or_name: The UUID or name of the virtual MCP server to start.
            request: FastAPI request object for extracting environment context.

        Returns:
            dict: Success message with server name and port.

        Raises:
            HTTPException: 404 if server or skill not found, 500 for other errors.
        """
        try:
            server, already_running = service.start(
                uuid_or_name, env_id=_extract_env_id(request)
            )
            message = (
                f"VMCP server '{server.name}' is already running."
                if already_running
                else f"VMCP server '{server.name}' started successfully."
            )
            return {"message": message, "port": server.port}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error starting vmcp server: {str(e)}"
            )

    @app.get(
        "/search/vmcp_servers",
        tags=[tags],
        openapi_extra={"x-cli-name": "search-vmcp-servers", "x-mcp-tool": True},
    )
    def search_vmcp_servers(
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
        """Search for virtual MCP servers using semantic similarity.

        Args:
            search_term: Search term to find similar virtual MCP servers.
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
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error searching vmcp servers: {str(e)}"
            )
