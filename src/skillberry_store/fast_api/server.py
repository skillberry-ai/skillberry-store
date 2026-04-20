import logging
import os
from typing import Any, Literal

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
from skillberry_store.modules.description import Description
from skillberry_store.modules.description_vector_index import (
    DescriptionVectorIndex,
)
from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.tools.configure import (
    get_files_directory_path,
    get_tools_descriptions_directory,
    get_snippets_descriptions_directory,
    get_skills_descriptions_directory,
    get_vmcp_descriptions_directory,
    configure_logging,
)

try:
    from skillberry_store.fast_api.git_version import __git_version__
except:
    __git_version__ = "unknown"

from skillberry_store.fast_api.observability import (
    observability_setup,
    OTEL_TRACES_PORT,
)
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
        
        # Store description instances in app state for access by admin API
        self.state.tools_descriptions = tools_descriptions_api()
        self.state.snippets_descriptions = snippets_descriptions_api()
        self.state.skills_descriptions = skills_descriptions_api()
        self.state.vmcp_descriptions = vmcp_descriptions_api()
        
        sts_url = f"http://{self.settings.sbs_host}:{self.settings.sbs_port}"
        register_vmcp_api(
            self, sts_url=sts_url, tags="vmcp_servers",
            vmcp_descriptions=self.state.vmcp_descriptions
        )
        register_skills_api(
            self, tags="skills", skills_descriptions=self.state.skills_descriptions
        )
        register_snippets_api(
            self, tags="snippets", snippets_descriptions=self.state.snippets_descriptions
        )
        register_tools_api(self, tags="tools", tools_descriptions=self.state.tools_descriptions)
        register_admin_api(self, tags="admin")

        # Mount MCP server
        mcp_server = FastApiMCP(self)
        mcp_server.mount_sse(mount_path="/control_sse")

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
        if OTEL_TRACES_PORT > 0:
            FastAPIInstrumentor.instrument_app(self)

    def run(self):
        """Starts the FastAPI app using Uvicorn."""
        self.logger.info("Starting SBS server")
        self.logger.info(f"API server running at: http://{self.settings.display_host}:{self.settings.sbs_port}")
        # self.logger.info(f"UI available at: http://localhost:{self.settings.ui_port}")
        self.logger.info(f"API documentation at: http://{self.settings.display_host}:{self.settings.sbs_port}/docs")

        if self.settings.observability:
            observability_setup()
        uvicorn.run(self, host=self.settings.sbs_host, port=self.settings.sbs_port)


def tools_descriptions_api():
    """Initialize tools descriptions APIs with proper persistency/db and APIs.

    Returns:
        Description: Description instance configured with vector index for tools.
    """
    tools_descriptions_directory = get_tools_descriptions_directory()
    tools_descriptions = Description(
        descriptions_directory=tools_descriptions_directory,
        vector_index=DescriptionVectorIndex,
    )
    return tools_descriptions


def snippets_descriptions_api():
    """Initialize snippets descriptions APIs with proper persistency/db and APIs.

    Returns:
        Description: Description instance configured with vector index for snippets.
    """
    snippets_descriptions_directory = get_snippets_descriptions_directory()
    snippets_descriptions = Description(
        descriptions_directory=snippets_descriptions_directory,
        vector_index=DescriptionVectorIndex,
    )
    return snippets_descriptions


def skills_descriptions_api():
    """Initialize skills descriptions APIs with proper persistency/db and APIs.

    Returns:
        Description: Description instance configured with vector index for skills.
    """
    skills_descriptions_directory = get_skills_descriptions_directory()
    skills_descriptions = Description(
        descriptions_directory=skills_descriptions_directory,
        vector_index=DescriptionVectorIndex,
    )
    return skills_descriptions


def vmcp_descriptions_api():
    """Initialize vmcp descriptions APIs with proper persistency/db and APIs.

    Returns:
        Description: Description instance configured with vector index for vmcp servers.
    """
    vmcp_descriptions_directory = get_vmcp_descriptions_directory()
    vmcp_descriptions = Description(
        descriptions_directory=vmcp_descriptions_directory,
        vector_index=DescriptionVectorIndex,
    )
    return vmcp_descriptions


def file_api():
    """Initialize file APIs with proper persistency and APIs.

    Returns:
        FileHandler: File handler instance configured with files directory.
    """
    files_directory_path = get_files_directory_path()
    file_handler = FileHandler(files_directory_path)
    return file_handler


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
