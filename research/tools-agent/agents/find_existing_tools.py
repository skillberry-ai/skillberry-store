import logging

from agents.state import State
from agents.tools_service_api import search_tools
from config.config_ui import config

logger = logging.getLogger(__name__)

# search for tools from the repository using API call (semantic search)
base_url = "http://9.148.245.32:8000"
search_url = f"{base_url}/description/search"

headers = {"Content-Type": "application/json"}
max_tools_count = config.get("advanced__max_tools_count")
similarity_threshold = config.get("advanced__similarity_threshold")


def find_existing_tools(state: State):
    thinking_log = []
    logging.info(f"=======>>> find_existing_tools. started <<<=======")
    existing_tools = []
    need_to_generate_tools = []

    try:
        for suggested_tool in state["suggested_tools"]:
            name = suggested_tool.name
            description = suggested_tool.description
            examples = suggested_tool.examples

            logger.info(f"find_existing_tools called for tool: {name}")
            # issue get request against the url with `search_term` equals to the name of the suggested tool
            found_tools = search_tools(
                base_url, name, description, max_tools_count, similarity_threshold)

            if found_tools is not None and len(found_tools) > 0:
                logger.info("find_existing_tools returned: %s", found_tools)

                for found_tool in found_tools:
                    logger.info(f"Found existing tool: {found_tool}")

                    found_tool["search_term_name"] = name
                    found_tool["search_term_description"] = description
                    found_tool["search_term_examples"] = examples

                    found_tool["name"] = found_tool["filename"]

                    # append only if the tool is not already in the list of existing tools
                    if not any(tool["name"] == found_tool["name"] for tool in existing_tools):
                        existing_tools.append(found_tool)
            else:
                # Can't find the tools, adding the tools to the list of need_to_generate_tools tools
                logger.info(f"Can't find the suggested_tool {name}")
                logger.info(f"Adding to the list of need_to_generate_tools tools")
                need_to_generate_tools.append(suggested_tool)
                continue
    except Exception as e:
        logging.error(f"Error while find_existing_tools: {e}")

    if len(existing_tools) > 0:
        thinking_log.append("I found existing approved tools that I will use.")
        tool_names = ""
        for i, tool in enumerate(existing_tools):
            tool_name = tool["name"].split('.py')[0] if '.py' in tool["name"] else tool["name"]
            tool_names += f"{tool_name}"
            if i < len(existing_tools) - 1:
                tool_names += ", and a tool named "
            else:
                tool_names += "."

        thinking_log.append(f"A tool named {tool_names}")

    logging.info(f"=======>>> find_existing_tools. ended <<<=======")
    return {"existing_tools": existing_tools,
            "need_to_generate_tools": need_to_generate_tools,
            "thinking_log": thinking_log}
