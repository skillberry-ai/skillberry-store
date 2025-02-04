import docker
import inspect
import io
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List

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


def code_missing_tools(state: State):
    logging.info(f"=======>>> code_missing_tools. starts <<<=======")
    need_to_generate_tools = state["need_to_generate_tools"]
    for need_to_generate_tool in need_to_generate_tools:
        name = need_to_generate_tool["name"]
        logging.info(f"code_missing_tools: generating tool {name}")
        # (1) create missing tools using LLM-as-coder (based on names and descriptions)
        name = need_to_generate_tool["name"]
        description = need_to_generate_tool["description"]
        tool_response, metadata = code_python_function_using_llm_as_a_coder(
            name, description)

        # (2) generalize and remove PII from the tool
        # TODO: implement
        logging.info(f"code_missing_tools: generalizing tool {name}")
        generalize_tool_response = tool_generalize_using_llm_as_a_coder(name=name,
                                                                        metadata=metadata,
                                                                        description=tool_response.docstring,
                                                                        code=tool_response.code)

        # (3) validate the function and make sure it is valid to be added to the repo
        logging.info(f"code_missing_tools: validating tool {name}")
        success = validate_tool_using_llm_as_a_coder(name=generalize_tool_response["name"],
                                                     metadata=generalize_tool_response["metadata"],
                                                     description=generalize_tool_response["description"],
                                                     code=generalize_tool_response["code"])
        if not success:
            logger.error(f"code_missing_tools: tool {name} validation failed")
            continue

        # (4) add the tool to the tool repository
        logging.info(f"code_missing_tools: adding tool {name} to the tool repository")
        success = add_tool_to_repo(name=generalize_tool_response["name"],
                                   metadata=generalize_tool_response["metadata"],
                                   description=generalize_tool_response["description"],
                                   code=generalize_tool_response["code"])
        if not success:
            logger.error(f"add_tool_to_repo: tool {name} upload to repo failed")
            continue
        else:
            # the name of tools at this stage are added with the .py because we support creation of .py code files
            # only. TODO fix this to support multiple languages and packaging --- later stage
            need_to_generate_tool["name"] = f'{need_to_generate_tool["name"]}.py'
    logging.info(f"=======>>> code_missing_tools. ended <<<=======")


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
        logger.error(f"add_tool_to_repo: tool {name} upload failed with status code {response.status_code}")
        return False


class CodePythonFunctionResponseJsonSchema(BaseModel):
    docstring: str = Field(
        description="The function docstring that includes input parameters, and the return value")
    code: str = Field(
        description="The function code including the cocstring without examples or usage")


code_python_function_chat_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are an expert in writing code in python"),
    ("system", "Always add meaningful docstrings and documentation to functions"),
    ("system", "The docstrings always include function description, input parameters with types, and the return value"),
    ("system", "Include the docstrings as part of the function code"),
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

def save_python_file(code: str, filename: str):
    try:
        with open(filename, 'w') as f:
            f.write(code)
        logger.info(f"Successfully saved code to {filename}")
    except Exception as e:
        logger.error(f"Error saving file: {e}")

class TestCase(BaseModel):
    params: List[Any]
    expected: Any

class TestCases(BaseModel):
    test_cases: List[TestCase]

def generate_test_cases(task: str) -> List[Dict]:
    """Generate test cases using LLM with structured output."""
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
    structured_llm = llm.with_structured_output(TestCases)
    result = structured_llm.invoke(prompt)

    return [{"params": t.params, "expected": t.expected}
            for t in result.test_cases]

def get_wrapped_code(code: str, func_name: str) -> str:
    """Create a wrapper script for testing the generated function."""
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

def build_image(client, dockerfile: str = "DockerfileCode", tag: str = "isolated-validation"):
    """Build Docker image for validation."""
    try:
        image, logs = client.images.build(
            path=".",
            dockerfile=dockerfile,
            tag=tag
        )
        return image
    except Exception as e:
        logger.error(f"Error building Docker image: {e}")
        raise

def run_test(client, image_tag: str, script_path: Path, test_case: Dict) -> bool:
    """Run a single test case in Docker container."""
    try:
        container = client.containers.run(
            image_tag,
            volumes={
                str(script_path.absolute()): {
                    'bind': '/app/llm_code_generated.py',
                    'mode': 'ro'
                },
            },
            command=[
                json.dumps(test_case["params"]),
                json.dumps(test_case["expected"])
            ],
            detach=True,
        )

        result = container.wait()
        container.remove()

        return result["StatusCode"] == 0
    except Exception as e:
        logger.error(f"Error running test in container: {e}")
        raise


def validate_tool_using_llm_as_a_coder(name: str, metadata: json, description: str, code: str) -> str:
    """Validate generated code using Docker isolation and LLM-generated tests."""
    logger.info(f"Validating function code:\n{name}\n")
    logger.info(f"code:\n{code}\n")
    logger.info(f"description:\n{description}\n")
    logger.info(f"metadata:\n{metadata}\n")

    unwanted_words = ["error", "manager", "handler", "api", "key"]
    try:
        description = description.lower() if isinstance(description, str) else ""
        code = code.lower() if isinstance(code, str) else ""
        metadata_text = " ".join(str(value).lower(
        ) for value in metadata.values()) if isinstance(metadata, dict) else ""

        for word in unwanted_words:
            if word in description or word in metadata_text or word in code:
                logger.warning(f"validate_tool_using_llm_as_a_coder: Tool '{name}' contains unwanted word '{word}'")
                return False  # Stop validation if any unwanted word is found

    except Exception as e:
        logger.error(
            f"validate_tool_using_llm_as_a_coder: Unexpected error while validating tool '{name}': {e}")
        return False  # Fail-safe return in case of an unexpected error

    # Create a Docker client
    client = docker.from_env()
    logger.info("Validating the python code...")
    # Generate test according to the metadata
    # tests = generate_test_cases(description)
    tests = generate_test_cases(metadata["description"])
    logger.info(f"Generated tests:\n{tests}\n")
    wrapper_script = get_wrapped_code(code, name)
    try:
        # format the content
        import black
        formatted_code = black.format_str(wrapper_script, mode=black.FileMode())
        save_python_file(formatted_code, "llm_code_generated.py")
        script_dir = Path(".")
        script_path = script_dir / "llm_code_generated.py"
        build_image(client=client)

        for test in tests:
            logger.info(f"Running test = {test}")
            if not run_test(client, "isolated-validation", script_path, test):
                logger.info("Test failed")
                return False
        logger.info("All tests passed")
        return True

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False
    
    # TODO: implement more checks

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
