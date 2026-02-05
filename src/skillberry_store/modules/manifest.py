import inspect
import json
import logging
import os
from typing import List, Optional, Dict, Any

from docstring_parser import Docstring

from fastapi import HTTPException

from skillberry_store.client.utils import base_client_utils, json_client_utils
from skillberry_store.modules.tool_type import ToolType
from skillberry_store.tools.shell_hook import ShellHook
from skillberry_store.utils.python_utils import (
    extract_docstring,
    get_function_node,
)

logger = logging.getLogger(__name__)


class Manifest:
    def __init__(self, manifest_directory: str):
        """
        Initialize the manifests with a directory to store manifests.
        """
        self.manifest_directory = manifest_directory
        os.makedirs(self.manifest_directory, exist_ok=True)
        ShellHook().execute("init_manifest", manifest_directory=manifest_directory)

        logger.info(f"Initialized Manifests with directory: {self.manifest_directory}")

    def get_manifest_file_path(self, filename: str) -> str:
        """
        Get the path of the manifest file associated with the given filename.
        """
        return os.path.join(self.manifest_directory, f"{filename}")

    def read_manifest(self, filename: str) -> Optional[str]:
        """
        Read the manifest for the given filename.

        Returns:
            str: The manifest, or None if not found.

        """
        data = None

        ShellHook().execute("pre_" + inspect.stack()[0].function, filename=filename)
        manifest_file_path = self.get_manifest_file_path(filename)
        if os.path.exists(manifest_file_path):
            with open(manifest_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        return data

    def write_manifest(self, filename: str, manifest: Dict[str, Any]) -> dict:
        """
        Write a manifest for the given file.
        """
        ShellHook().execute(
            "pre_" + inspect.stack()[0].function, filename=filename, manifest=manifest
        )
        manifest_file_path = self.get_manifest_file_path(filename)
        try:
            with open(manifest_file_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=4)
            ShellHook().execute(
                "post_" + inspect.stack()[0].function,
                filename=filename,
                manifest=manifest,
            )
            logger.info(f"manifest saved for file: {filename}")
            return {"message": f"manifest saved for file '{filename}'."}
        except Exception as e:
            logger.error(f"Error saving manifest for file '{filename}': {e}")
            ShellHook().execute(
                "post_fail_" + inspect.stack()[0].function,
                filename=filename,
                manifest=manifest,
            )
            raise HTTPException(
                status_code=500, detail=f"Error saving manifest: {str(e)}"
            )

    def create_manifest(
        self,
        tool_type: ToolType,
        tool_bytes: bytes,
        tool_name: str = None,
        parsed_kwargs: Dict = None,
    ) -> Dict:
        """
        Create a manifest out from the given tool_bytes (blob) and tool_name.

        Note: the behavior of manifest creation is dependant on tool_type:
        - CODE_PYTHON: manifest is created out from tool_bytes docsrting
        - JSON_GENAI_LH: manifest is created out from parsed_kwargs

        Parameters:
            tool_type (ToolType): tool type. Enumeration of the type of the tool to be added
            tool_bytes (bytes): tool blob e.g. Python module
            tool_name (str): tool name e.g. Python function name (Optional)
            parsed_kwargs (dict): additional key/val pairs to be processed depending on the
                                  too_type (Optional)

        Raises:
            HTTPException: if an error occurred

        Returns:
            dict: the manifest
        """
        if tool_type == ToolType.CODE_PYTHON:
            # generate manifest out from docstring
            func_name, docstring_obj = extract_docstring(
                tool_bytes, tool_name=tool_name
            )
            return python_manifest_from_function_docstring(func_name, docstring_obj)

        elif tool_type == ToolType.JSON_GENAI_LH:
            json_description = parsed_kwargs
            tool_name = json_description["name"]
            # validate tool name existence and raise exception
            if not get_function_node(tool_bytes, tool_name=tool_name):
                raise Exception(f"Function {tool_name} not found in module code")
            return python_manifest_from_json_description(json_description)

    def print_manifest(
        self, func_name: str, json_description: str = None, code: str = None
    ) -> dict:
        """
        NOTE: THIS METHOD IS DEPRECATED
        """
        try:
            json_description_as_dict = (
                json.loads(json_description) if json_description else {}
            )

            manifest = {}
            if json_description_as_dict:
                # return manifest out from json description format
                manifest = json_client_utils.python_manifest_from_json_base(
                    [[json_description_as_dict]], f"{func_name}.py", func_name
                )

            elif code:
                # return manifest out from code docstring
                docstring = base_client_utils.do_extract_docstring(
                    module_code=code, function_name=func_name
                )
                manifest = base_client_utils.python_manifest_from_function_docstring(
                    f"{func_name}.py", func_name, docstring
                )

            return manifest
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error generating manifest: {str(e)}"
            )

    def update_manifest(self, filename: str, new_manifest: Dict[str, Any]) -> dict:
        """
        Update the manifest for the given file.
        """
        ShellHook().execute(
            "pre_" + inspect.stack()[0].function,
            filename=filename,
            new_manifest=new_manifest,
        )
        manifest_file_path = self.get_manifest_file_path(filename)
        if not os.path.exists(manifest_file_path):
            raise HTTPException(
                status_code=404, detail=f"No manifest found for file '{filename}'"
            )

        try:
            with open(manifest_file_path, "w", encoding="utf-8") as f:
                json.dump(new_manifest, f, indent=4, default=str)
            logger.info(f"manifest updated for file: {filename}")
            ShellHook().execute(
                "post_" + inspect.stack()[0].function,
                filename=filename,
                new_manifest=new_manifest,
            )
            return {"message": f"manifest updated for file '{filename}'."}

        except Exception as e:
            logger.error(f"Error updating manifest for file '{filename}': {e}")
            ShellHook().execute(
                "post_fail_" + inspect.stack()[0].function,
                filename=filename,
                new_manifest=new_manifest,
            )
            raise HTTPException(
                status_code=500, detail=f"Error updating manifest: {str(e)}"
            )

    def list_manifests(self) -> List[Dict[str, str]]:
        """
        List all manifests in the directory.

        Returns:
            list (dict): A list of manifests (json) present in the directory.

        Raises:
            HTTPException: If there is an error accessing the directory.
        """
        try:
            ShellHook().execute("pre_" + inspect.stack()[0].function)
            manifest_files = os.listdir(self.manifest_directory)
            return [
                self.read_manifest(f)
                for f in manifest_files
                if self.read_manifest(f) is not None
            ]
        except Exception as e:
            ShellHook().execute("post_fail_" + inspect.stack()[0].function)
            logger.error(f"Error listing files: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing manifests: {str(e)}"
            )

    def delete_manifest(self, filename: str) -> dict:
        """
        Delete the manifest for a given file.
        """
        manifest_file_path = self.get_manifest_file_path(filename)
        try:
            ShellHook().execute("pre_" + inspect.stack()[0].function, filename=filename)
            if os.path.exists(manifest_file_path):
                os.remove(manifest_file_path)
                ShellHook().execute(
                    "post_" + inspect.stack()[0].function, filename=filename
                )

                logger.info(f"manifest deleted for file: {filename}")
                return {
                    "message": f"manifest for file '{filename}' deleted successfully."
                }
            else:
                raise HTTPException(
                    status_code=404, detail=f"manifest for file '{filename}' not found."
                )
        except Exception as e:
            logger.error(f"Error deleting manifest for file '{filename}': {e}")
            ShellHook().execute(
                "post_fail_" + inspect.stack()[0].function, filename=filename
            )
            raise HTTPException(
                status_code=500, detail=f"Error deleting manifest: {str(e)}"
            )


def init_manifest(prog_lang: str, pack_fmt="code"):
    """
    This utility function initializes and returns an empty tool manifest with
    programming language and packaging format.

    Parameters:
        prog_lang (str): programming language
        pack_fmt (str): packaging format of the tool, default "code"

    Returns:
        dict:   Initialized manifest with programming_language, packaging and
                history with initial "0.0.1" version with status "approved"
    """
    manifest = dict()
    manifest["programming_language"] = prog_lang
    manifest["packaging_format"] = pack_fmt
    manifest["version"] = "0.0.1"
    manifest["params"] = {
        "type": "object",
        "properties": {},
        "required": [],
        "optional": [],
    }
    return manifest


def add_docstring_to_manifest(docstring_obj, manifest):
    """
    Adds docstring object into the given manifest dictionary.

    Parameters:
        docstring_obj: A parsed docstring object from docstring_parser.parse()
        manifest (dict): The target manifest dictionary to update

    """

    # Descriptions
    manifest["description"] = docstring_obj.short_description

    # Not using docstring_obj.long_description

    # Store parameters as a dictionary: name -> {type, description}
    manifest["params"]["properties"] = {
        param.arg_name: {"type": param.type_name, "description": param.description}
        for param in docstring_obj.params
    }

    # All parameters are "required" - so "optional" remains empty
    manifest["params"]["required"] = [param.arg_name for param in docstring_obj.params]

    # Exceptions are not stored
    # Store return type and description
    manifest["returns"] = {
        "type": docstring_obj.returns.type_name if docstring_obj.returns else None,
        "description": (
            docstring_obj.returns.description if docstring_obj.returns else None
        ),
    }


def python_manifest_from_function_docstring(
    func_name: str, docstring_obj: Docstring
) -> Dict:
    """
    This utility function takes a function with a well-formatted docstring
    and extracts an initial Python manifest from the docstring

    Parameters:
        func_name (str): the name of the function as declared in the module
        docstring_obj (Docstring): the doc string of the function

    Returns:
        dict: the manifest

    Raises:
        Exception: if no valid docstring could be extracted or parse error
                   occurred

    """
    manifest = init_manifest("python")
    manifest["name"] = func_name
    manifest["module_name"] = func_name
    manifest["state"] = "approved"

    try:
        add_docstring_to_manifest(docstring_obj, manifest)
    except Exception as e:
        logger.error("Failed to apply docstring to manifest")
        raise

    return manifest


### genai lakehouse specific


def python_manifest_from_json_description(json_description: dict):
    """
    Generate a Python manifest for a function whose description is
    in a JSON record of the DOT project.

    Args:
        json_description (dict): a JSON record extracted from the DOT project descriptions

    Returns:
        dict:   the manifest
    """
    func_name = json_description["name"]
    manifest = init_manifest("python")
    manifest["name"] = func_name
    manifest["module_name"] = os.path.basename(func_name)
    manifest["state"] = "approved"
    manifest["description"] = json_description["description"]
    manifest["params"]["properties"] = json_description["arguments"]
    manifest["params"]["required"] = json_description["required"]
    if "optional" in json_description:
        manifest["params"]["optional"] = json_description["optional"]

    return manifest
