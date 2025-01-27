import logging

from agents.state import State
from llm.common import llm

logger = logging.getLogger(__name__)

# create missing tools using LLM ( based on name and description)
# add the tools to the repo

def code_missing_tools(state: State):
    return {"messages": [llm.invoke(state["messages"])]}


