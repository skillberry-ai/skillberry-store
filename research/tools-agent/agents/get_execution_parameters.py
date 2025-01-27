import logging

from agents.state import State
from llm.common import llm

logger = logging.getLogger(__name__)


# Using all the tools ( generated and existing) get from the LLM the parameters to execute the tools
def get_execution_parameters(state: State):
    return {"messages": [llm.invoke(state["messages"])]}
