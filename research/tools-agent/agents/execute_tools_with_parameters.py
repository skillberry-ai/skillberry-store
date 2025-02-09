import re
import json
import logging
import inspect
import requests

from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain_core.agents import AgentFinish, AgentActionMessageLog
from langchain_core.messages import AIMessageChunk, ToolCallChunk
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import tool

from agents.state import State
from agents.tools_service_api import get_tool_metadata
from llm.common import llm

logger = logging.getLogger(__name__)

base_url = "http://9.148.245.32:8000"

headers = {"Accept": "application/json"}

execute_tools_with_parameters_chat_prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are an helpful assistant"),
    ("system", "You are an expert in text analysis"),
    ("system", "Response in json format"),
    ("{chat_history}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])


@tool
def fake_tool():
    """
    This is a fake tool that does nothing.
    If is used so that the file will import the needed libraries from:
        import inspect
        import requests
        from langchain.tools import tool

    """
    frame = inspect.currentframe()
    print(frame)
    requests.get("do not delete this call", json=json.loads(""))
    return "fake_tool"


def parse(output):
    # If no function was invoked, return to user
    if "tool_calls" not in output.additional_kwargs:
        return AgentFinish(return_values={"output": output.content}, log=output.content)

    # Parse out the *first* tool to call
    tool_call = output.additional_kwargs["tool_calls"][0]["function"]
    name = tool_call["name"]
    if tool_call["arguments"] != "":
        inputs = json.loads(tool_call["arguments"])
    else:
        inputs = {}
    # If the Response function was invoked, return to the user with the function inputs
    if name == "Response":
        return AgentFinish(return_values=inputs, log=str(tool_call))
    # Otherwise, return an agent action
    else:
        logging.info(
            f"=====> The agentic flow will now call the function {name} with args {inputs}")
        message = AIMessageChunk(content="", tool_call_chunks=[ToolCallChunk(name=name,
                                                                             id="1",
                                                                             args=json.dumps(
                                                                                 inputs),
                                                                             index=1)])
        return AgentActionMessageLog(tool=name, tool_input=inputs, log="", message_log=[message])


def create_function_from_string(code: str, func_name: str, scope: dict):
    exec(code, globals(), scope)
    return scope.get(func_name)


def define_tool_dynamically(tool_name: str, arguments_string: str, scope: dict, _base_url: str):
    """
    Invoke a local tool based on OpenAI parameters definition to be used by the agentic workflow
    """

    # the function will use rest against the tool_service_api to execute the tool
    # with the required parameters
    tool_function_name = re.sub(r"[. ]", "_", tool_name)
    python_code = f"""
import requests
import json
import inspect
from langchain.tools import tool

headers = {{
    "accept": "application/json",
    "Content-Type": "application/json"
}}

@tool
def {tool_function_name} {arguments_string}:
    \"\"\"
    This function executes {tool_function_name} with the following arguments:

    Arguments:
    {arguments_string}
    \"\"\"

    frame = inspect.currentframe()
    args, _, _, values = inspect.getargvalues(frame)
    param_dict = {{arg: values[arg] for arg in args}}
    execute_tool_url = f"{_base_url}/execute/{tool_name}"
    response = requests.post(
        execute_tool_url, headers=headers, json=param_dict)
    if response.status_code == 200:
        response_json = response.json()
        return response_json["return value"]
    else:
        return None
"""
    _tool = create_function_from_string(python_code, tool_function_name, scope)
    return _tool


def generate_dynamic_tool(tool: dict, scope: dict, _base_url: str):
    name = tool["name"]
    metadata = get_tool_metadata(base_url, name)
    arguments_string = generate_function_arguments_from_metadata(metadata)
    tool_func = define_tool_dynamically(tool_name=name,
                                        arguments_string=arguments_string,
                                        scope=scope,
                                        _base_url=base_url)
    return tool_func


# execute the tools with the parameters
def execute_tools_with_parameters(state: State):
    logging.info(
        f"=======>>> execute_tools_with_parameters. started <<<=======")
    tools = []
    scope = {}

    for _tool in state["existing_tools"]:
        try:
            logging.info(
                f"existing_tools: Generating local tool stub {_tool['name']}")
            tool_func = generate_dynamic_tool(_tool, scope, base_url)
            tools.append(tool_func)
        except Exception as e:
            logging.error(
                f"existing_tools: Error while generate_dynamic_tool {_tool['name']}: {e}")

    # At this stage, generated tools are not being added to the
    # repo as "useful" immediately, hence we can't use them for the
    # current prompt.
    # TODO: once we improve the validation process we will add them and use them
    # to response to current prompt!
    use_generated_tools = False
    if use_generated_tools:
        for _tool in state["generated_tools"]:
            try:
                logging.info(
                    f"existing_tools: Generating local tool stub {_tool['name']}")
                tool_func = generate_dynamic_tool(_tool, scope, base_url)
                tools.append(tool_func)
            except Exception as e:
                logging.error(
                    f"need_to_generate_tools: Error while generate_dynamic_tool {_tool['name']}: {e}")

    try:
        logging.info(f"=====> Binding tools: {tools}")
        llm_with_tools = llm.bind_tools(tools=tools,
                                        strict=True)
    except Exception as e:
        logging.error(f"Error while binding tools: {e}")
        return {"messages_history": [{
            'role': 'ai',
            'content': json.dumps({"output": "Sorry, failed to answer using blueberry (tools binding)"}, indent=4)}]}

    chat_history = state["chat_history"]

    # print("*****************************")
    # print(f"{chat_history}")
    # print("*****************************")

    agent = (
        {
            "chat_history": lambda x: x["chat_history"],
            # Format agent scratchpad from intermediate steps
            "agent_scratchpad": lambda x: format_to_openai_function_messages(
                x["intermediate_steps"]
            ),
        }
        | execute_tools_with_parameters_chat_prompt_template
        | llm_with_tools
        | parse
    )

    try:
        logging.info(f"=====> Creating AgentExecutor")
        agent_executor = AgentExecutor(agent=agent,
                                       tools=tools,
                                       verbose=True,
                                       handle_parsing_errors=True)
    except Exception as e:
        logging.error(f"Error while AgentExecutor: {e}")
        return {"messages_history": [{
            'role': 'ai',
            'content': json.dumps({"output": "Sorry, failed to answer using blueberry (AgentExecutor)"}, indent=4)}]}

    try:
        logging.info(f"=====> Invoking agent_executor")
        response = agent_executor.invoke({"chat_history": f"{chat_history}"},
                                         config=None)
    except Exception as e:
        logging.error(f"Error while agent_executor.invoke: {e}")
        return {"messages_history": [{
            'role': 'ai',
            'content': json.dumps({"output": "Sorry, failed to answer using blueberry (invoke agent_executor)"}, indent=4)}]}

    logger.info(
        f"=====> The agentic flow has finished executing the tools with parameters")

    print(json.dumps(response, indent=4))

    logging.info(f"=======>>> execute_tools_with_parameters. ended <<<=======")
    return {"messages_history": [{
        'role': 'ai',
        'content': json.dumps(response, indent=4)
    }]}


def json_schema_to_python_type(json_schema_type: str) -> str:
    # Mapping JSON Schema types to Python types
    type_mapping = {
        "string": "str",
        "str": "str",
        "number": "float",
        "float": "float",
        "integer": "int",
        "int": "int",
        "bool": "bool",
        "boolean": "bool",
        "object": "dict",
        "list": "list",
        "array": "list",
        "datetime": "datetime",
        "null": "None",
        "any": "object",  # 'any' can be mapped to 'object' or 'str', depending on use case
    }

    # Return the corresponding Python type as a string
    return type_mapping.get(json_schema_type, "Unknown")


def generate_function_arguments_from_metadata(metadata: str):
    parsed_info = json.loads(metadata)
    function_arguments = f"("
    parameters = parsed_info['parameters']['properties']
    param_strs = []

    for param_name, param_info in parameters.items():
        param_type = json_schema_to_python_type(param_info['type'])
        param_strs.append(f"{param_name}: {param_type}")

    function_arguments += ", ".join(param_strs) + ")"

    return function_arguments
