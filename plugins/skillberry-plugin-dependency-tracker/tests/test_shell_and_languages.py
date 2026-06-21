"""Tests for shell command extraction and language detection."""

from skillberry_plugin_dependency_tracker.resolver.languages import detect_language
from skillberry_plugin_dependency_tracker.resolver.shell import (
    extract_shell_commands,
)

# ── language detection ────────────────────────────────────────────────────────


def test_detect_by_extension():
    assert detect_language("main.py", "") == "python"
    assert detect_language("setup.sh", "") == "shell"
    assert detect_language("run.bash", "") == "shell"
    assert detect_language("widget.js", "") is None


def test_detect_by_shebang():
    assert detect_language("noext", "#!/usr/bin/env python3\nprint(1)") == "python"
    assert detect_language("noext", "#!/bin/bash\necho hi") == "shell"
    assert detect_language("noext", "#!/bin/sh\necho hi") == "shell"


def test_detect_by_content_heuristic():
    assert detect_language("snippet", "import os\nfrom x import y") == "python"
    assert detect_language("snippet", "def foo():\n  pass") == "python"
    assert detect_language("snippet", 'export FOO=bar\nif [ -n "$X" ]; then') == "shell"


def test_detect_unknown_returns_none():
    assert detect_language("data", "just some prose, nothing codey") is None
    assert detect_language(None, "") is None


# ── shell command extraction ──────────────────────────────────────────────────


def test_extracts_external_commands():
    code = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "curl -sSL https://x -o o.json\n"
        "jq '.a' o.json\n"
        "node build.js\n"
    )
    cmds = extract_shell_commands(code)
    assert {"curl", "jq", "node"} <= cmds


def test_excludes_builtins_and_keywords():
    code = (
        "if true; then\n  echo hi\n  export X=1\nfi\nfor i in 1 2; do echo $i; done\n"
    )
    cmds = extract_shell_commands(code)
    for builtin in ("if", "then", "fi", "for", "do", "done", "echo", "export", "true"):
        assert builtin not in cmds


def test_excludes_locally_defined_functions():
    code = (
        "helper() {\n  curl https://x\n}\n"
        "function setup {\n  echo hi\n}\n"
        "helper\n"
        "setup\n"
    )
    cmds = extract_shell_commands(code)
    assert "helper" not in cmds
    assert "setup" not in cmds
    assert "curl" in cmds


def test_skips_comments_and_assignments():
    code = "# this calls wget\nFOO=bar\ngit clone https://x\n"
    cmds = extract_shell_commands(code)
    assert "wget" not in cmds  # only in a comment
    assert "FOO" not in cmds  # assignment, not a command
    assert "git" in cmds


def test_heredoc_body_not_parsed_as_commands():
    # Scripts often `cat <<EOF` an embedded JS/CSS/JSON file; that content must
    # NOT be treated as shell commands (the real-world false-positive source).
    code = (
        "#!/usr/bin/env bash\n"
        "cat > config.js <<EOF\n"
        "import something from 'x'\n"
        "const card = { colors: DEFAULT }\n"
        "module.exports = { darkMode: false }\n"
        "EOF\n"
        "node build.js\n"
        "npm install\n"
    )
    cmds = extract_shell_commands(code)
    assert cmds == {"cat", "node", "npm"}
    # none of the heredoc-body tokens leak in
    for noise in (
        "import",
        "const",
        "card",
        "colors",
        "DEFAULT",
        "module.exports",
        "EOF",
    ):
        assert noise not in cmds


def test_sudo_prefix_skipped_to_real_command():
    code = "sudo apt-get install -y jq\nnohup node server.js &\n"
    cmds = extract_shell_commands(code)
    assert "apt-get" in cmds  # sudo prefix stepped over
    assert "node" in cmds  # nohup prefix stepped over
    assert "sudo" not in cmds
    assert "nohup" not in cmds


def test_multiline_quoted_arg_body_not_parsed():
    # `node -e "<multi-line inline JS>"` — the JS body must not become commands.
    code = (
        'node -e "\n'
        "const fs = require('fs');\n"
        "config.compilerOptions = {};\n"
        "config.compilerOptions.baseUrl = '.';\n"
        '"\n'
        "npm run build\n"
    )
    cmds = extract_shell_commands(code)
    assert "node" in cmds
    assert "npm" in cmds
    for noise in ("const", "config.compilerOptions", "config.compilerOptions.baseUrl"):
        assert noise not in cmds


def test_pipeline_each_stage_is_a_command():
    code = "cat f | grep x | sort | uniq -c\n"
    cmds = extract_shell_commands(code)
    assert {"cat", "grep", "sort", "uniq"} <= cmds


def test_empty_safe():
    assert extract_shell_commands("") == set()
    assert extract_shell_commands(None) == set()
