# This script creates a manifest for a function in a module, based on the function's well-formatted
# and comprehensive doc string.

from client.utils import base_client_utils
import argparse

parser = argparse.ArgumentParser(
    description="Generate and print manifest for a function based on doc string"
)
parser.add_argument(
    "modpath", type=str, help="A path to the module containing the function"
)
parser.add_argument(
    "funcname", type=str, help="Name of the function as defined in the module"
)

args = parser.parse_args()
docstring = base_client_utils.extract_docstring(args.modpath, args.funcname)
manifest = base_client_utils.python_manifest_from_function_docstring(
    args.modpath, args.funcname, docstring
)
print(base_client_utils.json_pretty_print(manifest))
