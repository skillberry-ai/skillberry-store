"""Access control package for skillberry-store.

Implements the design in docs/design/access-control.md: Kubernetes-style
RBAC (roles + role bindings), pluggable identity providers, a policy
decision point (PDP), and a FastAPI middleware policy enforcement point
(PEP) that maps requests to (resource, verb) tuples.

Step 1 supports two modes: ``disabled`` (backward compatible; no PEP
installed) and ``standalone`` (username/password login → opaque session
token).
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
