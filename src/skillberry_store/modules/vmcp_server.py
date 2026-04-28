import logging
import os
import socket
import time

import requests
from pydantic import Field
from typing import Annotated, Any, List, Optional

from mcp.server.fastmcp import FastMCP


class VirtualMcpServer:
    """
    Represents a virtual MCP server.

    Attributes:
        name (str): The name of the virtual MCP server.
        description (str): A description of the virtual MCP server.
        port (int): The port on which the virtual MCP server is running.
        tools (List[str]): A list of tool UUIDs registered with the virtual MCP server.
        mcp (FastMCP): The underlying FastMCP instance.
    """

    def __init__(
        self,
        name: str,
        description: str,
        port: Optional[int],
        tools: List[str],
        snippets: List[str] = None,
        sts_url: str = None,
        app=None,
        env_id=None,
    ):
        """
        Initializes and starts a new VirtualMcpServer instance.

        Args:
            name (str): The name of the virtual MCP server.
            description (str): A description of the virtual MCP server.
            port (Optional[int]): The port for the virtual MCP server. If None, an available port will be found.
            tools (List[str]): A list of tool names to register with the virtual MCP server.
            snippets (List[str]): A list of snippet names to register as prompts with the virtual MCP server.
            env_id (str): A string representing the environment id to be used for this server (Optional).

        Raises:
            ValueError: If the specified port is not available.
        """
        self.name = name
        self.description = description
        self.tools = tools
        self.snippets = snippets or []
        self.sts_url = sts_url or "http://localhost:8000"
        self.app = app
        self.env_id = env_id

        if port is None:
            self.port = self._find_available_port()
        else:
            self.port = port
            if not self._is_port_available(port):
                raise ValueError(f"Port {port} is not available")

        logging.info(f"Creating VirtualMcpServer '{name}' on port {self.port}")

        # Create FastMCP instance
        self.mcp = FastMCP(name=name, port=self.port)

        # Configure CORS middleware for browser access
        # This will be passed to mcp.run() in _start_server()
        from starlette.middleware import Middleware
        from starlette.middleware.cors import CORSMiddleware

        self.cors_middleware = [
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],  # Allow all origins for development
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=[
                    "mcp-protocol-version",
                    "mcp-session-id",
                    "Authorization",
                    "Content-Type",
                    "*",  # Allow all headers
                ],
                expose_headers=["mcp-session-id"],
                allow_credentials=True,
            )
        ]
        logging.info("CORS middleware configured for FastMCP server")

        # Cache of tool_name -> raw manifest dict, populated during _register_tools so that
        # invoke_tool can execute code tools directly without re-reading files (which may have
        # been overwritten by an MCP wrapper with the same name after server creation).
        self._tool_manifests: dict = {}

        self._register_tools()
        self._register_prompts()
        self._start_server()
        logging.info(
            f"VirtualMcpServer '{name}' created and started on port {self.port} with {len(self.tools)} tools and {len(self.snippets)} prompts"
        )

    def _is_port_available(self, port: int) -> bool:
        """
        Checks if a port is available.

        Args:
            port (int): The port to check.

        Returns:
            bool: True if the port is available, False otherwise.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return True
            except socket.error:
                return False

    def _find_available_port(self, start_port: int = None) -> int:
        """
        Finds the next available port starting from a given port.

        Args:
            start_port (int): The port to start checking from. If None, uses VMCP_START_PORT env var or 10000.

        Returns:
            int: The available port.
        """
        if start_port is None:
            start_port = int(os.environ.get("VMCP_SERVERS_START_PORT", 10000))

        port = start_port
        while not self._is_port_available(port):
            port += 1
        return port

    def list_tools(self):
        """
        Lists the tools registered with the virtual MCP server.

        Returns:
            List (mcp.types.Tool): A list of tools
        """
        # Get tools from the tools directory directly to avoid HTTP dependency during startup
        print(f"DEBUG list_tools: self.tools = {self.tools}")
        tools = []
        for tool_name in self.tools:
            try:
                # Try HTTP first if available
                if self.app:
                    # Use direct file access when app is available (during startup)
                    import json
                    from skillberry_store.tools.configure import get_tools_directory
                    from skillberry_store.modules.file_handler import FileHandler

                    tools_handler = FileHandler(get_tools_directory())
                    tool_filename = f"{tool_name}.json"
                    content = tools_handler.read_file(tool_filename, raw_content=True)
                    if isinstance(content, str):
                        tool_dict = json.loads(content)
                        print(
                            f"DEBUG list_tools: Got tool {tool_name} from file: {tool_dict.get('name')}"
                        )
                        self._tool_manifests[tool_name] = tool_dict
                        tools.append(self.tool_dict_to_mcp_tool(tool_dict))
                    else:
                        logging.warning(
                            f"Failed to read tool {tool_name}: invalid content type"
                        )
                else:
                    # Fallback to HTTP when app is not available
                    response = requests.get(f"{self.sts_url}/tools/{tool_name}")
                    response.raise_for_status()
                    tool_dict = response.json()
                    print(
                        f"DEBUG list_tools: Got tool {tool_name} from HTTP: {tool_dict.get('name')}"
                    )
                    self._tool_manifests[tool_name] = tool_dict
                    tools.append(self.tool_dict_to_mcp_tool(tool_dict))
            except Exception as e:
                logging.warning(f"Failed to get tool {tool_name}: {e}")
                print(f"DEBUG list_tools: Failed to get tool {tool_name}: {e}")
        print(f"DEBUG list_tools: Returning {len(tools)} tools")
        return tools

    def list_snippets(self):
        """
        Lists the snippets registered with the virtual MCP server.

        Returns:
            List[dict]: A list of snippet dictionaries
        """
        print(f"DEBUG list_snippets: self.snippets = {self.snippets}")
        snippets = []
        for snippet_name in self.snippets:
            try:
                if self.app:
                    # Use direct file access when app is available (during startup)
                    import json
                    from skillberry_store.tools.configure import get_snippets_directory
                    from skillberry_store.modules.file_handler import FileHandler

                    snippets_handler = FileHandler(get_snippets_directory())
                    snippet_filename = f"{snippet_name}.json"
                    content = snippets_handler.read_file(
                        snippet_filename, raw_content=True
                    )
                    if isinstance(content, str):
                        snippet_dict = json.loads(content)
                        print(
                            f"DEBUG list_snippets: Got snippet {snippet_name} from file: {snippet_dict.get('name')}"
                        )
                        snippets.append(snippet_dict)
                    else:
                        logging.warning(
                            f"Failed to read snippet {snippet_name}: invalid content type"
                        )
                else:
                    # Fallback to HTTP when app is not available
                    response = requests.get(f"{self.sts_url}/snippets/{snippet_name}")
                    response.raise_for_status()
                    snippet_dict = response.json()
                    print(
                        f"DEBUG list_snippets: Got snippet {snippet_name} from HTTP: {snippet_dict.get('name')}"
                    )
                    snippets.append(snippet_dict)
            except Exception as e:
                logging.warning(f"Failed to get snippet {snippet_name}: {e}")
                print(f"DEBUG list_snippets: Failed to get snippet {snippet_name}: {e}")
        print(f"DEBUG list_snippets: Returning {len(snippets)} snippets")
        return snippets

    def _register_tools(self):
        """
        Register tools with the FastMCP server.
        """
        tools = self.list_tools()
        for tool in tools:
            # Create a dynamic function with the correct signature based on the tool's parameters
            def make_handler(tool_name, tool_schema):
                # Extract parameter names from the tool schema
                properties = tool_schema.get("inputSchema", {}).get("properties", {})
                logging.info(
                    f"@@@@@ make_handler: {tool_name} '{properties}' @@@@@"
                )  # OK..
                required = tool_schema.get("inputSchema", {}).get("required", [])

                # Create function signature dynamically
                import inspect

                try:
                    annotations = {}
                    params = []
                    for param_name, param_info in properties.items():
                        logging.info(f"@@@@@ param_info: {param_info} @@@@@")

                        # Skip variadic parameters like *args, **kwargs
                        if param_name.startswith("*"):
                            logging.warning(
                                f"Skipping variadic parameter: {param_name}"
                            )
                            continue

                        # Validate param_info has required keys
                        if not isinstance(param_info, dict) or "type" not in param_info:
                            logging.warning(
                                f"Skipping invalid parameter {param_name}: missing 'type' field"
                            )
                            continue

                        description = param_info.get(
                            "description", f"Parameter {param_name}"
                        )
                        _type = param_info["type"]

                        # annotate the parameter so that is appears inside MCP tool
                        # i.e. when being retrieved via MCP client
                        annotated_type = Annotated[
                            param_type_to_python_type(_type),
                            Field(title=description, description=description),
                        ]
                        annotations[param_name] = annotated_type

                        if param_name in required:
                            params.append(
                                inspect.Parameter(
                                    param_name,
                                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                    annotation=annotated_type,
                                )
                            )
                        else:
                            params.append(
                                inspect.Parameter(
                                    param_name,
                                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                    default=None,
                                    annotation=annotated_type,
                                )
                            )
                except Exception as e:
                    logging.error(
                        f"Error converting tool {tool_name} parameters into MCP format: {str(e)}"
                    )
                    raise

                # Create the handler function
                async def handler(*args, **kwargs):
                    """
                    Invocation function of the MCP tool.

                    """
                    # Convert args and kwargs back to a dictionary
                    param_names = list(properties.keys())
                    parameters = {}

                    # Handle positional arguments
                    for i, arg in enumerate(args):
                        if i < len(param_names):
                            parameters[param_names[i]] = arg

                    # Handle keyword arguments
                    parameters.update(kwargs)

                    logging.info(f"@@@@@ handler: env_id: {self.env_id}  @@@@@")

                    # Pass parameters as a dictionary to match SBS expectations
                    try:
                        return_value = await self.invoke_tool(
                            tool_name, parameters, self.env_id
                        )
                    except Exception as e:
                        logging.info(f"@@@@@ handler: Error '{str(e)}'  @@@@@")
                        # tool invocation logic
                        cleaned_return_value = f"EXCEPTION:Error executing tool: {e}"
                        logging.info(f"cleaned_return_value: {cleaned_return_value}")
                        return cleaned_return_value

                    logging.info(f"return_value from invoke_tool: {return_value}")

                    # Check if the response contains an error
                    if isinstance(return_value, dict) and "error" in return_value:
                        error_msg = return_value["error"]
                        # TODO (weit): Revise the below commented out block - it seems that
                        # stderr is always none.
                        # -------------------------------------------------
                        # # Include stderr if available for more context
                        # if "stderr" in return_value and return_value["stderr"]:
                        #     error_msg = f"{error_msg}\n\nStderr:\n{return_value['stderr']}"
                        # cleaned_return_value = f"EXCEPTION:{error_msg}"
                        cleaned_return_value = str(error_msg)
                        logging.error(
                            f"Tool execution returned error: {cleaned_return_value}"
                        )
                        return cleaned_return_value

                    # extract return value
                    if (
                        isinstance(return_value, dict)
                        and "return value" in return_value
                    ):
                        return_value = return_value["return value"]
                    else:
                        # Fallback: if response doesn't have expected format, return as-is
                        logging.warning(
                            f"Unexpected return value format: {return_value}"
                        )
                        return str(return_value)

                    # clean up the return value
                    cleaned_return_value = return_value.strip().replace('"', "")
                    logging.info(
                        f"====> returning response from the function: {cleaned_return_value}"
                    )
                    return cleaned_return_value

                # Set function metadata
                handler.__name__ = tool_name
                handler.__doc__ = tool.description
                handler.__signature__ = inspect.Signature(params)
                handler.__annotations__ = annotations
                logging.info(
                    f"@@@@@@ handler.__signature__ {handler.__signature__}  @@@@@@"
                )

                return handler

            handler = make_handler(tool.name, tool.__dict__)

            # Use FastMCP's add_tool method
            self.mcp.add_tool(handler, name=tool.name, description=tool.description)

    def _register_prompts(self):
        """
        Register snippets as prompts with the FastMCP server.

        Uses the @prompt decorator pattern to register each snippet as an MCP prompt.
        """
        snippets = self.list_snippets()
        for snippet in snippets:
            try:
                snippet_name = snippet.get("name")
                snippet_description = snippet.get("description", "")
                snippet_content = snippet.get("content", "")

                # Skip snippets with missing or invalid name
                if not snippet_name or not isinstance(snippet_name, str):
                    logging.warning(
                        f"Skipping snippet with missing or invalid name: {snippet}"
                    )
                    continue

                # Skip snippets with missing content
                if snippet_content is None:
                    logging.warning(
                        f"Skipping snippet '{snippet_name}': missing 'content' field"
                    )
                    continue

                # Create a prompt function with proper closure
                def make_prompt_func(name, desc, content):
                    # Use the @prompt decorator from FastMCP
                    @self.mcp.prompt(name=name, description=desc)
                    def prompt_func():
                        """Returns the snippet content as a prompt."""
                        return content

                    return prompt_func

                # Register the prompt
                make_prompt_func(snippet_name, snippet_description, snippet_content)
                logging.info(f"Registered prompt '{snippet_name}' with MCP server")
            except Exception as e:
                logging.error(
                    f"Failed to register prompt for snippet {snippet.get('name', 'unknown')}: {e}"
                )

    async def invoke_tool(self, tool_name: str, parameters: dict, env_id: str):
        """
        Invokes a tool on the virtual MCP server.

        Args:
            tool_name (str): The name of the tool to invoke.
            parameters (dict): The parameters for the tool invocation.
            env_id (str): A string representing the environment id to be used for this server (Optional).

        Returns:
            result: The result of the tool invocation.
        """
        # Import metrics here to avoid circular imports
        from skillberry_store.fast_api.vmcp_api import (
            invoke_vmcp_tool_counter,
            invoke_successfully_vmcp_tool_counter,
            invoke_successfully_vmcp_tool_latency,
        )

        # Record invocation attempt
        invoke_vmcp_tool_counter.labels(
            server_name=self.name, tool_name=tool_name
        ).inc()
        start_time = time.time()

        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")

        try:
            from skillberry_store.tools.configure import get_files_directory_path
            from skillberry_store.modules.file_handler import FileHandler
            from skillberry_store.modules.file_executor import FileExecutor

            # Use the manifest cached at server creation time so that a later overwrite of the
            # tool JSON file (e.g. by an MCP wrapper with the same name) cannot cause
            # infinite recursion back through this server.
            tool_dict = self._tool_manifests.get(tool_name)
            if tool_dict is None:
                raise ValueError(f"No cached manifest for tool '{tool_name}'")

            module_name = tool_dict.get("module_name")
            if not module_name:
                raise ValueError(
                    f"Tool '{tool_name}' has no module_name in cached manifest"
                )

            file_handler = FileHandler(get_files_directory_path())
            module_content = file_handler.read_file(module_name, raw_content=True)
            if not isinstance(module_content, str):
                raise ValueError(f"Could not read module for tool '{tool_name}'")

            executor = FileExecutor(
                name=tool_name,
                file_content=module_content,
                file_manifest=tool_dict,
            )
            result = await executor.execute_file(parameters=parameters, env_id=env_id)

            # Record successful execution metrics
            duration = time.time() - start_time
            invoke_successfully_vmcp_tool_counter.labels(
                server_name=self.name, tool_name=tool_name
            ).inc()
            invoke_successfully_vmcp_tool_latency.labels(
                server_name=self.name, tool_name=tool_name
            ).observe(duration)

            return result
        except Exception as e:
            logging.error(
                f"Error invoking tool {tool_name} on VMCP server {self.name}: {e}"
            )
            raise

    def tool_dict_to_mcp_tool(self, tool_dict: dict):
        """
        Convert SBS tool dictionary to MCP tool format.

        Args:
            tool_dict: Tool dictionary from the tools API (has same structure as manifest)

        Returns:
            mcp.types.Tool: MCP tool object
        """
        from mcp import types

        # Clean up extras before unpacking
        extras = tool_dict.copy()
        for key in ["name", "description", "params"]:
            extras.pop(key, None)

        return types.Tool(
            name=str(tool_dict["name"]),
            description=tool_dict.get("description"),
            inputSchema=tool_dict["params"],
            **extras,
        )

    def _start_server(self, transport="sse"):
        """
        Starts the virtual MCP server with CORS middleware.

        Args:
            transport (str): The transport to use. Defaults to "sse".
        """
        import threading
        import uvicorn

        def run_server():
            logging.info(f"Starting FastMCP server '{self.name}' on port {self.port}")

            # Get the SSE app and manually add CORS middleware
            if hasattr(self, "cors_middleware"):
                try:
                    # Get the Starlette app from FastMCP
                    app = self.mcp.sse_app()

                    # Add CORS middleware to the existing app
                    # We need to add it to app.user_middleware since the app is already created
                    from starlette.middleware.cors import CORSMiddleware

                    app.add_middleware(
                        CORSMiddleware,
                        allow_origins=["*"],
                        allow_methods=["GET", "POST", "OPTIONS"],
                        allow_headers=["*"],
                        allow_credentials=True,
                        expose_headers=["*"],
                    )

                    logging.info(
                        f"CORS middleware added, starting server on port {self.port}"
                    )
                    # Run the app with uvicorn
                    uvicorn.run(app, host="127.0.0.1", port=self.port, log_level="info")
                except Exception as e:
                    logging.error(f"Failed to start with CORS: {e}", exc_info=True)
                    # Fallback to default
                    self.mcp.run(transport=transport)
            else:
                self.mcp.run(transport=transport)

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

    def stop(self):
        """
        Stops the virtual MCP server.
        """
        if hasattr(self, "server_thread") and self.server_thread.is_alive():
            # FastMCP doesn't have a clean stop method, thread will terminate when process ends
            pass

    def to_dict(self):
        """
        Converts the VirtualMcpServer instance to a dictionary.

        Returns:
            dict: A dictionary representation of the VirtualMcpServer.
        """
        return {
            "name": self.name,
            "description": self.description,
            "port": self.port,
            "tools": self.tools,
            "snippets": self.snippets,
        }


def param_type_to_python_type(param_type: str) -> Any:
    """
    Helper utility to map parameter type string into a Python type.

    This method is used to properly annotate tool parameters for MCP tools.
    Inspired from https://github.ibm.com/skillberry/skillberry-agent/blob/main/agents/remote_tools_wrapper.py#L98

    Parameters:
        param_type (str): a type value of a tool parameter (e.g., 'string', 'integer', 'boolean')

    """
    # Mapping manifest properties types to Python types
    type_mapping = {
        "string": str,
        "str": str,
        "number": float,
        "float": float,
        "integer": int,
        "int": int,
        "bool": bool,
        "boolean": bool,
        "object": dict,
        "list": list,
        "array": list,
        # "datetime": datetime,
        "null": None,
        "any": object,  # 'any' can be mapped to object or str, depending on use case
    }

    # Return the corresponding Python type as a string
    return type_mapping.get(param_type, object)
