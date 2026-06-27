import fasteners
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set, Tuple


@dataclass
class DependencyManager:
    """In-memory store for reverse dependency records for a single object type."""

    _data: Dict[str, Set[Tuple[str, str]]] = field(default_factory=dict)
    _lock: fasteners.ReaderWriterLock = field(default_factory=fasteners.ReaderWriterLock)

    def add(
        self, referencing_type: str, referencing_uuid: str, referenced_uuids: Iterable[str]
    ):
        with self._lock.write_lock():
            dependent = (referencing_type, referencing_uuid)
            for referenced_uuid in referenced_uuids:
                if referenced_uuid not in self._data:
                    self._data[referenced_uuid] = set()
                self._data[referenced_uuid].add(dependent)

    def remove_referencing(self, referencing_type: str, referencing_uuid: str):
        with self._lock.write_lock():
            dependent = (referencing_type, referencing_uuid)
            empty_keys = []
            for referenced_uuid, dependents in self._data.items():
                dependents.discard(dependent)
                if not dependents:
                    empty_keys.append(referenced_uuid)
            for referenced_uuid in empty_keys:
                self._data.pop(referenced_uuid, None)

    def get_dependents(self, referenced_uuid: str) -> List[Tuple[str, str]]:
        with self._lock.read_lock():
            dependents = self._data.get(referenced_uuid)
            if dependents is None:
                return []
            return sorted(dependents)

    def clear(self):
        with self._lock.write_lock():
            self._data.clear()
