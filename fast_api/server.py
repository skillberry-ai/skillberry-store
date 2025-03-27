import asyncio
import json
import logging
import os
import re
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from modules.dictionary_checker import DictionaryChecker
from modules.lifecycle import LifecycleState, LifecycleManager
from modules.manifest import Manifest
from modules.description import Description
from modules.description_vector_index import DescriptionVectorIndex
from modules.file_handler import FileHandler
from modules.file_executor import FileExecutor
from tools.configure import get_files_directory_path, get_descriptions_directory, \
    get_manifest_directory
from fast_api.server_utils import get_mcp_tools, mcp_json_converter, mcp_content


# this environment variable is used to enable the latest API version
ENABLE_API_VERSION = os.environ.get('ENABLE_API_VERSION', 'latest')

logger = logging.getLogger(__name__)


def manifest_api(app, file_handler: FileHandler, descriptions: Description, tags: str):
    """
    Initialize manifest apis with proper persistency and APIs.

    """
    manifest_directory = get_manifest_directory()
    manifest = Manifest(manifest_directory=manifest_directory)

    @app.get("/manifests", tags=tags)
    def get_manifests(manifest_filter: str = ".",
                      lifecycle_state: LifecycleState = LifecycleState.ANY):
        """
        Return a list of manifests matching the given lifecycle state and properties filter.

        Parameters:
            manifest_filter (str): manifest properties to filter (Optional)
            lifecycle_state (LifecycleState): state to filter (Optional)

        Returns:
            list (dict): A list of matched manifests in json format

        """
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

    @app.get("/manifests/{uid}", tags=tags)
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
        file_manifest = manifest.read_manifest(f'{uid}.json')
        if file_manifest:
            logger.info(f"Manifest for {uid}: {file_manifest}")
        else:
            raise HTTPException(status_code=404, detail="Manifest not found")
        return file_manifest

    @app.get("/code/manifests/{uid}", tags=tags)
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
        manifest_as_dict = manifest.read_manifest(f'{uid}.json')
        if manifest_as_dict:
            logger.info(f"Manifest for {uid}: {manifest_as_dict}")
        else:
            raise HTTPException(status_code=404, detail="Manifest not found")
        if manifest_as_dict.get("packaging_format") != "code":
            raise HTTPException(status_code=400, detail="Manifest is not from 'code' type")

        # mandatory to exist
        module_name = manifest_as_dict['module_name']
        file_content = file_handler.read_file(module_name, raw_content=True)
        if not file_content:
            raise HTTPException(status_code=404, detail="Code not found")

        return {'module_code': file_content}

    @app.get("/search/manifests", tags=tags)
    def search_manifest(search_term: str,
                        max_number_of_results: int = 5,
                        similarity_threshold: float = 1,
                        manifest_filter: str = ".",
                        lifecycle_state: LifecycleState = LifecycleState.APPROVED):
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
        matched_entities = descriptions.search_description(
            search_term=search_term,
            k=max_number_of_results)

        filtered_matched_entities = [matched_entity for matched_entity in matched_entities if
                                     matched_entity["similarity_score"] <= similarity_threshold]

        # if we are requested to limit the search to a specific lifecycle state, we filter the results
        if lifecycle_state is not LifecycleState.ANY:
            lifecycle_filtered_matched_entities = []
            for matched_entity in filtered_matched_entities:
                # description_vector_index uses filename term
                manifest_as_dict = manifest.read_manifest(f'{matched_entity["filename"]}.json')
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
                manifest_as_dict = manifest.read_manifest(f'{matched_entity["filename"]}.json')
                if manifest_as_dict is None:
                    continue
                dictionary_checker = DictionaryChecker(manifest_as_dict)
                if not dictionary_checker.check_key_value_exists(manifest_filter):
                    continue
                manifest_filtered_matched_files.append(matched_entity)
            filtered_matched_entities = manifest_filtered_matched_files

        return filtered_matched_entities

    @app.post("/manifests/add", tags=tags)
    async def add_manifest(file_manifest: str, file: Optional [UploadFile] = File(None)):
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

        manifest_as_dict = json.loads(file_manifest)
        name = manifest_as_dict['name']

        manifest_as_dict_entities = manifest.list_manifests()
        if list(filter(lambda m: m['name'] == name, manifest_as_dict_entities)):
            raise HTTPException(status_code=409, detail=f"Manifest '{name}' already exists.")

        # TODO: generate UID
        uid = name
        manifest_as_dict['uid'] = uid

        # TODO: enum mcp/code

        if manifest_as_dict.get("packaging_format") == "mcp":
            if not manifest_as_dict.get('mcp_url'):
                raise HTTPException(status_code=400, detail=f"Missing 'mcp_url' in manifest.") 

            # error if tool does not exist in mcp
            tools = await get_mcp_tools(manifest_as_dict)
            if not tools:
                raise HTTPException(status_code=404, detail=f"MCP tool '{name}' not found.")
            if len(tools) != 1:
                logger.warning(f"More than one MCP tool '{name}' found.")

            tool_dict = vars(tools[0])
            _manifest_as_dict = mcp_json_converter(tool_dict, manifest_as_dict)
            manifest_as_dict.update(**_manifest_as_dict)

        if manifest_as_dict.get("packaging_format") == "code":
            module_name = manifest_as_dict['module_name']
            file_handler.write_file(file, filename=module_name)

        manifest.write_manifest(f'{uid}.json', manifest_as_dict)
        # TODO: in current version name == uid
        descriptions.write_description(name, manifest_as_dict['description'])

        return {'uid': manifest_as_dict['uid']}

    @app.post("/manifests/execute/{uid}", tags=tags)
    def execute_manifest(uid: str, parameters: Optional[Dict[str, Any]] = None):
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
        manifest_as_dict = manifest.read_manifest(f'{uid}.json')
        if not manifest_as_dict:
            raise HTTPException(status_code=404, detail="Manifest/file not found")

        name = manifest_as_dict["name"]
        # TODO: enum mcp/code
        if manifest_as_dict.get("packaging_format") == "code":
            module_name = manifest_as_dict['module_name']
            # note: if not found 404 is raised
            content = file_handler.read_file(module_name, raw_content=True)

        # TODO: enum mcp/code
        if manifest_as_dict.get("packaging_format") == "mcp":
            # ensure the tool exists in mcp
            tools = asyncio.run(get_mcp_tools(manifest_as_dict))
            if not tools:
                raise HTTPException(status_code=404, detail=f"MCP tool '{name}' not found.")
            # assert len(tools) == 1, 'More than one tool returned' # TypeError: object of type 'coroutine' has no len()
            tool_dict = vars(tools[0])
            content = mcp_content(tool_dict)

        file_executor = FileExecutor(
            name=name, file_content=content, file_manifest=manifest_as_dict)

        return file_executor.execute_file(parameters=parameters)

    @app.delete("/manifests/{uid}", tags=tags)
    def delete_manifest(uid: str):
        """
        Delete the manifest removing its description from vector db.

        Parameters:
            dict: manifest deletion message

        Raises:
            HTTPException (404): If manifest not found

        """
        logger.info(f"Request to delete manifest: {uid}")
        manifest_as_dict = manifest.read_manifest(f'{uid}.json')
        if not manifest_as_dict:
            raise HTTPException(status_code=404, detail="Manifest not found")

        name = manifest_as_dict['name']
        try:
            descriptions.delete_description(name)
        except Exception as e:
            # just log and continue
            logger.warning(f"Failed to delete description: {e}")
        try:
            manifest.delete_manifest(f'{uid}.json')
        except Exception as e:
            # just log and continue
            logger.warning(f"Failed to delete manifest: {e}")

        return {"message": f"Manifest '{uid}' deleted."}


def descriptions_api():
    """
    Initialize descriptions apis with proper persistency/db and APIs.

    """
    descriptions_directory = get_descriptions_directory()
    descriptions = Description(descriptions_directory=descriptions_directory,
                               vector_index=DescriptionVectorIndex)
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
        version="0.0.1",
        tags=openapi_tags,
        contact={
            "name": "Eran Raichstein",
            "email": "eranra@il.ibm.com",
        },
        routes=app.routes,
    )

    for path, methods in openapi_schema["paths"].items():
        for method in methods.keys():  # e.g., "get", "post"
            if method in ["get", "post", "put", "delete", "patch"]:  # Only HTTP methods
                url = f"http://127.0.0.1:8000{path}"

                python_example_requests = f"""import requests

response = requests.{method}("{url}")
print(response.json())"""

                curl_example = f"""curl -X {method.upper()} "{url}" """

                example_obj = {
                    "python_requests": {
                        "summary": "Python (requests)",
                        "value": python_example_requests
                    },
                    "curl": {
                        "summary": "cURL example",
                        "value": curl_example
                    }
                }

                # Add examples to the responses
                if "responses" in methods[method]:
                    methods[method]["responses"]["200"]["content"] = {
                        "text/plain": {
                            "examples": example_obj
                        }
                    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_app():
    openapi_tags = [
        {
            "name": "manifest",
            "description": "Operations for manifest (tools manifest, programming language, packaging format, "
                           "security, etc.)",
        }
    ]

    # app = FastAPI()
    # replacing non-versioned FastAPI with versioned FastAPI
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    descriptions = descriptions_api()
    file_handler = file_api()
    manifest_api(app=app, file_handler=file_handler, descriptions=descriptions, tags=["manifest"])
    app.openapi = lambda: custom_openapi(app, openapi_tags)
    return app
