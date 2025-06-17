import json
import logging
import os
from time import time

import uvicorn

from mcp.server.sse import SseServerTransport
from starlette.routing import Route, Mount

from typing import Optional, Dict, Any, Literal
from pydantic_settings import BaseSettings
from pydantic import Field

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from fast_api.mcp_proxy import MCPToBTSProxy
from modules.dictionary_checker import DictionaryChecker
from modules.lifecycle import LifecycleState, LifecycleManager
from modules.manifest import Manifest
from modules.description import Description
from modules.description_vector_index import DescriptionVectorIndex
from modules.file_handler import FileHandler
from modules.file_executor import FileExecutor
from tools.configure import (
    get_files_directory_path,
    get_descriptions_directory,
    get_manifest_directory,
    configure_logging,
)
from fast_api.server_utils import get_mcp_tools, mcp_json_converter, mcp_content

try:
    from fast_api.git_version import __git_version__
except:
    __git_version__ = "unknown"

from fast_api.observability import observability_setup
from prometheus_client import Counter, Histogram

# this environment variable is used to enable the latest API version
ENABLE_API_VERSION = os.environ.get("ENABLE_API_VERSION", "latest")

logger = logging.getLogger(__name__)

observability_setup()

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


class BTSettings(BaseSettings):
    """Configuration settings for the BTS server."""

    bts_host: str = Field("0.0.0.0", env="BTS_HOST")
    bts_port: int = Field(8000, env="BTS_PORT")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", env="UVICORN_LOG_LEVEL"
    )
    mcp_mode: bool = Field(False, env="MCP_MODE")


class BTS(FastAPI):
    def __init__(self, **settings: Any):
        """Initialize the BTS server with FastAPI and custom settings."""

        super().__init__()
        self.settings = BTSettings(**settings)
        self.configure_fastapi()
        configure_logging(logging._nameToLevel[self.settings.log_level])
        self.logger = logging.getLogger(__name__)
        self.manifest_api(
            file_handler=file_api(), descriptions=descriptions_api(), tags=["manifest"]
        )

    def configure_fastapi(self):
        """Configures CORS middleware and OpenAPI documentation settings."""
        openapi_tags = [
            {
                "name": "manifest",
                "description": "Operations for manifest (tools manifest, programming language, packaging format, "
                "security, etc.)",
            }
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
        FastAPIInstrumentor.instrument_app(self)

    def run(self):
        """Starts the FastAPI app using Uvicorn, and sets up SSE proxy routes if MCP mode is enabled."""
        self.logger.info("Starting BTS server")
        if self.settings.mcp_mode:
            self.logger.info("BTS server run in MCP mode with transport SSE")

            proxy = MCPToBTSProxy(self)
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

        uvicorn.run(self, host=self.settings.bts_host, port=self.settings.bts_port)

    def handle_get_manifests(
        self,
        manifest_filter: str = ".",
        lifecycle_state: LifecycleState = LifecycleState.ANY,
    ):
        """
        Return a list of manifests matching the given lifecycle state and properties filter.

        Parameters:
            manifest_filter (str): manifest properties to filter (Optional)
            lifecycle_state (LifecycleState): state to filter (Optional)

        Returns:
            list (dict): A list of matched manifests in json format

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
        self, uid: str, parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Invoke manifest function given its uid.

        Parameters:
            uid (str): The unique identifier of the manifest
            parameters (dict): List of key/val pair to be passed to method invocation (Optional)

        Returns:
            dict: function output

        Raises:
            HTTPException (404): If manifest/tool not found

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

        name = manifest_as_dict["name"]
        # TODO: enum mcp/code
        if manifest_as_dict.get("packaging_format") == "code":
            module_name = manifest_as_dict["module_name"]
            # note: if not found 404 is raised
            content = file_handler.read_file(module_name, raw_content=True)

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
            name=name, file_content=content, file_manifest=manifest_as_dict
        )
        result = await file_executor.execute_file(parameters=parameters)

        duration = time() - start_time
        execute_successfully_manifest_counter.labels(uid=uid).inc()
        execute_successfully_manifest_latency.labels(uid=uid).observe(duration)
        logger.info(f"result {result}")
        return result

    def manifest_api(
        self, file_handler: FileHandler, descriptions: Description, tags: str
    ):
        """
        Initialize manifest apis with proper persistency and APIs.

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
            """
            Retrieve manifest for the given uid.

            Parameters:
                uid (str): The uid of the manifest

            Returns:
                dict: The manifest in json format

            Raises:
                HTTPException (404): If manifest not found

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
            """
            Retrieve manifest code for the given uid.

            Note: supported for 'code' manifests only.

            Parameters:
                uid (str): The uid of the manifest

            Returns:
                str: The manifest code

            Raises:
                HTTPException (400): If manifest not from 'code' type
                HTTPException (404): If manifest or code not found

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
            """
            Return a list of manifests that are similar to the given search term and are below the
            similarity threshold matching the given lifecycle state.

            Parameters:
                search_term (str): search term
                max_number_of_results (int): number of results to return
                similarity_threshold (float): threshold to be used
                manifest_filter (str): manifest properties to filter
                lifecycle_state (LifecycleState): state to filter

            Returns:
                list (dict): A list of matched description_vector keys and
                            similarity score

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
            """
            Returns a manifest representation for the given function name.

            The manifest can either get generated out from the supplied json representation
            of the function or from function module code.

            Parameters:
                function_name (str): The name of the function
                json_description (str): The description of the function in a json format
                code (UploadFile): The module code

            Returns:
                dict: manifest representation

            """
            manifest_as_dict = manifest.generate_manifest(
                function_name,
                json_description=json_description,
                code=code.file.read() if code else None,
            )

            return manifest_as_dict

        @self.post("/manifests/add", tags=tags)
        async def add_manifest(
            file_manifest: str, file: Optional[UploadFile] = File(None)
        ):
            """
            Adds manifest.

            Two types of manifests are supported: code and mcp.

            - code: manifest points to corresponding method in a file module
            - mcp:  manifest points to corresponding tool in a mcp server

            As part of the addition, the description of the manifest is being embedded and
            stored in vector db.

            The manifest is assigned with a unique identifier.

            Parameters:
                file_manifest (str): The manifest of the file (json format).
                file (UploadFile): The file containing invocation code. Not applicable for
                                manifest from type mcp

            Returns:
                dict: The unique identifier of the manifest

            Raises:
                HTTPException (404): If mcp tool not found for this manifest
                HTTPException (409): If manifest already exist

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
                file_handler.write_file(file, filename=module_name)

            manifest.write_manifest(f"{uid}.json", manifest_as_dict)
            # TODO: in current version name == uid
            descriptions.write_description(name, manifest_as_dict["description"])

            return {"uid": manifest_as_dict["uid"]}

        @self.post("/manifests/execute/{uid}", tags=tags)
        async def execute_manifest(
            uid: str, parameters: Optional[Dict[str, Any]] = None
        ):
            """
            Invoke manifest function given its uid.

            Parameters:
                uid (str): The unique identifier of the manifest
                parameters (dict): List of key/val pair to be passed to method invocation (Optional)

            Returns:
                dict: function output

            Raises:
                HTTPException (404): If manifest/tool not found

            """
            return await self.handle_execute_manifest(uid, parameters)

        @self.post("/manifests/update/{uid}", tags=tags)
        def update_manifest(uid: str, new_manifest: Dict[str, Any]):
            """
            Update the manifest for the given uid.

            Parameters:
                uid (str): The uid of the manifest
                new_manifest (dict): the new manifest to update with

            Returns:
                dict: manifest update message

            Raises:
                HTTPException (404): If manifest not found

            """
            logger.info(f"Request to update manifest for uid: {uid}")
            update_manifests_counter.inc()
            return manifest.update_manifest(f"{uid}.json", new_manifest)

        @self.delete("/manifests/{uid}", tags=tags)
        def delete_manifest(uid: str):
            """
            Delete the manifest removing its description from vector db.

            Parameters:
                uid (str): The uid of the manifest

            Returns:
                dict: manifest deletion message

            Raises:
                HTTPException (404): If manifest not found

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
    """
    Initialize descriptions apis with proper persistency/db and APIs.

    """
    descriptions_directory = get_descriptions_directory()
    descriptions = Description(
        descriptions_directory=descriptions_directory,
        vector_index=DescriptionVectorIndex,
    )
    return descriptions


def file_api():
    """
    Initialize file apis with proper persistency and APIs.

    """
    files_directory_path = get_files_directory_path()
    file_handler = FileHandler(files_directory_path)
    return file_handler


def custom_openapi(app: FastAPI, openapi_tags):
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="blueberry",
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
