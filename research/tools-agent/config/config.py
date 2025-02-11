import json
import os

class DynamicConfig:
    def __init__(self, structure, config_file="/tmp/tool-agent-config.json"):
        self.structure = structure
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self):
        """Loads the configuration values, applying defaults from the structure if missing."""
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                config = json.load(f)
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

    def save_config(self):
        """Saves the configuration to a file."""
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key):
        """Retrieves a configuration value."""
        return self.config.get(key)

    def set(self, key, value):
        """Sets a configuration value."""
        self.config[key] = value
        self.save_config()
    