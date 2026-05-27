"""Tests for path traversal vulnerability fix in FileHandler."""

import os
import pytest
import tempfile
import shutil
from fastapi import HTTPException

from skillberry_store.modules.file_handler import FileHandler


class TestPathTraversalFix:
    """Test suite for path traversal vulnerability fix."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)

    @pytest.fixture
    def file_handler(self, temp_dir):
        """Create a FileHandler instance for testing."""
        return FileHandler(temp_dir)

    def test_valid_subdirectory_access(self, file_handler, temp_dir):
        """Test that valid subdirectory access works correctly."""
        # Write a file to a valid subdirectory
        result = file_handler.write_file_content(
            filename="test.txt",
            file_content="test content",
            subdirectory="valid_subdir"
        )
        assert result["message"] == "File 'test.txt' saved successfully."
        
        # Verify the file was created in the correct location
        expected_path = os.path.join(temp_dir, "valid_subdir", "test.txt")
        assert os.path.exists(expected_path)
        
        # Read the file back
        content = file_handler.read_file(
            filename="test.txt",
            raw_content=True,
            subdirectory="valid_subdir"
        )
        assert content == "test content"

    def test_path_traversal_with_dotdot(self, file_handler):
        """Test that path traversal using ../ is blocked."""
        with pytest.raises(HTTPException) as exc_info:
            file_handler.write_file_content(
                filename="malicious.txt",
                file_content="malicious content",
                subdirectory="../../../etc"
            )
        assert exc_info.value.status_code == 400
        assert "Path traversal detected" in exc_info.value.detail

    def test_path_traversal_read_file(self, file_handler):
        """Test that path traversal is blocked when reading files."""
        with pytest.raises(HTTPException) as exc_info:
            file_handler.read_file(
                filename="passwd",
                raw_content=True,
                subdirectory="../../../etc"
            )
        assert exc_info.value.status_code == 400
        assert "Path traversal detected" in exc_info.value.detail

    def test_path_traversal_delete_subdirectory(self, file_handler):
        """Test that path traversal is blocked when deleting subdirectories."""
        with pytest.raises(HTTPException) as exc_info:
            file_handler.delete_subdirectory("../../../tmp")
        assert exc_info.value.status_code == 400
        assert "Path traversal detected" in exc_info.value.detail

    def test_path_traversal_absolute_path(self, file_handler):
        """Test that absolute paths are blocked."""
        with pytest.raises(HTTPException) as exc_info:
            file_handler.write_file_content(
                filename="malicious.txt",
                file_content="malicious content",
                subdirectory="/etc"
            )
        assert exc_info.value.status_code == 400
        assert "Path traversal detected" in exc_info.value.detail

    def test_nested_valid_subdirectories(self, file_handler, temp_dir):
        """Test that nested valid subdirectories work correctly."""
        # Write a file to a nested subdirectory
        result = file_handler.write_file_content(
            filename="nested.txt",
            file_content="nested content",
            subdirectory="level1/level2/level3"
        )
        assert result["message"] == "File 'nested.txt' saved successfully."
        
        # Verify the file was created
        expected_path = os.path.join(temp_dir, "level1", "level2", "level3", "nested.txt")
        assert os.path.exists(expected_path)

    def test_delete_valid_subdirectory(self, file_handler, temp_dir):
        """Test that deleting a valid subdirectory works correctly."""
        # Create a subdirectory with a file
        subdir = "to_delete"
        file_handler.write_file_content(
            filename="file.txt",
            file_content="content",
            subdirectory=subdir
        )
        
        # Verify it exists
        subdir_path = os.path.join(temp_dir, subdir)
        assert os.path.exists(subdir_path)
        
        # Delete the subdirectory
        result = file_handler.delete_subdirectory(subdir)
        assert result["message"] == f"Subdirectory '{subdir}' deleted successfully."
        
        # Verify it's gone
        assert not os.path.exists(subdir_path)

    def test_path_traversal_with_encoded_characters(self, file_handler, temp_dir):
        """Test that URL-encoded path traversal attempts are handled correctly."""
        # URL encoding is not decoded by the filesystem, so ..%2f..%2f..%2fetc
        # is treated as a literal directory name, not a path traversal.
        # This is actually safe behavior - the encoded string stays within bounds.
        result = file_handler.write_file_content(
            filename="test.txt",
            file_content="content",
            subdirectory="..%2f..%2f..%2fetc"
        )
        assert result["message"] == "File 'test.txt' saved successfully."
        
        # Verify it was created as a literal directory name within temp_dir
        expected_path = os.path.join(temp_dir, "..%2f..%2f..%2fetc", "test.txt")
        assert os.path.exists(expected_path)

    def test_symlink_escape_attempt(self, file_handler, temp_dir):
        """Test that symbolic links cannot be used to escape the directory."""
        # Create a symlink pointing outside the directory
        symlink_path = os.path.join(temp_dir, "escape_link")
        try:
            os.symlink("/etc", symlink_path)
            
            # Try to access through the symlink
            with pytest.raises(HTTPException) as exc_info:
                file_handler.read_file(
                    filename="passwd",
                    raw_content=True,
                    subdirectory="escape_link"
                )
            assert exc_info.value.status_code == 400
            assert "Path traversal detected" in exc_info.value.detail
        except OSError:
            # Symlink creation might fail on some systems (e.g., Windows without admin)
            pytest.skip("Symlink creation not supported on this system")
        finally:
            # Cleanup
            if os.path.exists(symlink_path):
                os.remove(symlink_path)

# Made with Bob
