import inspect
import logging
import re

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from agents.code_python_function import parse_docstring, base_python_coding_prompt_messages
from llm.common import coder_llm

logger = logging.getLogger(__name__)


class GeneralizedPythonFunctionResponseJsonSchema(BaseModel):
    code: str = Field(
        description="The generlized function code including a complete (Google style) docstring")


generalize_python_function_chat_prompt_template = ChatPromptTemplate.from_messages(
    base_python_coding_prompt_messages + [
        ("system", "Do not include any private information in the generated code"),
        ("system", "Create code that is generic and not specific for any one use-case"),
        ("system", "The code should be generic and broad enough to be used for multiple use-cases"),
        ("system", "The code should be generic and not specific to any one use-case"),
        ("system", "use common and known terms and values"),
        ("system", "For literals and hard-coded values include broad list to support multiple "
                   "use-cases"),
        ("user",
         "Use the description of this specific tool: {base_function_description}\n"
         "and the code of the specific tool: {base_function_code}\n"
         "to write new generic python code for the {generalized_name} function:\n")
    ])


def generalize_python_function_using_llm_as_a_coder(base_function_name: str,
                                                    base_function_description: str,
                                                    base_function_metadata: dict,
                                                    base_function_code: str):
    logger.info(f"Generalizing function: {base_function_name}\n"
                f" with description:\n{base_function_description}\n"
                f" with metadata:\n{base_function_metadata}\n")

    structured_llm = coder_llm.with_structured_output(schema=GeneralizedPythonFunctionResponseJsonSchema,
                                                      method="function_calling",
                                                      include_raw=False)

    try:
        generalized_name = base_function_name + "_generalized"
        generalize_python_function_chain = generalize_python_function_chat_prompt_template | structured_llm
        response = generalize_python_function_chain.invoke(
            {"base_function_description": base_function_description,
             "base_function_code": base_function_code,
             "generalized_name": generalized_name})
        generalized_code = response.code
        print(f"The code:\n\n {generalized_code}\n")
    except Exception as e:
        logger.error(
            "generalize_python_function_using_llm_as_a_coder failed with error: %s", e)
        return False, "", {}, {}, {}

    try:
        # Get the generalized metadata of the function from the docstring
        generalize_docstring, generalize_function_calling_api = parse_docstring(generalized_name, generalized_code)
        generalize_metadata = {
            "programming_language": "python",
            "packaging_format": "code",
            "name": generalized_name,
            "description": generalize_docstring,
            "parameters": generalize_function_calling_api["parameters"],
        }

        return True, generalized_name, generalize_docstring, generalize_metadata, generalized_code
    except Exception as e:
        logger.error(
            "generalize_python_function_using_llm_as_a_coder: docstring parsing failed with error: %s", e)
        return False, "", {}, {}, {}
