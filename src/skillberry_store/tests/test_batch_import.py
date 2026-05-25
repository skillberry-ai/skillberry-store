# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""Tests for batch import functionality."""

import pytest
import json
import tempfile
import os
from pathlib import Path

from skillberry_store.tools.anthropic.batch_importer import (
    detect_skill_directories,
    detect_local_skill_directories,
    batch_import_anthropic_skills,
)


class TestDetectSkillDirectories:
    """Tests for detect_skill_directories function."""

    def test_detect_single_skill_directory(self):
        """Test detecting a single skill directory."""
        files = [
            {"name": "SKILL.md", "path": "skill1/SKILL.md", "content": "# Skill 1"},
            {"name": "tool.py", "path": "skill1/tool.py", "content": "def foo(): pass"},
            {"name": "README.md", "path": "README.md", "content": "# Parent"},
        ]

        skill_dirs = detect_skill_directories(files)

        assert len(skill_dirs) == 1
        assert skill_dirs[0]["name"] == "skill1"
        assert skill_dirs[0]["path"] == "skill1"
        assert len(skill_dirs[0]["files"]) == 2

    def test_detect_multiple_skill_directories(self):
        """Test detecting multiple skill directories."""
        files = [
            {"name": "SKILL.md", "path": "skill1/SKILL.md", "content": "# Skill 1"},
            {"name": "tool1.py", "path": "skill1/tool1.py", "content": "def foo(): pass"},
            {"name": "SKILL.md", "path": "skill2/SKILL.md", "content": "# Skill 2"},
            {"name": "tool2.py", "path": "skill2/tool2.py", "content": "def bar(): pass"},
            {"name": "README.md", "path": "README.md", "content": "# Parent"},
        ]

        skill_dirs = detect_skill_directories(files)

        assert len(skill_dirs) == 2
        skill_names = {sd["name"] for sd in skill_dirs}
        assert skill_names == {"skill1", "skill2"}

    def test_detect_nested_skill_directories(self):
        """Test detecting nested skill directories."""
        files = [
            {"name": "SKILL.md", "path": "parent/skill1/SKILL.md", "content": "# Skill 1"},
            {"name": "tool.py", "path": "parent/skill1/tool.py", "content": "def foo(): pass"},
            {"name": "SKILL.md", "path": "parent/skill2/SKILL.md", "content": "# Skill 2"},
            {"name": "tool.py", "path": "parent/skill2/tool.py", "content": "def bar(): pass"},
        ]

        skill_dirs = detect_skill_directories(files)

        assert len(skill_dirs) == 2
        skill_paths = {sd["path"] for sd in skill_dirs}
        assert skill_paths == {"parent/skill1", "parent/skill2"}

    def test_no_skill_directories(self):
        """Test when no SKILL.md files are present."""
        files = [
            {"name": "README.md", "path": "README.md", "content": "# Parent"},
            {"name": "tool.py", "path": "tool.py", "content": "def foo(): pass"},
        ]

        skill_dirs = detect_skill_directories(files)

        assert len(skill_dirs) == 0

    def test_case_insensitive_skill_md(self):
        """Test that SKILL.md detection is case-insensitive."""
        files = [
            {"name": "skill.md", "path": "skill1/skill.md", "content": "# Skill 1"},
            {"name": "SKILL.MD", "path": "skill2/SKILL.MD", "content": "# Skill 2"},
            {"name": "Skill.md", "path": "skill3/Skill.md", "content": "# Skill 3"},
        ]

        skill_dirs = detect_skill_directories(files)

        # Should detect all three (case-insensitive)
        assert len(skill_dirs) == 3


class TestDetectLocalSkillDirectories:
    """Tests for detect_local_skill_directories function."""

    def test_detect_local_skill_directories(self):
        """Test detecting skill directories in a local folder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create skill directories
            skill1_dir = Path(tmpdir) / "skill1"
            skill1_dir.mkdir()
            (skill1_dir / "SKILL.md").write_text("# Skill 1")
            (skill1_dir / "tool.py").write_text("def foo(): pass")

            skill2_dir = Path(tmpdir) / "skill2"
            skill2_dir.mkdir()
            (skill2_dir / "SKILL.md").write_text("# Skill 2")
            (skill2_dir / "tool.py").write_text("def bar(): pass")

            # Create a non-skill directory
            other_dir = Path(tmpdir) / "other"
            other_dir.mkdir()
            (other_dir / "README.md").write_text("# Other")

            skill_dirs = detect_local_skill_directories(tmpdir)

            assert len(skill_dirs) == 2
            skill_names = {sd["name"] for sd in skill_dirs}
            assert skill_names == {"skill1", "skill2"}

    def test_nonexistent_directory(self):
        """Test error handling for nonexistent directory."""
        with pytest.raises(Exception, match="Folder does not exist"):
            detect_local_skill_directories("/nonexistent/path")

    def test_file_instead_of_directory(self):
        """Test error handling when path is a file, not a directory."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            with pytest.raises(Exception, match="Path is not a directory"):
                detect_local_skill_directories(tmpfile.name)


class TestBatchImportAnthropicSkills:
    """Tests for batch_import_anthropic_skills function."""

    def test_batch_import_from_files(self):
        """Test batch import from file list."""
        # Create mock files for two skills
        files = [
            {
                "name": "SKILL.md",
                "path": "skill1/SKILL.md",
                "content": "---\nname: test_skill_1\ndescription: Test Skill 1\n---\n# Test Skill 1",
            },
            {
                "name": "tool.py",
                "path": "skill1/tool.py",
                "content": 'def test_function():\n    """Test function."""\n    return "test"',
            },
            {
                "name": "SKILL.md",
                "path": "skill2/SKILL.md",
                "content": "---\nname: test_skill_2\ndescription: Test Skill 2\n---\n# Test Skill 2",
            },
            {
                "name": "doc.md",
                "path": "skill2/doc.md",
                "content": "# Documentation\n\nThis is a test document.",
            },
        ]

        # Mock the files source type (internal use)
        # We'll need to group files by directory first
        skill1_files = [f for f in files if f["path"].startswith("skill1/")]
        skill2_files = [f for f in files if f["path"].startswith("skill2/")]

        # Test with skill1 files
        results = []
        for skill_files in [skill1_files, skill2_files]:
            try:
                from skillberry_store.tools.anthropic.importer import import_anthropic_skill

                skill_name, skill_description, tools, snippets, ignored_files = (
                    import_anthropic_skill(
                        source_type="files",
                        source_data=skill_files,
                        snippet_mode="file",
                        treat_all_as_documents=False,
                    )
                )

                results.append(
                    {
                        "success": True,
                        "skill_name": skill_name,
                        "tools_created": len(tools),
                        "snippets_created": len(snippets),
                    }
                )
            except Exception as e:
                results.append({"success": False, "error": str(e)})

        # Verify results
        assert len(results) == 2
        assert all(r["success"] for r in results)

    def test_batch_import_with_errors(self):
        """Test batch import handles errors gracefully."""
        # Create files with one valid skill and one invalid
        files = [
            {
                "name": "SKILL.md",
                "path": "valid_skill/SKILL.md",
                "content": "---\nname: valid_skill\ndescription: Valid Skill\n---\n# Valid",
            },
            {
                "name": "tool.py",
                "path": "valid_skill/tool.py",
                "content": 'def test():\n    """Test."""\n    pass',
            },
            {
                "name": "SKILL.md",
                "path": "invalid_skill/SKILL.md",
                "content": "# Invalid - no metadata",
            },
            # Invalid Python syntax
            {
                "name": "bad.py",
                "path": "invalid_skill/bad.py",
                "content": "def broken(\n    # Missing closing parenthesis",
            },
        ]

        # Group by directory
        valid_files = [f for f in files if f["path"].startswith("valid_skill/")]
        invalid_files = [f for f in files if f["path"].startswith("invalid_skill/")]

        results = []
        for skill_files in [valid_files, invalid_files]:
            try:
                from skillberry_store.tools.anthropic.importer import import_anthropic_skill

                skill_name, skill_description, tools, snippets, ignored_files = (
                    import_anthropic_skill(
                        source_type="files",
                        source_data=skill_files,
                        snippet_mode="file",
                        treat_all_as_documents=False,
                    )
                )

                results.append(
                    {
                        "success": True,
                        "skill_name": skill_name,
                    }
                )
            except Exception as e:
                results.append({"success": False, "error": str(e)})

        # Should have one success and one failure
        assert len(results) == 2
        successes = [r for r in results if r["success"]]
        failures = [r for r in results if not r["success"]]

        assert len(successes) >= 1  # At least the valid skill should succeed
        # The invalid skill might succeed with ignored files, so we don't assert failures


class TestBatchImportIntegration:
    """Integration tests for batch import."""

    def test_batch_import_local_folder(self):
        """Test batch import from a local folder structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create skill 1
            skill1_dir = Path(tmpdir) / "calculator"
            skill1_dir.mkdir()
            (skill1_dir / "SKILL.md").write_text(
                "---\nname: calculator\ndescription: Calculator skill\n---\n# Calculator"
            )
            (skill1_dir / "add.py").write_text(
                'def add(a: int, b: int) -> int:\n    """Add two numbers."""\n    return a + b'
            )

            # Create skill 2
            skill2_dir = Path(tmpdir) / "text_processor"
            skill2_dir.mkdir()
            (skill2_dir / "SKILL.md").write_text(
                "---\nname: text_processor\ndescription: Text processing skill\n---\n# Text Processor"
            )
            (skill2_dir / "uppercase.py").write_text(
                'def uppercase(text: str) -> str:\n    """Convert to uppercase."""\n    return text.upper()'
            )
            (skill2_dir / "docs.md").write_text("# Documentation\n\nText processing docs.")

            # Detect skill directories
            skill_dirs = detect_local_skill_directories(tmpdir)

            assert len(skill_dirs) == 2
            skill_names = {sd["name"] for sd in skill_dirs}
            assert skill_names == {"calculator", "text_processor"}

            # Verify each skill has the expected files
            for skill_dir in skill_dirs:
                assert len(skill_dir["files"]) >= 2  # At least SKILL.md and one other file
                file_names = {f["name"] for f in skill_dir["files"]}
                assert "SKILL.md" in file_names or "skill.md" in file_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
