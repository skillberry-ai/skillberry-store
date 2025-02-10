import json
import logging
import time
import re

from fastapi import FastAPI, HTTPException
from langchain.schema import HumanMessage
from pydantic import BaseModel
import requests

from agents.code_missing_tools import generate_tool
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


def get_last_user_message(chat_log):
    matches = re.findall(r'User: ([^\\n]+)', str(chat_log))
    return {"content": matches[-1], "role": "user"} if matches else chat_log


@chat_api_server.post("/chat/completions")
def chat_completion(request: ChatRequest):
    try:
        chat_log = request.messages
        last_user_message = get_last_user_message(chat_log)
        response = stream_graph_updates(chat_log, [last_user_message])
        final_response = json.loads(
            list(response)[0]['messages_history'][-1]['content'])
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


@chat_api_server.post("/generate_tool/{name}")
def api_generate_tool(tool_name: str, tool_description: str, skip_validation: bool = False):
    try:
        need_to_generate_tool = {
            "name": tool_name,
            "description": tool_description
        }
        success = generate_tool(need_to_generate_tool,
                                skip_validation=skip_validation)
        if success:
            return {"message": f"Tool {tool_name} generated successfully"}
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@chat_api_server.get("/health")
def health_check():
    return {"status": "ok"}
