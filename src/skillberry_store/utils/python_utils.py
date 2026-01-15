import ast

from docstring_parser import parse, ParseError


def get_function_node(tool_bytes: bytes, tool_name: str):
    """
    Utility to return the first matched node of function name.

    """
    try:
        tree = ast.parse(tool_bytes)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and tool_name == node.name:
                return node
        return None

    except Exception as e:
        raise Exception(f"Failed to parse Python code: {str(e)}")


def extract_docstring(tool_bytes: bytes, tool_name: str = None) -> str:
    """
    Extracts the docstring of a function from a Python module code.

    Parameters:
        tool (byte): Python module code.
        tool_name (str): The name of the function (Optional).

    Returns:
        (str, docstring_obj):
            The function name
            The docstring object of the function

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
                    if not docstring:
                        raise Exception(f"Docstring is missing for tool: {tool_name}")
                    try:
                        docstring_obj = parse(docstring)
                        assert (
                            docstring_obj.short_description is not None
                        ), "Missing docstring description"
                        assert len(node.args.args) == len(
                            docstring_obj.params
                        ), "Missing docstring parameters"
                    except ParseError as e:
                        raise Exception(f"Failed to parse docstring: {str(e)}")

                    return node.name, docstring_obj

        raise Exception(
            f"Function {tool_name} not found in module code"
            if tool_name
            else "No functions found in module code"
        )

    except (FileNotFoundError, SyntaxError, OSError, TypeError) as e:
        raise Exception(f"Failed to extract docstring: {str(e)}")
