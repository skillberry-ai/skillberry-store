from tools.configure import configure_logger
from client.modules_json_tools_client import ModulesJsonToolsClient
from client.utils import base_client_utils
import logging
import os, sys

# This is a DEMO to run and inspect, not a TEST. You should run it from the top folder of Blueberry-tools-service (python -m client.api_demo). 
# Before running, update EXAMPLESPATH env var to the location of examples root folder, such as the genai-lakehouse-mapping project clone

example_path = os.environ.get('EXAMPLESPATH')
if not example_path:
    print("Please set environment variable EXAMPLESPATH to the root directory of the examples, such as the genai-lakehouse-mapping clone", file=sys.stderr)
    sys.exit(-1)
logger=configure_logger("Main")
# Example usage
logger.info("Creating client")
my_client = ModulesJsonToolsClient(log_level=logging.CRITICAL) # use defaults - connect locally
# Set JSON base
logger.info("Setting JSON base")
my_client.set_json_base(f"{example_path}/examples/")
# Add tool - GetQuarter - from DOT project
logger.info("Adding tools - GetYear, GetQuarter, GetCurrencySymbol, ParseDealSize")
uids = my_client.add_tools_from_python_functions([
    (f"{example_path}/transformations/client-win-functions.py", "GetYear"),
    (f"{example_path}/transformations/client-win-functions.py", "GetQuarter"),
    (f"{example_path}/transformations/client-win-functions.py", "GetCurrencySymbol"),
    (f"{example_path}/transformations/client-win-functions.py", "ParseDealSize")
])
logger.info(f"Result = {base_client_utils.json_pretty_print(uids)}")
# List the tools
logger.info("Listing the tools")
result = my_client.list_tools()
logger.info(f"Result = {base_client_utils.json_pretty_print(result)}")
# Search for the tool - expect to find GetQuarter
logger.info("Searching for GetQuarter")
result = my_client.search_tools("quarter of the year")
logger.info(f"Result = {base_client_utils.json_pretty_print(result)}")
# Get the tool manifest - GetCurrencySymbol
logger.info("Getting tool manifest - GetCurrencySymbol")
result = my_client.get_tool_manifest("GetCurrencySymbol")
logger.info(f"Result = {base_client_utils.json_pretty_print(result)}")
# Get tool code - GetCurrencySymbol
logger.info("Getting tool code - GetCurrencySymbol")
result = my_client.get_tool_code("GetCurrencySymbol")
logger.info(f"Result = {result}")
# Execute the tool GetQuarter
logger.info("Executing tool - GetQuarter")
result = my_client.execute_tool("GetQuarter", {"input_string": "2Q2056"})
logger.info(f"Result = {base_client_utils.json_pretty_print(result)}")
# Delete the tool
logger.info("Deleting the tool - GetQuarter")
result = my_client.delete_tool("GetQuarter")
logger.info(f"Result = {base_client_utils.json_pretty_print(result)}")
# Get the tool (manifest) again - SHOULD FAIL
logger.info("Getting the deleted tool manifest - GetQuarter - SHOULD FAIL")
result = my_client.get_tool_manifest("GetQuarter")
logger.info(f"Result = {base_client_utils.json_pretty_print(result)}")
