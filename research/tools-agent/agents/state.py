from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph import add_messages


class State(TypedDict):
    original_user_prompt: str
    messages_history: Annotated[list, add_messages]

