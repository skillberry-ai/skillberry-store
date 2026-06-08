"""Global mutation counter — incremented on every write or delete."""

_count = 0


def bump() -> None:
    """Increment the mutation counter."""
    global _count
    _count += 1


def get() -> int:
    """Return the current mutation counter value."""
    return _count
