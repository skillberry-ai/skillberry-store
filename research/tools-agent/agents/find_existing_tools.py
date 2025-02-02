import logging
import requests

from agents.state import State
from agents.tools_service_api import search_tools, get_tool_description
from llm.common import llm

logger = logging.getLogger(__name__)

# search for tools from the repository using API call (semantic search)
base_url = "http://9.148.245.32:8000"
search_url = f"{base_url}/description/search"

headers = {"Content-Type": "application/json"}
max_numer_of_results = 5
similarity_threshold = 1

def find_existing_tools(state: State):
    existing_tools = []
    need_to_generate_tools = []
    for suggested_tool in state["suggested_tools"]:
        name = suggested_tool["name"]
        description = suggested_tool["description"]
        logger.info(f"find_existing_tools called for tool: {name}")

        # issue get request against the url with `search_term` equals to the name of the suggested tool
        found_tools = search_tools(base_url, name, description, max_numer_of_results, similarity_threshold)
        if found_tools is not None and len(found_tools) > 0:
            logger.info("find_existing_tools returned: %s", found_tools)
            for found_tool in found_tools:
                logger.info(f"Found existing tool: {found_tool}")
                found_tool["search_term_name"] = name
                found_tool["search_term_description"] = description
                found_tool["name"] = found_tool["filename"]
                # append only if the tool is not already in the list of existing tools
                if found_tool not in existing_tools:
                    existing_tools.append(found_tool)
        else:
            # Can't find the tools, adding the tools to the list of need_to_generate_tools tools
            logger.info(f"Can't find the suggested_tool {name}")
            logger.info(f"Adding to the list of need_to_generate_tools tools")
            need_to_generate_tools.append(suggested_tool)
            continue

    return {"existing_tools": existing_tools,
            "need_to_generate_tools": need_to_generate_tools}
