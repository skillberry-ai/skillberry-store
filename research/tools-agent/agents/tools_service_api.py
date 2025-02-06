import json

import requests

headers = {
    "accept": "application/json",
    "Content-Type": "application/json"
}


def search_tools(_base_url: str,
                 tool_name: str,
                 tool_description: str,
                 max_numer_of_results,
                 similarity_threshold):
    search_url = f"{_base_url}/description/search"
    response = requests.get(search_url, headers=headers, params={"search_term": f"{tool_name}: {tool_description}",
                                                                 "max_numer_of_results": max_numer_of_results,
                                                                 "similarity_threshold": similarity_threshold})
    if response.status_code == 200:
        return response.json()
    else:
        return None


def get_tool_description(_base_url: str, name: str):
    get_description_url = f"{_base_url}/description/"
    response = requests.get(get_description_url + name, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None


def get_tool_metadata(_base_url: str, name: str):
    get_metadata_url = f"{_base_url}/metadata/"
    response = requests.get(get_metadata_url + name, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None


def execute_tool(_base_url: str, _name: str, _parameters: dict):
    execute_tool_url = f"{_base_url}/execute/{_name}"
    response = requests.post(execute_tool_url, headers=headers, json=_parameters)
    if response.status_code == 200:
        response_json = response.json()
        return response_json["return value"]
    else:
        return None
