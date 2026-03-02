"""
Unit tests for Anthropic text and code parsers.
"""

import pytest
from skillberry_store.tools.anthropic.text_parser import (
    parse_text_file,
    parse_text_files,
    is_text_file,
    split_into_paragraphs,
    generate_description,
    extract_tags,
    strip_frontmatter,
)
from skillberry_store.tools.anthropic.code_parser import (
    parse_code_file,
    parse_code_files,
    is_code_file,
    extract_python_functions,
    extract_bash_functions,
    parse_python_function,
    parse_bash_function,
)


class TestTextParser:
    """Tests for text parser functionality."""
    
    def test_split_into_paragraphs(self):
        """Test splitting text into paragraphs."""
        content = "First paragraph.\n\nSecond paragraph.\n\n\nThird paragraph."
        paragraphs = split_into_paragraphs(content)
        assert len(paragraphs) == 3
        assert paragraphs[0] == "First paragraph."
        assert paragraphs[1] == "Second paragraph."
        assert paragraphs[2] == "Third paragraph."
    
    def test_split_into_paragraphs_single(self):
        """Test splitting text with single paragraph."""
        content = "Only one paragraph here."
        paragraphs = split_into_paragraphs(content)
        assert len(paragraphs) == 1
        assert paragraphs[0] == "Only one paragraph here."
    
    def test_generate_description_short(self):
        """Test generating description from short content."""
        content = "This is a short line."
        description = generate_description(content)
        assert description == "This is a short line."
    
    def test_generate_description_long(self):
        """Test generating description from long content."""
        content = "A" * 150
        description = generate_description(content)
        assert len(description) <= 103  # 100 chars + "..."
        assert description.endswith("...")
    
    def test_extract_tags(self):
        """Test extracting tags from file path."""
        tags = extract_tags("skills/pptx/utils.py", "utils.py", "test_skill")
        assert "py" in tags
        assert "anthropic" in tags
        assert "pptx" in tags
        assert "utils.py" in tags
    
    def test_strip_frontmatter(self):
        """Test stripping YAML frontmatter."""
        content = """---
name: test
description: A test
---

# Content

This is the actual content."""
        stripped = strip_frontmatter(content)
        assert not stripped.startswith("---")
        assert "# Content" in stripped
        assert "name: test" not in stripped
    
    def test_strip_frontmatter_no_frontmatter(self):
        """Test stripping when there's no frontmatter."""
        content = "# Just content\n\nNo frontmatter here."
        stripped = strip_frontmatter(content)
        assert stripped == content
    
    def test_is_text_file(self):
        """Test identifying text files."""
        assert is_text_file("README.md") is True
        assert is_text_file("config.yaml") is True
        assert is_text_file("data.json") is True
        assert is_text_file("script.py") is False
        assert is_text_file("image.png") is False
    
    def test_parse_text_file_single_snippet(self):
        """Test parsing text file as single snippet."""
        content = "This is a test file."
        snippets = parse_text_file(
            content,
            "test.md",
            "docs/test.md",
            "test_skill",
            split_by_paragraph=False
        )
        assert len(snippets) == 1
        assert snippets[0].name == "test"
        assert snippets[0].content == content
        assert "file:docs/test.md" in snippets[0].tags
        assert "skill:test_skill" in snippets[0].tags
    
    def test_parse_text_file_multiple_paragraphs(self):
        """Test parsing text file into multiple snippets."""
        content = "First paragraph.\n\nSecond paragraph."
        snippets = parse_text_file(
            content,
            "test.md",
            "docs/test.md",
            "test_skill",
            split_by_paragraph=True
        )
        assert len(snippets) == 2
        assert snippets[0].content == "First paragraph."
        assert snippets[1].content == "Second paragraph."
    
    def test_parse_skill_md_strips_frontmatter(self):
        """Test that SKILL.md frontmatter is stripped."""
        content = """---
name: test
---

# Content"""
        snippets = parse_text_file(
            content,
            "SKILL.md",
            "SKILL.md",
            "test_skill",
            split_by_paragraph=False
        )
        assert len(snippets) == 1
        assert "---" not in snippets[0].content
        assert "# Content" in snippets[0].content


class TestCodeParser:
    """Tests for code parser functionality."""
    
    def test_is_code_file(self):
        """Test identifying code files."""
        assert is_code_file("script.py") is True
        assert is_code_file("script.sh") is True
        assert is_code_file("script.bash") is True
        assert is_code_file("README.md") is False
        assert is_code_file("config.json") is False
    
    def test_extract_python_functions(self):
        """Test extracting Python functions."""
        code = """
def function1(a, b):
    return a + b

def function2(x):
    '''Docstring'''
    return x * 2
"""
        functions = extract_python_functions(code)
        assert len(functions) == 2
        assert functions[0]['name'] == 'function1'
        assert functions[1]['name'] == 'function2'
        assert 'Docstring' in functions[1]['code']
    
    def test_extract_bash_functions(self):
        """Test extracting Bash functions."""
        code = """
# Comment
greet() {
    echo "Hello $1"
}

function calculate() {
    echo $((1 + 2))
}
"""
        functions = extract_bash_functions(code)
        assert len(functions) == 2
        assert functions[0]['name'] == 'greet'
        assert functions[1]['name'] == 'calculate'
    
    def test_parse_python_function_with_docstring(self):
        """Test parsing Python function with docstring."""
        code = """
def add(a: int, b: int) -> int:
    '''Add two numbers.
    
    Args:
        a (int): First number
        b (int): Second number
        
    Returns:
        int: Sum
    '''
    return a + b
"""
        description, params, returns = parse_python_function(code, 'add')
        assert 'Add two numbers' in description
        assert params is not None
        assert 'a' in params['properties']
        assert 'b' in params['properties']
        assert params['properties']['a']['type'] == 'integer'
        assert returns is not None
        assert returns['type'] == 'integer'
    
    def test_parse_python_function_no_docstring(self):
        """Test parsing Python function without docstring."""
        code = """
def multiply(x, y):
    return x * y
"""
        description, params, returns = parse_python_function(code, 'multiply')
        assert 'multiply' in description
        assert params is not None
        assert 'x' in params['properties']
        assert 'y' in params['properties']
    
    def test_parse_bash_function(self):
        """Test parsing Bash function."""
        code = """
# Print greeting
greet_user() {
    echo "Hello, $1!"
}
"""
        description, params, returns = parse_bash_function(code, 'greet_user')
        assert 'Print greeting' in description
        assert params is not None
        assert 'arg1' in params['properties']
        assert returns is not None
        assert returns['type'] == 'string'
    
    def test_parse_code_file_python(self):
        """Test parsing Python code file."""
        code = """
def add(a, b):
    '''Add two numbers'''
    return a + b

def subtract(a, b):
    '''Subtract two numbers'''
    return a - b
"""
        tools = parse_code_file(code, "utils.py", "scripts/utils.py", "test_skill")
        assert len(tools) == 2
        assert tools[0].name == "add"
        assert tools[1].name == "subtract"
        assert tools[0].programming_language == "python"
        assert "file:scripts/utils.py" in tools[0].tags
        assert "skill:test_skill" in tools[0].tags

    def test_parse_code_file_python_multi_function_module_content_is_full_file(self):
        """Test that each tool's module_content is the full file when multiple functions exist."""
        code = """import os

GLOBAL_VAR = 42

def add(a, b):
    '''Add two numbers'''
    return a + b

def subtract(a, b):
    '''Subtract two numbers'''
    return a - b
"""
        tools = parse_code_file(code, "utils.py", "scripts/utils.py", "test_skill")
        assert len(tools) == 2
        # Every tool must carry the full file so imports and globals are available
        for tool in tools:
            assert tool.module_content == code
            assert "import os" in tool.module_content
            assert "GLOBAL_VAR" in tool.module_content

    def test_parse_code_file_python_single_function_module_content_is_full_file(self):
        """Test that module_content is the full file when there is exactly one function."""
        code = """import math

def compute(x):
    '''Compute something'''
    return math.sqrt(x)
"""
        tools = parse_code_file(code, "compute.py", "scripts/compute.py", "test_skill")
        assert len(tools) == 1
        assert tools[0].name == "compute"
        assert tools[0].module_content == code
        assert "import math" in tools[0].module_content

    def test_parse_code_file_python_no_functions_module_content_is_full_file(self):
        """Test that module_content is the full file when there are no functions."""
        code = """# A standalone script
import sys

print("Hello from script")
sys.exit(0)
"""
        tools = parse_code_file(code, "run.py", "scripts/run.py", "test_skill")
        assert len(tools) == 1
        assert tools[0].module_content == code
        assert "import sys" in tools[0].module_content

    def test_parse_code_file_bash(self):
        """Test parsing Bash code file."""
        code = """
greet() {
    echo "Hello"
}

calculate() {
    echo $((1 + 2))
}
"""
        tools = parse_code_file(code, "script.sh", "scripts/script.sh", "test_skill")
        assert len(tools) == 2
        assert tools[0].name == "greet"
        assert tools[1].name == "calculate"
        assert tools[0].programming_language == "bash"

    def test_parse_code_file_bash_multi_function_module_content_is_full_file(self):
        """Test that each bash tool's module_content is the full file when multiple functions exist."""
        code = """#!/bin/bash
export ENV_VAR="value"

greet() {
    echo "Hello $1"
}

calculate() {
    echo $((1 + 2))
}
"""
        tools = parse_code_file(code, "script.sh", "scripts/script.sh", "test_skill")
        assert len(tools) == 2
        for tool in tools:
            assert tool.module_content == code
            assert "#!/bin/bash" in tool.module_content
            assert "ENV_VAR" in tool.module_content
    
    def test_parse_code_files_mixed(self):
        """Test parsing multiple code files."""
        files = [
            {
                'name': 'utils.py',
                'path': 'scripts/utils.py',
                'content': 'def add(a, b):\n    return a + b'
            },
            {
                'name': 'script.sh',
                'path': 'scripts/script.sh',
                'content': 'greet() {\n    echo "Hello"\n}'
            },
            {
                'name': 'README.md',
                'path': 'README.md',
                'content': '# README'
            }
        ]
        result = parse_code_files(files, "test_skill")
        assert len(result['tools']) == 2
        assert 'README.md' not in result['ignoredFiles']
    
    def test_parse_python_function_with_defaults(self):
        """Test parsing Python function with default parameters."""
        code = """
def greet(name: str, greeting: str = "Hello") -> str:
    '''Greet someone.
    
    Args:
        name: Person's name
        greeting: Greeting message
    '''
    return f"{greeting}, {name}!"
"""
        description, params, returns = parse_python_function(code, 'greet')
        assert params is not None
        assert 'name' in params['required']
        assert 'greeting' not in params['required']  # Has default value
    
    def test_parse_python_function_type_annotations(self):
        """Test that type annotations are correctly parsed."""
        code = """
def process(count: int, items: list, data: dict) -> bool:
    return True
"""
        description, params, returns = parse_python_function(code, 'process')
        assert params['properties']['count']['type'] == 'integer'
        assert params['properties']['items']['type'] == 'array'
        assert params['properties']['data']['type'] == 'object'
        assert returns['type'] == 'boolean'
    
    def test_extract_python_functions_with_nested_function(self):
        """Test that nested/internal functions are not extracted separately."""
        code = """
def cancel_reservation_policy(reservation_id: str):
    '''Cancel reservation with policy check.
    
    Args:
        reservation_id (str): The reservation ID
    '''
    
    def is_within_24_hours(created_at_str, reference_str):
        '''Internal helper function.'''
        # Implementation here
        return True
    
    # Use the internal function
    if is_within_24_hours("2024-05-12", "2024-05-13"):
        return "Cancelled"
    return "Not cancelled"

def another_top_level_function():
    '''Another top-level function.'''
    return "result"
"""
        functions = extract_python_functions(code)
        # Should only extract top-level functions, not nested ones
        assert len(functions) == 2
        assert functions[0]['name'] == 'cancel_reservation_policy'
        assert functions[1]['name'] == 'another_top_level_function'
        # Verify the nested function is included in the parent's code
        assert 'def is_within_24_hours' in functions[0]['code']
        assert 'Internal helper function' in functions[0]['code']


class TestIntegration:
    """Integration tests for parsers."""
    
    def test_parse_complete_skill(self):
        """Test parsing a complete skill with mixed content."""
        files = [
            {
                'name': 'SKILL.md',
                'path': 'SKILL.md',
                'content': '---\nname: test\n---\n\n# Test Skill\n\nDescription here.'
            },
            {
                'name': 'utils.py',
                'path': 'scripts/utils.py',
                'content': 'def add(a, b):\n    return a + b'
            },
            {
                'name': 'README.md',
                'path': 'README.md',
                'content': '# README\n\nProject documentation.'
            }
        ]
        
        # Parse text files
        snippets = parse_text_files(files, "test_skill", split_by_paragraph=False)
        assert len(snippets) >= 2  # SKILL.md and README.md
        
        # Parse code files
        result = parse_code_files(files, "test_skill")
        assert len(result['tools']) == 1  # add function
        
        # Verify tags
        for snippet in snippets:
            assert any(tag.startswith('file:') for tag in snippet.tags)
            assert any(tag.startswith('skill:') for tag in snippet.tags)
        
        for tool in result['tools']:
            assert any(tag.startswith('file:') for tag in tool.tags)
            assert any(tag.startswith('skill:') for tag in tool.tags)