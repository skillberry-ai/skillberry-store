import logging
import os
import socket
import time
from dataclasses import dataclass, field

from prometheus_client import Counter, Histogram
from pydantic import Field
from typing import Annotated, Any, Callable, Dict, List, Optional, Protocol

from mcp.server.fastmcp import FastMCP
from skillberry_store.modules.object_handler import get_object_handler

logger = logging.getLogger(__name__)

# observability - metrics for runtime tool invocation inside the VMCP server.
# These belong here (not in the FastAPI layer) because they describe runtime
# behaviour of the running VMCP server, not HTTP requests.
_prom_prefix = "sts_vmcp_runtime_"
invoke_vmcp_tool_counter = Counter(
    f"{_prom_prefix}invoke_vmcp_tool_counter",
    "Count number of vmcp tool invoke operations",
    ["server_name", "tool_name"],
)
invoke_successfully_vmcp_tool_counter = Counter(
    f"{_prom_prefix}invoke_successfully_vmcp_tool_counter",
    "Count number of vmcp tool invoked successfully operations",
    ["server_name", "tool_name"],
)
invoke_successfully_vmcp_tool_latency = Histogram(
    f"{_prom_prefix}invoke_successfully_vmcp_tool_latency",
    "Histogram of invoke vmcp tool successfully latencies",
    ["server_name", "tool_name"],
)


def _patch_sse_starlette_for_multi_loop() -> None:
    """
    sse_starlette.EventSourceResponse._listen_for_exit_signal awaits a
    process-wide AppStatus.should_exit_event. anyio.Event binds to the
    first event loop that awaits it, so once one VMCP server's SSE
    handler creates that Event in its loop, every other VMCP server's
    SSE handler — running in its own thread+loop — fails with
    "RuntimeError: ... bound to a different event loop".

    Replace the listener with a poll on AppStatus.should_exit. We
    disable uvicorn's signal handlers in worker threads anyway, so the
    Event-based fast-path provides no value here, and the SSE task
    group is cancelled via _listen_for_disconnect when the connection
    closes during stop().
    """
    try:
        import anyio
        from sse_starlette.sse import AppStatus, EventSourceResponse
    except ImportError:
        return

    async def _listen_for_exit_signal_per_loop() -> None:
        while not AppStatus.should_exit:
            await anyio.sleep(0.5)

    EventSourceResponse._listen_for_exit_signal = staticmethod(
        _listen_for_exit_signal_per_loop
    )


_patch_sse_starlette_for_multi_loop()


class ToolSource(Protocol):
    """Where a server gets its tools' manifests, and how it runs them.

    Supplying one lets a caller own a server instance without the core
    server's process-global state. Deliberately expressed as *what the
    server needs* rather than as an ``ObjectHandler`` mirror: the server
    never reads module files or resolves dependencies itself, so execution
    strategy stays with whoever owns the content.
    """

    def get_manifest(self, uuid: str) -> dict:
        """Return the full manifest for ``uuid``. Raise if unavailable."""
        ...

    async def execute(self, manifest: dict, parameters: dict, env_id: str) -> dict:
        """Execute the tool described by ``manifest`` and return its result."""
        ...


class SnippetSource(Protocol):
    """Where a server gets its snippets' manifests."""

    def get_manifest(self, uuid: str) -> dict:
        """Return the full manifest for ``uuid``. Raise if unavailable."""
        ...


@dataclass
class InvokeRecord:
    """One observed tool invocation, passed to a server's ``on_invoke`` hook.

    Recorded for failures as well as successes — a caller observing a server
    to find misbehaviour cares most about the calls that blew up.
    """

    tool_name: str
    parameters: dict
    result: Any = None
    error: Optional[BaseException] = None
    duration: float = 0.0

    @property
    def failed(self) -> bool:
        return self.error is not None


class _HandlerToolSource:
    """Default source: the core ``ObjectHandler`` singletons and service registry.

    This is the behaviour every in-process server had before sources were
    injectable, kept verbatim — including pinning the manifest captured at
    registration time, so that a later overwrite of the tool JSON (e.g. by an
    MCP wrapper of the same name) cannot recurse back through the server.
    """

    def __init__(self, handler=None):
        self.handler = handler or get_object_handler("tool")

    def get_manifest(self, uuid: str) -> dict:
        return self.handler.read_dict(uuid)

    async def execute(self, manifest: dict, parameters: dict, env_id: str) -> dict:
        from skillberry_store.modules.file_executor import FileExecutor
        from skillberry_store.services.registry import get_service

        tool_name = manifest.get("name")
        module_name = manifest.get("module_name")
        if not module_name:
            raise ValueError(
                f"Tool '{tool_name}' has no module_name in cached manifest"
            )

        tool_uuid = manifest.get("uuid")
        if not tool_uuid:
            raise ValueError(f"Tool '{tool_name}' has no uuid in cached manifest")

        # Read the module file from the tool's UUID subdirectory.
        module_content = self.handler.read_file(
            tool_uuid, module_name, raw_content=True
        )
        if not isinstance(module_content, str):
            raise ValueError(f"Could not read module for tool '{tool_name}'")

        # Load tool dependencies recursively via the shared service method.
        dependencies = manifest.get("dependencies", [])
        tool_dep_ids = get_service("tool").find_dependencies(dependencies, tool_uuid)

        dep_dicts = self.handler.read_dicts(list(tool_dep_ids))
        dep_files = [
            self.handler.read_file(m["uuid"], m["module_name"], raw_content=True)
            for m in dep_dicts
        ]

        executor = FileExecutor(
            name=tool_name,
            file_content=module_content,
            file_manifest=manifest,
            dependent_file_contents=dep_files,
            dependent_tools_as_dict=dep_dicts,
        )
        return await executor.execute_file(parameters=parameters, env_id=env_id)


class _HandlerSnippetSource:
    """Default snippet source: the core ``ObjectHandler`` singleton."""

    def __init__(self, handler=None):
        self.handler = handler or get_object_handler("snippet")

    def get_manifest(self, uuid: str) -> dict:
        return self.handler.read_dict(uuid)


class VirtualMcpServer:
    """
    Represents a virtual MCP server.

    Attributes:
        name (str): The name of the virtual MCP server.
        description (str): A description of the virtual MCP server.
        port (int): The port on which the virtual MCP server is running.
        tool_uuids (List[str]): A list of tool UUIDs registered with the virtual MCP server.
        snippet_uuids (List[str]): A list of snippet UUIDs registered with the virtual MCP server.
        mcp (FastMCP): The underlying FastMCP instance.
    """

    def __init__(
        self,
        name: str,
        description: str,
        port: Optional[int],
        tools: List[str],
        snippets: Optional[List[str]] = None,
        sts_url: Optional[str] = None,
        app=None,
        env_id=None,
        tool_source: Optional[ToolSource] = None,
        snippet_source: Optional[SnippetSource] = None,
        serve: bool = True,
        metrics_enabled: bool = True,
        on_invoke: Optional[Callable[[InvokeRecord], None]] = None,
    ):
        """
        Initializes and starts a new VirtualMcpServer instance.

        Args:
            name (str): The name of the virtual MCP server.
            description (str): A description of the virtual MCP server.
            port (Optional[int]): The port for the virtual MCP server. If None, an available port will be found.
            tools (List[str]): A list of tool UUIDs to register with the virtual MCP server.
            snippets (List[str]): A list of snippet UUIDs to register as prompts with the virtual MCP server.
            env_id (str): A string representing the environment id to be used for this server (Optional).
            tool_source (ToolSource): Where to read tool manifests from and how to
                execute them. Defaults to the core ObjectHandler singletons plus
                the service registry — pass one to own a server instance without
                depending on that process-global state.
            snippet_source (SnippetSource): Likewise for snippets.
            serve (bool): When False, register nothing over HTTP: no port is
                taken, no FastMCP instance is built and no uvicorn thread is
                started. The server still resolves manifests and dispatches
                ``invoke_tool`` in-process, which is all a caller needs when it
                drives the tools itself rather than exposing them to an MCP client.
            metrics_enabled (bool): When False, skip the process-wide Prometheus
                metrics. Short-lived instances should disable them: the series are
                labelled by server name, so throwaway names accumulate cardinality
                that is never reclaimed.
            on_invoke (Callable): Called with an :class:`InvokeRecord` after every
                ``invoke_tool`` dispatch, successful or not. Exceptions raised by
                the hook are logged and swallowed.

        Raises:
            ValueError: If the specified port is not available.
        """
        self.name = name
        self.description = description
        self.tool_uuids = tools  # Store as UUIDs
        self.snippet_uuids = snippets or []  # Store as UUIDs
        self.sts_url = sts_url or "http://localhost:8000"
        self.app = app
        self.env_id = env_id
        self.serve = serve
        self.metrics_enabled = metrics_enabled
        self.on_invoke = on_invoke

        # Content + execution sources. Defaults fall back to the core
        # singletons so an in-process server behaves exactly as before, but they
        # are resolved *lazily*: a caller that injects a tool source and serves
        # no snippets must never touch a core singleton at all.
        self._tool_source = tool_source
        self._snippet_source = snippet_source

        # Cache of tool_name -> raw manifest dict, populated during
        # _load_manifests so that invoke_tool executes the manifest pinned at
        # registration time rather than re-reading files (which may have been
        # overwritten by an MCP wrapper with the same name after server creation).
        self._tool_manifests: dict = {}

        if not self.serve:
            # In-process only: no port, no FastMCP, no transport.
            self.port = None
            self.mcp = None
            self._load_manifests()
            logging.info(
                f"VirtualMcpServer '{name}' created (in-process, no transport) "
                f"with {len(self._tool_manifests)} tools"
            )
            return

        if port is None:
            self.port = self._find_available_port()
        else:
            self.port = port
            if not self._is_port_available(port):
                raise ValueError(f"Port {port} is not available")

        logging.info(f"Creating VirtualMcpServer '{name}' on port {self.port}")

        # Create FastMCP instance
        self.mcp = FastMCP(name=name, port=self.port)

        self._register_tools()
        self._register_prompts()
        self._start_server()
        logging.info(
            f"VirtualMcpServer '{name}' created and started on port {self.port} with {len(self.tool_uuids)} tools and {len(self.snippet_uuids)} prompts"
        )

    @property
    def tool_source(self) -> ToolSource:
        """The injected tool source, or the core-singleton default on first use."""
        if self._tool_source is None:
            self._tool_source = _HandlerToolSource()
        return self._tool_source

    @property
    def snippet_source(self) -> SnippetSource:
        """The injected snippet source, or the core-singleton default on first use."""
        if self._snippet_source is None:
            self._snippet_source = _HandlerSnippetSource()
        return self._snippet_source

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

    def _find_available_port(self, start_port: Optional[int] = None) -> int:
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

    def _load_manifests(self) -> dict:
        """Resolve this server's tool UUIDs to manifests and cache them.

        Pure data resolution — no FastMCP involvement — so it is usable with or
        without a transport. Populating the cache is the *point* of this method
        rather than a side effect of listing, which is what lets ``tool_names``
        report reliably.

        Returns:
            dict: the cache, mapping tool name -> manifest.
        """
        logger.debug("Loading manifests for tool UUIDs: %s", self.tool_uuids)
        for tool_uuid in self.tool_uuids:
            try:
                tool_dict = self.tool_source.get_manifest(tool_uuid)
                tool_name = tool_dict.get("name")
                if not tool_name:
                    logger.warning("Tool UUID %s has no name; skipping", tool_uuid)
                    continue
                self._tool_manifests[tool_name] = tool_dict
                logger.debug("Loaded tool UUID %s as '%s'", tool_uuid, tool_name)
            except Exception as e:
                logging.warning(f"Failed to get tool UUID {tool_uuid}: {e}")
        logger.debug("Loaded %d tool manifest(s)", len(self._tool_manifests))
        return self._tool_manifests

    def tool_names(self) -> List[str]:
        """Names of the tools this server serves, as registered."""
        return list(self._tool_manifests.keys())

    def tool_manifest(self, tool_name: str) -> Optional[dict]:
        """The pinned manifest for ``tool_name``, or None if not registered."""
        return self._tool_manifests.get(tool_name)

    def list_tools(self):
        """
        Lists the tools registered with the virtual MCP server.
        Resolves tool UUIDs to tool objects.

        Returns:
            List (mcp.types.Tool): A list of tools
        """
        tools = []
        for tool_name, tool_dict in self._load_manifests().items():
            try:
                tools.append(self.tool_dict_to_mcp_tool(tool_dict))
            except Exception as e:
                logging.warning(f"Failed to convert tool '{tool_name}': {e}")
        logger.debug("Returning %d MCP tool(s)", len(tools))
        return tools

    def list_snippets(self):
        """
        Lists the snippets registered with the virtual MCP server.
        Resolves snippet UUIDs to snippet objects.

        Returns:
            List[dict]: A list of snippet dictionaries
        """
        logger.debug("Loading snippet UUIDs: %s", self.snippet_uuids)
        snippets = []
        for snippet_uuid in self.snippet_uuids:
            try:
                snippet_dict = self.snippet_source.get_manifest(snippet_uuid)
                logger.debug(
                    "Loaded snippet UUID %s as '%s'",
                    snippet_uuid,
                    snippet_dict.get("name"),
                )
                snippets.append(snippet_dict)
            except Exception as e:
                logging.warning(f"Failed to get snippet UUID {snippet_uuid}: {e}")
        logger.debug("Returning %d snippet(s)", len(snippets))
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
        # Record invocation attempt
        if self.metrics_enabled:
            invoke_vmcp_tool_counter.labels(
                server_name=self.name, tool_name=tool_name
            ).inc()
        start_time = time.time()

        # Check if tool_name is in our cached tool names
        if tool_name not in self._tool_manifests:
            raise ValueError(f"Tool {tool_name} not found")

        # Execute the manifest pinned at registration time, not whatever is on
        # disk now: a later overwrite of the tool JSON (e.g. by an MCP wrapper
        # with the same name) would otherwise recurse back through this server.
        tool_dict = self._tool_manifests.get(tool_name)
        if tool_dict is None:
            raise ValueError(f"No cached manifest for tool '{tool_name}'")

        try:
            result = await self.tool_source.execute(tool_dict, parameters, env_id)
        except Exception as e:
            logging.error(
                f"Error invoking tool {tool_name} on VMCP server {self.name}: {e}"
            )
            self._notify_invoke(
                InvokeRecord(
                    tool_name=tool_name,
                    parameters=parameters,
                    error=e,
                    duration=time.time() - start_time,
                )
            )
            raise

        # Record successful execution metrics
        duration = time.time() - start_time
        if self.metrics_enabled:
            invoke_successfully_vmcp_tool_counter.labels(
                server_name=self.name, tool_name=tool_name
            ).inc()
            invoke_successfully_vmcp_tool_latency.labels(
                server_name=self.name, tool_name=tool_name
            ).observe(duration)

        self._notify_invoke(
            InvokeRecord(
                tool_name=tool_name,
                parameters=parameters,
                result=result,
                duration=duration,
            )
        )
        return result

    def _notify_invoke(self, record: InvokeRecord) -> None:
        """Hand one invocation to the ``on_invoke`` hook, if any.

        An observer must never be able to break dispatch, so its exceptions are
        logged and dropped.
        """
        if self.on_invoke is None:
            return
        try:
            self.on_invoke(record)
        except Exception as e:
            logging.warning(
                f"on_invoke hook failed for tool {record.tool_name} "
                f"on VMCP server {self.name}: {e}"
            )

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

    def _start_server(self):
        """
        Starts the virtual MCP server with CORS middleware over SSE transport.
        """
        import asyncio
        import threading
        import uvicorn

        self._server: "uvicorn.Server | None" = None
        self._loop: "asyncio.AbstractEventLoop | None" = None

        def run_server():
            logging.info(f"Starting FastMCP server '{self.name}' on port {self.port}")

            try:
                # Get the Starlette app from FastMCP and add CORS middleware
                app = self.mcp.sse_app()

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

                config = uvicorn.Config(
                    app,
                    host="127.0.0.1",
                    port=self.port,
                    log_level="info",
                )
                server = uvicorn.Server(config)
                # uvicorn installs SIGINT/SIGTERM handlers via signal.signal(),
                # which raises ValueError outside the main thread. We're in a
                # worker thread, so disable installation. stop() drives shutdown
                # via server.should_exit instead.
                setattr(server, "install_signal_handlers", lambda: None)

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop
                self._server = server

                try:
                    loop.run_until_complete(server.serve())
                finally:
                    try:
                        loop.run_until_complete(loop.shutdown_asyncgens())
                    except Exception:
                        pass
                    loop.close()
                    self._loop = None
                    self._server = None
            except Exception as e:
                logging.error(f"VMCP server '{self.name}' crashed: {e}", exc_info=True)

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

    def stop(self):
        """
        Stops the virtual MCP server: signals uvicorn to exit and joins the worker thread.
        """
        server = getattr(self, "_server", None)
        loop = getattr(self, "_loop", None)
        thread = getattr(self, "server_thread", None)

        if server is not None and loop is not None and not loop.is_closed():
            # should_exit is polled by serve()'s main loop; setting it from any
            # thread is safe (plain attribute write). Wake the loop in case it's
            # blocked on I/O so it observes the flag promptly.
            try:
                server.should_exit = True
                loop.call_soon_threadsafe(lambda: None)
            except Exception as e:
                logging.warning(
                    f"Failed to signal VMCP server '{self.name}' to exit: {e}"
                )

        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)
            if thread.is_alive():
                # Last resort: ask uvicorn to force-exit and give it a brief
                # window to bail before giving up.
                if server is not None:
                    try:
                        server.force_exit = True
                    except Exception:
                        pass
                thread.join(timeout=2.0)
                if thread.is_alive():
                    logging.warning(
                        f"VMCP server thread '{self.name}' did not stop within "
                        "timeout; leaving as daemon thread."
                    )

    def __enter__(self) -> "VirtualMcpServer":
        """Support ``with VirtualMcpServer(...) as server:`` so a served instance
        always releases its port, even if the caller raises."""
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

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
            "tools": self.tool_uuids,
            "snippets": self.snippet_uuids,
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
