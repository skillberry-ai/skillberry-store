import logging

from agents.state import State
from llm.common import llm

logger = logging.getLogger(__name__)


# run the LLM with the tools results
def generate_response_using_tools(state: State):
    return {"messages": [llm.invoke(state["messages"])]}
