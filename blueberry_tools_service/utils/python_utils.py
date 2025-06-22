import ast


def extract_docstring(tool_bytes: bytes, tool_name: str) -> str:
    """
    Extracts the docstring of a function from a Python module code.

    Parameters:
        tool (byte): Python module code.
        tool_name (str): The name of the function.

    Returns:
        str: The docstring of the function

    Raises:
        Exception: if the function or module is not found or if
                   an error occurs
    """
    try:
        tree = ast.parse(tool_bytes)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == tool_name:
                docstring = ast.get_docstring(node)
                return docstring

        raise Exception(f"Function {tool_name} not found in module code")

    except (FileNotFoundError, SyntaxError, OSError) as e:
        raise Exception(f"Failed to extract docstring: {str(e)}")
