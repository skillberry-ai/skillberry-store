import inspect
import logging
import re

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from llm.common import coder_llm

logger = logging.getLogger(__name__)


class CodePythonFunctionResponseJsonSchema(BaseModel):
    code: str = Field(
        description="The function code including a complete (Google style) docstring")


base_python_coding_prompt_messages = [
    ("system", "You are an expert in writing code in python"),
    ("system", "Always add meaningful docstring (Google style) to functions and tools that you generate"),
    ("system", "Always include a complete docstring as part of the generated code"),
    ("system", "Make sure to provide elaborated description as part of the docstring"),
    ("system", "The docstring should always include description, the input parameters including types, "
               "and the return value including the type"),
    ("system", "Write the code using defensive programming techniques, "
               "such as checking for None values, validating input parameters, and handling potential exceptions."),
    ("system", "Do not add examples or usage, answer with only the python code itself"),
    ("system", "An example of a function with valid docstring that includes parameters and"
               "return value looks like this:"),
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
     )
]
code_python_function_chat_prompt_template = ChatPromptTemplate.from_messages(
    base_python_coding_prompt_messages + [
        ("user",
         "Use the following description of the tool: {function_description}\n"
         "and usage examples of the tool: {function_examples}\n"
         "to write python code for the {function_name} function:\n")
    ])


def code_python_function_using_llm_as_a_coder(name: str, description: str, examples: str):
    logger.info(f"Coding function: {name}\n"
                f" with description:\n{description}\n"
                f" with examples:\n{examples}\n")

    structured_llm = coder_llm.with_structured_output(schema=CodePythonFunctionResponseJsonSchema,
                                                      method="function_calling",
                                                      include_raw=False)

    try:
        code_missing_tools_chain = code_python_function_chat_prompt_template | structured_llm
        response = code_missing_tools_chain.invoke(
            {"function_description": description, "function_name": name, "function_examples": examples})
        code = response.code
        print(f"The code:\n\n {code}\n")
    except Exception as e:
        logger.error(
            "code_python_function_using_llm_as_a_coder failed with error: %s", e)
        return False, {}, {}, {}

    try:
        # Get the metadata of the function from the docstring
        description, function_calling_api = parse_docstring(name, code)
        metadata = {
            "programming_language": "python",
            "packaging_format": "code",
            "name": name,
            "description": description,
            "examples": examples,
            "parameters": function_calling_api["parameters"],
        }

        return True, description, metadata, response.code
    except Exception as e:
        logger.error(
            "docstring parsing failed with error: %s", e)
        return False, {}, {}, {}


def parse_docstring(name: str, code: str) -> (str, dict):
    local_dict = {}
    exec(code, {}, local_dict)
    func = local_dict[name]

    docstring = inspect.getdoc(func)
    signature = inspect.signature(func)

    description = docstring.split("\n\n")[0] if docstring else ""
    param_docs = re.findall(r"(\w+) \((\w+)\): (.+)", docstring)  # For Google style
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

    return description, {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    }
