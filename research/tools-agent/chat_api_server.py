import json
import logging
import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

from tools_agentic_graph import stream_graph_updates, tools_agentic_graph

# Define the API
chat_api_server = FastAPI()

# Request data model


class ChatRequest(BaseModel):
    model: str
    messages: list
    temperature: float = 0.7
    max_tokens: int = 100

# Endpoint for chat completions


@chat_api_server.post("/chat/completions")
def chat_completion(request: ChatRequest):
    try:
        response = stream_graph_updates([list(request.messages)[-1]])
        final_response = json.loads(
            list(response)[0]['messages_history'][0]['content'])['output']
        logging.info(f"The response to the user prompt is: {final_response}")

        response = {
            "id": "blueberry",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "blueberry",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": final_response,
                        "refusal": None
                    },
                    "logprobs": None,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 1,
                "prompt_tokens_details": {
                    "cached_tokens": 0
                },
                "completion_tokens_details": {
                    "reasoning_tokens": 0,
                    "accepted_prediction_tokens": 0,
                    "rejected_prediction_tokens": 0
                }
            },
            "system_fingerprint": "blueberry"
        }

        return response
    except requests.HTTPError as e:
        raise HTTPException(
            status_code=response.status_code, detail=response.text)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint


@chat_api_server.get("/health")
def health_check():
    return {"status": "ok"}
