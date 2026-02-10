# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""Parser for text files (markdown, txt, etc.) to convert them into snippets."""

import re
from typing import List, Dict, Any


class ParsedSnippet:
    """Represents a parsed snippet from a text file."""
    
    def __init__(self, name: str, description: str, content: str, tags: List[str], version: str = "1.0.0"):
        self.name = name
        self.description = description
        self.content = content
        self.tags = tags
        self.version = version
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'content': self.content,
            'tags': self.tags,
            'version': self.version,
        }


def split_into_paragraphs(content: str) -> List[str]:
    """Split text content into paragraphs.
    
    A paragraph is defined as text separated by double newlines.
    
    Args:
        content: The text content to split
        
    Returns:
        List of paragraph strings
    """
    # Split by double newlines (or more) and filter out empty strings
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content) if p.strip()]
    return paragraphs


def generate_description(content: str) -> str:
    """Generate a description from content (first 100 chars or first line).
    
    Args:
        content: The content to generate description from
        
    Returns:
        Generated description string
    """
    first_line = content.split('\n')[0].strip()
    if first_line and len(first_line) <= 100:
        return first_line
    
    truncated = content[:100].strip()
    return truncated + ('...' if len(content) > 100 else '')


def extract_tags(file_path: str, file_name: str) -> List[str]:
    """Extract tags from filename and path.
    
    Args:
        file_path: The full file path
        file_name: The file name
        
    Returns:
        List of extracted tags
    """
    tags = []
    
    # Add file extension as tag
    parts = file_name.split('.')
    if len(parts) > 1:
        tags.append(parts[-1])
    
    # Add directory names as tags (excluding common ones)
    excluded_dirs = {'.', '..', 'src', 'docs'}
    path_parts = [p for p in file_path.split('/') if p and p not in excluded_dirs]
    tags.extend(path_parts)
    
    # Add 'anthropic' tag to identify source
    tags.append('anthropic')
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)
    
    return unique_tags


def strip_frontmatter(content: str) -> str:
    """Strip YAML frontmatter from content.
    
    Args:
        content: The content that may contain frontmatter
        
    Returns:
        Content with frontmatter removed
    """
    lines = content.split('\n')
    if lines and lines[0].strip() == '---':
        # Find the closing ---
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                # Return content after the closing ---
                return '\n'.join(lines[i + 1:]).strip()
    return content


def parse_text_file(
    content: str,
    file_name: str,
    file_path: str,
    skill_name: str,
    split_by_paragraph: bool = True
) -> List[ParsedSnippet]:
    """Parse a text file into snippets (one per paragraph or complete file).
    
    Args:
        content: The file content
        file_name: The file name
        file_path: The file path
        skill_name: The skill name
        split_by_paragraph: Whether to split by paragraph or keep as single snippet
        
    Returns:
        List of ParsedSnippet objects
    """
    tags = extract_tags(file_path, file_name)
    base_file_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
    
    # Add file path tag in format file:complete_path_filename as the first tag
    file_path_tag = f"file:{file_path}"
    
    # Strip frontmatter from SKILL.md files
    processed_content = content
    if file_name.upper() == 'SKILL.MD':
        processed_content = strip_frontmatter(content)
        # If content is empty after stripping frontmatter, skip creating snippet
        if not processed_content:
            return []
    
    if not split_by_paragraph:
        # Import as a single snippet (complete file)
        return [ParsedSnippet(
            name=f"{skill_name}_{base_file_name}",
            description=generate_description(processed_content),
            content=processed_content,
            tags=[file_path_tag] + tags,
            version='1.0.0'
        )]
    
    # Split by paragraphs
    paragraphs = split_into_paragraphs(processed_content)
    
    snippets = []
    for index, paragraph in enumerate(paragraphs):
        snippet_name = (
            f"{skill_name}_{base_file_name}"
            if len(paragraphs) == 1
            else f"{skill_name}_{base_file_name}_{index + 1}"
        )
        
        snippets.append(ParsedSnippet(
            name=snippet_name,
            description=generate_description(paragraph),
            content=paragraph,
            tags=[file_path_tag] + tags,  # File path tag first
            version='1.0.0'
        ))
    
    return snippets


def is_text_file(file_name: str) -> bool:
    """Check if a file should be processed as a text file.
    
    Args:
        file_name: The file name to check
        
    Returns:
        True if it's a text file, False otherwise
    """
    text_extensions = [
        '.md', '.txt', '.rst', '.adoc', '.asciidoc',
        '.markdown', '.mdown', '.mkd', '.mkdn',
        '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',
        '.xml', '.html', '.htm', '.css',
    ]
    
    file_name_lower = file_name.lower()
    return any(file_name_lower.endswith(ext) for ext in text_extensions)


def parse_text_files(
    files: List[Dict[str, str]],
    skill_name: str,
    split_by_paragraph: bool = True
) -> List[ParsedSnippet]:
    """Parse multiple text files from a skill.
    
    Args:
        files: List of file dictionaries with 'name', 'path', and 'content' keys
        skill_name: The skill name
        split_by_paragraph: Whether to split by paragraph or keep as single snippets
        
    Returns:
        List of ParsedSnippet objects
    """
    all_snippets = []
    
    for file in files:
        # In paragraph mode, only process text files
        # In file mode (split_by_paragraph=False), process all files
        should_process = not split_by_paragraph or is_text_file(file['name'])
        
        if should_process:
            try:
                snippets = parse_text_file(
                    file['content'],
                    file['name'],
                    file['path'],
                    skill_name,
                    split_by_paragraph
                )
                all_snippets.extend(snippets)
            except Exception as e:
                print(f"Failed to parse file {file['name']}: {e}")
    
    return all_snippets