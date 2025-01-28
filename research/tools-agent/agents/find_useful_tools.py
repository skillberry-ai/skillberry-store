import logging
from typing import List, Dict

from pydantic import BaseModel, Field

from agents.state import State
from llm.common import llm
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

find_useful_tools_chat_prompt_template = ChatPromptTemplate([
    ("system", "You are a helpful assistant"),
    ("system", "You are expert in finding functions and tools that are generated from code"),
    ("system", "For each tool and function that you suggest, "
               "you specify exactly the name of the tool in hungarian notation and a crisp description of the tool"),
    ("system", "Response only using json format"),
    ("user", "List deterministic tools and functions that helps to response to the prompt: \"{user_prompt}\""),
])


class FindingToolsResponseJsonSchema(BaseModel):
    suggested_tools: List[Dict[str, str]] = Field(
        description="A list of dictionaries, each dictionary containing exactly two fields."
                    "(1) The name of the function and (2) the description of the function"
    )


# plan what tools can help to resolve the user prompt
# get for each of the tools the name and description
def find_useful_tools(state: State):
    logger.info("find_useful_tools called")
    structured_llm = llm.with_structured_output(schema=FindingToolsResponseJsonSchema,
                                                method="function_calling",
                                                include_raw=False)

    find_useful_tools_chain = find_useful_tools_chat_prompt_template | structured_llm
    response = find_useful_tools_chain.invoke({"user_prompt": state["original_user_prompt"]})
    logger.info("find_useful_tools returned: %s", response)
    return {"suggested_tools": response.suggested_tools}

# the requirements
