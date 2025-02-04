import logging

from langgraph.graph import StateGraph, START, END

from agents.code_missing_tools import code_missing_tools
from agents.execute_tools_with_parameters import execute_tools_with_parameters
from agents.find_useful_tools import find_useful_tools
from agents.find_existing_tools import find_existing_tools
from agents.state import State

# from tools.graph_visualization import graph_visualization

logger = logging.getLogger(__name__)

tools_agentic_graph = None


def define_tools_agentic_graph():
    global tools_agentic_graph
    # Define the agentic graph
    graph_builder = StateGraph(State)
    graph_builder.add_node("find_useful_tools", find_useful_tools)
    graph_builder.add_node("find_existing_tools", find_existing_tools)
    graph_builder.add_node("code_missing_tools", code_missing_tools)
    graph_builder.add_node("execute_tools_with_parameters",
                           execute_tools_with_parameters)

    graph_builder.add_edge(START, "find_useful_tools")
    graph_builder.add_edge("find_useful_tools", "find_existing_tools")
    graph_builder.add_edge("find_existing_tools", "code_missing_tools")
    graph_builder.add_edge("code_missing_tools",
                           "execute_tools_with_parameters")
    graph_builder.add_edge("execute_tools_with_parameters", END)

    # Compile the agentic graph
    tools_agentic_graph = graph_builder.compile()
    logger.info("Tools agentic graph compiled")
    return tools_agentic_graph

# Visualize the agentic graph
# graph_visualization(graph)


def stream_graph_updates(input_messages: str):

    # print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")
    # print(f"{input_messages}")
    # print("&&&&&&&&&&&&&&&&&&&&&&&&&&&&&")

    for event in tools_agentic_graph.stream({"original_user_prompt": input_messages,
                                             "messages_history": input_messages}):
        # print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        # print(f"{input_messages}")
        # print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        for value in event.values():
            logging.info("==> stream_graph_updates: event.value: [%s]", value)
    return event.values()
