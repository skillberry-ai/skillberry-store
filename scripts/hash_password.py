#!/usr/bin/env python3
"""Mint a bcrypt password hash for the access-control config.

Usage:
    python scripts/hash_password.py [username]

Prompts (no-echo) for a password, prints the bcrypt hash to stdout. Never
touches the config file — copy the printed hash into
``access_control_config.yaml`` under ``standalone.users``.
"""

from __future__ import annotations

import getpass
import sys

import bcrypt


def main() -> int:
    username = sys.argv[1] if len(sys.argv) > 1 else "user"
    print(f"Generating password hash for user: {username}")
    p1 = getpass.getpass("Password: ")
    p2 = getpass.getpass("Confirm:  ")
    if p1 != p2:
        print("Passwords do not match", file=sys.stderr)
        return 1
    if not p1:
        print("Password cannot be empty", file=sys.stderr)
        return 1
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(p1.encode("utf-8"), salt).decode("ascii")
    print()
    print("Copy this into access_control_config.yaml under standalone.users:")
    print(f"  password_hash: {hashed!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
