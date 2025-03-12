# A basic client for the tools service

from tools.configure import configure_logger
import logging
from client.base_client import base_client_utils
from typing import Any, Dict, List, Optional
import os, sys
import httpx
import json
from urllib.parse import quote
from modules.lifecycle import LifecycleState
import inspect

# Generator-specific imports
import openapi_client
import openapi_client.models.lifecycle_state as lcs
from openapi_client.rest import ApiException


class ToolsClientBase:

    def __init__(self, name="MyToolsClient", log_level=logging.DEBUG, url="http://0.0.0.0:8000"):
        """
        Constructor - Initializes a tools client instance.

        Args:
            name (str): The name of the tools client.
            log_level (int): The logging level.
            url (string): URL of the service endpoint the client connects to

        Returns:
            ToolsClient - a new ToolsClient instance
        """
        self.name = name
        self.logger = configure_logger(self.name, log_level=log_level)
        self.url = url
        self.configuration = openapi_client.Configuration(
            host = "http://0.0.0.0:8000"
        )

        self.logger.debug(f"Base tools client: {self.name} initialized.")


    # ------- BEGIN 1-1 Server API mapping (internal) ----------

    # @app.get("/manifests", tags=tags)
    def get_manifests(self, manifest_filter: str = ".",
                      lifecycle_state: LifecycleState = LifecycleState.ANY) -> List[Dict]:
        """
        Return a list of manifests matching the given lifecycle state and properties filter.

        Parameters:
            manifest_filter (str): manifest properties to filter (Optional)
            lifecycle_state (LifecycleState): state to filter (Optional)

        Returns:
            list (dict): A list of matched manifests in json format

        """
        response = None
        with openapi_client.ApiClient(self.configuration) as api_client:
            api_instance = openapi_client.ManifestApi(api_client)
            response = api_instance.get_manifests_manifests_get_with_http_info(manifest_filter, lcs.LifecycleState(lifecycle_state))
        return json.loads(response.raw_data)


    # @app.get("/manifests/{uid}", tags=tags)
    def get_manifest(self, uid: str) -> Dict:
        """
        Retrieve manifest for the given uid.

        Parameters:
            uid (str): The uid of the manifest

        Returns:
            dict: The manifest 

        Raises:
            Exception: If call error or manifest not found

        """
        response = None
        with openapi_client.ApiClient(self.configuration) as api_client:
            api_instance = openapi_client.ManifestApi(api_client)
            response = api_instance.get_manifest_manifests_uid_get_with_http_info(uid)
        return json.loads(response.raw_data)


    # @app.get("/code/manifests/{uid}", tags=tags)
    def get_code_manifest(self, uid: str):
        """
        Retrieve manifest code for the given uid.

        Parameters:
            uid (str): The uid of the manifest

        Returns:
            str: The manifest code

        Raises:
            Exception: If manifest or code not found
        """
        response = None
        with openapi_client.ApiClient(self.configuration) as api_client:
            api_instance = openapi_client.ManifestApi(api_client)
            response = api_instance.get_code_manifest_code_manifests_uid_get_with_http_info(uid)
        return json.loads(response.raw_data)


    # @app.get("/search/manifests", tags=tags)
    def search_manifest(self,
                        search_term: str,
                        max_number_of_results: int = 5,
                        similarity_threshold: float = 1,
                        manifest_filter: str = ".",
                        lifecycle_state: LifecycleState = LifecycleState.APPROVED) -> List[Dict]:
        """
        Return a list of manifests that are similar to the given search term and are below the
        similarity threshold matching the given lifecycle state.

        Parameters:
            search_term (str): search term
            max_number_of_results (int): number of results to return
            similarity_threshold (float): threshold to be used
            manifest_filter (str): not used
            lifecycle_state (LifecycleState): state to filter

        Returns:
            List[Dict]: A list of matched manifests
        """
        response = None
        with openapi_client.ApiClient(self.configuration) as api_client:
            api_instance = openapi_client.ManifestApi(api_client)
            response = api_instance.search_manifest_search_manifests_get_with_http_info(
                search_term,
                max_number_of_results,
                similarity_threshold,
                manifest_filter,
                lcs.LifecycleState(lifecycle_state)
            )
        return json.loads(response.raw_data)


    # @app.post("/manifests/add", tags=tags)
    def add_manifest(self, file_manifest: str, file: str):
        """
        Adds manifest along with its invocation code. As part of the addition,
        the description of the manifest is embedded and stored in vector db.

        The manifest is assigned with a unique identifier.

        Parameters:
            file_manifest (str): The manifest of the file (json format).
            file (str): The file path containing invocation code.

        Returns:
            dict: The unique identifier of the manifest
        """
        response = None
        file_blob = base_client_utils.read_file_to_bytes(file)
        with openapi_client.ApiClient(self.configuration) as api_client:
            api_instance = openapi_client.ManifestApi(api_client)
            response = api_instance.add_manifest_manifests_add_post_with_http_info(file_manifest, file_blob)
        return json.loads(response.raw_data)

    
    # @app.post("/manifests/execute/{uid}", tags=tags)
    def execute_manifest(self, uid: str, parameters: Optional[Dict[str, Any]] = None):
        """
        Invoke manifest function given its uid.

        Parameters:
            uid (str): The unique identifier of the manifest
            parameters (dict): List of key/val pair to be passed to method invocation (Optional) 

        Returns:
            dict: function output

        Raises:
            Exception: If manifest not found

        """
        response = None
        with openapi_client.ApiClient(self.configuration) as api_client:
            api_instance = openapi_client.ManifestApi(api_client)
            response = api_instance.execute_manifest_manifests_execute_uid_post_with_http_info(uid=uid, body=parameters)
        return json.loads(response.raw_data)


    # @app.delete("/manifests/{uid}", tags=tags)
    def delete_manifest(self, uid: str):
        """
        Delete the manifest removing its description from vector db.

        Parameters:
            dict: manifest deletion message

        Raises:
            Exception: If manifest not found

        """
        response = None
        with openapi_client.ApiClient(self.configuration) as api_client:
            api_instance = openapi_client.ManifestApi(api_client)
            response = api_instance.delete_manifest_manifests_uid_delete_with_http_info(uid)
        return json.loads(response.raw_data)

    # ------- END 1-1 Server API mapping ----------

