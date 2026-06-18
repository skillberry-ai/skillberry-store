"""Extract external command dependencies from shell scripts.

A shell script's "dependencies" are the external executables it invokes
(``curl``, ``jq``, ``node``, ``zip`` …) — the shell analogue of Python imports.
We extract the command tokens, drop shell builtins/keywords and anything defined
in the script itself (functions, aliases, assigned variables used as commands),
and return the set of external command names.

These are *system* dependencies: they have no version or artifact hash here (they
are whatever is installed on the host), so the plugin records them with
``source: "system"`` and no hashes — distinct from resolved PyPI packages.
"""

from __future__ import annotations

import re
from typing import Set

# POSIX/bash builtins + common keywords that are never external deps.
_SHELL_BUILTINS = {
    "alias",
    "bg",
    "bind",
    "break",
    "builtin",
    "caller",
    "case",
    "cd",
    "command",
    "compgen",
    "complete",
    "continue",
    "declare",
    "dirs",
    "disown",
    "do",
    "done",
    "echo",
    "elif",
    "else",
    "enable",
    "esac",
    "eval",
    "exec",
    "exit",
    "export",
    "fi",
    "fg",
    "for",
    "function",
    "getopts",
    "hash",
    "help",
    "history",
    "if",
    "in",
    "jobs",
    "kill",
    "let",
    "local",
    "logout",
    "popd",
    "printf",
    "pushd",
    "pwd",
    "read",
    "readarray",
    "readonly",
    "return",
    "select",
    "set",
    "shift",
    "shopt",
    "source",
    "suspend",
    "test",
    "then",
    "time",
    "times",
    "trap",
    "type",
    "typeset",
    "ulimit",
    "umask",
    "unalias",
    "unset",
    "until",
    "wait",
    "while",
    "true",
    "false",
    ":",
    ".",
    "[",
    "[[",
    "]]",
    "fc",
    "mapfile",
}

# Split a logical line into statement segments at command separators. We split
# on ; | & and the openers $( ` and `&&`/`||` so each segment's first bareword is
# a command in command position.
_SEGMENT_SPLIT = re.compile(r"(?:\|\||&&|[;|&`]|\$\()")

# A command name: a bareword that may include dots/dashes (docker-compose) but is
# a plausible executable name (must contain a letter, no spaces).
_CMD_NAME = re.compile(r"^[A-Za-z_][\w.-]*$")

# Leading control words that may precede the real command on a segment.
_PREFIX_WORDS = {"sudo", "command", "exec", "nohup", "time", "then", "do", "else", "!"}

# A heredoc start: `<<EOF`, `<<-EOF`, `<< "EOF"`, `cat <<'EOF'` -> capture tag.
_HEREDOC_RE = re.compile(r"<<-?\s*[\"']?([A-Za-z_]\w*)[\"']?")


def _local_function_names(code: str) -> Set[str]:
    """Names of functions defined in the script (so calls to them aren't deps)."""
    names: Set[str] = set()
    for m in re.finditer(r"(?m)^\s*([A-Za-z_]\w*)\s*\(\)\s*\{?", code):
        names.add(m.group(1))
    for m in re.finditer(r"(?m)^\s*function\s+([A-Za-z_]\w*)", code):
        names.add(m.group(1))
    return names


def _count_unescaped(line: str, quote: str) -> int:
    """Count unescaped occurrences of ``quote`` in ``line``."""
    n = 0
    i = 0
    while i < len(line):
        c = line[i]
        if c == "\\":
            i += 2
            continue
        if c == quote:
            n += 1
        i += 1
    return n


def _logical_lines(code: str) -> list:
    """Yield code lines with comments, shebang, heredoc bodies, and multi-line
    quoted-string bodies removed.

    Two big false-positive sources are excluded here:
      - heredoc bodies (``cat <<EOF`` emitting a JS/CSS/JSON file), and
      - multi-line quoted arguments (``node -e "<inline JS spanning lines>"``).
    In both cases the embedded content is data, not shell, and must not be
    parsed as commands.
    """
    out = []
    heredoc_tag = None
    open_quote = None  # we are inside a multi-line '...' or "..." string
    for raw in (code or "").splitlines():
        if heredoc_tag is not None:
            if raw.strip() == heredoc_tag:
                heredoc_tag = None
            continue

        if open_quote is not None:
            # Inside a multi-line string body: drop the line; if the quote closes
            # here (odd count), resume normal parsing afterwards.
            if _count_unescaped(raw, open_quote) % 2 == 1:
                open_quote = None
            continue

        line = raw
        stripped = line.lstrip()
        if stripped.startswith("#"):  # comment / shebang
            continue

        # Heredoc opener: keep the command part before ``<<``.
        m = _HEREDOC_RE.search(line)
        if m:
            heredoc_tag = m.group(1)
            line = line[: m.start()]

        # Strip a trailing ` # comment` (best-effort, ignores quoting).
        hash_idx = line.find(" #")
        if hash_idx != -1:
            line = line[:hash_idx]

        # Detect an unterminated quote that opens a multi-line string (e.g.
        # ``node -e "`` ... ``"``). If a quote char appears an odd number of
        # times on this line, the string continues onto the next line.
        for q in ('"', "'"):
            if _count_unescaped(line, q) % 2 == 1:
                open_quote = q
                break

        if line.strip():
            out.append(line)
    return out


def extract_shell_commands(code: str) -> Set[str]:
    """Return external command names invoked by ``code`` (best-effort).

    Heredoc bodies are excluded, only the first bareword of each statement
    segment is considered, and builtins / locally-defined functions / path-based
    invocations / assignments are dropped.
    """
    if not code:
        return set()
    local_funcs = _local_function_names(code)
    commands: Set[str] = set()

    for line in _logical_lines(code):
        for segment in _SEGMENT_SPLIT.split(line):
            tokens = segment.split()
            # Walk past leading control words (sudo, command, then, …) and any
            # leading VAR=val assignments to reach the actual command token.
            idx = 0
            while idx < len(tokens) and (
                tokens[idx] in _PREFIX_WORDS or "=" in tokens[idx].split("/")[0]
            ):
                # stop if this is a real command that merely contains '=' in an
                # arg; assignment prefixes are NAME=VALUE with no spaces.
                if "=" in tokens[idx] and re.match(r"^[A-Za-z_]\w*=", tokens[idx]):
                    idx += 1
                    continue
                if tokens[idx] in _PREFIX_WORDS:
                    idx += 1
                    continue
                break
            if idx >= len(tokens):
                continue
            first = tokens[idx]
            if first.startswith((".", "/", "$", "-", '"', "'", "(", "{", "}")):
                continue
            if not _CMD_NAME.match(first):
                continue
            if first in _SHELL_BUILTINS or first in local_funcs:
                continue
            if first.isdigit():
                continue
            commands.add(first)
    return commands
