"""Tests for AST top-level import extraction."""

from skillberry_plugin_dependency_tracker.resolver.imports import (
    extract_top_level_imports,
)


def test_stdlib_excluded():
    code = "import os\nimport sys\nimport json\nfrom pathlib import Path\n"
    assert extract_top_level_imports(code) == set()


def test_dotted_import_reduced_to_top_level():
    code = "import a.b.c\nimport requests as r\n"
    assert extract_top_level_imports(code) == {"a", "requests"}


def test_from_import_absolute():
    code = "from requests import get\nfrom a.b import c\n"
    assert extract_top_level_imports(code) == {"requests", "a"}


def test_relative_imports_skipped():
    code = "from . import x\nfrom ..pkg import y\nfrom .sibling import z\n"
    assert extract_top_level_imports(code) == set()


def test_mixed_stdlib_and_external():
    code = "import os\nimport pandas\nfrom numpy import array\nfrom . import local\n"
    assert extract_top_level_imports(code) == {"pandas", "numpy"}


def test_bad_syntax_returns_empty_set():
    assert extract_top_level_imports("def (:\n  this is not python") == set()


def test_empty_and_none_safe():
    assert extract_top_level_imports("") == set()
    assert extract_top_level_imports(None) == set()
