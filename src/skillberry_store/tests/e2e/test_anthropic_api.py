"""
E2E tests for Anthropic skill import/export API endpoints.
Tests the full lifecycle of importing and exporting Anthropic skills.
"""

import io
import zipfile
import pytest
import httpx

from skillberry_store.tests.utils import clean_test_tmp_dir

BASE_URL = "http://localhost:8000"


def create_test_zip():
    """Create a test ZIP file with sample Anthropic skill structure."""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add SKILL.md
        skill_md = """---
name: test_anthropic_skill
description: A test skill for Anthropic import/export
---

# Test Anthropic Skill

This is a sample skill for testing.
"""
        zip_file.writestr('test_anthropic_skill/SKILL.md', skill_md)
        
        # Add Python file
        python_code = """# Sample Python file

def add_numbers(a: int, b: int) -> int:
    '''Add two numbers together.
    
    Args:
        a (int): First number
        b (int): Second number
        
    Returns:
        int: Sum of the two numbers
    '''
    return a + b


def multiply_numbers(x: float, y: float) -> float:
    '''Multiply two numbers.
    
    Args:
        x (float): First number
        y (float): Second number
        
    Returns:
        float: Product of the two numbers
    '''
    return x * y
"""
        zip_file.writestr('test_anthropic_skill/scripts/utils.py', python_code)
        
        # Add Bash file
        bash_code = """#!/bin/bash
# Sample Bash file

# Print a greeting message
greet_user() {
    echo "Hello, $1!"
}

# Calculate sum of arguments
sum_args() {
    local sum=0
    for arg in "$@"; do
        sum=$((sum + arg))
    done
    echo $sum
}
"""
        zip_file.writestr('test_anthropic_skill/scripts/scripts.sh', bash_code)
        
        # Add README
        readme = """# Test Anthropic Skill

This is a sample skill for testing purposes.

## Overview

This skill demonstrates the import/export functionality.
"""
        zip_file.writestr('test_anthropic_skill/README.md', readme)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


@pytest.mark.asyncio
async def test_import_anthropic_skill_from_zip(run_sbs):
    """Test importing an Anthropic skill from a ZIP file."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create test ZIP
        zip_content = create_test_zip()
        
        # Prepare form data
        files = {
            'zip_file': ('test_skill.zip', zip_content, 'application/zip')
        }
        data = {
            'source_type': 'zip',
            'snippet_mode': 'file'
        }
        
        # Import the skill
        response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Import failed: {response.text}"
        result = response.json()
        
        assert result['success'] is True
        # Importer slugifies the upstream SKILL.md `name` field so the
        # resulting skill is addressable under the Anthropic Agent Skills
        # name rules (lowercase, hyphens-only).
        assert result['skill_name'] == 'test-anthropic-skill'
        assert result['tools_created'] >= 2  # add_numbers, multiply_numbers, greet_user, sum_args
        assert result['snippets_created'] >= 1  # SKILL.md, README.md
        
        # Verify the skill was created
        skill_response = await client.get(f"{BASE_URL}/skills/{result['skill_name']}")
        assert skill_response.status_code == 200
        skill = skill_response.json()
        assert skill['name'] == result['skill_name']
        assert 'anthropic' in skill.get('tags', [])


@pytest.mark.asyncio
async def test_import_anthropic_skill_paragraph_mode(run_sbs):
    """Test importing an Anthropic skill with paragraph mode for snippets."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create test ZIP
        zip_content = create_test_zip()
        
        # Prepare form data
        files = {
            'zip_file': ('test_skill_para.zip', zip_content, 'application/zip')
        }
        data = {
            'source_type': 'zip',
            'snippet_mode': 'paragraph'
        }
        
        # Import the skill
        response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Import failed: {response.text}"
        result = response.json()
        
        assert result['success'] is True
        # In paragraph mode, text files are split into multiple snippets
        assert result['snippets_created'] >= 2  # Multiple paragraphs from SKILL.md and README.md


@pytest.mark.asyncio
async def test_export_anthropic_skill(run_sbs):
    """Test exporting a skill to Anthropic format."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First, import a skill
        zip_content = create_test_zip()
        files = {
            'zip_file': ('test_export.zip', zip_content, 'application/zip')
        }
        data = {
            'source_type': 'zip',
            'snippet_mode': 'file'
        }
        
        import_response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            files=files,
            data=data
        )
        assert import_response.status_code == 200
        import_result = import_response.json()
        skill_name = import_result['skill_name']
        
        # Now export the skill
        export_response = await client.get(
            f"{BASE_URL}/skills/{skill_name}/export-anthropic"
        )
        
        assert export_response.status_code == 200
        assert export_response.headers['content-type'] == 'application/zip'
        assert 'attachment' in export_response.headers.get('content-disposition', '')
        
        # Verify the ZIP content
        zip_buffer = io.BytesIO(export_response.content)
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            file_list = zip_file.namelist()
            
            # Check for SKILL.md (case-insensitive, anywhere in path)
            skill_md_files = [f for f in file_list if 'skill.md' in f.lower()]
            assert len(skill_md_files) > 0, f"SKILL.md not found in exported ZIP. Files: {file_list}"
            
            # Check for Python files
            py_files = [f for f in file_list if f.endswith('.py')]
            assert len(py_files) > 0, "No Python files found in exported ZIP"
            
            # Check for Bash files
            sh_files = [f for f in file_list if f.endswith('.sh')]
            assert len(sh_files) > 0, "No Bash files found in exported ZIP"


@pytest.mark.asyncio
async def test_import_export_roundtrip(run_sbs):
    """Test that import -> export -> import produces consistent results."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Import original skill
        zip_content = create_test_zip()
        files = {
            'zip_file': ('roundtrip_test.zip', zip_content, 'application/zip')
        }
        data = {
            'source_type': 'zip',
            'snippet_mode': 'file'
        }
        
        import1_response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            files=files,
            data=data
        )
        assert import1_response.status_code == 200
        import1_result = import1_response.json()
        skill_name_1 = import1_result['skill_name']
        tools_count_1 = import1_result['tools_created']
        snippets_count_1 = import1_result['snippets_created']
        
        # Step 2: Export the skill
        export_response = await client.get(
            f"{BASE_URL}/skills/{skill_name_1}/export-anthropic"
        )
        assert export_response.status_code == 200
        exported_zip = export_response.content
        
        # Step 3: Delete the original skill
        delete_response = await client.delete(f"{BASE_URL}/skills/{skill_name_1}")
        assert delete_response.status_code == 200
        
        # Step 4: Re-import from exported ZIP
        files2 = {
            'zip_file': ('roundtrip_reimport.zip', exported_zip, 'application/zip')
        }
        
        import2_response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            files=files2,
            data=data
        )
        assert import2_response.status_code == 200
        import2_result = import2_response.json()
        
        # Verify counts are similar (may not be exact due to SKILL.md handling)
        assert import2_result['tools_created'] == tools_count_1
        # Snippets might differ slightly due to SKILL.md frontmatter stripping
        assert import2_result['snippets_created'] >= snippets_count_1 - 1


@pytest.mark.asyncio
async def test_import_invalid_source_type(run_sbs):
    """Test that invalid source type returns error."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        data = {
            'source_type': 'invalid',
            'snippet_mode': 'file'
        }
        
        response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            data=data
        )
        
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_import_missing_zip_file(run_sbs):
    """Test that missing ZIP file returns error."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        data = {
            'source_type': 'zip',
            'snippet_mode': 'file'
        }
        
        response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            data=data
        )
        
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_export_nonexistent_skill(run_sbs):
    """Test that exporting a non-existent skill returns 404 or 500."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/skills/nonexistent_skill_12345/export-anthropic"
        )
        
        # File not found can trigger either 404 or 500 depending on where it fails
        assert response.status_code in [404, 500], f"Expected 404 or 500, got {response.status_code}"


@pytest.mark.asyncio
async def test_import_preserves_file_tags(run_sbs):
    """Test that file: tags are preserved during import."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Import a skill
        zip_content = create_test_zip()
        files = {
            'zip_file': ('test_tags.zip', zip_content, 'application/zip')
        }
        data = {
            'source_type': 'zip',
            'snippet_mode': 'file'
        }
        
        import_response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            files=files,
            data=data
        )
        assert import_response.status_code == 200
        import_result = import_response.json()
        skill_name = import_result['skill_name']
        
        # Get the skill details
        skill_response = await client.get(f"{BASE_URL}/skills/{skill_name}")
        assert skill_response.status_code == 200
        skill = skill_response.json()
        
        # Check that tools have file: tags
        if skill.get('tools'):
            for tool in skill['tools']:
                tags = tool.get('tags', [])
                file_tags = [t for t in tags if t.startswith('file:')]
                assert len(file_tags) > 0, f"Tool {tool['name']} missing file: tag"
        
        # Check that snippets have file: tags
        if skill.get('snippets'):
            for snippet in skill['snippets']:
                tags = snippet.get('tags', [])
                file_tags = [t for t in tags if t.startswith('file:')]
                assert len(file_tags) > 0, f"Snippet {snippet['name']} missing file: tag"


@pytest.mark.asyncio
async def test_import_treat_all_as_documents(run_sbs):
    """Test importing with treat_all_as_documents flag - all files become snippets."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create test ZIP
        zip_content = create_test_zip()
        
        # Prepare form data with treat_all_as_documents=true
        files = {
            'zip_file': ('test_all_docs.zip', zip_content, 'application/zip')
        }
        data = {
            'source_type': 'zip',
            'snippet_mode': 'file',
            'treat_all_as_documents': 'true'
        }
        
        # Import the skill
        response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Import failed: {response.text}"
        result = response.json()
        
        assert result['success'] is True
        # When treating all as documents, no tools should be created
        assert result['tools_created'] == 0, "Expected 0 tools when treating all as documents"
        # All files should be imported as snippets (including code files)
        assert result['snippets_created'] >= 4, "Expected at least 4 snippets (SKILL.md, README.md, utils.py, scripts.sh)"
        
        # Verify the skill was created
        skill_response = await client.get(f"{BASE_URL}/skills/{result['skill_name']}")
        assert skill_response.status_code == 200
        skill = skill_response.json()
        
        # Verify no tools exist
        assert len(skill.get('tools', [])) == 0, "No tools should exist when treating all as documents"
        
        # Verify snippets include code files
        snippets = skill.get('snippets', [])
        assert len(snippets) >= 4, "Expected at least 4 snippets"
        
        # Check that code files are present as snippets
        snippet_names = [s['name'] for s in snippets]
        # At least one Python file should be a snippet
        py_snippets = [name for name in snippet_names if 'utils' in name.lower() or name.endswith('.py')]
        assert len(py_snippets) > 0, "Expected Python file to be imported as snippet"


@pytest.mark.asyncio
async def test_import_treat_all_as_documents_paragraph_mode(run_sbs):
    """Test importing with treat_all_as_documents and paragraph mode."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create test ZIP
        zip_content = create_test_zip()
        
        # Prepare form data with treat_all_as_documents=true and paragraph mode
        files = {
            'zip_file': ('test_all_docs_para.zip', zip_content, 'application/zip')
        }
        data = {
            'source_type': 'zip',
            'snippet_mode': 'paragraph',
            'treat_all_as_documents': 'true'
        }
        
        # Import the skill
        response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Import failed: {response.text}"
        result = response.json()
        
        assert result['success'] is True
        # When treating all as documents, no tools should be created
        assert result['tools_created'] == 0, "Expected 0 tools when treating all as documents"
        # In paragraph mode, files should be split into multiple snippets
        assert result['snippets_created'] > 4, "Expected more snippets in paragraph mode"


@pytest.mark.asyncio
async def test_import_export_roundtrip_with_treat_all_as_documents(run_sbs):
    """Test that import -> export -> import with treat_all_as_documents produces consistent results."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Import original skill with treat_all_as_documents
        zip_content = create_test_zip()
        files = {
            'zip_file': ('roundtrip_docs.zip', zip_content, 'application/zip')
        }
        data = {
            'source_type': 'zip',
            'snippet_mode': 'file',
            'treat_all_as_documents': 'true'
        }
        
        import1_response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            files=files,
            data=data
        )
        assert import1_response.status_code == 200
        import1_result = import1_response.json()
        skill_name_1 = import1_result['skill_name']
        tools_count_1 = import1_result['tools_created']
        snippets_count_1 = import1_result['snippets_created']
        
        # Verify no tools were created
        assert tools_count_1 == 0, "Expected 0 tools in first import"
        
        # Step 2: Export the skill
        export_response = await client.get(
            f"{BASE_URL}/skills/{skill_name_1}/export-anthropic"
        )
        assert export_response.status_code == 200
        exported_zip = export_response.content
        
        # Step 3: Delete the original skill
        delete_response = await client.delete(f"{BASE_URL}/skills/{skill_name_1}")
        assert delete_response.status_code == 200
        
        # Step 4: Re-import from exported ZIP with treat_all_as_documents
        files2 = {
            'zip_file': ('roundtrip_docs_reimport.zip', exported_zip, 'application/zip')
        }
        
        import2_response = await client.post(
            f"{BASE_URL}/skills/import-anthropic",
            files=files2,
            data=data
        )
        assert import2_response.status_code == 200
        import2_result = import2_response.json()
        
        # Verify counts match
        assert import2_result['tools_created'] == tools_count_1, "Tool count should match (0)"
        # Snippets should be similar (may differ slightly due to SKILL.md handling)
        assert import2_result['snippets_created'] >= snippets_count_1 - 1, "Snippet count should be similar"