import logging

from agents.state import State
from llm.common import llm

logger = logging.getLogger(__name__)

# (1) create missing tools using LLM-as-coder (based on names and descriptions)
# (2) generalize and remove PII from the tools
# (3) validate the function and make sure it is valid to be added to the repo
# (4) add the tool to the tools repository


def code_missing_tools(state: State):
    return {}


