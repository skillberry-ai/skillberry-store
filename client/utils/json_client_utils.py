# Additional client utilities for tools that build from external JSON documentation

import os
from docstring_parser import parse, ParseError
import json
from typing import List, Dict
import ast
from .base_client_utils import init_manifest, extract_docstring, python_manifest_from_function_docstring


def python_manifest_from_json_record(json_rec: dict, module_path: str):
    """
    Generate a Python manifest for a function whose description is 
    in a JSON record of the DOT project. 

    Args:
        json_rec (dict): a JSON record extracted from the DOT project descriptions
        module_path (str): the path to the Python module containing the function

    Returns:
        dict:   the manifest 
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
    Generate a Python manifest for a function whose description is 
    in a JSON record inside a JSON base of the DOT project. 

    Args:
        json_base (List[List[Dict]]): a JSON base of DOT project function descriptions
        module_path (str): the path to the Python module containing the function
        func_name (str): the name of the function to generate a manifest for

    Returns:
        dict or None:   the manifest, if the function has a record in the JSON base. None otherwise.
    """
    for json_file in json_base:
        for json_record in json_file:
            if json_record["name"] == func_name:
                return python_manifest_from_json_record(json_record, module_path)
    return None



def python_manifest_from_docstring_or_json(json_base: List[List[Dict]], module_path: str, func_name: str):
    """
    Generate a Python manifest for a function whose description is 
    either in the function's docstring or in an accompanying JSON base (GIN).

    Args:
        json_base (List[List[Dict]]): a JSON base of DOT project function descriptions
        module_path (str): the path to the Python module containing the function
        func_name (str): the name of the function to generate a manifest for

    Returns:
        dict or None:   the manifest, if the function has proper docstring or matching JSON record. None otherwise.
    """
    docstring = extract_docstring(module_path, func_name)
    manifest = None
    if docstring != None:
        manifest = python_manifest_from_function_docstring(module_path, func_name, docstring)
    if manifest == None and json_base != None:
        manifest = python_manifest_from_json_base(json_base, module_path, func_name)
    return manifest



def load_json_base(json_path: str):
    """
    Load a JSON base of the LakeHouse project

    Args:
        json_path (str): a path to a folder containing the JSON files
    
    Returns:
        list:   the JSON base as a list of JSON data from the folder,
                each loaded from a different file
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


