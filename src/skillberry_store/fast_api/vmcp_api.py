"""Virtual MCP Server API endpoints for the Skillberry Store service."""

from __future__ import annotations

from typing import Annotated, Optional

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
        "/vmcp_servers/",
        tags=[tags],
        openapi_extra={"x-cli-name": "list-vmcp-servers", "x-mcp-tool": True},
    )
    def list_vmcp_servers(skill_uuid: Optional[str] = None):
        """List all virtual MCP servers in the store.

        Retrieves metadata for all virtual MCP servers, optionally filtered by skill UUID.

        Args:
            skill_uuid: Optional skill UUID to filter servers by.

        Returns:
            dict: Dictionary containing virtual_mcp_servers with server metadata.

        Raises:
            HTTPException: 500 if listing fails.
        """
        try:
            return service.list_all(skill_uuid=skill_uuid)
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
    ):
        """Search for virtual MCP servers using semantic similarity.

        Returns virtual MCP servers that are semantically similar to the search
        term and match the specified filters.

        Args:
            search_term: Search term to find similar virtual MCP servers.
            max_number_of_results: Maximum number of results to return (default: 5).
            similarity_threshold: Maximum similarity score threshold (default: 1, lower is more similar).
            manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
            lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).

        Returns:
            list: List of matched server names and similarity scores.

        Raises:
            HTTPException: 503 if search is not available, 500 for other errors.
        """
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
            raise HTTPException(
                status_code=500, detail=f"Error searching vmcp servers: {str(e)}"
            )
