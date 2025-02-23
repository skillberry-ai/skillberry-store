import inspect
import logging
import re
from typing import List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from agents.code_python_function import parse_docstring, base_python_coding_prompt_messages
from llm.common import coder_llm

logger = logging.getLogger(__name__)


class GenerateGeneralizedPromptsJsonSchema(BaseModel):
    example_prompts: List[str] = Field(description="List of example prompts")


generate_generalized_examples_chat_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are an expert in text analysis and generalization of examples"),
    ("system", "Do not include any private information in the examples you provide"),
    ("system", "use common and known terms and values"),
    ("user",
     "Build additional examples based on known standards and general terms"
     "from the example prompt {base_prompt_content} examples:\n")
])


def generate_generalized_prompt_examples(base_prompt_content: str):
    structured_llm = coder_llm.with_structured_output(schema=GenerateGeneralizedPromptsJsonSchema,
                                                      method="function_calling",
                                                      include_raw=False)

    try:
        generate_generalized_examples_chain = generate_generalized_examples_chat_prompt_template | structured_llm
        response = generate_generalized_examples_chain.invoke({"base_prompt_content": base_prompt_content})
        generalized_prompt_examples = response.example_prompts
        print(f"The prompt examples:\n\n {generalized_prompt_examples}\n")
    except Exception as e:
        logger.error("generate_generalized_prompt_examples failed with error: %s", e)
        return False, []

    return True, generalized_prompt_examples


class GeneralizedPythonFunctionResponseJsonSchema(BaseModel):
    code: str = Field(
        description="The generalized function code including a complete (Google style) docstring")


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
         "and the name of the specific tool name: {base_function_name}\n"
         "and the code of the specific tool: {base_function_code}\n"
         "to write new generic python code for the {generalized_function_name} function: that supports the following"
         "example prompts {generalized_prompt_examples}\n")
    ])


def generalize_python_function_using_llm_as_a_coder(base_function_name: str,
                                                    base_function_description: str,
                                                    base_function_metadata: dict,
                                                    base_function_code: str,
                                                    original_prompt: str):
    logger.info(f"Generalizing function: {base_function_name}\n"
                f" with description:\n{base_function_description}\n"
                f" with metadata:\n{base_function_metadata}\n")

    if original_prompt is not None and original_prompt != "" and "content" in original_prompt:
        original_prompt_content = original_prompt["content"]
        success, generalized_prompt_examples = generate_generalized_prompt_examples(original_prompt_content)
        if not success:
            logger.error("generalized_example_prompts failed")
            return False, "", {}, {}, {}
    else:
        generalized_prompt_examples = ""

    structured_llm = coder_llm.with_structured_output(schema=GeneralizedPythonFunctionResponseJsonSchema,
                                                      method="function_calling",
                                                      include_raw=False)

    try:
        generalized_function_name = base_function_name + "_generalized"
        generalize_python_function_chain = generalize_python_function_chat_prompt_template | structured_llm
        response = generalize_python_function_chain.invoke(
            {"base_function_description": base_function_description,
             "base_function_code": base_function_code,
             "base_function_name": base_function_name,
             "generalized_function_name": generalized_function_name,
             "generalized_prompt_examples": generalized_prompt_examples})
        generalized_code = response.code
        print(f"The code:\n\n {generalized_code}\n")
    except Exception as e:
        logger.error("generalize_python_function_using_llm_as_a_coder failed with error: %s", e)
        return False, "", {}, {}, {}

    try:
        # Get the generalized metadata of the function from the docstring
        generalize_description, generalize_function_calling_api = (
            parse_docstring(generalized_function_name, generalized_code))
        generalize_metadata = {
            "programming_language": "python",
            "packaging_format": "code",
            "name": generalized_function_name,
            "description": generalize_description,
            "parameters": generalize_function_calling_api["parameters"],
            "base_function_metadata": base_function_metadata,
        }

        return True, generalized_function_name, generalize_description, generalize_metadata, generalized_code
    except Exception as e:
        logger.error(
            "generalize_python_function_using_llm_as_a_coder: docstring parsing failed with error: %s", e)
        return False, "", {}, {}, {}
