from skillberry_store.client.utils import base_client_utils
from skillberry_store.client.utils import json_client_utils
import argparse

def main():
    """
    Generates and prints a manifest for a function based on JSON documentation.

    Args:
        jsonpath (str): The path to a folder containing JSON descriptions.
        modpath (str): The path to the module containing the function.
        funcname (str): The name of the function as defined in the module.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(
        description="Generate and print manifest for a function based on JSON"
    )
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

if __name__ == "__main__":
    main()
