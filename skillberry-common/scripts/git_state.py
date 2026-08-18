#!/usr/bin/env python3
"""Git-state management for the SkillBerry build system.

Consolidates the small shell/awk scripts that previously handled the
BUILD_VERSION label, the state manifest, and content-idempotent updates.
See ``docs/design/build_concepts.md`` for the semantics — concepts 1, 2,
and 4.

Subcommands:
  version   Print the BUILD_VERSION label to stdout.
  manifest  Print the canonical state manifest to stdout.
  update    Content-idempotent update of the state manifest at the given
            path, with observability lines to stderr on real state changes.
            If a VERSION_LOCATION path is given as the third argument, the
            label is projected there using the same content-idempotence
            rule (concept 2).

All human-facing output goes to stderr, so any subcommand is safe to call
from a Makefile's ``$(shell ...)``.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# git helpers
# ---------------------------------------------------------------------------

def _git(*args: str) -> str:
    """Run ``git <args>`` and return stdout as text; empty string on failure."""
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True)
    except FileNotFoundError:
        return ""
    return r.stdout if r.returncode == 0 else ""


def _git_bytes(*args: str) -> bytes:
    """Run ``git <args>`` and return stdout as bytes; empty on failure."""
    try:
        r = subprocess.run(["git", *args], capture_output=True)
    except FileNotFoundError:
        return b""
    return r.stdout if r.returncode == 0 else b""


def _in_repo() -> bool:
    r = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True, text=True,
    )
    return r.returncode == 0


# ---------------------------------------------------------------------------
# BUILD_VERSION label (concept 1)
# ---------------------------------------------------------------------------

def compute_version() -> str:
    """Return the BUILD_VERSION label for the current repository state.

    Formats (matching ``git describe --always --dirty`` conventions):
      * clean at release commit:       ``<release>``            (e.g. ``0.5.3``)
      * N commits past latest release: ``<release>-<N>-g<sha>``
      * no releases in the repo yet:   ``g<sha>``
      * any dirty state adds:          ``-dirty-<7hex>``

    The dirty fingerprint is a hash over ``git diff HEAD`` plus the sorted
    list and contents of untracked non-ignored files, so different dirty
    states produce different labels.
    """
    if not _in_repo():
        return "unknown"

    latest_release = _latest_release()
    commit = _git("rev-parse", "--short=7", "HEAD").strip() or "0000000"

    if not latest_release:
        base = f"g{commit}"
    else:
        count_out = _git("rev-list", "--count", f"{latest_release}..HEAD").strip()
        if count_out.isdigit():
            count = int(count_out)
            base = latest_release if count == 0 else f"{latest_release}-{count}-g{commit}"
        else:
            # Tag not resolvable locally — fall back to the no-release form
            # rather than emitting a spurious label.
            base = f"g{commit}"

    if not _git("status", "--porcelain").strip():
        return base
    return f"{base}-dirty-{_dirty_fingerprint()}"


def _latest_release() -> str:
    """Return the highest ``branch-*`` release found on remote refs, or ``""``."""
    releases: list[str] = []
    for line in _git("branch", "-r").splitlines():
        line = line.strip()
        idx = line.find("branch-")
        if idx >= 0:
            releases.append(line[idx + len("branch-"):])
    if not releases:
        return ""
    return sorted(releases, key=_version_key)[-1]


def _version_key(v: str) -> tuple:
    """Key for ``sort -V``-like ordering — numeric parts numerically, others lex."""
    parts: list[tuple[int, object]] = []
    for p in v.split("."):
        if p.isdigit():
            parts.append((0, int(p)))
        else:
            parts.append((1, p))
    return tuple(parts)


def _dirty_fingerprint() -> str:
    """7-char SHA1-prefix fingerprint of the current dirty content.

    Covers tracked diffs (staged + unstaged) plus untracked non-ignored file
    contents, matching the state manifest's scope.
    """
    h = hashlib.sha1()
    h.update(_git_bytes("diff", "HEAD"))
    untracked = _git_bytes("ls-files", "--others", "--exclude-standard", "-z")
    paths = [p for p in untracked.split(b"\0") if p]
    for path in sorted(paths):
        h.update(b"\n== ")
        h.update(path)
        h.update(b" ==\n")
        try:
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
        except OSError:
            pass
    return h.hexdigest()[:7]


# ---------------------------------------------------------------------------
# State manifest (concept 4 pivot)
# ---------------------------------------------------------------------------
#
# Manifest format:
#     HEAD: <sha>
#     <status>\t<hash>\t<path>
#     <status>\t<hash>\t<path>
#     ...
#
#   <status> is git status --porcelain=v1's 2-char XY code.
#   <hash>   is `git hash-object` of the current on-disk file, or
#            '-' for a deletion, '<dir>' for an untracked directory,
#            '<missing>' if the path resolves to nothing.
#   <path>   is the working-tree path (renames use the destination path).
#
# Body lines are sorted so equivalent states produce byte-identical
# manifests; different states produce different manifests, and two manifests
# can be diffed to enumerate the files responsible for a change.

def compute_manifest() -> str:
    if not _in_repo():
        return "HEAD: unknown\n"

    head = _git("rev-parse", "HEAD").strip() or "unknown"
    lines = [f"HEAD: {head}"]

    raw = _git_bytes("status", "--porcelain=v1", "-z", "--untracked-files=all")
    entries = raw.split(b"\0")
    body: list[str] = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 3:
            continue
        status = entry[:2].decode("utf-8", errors="replace")
        path = entry[3:].decode("utf-8", errors="replace")
        # Rename/copy emits <new>\0<origin>; the destination reflects the
        # current on-disk state, so we skip the origin slot.
        if status[0] in ("R", "C"):
            i += 1
        if "D" in status:
            fh = "-"
        elif os.path.isfile(path):
            fh = _git("hash-object", "--", path).strip() or "unknown"
        elif os.path.isdir(path):
            fh = "<dir>"
        else:
            fh = "<missing>"
        body.append(f"{status}\t{fh}\t{path}")

    body.sort()
    return "\n".join(lines + body) + "\n"


# ---------------------------------------------------------------------------
# Update (manifest + optional VERSION_LOCATION) with observability
# ---------------------------------------------------------------------------

def cmd_update(version: str, manifest_path: str, version_location: str) -> int:
    if not _in_repo():
        print("Skipping git-state update: not inside a Git repository.", file=sys.stderr)
        return 0

    new_manifest = compute_manifest()
    mp = Path(manifest_path)
    if mp.exists():
        old_manifest = mp.read_text()
        if old_manifest == new_manifest:
            return 0  # No change → keep mtime stable so downstream isn't invalidated.
        _print_observability(version, True, old_manifest, new_manifest)
    else:
        _print_observability(version, False, "", new_manifest)

    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(new_manifest)

    if version_location:
        _write_version_file(version, version_location)
    return 0


def _print_observability(version: str, prior_exists: bool, old: str, new: str) -> None:
    if not prior_exists:
        print(
            f"==> BUILD_VERSION set to '{version}'. No prior BUILD_VERSION detected.",
            file=sys.stderr,
        )
        return
    print(
        f"==> BUILD_VERSION updated to '{version}'. "
        "The following changes have been detected since previous BUILD_VERSION:",
        file=sys.stderr,
    )

    old_head, old_body = _split_manifest(old)
    new_head, new_body = _split_manifest(new)

    if old_head != new_head:
        print(f"    HEAD: {old_head} -> {new_head}", file=sys.stderr)
        if old_head != "unknown" and new_head != "unknown":
            r = subprocess.run(
                ["git", "rev-parse", "--verify", "--quiet", old_head],
                capture_output=True,
            )
            if r.returncode == 0:
                names = _git("diff", "--name-only", old_head, new_head).splitlines()
                for p in sorted(set(names)):
                    print(f"    ~ {p}", file=sys.stderr)

    old_map = _body_map(old_body)
    new_map = _body_map(new_body)
    for path in sorted(set(old_map) | set(new_map)):
        o, n = old_map.get(path), new_map.get(path)
        if o is not None and n is not None:
            if o != n:
                print(f"    ! {path}", file=sys.stderr)
        elif n is not None:
            print(f"    + {path}", file=sys.stderr)
        else:
            print(f"    - {path}", file=sys.stderr)


def _split_manifest(text: str) -> tuple[str, list[str]]:
    if not text:
        return "unknown", []
    lines = text.splitlines()
    if lines and lines[0].startswith("HEAD: "):
        return lines[0][len("HEAD: "):], lines[1:]
    return "unknown", lines


def _body_map(body: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in body:
        parts = line.split("\t")
        if len(parts) >= 3:
            status, fh, path = parts[0], parts[1], "\t".join(parts[2:])
            out[path] = f"{status}\t{fh}"
    return out


def _write_version_file(version: str, path: str) -> None:
    """Content-idempotent write of ``__git_version__ = "<version>"``."""
    new = f'__git_version__ = "{version}"\n'
    p = Path(path)
    if p.exists() and p.read_text() == new:
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    verb = "Updated" if p.exists() else "Created"
    p.write_text(new)
    print(f"{verb} git version in {path} to {version}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Git-state management for the SkillBerry build system.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version", help="Print BUILD_VERSION")
    sub.add_parser("manifest", help="Print state manifest")
    up = sub.add_parser("update", help="Content-idempotent manifest update")
    up.add_argument("version")
    up.add_argument("manifest_path")
    up.add_argument("version_location", nargs="?", default="")
    args = ap.parse_args()

    if args.cmd == "version":
        print(compute_version())
    elif args.cmd == "manifest":
        sys.stdout.write(compute_manifest())
    elif args.cmd == "update":
        return cmd_update(args.version, args.manifest_path, args.version_location)
    return 0


if __name__ == "__main__":
    sys.exit(main())
