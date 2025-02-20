import logging
import uvicorn
import threading
import colorlog

from langchain.globals import set_verbose, set_debug
from langchain.callbacks.tracers import ConsoleCallbackHandler

from config.config_structure import CONFIG_STRUCTURE
from llm.common import check_llm_communication
from tools_agentic_graph import define_tools_agentic_graph
from agent_analytics.instrumentation import agent_analytics_sdk

from api_server import api_server
from config.config_ui import config_ui_app
from config.config_ui import config

# Initialize logger
logger = logging.getLogger(__name__)

debug = config.get("advanced__debug")
otel_logging = config.get("advanced__otel_logging")
invoke_config = None

log_level = logging.INFO
if debug is True:
    log_level = logging.DEBUG
    set_debug(True)
    set_verbose(True)
    invoke_config = {'callbacks': [ConsoleCallbackHandler()]}

    if otel_logging is True:
        # Initialize logging with agent_analytics_sdk
        from agent_analytics.instrumentation.configs import OTLPCollectorConfig

        print("otel_logging mode enabled")
        agent_analytics_sdk.initialize_logging(
            tracer_type=agent_analytics_sdk.SUPPORTED_TRACER_TYPES.REMOTE,
            config=OTLPCollectorConfig(endpoint="http://localhost:4318/v1/traces"),
            # logs_dir_path="/tmp/",
            # log_filename="tools-agent",
        )

    print("Debug mode enabled")
else:
    set_debug(False)
    set_verbose(False)
    invoke_config = None

log_file = config.get("advanced__log_file")


# Define log format for colors (Console)
console_formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(message)s",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    }
)

# Define log format for file (No colors)
file_formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(message)s"
)
console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(file_formatter)

# Configure logger
logging.basicConfig(level=log_level, handlers=[console_handler, file_handler])


def run_config_ui():
    config_ui_app.run_server(debug=True, use_reloader=False, host="0.0.0.0", port=7001)


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

    # Run the configuration UI
    config_ui_thread = threading.Thread(target=run_config_ui)
    config_ui_thread.start()

    # Run the API server
    uvicorn.run(api_server, host="0.0.0.0", port=7000)


if __name__ == "__main__":
    main()
