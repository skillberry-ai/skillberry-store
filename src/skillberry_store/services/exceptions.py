"""Service-layer exception types shared across services."""


class ObjectAlreadyExistsError(ValueError):
    """Raised when an object with the given identifier already exists.

    Subclasses ``ValueError`` so legacy callers that catch ``ValueError`` for
    duplicate-object detection continue to work.
    """


class PortConflictError(ValueError):
    """Raised when a runtime server cannot bind because the requested port
    (or the auto-allocated port) is already in use or otherwise unavailable.

    Subclasses ``ValueError`` so legacy callers that catch ``ValueError`` for
    creation failures continue to work.
    """
