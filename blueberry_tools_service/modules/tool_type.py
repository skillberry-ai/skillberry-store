from enum import Enum


class ToolType(str, Enum):
    CODE_PYTHON = "code/python"

    # TODO: add support for json/genai-lh
    JSON_GENAI_LH = "json/genai-lh"
