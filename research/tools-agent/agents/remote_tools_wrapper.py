import re
import json
import logging
import inspect
import requests

from langchain.tools import tool

from agents.tools_service_api import get_tool_metadata

logger = logging.getLogger(__name__)

headers = {"Accept": "application/json"}


@tool
def fake_tool():
    """
    This is a fake tool that does nothing.
    If is used so that the file will import the necessary libraries from:
        import inspect
        import requests
        from langchain.tools import tool

    """
    frame = inspect.currentframe()
    print(frame)
    requests.get("do not delete this call", json=json.loads(""))
    return "fake_tool"


def create_function_from_string(code: str, func_name: str, scope: dict):
    exec(code, globals(), scope)
    return scope.get(func_name)


def define_tool_dynamically(tool_name: str, tool_docstring: str, arguments_string: str, scope: dict, _base_url: str):
    """
    Invoke a local tool based on OpenAI parameters definition to be used by the agentic workflow
    """

    # the function will use rest against the tool_service_api to execute the tool
    # with the required parameters
    tool_function_name = re.sub(r"[. ]", "_", tool_name)
    python_code = f"""
import requests
import json
import inspect
from langchain.tools import tool

headers = {{
    "accept": "application/json",
    "Content-Type": "application/json"
}}

@tool
def {tool_function_name} {arguments_string}:
    \"\"\"
    {tool_docstring}
    \"\"\"

    frame = inspect.currentframe()
    args, _, _, values = inspect.getargvalues(frame)
    param_dict = {{arg: values[arg] for arg in args}}
    execute_tool_url = f"{_base_url}/execute/{tool_name}"
    response = requests.post(
        execute_tool_url, headers=headers, json=param_dict)
    if response.status_code == 200:
        response_json = response.json()
        return_value = response_json["return value"]
        cleaned_return_value = return_value.strip().replace('"', '')
        print(f'====> returning response from the function: {{cleaned_return_value}}')
        return cleaned_return_value
    else:
        return None
"""
    _tool = create_function_from_string(python_code, tool_function_name, scope)
    return _tool


def generate_dynamic_tool(_tool: dict, scope: dict, _base_url: str):
    name = _tool["name"]
    metadata = get_tool_metadata(_base_url, name)
    arguments_string = generate_function_arguments_from_metadata(metadata)
    tool_docstring = generate_function_docstring_from_metadata(metadata)
    tool_func = define_tool_dynamically(tool_name=name,
                                        tool_docstring=tool_docstring,
                                        arguments_string=arguments_string,
                                        scope=scope,
                                        _base_url=_base_url)
    return tool_func


def json_schema_to_python_type(json_schema_type: str) -> str:
    # Mapping JSON Schema types to Python types
    type_mapping = {
        "string": "str",
        "str": "str",
        "number": "float",
        "float": "float",
        "integer": "int",
        "int": "int",
        "bool": "bool",
        "boolean": "bool",
        "object": "dict",
        "list": "list",
        "array": "list",
        "datetime": "datetime",
        "null": "None",
        "any": "object",  # 'any' can be mapped to 'object' or 'str', depending on use case
    }

    # Return the corresponding Python type as a string
    return type_mapping.get(json_schema_type, "Unknown")


def generate_function_arguments_from_metadata(metadata: str):
    parsed_info = metadata
    function_arguments = f"("
    parameters = parsed_info['parameters']['properties']
    param_strs = []

    for param_name, param_info in parameters.items():
        param_type = json_schema_to_python_type(param_info['type'])
        param_strs.append(f"{param_name}: {param_type}")

    try:
        returns = parsed_info['returns']['properties']
        returns_type = json_schema_to_python_type(returns['type'])
    except Exception as e:
        returns_type = "str"

    function_arguments += ", ".join(param_strs) + f") -> {returns_type}"

    return function_arguments


def generate_function_docstring_from_metadata(metadata: dict) -> str:
    """Generates a Google-style docstring from a parsed function metadata dictionary."""
    parsed_data = metadata
    description = parsed_data.get("description", "")
    params = parsed_data.get("parameters", {}).get("properties", {})

    docstring_lines = [description, ""] if description else []

    if params:
        docstring_lines.append("Args:")
        for param, details in params.items():
            dtype = details.get("type", "unknown").capitalize()
            desc = details.get("description", "")
            docstring_lines.append(f"    {param} ({dtype}): {desc}")

    return "\n".join(docstring_lines)
