import logging
from typing import List

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
    ("system", "Do not suggest tools and functions that performs error handling"),
    ("system", "Do not suggest tools and functions that are general helper tools"),
    ("system", "Do not suggest tools and functions that requires keys or access to external services"),
    ("system", "Suggest minimal amount of tools. Suggest simple tools and simple functions"),
    ("system", "Do not suggest tools and functions that are complicated"),
    ("system", "Response only using json format"),
    ("user",
     "List deterministic tools and functions that helps to response to the prompt: \"{user_prompt}\""),
])


class SuggestedTool(BaseModel):
    name: str = Field(description='the name of the tool')
    description: str = Field(description='the description of the tool')
    examples: str = Field(description='Usage examples of the tool')


class FindingToolsResponseJsonSchema(BaseModel):
    suggested_tools: List[SuggestedTool] = Field(
        description='A list of suggested tools.\n'
                    'Each suggested tool includes a dictionary with exactly three key and values:\n'
                    '"name" - the name of the tool.\n '
                    '"description" - the description of the tool\n'
                    '"examples" - Usage examples of the tool\n'
    )


# plan what tools can help to resolve the user prompt
# get for each of the tools the name and description
def find_useful_tools(state: State):
    thinking_log = []
    logging.info(f"=======>>> find_useful_tools. started <<<=======")
    logger.info("find_useful_tools called")
    structured_llm = llm.with_structured_output(schema=FindingToolsResponseJsonSchema,
                                                method="function_calling",
                                                include_raw=False)

    find_useful_tools_chain = find_useful_tools_chat_prompt_template | structured_llm
    user_content = state["original_user_prompt"]["content"]
    logger.info(f"finding useful tools for the user content: {user_content}")
    response = find_useful_tools_chain.invoke({"user_prompt": user_content})
    logger.info("find_useful_tools returned: %s", response)

    if response.suggested_tools is not None:
        thinking_log.append("I think that there are tools that "
                            "can help me to reduce hallucinations and be more accurate.")
        tool_descriptions = ""
        for i, tool in enumerate(response.suggested_tools):
            tool_descriptions += f"{tool.description}"
            if i < len(response.suggested_tools) - 1:
                tool_descriptions += ", and a tool that "
            else:
                tool_descriptions += "."

        thinking_log.append(f"I think that the tools are: a tool that {tool_descriptions}")

    logging.info(f"=======>>> find_useful_tools. ended <<<=======")
    return {"suggested_tools": response.suggested_tools,
            "thinking_log": thinking_log}
