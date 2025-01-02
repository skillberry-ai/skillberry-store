import os
import json
import logging
from tools import count_chars

from langchain_core.agents import AgentActionMessageLog, AgentFinish
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks.tracers import ConsoleCallbackHandler
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from pydantic import BaseModel, Field
from langchain.globals import set_verbose, set_debug

logger = logging.getLogger(__name__)





debug=True
invoke_config=None

if debug is True:
    logging.basicConfig(level=logging.DEBUG)
    set_debug(True)
    set_verbose(True)
    invoke_config={'callbacks': [ConsoleCallbackHandler()]}

if "RITS_API_KEY" not in os.environ:
    print("RITS_API_KEY environment variable not set")
    print("Please set RITS_API_KEY environment variable")
    print("Additional info can be found on #rits-community slack")
    exit(1)

os.environ["RITS_API_URL"] = "https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com"

RITS_API_URL = os.environ["RITS_API_URL"]
RITS_API_KEY = os.environ["RITS_API_KEY"]

MODEL_PROVIDER = "ibm-granite"
MODEL = "granite-3.1-8b-instruct"

# MODEL_PROVIDER = "meta-llama"
# MODEL = "Llama-3.1-8B-Instruct"

# MODEL_PROVIDER = "mistralai"
# MODEL = "mistral-large-instruct-2407"

BASE_URL = f"{RITS_API_URL}/{MODEL.replace('.', '-').lower()}/v1"


TEMPERATURE = 0
NUMER_OF_ITERATIONS = 1

class ResponseJsonSchema(BaseModel):
    question: str = Field(description="The user question")
    answer: str = Field(description="The answer")
    suggested_functions: list = Field(description="Suggest functions that might assist in answering the question")
    concise_answer: str = Field(description="A concise answer")

llm = ChatOpenAI(
    model=f"{MODEL_PROVIDER}/{MODEL}",
    temperature=TEMPERATURE,
    max_retries=2,
    api_key='/',
    base_url=BASE_URL,
    default_headers={'RITS_API_KEY': RITS_API_KEY},
)

structured_llm = llm.with_structured_output(ResponseJsonSchema, method="function_calling", include_raw=False)

USER_PROMPT = "How many b`s are in this text: 'This is bla big blue blueberry project.'?"

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an helpful assistant"),
    ("system", "You are an expert in text analysis"),
    ("user", "{user_prompt}")
])

chain = prompt | structured_llm

print("==> Not using tools:")
print("====================")
for iteration in range(NUMER_OF_ITERATIONS):
    response = chain.invoke({"user_prompt": f"{USER_PROMPT}"}, config=invoke_config)
    print(f"Iteration {iteration}: {response}")
print("====================")


############## USING TOOLS ###############

def parse(output):
    # If no function was invoked, return to user
    if "tool_calls" not in output.additional_kwargs:
        return AgentFinish(return_values={"output": output.content}, log=output.content)

    # Parse out the *first* tool to call
    tool_call = output.additional_kwargs["tool_calls"][0]["function"]
    tool_call["name"] = "count_chars" ## TODO: remove ---<<< hack hack
    name = tool_call["name"]
    inputs = json.loads(tool_call["arguments"])

    # If the Response function was invoked, return to the user with the function inputs
    if name == "Response":
        return AgentFinish(return_values=inputs, log=str(tool_call))
    # Otherwise, return an agent action
    else:
        return AgentActionMessageLog(
            tool=name, tool_input=inputs, log="", message_log=[output]
        )

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an helpful assistant"),
    ("system", "You are an expert in text analysis"),
    ("user", "{user_prompt}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

tools = [count_chars]
llm_with_tools = llm.bind_tools(tools=tools,
                                tool_choice={"type": "function", "function": {"name": "count_chars"}},
                                strict=True)

agent = (
    {
        "user_prompt": lambda x: x["user_prompt"],
        # Format agent scratchpad from intermediate steps
        "agent_scratchpad": lambda x: format_to_openai_function_messages(
            x["intermediate_steps"]
        ),
    }
    | prompt
    | llm_with_tools
    | parse
)

agent_executor = AgentExecutor(agent=agent,
                               tools=tools,
                               verbose=debug,
                               handle_parsing_errors=True)

print("==> Using tools:")
print("====================")
for iteration in range(NUMER_OF_ITERATIONS):
    response = agent_executor.invoke({"user_prompt": f"{USER_PROMPT}"},
    config={'callbacks': [ConsoleCallbackHandler()]})
print("====================")
