import logging
import uvicorn

from langchain.globals import set_verbose, set_debug
from langchain.callbacks.tracers import ConsoleCallbackHandler

from chat_api_server import chat_api_server
from llm.common import llm, check_llm_communication
from tools_agentic_graph import define_tools_agentic_graph

logger = logging.getLogger(__name__)

debug = False
invoke_config = None

if debug is True:
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(name)s %(message)s')
    set_debug(True)
    set_verbose(True)
    invoke_config = {'callbacks': [ConsoleCallbackHandler()]}
    print("Debug mode enabled")
else:
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s %(message)s')
    set_debug(False)
    set_verbose(False)
    invoke_config = None


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
