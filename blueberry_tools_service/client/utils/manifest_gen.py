# This script locates all the functions in all the modules in a given folder, and generates
# a manifest for each function. The manifest is based either on the function's doc string,
# or (if not available) on the matching JSON documentation.

from blueberry_tools_service.client.utils import base_client_utils
from blueberry_tools_service.client.utils import json_client_utils
import argparse
import os

parser = argparse.ArgumentParser(
    description="Generate manifests for all functions in a given folder"
)
parser.add_argument(
    "jsonpath", type=str, help="A path to a folder containing the JSON descriptions"
)
parser.add_argument(
    "codepath",
    type=str,
    help="A path to the module containing all the functions in modules",
)
parser.add_argument("mftpath", type=str, help="A target path to write the manifests to")

args = parser.parse_args()
json_base = json_client_utils.load_json_base(args.jsonpath)
func_list = base_client_utils.list_functions_in_folder(args.codepath)
for func_data in func_list:
    modpath, funcname, _ = func_data
    manifest = json_client_utils.python_manifest_from_docstring_or_json(
        json_base, modpath, funcname
    )
    if manifest == None:
        raise Exception(
            f"No manifest constructed for function {funcname} in module {modpath} - ABORTING"
        )
    mft_filepath = os.path.join(args.mftpath, funcname + ".json")
    try:
        with open(mft_filepath, "w") as file:
            file.write(base_client_utils.json_pretty_print(manifest))
        print(f"Wrote manifest for function: {funcname}")
    except Exception as e:
        print(f"An error occurred: {e}")
