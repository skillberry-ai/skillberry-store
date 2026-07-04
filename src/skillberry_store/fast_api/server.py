import logging
import os
from typing import Any, List, Literal

import uvicorn

from pydantic_settings import BaseSettings
from pydantic import Field, model_validator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fastapi_mcp import FastApiMCP

from skillberry_store.fast_api.skills_api import register_skills_api
from skillberry_store.fast_api.snippets_api import register_snippets_api
from skillberry_store.fast_api.tools_api import register_tools_api
from skillberry_store.fast_api.admin_api import register_admin_api
from skillberry_store.fast_api.vmcp_api import register_vmcp_api
from skillberry_store.fast_api.vnfs_api import register_vnfs_api
from skillberry_store.fast_api.plugins_api import register_plugins_api
from skillberry_store.fast_api.events_api import register_events_api
from skillberry_store.fast_api.plugin_proxy import PluginRegistry, add_plugin_proxy
from skillberry_store.tools.configure import (
    configure_logging,
)

try:
    from skillberry_store.fast_api.git_version import __git_version__
except:
    __git_version__ = "unknown"

from skillberry_store.fast_api.observability import observability_setup
from prometheus_client import Counter, Histogram

# this environment variable is used to enable the latest API version
ENABLE_API_VERSION = os.environ.get("ENABLE_API_VERSION", "latest")

logger = logging.getLogger(__name__)


class SBSettings(BaseSettings):
    """Configuration settings for the SBS server."""

    sbs_host: str = Field("0.0.0.0", validation_alias="SBS_HOST")
    sbs_port: int = Field(8000, validation_alias="SBS_PORT")
    ui_port: int = Field(8002, validation_alias="SBS_UI_PORT")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", validation_alias="UVICORN_LOG_LEVEL"
    )
    observability: bool = Field(True, validation_alias="OBSERVABILITY")
    sbs_vdb: str = Field("faiss", env="SBS_VDB")

    @property
    def display_host(self) -> str:
        """Return a browser-friendly host (0.0.0.0 is not browsable on Windows)."""
        return "localhost" if self.sbs_host == "0.0.0.0" else self.sbs_host


class SBS(FastAPI):
    def __init__(self, **settings: Any):
        """Initialize the SBS server with FastAPI and custom settings."""

        super().__init__()
        self.settings = SBSettings(**settings)
        self.configure_fastapi()
        configure_logging(logging._nameToLevel[self.settings.log_level])
        self.logger = logging.getLogger(__name__)
        logger.info(f"SBSettings sbs_vdb = {self.settings.sbs_vdb}")

        # Load per-endpoint import auth config (import_auth_config.yaml /
        # SBS_IMPORT_AUTH_CONFIG). Logs the
        # path and endpoint count; harmless if no config file is present.
        from skillberry_store.tools.endpoint_auth import get_config

        get_config()

        # Initialize object handlers (singleton pattern). Descriptions are created
        # inside each ObjectHandler using SBS_VDB (defaults to "faiss").
        from skillberry_store.modules.object_handler import initialize_object_handlers

        initialize_object_handlers()
        logger.info("Object handlers initialized")

        # Initialize service layer (singletons in services.registry)
        from skillberry_store.modules.vnfs_server_manager import VirtualNfsServerManager
        from skillberry_store.modules.vmcp_server_manager import VirtualMcpServerManager
        from skillberry_store.services.registry import (
            initialize_services,
            get_service,
        )

        sts_url = f"http://{self.settings.sbs_host}:{self.settings.sbs_port}"

        initialize_services(
            vmcp_server_manager=VirtualMcpServerManager(sts_url=sts_url, app=self),
            vnfs_server_manager=VirtualNfsServerManager(sts_url=sts_url, app=self),
        )
        tools_service = get_service("tool")
        skills_service = get_service("skill")
        snippets_service = get_service("snippet")
        vnfs_service = get_service("vnfs")
        vmcp_service = get_service("vmcp")

        from skillberry_store.services.admin_service import AdminService

        admin_service = AdminService(
            vmcp_server_manager=vmcp_service.server_manager,
            vnfs_server_manager=vnfs_service.server_manager,
        )

        # Initialize plugin system
        from skillberry_store.plugins.loader import PluginLoader
        from skillberry_store.plugins.store_api import StoreAPI

        store_api = StoreAPI(
            {
                "tools": tools_service,
                "skills": skills_service,
                "snippets": snippets_service,
                "vnfs": vnfs_service,
                "vmcp": vmcp_service,
            }
        )

        plugin_loader = PluginLoader(store_api=store_api)
        discovered = plugin_loader.discover_plugins()
        logger.info(f"Discovered {len(discovered)} plugins: {discovered}")

        self.state.plugin_loader = plugin_loader

        register_vmcp_api(
            self,
            tags="vmcp_servers",
            service=vmcp_service,
        )
        register_vnfs_api(
            self,
            tags="vnfs_servers",
            service=vnfs_service,
        )
        register_skills_api(
            self,
            tags="skills",
            service=skills_service,
        )
        register_snippets_api(
            self,
            tags="snippets",
            service=snippets_service,
        )
        register_tools_api(
            self,
            tags="tools",
            service=tools_service,
        )
        register_admin_api(self, tags="admin", service=admin_service)

        # Register SSE events endpoint and out-of-process plugin proxy.
        plugin_registry = PluginRegistry()
        self.state.plugin_registry = plugin_registry
        register_events_api(self, tags="events")

        # Build the plugin state store + manager. Test suites set
        # SKILLBERRY_PLUGIN_STATE_FILE="" so SBS boots with no plugins persisted.
        from skillberry_store.plugins.manager import PluginManager
        from skillberry_store.plugins.state_store import PluginStateStore

        state_store = PluginStateStore()
        plugin_manager = PluginManager(
            registry=plugin_registry,
            state_store=state_store,
            sbs_base_url=sts_url,
        )
        self.state.plugin_manager = plugin_manager

        register_plugins_api(
            self,
            plugin_loader=plugin_loader,
            plugin_manager=plugin_manager,
            tags="plugins",
        )

        # Mount plugin routers first so in-process routes win over the catch-all.
        plugin_loader.mount_routers(self)
        logger.info("Plugin routers mounted")

        add_plugin_proxy(self, plugin_registry)

        # Autostart plugins whose state entries request it, without blocking boot.
        @self.on_event("startup")
        async def _bootstrap_plugins() -> None:
            try:
                await plugin_manager.bootstrap()
            except Exception:
                logger.exception("plugin bootstrap failed")

        @self.on_event("shutdown")
        async def _shutdown_plugins() -> None:
            try:
                await plugin_manager.stop_all()
            except Exception:
                logger.exception("plugin stop_all failed")

        # Mount the Control MCP with a CURATED surface. The store auto-generates an
        # MCP tool per REST endpoint, but agents only need the content operations,
        # and many endpoints either don't belong on the agent surface (health,
        # readiness, metrics, admin backup/restore/purge, change polling, provenance)
        # or can't be MCP tools at all (file-upload endpoints — an MCP call has no
        # file body). Rather than maintaining a separate allow-list that drifts as
        # endpoints come and go, each endpoint opts in where it is declared via
        # ``openapi_extra={"x-mcp-tool": True}`` (alongside the existing
        # ``x-cli-name``). We derive the allow-list from those markers here.
        mcp_included_operations = self._mcp_included_operations()
        logger.info(
            "Exposing %d operations on the Control MCP: %s",
            len(mcp_included_operations),
            ", ".join(sorted(mcp_included_operations)),
        )
        mcp_server = FastApiMCP(self, include_operations=mcp_included_operations)
        mcp_server.mount_sse(mount_path="/control_sse")

    def _mcp_included_operations(self) -> List[str]:
        """Operation ids opted in to the Control MCP via ``x-mcp-tool``.

        Reads the generated OpenAPI schema (the same source ``FastApiMCP``
        consumes) so the Control MCP surface stays in sync with the endpoints
        automatically — there is no list to maintain in parallel.
        """
        return mcp_operations_from_openapi(self.openapi())

    def configure_fastapi(self):
        """Configures CORS middleware and OpenAPI documentation settings."""
        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.openapi = lambda: custom_openapi(self, [])

        # Add observability for FastAPI application
        if int(os.getenv("OTEL_TRACES_PORT", 0)) > 0:
            FastAPIInstrumentor.instrument_app(self)

    def run(self):
        """Starts the FastAPI app using Uvicorn."""
        self.logger.info("Starting SBS server")
        self.logger.info(
            f"API server running at: http://{self.settings.display_host}:{self.settings.sbs_port}"
        )
        # self.logger.info(f"UI available at: http://localhost:{self.settings.ui_port}")
        self.logger.info(
            f"API documentation at: http://{self.settings.display_host}:{self.settings.sbs_port}/docs"
        )

        if self.settings.observability:
            observability_setup()

        # Configure uvicorn logging - create custom config to ensure all requests are logged
        import copy
        from uvicorn.config import LOGGING_CONFIG

        log_config = copy.deepcopy(LOGGING_CONFIG)
        log_config["formatters"]["access"][
            "fmt"
        ] = '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
        log_config["loggers"]["uvicorn.access"][
            "level"
        ] = "DEBUG"  # Ensure all access logs are shown

        uvicorn.run(
            self,
            host=self.settings.sbs_host,
            port=self.settings.sbs_port,
            access_log=True,
            log_config=log_config,
        )


def mcp_operations_from_openapi(openapi_schema: dict) -> List[str]:
    """Collect ``operationId``s opted in to the Control MCP via ``x-mcp-tool``.

    An endpoint joins the Control MCP surface by declaring
    ``openapi_extra={"x-mcp-tool": True}`` (next to the existing ``x-cli-name``).
    FastAPI merges ``openapi_extra`` into each operation object, so the marker
    and the ``operationId`` both live in the generated schema — the same schema
    ``FastApiMCP`` consumes. Deriving the allow-list from there keeps the CLI and
    Control MCP aligned and avoids maintaining a parallel list that drifts.
    """
    operations: List[str] = []
    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            if operation.get("x-mcp-tool") and operation.get("operationId"):
                operations.append(operation["operationId"])
    return operations


def custom_openapi(app: FastAPI, openapi_tags):
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="skillberry",
        summary="Towards hallucination-less AI systems",
        version=__git_version__,
        tags=openapi_tags,
        contact={
            "name": "Eran Raichstein",
            "email": "eranra@il.ibm.com",
        },
        routes=app.routes,
    )

    # Fix file upload schema for SDK generation
    # FastAPI generates contentMediaType but OpenAPI generators expect format: binary
    if "components" in openapi_schema and "schemas" in openapi_schema["components"]:
        schemas = openapi_schema["components"]["schemas"]

        # Define all file upload endpoints and their file parameter names
        file_upload_fixes = [
            ("Body_add_tool_from_python_tools_add_post", "tool"),
            ("Body_create_tool_tools__post", "module"),
            ("Body_create_snippet_snippets__post", "file"),
            ("Body_import_anthropic_skill_skills_import_anthropic_post", "zip_file"),
        ]

        # Apply fix to all file upload schemas
        for schema_name, file_param in file_upload_fixes:
            if schema_name in schemas:
                schema = schemas[schema_name]
                if "properties" in schema and file_param in schema["properties"]:
                    file_prop = schema["properties"][file_param]
                    # Remove contentMediaType and add format: binary
                    if "contentMediaType" in file_prop:
                        del file_prop["contentMediaType"]
                    file_prop["format"] = "binary"

    app.openapi_schema = openapi_schema
    return app.openapi_schema
