import inspect
import io
import json
import logging
from pathlib import Path
import re
from typing import Dict, List

import requests
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from agents.state import State
from llm.common import llm

logger = logging.getLogger(__name__)

# search for tools from the repository using API call (semantic search)
base_url = "http://9.148.245.32:8000"
post_file_url = f"{base_url}/file/"

headers = {"Accept": "application/json"}
max_numer_of_results = 5
similarity_threshold = 1


def code_missing_tools(state: State):
    need_to_generate_tools = state["need_to_generate_tools"]
    for need_to_generate_tool in need_to_generate_tools:

        # (1) create missing tools using LLM-as-coder (based on names and descriptions)
        name = need_to_generate_tool["name"]
        description = need_to_generate_tool["description"]
        tool_response, metadata = code_python_function_using_llm_as_a_coder(name, description)

        # (2) generalize and remove PII from the tool
        # TODO: implement
        generalize_tool_response = tool_generalize_using_llm_as_a_coder(name=name,
                                                                        metadata=metadata,
                                                                        description=tool_response.docstring,
                                                                        code=tool_response.code)

        # (3) validate the function and make sure it is valid to be added to the repo
        success = validate_tool_using_llm_as_a_coder(name=generalize_tool_response["name"],
                                                     metadata=generalize_tool_response["metadata"],
                                                     description=generalize_tool_response["description"],
                                                     code=generalize_tool_response["code"])
        if not success:
            logger.error(f"code_missing_tools: tool {name} validation failed")
            continue

        # (4) add the tool to the tool repository
        success = add_tool_to_repo(name=generalize_tool_response["name"],
                                   metadata=generalize_tool_response["metadata"],
                                   description=generalize_tool_response["description"],
                                   code=generalize_tool_response["code"])
        if not success:
            logger.error(f"add_tool_to_repo: tool {name} upload to repo failed")
            continue
        else:
            # the name of tools at this stage are added with the .py because we supprot creation of .py code files
            # only. TODO fix this to support multiple languages and packaging --- later stage
            need_to_generate_tool["name"] = f'{need_to_generate_tool["name"]}.py'


def add_tool_to_repo(name: str, metadata: json, description: str, code: str) -> bool:
    logger.info(f"add_tool_to_repo called for tool: {name}")

    files = {'file': (f'{name}.py',
                      io.StringIO(code), 'text/plain')}


    response = requests.post(post_file_url,
                             headers=headers,
                             params={"file_description": description, "file_metadata": json.dumps(metadata)},
                             files=files)
    if response.status_code == 200:
        logger.info(f"add_tool_to_repo: tool {name} uploaded successfully")
        return True
    else:
        logger.error(f"add_tool_to_repo: tool {name} upload failed with status code {response.status_code}")
        return False


class CodePythonFunctionResponseJsonSchema(BaseModel):
    docstring: str = Field(description="The function docstring that includes input parameters, and the return value")
    code: str = Field(description="The function code including the cocstring without examples or usage")


code_python_function_chat_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are an expert in writing code in python"),
    ("system", "Always add meaningful Docstrings and documentation to functions"),
    ("system", "The Docstrings always include function description, input parameters with types, and the return value"),
    ("system", "Include the Docstrings as part of the function code"),
    ("system", "Do not add examples or usage, answer with only python code"),
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
    response = code_missing_tools_chain.invoke({"function_description": description, "function_name": name})
    logger.info("code_python_function_using_llm_as_a_coder returned: %s", response)

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

def save_python_file(code: str, filename: str):
    try:
        with open(filename, 'w') as f:
            f.write(code)
        logger.info(f"Successfully saved code to {filename}")
    except Exception as e:
        logger.error(f"Error saving file: {e}")

def generate_test_cases(task: str) -> List[Dict]:
    prompt = f"""
    For this task: {task}
    Generate 2 test cases in JSON format. Include edge cases and normal cases.
    Each test case should have 'params' (list of parameters) and 'expected' (expected output).
    Return only the JSON array.

    Example format:
    [
        {{"params": [1, 2, 3], "expected": 6}},
        {{"params": [0, 0, 0], "expected": 0}}
    ]
    """
    test_cases_str = llm.invoke(prompt)
    return json.loads(test_cases_str.content)

def get_wrapped_code(code: str, func_name: str) -> str:
    # Create a wrapper script that imports and runs the generated function
    wrapper_script = f"""
# Generated function
{code}

# Get command line arguments and run function
if __name__ == "__main__":
    import sys
    import json

    # Read input parameters from command line
    params = json.loads(sys.argv[1])
    expected = json.loads(sys.argv[2])

    # Run function with parameters
    result = {func_name}(*params)

    # Compare result
    if result == expected:
        print(json.dumps({{"success": True, "result": result}}))
        sys.exit(0)
    else:
        print(json.dumps({{"success": False, "result": result, "expected": expected}}))
        sys.exit(1)
"""
    return wrapper_script


def validate_tool_using_llm_as_a_coder(name: str, metadata: json, description: str, code: str) -> str:
    logger.info(f"Validating function code:\n{name}\n")
    logger.info(f"code:\n{code}\n")
    logger.info(f"description:\n{description}\n")
    logger.info(f"metadata:\n{metadata}\n")

    import docker
    # Create a Docker client
    client = docker.from_env()
    logger.info("Validating the python code...")
    # Generate test according to the metadata
    tests = generate_test_cases(description)
    wrapper_script = get_wrapped_code(code, name)
    try:
        # format the content
        import black
        formatted_code = black.format_str(wrapper_script, mode=black.FileMode())
        save_python_file(formatted_code, "llm_code_generated.py")
        script_dir = Path(".")
        script_path = script_dir / "llm_code_generated.py"
        # Build the Docker image for the workflow
        image, build_logs = client.images.build(
            path=".",
            dockerfile="DockerfileCode",
            tag="isolated-validation"
        )

        for test in tests:
            logger.info(f"test = {test}, {json.dumps(test['params'])}")
            # Run the container with mounted script
            container = client.containers.run(
                "isolated-validation",
                volumes={
                    str(script_path.absolute()): {
                        'bind': '/app/llm_code_generated.py',
                        'mode': 'ro'
                    },
                },
                command=[
                    json.dumps(test["params"]),
                    json.dumps(test["expected"])
                ],
                detach=True,
            )

            # Wait for the container to complete and get logs
            result = container.wait()

            # Clean up
            container.remove()
            if result["StatusCode"] == 0:
                logger.info("The tests passed")
                return True
            else:
                logger.info("The tests failed")
                return False

    except Exception as e:
        logger.error(str(e))
        logger.info("Error in running the code")
        return False

    return True


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
