#!/usr/bin/env python3
# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Provision users for `standalone` access-control mode.

Runs on its own -- no ``python`` prefix, no ``source``::

    ./scripts/setup_user.py alice                  # add/update alice in the repo config
    ./scripts/setup_user.py alice -b base-user     # ...and bind her tenant to a role
    ./scripts/setup_user.py alice -b readers:reader  # ...under a named binding
    ./scripts/setup_user.py alice -t team-blue     # ...mapped onto the team-blue tenant
    ./scripts/setup_user.py -l                     # list users, tenants, bindings, roles
    ./scripts/setup_user.py alice -d               # delete alice
    ./scripts/setup_user.py alice -f -             # just print the hash; touch nothing

Prompts (no-echo) for a password, mints a bcrypt hash, and writes the entry
into ``standalone.users`` of the target config. The file is rewritten through a
round-trip YAML loader, so comments, quoting and key order survive.

Supersedes the earlier ``hash_password.py``; ``-f -`` reproduces its behavior.
See ``docs/design/access-control.md`` §5 for the config schema.
"""

from __future__ import annotations

import argparse
import contextlib
import getpass
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any, List, NamedTuple, NoReturn, Optional, Sequence, Tuple

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parent.parent
DEFAULT_CONFIG = REPO_ROOT / "access_control_config.yaml"
BCRYPT_ROUNDS = 12

# Third-party imports this script needs, as (module, pip name).
DEPENDENCIES = (("bcrypt", "bcrypt"), ("ruamel.yaml", "ruamel.yaml"))
_REEXEC_ENV = "_SBS_SETUP_USER_REEXEC"


def _info(msg: str) -> None:
    """Chatter goes to stderr so ``-f -`` and ``-l`` keep stdout machine-readable."""
    print(msg, file=sys.stderr)


def _die(msg: str) -> NoReturn:
    print(f"error: {msg}", file=sys.stderr)
    raise SystemExit(1)


# --------------------------------------------------------------------------- #
# Interpreter bootstrap
# --------------------------------------------------------------------------- #
def _missing_dependencies() -> List[Tuple[str, str]]:
    from importlib.util import find_spec

    missing = []
    for module, pip_name in DEPENDENCIES:
        try:
            if find_spec(module) is None:
                missing.append((module, pip_name))
        except ImportError:  # parent package absent
            missing.append((module, pip_name))
    return missing


def _venv_interpreters() -> List[Path]:
    candidates = []
    active = os.environ.get("VIRTUAL_ENV")
    if active:
        candidates.append(Path(active) / "bin" / "python3")
    candidates.append(REPO_ROOT / ".venv" / "bin" / "python3")
    return candidates


def _bootstrap() -> None:
    """Hop into the project venv when this interpreter lacks the dependencies.

    ``#!/usr/bin/env python3`` lands on whatever interpreter is first on PATH,
    which typically has neither bcrypt nor ruamel. Re-exec once (guarded by
    ``_REEXEC_ENV``) so the script stays runnable straight from a bare shell.
    """
    missing = _missing_dependencies()
    if not missing:
        return

    names = ", ".join(module for module, _ in missing)
    hint = "pip install " + " ".join(pip for _, pip in missing)
    if os.environ.get(_REEXEC_ENV):
        _die(f"the project venv is missing required package(s): {names} ({hint})")

    current = Path(sys.executable).resolve()
    for interpreter in _venv_interpreters():
        if (
            interpreter.is_file()
            and os.access(interpreter, os.X_OK)
            and interpreter.resolve() != current
        ):
            os.environ[_REEXEC_ENV] = "1"
            os.execv(
                str(interpreter),
                [str(interpreter), str(SCRIPT_PATH), *sys.argv[1:]],
            )
    _die(
        f"missing required package(s): {names}. Create the project venv "
        f"(uv sync / python -m venv .venv) or install them here: {hint}"
    )


_bootstrap()

import bcrypt  # noqa: E402
from ruamel.yaml import YAML  # noqa: E402
from ruamel.yaml.comments import CommentedMap, CommentedSeq  # noqa: E402
from ruamel.yaml.error import CommentMark, YAMLError  # noqa: E402
from ruamel.yaml.scalarstring import SingleQuotedScalarString  # noqa: E402
from ruamel.yaml.tokens import CommentToken  # noqa: E402


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _split_bind(value: str, parser: argparse.ArgumentParser) -> Tuple[Optional[str], str]:
    """Parse ``-b`` into ``(binding_name_or_None, role)``.

    ``-b reader`` binds through the default ``<tenant>-binding``; the
    ``-b readers:reader`` form names the binding explicitly, which is how
    several tenants end up sharing one binding.
    """
    if ":" not in value:
        if not value:
            parser.error("-b needs a role: -b <role> or -b <binding>:<role>")
        return None, value
    if value.count(":") > 1:
        parser.error(f"-b {value!r}: expected at most one ':' (<binding>:<role>)")
    name, _, role = value.partition(":")
    if not name or not role:
        parser.error(
            f"-b {value!r}: both parts must be non-empty (<binding>:<role>)"
        )
    return name, role


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=SCRIPT_PATH.name,
        description=(
            "Provision a user for standalone access-control mode: mint a "
            "bcrypt password hash and write it into the ACL config."
        ),
        epilog=(
            "examples:\n"
            "  %(prog)s alice\n"
            "  %(prog)s alice -b base-user\n"
            "  %(prog)s alice -b readers:reader          # share a named binding\n"
            "  %(prog)s alice -b admin -t ops -f access_control_config.yaml.standalone\n"
            "  %(prog)s -l                               # list users\n"
            "  %(prog)s alice -d                         # delete a user\n"
            "  %(prog)s alice -f -                       # print a hash only\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "username",
        nargs="?",
        help="user to provision (required unless -l is given, where it filters)",
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="config",
        metavar="CONFIG",
        default=str(DEFAULT_CONFIG),
        help=(
            "target ACL config file (default: %(default)s). "
            "Use '-' to print the password hash to stdout and exit without "
            "touching any file."
        ),
    )
    parser.add_argument(
        "-b",
        "--bind",
        dest="bind",
        metavar="ROLE|BINDING:ROLE",
        help=(
            "role to bind the user's tenant to. Creates the binding if none "
            "covers the tenant, otherwise replaces that binding's roles. "
            "The BINDING:ROLE form names the binding (default: "
            "<tenant>-binding) and, when that binding already exists, adds "
            "the tenant to it. Without this flag a missing binding is a hard "
            "error."
        ),
    )
    parser.add_argument(
        "-t",
        "--tenant",
        dest="tenant_id",
        metavar="TENANT_ID",
        help=(
            "tenant the user maps to (default: the username; for an existing "
            "user, its current tenant_id is kept unless this flag is given)"
        ),
    )
    exclusive = parser.add_mutually_exclusive_group()
    exclusive.add_argument(
        "-l",
        "--list",
        dest="list_users",
        action="store_true",
        help=(
            "list the users in the target config as a user/tenant/binding/role "
            "table and exit; no username needed (given one, it filters)"
        ),
    )
    exclusive.add_argument(
        "-d",
        "--delete",
        dest="delete",
        action="store_true",
        help=(
            "delete the user from the target config; -b and -t are ignored. "
            "Bindings are left alone (other users may share the tenant)."
        ),
    )

    args = parser.parse_args(argv)
    if not args.list_users and not args.username:
        parser.error("the following arguments are required: username")
    if args.config == "-" and (args.list_users or args.delete):
        parser.error("-f - has no config to read or edit; drop -l/-d or name a file")
    args.binding_name, args.role = (
        _split_bind(args.bind, parser) if args.bind is not None else (None, None)
    )
    return args


# --------------------------------------------------------------------------- #
# Config I/O
# --------------------------------------------------------------------------- #
def _yaml() -> YAML:
    y = YAML()  # round-trip mode: comments and quoting survive a load/dump
    y.preserve_quotes = True
    y.indent(mapping=2, sequence=4, offset=2)  # matches the shipped configs
    y.width = 4096  # never re-wrap a long line into trailing whitespace
    return y


def _load_config(path: Path) -> Tuple[YAML, CommentedMap]:
    if not path.exists():
        _die(f"config file not found: {path}")
    if not path.is_file():
        _die(f"not a regular file: {path}")
    y = _yaml()
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = y.load(fh)
    except OSError as e:
        _die(f"cannot read {path}: {e}")
    except YAMLError as e:
        _die(f"{path} is not valid YAML: {e}")
    if data is None:
        _die(f"{path} is empty; expected an access-control config mapping")
    if not isinstance(data, dict):
        _die(f"{path} does not hold a mapping at the top level")
    return y, data


def _check_writable(path: Path) -> None:
    """Fail before the password prompt rather than after it."""
    if not os.access(path, os.W_OK):
        _die(f"no write permission for {path}")
    if not os.access(path.parent, os.W_OK):
        _die(
            f"no write permission for {path.parent} "
            f"(needed to replace {path.name} atomically)"
        )


def _save_config(y: YAML, data: CommentedMap, path: Path) -> None:
    """Write via a temp file in the same directory, then rename over the target."""
    original = path.stat()
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            y.dump(data, fh)
        os.chmod(tmp, stat.S_IMODE(original.st_mode))
        with contextlib.suppress(OSError):  # needs privilege; best effort
            os.chown(tmp, original.st_uid, original.st_gid)
        os.replace(tmp, path)
    except Exception as e:  # noqa: BLE001
        with contextlib.suppress(OSError):
            tmp.unlink()
        if isinstance(e, (OSError, YAMLError)):
            _die(f"failed to write {path}: {e}")
        raise


# ruamel's concrete classes leak into error messages otherwise.
_TYPE_NAMES = {
    "CommentedMap": "mapping",
    "CommentedSeq": "list",
    "dict": "mapping",
    "list": "list",
    "str": "string",
    "bool": "boolean",
}


def _typename(value: Any) -> str:
    name = type(value).__name__
    return _TYPE_NAMES.get(name, name)


def _mapping(parent: Any, key: str, path: Path) -> CommentedMap:
    """Return ``parent[key]`` as a mapping, creating it when absent or null."""
    value = parent.get(key)
    if value is None:
        value = CommentedMap()
        parent[key] = value
    elif not isinstance(value, dict):
        _die(f"'{key}' in {path} must be a mapping, found {_typename(value)}")
    return value


def _sequence(parent: Any, key: str, path: Path, label: str) -> CommentedSeq:
    """Return ``parent[key]`` as a sequence, creating it when absent or null.

    Read-only callers (``-l``) also go through here; the created key is only
    ever written back by ``_save_config``, which they never reach.
    """
    value = parent.get(key)
    if value is None:
        value = CommentedSeq()
        parent[key] = value
    elif not isinstance(value, list):
        _die(f"{label} in {path} must be a list, found {_typename(value)}")
    return value


def _flow_seq(items: Sequence[Any]) -> CommentedSeq:
    seq = CommentedSeq(items)
    seq.fa.set_flow_style()
    return seq


def _append_entry(
    parent: Any,
    key: str,
    seq: CommentedSeq,
    entry: CommentedMap,
    blank_line_before: bool = False,
) -> None:
    """Append ``entry`` to ``seq``, keeping comments that trail an empty list.

    ruamel parks everything that follows e.g. ``users: []`` -- the end-of-line
    note, a commented-out example block, even the next section divider -- on the
    key as a single comment token. A naive append then emits the new entry
    *below* all of it, which reads as if it belonged to the next section. So
    split the token: its first physical line stays on the key, the rest is
    re-attached under the entry we just added. Non-empty lists need none of
    this; there the trailing comments hang off the enclosing mapping already.
    """
    trailing = ""
    was_empty = not seq
    if was_empty:  # only an empty list carries the whole blob on its key
        token = (parent.ca.items.get(key) or [None] * 4)[2]
        if token is not None and "\n" in token.value.rstrip("\n"):
            head, _, trailing = token.value.partition("\n")
            token.value = head + "\n"

    seq.fa.set_block_style()  # an empty `key: []` would otherwise stay flow
    seq.append(entry)

    if blank_line_before and not was_empty:
        # Match the shipped configs, which breathe between multi-line entries.
        seq.ca.items[len(seq) - 1] = [
            None,
            [CommentToken("\n", CommentMark(0), None)],
            None,
            None,
        ]

    if trailing.strip():
        last_key = list(entry.keys())[-1]
        entry.ca.items[last_key] = [
            None,
            None,
            CommentToken("\n" + trailing, CommentMark(0), None),
            None,
        ]


def _empty_in_place(parent: Any, key: str, seq: CommentedSeq) -> None:
    """Render a just-emptied list as ``[]`` without dropping trailing comments.

    Comments that follow a block sequence live on the sequence's ``ca.end``, and
    ruamel drops them once there are no items left to emit -- deleting the last
    user would otherwise eat the ``# --- RBAC ---`` divider that follows the
    list. Flip the same object to flow style (so it prints as ``[]`` rather than
    a bare key with a null value) and fold those comments into the key's
    end-of-line comment, which the emitter still honors.
    """
    seq.fa.set_flow_style()
    end = seq.ca.end
    if not end:
        return
    # A token's own indentation lives in its start_mark, not its value, so it
    # has to be put back or the folded block loses its left margin.
    text = "".join(
        " " * token.start_mark.column + token.value
        if token.value.startswith("#")
        else token.value
        for token in end
    )
    seq.ca.end = []
    slot = parent.ca.items.setdefault(key, [None, None, None, None])
    if slot[2] is None:
        # The leading newline closes the `key: []` line; the rest reproduces the
        # original spacing verbatim.
        slot[2] = CommentToken("\n" + text, CommentMark(0), None)
    else:
        slot[2].value = slot[2].value.rstrip("\n") + "\n" + text


# --------------------------------------------------------------------------- #
# users
# --------------------------------------------------------------------------- #
def _tenant_of(entry: Any) -> str:
    return str(entry.get("tenant_id") or entry.get("username"))


def _find_user(users: CommentedSeq, username: str, path: Path) -> Optional[CommentedMap]:
    found = None
    for entry in users:  # scan every entry so bad ones are reported, not skipped
        if not isinstance(entry, dict):
            _die(f"non-mapping entry under standalone.users in {path}: {entry!r}")
        if entry.get("username") == username and found is None:
            found = entry
    return found


def _upsert_user(
    standalone: CommentedMap,
    users: CommentedSeq,
    existing: Optional[CommentedMap],
    username: str,
    tenant_id: str,
    password_hash: str,
) -> str:
    hashed = SingleQuotedScalarString(password_hash)  # bcrypt hashes are $-heavy
    if existing is not None:
        existing["tenant_id"] = tenant_id
        existing["password_hash"] = hashed
        if existing.get("groups") is None:
            existing["groups"] = _flow_seq([])  # keep any groups already curated
        return "updated"

    entry = CommentedMap()
    entry["username"] = username
    entry["tenant_id"] = tenant_id
    entry["password_hash"] = hashed
    entry["groups"] = _flow_seq([])
    _append_entry(standalone, "users", users, entry)
    return "created"


def _delete_user(
    standalone: CommentedMap, users: CommentedSeq, existing: CommentedMap
) -> None:
    index = next(i for i, entry in enumerate(users) if entry is existing)
    del users[index]
    if not users:
        _empty_in_place(standalone, "users", users)


# --------------------------------------------------------------------------- #
# bindings
# --------------------------------------------------------------------------- #
class BindingPlan(NamedTuple):
    bindings: CommentedSeq
    target: Optional[CommentedMap]  # existing binding to update
    new_name: Optional[str]  # name to create, when target is None
    others: List[CommentedMap]  # further bindings also covering the tenant


def _covers_tenant(binding: Any, tenant_id: str) -> bool:
    for subject in binding.get("subjects") or []:
        if (
            isinstance(subject, dict)
            and subject.get("kind") == "tenant"
            and subject.get("name") == tenant_id
        ):
            return True
    return False


def _bindings_for_tenant(
    bindings: CommentedSeq, tenant_id: str, path: Path
) -> List[CommentedMap]:
    matches = []
    for binding in bindings:
        if not isinstance(binding, dict):
            _die(f"non-mapping entry under bindings in {path}: {binding!r}")
        subjects = binding.get("subjects")
        if subjects is not None and not isinstance(subjects, list):
            _die(
                f"binding '{binding.get('name')}' in {path}: 'subjects' must be "
                f"a list, found {_typename(subjects)}"
            )
        if _covers_tenant(binding, tenant_id):
            matches.append(binding)
    return matches


def _role_names(roles: CommentedSeq, path: Path) -> List[str]:
    names = []
    for role in roles:
        if not isinstance(role, dict):
            _die(f"non-mapping entry under roles in {path}: {role!r}")
        if role.get("name"):
            names.append(str(role["name"]))
    return names


def _plan_binding(
    data: CommentedMap,
    tenant_id: str,
    binding_name: Optional[str],
    role: Optional[str],
    path: Path,
) -> BindingPlan:
    """Decide which binding to touch, failing before the password prompt."""
    bindings = _sequence(data, "bindings", path, "'bindings'")
    covering = _bindings_for_tenant(bindings, tenant_id, path)
    known = _role_names(_sequence(data, "roles", path, "'roles'"), path)
    defined = ", ".join(known) or "none"

    if role is None:
        if not covering:
            _die(
                f"no role binding covers tenant '{tenant_id}' in {path}; re-run "
                f"with -b <role> (or -b <binding>:<role>) to create one "
                f"(roles defined here: {defined})"
            )
        return BindingPlan(bindings, covering[0], None, covering[1:])

    if role not in known:
        _die(
            f"unknown role '{role}' in {path} (defined: {defined}). "
            f"A binding referencing an undefined role makes the store fail to "
            f"start in standalone mode."
        )

    if binding_name is None:
        if covering:
            return BindingPlan(bindings, covering[0], None, covering[1:])
        name = f"{tenant_id}-binding"
        if any(b.get("name") == name for b in bindings):
            _die(
                f"binding '{name}' already exists in {path} but does not cover "
                f"tenant '{tenant_id}'; pass -b {name}:{role} to add the tenant "
                f"to it, or name a different binding"
            )
        return BindingPlan(bindings, None, name, [])

    # An explicit name selects the binding outright: reuse it if it exists
    # (adding this tenant when missing), otherwise create it under that name.
    named = [b for b in bindings if b.get("name") == binding_name]
    if named:
        target = named[0]
        return BindingPlan(bindings, target, None, [b for b in covering if b is not target])
    return BindingPlan(bindings, None, binding_name, list(covering))


def _apply_binding(
    data: CommentedMap, plan: BindingPlan, tenant_id: str, role: Optional[str]
) -> str:
    if plan.others:
        others = ", ".join(str(b.get("name")) for b in plan.others)
        _info(
            f"note: tenant '{tenant_id}' is also covered by: {others}; "
            f"those roles still apply on top"
        )

    if role is None:  # no -b: an existing binding was only verified
        return (
            f"binding '{plan.target.get('name')}' already covers tenant "
            f"'{tenant_id}': unchanged"
        )

    if plan.target is None:
        binding = CommentedMap()
        binding["name"] = plan.new_name
        subject = CommentedMap()
        subject["kind"] = "tenant"
        subject["name"] = tenant_id
        binding["subjects"] = CommentedSeq([subject])
        binding["roles"] = _flow_seq([role])
        _append_entry(data, "bindings", plan.bindings, binding, blank_line_before=True)
        return f"binding '{plan.new_name}' created: tenant '{tenant_id}' -> [{role}]"

    target = plan.target
    name = target.get("name")
    changes = []

    if not _covers_tenant(target, tenant_id):
        subjects = target.get("subjects")
        if subjects is None:
            subjects = CommentedSeq()
            target["subjects"] = subjects
        subject = CommentedMap()
        subject["kind"] = "tenant"
        subject["name"] = tenant_id
        subjects.fa.set_block_style()
        subjects.append(subject)
        changes.append(f"tenant '{tenant_id}' added")

    previous = [str(r) for r in (target.get("roles") or [])]
    if previous != [role]:
        target["roles"] = _flow_seq([role])
        changes.append(f"roles [{', '.join(previous) or 'none'}] -> [{role}]")

    if not changes:
        return f"binding '{name}' already grants [{role}] to '{tenant_id}': unchanged"
    return f"binding '{name}' updated: " + "; ".join(changes)


# --------------------------------------------------------------------------- #
# listing
# --------------------------------------------------------------------------- #
HEADERS = ("USER", "TENANT", "BINDING", "ROLE")


def _list_users(data: CommentedMap, path: Path, only: Optional[str]) -> int:
    standalone = _mapping(data, "standalone", path)
    users = _sequence(standalone, "users", path, "'standalone.users'")
    bindings = _sequence(data, "bindings", path, "'bindings'")

    rows: List[Tuple[str, str, str, str]] = []
    for entry in users:
        if not isinstance(entry, dict):
            _die(f"non-mapping entry under standalone.users in {path}: {entry!r}")
        username = str(entry.get("username") or "?")
        if only is not None and username != only:
            continue
        tenant_id = _tenant_of(entry)
        covering = _bindings_for_tenant(bindings, tenant_id, path)
        if not covering:
            rows.append((username, tenant_id, "-", "-"))
            continue
        for i, binding in enumerate(covering):
            roles = ", ".join(str(r) for r in (binding.get("roles") or [])) or "-"
            # A tenant under several bindings gets one row each; the repeated
            # user/tenant cells are blanked so the grouping reads at a glance.
            rows.append(
                (
                    username if i == 0 else "",
                    tenant_id if i == 0 else "",
                    str(binding.get("name") or "?"),
                    roles,
                )
            )

    if not rows:
        _info(
            f"no user '{only}' in {path}"
            if only is not None
            else f"no users defined in {path}"
        )
        return 0 if only is None else 1

    widths = [
        max(len(row[i]) for row in (HEADERS, *rows)) for i in range(len(HEADERS))
    ]
    for row in (HEADERS, *rows):
        print("  ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip())
    return 0


# --------------------------------------------------------------------------- #
# password
# --------------------------------------------------------------------------- #
def _prompt_password_hash(username: str) -> str:
    _info(f"Generating password hash for user: {username}")
    try:
        first = getpass.getpass("Password: ")
        second = getpass.getpass("Confirm:  ")
    except (EOFError, KeyboardInterrupt):
        _die("aborted")
    if first != second:
        _die("passwords do not match")
    if not first:
        _die("password cannot be empty")
    return bcrypt.hashpw(
        first.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    ).decode("ascii")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def _note_ignored(active: str, args: argparse.Namespace) -> None:
    for flag, value in (("-b", args.bind), ("-t", args.tenant_id)):
        if value:
            _info(f"note: {flag} is ignored with {active}")


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    username = args.username

    # Hash-only mode: print and leave every file alone.
    if args.config == "-":
        _note_ignored("'-f -' (nothing is written)", args)
        print(_prompt_password_hash(username))
        return 0

    path = Path(args.config).expanduser()
    y, data = _load_config(path)

    if args.list_users:
        _note_ignored("-l", args)
        return _list_users(data, path, username)

    _check_writable(path)
    standalone = _mapping(data, "standalone", path)
    users = _sequence(standalone, "users", path, "'standalone.users'")
    existing = _find_user(users, username, path)

    if args.delete:
        _note_ignored("-d", args)
        if existing is None:
            _die(f"user '{username}' not found under standalone.users in {path}")
        tenant_id = _tenant_of(existing)
        _delete_user(standalone, users, existing)
        _save_config(y, data, path)
        print(f"{path}: user '{username}' deleted (tenant_id: {tenant_id})")

        # Bindings are per-tenant, so they are never deleted implicitly: another
        # user may still map to this tenant. Report instead.
        bindings = _sequence(data, "bindings", path, "'bindings'")
        covering = _bindings_for_tenant(bindings, tenant_id, path)
        if covering and not any(_tenant_of(u) == tenant_id for u in users):
            names = ", ".join(str(b.get("name")) for b in covering)
            print(
                f"  binding(s) {names} still grant roles to tenant "
                f"'{tenant_id}', which no remaining user maps to; "
                f"remove by hand if unwanted"
            )
        return 0

    # An existing user keeps its tenant unless -t says otherwise: silently
    # resetting tenant_id to the username would re-point the user's bindings.
    if args.tenant_id:
        tenant_id = args.tenant_id
    elif existing is not None and existing.get("tenant_id"):
        tenant_id = str(existing["tenant_id"])
    else:
        tenant_id = username

    # Validate everything that can fail before asking for a password.
    plan = _plan_binding(data, tenant_id, args.binding_name, args.role, path)

    mode = data.get("mode")
    if mode != "standalone":
        _info(
            f"note: {path} has mode: {mode!r} -- users are only consulted in "
            f"mode: standalone"
        )

    password_hash = _prompt_password_hash(username)

    user_action = _upsert_user(
        standalone, users, existing, username, tenant_id, password_hash
    )
    binding_note = _apply_binding(data, plan, tenant_id, args.role)
    _save_config(y, data, path)

    print(f"{path}: user '{username}' {user_action} (tenant_id: {tenant_id})")
    print(f"{path}: {binding_note}")
    if existing is not None and not args.tenant_id:
        print("  tenant_id kept from the existing entry; pass -t to change it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
