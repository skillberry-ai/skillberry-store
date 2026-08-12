"""Access control package for skillberry-store.

Implements the design in docs/design/access-control.md: Kubernetes-style
RBAC (roles + role bindings), a pure policy decision point (PDP), a
route-to-``(resource, verb)`` mapper, and a policy enforcement point
(PEP) implemented as a single global FastAPI dependency (see
``deps.py``).

Step 1 supports two modes: ``disabled`` (backward compatible; no PEP
dependency installed and no OpenAPI security scheme published) and
``standalone`` (username/password login → opaque session token, bearer
extraction via FastAPI's ``HTTPBearer`` security scheme).
"""

from skillberry_store.access_control.config import (  # noqa: F401
    AccessControlConfig,
    User,
    Role,
    Rule,
    RoleBinding,
    Subject as SubjectRef,
    load_config,
)
from skillberry_store.access_control.pdp import (  # noqa: F401
    Decision,
    Subject,
    authorize,
)
from skillberry_store.access_control.sessions import SessionStore  # noqa: F401
