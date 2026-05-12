"""Tools API endpoints for the Skillberry Store service."""

import json
import logging
from io import BytesIO
import os
from starlette.responses import PlainTextResponse
import traceback
import uuid
from datetime import datetime, timezone
from typing import Optional, Type, TypeVar, Annotated, Dict, Any, List, Set, Tuple
from inspect import Parameter, Signature
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from prometheus_client import Counter, Histogram
import time

from skillberry_store.modules.resource_handler import ResourceHandler
from skillberry_store.modules.file_executor import FileExecutor, detect_tool_dependencies
from skillberry_store.modules.description import Description
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.tool_schema import (
    ToolSchema,
    ToolParamsSchema,
    ToolReturnsSchema,
)
from skillberry_store.schemas.manifest_schema import ManifestState
from skillberry_store.tools.configure import (
    is_auto_detect_dependencies_enabled,
    get_tools_directory,
    get_files_directory_path,
)
from skillberry_store.utils.utils import SKILLBERRY_CONTEXT, unflatten_keys
from skillberry_store.utils.python_utils import extract_docstring
from skillberry_store.fast_api.server_utils import (
    get_mcp_tools,
    mcp_json_converter,
    mcp_content,
    mcp_content_from_manifest,
)
from skillberry_store.fast_api.search_filters import apply_search_filters

logger = logging.getLogger(__name__)


def find_tool_dependencies(
    dependencies: List[str],
    tool_handler: ResourceHandler,
    tool_uuid: str
) -> Set[str]:
    """
    Recursively locate UUIDs of all dependencies of a given tool.
    
    Args:
        dependencies: List of current dependency tool UUIDs
        tool_handler: ResourceHandler for tools
        tool_uuid: UUID of the tool whose dependencies are found (for logging)
    
    Returns:
        - Set of UUIDs of all dependencies (transitive closure) of the given tool.
    """
    dependencies_uuids: Set[str] = set()

    if not dependencies:
        return dependencies_uuids

    logger.info(f"Scanning {len(dependencies)} dependencies for tool '{tool_uuid}'")
    
    for dep_uuid in dependencies:
        # Skip if already visited (avoid circular dependencies)
        if dep_uuid in dependencies_uuids:
            logger.debug(f"Skipping already found dependency: {dep_uuid}")
            continue

        dependencies_uuids.add(dep_uuid)

        dep_dict = tool_handler.read_manifest(dep_uuid)
            
        # Recursively load nested dependencies first
        nested_dependencies = dep_dict.get("dependencies", [])
        if nested_dependencies:
            logger.info(f"Finding dependencies for '{dep_uuid}'")
            nested_deps = find_tool_dependencies(
                dependencies=nested_dependencies,
                tool_handler=tool_handler,
                tool_uuid=dep_uuid
            )
            dependencies_uuids.update(nested_deps)

    return dependencies_uuids


# observability - metrics
prom_prefix = "sts_fastapi_tools_"
create_tool_counter = Counter(
    f"{prom_prefix}create_tool_counter", "Count number of tool create operations"
)
list_tools_counter = Counter(
    f"{prom_prefix}list_tools_counter", "Count number of tool list operations"
)
get_tool_counter = Counter(
    f"{prom_prefix}get_tool_counter", "Count number of tool get operations"
)
get_tool_module_counter = Counter(
    f"{prom_prefix}get_tool_module_counter",
    "Count number of tool module get operations",
)
delete_tool_counter = Counter(
    f"{prom_prefix}delete_tool_counter", "Count number of tool delete operations"
)
update_tool_counter = Counter(
    f"{prom_prefix}update_tool_counter", "Count number of tool update operations"
)
execute_tool_counter = Counter(
    f"{prom_prefix}execute_tool_counter",
    "Count number of tool execute operations",
    ["name"],
)
execute_successfully_tool_counter = Counter(
    f"{prom_prefix}execute_successfully_tool_counter",
    "Count number of tool executed successfully operations",
    ["name"],
)
execute_successfully_tool_latency = Histogram(
    f"{prom_prefix}execute_successfully_tool_latency",
    "Histogram of execute tool successfully latencies",
    ["name"],
)
search_tools_counter = Counter(
    f"{prom_prefix}search_tools_counter", "Count number of tool search operations"
)
add_tool_from_python_counter = Counter(
    f"{prom_prefix}add_tool_from_python_counter",
    "Count number of tool add from Python operations",
)


def register_tools_api(
    app: FastAPI, tags: str = "tools", tools_descriptions: Optional[Description] = None
):
    """Register tools API endpoints with the FastAPI application.

    Args:
        app: The FastAPI application instance.
        tags: FastAPI tags for grouping the endpoints in documentation.
        tools_descriptions: Description instance for managing tool descriptions.
    """
    tools_directory = get_tools_directory()
    tool_handler = ResourceHandler(tools_directory, "tool")

    @app.post("/tools/", tags=[tags])
    async def create_tool(
        tool: Annotated[ToolSchema, Query()],
        module: UploadFile = File(...),
    ) -> Dict[str, Any]:
        """Create a new tool with required file upload.

        The form fields are dynamically generated from ToolSchema.
        Any changes to ToolSchema will automatically reflect in this API.

        Args:
            tool: Tool schema with all fields (auto-generated from ToolSchema).
            module: Required file upload for the tool module (e.g., Python file).

        Returns:
            dict: Success message with the tool name and uuid.

        Raises:
            HTTPException: If tool already exists (409) or creation fails (500).
        """
        logger.info(f"Request to create tool: {tool.name}")
        create_tool_counter.inc()

        # Generate UUID if not provided
        if not tool.uuid:
            tool.uuid = str(uuid.uuid4())
            logger.info(f"Generated UUID for tool '{tool.name}': {tool.uuid}")

        # Set timestamps
        current_time = datetime.now(timezone.utc).isoformat()
        tool.created_at = current_time
        tool.modified_at = current_time

        # Check if tool with this UUID already exists
        tool_uuid_lower = tool.uuid.lower()
        if tool_handler.resource_exists(tool_uuid_lower):
            raise HTTPException(
                status_code=409, detail=f"Tool with UUID '{tool.uuid}' already exists."
            )

        try:
            # Save the module file to UUID sub-folder
            file_content = await module.read()
            module_filename = module.filename if module.filename else f"{tool.name}.py"

            # Write module file to tool's UUID sub-folder
            tool_handler.write_resource_file(tool.uuid.lower(), module_filename, file_content)
            tool.module_name = module_filename
            logger.info(f"Saved module file to UUID sub-folder: {module_filename}")

            # Auto-detect dependencies if not provided and auto-detection is enabled
            if not tool.dependencies and is_auto_detect_dependencies_enabled():
                try:
                    # Get list of available tools
                    available_tools = tool_handler.get_available_resource_names()
                    # Detect dependencies from code
                    detected_dep_names = detect_tool_dependencies(
                        file_content.decode('utf-8') if isinstance(file_content, bytes) else file_content,
                        tool.name,
                        available_tools,
                    )
                    if detected_dep_names:
                        detected_deps = [tool_handler.resolve_id(m) for m in detected_dep_names]
                        tool.dependencies = detected_deps
                        logger.info(
                            f"Auto-detected dependencies for '{tool.name}': {detected_deps}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to auto-detect dependencies: {e}")

            # Convert tool to JSON and save as tool.json in UUID folder
            tool_handler.write_manifest(tool.uuid.lower(), tool.to_dict())

            # Write description for search capability (indexed by UUID)
            if tools_descriptions and tool.description and tool.uuid:
                tools_descriptions.write_description(tool.uuid, tool.description)
                logger.info(f"Tool description saved for: {tool.name} (UUID: {tool.uuid})")

            logger.info(f"Tool '{tool.name}' created successfully with UUID {tool.uuid}")
            return {
                "message": f"Tool '{tool.name}' created successfully.",
                "name": tool.name,
                "uuid": tool.uuid,
                "module_name": tool.module_name,
            }
        except Exception as e:
            logger.error(f"Error creating tool '{tool.name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error creating tool: {str(e)}"
            )

    @app.get("/tools/", tags=[tags])
    def list_tools() -> List[Dict[str, Any]]:
        """List all tools.

        Returns:
            list: A list of all tool objects.

        Raises:
            HTTPException: If listing fails (500).
        """
        logger.info("Request to list tools")
        list_tools_counter.inc()

        try:
            # Use ResourceHandler to list all tools
            tools = tool_handler.list_all_resources()
            # Log all tools with their details
            logger.info(f"Listing {len(tools)} unordered tools")
            for tool in tools:
                logger.info(
                    f"Tool: name={tool.get('name')}, "
                    f"uuid={tool.get('uuid')}, "
                    f"created_at={tool.get('created_at')}, "
                    f"modified_at={tool.get('modified_at')}"
                )
            
            
            # Sort by modified_at in descending order (most recent first)
            tools.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

            logger.info(f"Listed {len(tools)} tools")
            return tools
        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(f"Error listing tools: {e}\n{error_traceback}")
            raise HTTPException(
                status_code=500, detail=f"Error listing tools: {str(e)}\n{error_traceback}"
            )

    @app.get("/tools/{id}", tags=[tags])
    def get_tool(id: str) -> Dict[str, Any]:
        """Get a specific tool by ID (name or UUID).

        Args:
            id: The ID of the tool (can be either name or UUID).

        Returns:
            dict: The tool object.

        Raises:
            HTTPException: If tool not found (404) or retrieval fails (500).
        """
        logger.info(f"Request to get tool: {id}")
        get_tool_counter.inc()

        try:
            # Use ResourceHandler to get tool by ID (handles ID resolution and 404 internally)
            tool_dict = tool_handler.get_resource_by_id(id)
            logger.info(f"Retrieved tool with ID '{id}'")
            return tool_dict
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving tool with ID '{id}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving tool: {str(e)}"
            )

    @app.get("/tools/{id}/module", tags=[tags], response_class=PlainTextResponse)
    async def get_tool_module(id: str) -> PlainTextResponse:
        """Get the module file content for a specific tool.

        Note: For MCP tools, this returns the generated function signature.
        For code tools, this returns the actual module file content.

        Args:
            id: The ID of the tool (can be either name or UUID).

        Returns:
            PlainTextResponse: The module file content as plain text.

        Raises:
            HTTPException: If tool not found (404), module not specified (404),
                          module file not found (404), or retrieval fails (500).
        """
        logger.info(f"Request to get module file for tool: {id}")
        get_tool_module_counter.inc()

        try:
            # Get the tool manifest using ResourceHandler
            tool_dict = tool_handler.get_resource_by_id(id)
            tool_uuid = tool_dict.get("uuid")
            
            if not tool_uuid:
                raise HTTPException(
                    status_code=500, detail=f"Tool with ID '{id}' has no UUID in manifest"
                )

            # Handle MCP packaging format
            if tool_dict.get("packaging_format") == "mcp":
                # Generate content from MCP tool
                tools = await get_mcp_tools(tool_dict)
                if not tools:
                    raise HTTPException(
                        status_code=404, detail=f"MCP tool with ID '{id}' not found."
                    )
                tool_mcp_dict = vars(tools[0])
                module_content = mcp_content(tool_mcp_dict)
                return PlainTextResponse(
                    content=module_content, media_type="text/plain"
                )

            # Handle code packaging format
            # Check if module_name exists
            module_name = tool_dict.get("module_name")
            if not module_name:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tool with ID '{id}' does not have a module file specified",
                )

            # Return the module file content from UUID sub-folder
            logger.info(f"Retrieving module file: {module_name}")
            module_content = tool_handler.read_resource_file(tool_uuid, module_name, raw_content=True)
            return PlainTextResponse(content=module_content, media_type="text/plain")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving module file for tool with ID '{id}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving module file: {str(e)}"
            )

    @app.delete("/tools/{id}", tags=[tags])
    def delete_tool(id: str) -> Dict:
        """Delete a tool by ID (name or UUID).

        Args:
            id: The ID of the tool to delete (can be either name or UUID).
                Also deletes the associated module file if it exists.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If tool not found (404) or deletion fails (500).
        """
        logger.info(f"Request to delete tool: {id}")
        delete_tool_counter.inc()

        try:
            # Resolve ID to UUID and read tool before deletion
            tool_uuid = None
            tool_name = None
            try:
                tool_uuid = tool_handler.resolve_id(id)
                if tool_uuid:
                    tool_dict = tool_handler.read_manifest(tool_uuid)
                    tool_name = tool_dict.get("name")
            except Exception as e:
                logger.warning(f"Could not read tool before deletion: {e}")

            # Delete the tool using ResourceHandler (deletes entire UUID subfolder)
            result = tool_handler.delete_resource_by_id(id)

            # Delete the description for the tool (indexed by UUID)
            if tools_descriptions and tool_uuid:
                try:
                    tools_descriptions.delete_description(tool_uuid)
                    logger.info(f"Tool description deleted for: {tool_name} (UUID: {tool_uuid})")
                except Exception as e:
                    logger.warning(
                        f"Could not delete tool description for UUID '{tool_uuid}': {e}"
                    )

            logger.info(f"Tool with ID '{id}' deleted successfully")
            return {"message": f"Tool with ID '{id}' deleted successfully."}
        except HTTPException as e:
            # Re-raise HTTPException (like 404) without modification
            raise
        except Exception as e:
            logger.error(f"Error deleting tool with ID '{id}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting tool: {str(e)}"
            )

    @app.put("/tools/{id}", tags=[tags])
    def update_tool(id: str, tool: ToolSchema) -> Dict:
        """Update an existing tool.

        Args:
            id: The ID of the tool to update (can be either name or UUID).
            tool: The updated tool schema.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If tool not found (404) or update fails (500).
        """
        logger.info(f"Request to update tool: {id}")
        update_tool_counter.inc()

        try:
            # Resolve ID to UUID and verify tool exists
            tool_uuid = tool_handler.resolve_id(id)
            if not tool_uuid:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tool with ID '{id}' not found"
                )

            # Read existing manifest to preserve uuid and created_at
            existing_manifest = tool_handler.read_manifest(tool_uuid)
            
            # Convert update data to dict
            update_data = tool.to_dict()
            
            # Merge: preserve uuid and created_at from existing, update modified_at
            merged_manifest = {**existing_manifest, **update_data}
            merged_manifest["uuid"] = existing_manifest.get("uuid", tool_uuid)
            merged_manifest["created_at"] = existing_manifest.get("created_at")
            merged_manifest["modified_at"] = datetime.now(timezone.utc).isoformat()

            # Write the merged manifest using ResourceHandler
            tool_handler.write_manifest(tool_uuid, merged_manifest)
            
            # Update description for search capability if description changed (indexed by UUID)
            if tools_descriptions and tool.description:
                old_description = existing_manifest.get("description")
                if old_description != tool.description:
                    try:
                        # Delete old description
                        tools_descriptions.delete_description(tool_uuid)
                    except Exception as e:
                        logger.warning(f"Failed to delete old description: {e}")
                    
                    # Write new description
                    tools_descriptions.write_description(tool_uuid, tool.description)
                    logger.info(f"Tool description updated for: {tool.name} (UUID: {tool_uuid})")
            
            logger.info(f"Tool with ID '{id}' (UUID: {tool_uuid}) updated successfully")
            return {"message": f"Tool with ID '{id}' updated successfully."}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating tool with ID '{id}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating tool: {str(e)}"
            )

    @app.post("/tools/{id}/execute", tags=[tags])
    async def execute_tool(
        id: str, request: Request, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """Execute a tool by ID (name or UUID) with the provided parameters.

        This endpoint mirrors the functionality of /manifests/execute/{uid} but works
        with tool IDs instead of manifest UIDs.

        Args:
            id: The ID of the tool to execute (can be either name or UUID).
            request: Represents an incoming fast api request object.
            parameters: Dictionary of key/value pairs to be passed to the tool execution (Optional).

        Returns:
            dict: Tool execution output.

        Raises:
            HTTPException: If tool not found (404) or execution fails (500).
        """
        logger.info(f"[execute_tool] Received execute tool: {id} with parameters: {parameters}")
        
        
        try:
            logger.info(f"[execute_tool] Reading tool manifest for: {id}")
            # Get tool manifest (raises 404 if not found)
            tool_dict = tool_handler.get_resource_by_id(id)
            tool_uuid = tool_dict.get("uuid")
            tool_name = tool_dict.get("name", id)
            
            execute_tool_counter.labels(name=tool_uuid).inc()
            start_time = time.time()

            logger.info(f"[execute_tool] START - Request to execute tool: {tool_uuid} with parameters: {parameters}")
            execute_tool_counter.labels(name=tool_uuid).inc()
            start_time = time.time()

            # Extract skillberry context from headers (similar to manifest execution)
            headers = request.headers
            logger.info(f"Request headers: {headers}")

            # Convert headers to dict for unflatten_keys
            headers_dict = dict(headers.items())
            skillberry_context = unflatten_keys(headers_dict).get(
                SKILLBERRY_CONTEXT.lower()
            )
            logger.info(f"Skillberry context: {skillberry_context}")

            env_id = (
                skillberry_context.get("env_id")
                if skillberry_context is not None
                else None
            )

            # Handle MCP packaging format
            if tool_dict.get("packaging_format") == "mcp":
                # Build the function stub from the stored manifest — no SSE round-trip needed
                # here. FileExecutor.execute_python_file_in_mcp_server opens its own connection
                # and will surface a clear error if the tool is absent on the MCP server.
                module_content = mcp_content_from_manifest(tool_dict)
            else:
                # Handle code packaging format
                # Check if module_name exists
                module_name = tool_dict.get("module_name")
                if not module_name:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Tool with ID '{id}' does not have a module file specified",
                    )

                # Get the module file content from resource folder
                if not tool_uuid:
                    raise HTTPException(status_code=500, detail="Tool UUID not found in manifest")
                module_content = tool_handler.read_resource_file(tool_uuid, module_name, raw_content=True)
                if not isinstance(module_content, str):
                    raise HTTPException(status_code=500, detail=f"Invalid module content type for tool with ID '{id}'")

            # Find tool dependencies if they exist
            tool_dependencies_uuids = find_tool_dependencies(
                dependencies=tool_dict.get("dependencies", []),
                tool_handler=tool_handler,
                tool_uuid=tool_uuid
            )

            dep_manifests = tool_handler.get_resources_by_ids(list(tool_dependencies_uuids))
            dep_files = [tool_handler.read_resource_file(m["uuid"], m["module_name"], raw_content=True) for m in dep_manifests]

            # Execute the tool using FileExecutor
            file_executor = FileExecutor(
                name=tool_name,
                file_content=module_content,
                file_manifest=tool_dict,
                dependent_file_contents=dep_files,
                dependent_tools_as_dict=dep_manifests,
            )

            # Ensure parameters is not None
            exec_parameters = parameters if parameters is not None else {}
            result = await file_executor.execute_file(
                parameters=exec_parameters, env_id=env_id
            )
            
            # Record successful execution metrics only if no error
            if not (isinstance(result, dict) and "error" in result):
                duration = time.time() - start_time
                execute_successfully_tool_counter.labels(name=tool_uuid).inc()
                execute_successfully_tool_latency.labels(name=tool_uuid).observe(duration)
                logger.info(f"Tool '{tool_name}' (UUID: {tool_uuid}) executed successfully with result: {result}")
            else:
                error_message = result.get('error', 'Unknown Error')
                logger.error(f"Tool '{tool_name}' (UUID: {tool_uuid}) execution failed with error: {error_message}")

                # Determine appropriate HTTP status code based on error message
                # Tool not found on MCP server -> 404
                # Connection/timeout/other MCP errors -> 500
                if "not found" in error_message.lower():
                    status_code = 404
                else:
                    status_code = 500

                raise HTTPException(status_code=status_code, detail=error_message)

            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error executing tool with ID '{id}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error executing tool: {str(e)}"
            )

    @app.get("/search/tools", tags=[tags])
    def search_tools(
        search_term: str,
        max_number_of_results: int = 5,
        similarity_threshold: float = 1,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ) -> List:
        """Return a list of tools that are similar to the given search term.

        Returns tools that are below the similarity threshold and match the filters.

        Args:
            search_term: Search term.
            max_number_of_results: Number of results to return.
            similarity_threshold: Threshold to be used.
            manifest_filter: Manifest properties to filter (e.g., "tags:python", "state:approved").
            lifecycle_state: State to filter by (e.g., LifecycleState.APPROVED).

        Returns:
            list: A list of matched tool names and similarity scores.
        """
        logger.info(f"Request to search tool descriptions for term: {search_term}")
        search_tools_counter.inc()

        if not tools_descriptions:
            raise HTTPException(
                status_code=503,
                detail="Tool search is not available - descriptions not initialized",
            )

        try:
            matched_entities = tools_descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )

            filtered_matched_entities = [
                matched_entity
                for matched_entity in matched_entities
                if float(matched_entity["similarity_score"]) <= similarity_threshold
            ]

            # Get full tool objects for filtering
            tools_to_filter = []
            for matched_entity in filtered_matched_entities:
                tool_name = matched_entity.get("filename") or matched_entity.get("name")
                if not tool_name:
                    logger.warning(
                        f"Matched entity missing 'filename' or 'name' field: {matched_entity}"
                    )
                    continue
                try:
                    # Get tool manifest by name (raises 404 if not found)
                    tool_dict = tool_handler.get_resource_by_id(tool_name)
                    tool_dict["similarity_score"] = matched_entity.get("similarity_score", 0.0)
                    tools_to_filter.append(tool_dict)
                except Exception as e:
                    logger.warning(
                        f"Could not load tool {tool_name} for filtering: {e}"
                    )

            # Apply manifest and lifecycle filters
            filtered_tools = apply_search_filters(
                tools_to_filter,
                manifest_filter=manifest_filter,
                lifecycle_state=lifecycle_state,
            )

            # Sort by modified_at in descending order (most recent first)
            filtered_tools.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

            # Return only filename and similarity_score (filename is the tool name)
            result = [
                {
                    "filename": tool.get("name", ""),
                    "similarity_score": tool.get("similarity_score", 0.0),
                }
                for tool in filtered_tools
                if tool.get("name")  # Only include if name exists
            ]

            logger.info(f"Found {len(result)} matching tools after filtering")
            return result
        except Exception as e:
            logger.error(f"Error searching tools: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error searching tools: {str(e)}"
            )

    @app.post("/tools/add", tags=[tags])
    async def add_tool_from_python(
        tool: UploadFile = File(...),
        selected_func: Optional[str] = None,
        update: bool = False,
    ) -> Dict[str, Any]:
        """Add a tool by automatically extracting parameters from Python code docstring.

        This endpoint uploads a Python file and automatically generates a tool manifest
        by parsing the function's docstring. The docstring must follow standard Python
        documentation conventions (Google, NumPy, or Sphinx style).

        Args:
            tool: The Python file to upload containing the function.
            selected_func: Optional name of the specific function to extract. If not provided,
                      the first function in the file will be used.
            update: Whether to update if a tool with the same name already exists.

        Returns:
            dict: Success message with the tool name, uuid, and module_name.

        Raises:
            HTTPException: If file is not Python (400), tool already exists (409),
                          or any other error occurs (500).
        """
        logger.info(f"Request to add tool from Python file: {tool.filename}")
        add_tool_from_python_counter.inc()

        # Validate that the uploaded file is a Python file
        if not tool.filename or not tool.filename.endswith(".py"):
            raise HTTPException(
                status_code=400,
                detail="Only Python (.py) files are supported. Please upload a valid Python file.",
            )

        try:
            tool_bytes = await tool.read()

            try:
                func_name, docstring_obj = extract_docstring(tool_bytes, selected_func)  # type: ignore
                logger.info(f"Extracted function '{func_name}' from uploaded file")
            except Exception as e:
                logger.error(f"Failed to extract docstring: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to parse Python code or extract docstring: {str(e)}. "
                    "Ensure the function has a properly formatted docstring with parameters.",
                )

            description = docstring_obj.short_description  # type: ignore
            if not description:
                raise HTTPException(
                    status_code=400,
                    detail="Function docstring must include a description.",
                )

            params_properties = {}
            required_params = []

            for param in docstring_obj.params:  # type: ignore
                params_properties[param.arg_name] = {
                    "type": param.type_name if param.type_name else "string",
                    "description": param.description if param.description else "",
                }
                required_params.append(param.arg_name)

            returns_schema = None
            if docstring_obj.returns:  # type: ignore
                returns_schema = ToolReturnsSchema(
                    type=docstring_obj.returns.type_name if docstring_obj.returns.type_name else None,  # type: ignore
                    description=docstring_obj.returns.description if docstring_obj.returns.description else None,  # type: ignore
                )

            # Check if tool with this name already exists
            existing_tool = tool_handler.lookup_by_name(func_name)
            
            # Auto-detect dependencies if enabled
            dependencies = None
            if is_auto_detect_dependencies_enabled():
                try:
                    available_tools = tool_handler.get_available_resource_names()
                    detected_deps = detect_tool_dependencies(
                        tool_bytes.decode('utf-8') if isinstance(tool_bytes, bytes) else tool_bytes,
                        func_name,
                        available_tools
                    )
                    if detected_deps:
                        dependencies = detected_deps
                        logger.info(f"Auto-detected dependencies for '{func_name}': {detected_deps}")
                except Exception as e:
                    logger.warning(f"Failed to auto-detect dependencies: {e}")
            
            if update and existing_tool:

                logger.info(f"Updating existing tool: {func_name}")
                
                # Use existing UUID for update
                tool_uuid = existing_tool.get("uuid", str(uuid.uuid4()))
                
                # Update the module file in UUID sub-folder (update_tool doesn't handle files)
                module_filename = tool.filename if tool.filename else f"{func_name}.py"
                tool_handler.write_resource_file(tool_uuid.lower(), module_filename, tool_bytes)
                logger.info(f"Updated module file in UUID sub-folder: {module_filename}")
                
                # Create the tool schema for update
                tool_schema = ToolSchema(
                    name=func_name,
                    uuid=tool_uuid,
                    description=description,
                    programming_language="python",
                    packaging_format="code",
                    module_name=module_filename,
                    version="0.0.1",
                    state=ManifestState.APPROVED,
                    params=ToolParamsSchema(
                        type="object",
                        properties=params_properties,
                        required=required_params,
                        optional=[],
                    ),
                    returns=returns_schema,
                    dependencies=dependencies,
                )
                
                # Delegate to update_tool to handle manifest merge and description update
                update_result = update_tool(tool_uuid, tool_schema)
                logger.info(f"Tool '{func_name}' updated successfully")
                
                return {
                    "message": f"Tool '{func_name}' created successfully.",
                    "name": func_name,
                    "uuid": tool_uuid,
                    "module_name": module_filename,
                    "parameters": params_properties,
                    "description": description,
                }
            else:
                # Generate new UUID for new tool
                tool_uuid = str(uuid.uuid4())
                logger.info(f"Generated UUID for tool '{func_name}': {tool_uuid}")

                # Create the tool schema for new tool
                tool_schema = ToolSchema(
                    name=func_name,
                    uuid=tool_uuid,
                    module_name=tool.filename if tool.filename else f"{func_name}.py",
                    description=description,
                    programming_language="python",
                    packaging_format="code",
                    version="0.0.1",
                    state=ManifestState.APPROVED,
                    params=ToolParamsSchema(
                        type="object",
                        properties=params_properties,
                        required=required_params,
                        optional=[],
                    ),
                    returns=returns_schema,
                    dependencies=dependencies,
                )

                # Delegate to create_tool to handle everything (file, manifest, description)
                create_response = await create_tool(
                    tool=tool_schema,
                    module=UploadFile(filename=tool.filename, file=BytesIO(tool_bytes)),
                )

                logger.info(f"Tool '{func_name}' added successfully with UUID {tool_uuid}")
                return {
                    **create_response,
                    "parameters": params_properties,
                    "description": description,
                }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding tool: {e}")
            raise HTTPException(status_code=500, detail=f"Error adding tool: {str(e)}")
