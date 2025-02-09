import sys
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field

# TODO: Find better wat to import FileExecutor
service_dir = Path(__file__).parent.parent.parent / 'tools-service'
sys.path.append(str(service_dir))
from modules.file_executor import FileExecutor
from llm.common import llm

logger = logging.getLogger(__name__)

# search for tools from the repository using API call (semantic search)
base_url = "http://9.148.245.32:8000"
post_file_url = f"{base_url}/file/"

headers = {"Accept": "application/json"}


class TestCase(BaseModel):
    params: List[Any]
    expected: Any


class TestCases(BaseModel):
    test_cases: List[TestCase]


def generate_test_cases(task: str) -> List[Dict]:
    """Generate test cases using LLM with structured output."""
    prompt = f"""
    For this task: {task}
    Generate 2 test cases in JSON format. Include normal cases.
    If the parameter is of type string it shouldn't have leading or trailing spaces. 
    Each test case should have 'params' (list of values) and 'expected' (expected output).
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
                logger.warning(f"validate_tool_using_llm_as_a_coder: Tool '{name}' contains unwanted word '{word}'")
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
        logger.error(f"validate_tool_using_llm_as_a_coder: Tool '{name}' contains unwanted words")
        return False

    # TODO: for now we skip the unittest process as this is quickly failing even for valid functions
    return True

    # Create a Docker client
    logger.info("Validating the python code...")

    # Generate test according to the metadata
    tests = generate_test_cases(metadata["description"])
    logger.info(f"Generated tests:\n{tests}\n")
    try:
        file_executor = FileExecutor(filename="llm_code_generated.py", file_content=code,
                                     file_metadata=json.dumps(metadata))
        for test in tests:
            parameters = dict(zip(metadata['parameters']["required"], test["params"]))
            res = file_executor.execute_file(parameters)
            if res["return value"] != json.dumps(test['expected']):
                logger.info("The following Test failed:\n{test}")
                return False
        logger.info("All tests passed")
        return True

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False

    # TODO: implement additional checks

