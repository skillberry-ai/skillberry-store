import logging

from agents.state import State
from llm.common import llm

logger = logging.getLogger(__name__)


# plan what tools can help to resolve the user prompt
# get for each of the tools the name and description
def find_useful_tools(state: State):
    return {"messages": [llm.invoke(state["messages"])]}


