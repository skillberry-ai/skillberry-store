import os
import logging
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

if "RITS_API_KEY" not in os.environ:
    print("RITS_API_KEY environment variable not set")
    print("Please set RITS_API_KEY environment variable")
    print("Additional info can be found on #rits-community slack")
    exit(1)

os.environ["BLUEBERRY_TOOLS_AGENT_API_URL"] = "http://9.148.245.32:7000"
os.environ["RITS_API_URL"] = "https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com"
os.environ["RITS_PROXY_API_URL"] = "http://9.148.245.32:4000"

rits_api_url = os.environ["RITS_API_URL"]
rits_proxy_api_url = os.environ["RITS_PROXY_API_URL"]
rits_api_key = os.environ["RITS_API_KEY"]

selected_model = "meta-llama/llama-3-3-70b-instruct"

temperature = 0
use_rits_proxy = True

logger.info(f"\n\n"
            f"==> 0. Configuration:\n"
            f"==> =================\n"
            f"==> Using model: {selected_model}\n"
            f"==> Temperature: {temperature}\n"
            f"==> Using rits proxy: {use_rits_proxy}\n"
            f"==> =================\n\n")

if use_rits_proxy:
    model_name = f"rits/{selected_model}".replace('.', '-').lower()

    llm = ChatOpenAI(
        model=f"{model_name}",
        temperature=temperature,
        max_retries=2,
        api_key=rits_api_key,
        base_url=rits_proxy_api_url
    )
else:
    model = selected_model.split(
        '/')[1].replace('.', '-').lower()
    url = f"{rits_api_url}/{model}/v1"

    llm = ChatOpenAI(
        model=f"{model}",
        temperature=temperature,
        max_retries=2,
        api_key='/',
        base_url=url,
        default_headers={'RITS_API_KEY': rits_api_key}
    )


def check_llm_communication():
    try:
        llm.invoke("try to communicate with the llm")
        logger.info("Communication with the LLM established.")
        return True
    except Exception as e:
        logger.error(f"LLM is not working {e}")

    return False
