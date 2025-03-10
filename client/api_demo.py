from tools.configure import configure_logger
from client.modules_json_client.modules_json_tools_client import ModulesJsonToolsClient
from client.base_client import base_client_utils

# This is a DEMO to run and inspect, not a TEST. You should run it from the top folder of Blueberry-tools-service (python -m client.api_demo). 
# Before running, update genai_proj_loc below to the location of the genai-lakehouse-mapping project
genai_proj_loc="../../mc_connectors/genai-lakehouse-mapping"
logger=configure_logger("Main")
# Example usage
logger.info("Creating client")
my_client = ModulesJsonToolsClient() # use defaults - connect locally
# Set JSON base
logger.info("Setting JSON base")
my_client.set_json_base(f"{genai_proj_loc}/examples/")
# Add tool - GetQuarter - from DOT project
logger.info("Adding tool - GetQuarter")
uids = my_client.add_tools_from_python_functions([(f"{genai_proj_loc}/transformations/client-win-functions.py", "GetQuarter")])
logger.info(f"Result = {base_client_utils.json_pretty_print(uids)}")
# Search for the tool - expect to find GetQuarter
logger.info("Searching for GetQuarter")
logger.info(f"Result = {base_client_utils.json_pretty_print(my_client.search_tools("quarter of the year"))}")
# Get the tool (manifest)
logger.info("Getting tool - GetQuarter")
logger.info(f"Result = {base_client_utils.json_pretty_print(my_client.get_tool("GetQuarter"))}")
# Execute the tool GetQuarter
logger.info("Executing tool - GetQuarter")
logger.info(f"Result = {base_client_utils.json_pretty_print(my_client.execute_tool("GetQuarter", {"input_string": "2Q2056"}))}")
# Delete the tool
logger.info("Deleting the tool - GetQuarter")
logger.info(f"Result = {base_client_utils.json_pretty_print(my_client.delete_tool("GetQuarter"))}")
# Get the tool (manifest) again - SHOULD FAIL
logger.info("Getting the deleted tool - GetQuarter")
logger.info(f"Result = {base_client_utils.json_pretty_print(my_client.get_tool("GetQuarter"))}")
