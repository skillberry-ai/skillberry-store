import logging
import requests

from agents.state import State
from llm.common import llm

logger = logging.getLogger(__name__)

# search for tools from the repository using API call (semantic search)

url = "http://9.148.245.32:8000/description/search"
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

        response = requests.get(url, headers=headers, params={"search_term": f"{name}: {description}",
                                                              "max_numer_of_results": max_numer_of_results,
                                                              "similarity_threshold": similarity_threshold})
        if response.status_code == 200 and len(response.json()) > 0:
            logger.info("find_existing_tools returned: %s", response.json())
            for found_tool in response.json():
                logger.info(f"Found existing tool: {found_tool}")
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
