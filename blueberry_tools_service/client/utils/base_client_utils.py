import os
from docstring_parser import parse, ParseError
import json
import ast

def list_functions_in_module(module_path: str):
    """
    Parses a Python module at the given path and extracts function names and docstrings.

    Args:
        module_path (str): The path to the Python module to be processed.

    Returns:
        list[tuple]: A list of tuples containing the module file name, function name, and docstring.

    Raises:
        SyntaxError: If the module contains invalid Python code.
    """
    function_list = []
    module_name = os.path.basename(module_path)

    # Read the file and parse it using AST
    with open(module_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=module_name)
        # Extract functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):  # Check for function definitions
                function_list.append((module_name, node.name, ast.get_docstring(node)))

    return function_list

def list_functions_in_folder(folder_path: str):
    """
    Parses all Python modules in a folder and extracts function names and docstrings without executing the code.

    Args:
        folder_path (str): The path to the folder containing Python modules.

    Returns:
        list[tuple]: A list of tuples containing the module file name, function name, and docstring.

    Raises:
        NotADirectoryError: If the provided folder path is not a directory.
        SyntaxError: If a module contains invalid Python code.
    """
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"Folder not found: {folder_path}")

    function_list = []

    for filename in os.listdir(folder_path):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_path = os.path.join(folder_path, filename)
            mod_func_list = list_functions_in_module(module_path)
            function_list.extend(mod_func_list)

    return function_list

def init_manifest(uid: str, prog_lang: str, pack_fmt="code"):
    """
    Initializes and returns an empty tool manifest with the specified uid, programming language, and packaging format.

    Args:
        uid (str): The unique identifier of the tool.
        prog_lang (str): The programming language of the tool.
        pack_fmt (str, optional): The packaging format of the tool. Defaults to "code".

    Returns:
        dict: The initialized manifest dictionary.
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

def do_extract_docstring(module_code: str, function_name: str) -> str:
    try:
        tree = ast.parse(module_code)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                docstring = ast.get_docstring(node)
                return docstring

        return None  # Function not found

    except (FileNotFoundError, SyntaxError, OSError) as e:
        return None  # Module not found or parsing error

def extract_docstring(module_path, function_name):
    """
    Extracts the docstring of a function from a Python file without importing it.

    Args:
        module_path (str): The path to the Python module file.
        function_name (str): The name of the function.

    Returns:
        str or None: The docstring of the function, or None if not found.
    """
    try:
        with open(module_path, "r", encoding="utf-8") as f:
            module_code = f.read()
        return do_extract_docstring(module_code=module_code, function_name=function_name)

    except (FileNotFoundError, SyntaxError, OSError):
        return None  # Module not found or parsing error

def docstring_to_manifest(docstring_obj, mft):
    """
    Converts a parsed Docstring object into a manifest dictionary.

    Args:
        docstring_obj: A parsed Docstring object from docstring_parser.parse().
        mft (dict): The target manifest dictionary to update.

    Returns:
        None
    """
    # Descriptions
    mft["description"] = docstring_obj.short_description

    # Store parameters as a dictionary: name -> {type, description}
    mft["params"]["properties"] = {
        param.arg_name: {"type": param.type_name, "description": param.description}
        for param in docstring_obj.params
    }

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
    Generates a Python manifest for a function based on its docstring.

    Args:
        module_path (str): The path to the Python module containing the function.
        func_name (str): The name of the function.
        docstring: The docstring of the function.

    Returns:
        dict or None: The generated manifest, or None if the docstring is invalid.
    """
    manifest = init_manifest(func_name, "python")
    manifest["name"] = func_name
    manifest["module_name"] = os.path.basename(module_path)
    manifest["state"] = "approved"

    if not docstring:
        return None

    try:
        func_ds = parse(docstring)
        docstring_to_manifest(func_ds, manifest)  # docstring object -> manifest
    except ParseError:
        return None

    return manifest

def json_pretty_print(d: dict):
    """
    Generates a pretty-print string of a dictionary in JSON notation.

    Args:
        d (dict): The dictionary to pretty-print.

    Returns:
        str: The JSON-formatted pretty-print string of the dictionary.
    """
    return json.dumps(d, indent=4) + "\n"

def read_file_to_bytes(file_path):
    """
    Reads a file into a bytes buffer.

    Args:
        file_path (str): The path to the file.

    Returns:
        bytes or None: The file content as a bytes object, or None if an error occurs.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If any I/O error occurs while reading the file.
    """
    with open(file_path, "rb") as file:  # 'rb' mode for reading in binary
        file_bytes = file.read()
        return file_bytes
