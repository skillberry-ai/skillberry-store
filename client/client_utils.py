import os
from docstring_parser import parse, ParseError
import json
from typing import List, Dict
import ast

def list_functions_in_folder(folder_path: str):
    """
    Parses all Python modules in a folder and extracts function names and docstrings 
    without executing the code.

    Args:
        folder_path (str): Path to the folder containing Python modules.

    Returns:
        list of tuple: A list of tuples where each tuple contains:
            - str: Module file name (e.g., "example.py").
            - str: Function name.
            - str or None: Function docstring, or None if not present.

    Raises:
        NotADirectoryError: If the provided folder path is not a directory.
    """
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"Folder not found: {folder_path}")

    function_list = []

    for filename in os.listdir(folder_path):
        if filename.endswith(".py") and not filename.startswith("__"):  # Ignore __init__.py
            module_path = os.path.join(folder_path, filename)

            # Read the file and parse it using AST
            with open(module_path, "r", encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read(), filename=filename)
                except SyntaxError as e:
                    print(f"Syntax error in {filename}: {e}")
                    continue  # Skip files with syntax errors

            # Extract functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):  # Check for function definitions
                    function_list.append((filename, node.name, ast.get_docstring(node)))

    return function_list



def init_manifest(uid: str, prog_lang: str, pack_fmt="code"):
    """
    This utility function initializes and returns an empty tool manifest with 
    a specific uid (tool unique identifier), programming language and packaging format

    Args:
        uid (str): Unique identifier of the tool
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
        "optional": []
    }
    return manifest



def extract_docstring(module_path, function_name):
    """
    Extracts the docstring of a function from a Python file without importing it.

    Args:
        module_path (str): The path to the Python module file.
        function_name (str): The name of the function.

    Returns:
        str or None: The docstring of the function, or None if the function
                     or module is not found or if an error occurs.
    """
    try:
        with open(module_path, "r", encoding="utf-8") as f:
            module_code = f.read()
        tree = ast.parse(module_code)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                docstring = ast.get_docstring(node)
                return docstring

        return None  # Function not found

    except (FileNotFoundError, SyntaxError, OSError):
        return None  # Module not found or parsing error



def docstring_to_manifest(docstring_obj, mft):
    """
    Convert a Docstring object into a manifest dictionary.

    Args:
        docstring_obj: A parsed Docstring object from docstring_parser.parse()
        mft (dict): the target manifest dictionary to update
    
    Returns:
        None
    """

    # Descriptions
    mft["description"] = docstring_obj.short_description

    # Not using docstring_obj.long_description

    # Store parameters as a dictionary: name -> {type, description}
    mft["params"]["properties"] = {param.arg_name: {"type": param.type_name, "description": param.description}
        for param in docstring_obj.params}

    # All parameters are "required" - so "optional" remains empty
    mft["params"]["required"] = [param.arg_name for param in docstring_obj.params]

    # Exceptions are not stored
    # Store return type and description
    mft["returns"] = {
        "type": docstring_obj.returns.type_name if docstring_obj.returns else None,
        "description": docstring_obj.returns.description if docstring_obj.returns else None,
    }



def python_manifest_from_function_docstring(module_path: str, func_name: str, docstring):
    """
    This utility function takes a function with a well-formatted docstring
    and extracts an initial Python manifest from the docstring

    Args:
        module_path (str): the path to the Python module containing the function
        func_name (str): the name of the function as declared in the module
        docstring: the doc string of the function

    Returns:
        dict or None:   the manifest if available, or None if no 
                        valid docstring could be extracted and parsed
    """
    manifest = init_manifest(func_name, "python")
    manifest["name"] = func_name
    manifest["module_name"] = os.path.basename(module_path)
    manifest["state"] = "approved"

    if not docstring:
        return None
    
    try:
        func_ds = parse(docstring)
        docstring_to_manifest(func_ds, manifest)   # docstring object -> manifest
    except ParseError:
        return None

    return manifest



def python_manifest_from_lh_json_record(lh_json: dict, module_path: str):
    """
    Generate a Python manifest for a function whose description is 
    in a JSON record of the LakeHouse project. 

    Args:
        lh_json (dict): a JSON record extracted from the LakeHouse project descriptions
        module_path (str): the path to the Python module containing the function

    Returns:
        dict:   the manifest 
    """
    func_name = lh_json["name"]
    manifest = init_manifest(func_name, "Python")
    manifest["module_name"] = os.path.basename(module_path)
    manifest["state"] = "approved"
    manifest["description"] = lh_json["description"]
    manifest["params"]["properties"] = lh_json["arguments"]
    manifest["params"]["required"] = lh_json["required"]
    if "optional" in lh_json:
        manifest["params"]["optional"] = lh_json["optional"]

    return manifest



def python_manifest_from_lh_json_base(lh_json_base: List[List[Dict]], module_path: str, func_name: str):
    """
    Generate a Python manifest for a function whose description is 
    in a JSON record inside a JSON base of the LakeHouse project. 

    Args:
        lh_json_base (List[Dict]): a JSON base of LakeHouse project function descriptions
        module_path (str): the path to the Python module containing the function
        func_name (str): the name of the function to generate a manifest for

    Returns:
        dict or None:   the manifest, if the function has a record in the JSON base
    """
    for json_file in lh_json_base:
        for json_record in json_file:
            if json_record["name"] == func_name:
                return python_manifest_from_lh_json_record(json_record, module_path)
    return None



def load_lh_json_base(lh_json_path: str):
    """
    Load a JSON base of the LakeHouse project

    Args:
        lh_json_path (str): a path to a folder containing the JSON files
    
    Returns:
        list:   the JSON base as a list of JSON data from the folder,
                each loaded from a different file
    """
    json_base = []
    try:
        for filename in os.listdir(lh_json_path):
            if filename.endswith(".json"):
                file_path = os.path.join(lh_json_path, filename)
                with open(file_path, "r") as f:
                    try:
                        data = json.load(f)
                        json_base.append(data)
                    except json.JSONDecodeError:
                        raise Exception(f"Could not decode JSON in file: {filename}")
                    except Exception as e:
                        raise Exception(f"An error occurred while processing file: {filename} - {e}")
    except FileNotFoundError:
        raise Exception(f"Error: Folder not found: {lh_json_path}")
    except Exception as e:
        raise e

    return json_base


def json_pretty_print(d: dict):
    """
    Generate a pretty-print string of a dictionary in JSON notation.

    Args:
        d (dict): the dictionary to pretty-print

    Returns:
        str: the JSON-formatted pretty-print string of the dictionary
    """

    return json.dumps(d, indent=4)
