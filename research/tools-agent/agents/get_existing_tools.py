import logging

from agents.state import State
from llm.common import llm

logger = logging.getLogger(__name__)



# search for tools using API calls (shortlist)
def get_existing_tools(state: State):
    return {"messages": [llm.invoke(state["messages"])]}
