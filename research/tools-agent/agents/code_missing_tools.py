import inspect
import io
import json
import logging
import os
import re

import requests
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from agents.state import State
from agents.unittest_tools import validate_tool_using_llm_as_a_coder
from llm.common import llm

logger = logging.getLogger(__name__)

# search for tools from the repository using API call (semantic search)
base_url = "http://9.148.245.32:8000"
post_file_url = f"{base_url}/file/"

headers = {"Accept": "application/json"}

# A general variable that allows (or disallows) to generate tools dynamically by the agent
generate_tools_dynamically = os.getenv('GENERATE_TOOLS_DYNAMICALLY', False)


def code_missing_tools(state: State):
    logging.info(f"=======>>> code_missing_tools. starts <<<=======")
    need_to_generate_tools = state["need_to_generate_tools"]
    generated_tools = []

    logging.info(
        f"code_missing_tools: need_to_generate_tools: {need_to_generate_tools}")
    for need_to_generate_tool in need_to_generate_tools:
        name = need_to_generate_tool["name"]
        if not generate_tools_dynamically:
            logger.info(
                f"!!! generate_tools_dynamically is False: tool {name} will not be generated !!!")
            continue

        success = generate_tool(need_to_generate_tool)
        if not success:
            logger.error(f"code_missing_tools: tool {name} generation failed")
            continue

        # the name of tool at this stage is added with the .py because we support creation of .py code files
        # only. TODO fix this to support multiple languages and packaging --- later stage
        need_to_generate_tool["name"] = f'{need_to_generate_tool["name"]}.py'

        #  (5) add the tool to the generated tools list
        generated_tools.append(need_to_generate_tool)

    logging.info(f"=======>>> code_missing_tools. ended <<<=======")
    # (6) update the state with the generated tools
    return {"generated_tools": generated_tools}


def generate_tool(need_to_generate_tool: dict) -> bool:
    name = need_to_generate_tool["name"]
    description = need_to_generate_tool["description"]
    logging.info(f"generate_tool: generating tool {name}")
    logging.info(f"description: {description}")

    # (1) create tool using LLM-as-coder (based on the tool name and description)
    tool_response, metadata = code_python_function_using_llm_as_a_coder(
        name, description)

    # (2) generalize and remove PII from the tool
    # TODO: implement
    logging.info(f"generate_tool: generalizing tool {name}")
    generalize_tool_response = tool_generalize_using_llm_as_a_coder(name=name,
                                                                    metadata=metadata,
                                                                    description=tool_response.docstring,
                                                                    code=tool_response.code)

    # (3) validate the function and make sure it is valid to be added to the repo
    logging.info(f"generate_tool: validating tool {name}")
    success = validate_tool_using_llm_as_a_coder(name=generalize_tool_response["name"],
                                                 metadata=generalize_tool_response["metadata"],
                                                 description=generalize_tool_response["description"],
                                                 code=generalize_tool_response["code"])
    if not success:
        logger.error(f"generate_tool: tool {name} validation failed")
        return False

    # (4) add the tool to the tool repository
    logging.info(f"generate_tool: adding tool {name} to the tool repository")
    success = add_tool_to_repo(name=generalize_tool_response["name"],
                               metadata=generalize_tool_response["metadata"],
                               description=generalize_tool_response["description"],
                               code=generalize_tool_response["code"])
    if not success:
        logger.error(
            f"generate_tool: add_tool_to_repo: tool {name} upload to repo failed")
        return False

    return True


def add_tool_to_repo(name: str, metadata: json, description: str, code: str) -> bool:
    logger.info(f"add_tool_to_repo called for tool: {name}")

    files = {'file': (f'{name}.py', io.StringIO(code), 'text/plain')}

    response = requests.post(post_file_url,
                             headers=headers,
                             params={"file_description": description,
                                     "file_metadata": json.dumps(metadata)},
                             files=files)
    if response.status_code == 200:
        logger.info(f"add_tool_to_repo: tool {name} uploaded successfully")
        return True
    else:
        logger.error(
            f"add_tool_to_repo: tool {name} upload failed with status code {response.status_code}")
        return False


class CodePythonFunctionResponseJsonSchema(BaseModel):
    docstring: str = Field(
        description="The function docstring that includes input parameters, and the return value")
    code: str = Field(
        description="The function code including the docstring without examples or usage")


code_python_function_chat_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are an expert in writing code in python"),
    ("system", "Always add meaningful docstring and elaborated documentation to functions"),
    ("system", "The docstring always include function description, input parameters with types, and the return value"),
    ("system", "Include the docstring as part of the function code"),
    ("system", "Do not add examples or usage, answer with only python code"),
    ("system", "The return value of the functions should always be a string"),
    ("system", """An example for a good function with docstring looks like this:
def calculate_rectangle_area(length, width):
    \"\"\"
    Calculate the area of a rectangle.

    Parameters:
    length (float): The length of the rectangle.
    width (float): The width of the rectangle.

    Returns:
    float: The area of the rectangle, calculated as length * width.
    \"\"\"
    if length <= 0 or width <= 0:
        raise ValueError("Length and width must be positive values.")
    
    area = length * width
    return area
"""
     ),
    ("user",
     "Use the following description: {function_description} to write python code for the {function_name} function:")
])


def code_python_function_using_llm_as_a_coder(name: str, description) -> str:
    logger.info(f"Coding function: {name} with description:\n{description}\n")

    structured_llm = llm.with_structured_output(schema=CodePythonFunctionResponseJsonSchema,
                                                method="function_calling",
                                                include_raw=False)

    code_missing_tools_chain = code_python_function_chat_prompt_template | structured_llm
    response = code_missing_tools_chain.invoke(
        {"function_description": description, "function_name": name})
    logger.info(
        "code_python_function_using_llm_as_a_coder returned: %s", response)

    # Get the metadata of the function from the docstring
    function_calling_api = parse_docstring(name, response.code)
    metadata = {
        "programming_language": "python",
        "packaging_format": "code",
        "name": name,
        "description": description,
        "parameters": function_calling_api["parameters"],
    }

    return response, metadata


def tool_generalize_using_llm_as_a_coder(name: str, metadata: json, description: str, code: str) -> str:
    logger.info(f"Validating function code:\n{name}\n")
    logger.info(f"code:\n{code}\n")
    logger.info(f"description:\n{description}\n")
    logger.info(f"metadata:\n{metadata}\n")

    # TODO: implement
    generalized_tool_response = {"name": name,
                                 "metadata": metadata,
                                 "description": description,
                                 "code": code}
    return generalized_tool_response


def parse_docstring(name: str, code: str):
    local_dict = {}
    exec(code, {}, local_dict)
    func = local_dict[name]

    doc = inspect.getdoc(func)
    signature = inspect.signature(func)

    description = doc.split("\n\n")[0] if doc else ""
    param_docs = re.findall(r"(\w+) \((\w+)\): (.+)", doc)  # For Google style
    properties = {}
    required = []

    for param in param_docs:
        name, dtype, desc = param
        if name in signature.parameters:
            properties[name] = {
                "type": dtype.lower(),  # Convert Python types to JSON Schema types
                "description": desc
            }
            required.append(name)

    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    }
