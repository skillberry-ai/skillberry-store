import os
import json
import logging

logger = logging.getLogger(__name__)


class DynamicConfig:
    TYPE_MAP = {
        "int": int,
        "str": str,
        "string": str,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict
    }

    def __init__(self, structure, config_file="/tmp/tool-agent-config.json"):
        self.structure = structure
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        """Loads the configuration values, applying defaults from the structure if missing."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, IOError):
                config = {}  # If the file is corrupted, start fresh
        else:
            config = {}

        return self.apply_defaults(self.structure, config)

    def apply_defaults(self, structure, config):
        """Recursively applies default values to missing fields."""
        new_config = {}
        for key, value in structure.items():
            if value["type"] == "group":
                new_config[key] = self.apply_defaults(value["children"], config.get(key, {}))
            else:
                new_config[key] = config.get(key, value["default"])
        return new_config

    def restore_defaults(self):
        """Restores all configuration values to their default settings."""
        self.config = self.apply_defaults(self.structure, {})
        self.save_config()

    def save_config(self):
        """Saves the configuration to a file."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
        except IOError as e:
            print(f"Error saving config: {e}")

    def get(self, key, default=None):
        """Retrieves a configuration value using '__' notation for nesting."""
        keys = key.split("__")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key, value):
        """Sets a configuration value using '__' notation with type validation."""
        keys = key.split("__")
        config = self.config
        current_structure = self.structure

        # Traverse structure to get an expected type
        for k in keys[:-1]:
            if k in current_structure and current_structure[k]["type"] == "group":
                current_structure = current_structure[k]["children"]
            else:
                raise KeyError(f"Invalid config path: {key}")

        last_key = keys[-1]
        if last_key not in current_structure:
            raise KeyError(f"Unknown config key: {key}")

        expected_type = self.TYPE_MAP.get(current_structure[last_key]["type"])

        if expected_type is float and isinstance(value, int):
            value = float(value)

        if expected_type and not isinstance(value, expected_type):
            raise TypeError(f"Expected '{expected_type.__name__}' for key '{key}', but got '{type(value).__name__}'")

        # Traverse and set value
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        config[last_key] = value
        self.save_config()

    def get_type(self, key):
        """Returns the expected type of a configuration key."""
        keys = key.split("__")
        current_structure = self.structure

        for k in keys[:-1]:
            if k in current_structure and current_structure[k]["type"] == "group":
                current_structure = current_structure[k]["children"]
            else:
                return None  # Key path does not exist

        last_key = keys[-1]
        if last_key not in current_structure:
            return None  # Unknown key

        return self.TYPE_MAP.get(current_structure[last_key]["type"])

    def isinstance_check(self, key):
        """Checks if the value stored under `key` matches its expected type."""
        keys = key.split("__")
        value = self.get(key)
        current_structure = self.structure

        for k in keys[:-1]:
            if k in current_structure and current_structure[k]["type"] == "group":
                current_structure = current_structure[k]["children"]
            else:
                return False  # Key path does not exist

        last_key = keys[-1]
        if last_key not in current_structure:
            return False  # Unknown key

        expected_type = self.TYPE_MAP.get(current_structure[last_key]["type"])
        return isinstance(value, expected_type)
