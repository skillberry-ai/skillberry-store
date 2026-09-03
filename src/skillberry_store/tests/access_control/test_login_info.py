# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0
"""Unit tests for the login-information message resolver.

Covers §4.2 (validation), §5 steps 1-6 (resolution and sanitization) and §9
(mode interaction) of docs/design/login-info.md. Parsing only — no HTTP.

The invariant under test throughout: ``cfg.login_info`` is either ``None`` or
an already-sanitized string. Every "off" condition — the gate, an absent or
malformed message, a mode other than ``standalone`` — collapses into ``None``,
which is what lets the UI, CLI and REST surfaces carry no gate checks of their
own.
"""

from __future__ import annotations

import logging
import textwrap

import pytest

from skillberry_store.access_control.config import (
    LOGIN_INFO_MAX_CHARS,
    LOGIN_INFO_MAX_LINES,
    AccessControlConfigError,
    load_config,
)

MESSAGE = "Shared eval box — do not store secrets."


def _write(tmp_path, contents: str) -> str:
    path = tmp_path / "acl.yaml"
    path.write_text(textwrap.dedent(contents))
    return str(path)


def _standalone(login_info_block: str, mode: str = "standalone") -> str:
    """A minimal valid config with ``login_info_block`` spliced under standalone."""
    return f"""
        mode: {mode}
        standalone:
          users:
            - username: alice
              password_hash: "$2b$12$x"
{textwrap.indent(textwrap.dedent(login_info_block), "          ")}
        """


# --------------------------------------------------------------------------- #
# The gate × the message (§4.1, §4.2)
# --------------------------------------------------------------------------- #

def test_enabled_with_a_message_resolves_it(tmp_path):
    cfg = load_config(
        _write(
            tmp_path,
            _standalone(
                f"""
                login_info:
                  enabled: true
                  message: "{MESSAGE}"
                """
            ),
        )
    )
    assert cfg.login_info == MESSAGE


def test_absent_block_is_silently_none(tmp_path, caplog):
    """The normal state: no block, no value, and nothing logged about it."""
    with caplog.at_level(logging.DEBUG):
        cfg = load_config(
            _write(
                tmp_path,
                """
                mode: standalone
                standalone:
                  users:
                    - username: alice
                      password_hash: "$2b$12$x"
                """,
            )
        )
    assert cfg.login_info is None
    assert "login_info" not in caplog.text


def test_message_without_the_gate_is_debug_only(tmp_path, caplog):
    """A staged message is the steady state; it must not be noisy (§4.2)."""
    with caplog.at_level(logging.DEBUG):
        cfg = load_config(
            _write(
                tmp_path,
                _standalone(
                    f"""
                    login_info:
                      message: "{MESSAGE}"
                    """
                ),
            )
        )
    assert cfg.login_info is None
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert any(r.levelno == logging.DEBUG for r in caplog.records)


def test_gate_explicitly_false_with_a_message_is_inert(tmp_path):
    cfg = load_config(
        _write(
            tmp_path,
            _standalone(
                f"""
                login_info:
                  enabled: false
                  message: "{MESSAGE}"
                """
            ),
        )
    )
    assert cfg.login_info is None


@pytest.mark.parametrize(
    "message_line",
    [
        "",  # key absent entirely
        '  message: ""',
        '  message: "   "',
        "  message: \"\\n\\n\"",
    ],
    ids=["absent", "empty", "whitespace", "newlines-only"],
)
def test_gate_on_without_usable_text_warns(tmp_path, caplog, message_line):
    """An operator who opted in and gets nothing needs to be told (§4.2)."""
    block = "login_info:\n  enabled: true\n" + (
        f"{message_line}\n" if message_line else ""
    )
    with caplog.at_level(logging.WARNING):
        cfg = load_config(_write(tmp_path, _standalone(block)))
    assert cfg.login_info is None
    assert "login_info" in caplog.text


# --------------------------------------------------------------------------- #
# Mode interaction (§9)
# --------------------------------------------------------------------------- #

def test_disabled_mode_drops_a_fully_populated_block(tmp_path, caplog):
    """No in-store login to annotate; debug, not a warning — the file is shared."""
    with caplog.at_level(logging.DEBUG):
        cfg = load_config(
            _write(
                tmp_path,
                _standalone(
                    f"""
                    login_info:
                      enabled: true
                      message: "{MESSAGE}"
                    """,
                    mode="disabled",
                ),
            )
        )
    assert cfg.login_info is None
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


# --------------------------------------------------------------------------- #
# Malformed shapes: warn and boot, never raise (§4.2)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "block",
    [
        "login_info: just-a-string",
        "login_info: [a, b]",
        "login_info:\n  enabled: true\n  message: [a, b]",
        "login_info:\n  enabled: true\n  message: {a: b}",
        "login_info:\n  enabled: true\n  message: 42",
    ],
    ids=["block-string", "block-list", "msg-list", "msg-mapping", "msg-number"],
)
def test_malformed_shapes_warn_and_resolve_to_none(tmp_path, caplog, block):
    with caplog.at_level(logging.WARNING):
        cfg = load_config(_write(tmp_path, _standalone(block)))
    assert cfg.login_info is None
    assert "login_info" in caplog.text


def test_a_malformed_block_never_stops_standalone_from_booting(tmp_path):
    """Regression for §4.2: a banner must not be able to fail the server closed.

    ``load_config`` hard-fails on a broken *standalone* config, which is what
    makes this worth asserting explicitly rather than inferring from the tests
    above.
    """
    path = _write(tmp_path, _standalone("login_info: not-a-mapping"))
    cfg = load_config(path)  # must not raise
    assert cfg.mode == "standalone"
    assert cfg.login_info is None
    # Sanity: the loader really does still fail closed on other breakage.
    with pytest.raises(AccessControlConfigError):
        load_config(_write(tmp_path, "mode: bogus\n"))


@pytest.mark.parametrize("raw", ["yes", "TRUE", "1", "on"])
def test_quoted_truthy_enabled_is_coerced(tmp_path, raw):
    cfg = load_config(
        _write(
            tmp_path,
            _standalone(
                f"""
                login_info:
                  enabled: "{raw}"
                  message: "{MESSAGE}"
                """
            ),
        )
    )
    assert cfg.login_info == MESSAGE


@pytest.mark.parametrize("raw", ["nope", "0", "maybe"])
def test_quoted_non_truthy_enabled_is_false_with_a_warning(tmp_path, caplog, raw):
    with caplog.at_level(logging.WARNING):
        cfg = load_config(
            _write(
                tmp_path,
                _standalone(
                    f"""
                    login_info:
                      enabled: "{raw}"
                      message: "{MESSAGE}"
                    """
                ),
            )
        )
    assert cfg.login_info is None
    assert "enabled" in caplog.text


# --------------------------------------------------------------------------- #
# Line breaks (§4.3) and normalization (§5 step 3)
# --------------------------------------------------------------------------- #

def test_literal_block_scalar_preserves_newlines(tmp_path):
    cfg = load_config(
        _write(
            tmp_path,
            _standalone(
                """
                login_info:
                  enabled: true
                  message: |
                    First line.
                    Second line.
                """
            ),
        )
    )
    assert cfg.login_info == "First line.\nSecond line."


def test_folded_block_scalar_folds_newlines(tmp_path):
    cfg = load_config(
        _write(
            tmp_path,
            _standalone(
                """
                login_info:
                  enabled: true
                  message: >
                    First line.
                    Second line.
                """
            ),
        )
    )
    assert cfg.login_info == "First line. Second line."


def test_backslash_n_in_a_block_scalar_stays_two_characters(tmp_path):
    """There is no escape syntax to get wrong inside a block scalar (§4.3)."""
    cfg = load_config(
        _write(
            tmp_path,
            _standalone(
                r"""
                login_info:
                  enabled: true
                  message: |
                    One\nTwo
                """
            ),
        )
    )
    assert cfg.login_info == "One\\nTwo"
    assert "\n" not in cfg.login_info


@pytest.mark.parametrize("escape", ["\\r\\n", "\\r"], ids=["crlf", "cr"])
def test_carriage_returns_are_normalized(tmp_path, escape):
    """A ``\\r`` escape is the one route by which a CR reaches the sanitizer.

    YAML itself normalizes on-disk line breaks (see the test below), so step 3
    exists for the escaped form — and as belt-and-braces should the value ever
    arrive from somewhere other than the parser.
    """
    cfg = load_config(
        _write(
            tmp_path,
            _standalone(
                f"""
                login_info:
                  enabled: true
                  message: "First.{escape}Second."
                """
            ),
        )
    )
    assert cfg.login_info == "First.\nSecond."


def test_a_crlf_file_on_disk_yields_lf_line_breaks(tmp_path):
    """A config edited on Windows must not leave CRs in the message."""
    path = tmp_path / "acl.yaml"
    path.write_bytes(
        b"mode: standalone\r\n"
        b"standalone:\r\n"
        b"  users:\r\n"
        b'    - username: alice\r\n      password_hash: "$2b$12$x"\r\n'
        b"  login_info:\r\n"
        b"    enabled: true\r\n"
        b"    message: |\r\n"
        b"      First.\r\n"
        b"      Second.\r\n"
    )
    cfg = load_config(str(path))
    assert cfg.login_info == "First.\nSecond."
    assert "\r" not in cfg.login_info


# --------------------------------------------------------------------------- #
# Control characters (§5 step 4)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "escaped",
    [
        "\\e[31mred\\e[0m",  # ANSI CSI: the terminal-injection case
        "a\\0b",             # NUL
        "a\\ab",             # BEL
        "a\\tb",             # TAB — stripped like any other control character
        "a\\x85b",           # C1 NEL
        "a\\x7fb",           # DEL
    ],
    ids=["ansi-csi", "nul", "bel", "tab", "c1-nel", "del"],
)
def test_control_characters_are_stripped(tmp_path, escaped):
    cfg = load_config(
        _write(
            tmp_path,
            _standalone(
                f"""
                login_info:
                  enabled: true
                  message: "{escaped}"
                """
            ),
        )
    )
    assert cfg.login_info is not None
    for ch in cfg.login_info:
        assert not ("\x00" <= ch <= "\x1f" or "\x7f" <= ch <= "\x9f"), repr(ch)


def test_newline_survives_the_control_character_strip(tmp_path):
    cfg = load_config(
        _write(
            tmp_path,
            _standalone(
                """
                login_info:
                  enabled: true
                  message: "a\\e[31m\\nb"
                """
            ),
        )
    )
    assert cfg.login_info == "a[31m\nb"


# --------------------------------------------------------------------------- #
# Caps (§5 step 5)
# --------------------------------------------------------------------------- #

def test_over_long_message_is_truncated_with_a_warning(tmp_path, caplog):
    with caplog.at_level(logging.WARNING):
        cfg = load_config(
            _write(
                tmp_path,
                _standalone(
                    f"""
                    login_info:
                      enabled: true
                      message: "{'x' * 2000}"
                    """
                ),
            )
        )
    assert cfg.login_info is not None
    assert len(cfg.login_info) == LOGIN_INFO_MAX_CHARS
    assert "character" in caplog.text


def test_too_many_lines_are_truncated_with_a_warning(tmp_path, caplog):
    lines = "\n".join(f"    line {i}" for i in range(20))
    with caplog.at_level(logging.WARNING):
        cfg = load_config(
            _write(
                tmp_path,
                _standalone("login_info:\n  enabled: true\n  message: |\n" + lines),
            )
        )
    assert cfg.login_info is not None
    assert len(cfg.login_info.split("\n")) == LOGIN_INFO_MAX_LINES
    assert "line" in caplog.text


# --------------------------------------------------------------------------- #
# Idempotence
# --------------------------------------------------------------------------- #

def test_sanitizing_an_already_sanitized_value_is_a_no_op(tmp_path):
    from skillberry_store.access_control.config import _sanitize_login_info

    once = _sanitize_login_info("  a\r\n\x1b[31mb\t \n c  ", "cfg.yaml")
    assert _sanitize_login_info(once, "cfg.yaml") == once
