# This script creates a manifest for a function in a module, based on JSON documentation
# for the function in a separate folder

from client.utils import base_client_utils
from client.utils import json_client_utils
import argparse

parser = argparse.ArgumentParser(
    description="Generate and print manifest for a function based on JSON"
)
# TODO: specify json file(s) as an optional parameter(s)
parser.add_argument(
    "jsonpath", type=str, help="A path to a folder containing the JSON descriptions"
)
parser.add_argument(
    "modpath", type=str, help="A path to the module containing the function"
)
parser.add_argument(
    "funcname", type=str, help="Name of the function as defined in the module"
)

args = parser.parse_args()
json_base = json_client_utils.load_json_base(args.jsonpath)
manifest = json_client_utils.python_manifest_from_json_base(
    json_base, args.modpath, args.funcname
)
print(base_client_utils.json_pretty_print(manifest))
