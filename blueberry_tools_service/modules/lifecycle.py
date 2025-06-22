import json
from enum import Enum


class LifecycleState(str, Enum):
    UNKNOWN = "unknown"
    ANY = "any"

    NEW = "new"
    CHECKED = "checked"
    APPROVED = "approved"


class LifecycleManager:
    def __init__(self, metadata):
        self.metadata = metadata

    def get_state(self):
        return self.metadata.get("state", LifecycleState.UNKNOWN)

    def set_state(self, state: LifecycleState):
        if not isinstance(state, LifecycleState):
            raise ValueError(f"Invalid lifecycle State value {state}")

        self.metadata["state"] = state

    def get_metadata(self):
        return self.metadata
