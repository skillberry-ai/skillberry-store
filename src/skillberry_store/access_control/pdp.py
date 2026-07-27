"""Policy Decision Point.

Pure, side-effect-free authorization logic. See §9 of
``docs/design/access-control.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from skillberry_store.access_control.config import AccessControlConfig


@dataclass
class Subject:
    """The authenticated caller. See §7 of the design doc."""

    tenant_id: Optional[str] = None
    groups: List[str] = field(default_factory=list)


@dataclass
class Decision:
    allowed: bool
    reason: str


def _match(patterns: List[str], value: str) -> bool:
    return "*" in patterns or value in patterns


def authorize(
    subject: Subject,
    resource: str,
    verb: str,
    cfg: "AccessControlConfig",
) -> Decision:
    """Return an allow/deny decision for ``(subject, resource, verb)``.

    Roles are unioned across every binding whose ``subjects:`` block matches
    the subject's ``tenant_id`` or any of its ``groups``.
    """
    tenant_id = subject.tenant_id or ""
    for role_name in cfg.roles_for(subject):
        role = cfg.role(role_name)
        if role is None:
            continue
        for rule in role.rules:
            if _match(rule.resources, resource) and _match(rule.verbs, verb):
                return Decision(
                    allowed=True,
                    reason=f"granted by role '{role_name}'",
                )
    return Decision(
        allowed=False,
        reason=(
            f"no role grants '{verb}' on '{resource}' to tenant "
            f"'{tenant_id or '<anonymous>'}'"
        ),
    )
