"""Virtual MCP Server API endpoints for the Skillberry Store service."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from prometheus_client import Counter, Histogram

from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.vmcp_schema import VmcpSchema
from skillberry_store.fast_api.search_filters import apply_search_filters
from skillberry_store.utils.utils import SKILLBERRY_CONTEXT, unflatten_keys
from skillberry_store.services.vmcp_service import VmcpService

if TYPE_CHECKING:
    from skillberry_store.modules.description import Description

logger = logging.getLogger(__name__)

prom_prefix = "sts_fastapi_vmcp_"
create_vmcp_counter = Counter(
    f"{prom_prefix}create_vmcp_counter", "Count number of vmcp create operations"
)
list_vmcp_counter = Counter(
    f"{prom_prefix}list_vmcp_counter", "Count number of vmcp list operations"
)
get_vmcp_counter = Counter(
    f"{prom_prefix}get_vmcp_counter", "Count number of vmcp get operations"
)
delete_vmcp_counter = Counter(
    f"{prom_prefix}delete_vmcp_counter", "Count number of vmcp delete operations"
)
update_vmcp_counter = Counter(
    f"{prom_prefix}update_vmcp_counter", "Count number of vmcp update operations"
)
search_vmcp_counter = Counter(
    f"{prom_prefix}search_vmcp_counter", "Count number of vmcp search operations"
)
invoke_vmcp_tool_counter = Counter(
    f"{prom_prefix}invoke_vmcp_tool_counter",
    "Count number of vmcp tool invoke operations",
    ["server_name", "tool_name"],
)
invoke_successfully_vmcp_tool_counter = Counter(
    f"{prom_prefix}invoke_successfully_vmcp_tool_counter",
    "Count number of vmcp tool invoked successfully operations",
    ["server_name", "tool_name"],
)
invoke_successfully_vmcp_tool_latency = Histogram(
    f"{prom_prefix}invoke_successfully_vmcp_tool_latency",
    "Histogram of invoke vmcp tool successfully latencies",
    ["server_name", "tool_name"],
)


def register_vmcp_api(
    app: FastAPI,
    sts_url: str,
    tags: str = "vmcp_servers",
    vmcp_descriptions: Optional[Description] = None,
    service: Optional[VmcpService] = None,
):
    """Register all Virtual MCP Server API endpoints with the FastAPI application.

    This function sets up all REST API endpoints for managing virtual MCP servers,
    which expose skills as MCP-compatible servers.

    Args:
        app: The FastAPI application instance to register routes with.
        sts_url: The Skillberry Store URL for server communication.
        tags: OpenAPI tag for grouping these endpoints (default: "vmcp_servers").
        vmcp_descriptions: Optional Description instance for semantic search functionality.
        service: Optional VmcpService instance. If None, a new instance will be created.

    Returns:
        None. Endpoints are registered directly on the app instance.
    """
    if service is None:
        from skillberry_store.modules.object_handler import get_object_handler
        from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager

        service = VmcpService(
            get_object_handler("vmcp"),
            VirtualMcpServerManager(sts_url=sts_url, app=app),
            get_object_handler("skill"),
            vmcp_descriptions,
        )
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
        openapi_extra={"x-cli-name": "create-vmcp-server"},
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
        logger.info(f"Request to create vmcp server: {vmcp.name}")
        create_vmcp_counter.inc()
        try:
            result = service.create(vmcp.to_dict(), env_id=_extract_env_id(request))
            return {
                "message": f"VMCP server '{result['name']}' created successfully.",
                "name": result["name"],
                "uuid": result["uuid"],
                "port": result["port"],
            }
        except ValueError as e:
            error_msg = str(e)
            if "already exists" in error_msg:
                raise HTTPException(status_code=409, detail=error_msg)
            if "port" in error_msg.lower() and (
                "not available" in error_msg.lower()
                or "already in use" in error_msg.lower()
                or "in use" in error_msg.lower()
            ):
                raise HTTPException(
                    status_code=409, detail=f"Port conflict: {error_msg}"
                )
            raise HTTPException(status_code=500, detail=error_msg)
        except Exception as e:
            logger.error(f"Error creating vmcp server '{vmcp.name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating vmcp server: {str(e)}"
            )

    @app.get(
        "/vmcp_servers/", tags=[tags], openapi_extra={"x-cli-name": "list-vmcp-servers"}
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
        logger.info("Request to list vmcp servers")
        list_vmcp_counter.inc()
        try:
            result = service.list_all()
            if skill_uuid:
                servers = result["virtual_mcp_servers"]
                result = {
                    "virtual_mcp_servers": {
                        k: v
                        for k, v in servers.items()
                        if v.get("skill_uuid") == skill_uuid
                    }
                }
            return result
        except Exception as e:
            logger.error(f"Error listing vmcp servers: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing vmcp servers: {str(e)}"
            )

    @app.get(
        "/vmcp_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "get-vmcp-server"},
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
        logger.info(f"Request to get vmcp server: {uuid_or_name}")
        get_vmcp_counter.inc()
        try:
            return service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error retrieving vmcp server '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving vmcp server: {str(e)}"
            )

    @app.delete(
        "/vmcp_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "delete-vmcp-server"},
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
        logger.info(f"Request to delete vmcp server: {uuid_or_name}")
        delete_vmcp_counter.inc()
        try:
            service.delete(uuid_or_name)
            return {"message": f"VMCP server '{uuid_or_name}' deleted successfully."}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error deleting vmcp server '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting vmcp server: {str(e)}"
            )

    @app.put(
        "/vmcp_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "update-vmcp-server"},
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
        logger.info(f"Request to update vmcp server: {uuid_or_name}")
        update_vmcp_counter.inc()
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
            logger.error(f"Error updating vmcp server '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating vmcp server: {str(e)}"
            )

    @app.post(
        "/vmcp_servers/{uuid_or_name}/start",
        tags=[tags],
        openapi_extra={"x-cli-name": "start-vmcp-server"},
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
        logger.info(f"Request to start vmcp server: {uuid_or_name}")
        try:
            vmcp_uuid = service._resolve_uuid(uuid_or_name)
            vmcp_data = service.handler.read_dict(vmcp_uuid)
            server_name = vmcp_data.get("name", "")
            server_uuid = vmcp_data.get("uuid", "")
            try:
                existing = service.server_manager.get_server(server_name, server_uuid)
                if existing:
                    return {
                        "message": f"VMCP server '{server_name}' is already running.",
                        "port": existing.port,
                    }
            except Exception:
                pass
            env_id = _extract_env_id(request)
            tool_uuids, snippet_uuids = service._resolve_skill_uuids(
                vmcp_data.get("skill_uuid")
            )
            server = service.server_manager.add_server(
                name=server_name,
                uuid=server_uuid,
                description=vmcp_data.get("description", ""),
                port=vmcp_data.get("port"),
                tools=tool_uuids,
                snippets=snippet_uuids,
                env_id=env_id,
            )
            logger.info(f"VMCP server '{server_name}' started on port {server.port}")
            return {
                "message": f"VMCP server '{server_name}' started successfully.",
                "port": server.port,
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error starting vmcp server '{uuid_or_name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error starting vmcp server: {str(e)}"
            )

    @app.get(
        "/search/vmcp_servers",
        tags=[tags],
        openapi_extra={"x-cli-name": "search-vmcp-servers"},
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
        logger.info(f"Request to search vmcp servers for: {search_term}")
        search_vmcp_counter.inc()
        if not vmcp_descriptions:
            raise HTTPException(
                status_code=503, detail="VMCP server search is not available"
            )
        try:
            matched_entities = vmcp_descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )
            filtered = [
                m
                for m in matched_entities
                if float(m.get("similarity_score", 0)) <= similarity_threshold
            ]
            to_filter = []
            for m in filtered:
                vmcp_uuid = m.get("filename") or m.get("name")
                if not vmcp_uuid:
                    continue
                try:
                    d = service.handler.read_dict(vmcp_uuid)
                    d["similarity_score"] = m.get("similarity_score", 0.0)
                    to_filter.append(d)
                except Exception as exc:
                    logger.warning(f"Could not load vmcp '{vmcp_uuid}': {exc}")
            result_items = apply_search_filters(
                to_filter,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )
            result_items.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            return [
                {
                    "filename": s.get("name", ""),
                    "similarity_score": s.get("similarity_score", 0.0),
                }
                for s in result_items
                if s.get("name")
            ]
        except Exception as e:
            logger.error(f"Error searching vmcp servers: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error searching vmcp servers: {str(e)}"
            )
