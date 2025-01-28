import logging
from langgraph.graph import StateGraph, START, END
from langchain.globals import set_verbose, set_debug
from langchain.callbacks.tracers import ConsoleCallbackHandler

from agents.find_useful_tools import find_useful_tools
from agents.find_existing_tools import find_existing_tools
from agents.state import State
from llm.common import llm, check_llm_communication

from tools.graph_visualization import graph_visualization

logger = logging.getLogger(__name__)

debug = True
invoke_config = None

if debug is True:
    logging.basicConfig(level=logging.DEBUG)
    set_debug(True)
    set_verbose(True)
    invoke_config = {'callbacks': [ConsoleCallbackHandler()]}
    print("Debug mode enabled")
else:
    logging.basicConfig(level=logging.ERROR)
    set_debug(False)
    set_verbose(False)
    invoke_config = None


# Define the agentic graph
graph_builder = StateGraph(State)
graph_builder.add_node("find_useful_tools", find_useful_tools)
graph_builder.add_node("find_existing_tools", find_existing_tools)
graph_builder.add_edge("find_useful_tools", "find_existing_tools")

graph_builder.add_edge(START, "find_useful_tools")
graph_builder.add_edge("find_existing_tools", END)

# Compile the agentic graph
tools_agentic_graph = graph_builder.compile()
logger.info("Tools agentic graph compiled")

# Visualize the agentic graph
# graph_visualization(graph)


def stream_graph_updates(_user_input: str):
    for event in tools_agentic_graph.stream({"original_user_prompt": _user_input,
                                             "messages_history": []}):
        for value in event.values():
            print("Assistant:", value)


# main function
def main():
    if not check_llm_communication():
        logger.error("Can't communicate with the LLM, please check network, VPN, access keys etc.")
        exit(2)

    user_input = "What is the 4th prime number"
    stream_graph_updates(user_input)


if __name__ == "__main__":
    main()
