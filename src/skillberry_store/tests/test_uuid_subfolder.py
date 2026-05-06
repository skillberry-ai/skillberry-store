"""Test UUID-based sub-folder functionality for tools."""

import os
import tempfile
import shutil
import json
import pytest
from fastapi import HTTPException
from skillberry_store.modules.resource_handler import ResourceHandler
from skillberry_store.modules.file_handler import FileHandler


class TestUUIDSubfolder:
    """Test suite for UUID-based sub-folder operations."""

    @pytest.fixture
    def temp_tools_dir(self):
        """Create a temporary tools directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def file_handler(self, temp_tools_dir):
        """Create a FileHandler instance for testing."""
        return FileHandler(temp_tools_dir)
    
    @pytest.fixture
    def resource_handler(self, temp_tools_dir):
        """Create a ResourceHandler instance for testing."""
        return ResourceHandler(temp_tools_dir, "tool")

    def test_get_tool_subfolder_path(self, temp_tools_dir, resource_handler):
        """Test getting the path to a tool's sub-folder."""
        tool_uuid = "12345678-1234-1234-1234-123456789abc"
        expected_path = os.path.join(temp_tools_dir, tool_uuid.lower())
        
        result = resource_handler.get_resource_subfolder_path(tool_uuid)
        
        assert result == expected_path

    def test_ensure_tool_subfolder(self, temp_tools_dir, resource_handler):
        """Test creating a tool's sub-folder."""
        tool_uuid = "12345678-1234-1234-1234-123456789abc"
        
        subfolder_path = resource_handler.ensure_resource_subfolder(tool_uuid)
        
        assert os.path.exists(subfolder_path)
        assert os.path.isdir(subfolder_path)
        assert subfolder_path == os.path.join(temp_tools_dir, tool_uuid.lower())

    def test_get_module_file_path(self, temp_tools_dir, resource_handler):
        """Test getting the full path to a module file."""
        tool_uuid = "12345678-1234-1234-1234-123456789abc"
        module_name = "test_module.py"
        expected_path = os.path.join(temp_tools_dir, tool_uuid.lower(), module_name)
        
        result = resource_handler.get_resource_file_path(tool_uuid, module_name)
        
        assert result == expected_path

    def test_write_and_read_module_file(self, temp_tools_dir, resource_handler):
        """Test writing and reading a module file."""
        tool_uuid = "12345678-1234-1234-1234-123456789abc"
        module_name = "test_module.py"
        content = "def test_function():\n    return 'Hello, World!'\n"
        
        # Write the file
        resource_handler.write_resource_file(tool_uuid, module_name, content)
        
        # Verify file exists
        file_path = resource_handler.get_resource_file_path(tool_uuid, module_name)
        assert os.path.exists(file_path)
        
        # Read the file
        read_content = resource_handler.read_resource_file(tool_uuid, module_name, raw_content=True)
        
        assert read_content == content

    def test_read_nonexistent_module_file(self, temp_tools_dir, resource_handler):
        """Test reading a non-existent module file raises HTTPException."""
        tool_uuid = "12345678-1234-1234-1234-123456789abc"
        module_name = "nonexistent.py"
        
        with pytest.raises(HTTPException) as exc_info:
            resource_handler.read_resource_file(tool_uuid, module_name, raw_content=True)
        
        assert exc_info.value.status_code == 404

    def test_delete_tool_subfolder(self, temp_tools_dir, resource_handler):
        """Test deleting a tool's sub-folder."""
        tool_uuid = "12345678-1234-1234-1234-123456789abc"
        module_name = "test_module.py"
        content = "def test():\n    pass\n"
        
        # Create sub-folder and file
        resource_handler.write_resource_file(tool_uuid, module_name, content)
        subfolder_path = resource_handler.get_resource_subfolder_path(tool_uuid)
        assert os.path.exists(subfolder_path)
        
        # Delete the sub-folder
        resource_handler.delete_resource_folder(tool_uuid)
        
        # Verify it's deleted
        assert not os.path.exists(subfolder_path)

    def test_delete_nonexistent_subfolder(self, temp_tools_dir, resource_handler):
        """Test deleting a non-existent sub-folder raises HTTPException."""
        tool_uuid = "12345678-1234-1234-1234-123456789abc"
        
        # Should raise HTTPException for non-existent resource
        with pytest.raises(HTTPException) as exc_info:
            resource_handler.delete_resource_folder(tool_uuid)
        assert exc_info.value.status_code == 404

    def test_multiple_files_in_subfolder(self, temp_tools_dir, resource_handler):
        """Test storing multiple files in a tool's sub-folder."""
        tool_uuid = "12345678-1234-1234-1234-123456789abc"
        
        files = {
            "main.py": "def main():\n    pass\n",
            "utils.py": "def helper():\n    pass\n",
            "config.json": '{"key": "value"}\n',
        }
        
        # Write all files
        for filename, content in files.items():
            resource_handler.write_resource_file(tool_uuid, filename, content)
        
        # Verify all files exist
        subfolder_path = resource_handler.get_resource_subfolder_path(tool_uuid)
        for filename in files.keys():
            file_path = os.path.join(subfolder_path, filename)
            assert os.path.exists(file_path)
        
        # Read and verify content
        for filename, expected_content in files.items():
            read_content = resource_handler.read_resource_file(tool_uuid, filename, raw_content=True)
            assert read_content == expected_content

    def test_uuid_case_insensitive(self, temp_tools_dir, resource_handler):
        """Test that UUID handling is case-insensitive."""
        tool_uuid_upper = "ABCDEF12-3456-7890-ABCD-EF1234567890"
        tool_uuid_lower = tool_uuid_upper.lower()
        module_name = "test.py"
        content = "# test\n"
        
        # Write with uppercase UUID
        resource_handler.write_resource_file(tool_uuid_upper, module_name, content)
        
        # Read with lowercase UUID
        read_content = resource_handler.read_resource_file(tool_uuid_lower, module_name, raw_content=True)
        
        assert read_content == content
        
        # Verify only one folder was created (lowercase)
        subfolder_path = resource_handler.get_resource_subfolder_path(tool_uuid_lower)
        assert os.path.exists(subfolder_path)

    def test_get_tool_manifest_path(self, temp_tools_dir, resource_handler):
        """Test getting the path to tool.json."""
        tool_uuid = "12345678-1234-1234-1234-123456789abc"
        expected_path = os.path.join(temp_tools_dir, tool_uuid.lower(), "tool.json")
        
        result = resource_handler.get_manifest_path(tool_uuid)
        
        assert result == expected_path

    def test_write_and_read_tool_manifest(self, temp_tools_dir, resource_handler):
        """Test writing and reading tool.json."""
        tool_uuid = "12345678-1234-1234-1234-123456789abc"
        manifest_data = {"name": "test_tool", "uuid": tool_uuid, "version": "1.0.0"}
        
        # Write the manifest
        resource_handler.write_manifest(tool_uuid, manifest_data)
        
        # Verify file exists
        manifest_path = resource_handler.get_manifest_path(tool_uuid)
        assert os.path.exists(manifest_path)
        
        # Read the manifest
        read_data = resource_handler.read_manifest(tool_uuid)
        
        assert read_data == manifest_data

    def test_read_nonexistent_tool_manifest(self, temp_tools_dir, resource_handler):
        """Test reading a non-existent tool.json raises HTTPException."""
        tool_uuid = "12345678-1234-1234-1234-123456789abc"
        
        with pytest.raises(HTTPException) as exc_info:
            resource_handler.read_manifest(tool_uuid)
        
        assert exc_info.value.status_code == 404

    def test_get_available_tool_names(self, temp_tools_dir, resource_handler):
        """Test getting list of available tool names."""
        # Create multiple tools
        tools = [
            ("aaaaaaaa-1111-1111-1111-111111111111", "tool_one"),
            ("bbbbbbbb-2222-2222-2222-222222222222", "tool_two"),
            ("cccccccc-3333-3333-3333-333333333333", "tool_three"),
        ]
        
        for tool_uuid, tool_name in tools:
            manifest = {"name": tool_name, "uuid": tool_uuid}
            resource_handler.write_manifest(tool_uuid, manifest)
        
        # Get available tool names
        all_resources = resource_handler.list_all_resources()
        available_names = [r["name"] for r in all_resources]
        
        assert len(available_names) == 3
        assert "tool_one" in available_names
        assert "tool_two" in available_names
        assert "tool_three" in available_names

    def test_complete_tool_structure(self, temp_tools_dir, resource_handler):
        """Test complete tool structure with manifest and modules."""
        tool_uuid = "12345678-1234-1234-1234-123456789abc"
        tool_name = "complete_tool"
        
        # Write manifest
        manifest = {"name": tool_name, "uuid": tool_uuid, "module_name": "main.py"}
        resource_handler.write_manifest(tool_uuid, manifest)
        
        # Write module files
        resource_handler.write_resource_file(tool_uuid, "main.py", "def main():\n    pass\n")
        resource_handler.write_resource_file(tool_uuid, "utils.py", "def helper():\n    pass\n")
        
        # Verify structure
        tool_folder = resource_handler.get_resource_subfolder_path(tool_uuid)
        assert os.path.exists(os.path.join(tool_folder, "tool.json"))
        assert os.path.exists(os.path.join(tool_folder, "main.py"))
        assert os.path.exists(os.path.join(tool_folder, "utils.py"))
        
        # Verify we can read everything
        read_manifest = resource_handler.read_manifest(tool_uuid)
        assert read_manifest["name"] == tool_name
        
        main_content = resource_handler.read_resource_file(tool_uuid, "main.py", raw_content=True)
        assert "def main()" in main_content
        
        # Delete and verify everything is gone
        resource_handler.delete_resource_folder(tool_uuid)
        assert not os.path.exists(tool_folder)

# Made with Bob
