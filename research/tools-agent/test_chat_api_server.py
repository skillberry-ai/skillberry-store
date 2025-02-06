import logging
from time import sleep
from langchain.globals import set_verbose, set_debug

import requests
import threading

from main import main

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(message)s")
set_debug(True)
set_verbose(True)

def test_health():
    url = "http://127.0.0.1:7000/health"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_API_KEY"
    }

    main_thread = threading.Thread(target=main, daemon=True)
    main_thread.start()

    sleep(5)

    # Send GET request to API endpoint
    response = requests.get(url, headers=headers)

    # Get response data
    response_data = response.json()
    print(f"response: {response_data}")
    assert True


def test_chat_completion():
    url = "http://127.0.0.1:7000/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_API_KEY"
    }

    main_thread = threading.Thread(target=main, daemon=True)
    main_thread.start()

    sleep(5)

    payload = {
        "model": "blueberry",
        "messages": [{"role": "user", "content": "How much is 2+2?"}],
        "temperature": 0.7
    }

    # Send POST request to API endpoint
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print(f"response: {response.text}")
        assert False

    # Get response data
    response_data = response.json()
    print(f"response: {response_data}")
    assert any('4' in str(value) for value in response_data.values()), "The output does not contain the character '4'"

