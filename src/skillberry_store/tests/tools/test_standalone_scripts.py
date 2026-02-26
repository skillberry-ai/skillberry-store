# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""Tests for standalone script parsing (scripts without function definitions)."""

import pytest
from skillberry_store.tools.anthropic.code_parser import parse_code_file


class TestStandaloneScripts:
    """Test parsing of standalone scripts without function definitions."""
    
    def test_parse_python_standalone_script(self):
        """Test parsing a Python script without function definitions."""
        content = '''"""
Extract form structure from a non-fillable PDF.

This script analyzes the PDF to find text labels and boundaries.
"""

import json
import sys

if __name__ == "__main__":
    pdf_path = sys.argv[1]
    output_path = sys.argv[2]
    
    # Process the PDF
    result = {"status": "success"}
    
    with open(output_path, 'w') as f:
        json.dump(result, f)
'''
        
        tools = parse_code_file(content, 'extract_form_structure.py', 'scripts/extract_form_structure.py', 'pdf')
        
        assert len(tools) == 1
        tool = tools[0]
        
        assert tool.name == 'extract_form_structure'
        assert 'Extract form structure' in tool.description
        assert tool.module_content == content
        assert tool.programming_language == 'python'
        assert 'script' in tool.tags
        assert 'file:scripts/extract_form_structure.py' in tool.tags
        assert tool.params is None
        assert tool.returns is None
    
    def test_parse_python_script_with_comment(self):
        """Test parsing a Python script with only a comment."""
        content = '''# Convert PDF to images
import sys
from pdf2image import convert_from_path

pdf_path = sys.argv[1]
images = convert_from_path(pdf_path)
'''
        
        tools = parse_code_file(content, 'convert_pdf.py', 'scripts/convert_pdf.py', 'pdf')
        
        assert len(tools) == 1
        tool = tools[0]
        
        assert tool.name == 'convert_pdf'
        assert tool.description == 'Convert PDF to images'
        assert tool.programming_language == 'python'
    
    def test_parse_bash_standalone_script(self):
        """Test parsing a Bash script without function definitions."""
        content = '''#!/bin/bash
# Process PDF files in a directory

for file in *.pdf; do
    echo "Processing $file"
    python extract.py "$file"
done
'''
        
        tools = parse_code_file(content, 'process_pdfs.sh', 'scripts/process_pdfs.sh', 'pdf')
        
        assert len(tools) == 1
        tool = tools[0]
        
        assert tool.name == 'process_pdfs'
        assert tool.description == 'Process PDF files in a directory'
        assert tool.module_content == content
        assert tool.programming_language == 'bash'
        assert 'script' in tool.tags
    
    def test_parse_python_with_functions_still_works(self):
        """Test that scripts with functions are still parsed correctly."""
        content = '''def add(a, b):
    """Add two numbers."""
    return a + b

def subtract(a, b):
    """Subtract b from a."""
    return a - b
'''
        
        tools = parse_code_file(content, 'math.py', 'utils/math.py', 'test')
        
        # Should extract both functions, not treat as standalone script
        assert len(tools) == 2
        assert tools[0].name == 'add'
        assert tools[1].name == 'subtract'
        assert 'script' not in tools[0].tags
        assert 'script' not in tools[1].tags