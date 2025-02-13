from typing_extensions import TypedDict
from typing import Annotated, List, Dict
from langgraph.graph import add_messages
from langchain_core.messages import HumanMessage, AIMessage


class State(TypedDict):

    thinking_log: Annotated[list[AIMessage], add_messages]
    original_user_prompt: HumanMessage
    chat_history: list[HumanMessage | AIMessage]

    suggested_tools: List[Dict[str, str]]

    existing_tools: List[Dict[str, str]]
    need_to_generate_tools: List[Dict[str, str]]
    generated_tools: List[Dict[str, str]]

    messages_history: Annotated[list[HumanMessage | AIMessage], add_messages]
