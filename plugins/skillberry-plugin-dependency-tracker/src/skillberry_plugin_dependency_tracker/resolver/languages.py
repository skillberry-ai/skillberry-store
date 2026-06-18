"""Language detection for a code blob.

Routes each collected file to the right extractor (Python or shell) or marks it
unsupported. Detection uses the filename extension first (most reliable for store
tools, whose ``module_name`` carries a real extension), then a shebang, then a
light content heuristic. Returns ``None`` when the language is unsupported, so
the caller can record the file in ``skipped_files``.
"""

from __future__ import annotations

import re
from typing import Optional

from .base import LANG_PYTHON, LANG_SHELL

# Extension -> language.
_EXT_LANG = {
    ".py": LANG_PYTHON,
    ".pyw": LANG_PYTHON,
    ".pyi": LANG_PYTHON,
    ".sh": LANG_SHELL,
    ".bash": LANG_SHELL,
    ".zsh": LANG_SHELL,
    ".ksh": LANG_SHELL,
}

_SHEBANG_RE = re.compile(r"^#!\s*(\S+)")


def _from_shebang(code: str) -> Optional[str]:
    first = (code or "").lstrip().splitlines()[:1]
    if not first:
        return None
    m = _SHEBANG_RE.match(first[0])
    if not m:
        return None
    interp = m.group(1).rsplit("/", 1)[-1]
    if interp.startswith("python"):
        return LANG_PYTHON
    if interp in ("sh", "bash", "zsh", "ksh", "dash") or interp == "env":
        # `#!/usr/bin/env bash` -> the env arg is on the same token list; keep
        # it simple: env defaults to shell unless a python arg follows.
        return LANG_SHELL
    return None


# Light content heuristics for blobs with no extension (e.g. snippets). Applied
# only after extension + shebang fail. Deliberately conservative.
_PY_HINT = re.compile(
    r"(?m)^\s*(?:import\s+\w|from\s+[\w.]+\s+import\s|def\s+\w+\s*\(|class\s+\w+\s*[:(])"
)
_SH_HINT = re.compile(
    r"(?m)^\s*(?:export\s+\w+=|if\s+\[|for\s+\w+\s+in\s|fi\b|done\b|"
    r"\w+\s*=\s*\$\(|echo\s)"
)


def _from_content(code: str) -> Optional[str]:
    text = code or ""
    if _PY_HINT.search(text):
        return LANG_PYTHON
    if _SH_HINT.search(text):
        return LANG_SHELL
    return None


def detect_language(filename: Optional[str], code: str) -> Optional[str]:
    """Best-effort language for a blob. ``None`` => unsupported / unknown.

    Order of evidence: filename extension, then shebang, then a light content
    heuristic (for extension-less blobs such as snippets).
    """
    name = (filename or "").lower()
    for ext, lang in _EXT_LANG.items():
        if name.endswith(ext):
            return lang

    # `#!/usr/bin/env python3` etc.
    shebang = _from_shebang(code or "")
    if shebang:
        # refine env-python case
        first_line = (code or "").lstrip().splitlines()[:1]
        if first_line and "python" in first_line[0]:
            return LANG_PYTHON
        return shebang

    return _from_content(code or "")
