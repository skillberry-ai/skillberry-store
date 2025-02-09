import logging
import requests
import json
import csv
import argparse
import sys
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

rits_api_key = os.environ["RITS_API_KEY"]


def list_models():
    models = []
    url = "https://rits.fmaas.res.ibm.com/ritsapi/inferenceinfo"

    headers = {
        "Authorization": "Bearer " + rits_api_key,
        'RITS_API_KEY': rits_api_key
    }

    response = requests.get(url=url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code} - {response.text}")

    json_response = response.json()
    for model in json_response:
        models.append({"name": model["model_name"],
                      "endpoint": model["endpoint"]})

    return models


def load_csv_priority(csv_path):
    """Load model priority from a CSV file and return as an ordered list."""
    try:
        with open(csv_path, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError as e:
        print(f"Error loading CSV: {e}", file=sys.stderr)
        return []

        [m for m in priority_order if m in models]


def get_prioritized_models(model_names_priority_order, models):
    prioritized_models = []
    for prioritized_model_name in model_names_priority_order:
        for model in models:
            if prioritized_model_name in model['name'] or prioritized_model_name in model['endpoint']:
                prioritized_models.append(model)
                break
    return prioritized_models


def main():
    parser = argparse.ArgumentParser(description='utils wrapper')
    parser.add_argument('command', choices=[
                        'list_models'], help='Command to execute')
    parser.add_argument('--models_priority', type=str,
                        help='CSV file with models popularity')
    parser.add_argument('--output', type=str, help='File to save the output')

    args = parser.parse_args()

    if args.command == 'list_models':
        try:
            models = list_models()

           # If CSV file is provided, merge popularity data
            if args.models_priority:
                model_names_priority_order = load_csv_priority(
                    args.models_priority)
                models = get_prioritized_models(
                    model_names_priority_order, models)

            model_data = json.dumps(models, indent=2)

            if args.output:
                with open(args.output, 'w') as file:
                    file.write(model_data)
                print(f"Models saved to {args.output}")
            else:
                print(model_data)

        except Exception as e:
            print(f"Error executing command: {str(e)}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
