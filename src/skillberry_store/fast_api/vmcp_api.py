"""Virtual MCP Server API endpoints for the Skillberry Store service."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Annotated
from fastapi import FastAPI, HTTPException, Query, Request
from prometheus_client import Counter, Histogram

from skillberry_store.modules.object_handler import get_object_handler
from skillberry_store.modules.description import Description
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager
from skillberry_store.schemas.vmcp_schema import VmcpSchema
from skillberry_store.tools.configure import (
    get_skills_directory,
    get_snippets_directory,
    get_tools_directory,
    get_vmcp_directory,
)
from skillberry_store.utils.utils import (
    SKILLBERRY_CONTEXT,
    unflatten_keys,
    normalize_uuid,
    generate_or_validate_uuid,
)
from skillberry_store.fast_api.search_filters import apply_search_filters

logger = logging.getLogger(__name__)

# observability - metrics
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
):
    """Register virtual MCP server API endpoints with the FastAPI application.

    This uses a hybrid approach:
    - VmcpSchema for data persistence (JSON files)
    - VirtualMcpServerManager for runtime server management

    Args:
        app: The FastAPI application instance.
        sts_url: The base URL for the Skillberry Store service.
        tags: FastAPI tags for grouping the endpoints in documentation.
        vmcp_descriptions: Description instance for managing vmcp descriptions.
    """
    vmcp_handler = get_object_handler("vmcp")

    # Initialize the server manager for runtime management
    vmcp_server_manager = VirtualMcpServerManager(sts_url=sts_url, app=app)

    # Store in app state for cleanup access
    app.state.vmcp_server_manager = vmcp_server_manager

    @app.post(
        "/vmcp_servers/",
        tags=[tags],
        openapi_extra={"x-cli-name": "create-vmcp-server"},
    )
    def create_vmcp_server(vmcp: Annotated[VmcpSchema, Query()], request: Request):
        """Create a new virtual MCP server.

        Creates both the persistent JSON representation and starts the runtime server.

        Args:
            vmcp: The vmcp schema (auto-generated from VmcpSchema).
            request: The incoming request object for context extraction.

        Returns:
            dict: Success message with the vmcp server name, uuid, and port.

        Raises:
            HTTPException: If vmcp server already exists (409) or creation fails (500).
        """
        logger.info(f"Request to create vmcp server: {vmcp.name}")
        create_vmcp_counter.inc()

        # Generate or validate UUID
        vmcp.uuid = generate_or_validate_uuid(vmcp.uuid)
        logger.info(f"UUID for vmcp server '{vmcp.name}': {vmcp.uuid}")

        # Set timestamps
        current_time = datetime.now(timezone.utc).isoformat()
        vmcp.created_at = current_time
        vmcp.modified_at = current_time

        # Check if vmcp server with this UUID already exists
        if vmcp_handler.object_exists(vmcp.uuid):
            raise HTTPException(
                status_code=409,
                detail=f"VMCP server with UUID '{vmcp.uuid}' already exists.",
            )

        # Determine correct parent for this VMCP server becoming HEAD
        if vmcp.name:
            vmcp.parent = vmcp_handler.get_cache_parent_for_head(vmcp.uuid, vmcp.name)
            logger.info(
                f"Setting parent for VMCP server '{vmcp.name}' to {vmcp.parent}"
            )

        # Extract env_id from request headers
        headers = request.headers
        skillberry_context = unflatten_keys(dict(headers)).get(
            SKILLBERRY_CONTEXT.lower()
        )
        env_id = (
            skillberry_context.get("env_id") if skillberry_context is not None else ""
        )

        try:
            # Get tool and snippet UUIDs from the skill
            tool_uuids = []
            snippet_uuids = []
            print(f"DEBUG: vmcp.skill_uuid = {vmcp.skill_uuid}")
            if vmcp.skill_uuid:
                print(
                    f"DEBUG: Resolving tools and snippets for skill_uuid: {vmcp.skill_uuid}"
                )
                logger.info(
                    f"Resolving tools and snippets for skill_uuid: {vmcp.skill_uuid}"
                )
                # Load the skill to get tool UUIDs and snippet UUIDs
                skills_handler = get_object_handler("skill")

                try:
                    # Read skill dict by UUID
                    skill_dict = skills_handler.read_dict(vmcp.skill_uuid)
                    tool_uuids = skill_dict.get("tool_uuids", [])
                    snippet_uuids = skill_dict.get("snippet_uuids", [])
                    logger.info(
                        f"Found skill '{skill_dict.get('name')}' with {len(tool_uuids)} tool UUIDs and {len(snippet_uuids)} snippet UUIDs"
                    )
                except Exception as e:
                    logger.warning(f"Error loading skill {vmcp.skill_uuid}: {e}")

                if not tool_uuids and not snippet_uuids:
                    logger.warning(
                        f"No tools or snippets found for skill_uuid: {vmcp.skill_uuid}"
                    )

                logger.info(
                    f"Final tool_uuids list: {tool_uuids}, snippet_uuids list: {snippet_uuids}"
                )
            else:
                logger.info(
                    "No skill_uuid provided, creating VMCP server without tools or snippets"
                )

            # Start the runtime server using VirtualMcpServerManager with UUIDs
            # Manager will create composite name internally
            server = vmcp_server_manager.add_server(
                name=vmcp.name or "",
                uuid=vmcp.uuid or "",
                description=vmcp.description or "",
                port=vmcp.port if hasattr(vmcp, "port") and vmcp.port else None,
                tools=tool_uuids,  # Pass UUIDs, not names
                snippets=snippet_uuids,  # Pass UUIDs, not names
                env_id=env_id,
            )

            # Update the schema with the actual port assigned
            vmcp.port = server.port

            # Save the persistent JSON representation using ObjectHandler
            vmcp_handler.write_dict(vmcp.uuid, vmcp.to_dict())

            # Update cache after create
            if vmcp.name:
                vmcp_handler.update_cache(vmcp.uuid, new_name=vmcp.name)

            # Write description for search capability (indexed by UUID)
            if vmcp_descriptions and vmcp.description:
                vmcp_descriptions.write_description(vmcp.uuid, vmcp.description)
                logger.info(f"VMCP server description saved for UUID: {vmcp.uuid}")

            logger.info(
                f"VMCP server '{vmcp.name}' created successfully on port {server.port}"
            )
            return {
                "message": f"VMCP server '{vmcp.name}' created successfully.",
                "name": vmcp.name,
                "uuid": vmcp.uuid,
                "port": server.port,
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error creating vmcp server '{vmcp.name}': {e}")

            # Check if it's a port conflict error
            if "port" in error_msg.lower() and (
                "not available" in error_msg.lower()
                or "already in use" in error_msg.lower()
                or "in use" in error_msg.lower()
            ):
                raise HTTPException(
                    status_code=409, detail=f"Port conflict: {error_msg}"
                )

            raise HTTPException(
                status_code=500, detail=f"Error creating vmcp server: {error_msg}"
            )

    @app.get(
        "/vmcp_servers/", tags=[tags], openapi_extra={"x-cli-name": "list-vmcp-servers"}
    )
    def list_vmcp_servers():
        """List all virtual MCP servers.

        Returns both persistent and runtime information.

        Returns:
            dict: Dictionary containing a dict of virtual MCP servers with full details.

        Raises:
            HTTPException: If listing fails (500).
        """
        logger.info("Request to list vmcp servers")
        list_vmcp_counter.inc()

        try:
            # Get all VMCP objects using ObjectHandler
            vmcp_resources = vmcp_handler.list_all_dicts()

            # Build full server objects by combining persistent and runtime data
            servers_list = []
            for vmcp_data in vmcp_resources:
                server_name = vmcp_data.get("name")
                server_uuid = vmcp_data.get("uuid")
                try:
                    # Get runtime data (may be None if server not running)
                    # Manager will construct composite name internally
                    runtime_server = None
                    try:
                        runtime_server = vmcp_server_manager.get_server(
                            server_name or "", server_uuid or ""
                        )
                    except Exception:
                        pass  # Server not running, which is fine

                    # Combine persistent and runtime data
                    server_info = {
                        "uuid": vmcp_data.get("uuid"),
                        "name": vmcp_data.get("name"),
                        "description": vmcp_data.get("description"),
                        "version": vmcp_data.get("version"),
                        "state": vmcp_data.get("state"),
                        "tags": vmcp_data.get("tags", []),
                        "port": vmcp_data.get("port"),
                        "skill_uuid": vmcp_data.get("skill_uuid"),
                        "modified_at": vmcp_data.get("modified_at", ""),
                        "running": runtime_server is not None,
                        "runtime": (
                            {
                                "name": runtime_server.name if runtime_server else "",
                                "description": (
                                    runtime_server.description if runtime_server else ""
                                ),
                                "port": runtime_server.port if runtime_server else None,
                                "tools": (
                                    runtime_server.tool_uuids if runtime_server else []
                                ),
                            }
                            if runtime_server
                            else None
                        ),
                    }
                    servers_list.append(server_info)
                except Exception as e:
                    logger.warning(f"Error loading server {server_name}: {e}")

            # Sort by modified_at in descending order (most recent first)
            servers_list.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

            # Convert to dict with server UUIDs as keys to avoid duplications
            servers_dict = {server["uuid"]: server for server in servers_list}

            logger.info(f"Listed {len(servers_dict)} vmcp servers")
            return {"virtual_mcp_servers": servers_dict}
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
        """Get a specific virtual MCP server by UUID or name.

        Returns both persistent and runtime information.

        Args:
            uuid_or_name: The UUID or name of the vmcp server.

        Returns:
            dict: The vmcp server object with runtime details.

        Raises:
            HTTPException: If vmcp server not found (404) or retrieval fails (500).
        """
        logger.info(f"Request to get vmcp server: {uuid_or_name}")
        get_vmcp_counter.inc()

        try:
            # Resolve UUID or name to UUID and read manifest
            vmcp_uuid = vmcp_handler.resolve_to_uuid_or_error(uuid_or_name)
            vmcp_dict = vmcp_handler.read_dict(vmcp_uuid)
            server_name = vmcp_dict.get("name")
            server_uuid = vmcp_dict.get("uuid")

            # Get runtime details from manager
            try:
                runtime_details = vmcp_server_manager.get_server_details(
                    server_name or "", server_uuid or ""
                )
                vmcp_dict["runtime"] = runtime_details
                vmcp_dict["running"] = True
            except Exception:
                vmcp_dict["running"] = False
                vmcp_dict["runtime"] = None

            logger.info(f"Retrieved vmcp server: {uuid_or_name}")
            return vmcp_dict
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
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
        """Delete a virtual MCP server by UUID or name.

        Stops the runtime server and removes persistent data.

        Args:
            uuid_or_name: The UUID or name of the vmcp server to delete.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If vmcp server not found (404) or deletion fails (500).
        """
        logger.info(f"Request to delete vmcp server: {uuid_or_name}")
        delete_vmcp_counter.inc()

        try:
            # Resolve UUID or name to UUID and read dict
            server_uuid = vmcp_handler.resolve_to_uuid_or_error(uuid_or_name)
            vmcp_dict = vmcp_handler.read_dict(server_uuid)
            server_name = vmcp_dict.get("name")
            server_parent = vmcp_dict.get("parent")

            # Stop and remove the runtime server
            try:
                vmcp_server_manager.remove_server(server_name or "", server_uuid or "")
                logger.info(f"Stopped runtime server: {server_name}_{server_uuid}")
            except Exception as e:
                logger.warning(f"Could not stop runtime server: {e}")

            # Delete persistent data using ObjectHandler
            vmcp_handler.delete_object(server_uuid)

            # Update cache after delete
            if server_name and server_uuid:
                vmcp_handler.update_cache(
                    server_uuid,
                    new_name=None,
                    old_name=server_name,
                    old_parent=server_parent,
                )

            # Delete the description (indexed by UUID)
            if vmcp_descriptions:
                try:
                    vmcp_descriptions.delete_description(server_uuid or "")
                    logger.info(
                        f"VMCP server description deleted for UUID: {server_uuid}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not delete vmcp server description for UUID '{server_uuid}': {e}"
                    )

            logger.info(f"VMCP server '{uuid_or_name}' deleted successfully")
            return {"message": f"VMCP server '{uuid_or_name}' deleted successfully."}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException as e:
            raise
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
        """Update an existing virtual MCP server.

        Updates both persistent data and restarts the runtime server.

        Args:
            uuid_or_name: The UUID or name of the vmcp server to update.
            vmcp: The updated vmcp schema.
            request: The incoming request object for context extraction.

        Returns:
            dict: Success message with new port.

        Raises:
            HTTPException: If vmcp server not found (404) or update fails (500).
        """
        logger.info(f"Request to update vmcp server: {uuid_or_name}")
        update_vmcp_counter.inc()

        try:
            # Resolve UUID or name to UUID and read current data
            vmcp_uuid = vmcp_handler.resolve_to_uuid_or_error(uuid_or_name)
            existing_vmcp = vmcp_handler.read_dict(vmcp_uuid)
            old_name = existing_vmcp.get("name")
            old_parent = existing_vmcp.get("parent")
            server_uuid = existing_vmcp.get("uuid")

            # Update modified timestamp
            vmcp.modified_at = datetime.now(timezone.utc).isoformat()

            # Preserve UUID if not provided in update
            if not vmcp.uuid:
                vmcp.uuid = server_uuid

            # Determine new name and correct parent
            new_name = vmcp.name
            if new_name:
                # Determine correct parent for this VMCP server becoming HEAD
                vmcp.parent = vmcp_handler.get_cache_parent_for_head(
                    vmcp.uuid or "", new_name
                )
                logger.info(
                    f"Setting parent for VMCP server '{new_name}' to {vmcp.parent}"
                )

            # Extract env_id from request headers
            headers = request.headers
            skillberry_context = unflatten_keys(dict(headers)).get(
                SKILLBERRY_CONTEXT.lower()
            )
            env_id = (
                skillberry_context.get("env_id")
                if skillberry_context is not None
                else ""
            )

            # Stop the old runtime server
            try:
                vmcp_server_manager.remove_server(old_name or "", server_uuid or "")
                logger.info(f"Stopped old runtime server: {old_name}_{server_uuid}")
            except Exception as e:
                logger.warning(f"Could not stop old runtime server: {e}")

            # Get tool and snippet UUIDs from the skill
            tool_uuids = []
            snippet_uuids = []
            if vmcp.skill_uuid:
                skills_handler = get_object_handler("skill")

                try:
                    # Read skill dict by UUID
                    skill_dict = skills_handler.read_dict(vmcp.skill_uuid)
                    tool_uuids = skill_dict.get("tool_uuids", [])
                    snippet_uuids = skill_dict.get("snippet_uuids", [])
                    logger.info(
                        f"Found skill with {len(tool_uuids)} tool UUIDs and {len(snippet_uuids)} snippet UUIDs"
                    )
                except Exception as e:
                    logger.warning(f"Error loading skill {vmcp.skill_uuid}: {e}")

            # Start new runtime server with UUIDs
            server = vmcp_server_manager.add_server(
                name=vmcp.name or "",
                uuid=vmcp.uuid or "",
                description=vmcp.description or "",
                port=vmcp.port if hasattr(vmcp, "port") and vmcp.port else None,
                tools=tool_uuids,  # Pass UUIDs, not names
                snippets=snippet_uuids,  # Pass UUIDs, not names
                env_id=env_id,
            )

            # Update the schema with the actual port
            vmcp.port = server.port

            # Update persistent data using ObjectHandler
            vmcp_handler.write_dict(vmcp.uuid or "", vmcp.to_dict())

            # Update cache after update
            if vmcp.name and old_name:
                vmcp_handler.update_cache(
                    vmcp.uuid or "",
                    new_name=vmcp.name,
                    old_name=old_name,
                    old_parent=old_parent,
                )

            logger.info(
                f"VMCP server '{vmcp.name}' updated successfully on port {server.port}"
            )
            return {
                "message": f"VMCP server '{vmcp.name}' updated successfully.",
                "port": server.port,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating vmcp server '{id}': {e}")
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

        This endpoint allows starting a server that exists in persistent storage
        but is not currently running in the runtime manager.

        Args:
            uuid_or_name: The UUID or name of the vmcp server to start.
            request: The incoming request object for context extraction.

        Returns:
            dict: Success message with the server port.

        Raises:
            HTTPException: If vmcp server not found (404) or start fails (500).
        """
        logger.info(f"Request to start vmcp server: {uuid_or_name}")

        try:
            # Resolve UUID or name to UUID and read manifest
            vmcp_uuid = vmcp_handler.resolve_to_uuid_or_error(uuid_or_name)
            vmcp_data = vmcp_handler.read_dict(vmcp_uuid)
            server_name = vmcp_data.get("name", "")
            server_uuid = vmcp_data.get("uuid", "")

            # Check if server already running
            try:
                existing_server = vmcp_server_manager.get_server(
                    server_name, server_uuid
                )
                if existing_server:
                    return {
                        "message": f"VMCP server '{server_name}' is already running.",
                        "port": existing_server.port,
                    }
            except Exception:
                pass  # Server not running, proceed to start it

            # Extract env_id from request headers
            headers = request.headers
            skillberry_context = unflatten_keys(dict(headers)).get(
                SKILLBERRY_CONTEXT.lower()
            )
            env_id = (
                skillberry_context.get("env_id")
                if skillberry_context is not None
                else ""
            )

            # Get tool and snippet UUIDs from skill_uuid
            tool_uuids = []
            snippet_uuids = []
            skill_uuid = vmcp_data.get("skill_uuid")

            if skill_uuid:
                logger.info(
                    f"Resolving tools and snippets for skill_uuid: {skill_uuid}"
                )
                skills_handler = get_object_handler("skill")

                try:
                    # Read skill dict by UUID
                    skill_dict = skills_handler.read_dict(skill_uuid)
                    tool_uuids = skill_dict.get("tool_uuids", [])
                    snippet_uuids = skill_dict.get("snippet_uuids", [])
                    logger.info(
                        f"Found skill with {len(tool_uuids)} tool UUIDs and {len(snippet_uuids)} snippet UUIDs"
                    )
                except Exception as e:
                    logger.warning(f"Error loading skill {skill_uuid}: {e}")

            # Start the runtime server with UUIDs
            server = vmcp_server_manager.add_server(
                name=server_name,
                uuid=server_uuid,
                description=vmcp_data.get("description", ""),
                port=vmcp_data.get("port"),
                tools=tool_uuids,  # Pass UUIDs, not names
                snippets=snippet_uuids,  # Pass UUIDs, not names
                env_id=env_id,
            )

            logger.info(
                f"VMCP server '{server_name}' started successfully on port {server.port}"
            )
            return {
                "message": f"VMCP server '{server_name}' started successfully.",
                "port": server.port,
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error starting vmcp server '{id}': {e}")
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
        """Search for vmcp servers by description.

        Returns vmcp servers that are below the similarity threshold and match the filters.

        Args:
            search_term: Search term.
            max_number_of_results: Number of results to return.
            similarity_threshold: Threshold to be used.
            manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
            lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).

        Returns:
            list: A list of matched vmcp server names and similarity scores.
        """
        logger.info(
            f"Request to search vmcp server descriptions for term: {search_term}"
        )
        search_vmcp_counter.inc()

        if not vmcp_descriptions:
            raise HTTPException(
                status_code=503,
                detail="VMCP server search is not available - descriptions not initialized",
            )

        try:
            matched_entities = vmcp_descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )

            filtered_matched_entities = [
                matched_entity
                for matched_entity in matched_entities
                if float(matched_entity.get("similarity_score", 0))
                <= similarity_threshold
            ]

            # Get full vmcp server objects for filtering
            vmcp_servers_to_filter = []
            for matched_entity in filtered_matched_entities:
                # The filename in matched_entity is the UUID (since we index by UUID)
                vmcp_uuid = matched_entity.get("filename") or matched_entity.get("name")
                if not vmcp_uuid:
                    logger.warning(
                        f"Matched entity missing 'filename' or 'name' field: {matched_entity}"
                    )
                    continue
                try:
                    # Read dict by UUID
                    vmcp_dict = vmcp_handler.read_dict(vmcp_uuid)
                    vmcp_dict["similarity_score"] = matched_entity.get(
                        "similarity_score", 0.0
                    )
                    vmcp_servers_to_filter.append(vmcp_dict)
                except Exception as e:
                    logger.warning(
                        f"Could not load vmcp server {vmcp_uuid} for filtering: {e}"
                    )

            # Apply manifest and lifecycle filters
            filtered_vmcp_servers = apply_search_filters(
                vmcp_servers_to_filter,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )

            # Sort by modified_at in descending order (most recent first)
            filtered_vmcp_servers.sort(
                key=lambda x: x.get("modified_at", ""), reverse=True
            )

            # Return only filename and similarity_score (filename is the vmcp server name)
            result = [
                {
                    "filename": vmcp.get("name", ""),
                    "similarity_score": vmcp.get("similarity_score", 0.0),
                }
                for vmcp in filtered_vmcp_servers
                if vmcp.get("name")  # Only include if name exists
            ]

            logger.info(f"Found {len(result)} matching vmcp servers after filtering")
            return result
        except Exception as e:
            logger.error(f"Error searching vmcp servers: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error searching vmcp servers: {str(e)}"
            )
