import json
import logging
import os
from time import time
from typing import Optional, Dict, Any, Literal, List

import uvicorn

from mcp.server.sse import SseServerTransport
from starlette.routing import Route, Mount

from pydantic_settings import BaseSettings
from pydantic import Field, BaseModel

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from fastapi_mcp import FastApiMCP

from skillberry_store.fast_api.mcp_proxy import MCPToSBSProxy
from skillberry_store.fast_api.skills_api import register_skills_api
from skillberry_store.fast_api.snippets_api import register_snippets_api
from skillberry_store.fast_api.tools_api import register_tools_api
from skillberry_store.fast_api.admin_api import register_admin_api
from skillberry_store.fast_api.vmcp_api import register_vmcp_api
from skillberry_store.modules.dictionary_checker import DictionaryChecker
from skillberry_store.modules.lifecycle import LifecycleState, LifecycleManager
from skillberry_store.modules.manifest import Manifest
from skillberry_store.modules.description import Description
from skillberry_store.modules.description_vector_index import (
    DescriptionVectorIndex,
)
from skillberry_store.modules.file_handler import FileHandler
from skillberry_store.modules.file_executor import FileExecutor
from skillberry_store.modules.tool_type import ToolType
from skillberry_store.tools.configure import (
    get_files_directory_path,
    get_descriptions_directory,
    get_tools_descriptions_directory,
    get_snippets_descriptions_directory,
    get_skills_descriptions_directory,
    get_vmcp_descriptions_directory,
    get_manifest_directory,
    get_snippets_directory,
    configure_logging,
)
from skillberry_store.utils.utils import SKILLBERRY_CONTEXT, unflatten_keys
from skillberry_store.fast_api.server_utils import (
    get_mcp_tools,
    mcp_json_converter,
    mcp_content,
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

# observability - metrics
prom_prefix = "bts_fastapi_"
list_manifests_counter = Counter(
    f"{prom_prefix}list_manifests_counter", "Count number of manifest list operations"
)
delete_manifest_counter = Counter(
    f"{prom_prefix}delete_manifest_counter",
    "Count number of manifest delete operations",
)
update_manifests_counter = Counter(
    f"{prom_prefix}update_manifests_counter",
    "Count number of manifest update operations",
)
add_manifest_counter = Counter(
    f"{prom_prefix}add_manifest_counter", "Count number of manifest delete operations"
)
get_manifest_counter = Counter(
    f"{prom_prefix}get_manifest_counter", "Count number of manifest get operations"
)
get_code_manifest_counter = Counter(
    f"{prom_prefix}get_code_manifest_counter",
    "Count number of manifest get code operations",
)
search_manifest_counter = Counter(
    f"{prom_prefix}search_manifest_counter",
    "Count number of manifest search operations",
)
execute_manifest_counter = Counter(
    f"{prom_prefix}execute_manifest_counter",
    "Count number of manifest execute operations",
    ["uid"],
)
execute_successfully_manifest_counter = Counter(
    f"{prom_prefix}execute_successfully_manifest_counter",
    "Count number of manifest executed successfully operations",
    ["uid"],
)
execute_successfully_manifest_latency = Histogram(
    f"{prom_prefix}execute_successfully_manifest_latency",
    "Histogram of execute manifest successfully latencies",
    ["uid"],
    unit="seconds",
)


class SBSettings(BaseSettings):
    """Configuration settings for the SBS server."""

    bts_host: str = Field("0.0.0.0", env="SBS_HOST")
    bts_port: int = Field(8000, env="SBS_PORT")
    ui_port: int = Field(8002, env="SBS_UI_PORT")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", env="UVICORN_LOG_LEVEL"
    )
    mcp_mode: bool = Field(False, env="MCP_MODE")
    observability: bool = Field(True, env="OBSERVABILITY")


class SBS(FastAPI):
    def __init__(self, **settings: Any):
        """Initialize the SBS server with FastAPI and custom settings."""

        super().__init__()
        self.settings = SBSettings(**settings)
        self.configure_fastapi()
        configure_logging(logging._nameToLevel[self.settings.log_level])
        self.logger = logging.getLogger(__name__)
        
        # Store description instances in app state for access by admin API
        self.state.descriptions = descriptions_api()
        self.state.tools_descriptions = tools_descriptions_api()
        self.state.snippets_descriptions = snippets_descriptions_api()
        self.state.skills_descriptions = skills_descriptions_api()
        self.state.vmcp_descriptions = vmcp_descriptions_api()
        
        self.manifest_api(
            file_handler=file_api(), descriptions=self.state.descriptions, tags=["manifest"]
        )
        sts_url = f"http://{self.settings.bts_host}:{self.settings.bts_port}"
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
        openapi_tags = [
            {
                "name": "manifest",
                "description": "Operations for manifest (tools manifest, programming language, packaging format, "
                "security, etc.)",
            },
            {
                "name": "virtual mcp servers",
                "description": "Operations for Virtual MCP Servers",
            },
            {
                "name": "snippets",
                "description": "Operations for managing text snippets",
            },
        ]

        self.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.openapi = lambda: custom_openapi(self, openapi_tags)

        # Add observability for FastAPI application
        if OTEL_TRACES_PORT > 0:
            FastAPIInstrumentor.instrument_app(self)

    def run(self):
        """Starts the FastAPI app using Uvicorn, and sets up SSE proxy routes if MCP mode is enabled."""
        self.logger.info("Starting SBS server")
        self.logger.info(f"API server running at: http://{self.settings.bts_host}:{self.settings.bts_port}")
        self.logger.info(f"UI available at: http://localhost:{self.settings.ui_port}")
        self.logger.info(f"API documentation at: http://{self.settings.bts_host}:{self.settings.bts_port}/docs")
        if self.settings.mcp_mode:
            self.logger.info("SBS server run in MCP mode with transport SSE")

            proxy = MCPToSBSProxy(self)
            sse = SseServerTransport("/messages/")

            async def handle_sse(request):
                async with sse.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    await proxy.run(
                        streams[0],
                        streams[1],
                        proxy.create_initialization_options(),
                    )

            self.router.routes.append(Route("/sse", endpoint=handle_sse))
            self.router.routes.append(Mount("/messages/", app=sse.handle_post_message))

        if self.settings.observability:
            observability_setup()
        uvicorn.run(self, host=self.settings.bts_host, port=self.settings.bts_port)

    def handle_get_manifests(
        self,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ):
        """Return a list of manifests matching the given lifecycle state and properties filter.

        Args:
            manifest_filter: Manifest properties to filter (Optional).
            lifecycle_state: State to filter (Optional).

        Returns:
            list: A list of matched manifests in json format.
        """
        list_manifests_counter.inc()

        manifest_directory = get_manifest_directory()
        manifest = Manifest(manifest_directory=manifest_directory)
        manifest_as_dict_entities = manifest.list_manifests()

        # if we are requested to limit the search to a specific lifecycle state, we filter the results
        if lifecycle_state is not LifecycleState.ANY:
            matched_manifest_as_dict_entities = []
            for manifest_as_dict in manifest_as_dict_entities:
                life_cycle_manager = LifecycleManager(manifest_as_dict)
                if life_cycle_manager.get_state() != lifecycle_state:
                    continue
                matched_manifest_as_dict_entities.append(manifest_as_dict)
            # update list to only ones matching state
            manifest_as_dict_entities = matched_manifest_as_dict_entities

        if manifest_filter != "" and manifest_filter != ".":
            matched_manifest_as_dict_entities = []
            for manifest_as_dict in manifest_as_dict_entities:
                dictionary_checker = DictionaryChecker(manifest_as_dict)
                if not dictionary_checker.check_key_value_exists(manifest_filter):
                    continue
                matched_manifest_as_dict_entities.append(manifest_as_dict)
            # update list to only ones matching filter attributes
            manifest_as_dict_entities = matched_manifest_as_dict_entities

        return manifest_as_dict_entities

    async def handle_execute_manifest(
        self, uid: str, parameters: Optional[Dict[str, Any]] = None, env_id=None
    ):
        """Invoke manifest function given its uid.

        Args:
            uid: The unique identifier of the manifest.
            parameters: List of key/val pair to be passed to method invocation (Optional).
            env_id: A string representing the environment id to be used for this server (Optional).

        Returns:
            dict: Function output.

        Raises:
            HTTPException: If manifest/tool not found (404).
        """
        logger.info(f"Request to execute manifest: {uid} with parameters: {parameters}")
        execute_manifest_counter.labels(uid=uid).inc()
        start_time = time()

        manifest_directory = get_manifest_directory()
        manifest = Manifest(manifest_directory=manifest_directory)
        file_handler = file_api()
        manifest_as_dict = manifest.read_manifest(f"{uid}.json")
        if not manifest_as_dict:
            raise HTTPException(status_code=404, detail="Manifest/file not found")

        dependent_manifests_as_dict = []
        dependent_file_contents = []

        name = manifest_as_dict["name"]

        # TODO: enum mcp/code
        if manifest_as_dict.get("packaging_format") == "code":

            module_name = manifest_as_dict["module_name"]
            # note: if not found 404 is raised
            content = file_handler.read_file(module_name, raw_content=True)

            def process_manifest(
                manifest_uid, dependent_file_contents, dependent_manifests_as_dict
            ):
                """
                Internal recursive function to iterate though the dependent manifests

                """
                manifest_as_dict = manifest.read_manifest(f"{manifest_uid}.json")
                if not manifest_as_dict:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Manifest/file {manifest_uid}.json not found",
                    )

                if manifest_as_dict.get("packaging_format") != "code":
                    raise ValueError(
                        f"Manifest {manifest_uid} must be from type 'code'"
                    )

                module_name = manifest_as_dict["module_name"]
                # note: if not found 404 is raised
                content = file_handler.read_file(module_name, raw_content=True)

                # code and manifest should be stored under same index
                dependent_file_contents.append(content)
                dependent_manifests_as_dict.append(manifest_as_dict)

                # Recursively process dependent manifests
                dependent_uids = manifest_as_dict.get("dependent_manifest_uids", [])
                for d_uid in dependent_uids:
                    process_manifest(
                        d_uid, dependent_file_contents, dependent_manifests_as_dict
                    )

            dependent_uids = manifest_as_dict.get("dependent_manifest_uids", [])
            for d_uid in dependent_uids:
                process_manifest(
                    d_uid, dependent_file_contents, dependent_manifests_as_dict
                )

        # TODO: enum mcp/code
        if manifest_as_dict.get("packaging_format") == "mcp":
            # ensure the tool exists in mcp
            tools = await get_mcp_tools(manifest_as_dict)
            if not tools:
                raise HTTPException(
                    status_code=404, detail=f"MCP tool '{name}' not found."
                )
            # assert len(tools) == 1, 'More than one tool returned' # TypeError: object of type 'coroutine' has no len()
            tool_dict = vars(tools[0])
            content = mcp_content(tool_dict)

        file_executor = FileExecutor(
            name=name,
            file_content=content,
            file_manifest=manifest_as_dict,
            dependent_file_contents=dependent_file_contents,
            dependent_manifests_as_dict=dependent_manifests_as_dict,
        )
        result = await file_executor.execute_file(parameters=parameters, env_id=env_id)

        duration = time() - start_time
        execute_successfully_manifest_counter.labels(uid=uid).inc()
        execute_successfully_manifest_latency.labels(uid=uid).observe(duration)
        logger.info(f"result {result}")
        return result

    def manifest_api(
        self, file_handler: FileHandler, descriptions: Description, tags: str
    ):
        """Initialize manifest APIs with proper persistency and APIs.

        Args:
            file_handler: File handler instance for file operations.
            descriptions: Description instance for vector database operations.
            tags: FastAPI tags for grouping the endpoints in documentation.
        """
        manifest_directory = get_manifest_directory()
        manifest = Manifest(manifest_directory=manifest_directory)

        @self.get("/manifests/", tags=tags)
        def get_manifests(
            manifest_filter: str = ".",
            lifecycle_state: LifecycleState = LifecycleState.ANY,
        ):
            return self.handle_get_manifests(manifest_filter, lifecycle_state)

        @self.get("/manifests/{uid}", tags=tags)
        def get_manifest(uid: str):
            """Retrieve manifest for the given uid.

            Args:
                uid: The uid of the manifest.

            Returns:
                dict: The manifest in json format.

            Raises:
                HTTPException: If manifest not found (404).
            """
            logger.info(f"Request to read manifest for uid: {uid}")
            get_manifest_counter.inc()

            file_manifest = manifest.read_manifest(f"{uid}.json")
            if file_manifest:
                logger.info(f"Manifest for {uid}: {file_manifest}")
            else:
                raise HTTPException(status_code=404, detail="Manifest not found")
            return file_manifest

        @self.get("/code/manifests/{uid}", tags=tags)
        def get_code_manifest(uid: str):
            """Retrieve manifest code for the given uid.

            Note: supported for 'code' manifests only.

            Args:
                uid: The uid of the manifest.

            Returns:
                str: The manifest code.

            Raises:
                HTTPException: If manifest not from 'code' type (400) or if manifest or code not found (404).
            """
            logger.info(f"Request to read manifest code for uid: {uid}")
            get_code_manifest_counter.inc()

            manifest_as_dict = manifest.read_manifest(f"{uid}.json")
            if manifest_as_dict:
                logger.info(f"Manifest for {uid}: {manifest_as_dict}")
            else:
                raise HTTPException(status_code=404, detail="Manifest not found")
            if manifest_as_dict.get("packaging_format") != "code":
                raise HTTPException(
                    status_code=400, detail="Manifest is not from 'code' type"
                )

            # mandatory to exist
            module_name = manifest_as_dict["module_name"]
            file_content = file_handler.read_file(module_name, raw_content=True)
            if not file_content:
                raise HTTPException(status_code=404, detail="Code not found")

            return {"module_code": file_content}

        @self.get("/search/manifests", tags=tags)
        def search_manifest(
            search_term: str,
            max_number_of_results: int = 5,
            similarity_threshold: float = 1,
            manifest_filter: str = ".",
            lifecycle_state: LifecycleState = LifecycleState.APPROVED,
        ):
            """Return a list of manifests that are similar to the given search term.

            Returns manifests that are below the similarity threshold and match the given lifecycle state.

            Args:
                search_term: Search term.
                max_number_of_results: Number of results to return.
                similarity_threshold: Threshold to be used.
                manifest_filter: Manifest properties to filter.
                lifecycle_state: State to filter.

            Returns:
                list: A list of matched description_vector keys and similarity score.
            """
            logger.info(f"Request to search descriptions for term: {search_term}")
            search_manifest_counter.inc()

            matched_entities = descriptions.search_description(
                search_term=search_term, k=max_number_of_results
            )

            filtered_matched_entities = [
                matched_entity
                for matched_entity in matched_entities
                if matched_entity["similarity_score"] <= similarity_threshold
            ]

            # if we are requested to limit the search to a specific lifecycle state, we filter the results
            if lifecycle_state is not LifecycleState.ANY:
                lifecycle_filtered_matched_entities = []
                for matched_entity in filtered_matched_entities:
                    # description_vector_index uses filename term
                    manifest_as_dict = manifest.read_manifest(
                        f'{matched_entity["filename"]}.json'
                    )
                    if manifest_as_dict is None:
                        continue
                    life_cycle_manager = LifecycleManager(manifest_as_dict)
                    if life_cycle_manager.get_state() != lifecycle_state:
                        continue
                    lifecycle_filtered_matched_entities.append(matched_entity)
                filtered_matched_entities = lifecycle_filtered_matched_entities

            if manifest_filter != "" and manifest_filter != ".":
                manifest_filtered_matched_files = []
                for matched_entity in filtered_matched_entities:
                    manifest_as_dict = manifest.read_manifest(
                        f'{matched_entity["filename"]}.json'
                    )
                    if manifest_as_dict is None:
                        continue
                    dictionary_checker = DictionaryChecker(manifest_as_dict)
                    if not dictionary_checker.check_key_value_exists(manifest_filter):
                        continue
                    manifest_filtered_matched_files.append(matched_entity)
                filtered_matched_entities = manifest_filtered_matched_files

            return filtered_matched_entities

        @self.post("/manifests/generate/{function_name}", tags=tags)
        async def generate_manifest(
            function_name: str,
            json_description: str = None,
            code: Optional[UploadFile] = File(None),
        ):
            """Returns a manifest representation for the given function name.

            TODO: this API will be deprecated and will be removed in future version. Use
            POST /tools/add instead.

            The manifest can either get generated out from the supplied json representation
            of the function or from function module code.

            Args:
                function_name: The name of the function.
                json_description: The description of the function in a json format.
                code: The module code.

            Returns:
                dict: Manifest representation.
            """
            manifest_as_dict = manifest.print_manifest(
                function_name,
                json_description=json_description,
                code=code.file.read() if code else None,
            )

            return manifest_as_dict

        @self.post("/manifests/add", tags=tags)
        async def add_manifest(
            file_manifest: str, file: Optional[UploadFile] = File(None)
        ):
            """Adds manifest.

            NOTE: this API will be considered to be deprecated and planed to be removed
            in future version.

            Two types of manifests are supported: code and mcp.
            - code: manifest points to corresponding method in a file module
            - mcp:  manifest points to corresponding tool in a mcp server

            As part of the addition, the description of the manifest is being embedded and
            stored in vector db. The manifest is assigned with a unique identifier.

            Args:
                file_manifest: The manifest of the file (json format).
                file: The file containing invocation code. Not applicable for manifest from type mcp.

            Returns:
                dict: The unique identifier of the manifest.

            Raises:
                HTTPException: If mcp tool not found for this manifest (404) or if manifest already exist (409).
            """
            logger.info(f"Request to add manifest")
            add_manifest_counter.inc()

            manifest_as_dict = json.loads(file_manifest)
            name = manifest_as_dict["name"]

            manifest_as_dict_entities = manifest.list_manifests()
            if list(filter(lambda m: m["name"] == name, manifest_as_dict_entities)):
                raise HTTPException(
                    status_code=409, detail=f"Manifest '{name}' already exists."
                )

            # TODO: generate UID
            uid = name
            manifest_as_dict["uid"] = uid

            # TODO: enum mcp/code

            if manifest_as_dict.get("packaging_format") == "mcp":
                if not manifest_as_dict.get("mcp_url"):
                    raise HTTPException(
                        status_code=400, detail=f"Missing 'mcp_url' in manifest."
                    )
                if "dependent_manifest_uids" in manifest_as_dict:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Manifest that depends on other manifests "
                        "is not supported for 'packaging_format' == mcp.",
                    )

                # error if tool does not exist in mcp
                tools = await get_mcp_tools(manifest_as_dict)
                if not tools:
                    raise HTTPException(
                        status_code=404, detail=f"MCP tool '{name}' not found."
                    )
                if len(tools) != 1:
                    logger.warning(f"More than one MCP tool '{name}' found.")

                tool_dict = vars(tools[0])
                _manifest_as_dict = mcp_json_converter(tool_dict, manifest_as_dict)
                manifest_as_dict.update(**_manifest_as_dict)

            if manifest_as_dict.get("packaging_format") == "code":
                module_name = manifest_as_dict["module_name"]
                file_handler.write_file(file.file.read(), filename=module_name)

            manifest.write_manifest(f"{uid}.json", manifest_as_dict)
            # TODO: in current version name == uid
            descriptions.write_description(name, manifest_as_dict["description"])

            return {"uid": manifest_as_dict["uid"]}

        @self.post("/manifests/execute/{uid}", tags=tags)
        async def execute_manifest(
            uid: str, request: Request, parameters: Optional[Dict[str, Any]] = None
        ):
            """Invoke manifest function given its uid.

            Args:
                uid: The unique identifier of the manifest.
                request: Represents an incoming fast api request object.
                parameters: List of key/val pair to be passed to method invocation (Optional).

            Returns:
                dict: Function output.

            Raises:
                HTTPException: If manifest/tool not found (404).

            """
            # TODO: BEGIN common skillberry library
            headers = request.headers
            logging.info("!!!!!!!!!!!!!!!!!")
            logging.info(f"headers: {headers}")
            logging.info("!!!!!!!!!!!!!!!!!")

            skillberry_context = unflatten_keys(headers).get(SKILLBERRY_CONTEXT.lower())
            logging.info(f"@@@@@@@@@@@@@@@@")
            logging.info(f"skillberery_context: {skillberry_context}")
            logging.info(f"@@@@@@@@@@@@@@@@")
            # TODO: END common skillberry library

            env_id = (
                skillberry_context.get("env_id")
                if skillberry_context is not None
                else None
            )

            return await self.handle_execute_manifest(uid, parameters, env_id=env_id)

        @self.post("/manifests/update/{uid}", tags=tags)
        def update_manifest(uid: str, new_manifest: Dict[str, Any]):
            """Update the manifest for the given uid.

            Args:
                uid: The uid of the manifest.
                new_manifest: The new manifest to update with.

            Returns:
                dict: Manifest update message.

            Raises:
                HTTPException: If manifest not found (404).
            """
            logger.info(f"Request to update manifest for uid: {uid}")
            update_manifests_counter.inc()
            #
            # This logic should be revised:
            # there are cases where new_manifest does not contain uid
            # especially when being passed from btm. btm git issue #45 opened to
            # handle this.
            #
            new_manifest["uid"] = uid
            return manifest.update_manifest(f"{uid}.json", new_manifest)

        @self.delete("/manifests/", tags=tags)
        def delete_manifests(
            manifest_filter: str = ".",
            lifecycle_state: LifecycleState = LifecycleState.ANY,
        ):
            """Delete the manifests removing their descriptions from vector db.

            Args:
                manifest_filter: Manifest properties to filter (Optional).
                lifecycle_state: State to filter (Optional).

            Returns:
                dict: Manifest deletion message with a list of deleted manifest uids.
            """
            logger.info(f"Request to delete manifests")
            manifest_as_dict_entities = manifest.list_manifests()
            # if we are requested to limit delete to a specific lifecycle state, we filter the results
            if lifecycle_state is not LifecycleState.ANY:
                matched_manifest_as_dict_entities = []
                for manifest_as_dict in manifest_as_dict_entities:
                    life_cycle_manager = LifecycleManager(manifest_as_dict)
                    if life_cycle_manager.get_state() != lifecycle_state:
                        continue
                    matched_manifest_as_dict_entities.append(manifest_as_dict)
                # update list to only ones matching state
                manifest_as_dict_entities = matched_manifest_as_dict_entities

            if manifest_filter != "" and manifest_filter != ".":
                matched_manifest_as_dict_entities = []
                for manifest_as_dict in manifest_as_dict_entities:
                    dictionary_checker = DictionaryChecker(manifest_as_dict)
                    if not dictionary_checker.check_key_value_exists(manifest_filter):
                        continue
                    matched_manifest_as_dict_entities.append(manifest_as_dict)
                # update list to only ones matching filter attributes
                manifest_as_dict_entities = matched_manifest_as_dict_entities
            success_deleted = []
            for m in manifest_as_dict_entities:
                uid = m["uid"]
                try:
                    delete_manifest(uid)
                    success_deleted.append(uid)
                except Exception as e:
                    logger.warning(f"Failed to delete manifest {uid}: {str(e)}")

            return {"message": f"Manifests {success_deleted} deleted."}

        @self.delete("/manifests/{uid}", tags=tags)
        def delete_manifest(uid: str):
            """Delete the manifest removing its description from vector db.

            Args:
                uid: The uid of the manifest.

            Returns:
                dict: Manifest deletion message.

            Raises:
                HTTPException: If manifest not found (404).
            """
            logger.info(f"Request to delete manifest: {uid}")
            delete_manifest_counter.inc()

            manifest_as_dict = manifest.read_manifest(f"{uid}.json")
            if not manifest_as_dict:
                raise HTTPException(status_code=404, detail="Manifest not found")

            name = manifest_as_dict["name"]
            try:
                descriptions.delete_description(name)
            except Exception as e:
                # just log and continue
                logger.warning(f"Failed to delete description: {e}")
            try:
                manifest.delete_manifest(f"{uid}.json")
            except Exception as e:
                # just log and continue
                logger.warning(f"Failed to delete manifest: {e}")

            return {"message": f"Manifest '{uid}' deleted."}


def descriptions_api():
    """Initialize descriptions APIs with proper persistency/db and APIs.

    Returns:
        Description: Description instance configured with vector index.
    """
    descriptions_directory = get_descriptions_directory()
    descriptions = Description(
        descriptions_directory=descriptions_directory,
        vector_index=DescriptionVectorIndex,
    )
    return descriptions


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

    app.openapi_schema = openapi_schema
    return app.openapi_schema
