"""Tools API endpoints for the Skillberry Store service."""

import json
import logging
from starlette.responses import PlainTextResponse
import uuid
from datetime import datetime, timezone
from typing import Optional, Type, TypeVar, Annotated, Dict, Any, List
from inspect import Parameter, Signature
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from prometheus_client import Counter, Histogram
import time

from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.file_executor import FileExecutor, detect_tool_dependencies
from skillberry_store.modules.description import Description
from skillberry_store.modules.lifecycle import LifecycleState
from skillberry_store.schemas.tool_schema import ToolSchema, ToolParamsSchema, ToolReturnsSchema
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


def load_tool_dependencies(
    dependencies: List[str],
    tool_handler: FileHandler,
    file_handler: FileHandler,
    tool_name: str,
    visited: Optional[set] = None
) -> tuple[List[str], List[Dict[str, Any]]]:
    """
    Recursively load dependency file contents and manifests for a tool and all its nested dependencies.
    
    Args:
        dependencies: List of dependency tool names
        tool_handler: FileHandler for tool manifests
        file_handler: FileHandler for module files
        tool_name: Name of the tool requesting dependencies (for logging)
        visited: Set of already visited dependency names to avoid circular dependencies
    
    Returns:
        Tuple of:
        - List of dependency file contents as strings (in dependency order)
        - List of dependency manifests as dictionaries (in dependency order)
    """
    if visited is None:
        visited = set()
    
    dependent_file_contents = []
    dependent_tools_as_dict = []
    
    if not dependencies:
        return dependent_file_contents, dependent_tools_as_dict
    
    logger.info(f"Loading {len(dependencies)} dependencies for tool '{tool_name}'")
    
    for dep_name in dependencies:
        # Skip if already visited (avoid circular dependencies)
        if dep_name in visited:
            logger.debug(f"Skipping already loaded dependency: {dep_name}")
            continue
        
        visited.add(dep_name)
        
        try:
            # Load dependency tool manifest
            dep_filename = f"{dep_name}.json"
            dep_content = tool_handler.read_file(dep_filename, raw_content=True)
            if isinstance(dep_content, str):
                dep_dict = json.loads(dep_content)
                
                # Recursively load nested dependencies first
                nested_dependencies = dep_dict.get("dependencies", [])
                if nested_dependencies:
                    logger.info(f"Loading nested dependencies for '{dep_name}'")
                    nested_contents, nested_dicts = load_tool_dependencies(
                        dependencies=nested_dependencies,
                        tool_handler=tool_handler,
                        file_handler=file_handler,
                        tool_name=dep_name,
                        visited=visited
                    )
                    dependent_file_contents.extend(nested_contents)
                    dependent_tools_as_dict.extend(nested_dicts)
                
                # Load dependency module content
                dep_module_name = dep_dict.get("module_name")
                if dep_module_name:
                    dep_module_content = file_handler.read_file(dep_module_name, raw_content=True)
                    if isinstance(dep_module_content, str):
                        dependent_file_contents.append(dep_module_content)
                        dependent_tools_as_dict.append(dep_dict)
                        logger.info(f"Loaded dependency: {dep_name}")
                    else:
                        logger.warning(f"Could not load module content for dependency: {dep_name}")
                else:
                    logger.warning(f"Dependency {dep_name} has no module_name")
            else:
                logger.warning(f"Could not load dependency manifest: {dep_name}")
        except Exception as e:
            logger.warning(f"Failed to load dependency {dep_name}: {e}")
    
    return dependent_file_contents, dependent_tools_as_dict

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
    f"{prom_prefix}get_tool_module_counter", "Count number of tool module get operations"
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
    f"{prom_prefix}add_tool_from_python_counter", "Count number of tool add from Python operations"
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
    tool_handler = FileHandler(tools_directory)

    # File handler for storing tool module files
    files_directory = get_files_directory_path()
    file_handler = FileHandler(files_directory)

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

        # Check if tool already exists
        existing_tools = tool_handler.list_files()
        tool_filename = f"{tool.name}.json"

        if tool_filename in existing_tools:
            raise HTTPException(
                status_code=409, detail=f"Tool '{tool.name}' already exists."
            )

        try:
            # Save the module file and automatically set module_name from the uploaded filename
            file_content = await module.read()
            module_filename = module.filename if module.filename else f"{tool.name}.py"

            file_handler.write_file(file_content, filename=module_filename)
            tool.module_name = module_filename
            logger.info(f"Saved module file: {module_filename}")

            # Auto-detect dependencies if not provided and auto-detection is enabled
            if not tool.dependencies and is_auto_detect_dependencies_enabled():
                try:
                    # Get list of available tools
                    available_tools = [f.replace('.json', '') for f in tool_handler.list_files()]
                    # Detect dependencies from code
                    detected_deps = detect_tool_dependencies(
                        file_content.decode('utf-8') if isinstance(file_content, bytes) else file_content,
                        tool.name,
                        available_tools
                    )
                    if detected_deps:
                        tool.dependencies = detected_deps
                        logger.info(f"Auto-detected dependencies for '{tool.name}': {detected_deps}")
                except Exception as e:
                    logger.warning(f"Failed to auto-detect dependencies: {e}")

            # Convert tool to JSON and save
            tool_json = json.dumps(tool.to_dict(), indent=4)
            tool_handler.write_file_content(tool_filename, tool_json)

            # Write description for search capability
            if tools_descriptions and tool.description:
                tools_descriptions.write_description(tool.name, tool.description)
                logger.info(f"Tool description saved for: {tool.name}")

            logger.info(f"Tool '{tool.name}' created successfully")
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
            tool_files = tool_handler.list_files()
            tools = []

            for filename in tool_files:
                if filename.endswith(".json"):
                    content = tool_handler.read_file(filename, raw_content=True)
                    if isinstance(content, str):
                        tool_dict = json.loads(content)
                    else:
                        continue
                    tools.append(tool_dict)

            # Sort by modified_at in descending order (most recent first)
            tools.sort(key=lambda x: x.get("modified_at", ""), reverse=True)

            logger.info(f"Listed {len(tools)} tools")
            return tools
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing tools: {str(e)}"
            )

    @app.get("/tools/{name}", tags=[tags])
    def get_tool(name: str) -> Dict[str, Any]:
        """Get a specific tool by name.

        Args:
            name: The name of the tool.

        Returns:
            dict: The tool object.

        Raises:
            HTTPException: If tool not found (404) or retrieval fails (500).
        """
        logger.info(f"Request to get tool: {name}")
        get_tool_counter.inc()

        try:
            tool_filename = f"{name}.json"
            content = tool_handler.read_file(tool_filename, raw_content=True)
            if not isinstance(content, str):
                raise HTTPException(
                    status_code=500, detail=f"Invalid content type for tool '{name}'"
                )
            tool_dict = json.loads(content)
            logger.info(f"Retrieved tool: {name}")
            return tool_dict
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving tool '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving tool: {str(e)}"
            )

    @app.get("/tools/{name}/module", tags=[tags], response_class=PlainTextResponse)
    async def get_tool_module(name: str) -> PlainTextResponse:
        """Get the module file content for a specific tool.

        Note: For MCP tools, this returns the generated function signature.
        For code tools, this returns the actual module file content.

        Args:
            name: The name of the tool.

        Returns:
            PlainTextResponse: The module file content as plain text.

        Raises:
            HTTPException: If tool not found (404), module not specified (404),
                          module file not found (404), or retrieval fails (500).
        """
        logger.info(f"Request to get module file for tool: {name}")
        get_tool_module_counter.inc()

        try:
            # First, get the tool to find the module_name
            tool_filename = f"{name}.json"
            content = tool_handler.read_file(tool_filename, raw_content=True)
            if not isinstance(content, str):
                raise HTTPException(
                    status_code=500, detail=f"Invalid content type for tool '{name}'"
                )
            tool_dict = json.loads(content)

            # Handle MCP packaging format
            if tool_dict.get("packaging_format") == "mcp":
                # Generate content from MCP tool
                tools = await get_mcp_tools(tool_dict)
                if not tools:
                    raise HTTPException(
                        status_code=404, detail=f"MCP tool '{name}' not found."
                    )
                tool_mcp_dict = vars(tools[0])
                module_content = mcp_content(tool_mcp_dict)
                return PlainTextResponse(content=module_content, media_type="text/plain")
            
            # Handle code packaging format
            # Check if module_name exists
            module_name = tool_dict.get("module_name")
            if not module_name:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tool '{name}' does not have a module file specified",
                )

            # Return the module file content as plain text
            logger.info(f"Retrieving module file: {module_name}")
            module_content = file_handler.read_file(module_name, raw_content=True)
            return PlainTextResponse(content=module_content, media_type="text/plain")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving module file for tool '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error retrieving module file: {str(e)}"
            )

    @app.delete("/tools/{name}", tags=[tags])
    def delete_tool(name: str) -> Dict:
        """Delete a tool by name.

        Args:
            name: The name of the tool to delete.
                  Also deletes the associated module file if it exists.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If tool not found (404) or deletion fails (500).
        """
        logger.info(f"Request to delete tool: {name}")
        delete_tool_counter.inc()

        try:
            tool_filename = f"{name}.json"

            # Read tool to get module_name before deletion
            try:
                content = tool_handler.read_file(tool_filename, raw_content=True)
                if isinstance(content, str):
                    tool_dict = json.loads(content)
                    module_name = tool_dict.get("module_name")

                    # Delete the module file if it exists
                    if module_name:
                        try:
                            file_handler.delete_file(module_name)
                            logger.info(f"Deleted module file: {module_name}")
                        except Exception as e:
                            logger.warning(
                                f"Could not delete module file '{module_name}': {e}"
                            )
            except Exception as e:
                logger.warning(f"Could not read tool before deletion: {e}")

            # Delete the tool JSON file
            result = tool_handler.delete_file(tool_filename)

            # Delete the description for the tool
            if tools_descriptions:
                try:
                    tools_descriptions.delete_description(name)
                    logger.info(f"Tool description deleted for: {name}")
                except Exception as e:
                    logger.warning(
                        f"Could not delete tool description for '{name}': {e}"
                    )

            logger.info(f"Tool '{name}' deleted successfully")
            return {"message": f"Tool '{name}' deleted successfully."}
        except HTTPException as e:
            # Re-raise HTTPException (like 404) without modification
            raise
        except Exception as e:
            logger.error(f"Error deleting tool '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting tool: {str(e)}"
            )

    @app.put("/tools/{name}", tags=[tags])
    def update_tool(name: str, tool: ToolSchema) -> Dict:
        """Update an existing tool.

        Args:
            name: The name of the tool to update.
            tool: The updated tool schema.

        Returns:
            dict: Success message.

        Raises:
            HTTPException: If tool not found (404) or update fails (500).
        """
        logger.info(f"Request to update tool: {name}")
        update_tool_counter.inc()

        try:
            tool_filename = f"{name}.json"

            # Check if tool exists
            existing_tools = tool_handler.list_files()
            if tool_filename not in existing_tools:
                raise HTTPException(status_code=404, detail=f"Tool '{name}' not found.")

            # Update modified timestamp
            tool.modified_at = datetime.now(timezone.utc).isoformat()

            # Update the tool
            tool_json = json.dumps(tool.to_dict(), indent=4)
            tool_handler.write_file_content(tool_filename, tool_json)
            logger.info(f"Tool '{name}' updated successfully")
            return {"message": f"Tool '{name}' updated successfully."}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating tool '{name}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error updating tool: {str(e)}"
            )

    @app.post("/tools/{name}/execute", tags=[tags])
    async def execute_tool(
        name: str, request: Request, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """Execute a tool by name with the provided parameters.

        This endpoint mirrors the functionality of /manifests/execute/{uid} but works
        with tool names instead of manifest UIDs.

        Args:
            name: The name of the tool to execute.
            request: Represents an incoming fast api request object.
            parameters: Dictionary of key/value pairs to be passed to the tool execution (Optional).

        Returns:
            dict: Tool execution output.

        Raises:
            HTTPException: If tool not found (404) or execution fails (500).
        """
        logger.info(f"[execute_tool] START - Request to execute tool: {name} with parameters: {parameters}")
        execute_tool_counter.labels(name=name).inc()
        start_time = time.time()

        try:
            logger.info(f"[execute_tool] Reading tool manifest for: {name}")
            # Get the tool metadata
            tool_filename = f"{name}.json"
            content = tool_handler.read_file(tool_filename, raw_content=True)
            if not isinstance(content, str):
                raise HTTPException(
                    status_code=500, detail=f"Invalid content type for tool '{name}'"
                )
            tool_dict = json.loads(content)

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
                        detail=f"Tool '{name}' does not have a module file specified",
                    )

                # Get the module file content
                module_content = file_handler.read_file(module_name, raw_content=True)
                if not isinstance(module_content, str):
                    raise HTTPException(
                        status_code=500, detail=f"Invalid module content for tool '{name}'"
                    )

            # Load dependencies if they exist
            dependencies = tool_dict.get("dependencies", [])
            dependent_file_contents, dependent_tools_as_dict = load_tool_dependencies(
                dependencies=dependencies,
                tool_handler=tool_handler,
                file_handler=file_handler,
                tool_name=name
            )

            # Execute the tool using FileExecutor
            file_executor = FileExecutor(
                name=name,
                file_content=module_content,
                file_manifest=tool_dict,
                dependent_file_contents=dependent_file_contents,
                dependent_tools_as_dict=dependent_tools_as_dict,
            )

            # Ensure parameters is not None
            exec_parameters = parameters if parameters is not None else {}
            result = await file_executor.execute_file(
                parameters=exec_parameters, env_id=env_id
            )
            
            # Check if the result contains an error payload
            if isinstance(result, dict) and "error" in result:
                error_message = result.get("error", "Unknown error")
                logger.error(f"Tool '{name}' execution failed with error: {error_message}")
                
                # Determine appropriate HTTP status code based on error message
                # Tool not found on MCP server -> 404
                # Connection/timeout/other MCP errors -> 500
                if "not found" in error_message.lower():
                    status_code = 404
                else:
                    status_code = 500
                
                raise HTTPException(
                    status_code=status_code,
                    detail=error_message
                )
            
            # Record successful execution metrics
            duration = time.time() - start_time
            execute_successfully_tool_counter.labels(name=name).inc()
            execute_successfully_tool_latency.labels(name=name).observe(duration)
            logger.info(f"Tool '{name}' executed successfully with result: {result}")
            
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
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
                if matched_entity["similarity_score"] <= similarity_threshold
            ]

            # Get full tool objects for filtering
            tools_to_filter = []
            for matched_entity in filtered_matched_entities:
                tool_name = matched_entity.get("filename") or matched_entity.get("name")
                if not tool_name:
                    logger.warning(f"Matched entity missing 'filename' or 'name' field: {matched_entity}")
                    continue
                try:
                    tool_filename = f"{tool_name}.json"
                    content = tool_handler.read_file(tool_filename, raw_content=True)
                    if isinstance(content, str):
                        tool_dict = json.loads(content)
                        tool_dict["similarity_score"] = matched_entity.get("similarity_score", 0.0)
                        tools_to_filter.append(tool_dict)
                except Exception as e:
                    logger.warning(f"Could not load tool {tool_name} for filtering: {e}")

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
                {"filename": tool.get("name", ""), "similarity_score": tool.get("similarity_score", 0.0)}
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
        tool_name: Optional[str] = None,
        update: bool = False,
    ) -> Dict[str, Any]:
        """Add a tool by automatically extracting parameters from Python code docstring.

        This endpoint uploads a Python file and automatically generates a tool manifest
        by parsing the function's docstring. The docstring must follow standard Python
        documentation conventions (Google, NumPy, or Sphinx style).

        Args:
            tool: The Python file to upload containing the function.
            tool_name: Optional name of the specific function to extract. If not provided,
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
        if not tool.filename or not tool.filename.endswith('.py'):
            raise HTTPException(
                status_code=400,
                detail="Only Python (.py) files are supported. Please upload a valid Python file."
            )

        try:
            # Read the uploaded file content
            tool_bytes = await tool.read()
            
            # Extract function name and docstring from the Python code
            try:
                # extract_docstring returns (func_name, docstring_obj) tuple
                func_name, docstring_obj = extract_docstring(tool_bytes, tool_name=tool_name)  # type: ignore
                logger.info(f"Extracted function '{func_name}' from uploaded file")
            except Exception as e:
                logger.error(f"Failed to extract docstring: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to parse Python code or extract docstring: {str(e)}. "
                           "Ensure the function has a properly formatted docstring with parameters."
                )

            # Build the tool schema from the docstring
            # Extract description
            description = docstring_obj.short_description  # type: ignore
            if not description:
                raise HTTPException(
                    status_code=400,
                    detail="Function docstring must include a description."
                )

            # Extract parameters from docstring
            params_properties = {}
            required_params = []
            
            for param in docstring_obj.params:  # type: ignore
                params_properties[param.arg_name] = {
                    "type": param.type_name if param.type_name else "string",
                    "description": param.description if param.description else ""
                }
                required_params.append(param.arg_name)
            
            # Extract return information
            returns_schema = None
            if docstring_obj.returns:  # type: ignore
                returns_schema = ToolReturnsSchema(
                    type=docstring_obj.returns.type_name if docstring_obj.returns.type_name else None,  # type: ignore
                    description=docstring_obj.returns.description if docstring_obj.returns.description else None  # type: ignore
                )

            # Check if tool already exists
            existing_tools = tool_handler.list_files()
            tool_filename = f"{func_name}.json"

            if tool_filename in existing_tools:
                if not update:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Tool '{func_name}' already exists. Set update=true to overwrite."
                    )
                logger.info(f"Updating existing tool: {func_name}")
                
                # Delete old description if updating
                if tools_descriptions:
                    try:
                        tools_descriptions.delete_description(func_name)
                    except Exception as e:
                        logger.warning(f"Failed to delete old description: {e}")

            # Generate UUID
            tool_uuid = str(uuid.uuid4())
            logger.info(f"Generated UUID for tool '{func_name}': {tool_uuid}")

            # Save the module file
            module_filename = tool.filename if tool.filename else f"{func_name}.py"
            file_handler.write_file(tool_bytes, filename=module_filename)
            logger.info(f"Saved module file: {module_filename}")

            # Auto-detect dependencies if enabled
            dependencies = None
            if is_auto_detect_dependencies_enabled():
                try:
                    # Get list of available tools
                    available_tools = [f.replace('.json', '') for f in tool_handler.list_files()]
                    # Detect dependencies from code
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

            # Create the tool schema
            params_schema = ToolParamsSchema(
                type="object",
                properties=params_properties,
                required=required_params,
                optional=[]
            )
            
            # Set timestamps
            current_time = datetime.now(timezone.utc).isoformat()
            
            tool_schema = ToolSchema(
                name=func_name,
                description=description,
                uuid=tool_uuid,
                module_name=module_filename,
                programming_language="python",
                packaging_format="code",
                version="0.0.1",
                state=ManifestState.APPROVED,
                params=params_schema,
                returns=returns_schema,
                dependencies=dependencies,
                created_at=current_time,
                modified_at=current_time
            )

            # Save the manifest
            tool_json = json.dumps(tool_schema.to_dict(), indent=4)
            tool_handler.write_file_content(tool_filename, tool_json)
            logger.info(f"Saved manifest: {tool_filename}")

            # Write description for search capability
            if tools_descriptions:
                tools_descriptions.write_description(func_name, description)
                logger.info(f"Tool description saved for: {func_name}")

            logger.info(f"Tool '{func_name}' added successfully")
            return {
                "message": f"Tool '{func_name}' added successfully.",
                "name": func_name,
                "uuid": tool_uuid,
                "module_name": module_filename,
                "parameters": params_properties,
                "description": description,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding tool: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error adding tool: {str(e)}"
            )
            raise HTTPException(
                status_code=500, detail=f"Error searching tools: {str(e)}"
            )
