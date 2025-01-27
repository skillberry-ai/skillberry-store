import logging
from langgraph.graph import StateGraph, START, END
from langchain.globals import set_verbose, set_debug
from langchain.callbacks.tracers import ConsoleCallbackHandler

from agents.find_useful_tools import find_useful_tools
from agents.get_existing_tools import get_existing_tools
from agents.state import State
from llm.common import llm

from tools.graph_visualization import graph_visualization

logger = logging.getLogger(__name__)

debug = False
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
graph_builder.add_node("get_existing_tools", get_existing_tools)
graph_builder.add_edge(START, "find_useful_tools")
graph_builder.add_edge("find_useful_tools", "get_existing_tools")
graph_builder.add_edge("get_existing_tools", END)

# Compile the agentic graph
graph = graph_builder.compile()
logger.info("Graph compiled")

# Visualize the agentic graph
# graph_visualization(graph)

try:
    llm.invoke("try to communicate with the llm")
    logger.info("LLM is working")
except Exception as e:
    logger.error(f"LLM is not working {e}")
    exit(2)


def stream_graph_updates(_user_input: str):
    for event in graph.stream({"messages": [{"role": "user", "content": _user_input}]}):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)


# main function
def main():
    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            stream_graph_updates(user_input)

        except:
            user_input = "Why the user didn't ask a question?"
            print("User: " + user_input)
            stream_graph_updates(user_input)
            break


if __name__ == "__main__":
    main()
