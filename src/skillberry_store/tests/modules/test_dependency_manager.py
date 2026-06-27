import threading

import pytest

from skillberry_store.modules.dependency_manager import DependencyManager


@pytest.fixture
def dm():
    return DependencyManager()


# ─── add / get_dependents ────────────────────────────────────────────────────

def test_get_dependents_empty_initially(dm):
    assert dm.get_dependents("uuid-A") == []


def test_add_single_dependency(dm):
    dm.add("skill", "sk-1", ["tool-A"])
    deps = dm.get_dependents("tool-A")
    assert deps == [("skill", "sk-1")]


def test_add_multiple_referenced_uuids(dm):
    dm.add("skill", "sk-1", ["tool-A", "tool-B"])
    assert dm.get_dependents("tool-A") == [("skill", "sk-1")]
    assert dm.get_dependents("tool-B") == [("skill", "sk-1")]


def test_add_multiple_referencing_objects(dm):
    dm.add("skill", "sk-1", ["tool-A"])
    dm.add("skill", "sk-2", ["tool-A"])
    deps = dm.get_dependents("tool-A")
    assert sorted(deps) == [("skill", "sk-1"), ("skill", "sk-2")]


def test_add_same_dependency_twice_is_idempotent(dm):
    dm.add("skill", "sk-1", ["tool-A"])
    dm.add("skill", "sk-1", ["tool-A"])
    assert len(dm.get_dependents("tool-A")) == 1


def test_add_empty_referenced_list_is_noop(dm):
    dm.add("skill", "sk-1", [])
    assert dm.get_dependents("sk-1") == []


# ─── remove_referencing ──────────────────────────────────────────────────────

def test_remove_referencing_clears_entries(dm):
    dm.add("skill", "sk-1", ["tool-A", "tool-B"])
    dm.remove_referencing("skill", "sk-1")
    assert dm.get_dependents("tool-A") == []
    assert dm.get_dependents("tool-B") == []


def test_remove_referencing_only_removes_matching_type_and_uuid(dm):
    dm.add("skill", "sk-1", ["tool-A"])
    dm.add("skill", "sk-2", ["tool-A"])
    dm.remove_referencing("skill", "sk-1")
    # sk-2 is still there
    assert dm.get_dependents("tool-A") == [("skill", "sk-2")]


def test_remove_referencing_nonexistent_is_noop(dm):
    dm.remove_referencing("skill", "sk-99")  # must not raise


def test_remove_referencing_prunes_empty_keys(dm):
    dm.add("skill", "sk-1", ["tool-A"])
    dm.remove_referencing("skill", "sk-1")
    # Internal dict should be empty (no empty-set entries left)
    assert dm._data == {}


# ─── clear ───────────────────────────────────────────────────────────────────

def test_clear_removes_all_entries(dm):
    dm.add("skill", "sk-1", ["tool-A"])
    dm.add("vmcp", "v-1", ["skill-X"])
    dm.clear()
    assert dm.get_dependents("tool-A") == []
    assert dm.get_dependents("skill-X") == []
    assert dm._data == {}


# ─── get_dependents return is sorted ─────────────────────────────────────────

def test_get_dependents_returns_sorted(dm):
    dm.add("vmcp", "v-2", ["skill-X"])
    dm.add("vmcp", "v-1", ["skill-X"])
    dm.add("skill", "s-1", ["skill-X"])
    deps = dm.get_dependents("skill-X")
    assert deps == sorted(deps)


# ─── thread-safety smoke test ─────────────────────────────────────────────────

def test_concurrent_add_does_not_raise():
    dm = DependencyManager()
    errors = []

    def worker(i):
        try:
            dm.add("skill", f"sk-{i}", [f"tool-{i % 5}"])
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
