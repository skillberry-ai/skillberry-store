"""Virtual NFS Server API endpoints for the Skillberry Store service."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Annotated, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from prometheus_client import Counter

from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.vnfs_schema import VnfsSchema
from skillberry_store.fast_api.search_filters import apply_search_filters
from skillberry_store.services.vnfs_service import VnfsService

if TYPE_CHECKING:
    from skillberry_store.modules.description import Description

logger = logging.getLogger(__name__)

prom_prefix = "sts_fastapi_vnfs_"
create_vnfs_counter = Counter(f"{prom_prefix}create_counter", "vNFS create operations")
list_vnfs_counter = Counter(f"{prom_prefix}list_counter", "vNFS list operations")
get_vnfs_counter = Counter(f"{prom_prefix}get_counter", "vNFS get operations")
delete_vnfs_counter = Counter(f"{prom_prefix}delete_counter", "vNFS delete operations")
update_vnfs_counter = Counter(f"{prom_prefix}update_counter", "vNFS update operations")
search_vnfs_counter = Counter(f"{prom_prefix}search_counter", "vNFS search operations")


def register_vnfs_api(
    app: FastAPI,
    sts_url: str,
    tags: str = "vnfs_servers",
    vnfs_descriptions: Optional[Description] = None,
    service: Optional[VnfsService] = None,
):
    """Register all Virtual NFS Server API endpoints with the FastAPI application.

    This function sets up all REST API endpoints for managing virtual NFS servers,
    which expose snippets as network file system endpoints.

    Args:
        app: The FastAPI application instance to register routes with.
        sts_url: The Skillberry Store URL for server communication.
        tags: OpenAPI tag for grouping these endpoints (default: "vnfs_servers").
        vnfs_descriptions: Optional Description instance for semantic search functionality.
        service: Optional VnfsService instance. If None, a new instance will be created.

    Returns:
        None. Endpoints are registered directly on the app instance.
    """
    if service is None:
        from skillberry_store.modules.object_handler import get_object_handler
        from skillberry_store.modules.vnfs_server_manager import VirtualNfsServerManager

        service = VnfsService(
            get_object_handler("vnfs"),
            VirtualNfsServerManager(sts_url=sts_url, app=app),
            vnfs_descriptions,
        )
    app.state.vnfs_server_manager = service.server_manager

    @app.post(
        "/vnfs_servers/",
        tags=[tags],
        openapi_extra={"x-cli-name": "create-vnfs-server"},
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
        logger.info(f"Request to create vnfs server: {vnfs.name}")
        create_vnfs_counter.inc()
        try:
            result = service.create(vnfs.to_dict())
            return {
                "message": f"vNFS server '{result['name']}' created successfully.",
                "name": result["name"],
                "uuid": result["uuid"],
                "port": result["port"],
            }
        except ValueError as e:
            status = (
                409 if "already exists" in str(e) or "not available" in str(e) else 500
            )
            raise HTTPException(status_code=status, detail=str(e))
        except Exception as exc:
            logger.error(f"Error creating vnfs server '{vnfs.name}': {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error creating vNFS server: {exc}"
            )

    @app.get(
        "/vnfs_servers/", tags=[tags], openapi_extra={"x-cli-name": "list-vnfs-servers"}
    )
    def list_vnfs_servers(skill_uuid: Optional[str] = None):
        """List all virtual NFS servers in the store.

        Retrieves metadata for all virtual NFS servers, optionally filtered by skill UUID.

        Args:
            skill_uuid: Optional skill UUID to filter servers by.

        Returns:
            dict: Dictionary containing virtual_nfs_servers with server metadata.

        Raises:
            HTTPException: 500 if listing fails.
        """
        logger.info("Request to list vnfs servers")
        list_vnfs_counter.inc()
        try:
            result = service.list_all()
            if skill_uuid:
                servers = result["virtual_nfs_servers"]
                result = {
                    "virtual_nfs_servers": {
                        k: v
                        for k, v in servers.items()
                        if v.get("skill_uuid") == skill_uuid
                    }
                }
            return result
        except Exception as exc:
            logger.error(f"Error listing vnfs servers: {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error listing vNFS servers: {exc}"
            )

    @app.get(
        "/vnfs_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "get-vnfs-server"},
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
        logger.info(f"Request to get vnfs server: {uuid_or_name}")
        get_vnfs_counter.inc()
        try:
            return service.get(uuid_or_name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as exc:
            logger.error(f"Error retrieving vnfs server '{uuid_or_name}': {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving vNFS server: {exc}"
            )

    @app.delete(
        "/vnfs_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "delete-vnfs-server"},
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
        logger.info(f"Request to delete vnfs server: {uuid_or_name}")
        delete_vnfs_counter.inc()
        try:
            service.delete(uuid_or_name)
            return {"message": f"vNFS server '{uuid_or_name}' deleted successfully."}
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as exc:
            logger.error(f"Error deleting vnfs server '{uuid_or_name}': {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting vNFS server: {exc}"
            )

    @app.put(
        "/vnfs_servers/{uuid_or_name}",
        tags=[tags],
        openapi_extra={"x-cli-name": "update-vnfs-server"},
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
        logger.info(f"Request to update vnfs server: {uuid_or_name}")
        update_vnfs_counter.inc()
        try:
            result = service.update(uuid_or_name, vnfs.to_dict())
            return {
                "message": f"vNFS server '{result.get('name')}' updated successfully.",
                "port": result["port"],
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as exc:
            logger.error(f"Error updating vnfs server '{uuid_or_name}': {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error updating vNFS server: {exc}"
            )

    @app.post(
        "/vnfs_servers/{uuid_or_name}/start",
        tags=[tags],
        openapi_extra={"x-cli-name": "start-vnfs-server"},
    )
    def start_vnfs_server(uuid_or_name: str, request: Request):
        """Start or restart a virtual NFS server.

        Starts a virtual NFS server process that exposes the associated skill's
        snippets via a network file system interface. If already running, returns
        the existing server information.

        Args:
            uuid_or_name: The UUID or name of the virtual NFS server to start.
            request: FastAPI request object for extracting environment context.

        Returns:
            dict: Success message with server name and port.

        Raises:
            HTTPException: 404 if server or skill not found, 500 for other errors.
        """
        logger.info(f"Request to start vnfs server: {uuid_or_name}")
        try:
            vnfs_data = service.handler.read_dict(service._resolve_uuid(uuid_or_name))
            server_name = vnfs_data.get("name", "")
            server_uuid = vnfs_data.get("uuid", "")
            try:
                existing = service.server_manager.get_server(server_name, server_uuid)
                if existing and existing.running:
                    return {
                        "message": f"vNFS server '{server_name}' is already running.",
                        "port": existing.port,
                    }
            except Exception:
                pass
            schema = VnfsSchema.from_dict(vnfs_data)
            server = service.server_manager.add_server(schema)
            logger.info(f"vNFS server '{server_name}' started on port {server.port}")
            return {
                "message": f"vNFS server '{server_name}' started successfully.",
                "port": server.port,
            }
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error starting vnfs server '{uuid_or_name}': {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error starting vNFS server: {exc}"
            )

    @app.get(
        "/search/vnfs_servers",
        tags=[tags],
        openapi_extra={"x-cli-name": "search-vnfs-servers"},
    )
    def search_vnfs_servers(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ):
        """Search for virtual NFS servers using semantic similarity.

        Returns virtual NFS servers that are semantically similar to the search
        term and match the specified filters.

        Args:
            search_term: Search term to find similar virtual NFS servers.
            max_number_of_results: Maximum number of results to return (default: 5).
            similarity_threshold: Maximum similarity score threshold (default: 1, lower is more similar).
            manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
            lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).

        Returns:
            list: List of matched server names and similarity scores.

        Raises:
            HTTPException: 503 if search is not available, 500 for other errors.
        """
        logger.info(f"Request to search vnfs servers for: {search_term}")
        search_vnfs_counter.inc()
        if not vnfs_descriptions:
            raise HTTPException(
                status_code=503, detail="vNFS server search is not available"
            )
        try:
            matched = vnfs_descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )
            filtered = [
                m
                for m in matched
                if float(m["similarity_score"]) <= similarity_threshold
            ]
            to_filter = []
            for m in filtered:
                vnfs_uuid = m.get("filename") or m.get("name")
                if not vnfs_uuid:
                    continue
                try:
                    d = service.handler.read_dict(vnfs_uuid)
                    d["similarity_score"] = m.get("similarity_score", 0.0)
                    to_filter.append(d)
                except Exception as exc:
                    logger.warning(f"Could not load vnfs '{vnfs_uuid}': {exc}")
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
        except Exception as exc:
            logger.error(f"Error searching vnfs servers: {exc}")
            raise HTTPException(
                status_code=500, detail=f"Error searching vNFS servers: {exc}"
            )
