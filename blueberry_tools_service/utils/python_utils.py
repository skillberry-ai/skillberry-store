import ast


def extract_docstring(tool_bytes: bytes, tool_name: str = None) -> str:
    """
    Extracts the docstring of a function from a Python module code.

    Parameters:
        tool (byte): Python module code.
        tool_name (str): The name of the function (Optional).

    Returns:
        (str, str):
            The function name
            The docstring of the function

    Raises:
        Exception: if the function or module is not found or if
                   an error occurs
    """
    try:
        tree = ast.parse(tool_bytes)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # return the first (if no name) or the matched one
                if not tool_name or tool_name == node.name:
                    docstring = ast.get_docstring(node)
                    return node.name, docstring

        raise Exception(
            f"Function {tool_name} not found in module code"
            if tool_name
            else "No functions found in module code"
        )

    except (FileNotFoundError, SyntaxError, OSError, TypeError) as e:
        raise Exception(f"Failed to extract docstring: {str(e)}")
