import os
import json
import logging
from langchain_core.messages.tool import ToolCallChunk
from langchain_core.agents import AgentActionMessageLog, AgentFinish
from langchain_core.messages import HumanMessage, SystemMessage, AIMessageChunk
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks.tracers import ConsoleCallbackHandler
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from pydantic import BaseModel, Field
import json

logger = logging.getLogger(__name__)

if "RITS_API_KEY" not in os.environ:
    print("RITS_API_KEY environment variable not set")
    print("Please set RITS_API_KEY environment variable")
    print("Additional info can be found on #rits-community slack")
    exit(1)

os.environ["RITS_API_URL"] = "https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com"

RITS_API_URL = os.environ["RITS_API_URL"]
RITS_API_KEY = os.environ["RITS_API_KEY"]

# MODEL_PROVIDER = "ibm-granite"
# MODEL = "granite-3.1-8b-instruct"

MODEL_PROVIDER = "meta-llama"
MODEL = "llama-3-1-70b-instruct"
# MODEL = "Llama-3.1-8B-Instruct"

# MODEL_PROVIDER = "mistralai"
# MODEL = "mistral-large-instruct-2407"

BASE_URL = f"{RITS_API_URL}/{MODEL.replace('.', '-').lower()}/v1"
TEMPERATURE = 0

print(f"==> 0. Configuration:\n"
      f"==> =================\n"
      f"==> Using model: {MODEL_PROVIDER}/{MODEL}\n"
      f"==> EndPoint: {BASE_URL}\n"
      f"==> Temperature: {TEMPERATURE}\n"
      f"==> =================\n\n")

llm = ChatOpenAI(
    model=f"{MODEL_PROVIDER}/{MODEL}",
    temperature=TEMPERATURE,
    max_retries=2,
    api_key='/',
    base_url=BASE_URL,
    default_headers={'RITS_API_KEY': RITS_API_KEY},
)


def check_llm_communication():
    try:
        llm.invoke("try to communicate with the llm")
        logger.info("Communication with the LLM established.")
        return True
    except Exception as e:
        logger.error(f"LLM is not working {e}")

    return False
