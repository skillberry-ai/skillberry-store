import json
import logging

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
@chat_api_server.post("/v1/chat/completions")
def chat_completion(request: ChatRequest):
    try:
        response = stream_graph_updates(request.messages[0])
        final_response = json.loads(list(response)[0]['messages_history'][0]['content'])['output']
        logging.info(f"The response to the user prompt is: {final_response}")
        return final_response
    except requests.HTTPError as e:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@chat_api_server.get("/health")
def health_check():
    return {"status": "ok"}
