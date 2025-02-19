import io
import json
import logging
import time

import requests

from agents.code_python_function import code_python_function_using_llm_as_a_coder
from agents.generalize_python_function import generalize_python_function_using_llm_as_a_coder
from agents.state import State
from agents.unittest_tools import validate_tool_using_llm_as_a_coder
from config.config_ui import config

logger = logging.getLogger(__name__)

# search for tools from the repository using API call (semantic search)
tools_repo_base_url = config.get("tools_repo_base_url")
post_file_url = f"{tools_repo_base_url}/file/"

headers = {"Accept": "application/json"}


def code_missing_tools(state: State):
    thinking_log = []
    logging.info(f"=======>>> code_missing_tools. starts <<<=======")
    need_to_generate_tools = state["need_to_generate_tools"]
    generated_tools = []

    logging.info(f"code_missing_tools: need_to_generate_tools: {need_to_generate_tools}")
    for need_to_generate_tool in need_to_generate_tools:
        name = need_to_generate_tool.name

        # A flag that allows (or disallows) to generate tools dynamically by the agent
        generate_tools_dynamically = config.get("llm_as_coder__generate_tools_dynamically")
        if not generate_tools_dynamically:
            thinking_log.append("I am not allowed to code new tools. ")
            logger.info(
                f"!!! generate_tools_dynamically is False: tool {name} will not be generated !!!")
            continue

        success, generate_tool_name, generate_tool_description = (
            generate_tool(need_to_generate_tool=need_to_generate_tool,
                          original_prompt=state["original_user_prompt"]))
        if not success:
            logger.error(f"code_missing_tools: tool {name} generation failed")
            thinking_log.append(f"I failed to code the tool {name}. ")
            continue

        #  (5) add the tool to the generated tools list
        generated_tools.append({
            "name": generate_tool_name,
            "description": generate_tool_description,
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


def generate_tool(need_to_generate_tool: dict, original_prompt: str = "", skip_validation=False) -> (bool, str, str):
    name = need_to_generate_tool.name
    description = need_to_generate_tool.description
    examples = need_to_generate_tool.examples

    logging.info(f"generate_tool: generating tool {name}")
    logging.info(f"description: {description}")
    logging.info(f"examples: {examples}")

    # (1) create tool using LLM-as-coder (based on the tool name and description)
    success, description, metadata, code = code_python_function_using_llm_as_a_coder(
        name=name,
        description=description,
        examples=examples)

    if not success:
        logger.error(f"generate_tool: tool {name} code python function failed")
        return False, "", ""

    # (2) generalize and remove PII from the tool
    # TODO: implement
    logging.info(f"generate_tool: generalizing tool {name}")
    success, name, description, metadata, code = generalize_python_function_using_llm_as_a_coder(
        base_function_name=name,
        base_function_description=description,
        base_function_metadata=metadata,
        base_function_code=code,
        original_prompt=original_prompt)

    if not success:
        logger.error(f"generate_tool: tool {name} code generalization failed")
        return False, "", ""

    # (3) validate the function and make sure it is valid to be added to the repo
    logging.info(f"generate_tool: validating tool {name}")
    if skip_validation is True:
        logging.info(f"generate_tool: skipping validating for tool {name}")
    else:
        success = validate_tool_using_llm_as_a_coder(name=name,
                                                     description=description,
                                                     metadata=metadata,
                                                     code=code)
        if not success:
            logger.error(f"generate_tool: tool {name} validation failed")
            return False, "", ""

    # The tool will be uploaded to the repo with a "private" name, and
    # used privately until it will be approved.
    # TODO: make sure that this is the accepted design
    timestamp = int(time.time())
    private_tool_name = f"{name}_at_{timestamp}.py"

    # (4) add the tool to the tool repository
    logging.info(f"generate_tool: adding tool {name} to the tool repository.\n"
                 f"Using private tool name {private_tool_name} until approval")
    success = add_tool_to_repo(private_tool_name=private_tool_name,
                               metadata=metadata,
                               description=description,
                               code=code)
    if not success:
        logger.error(
            f"generate_tool: add_tool_to_repo: tool {private_tool_name} upload to repo failed")
        return False, "", ""

    logging.info(f"generate_tool: tool {private_tool_name} added to the repository successfully.")
    return True, private_tool_name, description


def add_tool_to_repo(private_tool_name: str, metadata: json, description: str, code: str) -> bool:
    logger.info(f"add_tool_to_repo called for tool: {private_tool_name}")

    files = {'file': (private_tool_name, io.StringIO(code), 'text/plain')}

    response = requests.post(post_file_url,
                             headers=headers,
                             params={"file_description": description,
                                     "file_metadata": json.dumps(metadata)},
                             files=files)
    if response.status_code == 200:
        logger.info(f"add_tool_to_repo: tool {private_tool_name} uploaded successfully")
        return True
    else:
        logger.error(
            f"add_tool_to_repo: tool {private_tool_name} upload failed with status code {response.status_code}")
        return False
