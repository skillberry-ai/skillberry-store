import os
import litellm

if "RITS_API_KEY" not in os.environ:
    print("RITS_API_KEY environment variable not set")
    print("Please set RITS_API_KEY environment variable")
    print("more info can be found in the #rits-community slack")
    exit(1)


os.environ["RITS_API_URL"] = "https://inference-3scale-apicast-production.apps.rits.fmaas.res.ibm.com"

RITS_API_URL = os.environ["RITS_API_URL"]
RITS_API_KEY = os.environ["RITS_API_KEY"]
MODEL = "llama-3-1-70b-instruct"
MODEL_PROVIDER = "meta-llama"
USER_PROMPT = "How many b's are in blueberry?"

# litellm.set_verbose = True

response = litellm.completion(
    model=f"openai/{MODEL_PROVIDER}/{MODEL}",
    api_base=f"{RITS_API_URL}/{MODEL}/v1",
    api_key="dummy",
    messages=[
                {
                    "role": "user",
                    "content": f"{USER_PROMPT}",
                }
    ],
    extra_headers={'RITS_API_KEY': RITS_API_KEY}
)
print(response)
