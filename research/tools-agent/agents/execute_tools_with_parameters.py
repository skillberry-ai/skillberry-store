import logging

from agents.state import State
from llm.common import llm

logger = logging.getLogger(__name__)


# execute the tools with the parameters
def execute_tools_with_parameters(state: State):
    return {"messages": [llm.invoke(state["messages"])]}
