import inspect
import io
import json
import logging
import os
import re
import time

import requests
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from agents.state import State
from agents.unittest_tools import validate_tool_using_llm_as_a_coder
from config.config_ui import config
from llm.common import llm

logger = logging.getLogger(__name__)

# search for tools from the repository using API call (semantic search)
base_url = "http://9.148.245.32:8000"
post_file_url = f"{base_url}/file/"

headers = {"Accept": "application/json"}

# A general variable that allows (or disallows) to generate tools dynamically by the agent
generate_tools_dynamically = config.get("advanced__generate_tools_dynamically")


def code_missing_tools(state: State):
    thinking_log = []
    logging.info(f"=======>>> code_missing_tools. starts <<<=======")
    need_to_generate_tools = state["need_to_generate_tools"]
    generated_tools = []

    logging.info(
        f"code_missing_tools: need_to_generate_tools: {need_to_generate_tools}")
    for need_to_generate_tool in need_to_generate_tools:
        name = need_to_generate_tool.name

        if not generate_tools_dynamically:
            logger.info(
                f"!!! generate_tools_dynamically is False: tool {name} will not be generated !!!")
            continue

        # Generate a new `private` name for the tool.
        # The tool will be uploaded to the repo with this name, and
        # used privately until approval.
        # TODO: make sure that this is the accepted design
        timestamp = int(time.time())
        private_tool_name = f"{name}_at_{timestamp}"

        need_to_generate_tool.name = private_tool_name
        success = generate_tool(need_to_generate_tool)
        if not success:
            logger.error(f"code_missing_tools: tool {name} generation failed")
            continue

        # the name of tool at this stage is added with the .py because we support creation of .py code files
        # only. TODO fix this to support multiple languages and packaging --- later stage
        need_to_generate_tool.name = f'{need_to_generate_tool.name}.py'

        #  (5) add the tool to the generated tools list
        generated_tools.append({
            "name": need_to_generate_tool.name,
            "description": need_to_generate_tool.description,
        })

    if len(generated_tools) > 0:
        thinking_log.append("I just coded ephemeral tools that I will use.")
        tool_descriptions = ""
        for i, tool in enumerate(generated_tools):
            tool_description = tool["description"]
            tool_descriptions += f"{tool_description} "
            if i < len(generated_tools) - 1:
                tool_descriptions += ", and a tool that "
            else:
                tool_descriptions += "."

        thinking_log.append(f"a tool that {tool_descriptions}")

    logging.info(f"=======>>> code_missing_tools. ended <<<=======")
    # (6) update the state with the generated tools
    return {"generated_tools": generated_tools,
            "thinking_log": thinking_log}


def generate_tool(need_to_generate_tool: dict, skip_validation=False) -> bool:
    name = need_to_generate_tool.name
    description = need_to_generate_tool.description
    examples = need_to_generate_tool.examples

    logging.info(f"generate_tool: generating tool {name}")
    logging.info(f"description: {description}")
    logging.info(f"examples: {examples}")

    # (1) create tool using LLM-as-coder (based on the tool name and description)
    success, tool_response, metadata = code_python_function_using_llm_as_a_coder(
        name=name,
        description=description,
        examples=examples)

    if not success:
        logger.error(f"generate_tool: tool {name} code python function failed")
        return False

    # (2) generalize and remove PII from the tool
    # TODO: implement
    logging.info(f"generate_tool: generalizing tool {name}")
    generalize_tool_response = tool_generalize_using_llm_as_a_coder(name=name,
                                                                    metadata=metadata,
                                                                    description=tool_response.docstring,
                                                                    code=tool_response.code)

    # (3) validate the function and make sure it is valid to be added to the repo
    logging.info(f"generate_tool: validating tool {name}")
    if skip_validation is True:
        logging.info(f"generate_tool: skipping validating for tool {name}")
    else:
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

    logging.info(f"generate_tool: tool {name} added to the repository successfully.")
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
        description="The function docstring (Google style) including all input parameters, and the return value")
    code: str = Field(
        description="The function code including the docstring without examples or usage")


code_python_function_chat_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are an expert in writing code in python"),
    ("system", "Always add meaningful docstring (Google style) to functions and tools that you generate"),
    ("system", "The docstring should always include description, the input parameters including types, "
               "and the return value including the type"),
    ("system", "Make sure to provide elaborated description as part of the docstring"),
    ("system", "Include the complete docstring also as part of the code that you generate"),
    ("system", "Do not add examples or usage, answer with only the python code itself"),
    ("system", "The return value of the functions should always be a string"),
    ("system", "An example of a function with valid docstring that includes Parameters and"
               "Return value looks like this:"),
    ("system", """
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
     "Use the following description of the tool: {function_description}"
     "and usage examples of the tool: {function_examples} "
     "to write python code for the {function_name} function:")
])


def code_python_function_using_llm_as_a_coder(name: str, description: str, examples: str):
    logger.info(f"Coding function: {name}\n"
                f" with description:\n{description}\n"
                f" with examples:\n{examples}\n")

    structured_llm = llm.with_structured_output(schema=CodePythonFunctionResponseJsonSchema,
                                                method="function_calling",
                                                include_raw=False)

    try:
        code_missing_tools_chain = code_python_function_chat_prompt_template | structured_llm
        response = code_missing_tools_chain.invoke(
            {"function_description": description, "function_name": name, "function_examples": examples})
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

        return True, response, metadata
    except Exception as e:
        logger.error(
            "code_python_function_using_llm_as_a_coder failed with error: %s", e)
        return False, {}, {}


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
