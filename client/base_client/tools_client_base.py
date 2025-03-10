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

        self.logger.debug(f"Base tools client: {self.name} initialized.")


    def _build_url(self, url_path: str, params: dict = {}):
        """
        Builds a full URL starting with the base URL of the client, then the URL path, 
        then the parameters properly encoded using quote()

        Args:
            url_path (str): the path beyond the base URL
            params (dict): parameters that need to be encoded and appended to the URL

        Returns:
            str: the full URL
        """
        url = f"{self.url}{url_path}"
        if params:
            separator = "?"
            for key, value in params.items():
                url = url + f"{separator}{key}=" + quote(value)
                separator = "&"    
        return url


    def _verify_success(self, response: httpx.Response):
        """
        Evaluates the status code returned in the Response object 
        and raises exception if it's not 2XX (success)

        Args:
            response (https.Response): the Response to evaluate

        Returns:
            None

        Raises:
            HTTPStatusError - if the response status code is not success
        """
        if not response.is_success:
            frame = inspect.currentframe().f_back  # Get the caller's frame
            filename = os.path.basename(frame.f_code.co_filename)
            line_number = frame.f_lineno

            self.logger.error(f"HTTP Failure Response: {response.text}\n\tVerification called at line {line_number} in {filename}")
            raise httpx.HTTPStatusError(f"HTTP {response.status_code} Error: {response.text}", request=response.request, response=response)


    # ------- BEGIN 1-1 Server API mapping (internal) ----------

    # @app.get("/manifests/{uid}", tags=tags)
    def _get_manifest(self, uid: str):
        """
        Retrieve manifest for the given uid.

        Parameters:
            uid (str): The uid of the manifest

        Returns:
            dict: The manifest in json format

        Raises:
            HTTPException (404): If manifest not found

        """
        url_obj = self._build_url(url_path="/manifests/" + uid)    

        with httpx.Client() as client:
            response = client.get(
                url_obj,
                headers={"accept": "application/json"}
            )
            self._verify_success(response)
            return response.json()


    # @app.get("/search/manifests", tags=tags)
    def _search_manifest(self,
                        search_term: str,
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
            manifest_filter (str): not used
            lifecycle_state (LifecycleState): state to filter

        Returns:
            list (dict): A list of matched manifests in json format
        """
        params = {
            "search_term": search_term,
            "max_number_of_results": str(max_number_of_results),
            "similarity_threshold": str(similarity_threshold),
            "manifest_filter": manifest_filter,
            "lifecycle_state": lifecycle_state
        }
        url_obj = self._build_url(url_path="/search/manifests", params=params)

        with httpx.Client() as client:
            response = client.get(
                url_obj,
                headers={"accept": "application/json"}
            )
            self._verify_success(response)
            return response.json()


    # @app.post("/manifests/add", tags=tags)
    def _add_manifest(self, file_manifest: str, file: str):
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
        with open(file, "rb") as file_to_upload:
            files = {"file": file_to_upload}
            params = {"file_manifest": file_manifest}
            url_obj = self._build_url(url_path="/manifests/add", params=params)

            with httpx.Client() as client:
                response = client.post(
                    url_obj,
                    files=files,
                    headers={"accept": "application/json"}
                )
                self._verify_success(response)
                return response.json()

    
    # @app.post("/manifests/execute/{uid}", tags=tags)
    def _execute_manifest(self, uid: str, parameters: Optional[Dict[str, Any]] = None):
        """
        Invoke manifest function given its uid.

        Parameters:
            uid (str): The unique identifier of the manifest
            parameters (dict): List of key/val pair to be passed to method invocation (Optional) 

        Returns:
            dict: function output

        Raises:
            HTTPException (404): If manifest not found

        """
        url_obj = self._build_url(url_path="/manifests/execute/" + uid)

        with httpx.Client() as client:
            response = client.post(
                url_obj,
                json=parameters,
                headers={"accept": "application/json"}
            )
            self._verify_success(response)
            return response.json()


    # @app.delete("/manifests/{uid}", tags=tags)
    def _delete_manifest(self, uid: str):
        """
        Delete the manifest removing its description from vector db.

        Parameters:
            dict: manifest deletion message

        Raises:
            HTTPException (404): If manifest not found

        """
        url_obj = self._build_url(url_path="/manifests/" + uid)

        with httpx.Client() as client:
            response = client.delete(
                url_obj,
                headers={"accept": "application/json"}
            )
            self._verify_success(response)
            return response.json()


    # ------- END 1-1 Server API mapping ----------

