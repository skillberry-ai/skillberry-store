import logging
import uvicorn

from langchain.globals import set_verbose, set_debug
from langchain.callbacks.tracers import ConsoleCallbackHandler

from chat_api_server import chat_api_server
from llm.common import llm, check_llm_communication
from tools_agentic_graph import define_tools_agentic_graph
from agent_analytics.instrumentation import agent_analytics_sdk 


# Initialize logger
logger = logging.getLogger(__name__)

debug = False
invoke_config = None

if debug is True:
    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(message)s")
    set_debug(True)
    set_verbose(True)
    invoke_config = {'callbacks': [ConsoleCallbackHandler()]}
    print("Debug mode enabled")
else:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(message)s")
    set_debug(False)
    set_verbose(False)
    invoke_config = None

from agent_analytics.instrumentation.configs import OTLPCollectorConfig

# Initialize logging with agent_analytics_sdk
agent_analytics_sdk.initialize_logging(
    tracer_type=agent_analytics_sdk.SUPPORTED_TRACER_TYPES.REMOTE,
    config=OTLPCollectorConfig(endpoint="http://localhost:4318/v1/traces"),
    # logs_dir_path="/tmp/",
    # log_filename="tools-agent",
)


def main():
    # make sure we can communicate with the LLM
    if not check_llm_communication():
        logger.error(
            "Can't communicate with the LLM, please check network, VPN, access keys etc.")
        exit(2)

    # define the agentic graph
    define_tools_agentic_graph()

    # user_input = "What is the 1294th prime number?"
    # user_input = "How much is 2+2?"
    # stream_graph_updates(tools_agentic_graph, user_input)

    # Run the API server
    uvicorn.run(chat_api_server, host="0.0.0.0", port=7000)


if __name__ == "__main__":
    main()
