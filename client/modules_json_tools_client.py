# A client for the tools service that creates tools from Python modules with possibly external documentation in JSON format.

from tools.configure import configure_logger
import logging
from typing import Any, Dict, List, Optional
import os, sys
import httpx
import json
from urllib.parse import quote
from modules.lifecycle import LifecycleState
import inspect
from client.utils import base_client_utils
from client.utils import json_client_utils
from client.base_client.tools_client_base import ToolsClientBase

class ModulesJsonToolsClient(ToolsClientBase):

    def __init__(self, name="MyModulesJsonToolsClient", log_level=logging.DEBUG, url="http://0.0.0.0:8000", json_path: str = None):
        """
        Constructor - Initializes a tools client instance.

        Args (optional):
            name (str): The name of the tools client.
            log_level (int): The logging level.
            url (str): URL of the service endpoint the client connects to
            json_path (str): path to a JSON base to load

        Returns:
            ModulesJsonToolsClient - a new instance
        """
        super().__init__(name, log_level, url)
        self.json_base = None
        if json_path:
            self.set_json_base(json_path)

        self.logger.info(f"Tools client: {self.name} initialized.")


    def set_json_base(self, json_path: str):
        """
        Set the JSON base of descriptions (DOT format) using the given path.
        This operation replaces any previous JSON base.

        Args:
            json_path (str): the path to the folder containing the JSON descriptions

        Returns:
            None
        """
        self.json_path=json_path
        self.json_base = json_client_utils.load_json_base(json_path)
        self.logger.debug(f"Loaded JSON base from: {json_path}")


    # ------- BEGIN client API --------

    def list_tools(self, manifest_filter: str = ".", lifecycle_state: LifecycleState = LifecycleState.ANY) -> List[Dict]:
        """
        Retrieve a list of manifests of stored tools according to criteria

        Args:
            filter (str): a JSON filter of criteria, jq format. Default: all 
            lifecycle_state (LifeCycleState): filter on the life cycle state. Default: any

        Returns:
            List[Dict]: List of matching manifests
        """
        self.logger.debug(f"Listing tool manifests with criteria:\n\tManifest Filter: {manifest_filter}\n\tLifecycle State: {lifecycle_state}")
        response = self.get_manifests(manifest_filter, lifecycle_state)
        self.logger.debug(f"Service response: \n{base_client_utils.json_pretty_print(response)}")
        return response    
    
    
    def get_tool_manifest(self, uid: str):
        """
        Retrieve the manifest of a stored tool based on the tool UID

        Args:
            uid (str): the unique id of the tool (e.g., as returned from adding the tool, listing tools, etc)

        Returns:
            str: the JSON manifest of the tool if the tool exists
        """
        self.logger.debug(f"Retrieving tool manifest for UID: {uid}")
        response = self.get_manifest(uid)
        self.logger.debug(f"Service response: \n{base_client_utils.json_pretty_print(response)}")
        return response    


    def get_tool_code(self, uid: str) -> str:
        """
        Retrieve code for the given tool uid.

        Parameters:
            uid (str): The uid of the tool

        Returns:
            str: The tool code (single code module)

        Raises:
            Exception: If tool or code not found
        """
        self.logger.debug(f"Retrieving tool code for UID: {uid}")
        response = self.get_code_manifest(uid)
        self.logger.debug(f"Service response: \n{base_client_utils.json_pretty_print(response)}")
        return response["module_code"]   


    def search_tools(self,
                    description: str,
                    max_number_of_results: int = 5,
                    similarity_threshold: float = 1.0,
                    lifecycle_state: LifecycleState = LifecycleState.APPROVED):
        """
        Return a list of tool manifests that are similar to the given description.
        Optional filters for results:
         - maximum number of results (default: 5)
         - max distance threshold for similarity (default: 1.0) 
         - Life Cycle state (default: APPROVED)

        Parameters:
            description (str): text description of desired tool
            max_number_of_results (int): filter (see above)
            similarity_threshold (float): filter (see above)
            lifecycle_state (LifecycleState): filter (see above)

        Returns:
            list (dict): A list of matched manifests in json format
        """
        self.logger.debug(f"Begin searching tool manifests with:\n\tDescription: {description}\n\tMax results: {max_number_of_results}\n\tSimilarity distance <= {similarity_threshold}\n\tLife cycle state: {lifecycle_state}")
        results = self.search_manifest(search_term=description, 
                                       max_number_of_results=max_number_of_results, 
                                       similarity_threshold=similarity_threshold,
                                       lifecycle_state=lifecycle_state)
        self.logger.debug(f"Search results:\n{base_client_utils.json_pretty_print(results)}")
        return results
    

    def add_tools_from_python_functions(self, mod_func_pairs: List):
        """
        A bulk operation of adding new tools from python functions in specific modules
        NOTE: all tools are considered NEW, s.t. they are loaded as initial versions
        regardless of what's already inside. BE CAREFUL!

        Args:
            mod_func_pairs: A list of pairs (2-tuples) of (module_path, function_name)

        Returns:
            List: a list of UIDs - one for each tool artifact generated from the respective pair
        """
        self.logger.debug(f"Begin bulk adding of tools from: {mod_func_pairs}")
        uids=[]
        for module_path, func_name in mod_func_pairs:
            manifest = json_client_utils.python_manifest_from_docstring_or_json(self.json_base, module_path, func_name)
            if manifest == None:
                raise Exception(f"Failed to generate manifest for: ({module_path}, {func_name})")
            self.logger.debug(f"Generated manifest for ({module_path}, {func_name}): \n{base_client_utils.json_pretty_print(manifest)}")
            manifest_str = json.dumps(manifest)
            response = self.add_manifest(manifest_str, module_path)
            self.logger.debug(f"Service response: \n{base_client_utils.json_pretty_print(response)}")
            uids.append(response["uid"])
        return uids
    

    def execute_tool(self, uid: str, parameters: Optional[Dict[str, Any]] = None):
        """
        Invoke tool by uid.

        Parameters:
            uid (str): The unique identifier of the tool
            parameters (dict): Optional arguments or parameters (k/v) 

        Returns:
            dict: function output

        Raises:
            HTTPException (404): If tool manifest not found

        """
        self.logger.debug(f"Invoking tool with UID: {uid}\nArguments: {base_client_utils.json_pretty_print(parameters)}")
        response = self.execute_manifest(uid, parameters)
        self.logger.debug(f"Service response: \n{base_client_utils.json_pretty_print(response)}")
        return response    


    def delete_tool(self, uid: str):
        """
        Delete a tool given its UID.

        Parameters:
            uid (str): UID of tool (manifest) for deletion

        Raises:
            HTTPException (404): If manifest not found
        """
        self.logger.debug(f"Deleting tool with UID: {uid}")
        response = self.delete_manifest(uid)
        self.logger.debug(f"Service response: \n{base_client_utils.json_pretty_print(response)}")
        return response    
    
    # ------- END client API --------


