import logging

from agents.state import State
from llm.common import llm
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

find_useful_tools_prompt_template = ChatPromptTemplate([
    ("system", "You are a helpful assistant"),
    ("system", "You are expert in finding functions and tools"),
    ("system", "For each tool you find, you will specify, the name of the tool and a description of the tool"),
    ("system", "Response using json format"),
    ("user", "List deterministic tools and functions that helps to answer the question {question}"),
])


# plan what tools can help to resolve the user prompt
# get for each of the tools the name and description
def find_useful_tools(state: State):
    logger.info("find_useful_tools called with state: %s", state)
    state["messages"].append({"role": "user",
                              "content": find_useful_tools_prompt_template.format(question=state["messages"][-1].content)})
    messages = [llm.invoke(state["messages"])]
    logger.info("find_useful_tools returned: %s", messages)
    return {"messages": messages}
