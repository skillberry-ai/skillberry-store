"""Unit tests for the global mutation counter."""

import importlib
import skillberry_store.fast_api.changes as changes_module


def _reset():
    """Reset the counter between tests."""
    changes_module._count = 0


def test_get_returns_zero_initially():
    _reset()
    assert changes_module.get() == 0


def test_bump_increments_count():
    _reset()
    changes_module.bump()
    assert changes_module.get() == 1


def test_bump_multiple_times():
    _reset()
    for _ in range(5):
        changes_module.bump()
    assert changes_module.get() == 5


def test_get_does_not_change_count():
    _reset()
    changes_module.bump()
    changes_module.get()
    changes_module.get()
    assert changes_module.get() == 1
