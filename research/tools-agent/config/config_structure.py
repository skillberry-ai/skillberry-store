import logging

logger = logging.getLogger(__name__)

CONFIG_STRUCTURE = {
    "selected_model": {
        "type": "str",
        "default": "meta-llama/llama-3-3-70b-instruct",
        "label": "LLM rits model to be used by the agent",
    },
    "use_rits_proxy": {
        "type": "bool",
        "default": True,
        "label": "Should use the rits proxy or connect to rits directly"
    },
    "temperature": {
        "type": "int",
        "default": 0,
        "label": "The model temperature"
    },
    "nested": {
        "type": "group",
        "label": "Advanced Settings",
        "children": {
            "param1": {
                "type": "int",
                "default": 10,
                "label": "Max Retries"
            },
            "param2": {
                "type": "str",
                "default": "default",
                "label": "Log Level"
            }
        }
    }
}