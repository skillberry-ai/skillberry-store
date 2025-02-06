import os
import json
import logging
from tools import count_chars
from langchain_core.messages.tool import ToolCallChunk
from langchain_core.agents import AgentActionMessageLog, AgentFinish
from langchain_core.messages import HumanMessage, SystemMessage, AIMessageChunk
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks.tracers import ConsoleCallbackHandler
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from pydantic import BaseModel, Field
from langchain.globals import set_verbose, set_debug
import json

logger = logging.getLogger(__name__)

debug = False
invoke_config = None

if debug is True:
    logging.basicConfig(level=logging.DEBUG)
    set_debug(True)
    set_verbose(True)
    invoke_config = {'callbacks': [ConsoleCallbackHandler()]}
    print("Debug mode enabled")
else:
    logging.basicConfig(level=logging.ERROR)
    set_debug(False)
    set_verbose(False)
    invoke_config = None

if "RITS_API_KEY" not in os.environ:
    print("RITS_API_KEY environment variable not set")
    print("Please set RITS_API_KEY environment variable")
    print("Additional info can be found on #rits-community slack")
    exit(1)

os.environ["RITS_API_URL"] = "https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com"

RITS_API_URL = os.environ["RITS_API_URL"]
RITS_API_KEY = os.environ["RITS_API_KEY"]

# MODEL_PROVIDER = "ibm-granite"
# MODEL = "granite-3.1-8b-instruct"

MODEL_PROVIDER = "meta-llama"
MODEL = "llama-3-1-70b-instruct"
# MODEL = "Llama-3.1-8B-Instruct"

# MODEL_PROVIDER = "mistralai"
# MODEL = "mistral-large-instruct-2407"

BASE_URL = f"{RITS_API_URL}/{MODEL.replace('.', '-').lower()}/v1"
TEMPERATURE = 0

print(f"==> 0. Configuration:\n"
      f"==> =================\n"
      f"==> Using model: {MODEL_PROVIDER}/{MODEL}\n"
      f"==> EndPoint: {BASE_URL}\n"
      f"==> Temperature: {TEMPERATURE}\n"
      f"==> =================\n\n")

llm = ChatOpenAI(
    model=f"{MODEL_PROVIDER}/{MODEL}",
    temperature=TEMPERATURE,
    max_retries=2,
    api_key='/',
    base_url=BASE_URL,
    default_headers={'RITS_API_KEY': RITS_API_KEY},
)

############## Asking the basic question ###############

USER_QUESTION = "How many 'b' characters are in the text: 'This is the blablabla best big-blue blueberry project'?"


# USER_PROMPT = "Is 1299709 a prime number?"


class ResponseJsonSchema(BaseModel):
    question: str = Field(description="The user question")
    answer: str = Field(description="The answer to the question")
    suggested_functions: list = Field(description="Names of deterministic functions "
                                                  "that can be used to answer the question")


structured_llm = llm.with_structured_output(schema=ResponseJsonSchema,
                                            method="function_calling",
                                            include_raw=False,
                                            strict=True)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an helpful assistant"),
    ("system", "You are an expert in text analysis"),
    ("user", "Answer the following question: {user_prompt}")
])

chain = prompt | structured_llm

print(f"==> 1. Asking the question:\n"
      f"    {USER_QUESTION}\n"
      f"    > Note: Using structured output, without tools\n"
      f"    > Note: In addition, asking for supportive tools\n"
      f"==> =============================================\n\n")

print(f"==> Invoking chain\n")
response = chain.invoke({"user_prompt": f"{USER_QUESTION}"}, config=invoke_config)
print(f"==> Chain completed\n")
print(json.dumps(response.model_dump(), indent=4))

TOOL_NAME = response.suggested_functions[0]

print(f"==> =============================================\n\n")

############## Build the relevant tools  ###############
BUILDING_TOOL_PROMPT = f"A generic python function called '{TOOL_NAME}' to assist in " \
                       f"answering the question: \"{USER_QUESTION}\""


class ResponseJsonSchema(BaseModel):
    description: str = Field(description="The Docstrings of the function")
    code: str = Field(description="The function code including the Docstrings without examples or usage")


structured_llm = llm.with_structured_output(schema=ResponseJsonSchema,
                                            method="function_calling",
                                            include_raw=False,
                                            strict=True)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an helpful assistant"),
    ("system", "You are an expert in writing code in python"),
    ("system", "Make sure to add meaningful Docstrings to the function"
               "The Docstrings will include the function description, input Parameters, and Return values"),
    ("system", "Include the Docstrings as part of the function code"),
    ("system", "Do not add examples or usage, answer with only python code"),
    ("user", "Write code for the following function: {user_prompt}")
])

chain = prompt | structured_llm

print(f"==> 2. Write code for the following:\n"
      f"    {BUILDING_TOOL_PROMPT}\n"
      f"    > Note: Using structured output, without tools\n"
      f"==> =============================================\n\n")

print(f"==> Invoking chain\n")
response = chain.invoke({"user_prompt": f"{BUILDING_TOOL_PROMPT}"}, config=invoke_config)
print(f"==> Chain completed\n")
print(json.dumps(response.model_dump(), indent=4))

TOOL_DESCRIPTION = response.description
TOOL_CODE = response.code

# defining the function dynamically.
# This will allow us to use the function in the next phase using LLM function calling

namespace = {}

# Wrap the generated code with langchain @tool decorator
TOOL_CODE_WITH_LANGCHAIN_DECORATOR = (f"from langchain_core.tools import tool\n\n"
                                      f"@tool\n\n"
                                      f"{TOOL_CODE}")
exec(TOOL_CODE_WITH_LANGCHAIN_DECORATOR, namespace)

# Now extract the function from the namespace
if TOOL_NAME not in namespace:
    raise ValueError(f"Function {TOOL_NAME} not found in namespace")

generated_tool = namespace[TOOL_NAME]

# Try to call the tool to make sure it is valid
try:
    return_value = generated_tool.invoke({"text": "This is the blablabla best big-blue blueberry project", "char": "b"})
    if return_value != 8:
        raise ValueError(f"Tool {TOOL_NAME} is not working as expected")
    print(f"==> The function is valid\n")
except  Exception as e:
    print(f"==> =============================================\n\n")
    print(f"==> The function is invalid\n"
          f"==> {e}\n"
          f"==> =============================================\n\n")
    exit(1)


############## USING THE FUNCTION TO ANSWER THE QUESTION ###############

def parse(output):
    # If no function was invoked, return to user
    if "tool_calls" not in output.additional_kwargs:
        return AgentFinish(return_values={"output": output.content}, log=output.content)

    # Parse out the *first* tool to call
    tool_call = output.additional_kwargs["tool_calls"][0]["function"]
    name = tool_call["name"]
    inputs = json.loads(tool_call["arguments"])
    # If the Response function was invoked, return to the user with the function inputs
    if name == "Response":
        return AgentFinish(return_values=inputs, log=str(tool_call))
    # Otherwise, return an agent action
    else:
        print(f"=====> The agentic flow will now call the function {name} with args {inputs}")
        message = AIMessageChunk(content="", tool_call_chunks=[ToolCallChunk(name=name,
                                                                             id="1",
                                                                             args=json.dumps(inputs),
                                                                             index=1)])
        return AgentActionMessageLog(
            tool=name, tool_input=inputs, log="", message_log=[message]
        )


prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an helpful assistant"),
    ("system", "You are an expert in text analysis"),
    ("system", "Response in json format"),
    ("user", "Answer the following question: {user_prompt}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

tools = [generated_tool]
llm_with_tools = llm.bind_tools(tools=tools,
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

print(f"==> 3. Asking the question using tools:\n"
      f"    {USER_QUESTION}\n"
      f"    > Note: Using function calling with generated tool: {TOOL_NAME}\n"
      f"==> =============================================\n\n")
print(f"==> Invoking agent\n")
response = agent_executor.invoke({"user_prompt": f"{USER_QUESTION}"},
                                 config=invoke_config)
print(f"==> Agent completed\n")
print(json.dumps(response, indent=4))

print(f"==> =============================================\n\n")
