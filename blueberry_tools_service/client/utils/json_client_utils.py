import os
import json
from typing import List, Dict
from .base_client_utils import (
    init_manifest,
    extract_docstring,
    python_manifest_from_function_docstring,
)

def python_manifest_from_json_record(json_rec: dict, module_path: str):
    """
    Generates a Python manifest for a function based on a JSON record from the DOT project.

    Args:
        json_rec (dict): A JSON record extracted from the DOT project descriptions.
        module_path (str): The path to the Python module containing the function.

    Returns:
        dict: The generated manifest.
    """
    func_name = json_rec["name"]
    manifest = init_manifest(func_name, "python")
    manifest["name"] = func_name
    manifest["module_name"] = os.path.basename(module_path)
    manifest["state"] = "approved"
    manifest["description"] = json_rec["description"]
    manifest["params"]["properties"] = json_rec["arguments"]
    manifest["params"]["required"] = json_rec["required"]
    if "optional" in json_rec:
        manifest["params"]["optional"] = json_rec["optional"]

    return manifest

def python_manifest_from_json_base(json_base: List[List[Dict]], module_path: str, func_name: str):
    """
    Generates a Python manifest for a function based on a JSON record inside a JSON base of the DOT project.

    Args:
        json_base (List[List[Dict]]): A JSON base of DOT project function descriptions.
        module_path (str): The path to the Python module containing the function.
        func_name (str): The name of the function to generate a manifest for.

    Returns:
        dict or None: The generated manifest if the function has a record in the JSON base, otherwise None.
    """
    for json_file in json_base:
        for json_record in json_file:
            if json_record["name"] == func_name:
                return python_manifest_from_json_record(json_record, module_path)
    return None

def python_manifest_from_docstring_or_json(json_base: List[List[Dict]], module_path: str, func_name: str):
    """
    Generates a Python manifest for a function based on either its docstring or a JSON base.

    Args:
        json_base (List[List[Dict]]): A JSON base of DOT project function descriptions.
        module_path (str): The path to the Python module containing the function.
        func_name (str): The name of the function to generate a manifest for.

    Returns:
        dict or None: The generated manifest if the function has a proper docstring or a matching JSON record, otherwise None.
    """
    docstring = extract_docstring(module_path, func_name)
    manifest = None
    if docstring is not None:
        manifest = python_manifest_from_function_docstring(module_path, func_name, docstring)
    if manifest is None and json_base is not None:
        manifest = python_manifest_from_json_base(json_base, module_path, func_name)
    return manifest

def load_json_base(json_path: str):
    """
    Loads a JSON base from a specified directory.

    Args:
        json_path (str): The path to the directory containing JSON files.

    Returns:
        list: A list of JSON data loaded from the files in the directory.

    Raises:
        Exception: If the directory is not found or if there's an error parsing the JSON files.
    """
    json_base = []
    try:
        for filename in os.listdir(json_path):
            if filename.endswith(".json"):
                file_path = os.path.join(json_path, filename)
                with open(file_path, "r") as f:
                    try:
                        data = json.load(f)
                        json_base.append(data)
                    except json.JSONDecodeError:
                        raise Exception(f"Could not decode JSON in file: {filename}")
                    except Exception as e:
                        raise Exception(f"An error occurred while processing file: {filename} - {e}")
    except FileNotFoundError:
        raise Exception(f"Error: Folder not found: {json_path}")
    except Exception as e:
        raise e

    return json_base
