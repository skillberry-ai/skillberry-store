import logging

logger = logging.getLogger(__name__)

CONFIG_STRUCTURE = {
    "selected_model": {
        "type": "str",
        "default": "meta-llama/llama-3-3-70b-instruct",
        "label": "LLM rits model to be used by the agent: ",
    },
    "tools_repo_base_url": {
        "type": "str",
        "default": "http://9.148.245.32:8000",
        "label": "The tools repository url: ",
    },
    "use_rits_proxy": {
        "type": "bool",
        "default": True,
        "label": "Should use the rits proxy (or connect to rits directly): "
    },
    "temperature": {
        "type": "float",
        "default": 0,
        "label": "The LLM model temperature: "
    },
    "advanced": {
        "type": "group",
        "label": "Advanced Settings",
        "children": {
            "debug": {
                "type": "bool",
                "default": False,
                "label": "Enable debug mode: "
            },
            "otel_logging": {
                "type": "bool",
                "default": False,
                "label": "Enable open-telemetry Logging (applicable only when debug is enabled): "
            },
            "generate_tools_dynamically": {
                "type": "bool",
                "default": False,
                "label": "Generate (code) tools dynamically: "
            },
            "similarity_threshold": {
                "type": "float",
                "default": 1.0,
                "label": "Similarity threshold for tools shortlisting: "
            },
            "max_tools_count": {
                "type": "int",
                "default": 5,
                "label": "Maximum number of tools in the tools shortlisting: "
            },
            "unittests_count": {
                "type": "int",
                "default": 3,
                "label": "The number of unittests to generate: "
            },
        }
    }
}

