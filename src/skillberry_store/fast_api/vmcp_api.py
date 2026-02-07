"""Virtual MCP Server API endpoints for the Skillberry Store service."""

import json
import logging
import uuid
from typing import Optional, Annotated
from fastapi import FastAPI, HTTPException, Query, Request
from prometheus_client import Counter

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.description import Description
from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager
from skillberry_store.schemas.vmcp_schema import VmcpSchema
from skillberry_store.tools.configure import get_vmcp_directory
from skillberry_store.utils.utils import SKILLBERRY_CONTEXT, unflatten_keys

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
    vmcp_directory = get_vmcp_directory()
    vmcp_handler = FileHandler(vmcp_directory)
    
    # Initialize the server manager for runtime management
    vmcp_server_manager = VirtualMcpServerManager(sts_url=sts_url, app=app)

    @app.post("/vmcp_servers/", tags=[tags])
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

        # Generate UUID if not provided
        if not vmcp.uuid:
            vmcp.uuid = str(uuid.uuid4())
            logger.info(f"Generated UUID for vmcp server '{vmcp.name}': {vmcp.uuid}")

        # Check if vmcp server already exists
        existing_vmcp = vmcp_handler.list_files()
        vmcp_filename = f"{vmcp.name}.json"

        if vmcp_filename in existing_vmcp:
            raise HTTPException(
                status_code=409, detail=f"VMCP server '{vmcp.name}' already exists."
            )

        # Extract env_id from request headers
        headers = request.headers
        skillberry_context = unflatten_keys(dict(headers)).get(SKILLBERRY_CONTEXT.lower())
        env_id = (
            skillberry_context.get("env_id")
            if skillberry_context is not None
            else ""
        )

        try:
            # Extract tool names from the skill by resolving skill_uuid
            tool_names = []
            print(f"DEBUG: vmcp.skill_uuid = {vmcp.skill_uuid}")
            if vmcp.skill_uuid:
                print(f"DEBUG: Resolving tools for skill_uuid: {vmcp.skill_uuid}")
                logger.info(f"Resolving tools for skill_uuid: {vmcp.skill_uuid}")
                # Load the skill to get tool UUIDs
                from skillberry_store.tools.configure import get_skills_directory, get_tools_directory
                from skillberry_store.modules.file_handler import FileHandler
                
                skills_handler = FileHandler(get_skills_directory())
                tools_handler = FileHandler(get_tools_directory())
                
                # Find skill by UUID
                skill_tool_uuids = []
                skill_files = skills_handler.list_files()
                logger.info(f"Searching through {len(skill_files)} skill files")
                for filename in skill_files:
                    if filename.endswith(".json"):
                        try:
                            content = skills_handler.read_file(filename, raw_content=True)
                            if isinstance(content, str):
                                skill_dict = json.loads(content)
                                if skill_dict.get("uuid") == vmcp.skill_uuid:
                                    skill_tool_uuids = skill_dict.get("tool_uuids", [])
                                    logger.info(f"Found skill '{skill_dict.get('name')}' with {len(skill_tool_uuids)} tool UUIDs: {skill_tool_uuids}")
                                    break
                        except Exception as e:
                            logger.warning(f"Error reading skill file {filename}: {e}")
                
                if not skill_tool_uuids:
                    logger.warning(f"No tools found for skill_uuid: {vmcp.skill_uuid}")
                
                # Resolve tool UUIDs to tool names
                for tool_uuid in skill_tool_uuids:
                    for filename in tools_handler.list_files():
                        if filename.endswith(".json"):
                            try:
                                content = tools_handler.read_file(filename, raw_content=True)
                                if isinstance(content, str):
                                    tool_dict = json.loads(content)
                                    if tool_dict.get("uuid") == tool_uuid:
                                        tool_name = tool_dict.get("name")
                                        tool_names.append(tool_name)
                                        logger.info(f"Resolved tool UUID {tool_uuid} to name '{tool_name}'")
                                        break
                            except Exception as e:
                                logger.warning(f"Error reading tool file {filename}: {e}")
                
                logger.info(f"Final tool_names list: {tool_names}")
            else:
                logger.info("No skill_uuid provided, creating VMCP server without tools")

            # Start the runtime server using VirtualMcpServerManager
            server = vmcp_server_manager.add_server(
                name=vmcp.name,
                description=vmcp.description or "",
                port=vmcp.port if hasattr(vmcp, 'port') and vmcp.port else None,
                tools=tool_names,
                env_id=env_id,
            )

            # Update the schema with the actual port assigned
            vmcp.port = server.port

            # Save the persistent JSON representation
            vmcp_json = json.dumps(vmcp.to_dict(), indent=4)
            vmcp_handler.write_file_content(vmcp_filename, vmcp_json)

            # Write description for search capability
            if vmcp_descriptions and vmcp.description:
                vmcp_descriptions.write_description(vmcp.name, vmcp.description)
                logger.info(f"VMCP server description saved for: {vmcp.name}")

            logger.info(f"VMCP server '{vmcp.name}' created successfully on port {server.port}")
            return {
                "message": f"VMCP server '{vmcp.name}' created successfully.",
                "name": vmcp.name,
                "uuid": vmcp.uuid,
                "port": server.port,
            }
        except Exception as e:
            logger.error(f"Error creating vmcp server '{vmcp.name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating vmcp server: {str(e)}"
            )

    @app.get("/vmcp_servers/", tags=[tags])
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
            # Get all server names from runtime
            server_names = vmcp_server_manager.list_servers()
            
            # Build full server objects by combining persistent and runtime data
            servers_dict = {}
            for server_name in server_names:
                try:
                    # Read persistent data from JSON
                    content = vmcp_handler.read_file(f"{server_name}.json", raw_content=True)
                    if isinstance(content, str):
                        vmcp_data = json.loads(content)
                    else:
                        logger.warning(f"Unexpected content type for {server_name}.json")
                        continue
                    
                    # Get runtime data
                    runtime_server = vmcp_server_manager.get_server(server_name)
                    
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
                        "running": runtime_server is not None,
                        "runtime": {
                            "name": runtime_server.name if runtime_server else "",
                            "description": runtime_server.description if runtime_server else "",
                            "port": runtime_server.port if runtime_server else None,
                            "tools": runtime_server.tools if runtime_server else [],
                        } if runtime_server else None,
                    }
                    servers_dict[server_name] = server_info
                except Exception as e:
                    logger.warning(f"Error loading server {server_name}: {e}")
            
            logger.info(f"Listed {len(servers_dict)} vmcp servers")
            return {"virtual_mcp_servers": servers_dict}
        except Exception as e:
            logger.error(f"Error listing vmcp servers: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing vmcp servers: {str(e)}"
            )

    @app.get("/vmcp_servers/{name}", tags=[tags])
    def get_vmcp_server(name: str):
        """Get a specific virtual MCP server by name.

        Returns both persistent and runtime information.

        Args:
            name: The name of the vmcp server.

        Returns:
            dict: The vmcp server object with runtime details.

        Raises:
            HTTPException: If vmcp server not found (404) or retrieval fails (500).
        """
        logger.info(f"Request to get vmcp server: {name}")
        get_vmcp_counter.inc()

        try:
            # Get persistent data
            vmcp_filename = f"{name}.json"
            content = vmcp_handler.read_file(vmcp_filename, raw_content=True)
            if not isinstance(content, str):
                raise HTTPException(
                    status_code=500, detail=f"Invalid content type for vmcp server '{name}'"
                )
            vmcp_dict = json.loads(content)
            
            # Get runtime details from manager
            try:
                runtime_details = vmcp_server_manager.get_server_details(name)
                vmcp_dict["runtime"] = runtime_details
                vmcp_dict["running"] = True
            except Exception:
                vmcp_dict["running"] = False
                vmcp_dict["runtime"] = None
            
            logger.info(f"Retrieved vmcp server: {name}")
            return vmcp_dict
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving vmcp server '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving vmcp server: {str(e)}"
            )

    @app.delete("/vmcp_servers/{name}", tags=[tags])
    def delete_vmcp_server(name: str):
        """Delete a virtual MCP server by name.

        Stops the runtime server and removes persistent data.

        Args:
            name: The name of the vmcp server to delete.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If vmcp server not found (404) or deletion fails (500).
        """
        logger.info(f"Request to delete vmcp server: {name}")
        delete_vmcp_counter.inc()

        try:
            # Stop and remove the runtime server
            try:
                vmcp_server_manager.remove_server(name)
                logger.info(f"Stopped runtime server: {name}")
            except Exception as e:
                logger.warning(f"Could not stop runtime server '{name}': {e}")

            # Delete persistent data
            vmcp_filename = f"{name}.json"
            result = vmcp_handler.delete_file(vmcp_filename)

            # Delete the description
            if vmcp_descriptions:
                try:
                    vmcp_descriptions.delete_description(name)
                    logger.info(f"VMCP server description deleted for: {name}")
                except Exception as e:
                    logger.warning(
                        f"Could not delete vmcp server description for '{name}': {e}"
                    )

            logger.info(f"VMCP server '{name}' deleted successfully")
            return {"message": f"VMCP server '{name}' deleted successfully."}
        except HTTPException as e:
            raise
        except Exception as e:
            logger.error(f"Error deleting vmcp server '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting vmcp server: {str(e)}"
            )

    @app.put("/vmcp_servers/{name}", tags=[tags])
    def update_vmcp_server(name: str, vmcp: Annotated[VmcpSchema, Query()], request: Request):
        """Update an existing virtual MCP server.

        Updates both persistent data and restarts the runtime server.

        Args:
            name: The name of the vmcp server to update.
            vmcp: The updated vmcp schema.
            request: The incoming request object for context extraction.

        Returns:
            dict: Success message with new port.

        Raises:
            HTTPException: If vmcp server not found (404) or update fails (500).
        """
        logger.info(f"Request to update vmcp server: {name}")
        update_vmcp_counter.inc()

        try:
            vmcp_filename = f"{name}.json"

            # Check if vmcp server exists
            existing_vmcp = vmcp_handler.list_files()
            if vmcp_filename not in existing_vmcp:
                raise HTTPException(
                    status_code=404, detail=f"VMCP server '{name}' not found."
                )

            # Extract env_id from request headers
            headers = request.headers
            skillberry_context = unflatten_keys(dict(headers)).get(SKILLBERRY_CONTEXT.lower())
            env_id = (
                skillberry_context.get("env_id")
                if skillberry_context is not None
                else ""
            )

            # Stop the old runtime server
            try:
                vmcp_server_manager.remove_server(name)
                logger.info(f"Stopped old runtime server: {name}")
            except Exception as e:
                logger.warning(f"Could not stop old runtime server '{name}': {e}")

            # Extract tool names from the skill by resolving skill_uuid
            tool_names = []
            if vmcp.skill_uuid:
                # Load the skill to get tool UUIDs
                from skillberry_store.tools.configure import get_skills_directory, get_tools_directory
                from skillberry_store.modules.file_handler import FileHandler
                
                skills_handler = FileHandler(get_skills_directory())
                tools_handler = FileHandler(get_tools_directory())
                
                # Find skill by UUID
                skill_tool_uuids = []
                for filename in skills_handler.list_files():
                    if filename.endswith(".json"):
                        try:
                            content = skills_handler.read_file(filename, raw_content=True)
                            if isinstance(content, str):
                                skill_dict = json.loads(content)
                                if skill_dict.get("uuid") == vmcp.skill_uuid:
                                    skill_tool_uuids = skill_dict.get("tool_uuids", [])
                                    break
                        except Exception as e:
                            logger.warning(f"Error reading skill file {filename}: {e}")
                
                # Resolve tool UUIDs to tool names
                for tool_uuid in skill_tool_uuids:
                    for filename in tools_handler.list_files():
                        if filename.endswith(".json"):
                            try:
                                content = tools_handler.read_file(filename, raw_content=True)
                                if isinstance(content, str):
                                    tool_dict = json.loads(content)
                                    if tool_dict.get("uuid") == tool_uuid:
                                        tool_names.append(tool_dict.get("name"))
                                        break
                            except Exception as e:
                                logger.warning(f"Error reading tool file {filename}: {e}")

            # Start new runtime server
            server = vmcp_server_manager.add_server(
                name=vmcp.name,
                description=vmcp.description or "",
                port=vmcp.port if hasattr(vmcp, 'port') and vmcp.port else None,
                tools=tool_names,
                env_id=env_id,
            )

            # Update the schema with the actual port
            vmcp.port = server.port

            # Update persistent data
            vmcp_json = json.dumps(vmcp.to_dict(), indent=4)
            vmcp_handler.write_file_content(vmcp_filename, vmcp_json)
            
            logger.info(f"VMCP server '{name}' updated successfully on port {server.port}")
            return {
                "message": f"VMCP server '{name}' updated successfully.",
                "port": server.port,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating vmcp server '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating vmcp server: {str(e)}"
            )

    @app.get("/search/vmcp_servers", tags=[tags])
    def search_vmcp_servers(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
    ):
        """Search for vmcp servers by description.

        Args:
            search_term: Search term.
            max_number_of_results: Number of results to return.
            similarity_threshold: Threshold to be used.

        Returns:
            list: A list of matched vmcp server names and similarity scores.
        """
        logger.info(f"Request to search vmcp server descriptions for term: {search_term}")
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
                if matched_entity["similarity_score"] <= similarity_threshold
            ]

            logger.info(f"Found {len(filtered_matched_entities)} matching vmcp servers")
            return filtered_matched_entities
        except Exception as e:
            logger.error(f"Error searching vmcp servers: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error searching vmcp servers: {str(e)}"
            )