from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Any, Dict, List
from pathlib import Path
import logging
import json
import sys

from config.config_ui import config
from llm.common import coder_llm

service_dir = Path(__file__).parent.parent.parent / 'tools-service'
sys.path.append(str(service_dir))

from modules.file_executor import FileExecutor

# TODO: Find better wat to import FileExecutor


logger = logging.getLogger(__name__)

# search for tools from the repository using API call (semantic search)
tools_repo_base_url = config.get("tools_repo_base_url")
post_file_url = f"{tools_repo_base_url}/file/"

headers = {"Accept": "application/json"}
base_unittests_directory = "/tmp"


class TestCase(BaseModel):
    params: List[Any] = Field(description='list of values for the function input parameters')
    expected: Any = Field(description='the expected return value of the function')


class TestCasesJsonSchema(BaseModel):
    test_cases: List[TestCase] = Field(
        description='A list of testcases for the function. Each testcase includes '
                    'a dictionary with exactly two key and values:\n'
                    '"params" - the parameters of the function.\n '
                    '"expected" - the expected output of the function\n')


unittests_count = config.get("llm_as_coder__unittests_count")

unittest_function_chat_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are an expert in testing and providing test cases for unit testing of python functions"),
    ("system", "Do not add examples, usage or code. "
               "For each test case answer with list of input parameter values and an expected return value"),
    ("system", "Each test case will include two fields: 'params' with a list of input values "
               "and 'expected' with a value of the expected output."),
    ("system", """ for  this is a valid output format of two use-cases:
    [
        {{"params": [1, 2, 3], "expected": 6}},
        {{"params": [0, 0, 0], "expected": 0}}
    ]
     """),
    ("system", "If the parameter is of type string it shouldn't have leading or trailing spaces."),
    ("system", "Include at least one normal use-case"),
    ("system", "Response only the JSON structure"),
    ("user",
     "to test the function {function_name} with description {function_description} and the code ```{function_code}``` "
     "generate {unittests_count} test cases in JSON format.")
])


def generate_test_cases(function_name: str, function_description: str, function_code: str) -> List[Dict]:
    """Generate test cases using LLM with structured output."""

    structured_llm = coder_llm.with_structured_output(schema=TestCasesJsonSchema,
                                                      method="function_calling",
                                                      include_raw=False)

    try:
        code_unittests_chain = unittest_function_chat_prompt_template | structured_llm
        response = code_unittests_chain.invoke(
            {"function_name": function_name,
             "function_description": function_description,
             "function_code": function_code,
             "unittests_count": unittests_count})
        logger.info(
            "generate_test_cases returned: %s", response)
    except Exception as e:
        logger.error(
            f"generate_test_cases: Unexpected error while generating test cases: {e}")
        return False, []

    return True, [{"params": testcase.params, "expected": testcase.expected} for testcase in response.test_cases]


def check_unwanted_words(name: str, metadata: dict, description: str, code: str) -> bool:
    """Check if the tool's description, metadata, and code use unwanted words."""
    unwanted_words = ["error", "manager", "handler", "api", "key"]
    try:
        description = description.lower() if isinstance(description, str) else ""
        code = code.lower() if isinstance(code, str) else ""
        metadata_text = " ".join(str(value).lower(
        ) for value in metadata.values()) if isinstance(metadata, dict) else ""

        for word in unwanted_words:
            if word in description or word in metadata_text or word in code:
                logger.warning(
                    f"validate_tool_using_llm_as_a_coder: Tool '{name}' contains unwanted word '{word}'")
                return True  # Stop validation if any unwanted word is found

    except Exception as e:
        logger.error(
            f"validate_tool_using_llm_as_a_coder: Unexpected error while validating tool '{name}': {e}")
        return True  # Fail-safe return in case of an unexpected error

    return False


def validate_tool_using_llm_as_a_coder(name: str, metadata: dict, description: str, code: str) -> str:
    """Validate generated code using Docker isolation and LLM-generated tests."""
    logger.info(f"Validating function code:\n{name}\n")
    logger.info(f"code:\n{code}\n")
    logger.info(f"description:\n{description}\n")
    logger.info(f"metadata:\n{metadata}\n")

    # check if there are unwanted wards in the tools
    if check_unwanted_words(name, metadata, description, code):
        logger.error(
            f"validate_tool_using_llm_as_a_coder: Tool '{name}' contains unwanted words")
        return False

    # Create a Docker client
    logger.info("Validating the python code...")

    # Generate test according to the metadata
    success, unittests = generate_test_cases(name, description, code)
    if not success:
        logger.error("Failed to generate test cases")
        return False

    logger.info(f"Generated unittests:\n{unittests}\n")
    try:
        file_executor = FileExecutor(filename=f"{base_unittests_directory}/{name}_unittest_generated.py",
                                     file_content=code,
                                     file_metadata=metadata)
        for unittest in unittests:
            parameters = dict(
                zip(metadata['parameters']["required"], unittest["params"]))
            res = file_executor.execute_file(parameters)
            if res["return value"] != json.dumps(unittest['expected']):
                logger.error(f"!!!! The following Test failed:\n{unittest}\n!!!!!\n")
                return False
        logger.info("All tests passed")
        return True

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False

    # TODO: implement additional checks
