# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""Importer for converting Anthropic skills to Skillberry format."""

import re
import io
import os
import zipfile
import requests
from typing import Dict, List, Any, Optional, Tuple


def extract_skill_name(url: str, filename: str) -> str:
    """Extract skill name from GitHub URL or zip filename.
    
    Args:
        url: GitHub URL
        filename: Filename
        
    Returns:
        Extracted skill name
    """
    if url:
        # Extract from URL like: https://github.com/anthropics/skills/tree/main/skills/pptx
        match = re.search(r'/skills/([^/]+)/?$', url)
        if match:
            return match.group(1)
        # Fallback: use last part of URL
        parts = [p for p in url.split('/') if p]
        return parts[-1] if parts else 'anthropic_skill'
    
    # Extract from filename
    return re.sub(r'\.(zip|tar\.gz|tgz)$', '', filename, flags=re.IGNORECASE).replace('-', '_').replace(' ', '_')


def parse_skill_metadata(files: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Parse SKILL.md file to extract name and description from header.
    
    Args:
        files: List of file dictionaries with 'name', 'path', and 'content' keys
        
    Returns:
        Dictionary with 'name' and 'description' or None
    """
    skill_file = next((f for f in files if f['name'].upper() == 'SKILL.MD'), None)
    if not skill_file:
        return None
    
    try:
        content = skill_file['content']
        lines = content.split('\n')
        name = ''
        description = ''
        in_header = False
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check for YAML front matter
            if i == 0 and line_stripped == '---':
                in_header = True
                continue
            
            if in_header:
                if line_stripped == '---':
                    # End of header
                    break
                
                # Parse name field
                name_match = re.match(r'^name:\s*(.+)$', line_stripped, re.IGNORECASE)
                if name_match:
                    name = name_match.group(1).strip().strip('"\'')
                
                # Parse description field
                desc_match = re.match(r'^description:\s*(.+)$', line_stripped, re.IGNORECASE)
                if desc_match:
                    description = desc_match.group(1).strip().strip('"\'')
        
        if name or description:
            return {'name': name, 'description': description}
    except Exception as e:
        print(f"Failed to parse SKILL.md metadata: {e}")
    
    return None


def fetch_from_github(url: str) -> List[Dict[str, str]]:
    """Fetch files from GitHub repository.
    
    Args:
        url: GitHub URL
        
    Returns:
        List of file dictionaries with 'name', 'path', and 'content' keys
        
    Raises:
        Exception: If fetching fails
    """
    # Convert GitHub URL to API URL
    # From: https://github.com/anthropics/skills/tree/main/skills/pptx
    # To: https://api.github.com/repos/anthropics/skills/contents/skills/pptx
    api_url = url.replace('github.com', 'api.github.com/repos')
    api_url = re.sub(r'/tree/(main|master)/', r'/contents/', api_url)
    
    print(f"Fetching from GitHub API URL: {api_url}")
    
    files: List[Dict[str, str]] = []
    
    def fetch_directory(dir_url: str, base_path: str = '') -> None:
        """Recursively fetch directory contents."""
        try:
            response = requests.get(dir_url, timeout=30)
            if not response.ok:
                raise Exception(f"GitHub API returned {response.status_code}: {response.text or response.reason}")
            
            items = response.json()
            
            for item in items:
                if item['type'] == 'file':
                    # Fetch file content
                    try:
                        content_response = requests.get(item['download_url'], timeout=30)
                        if content_response.ok:
                            relative_path = f"{base_path}/{item['name']}" if base_path else item['name']
                            files.append({
                                'name': item['name'],
                                'path': relative_path,
                                'content': content_response.text,
                            })
                        else:
                            print(f"Failed to fetch file {item['name']}: {content_response.reason}")
                    except Exception as e:
                        print(f"Error fetching file {item['name']}: {e}")
                elif item['type'] == 'dir':
                    # Recursively fetch subdirectory
                    relative_path = f"{base_path}/{item['name']}" if base_path else item['name']
                    fetch_directory(item['url'], relative_path)
        except Exception as e:
            raise Exception(f"Failed to fetch directory {dir_url}: {str(e)}")
    
    fetch_directory(api_url)
    return files


def extract_from_zip(zip_content: bytes) -> List[Dict[str, str]]:
    """Extract files from ZIP.
    
    Args:
        zip_content: ZIP file content as bytes
        
    Returns:
        List of file dictionaries with 'name', 'path', and 'content' keys
    """
    files: List[Dict[str, str]] = []
    
    with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as zip_file:
        for zip_info in zip_file.filelist:
            if not zip_info.is_dir() and zip_info.filename:
                try:
                    content = zip_file.read(zip_info.filename).decode('utf-8')
                    name = zip_info.filename.split('/')[-1]
                    files.append({
                        'name': name,
                        'path': zip_info.filename,
                        'content': content,
                    })
                except Exception as e:
                    print(f"Failed to extract {zip_info.filename}: {e}")
    
    return files


def read_from_folder(folder_path: str) -> List[Dict[str, str]]:
    """Read files from a local folder.
    
    Args:
        folder_path: Path to the folder containing skill files
        
    Returns:
        List of file dictionaries with 'name', 'path', and 'content' keys
        
    Raises:
        Exception: If folder doesn't exist or can't be read
    """
    if not os.path.exists(folder_path):
        raise Exception(f"Folder does not exist: {folder_path}")
    
    if not os.path.isdir(folder_path):
        raise Exception(f"Path is not a directory: {folder_path}")
    
    files: List[Dict[str, str]] = []
    
    # Walk through the directory recursively
    for root, dirs, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            try:
                # Calculate relative path from the base folder
                relative_path = os.path.relpath(file_path, folder_path)
                
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                files.append({
                    'name': filename,
                    'path': relative_path,
                    'content': content,
                })
            except Exception as e:
                print(f"Failed to read {file_path}: {e}")
    
    return files


def import_anthropic_skill(
    source_type: str,
    source_data: Any,
    snippet_mode: str = 'file'
) -> Tuple[str, str, List[Any], List[Any], List[str]]:
    """Import Anthropic skill from various sources.
    
    Args:
        source_type: 'url', 'zip', or 'folder'
        source_data: URL string, ZIP bytes, or list of file dicts
        snippet_mode: 'file' or 'paragraph'
        
    Returns:
        Tuple of (skill_name, skill_description, tools, snippets, ignored_files)
        
    Raises:
        Exception: If import fails
    """
    from .text_parser import parse_text_files
    from .code_parser import parse_code_files
    
    # Step 1: Get files
    files: List[Dict[str, str]]
    skill_name: str
    
    if source_type == 'url':
        if not isinstance(source_data, str):
            raise ValueError("source_data must be a URL string for 'url' source_type")
        skill_name = extract_skill_name(source_data, '')
        files = fetch_from_github(source_data)
    elif source_type == 'zip':
        if not isinstance(source_data, bytes):
            raise ValueError("source_data must be bytes for 'zip' source_type")
        # Extract skill name from first file's path
        temp_files = extract_from_zip(source_data)
        if temp_files:
            first_path = temp_files[0]['path']
            folder_name = first_path.split('/')[0] if '/' in first_path else 'anthropic_skill'
            skill_name = extract_skill_name('', folder_name)
        else:
            skill_name = 'anthropic_skill'
        files = temp_files
    elif source_type == 'folder':
        if not isinstance(source_data, str):
            raise ValueError("source_data must be a folder path string for 'folder' source_type")
        # Read files from the local folder
        files = read_from_folder(source_data)
        # Extract skill name from folder name
        folder_name = os.path.basename(os.path.normpath(source_data))
        skill_name = extract_skill_name('', folder_name)
    else:
        raise ValueError(f"Invalid source_type: {source_type}")
    
    if not files:
        raise Exception('No files found to import')
    
    # Step 2: Parse SKILL.md metadata if available
    skill_metadata = parse_skill_metadata(files)
    if skill_metadata and skill_metadata.get('name'):
        skill_name = skill_metadata['name']
    
    skill_description = (
        skill_metadata.get('description', '')
        if skill_metadata
        else f"Anthropic skill imported from {source_type}"
    )
    
    # Step 3: Parse files based on snippet mode
    snippets: List[Any]
    tools: List[Any]
    ignored_files: List[str]
    
    if snippet_mode == 'file':
        # In file mode, import all non-code files as snippets
        code_parse_result = parse_code_files(files, skill_name)
        tools = code_parse_result['tools']
        
        # Get all files that weren't parsed as tools
        tool_file_names = {t.source_file_name for t in tools}
        non_code_files = [f for f in files if f['name'] not in tool_file_names]
        
        # Import all non-code files as complete file snippets
        snippets = parse_text_files(non_code_files, skill_name, False)
        ignored_files = []  # No files are ignored in complete file mode
    else:
        # In paragraph mode, only parse text files and split by paragraph
        snippets = parse_text_files(files, skill_name, True)
        code_parse_result = parse_code_files(files, skill_name)
        tools = code_parse_result['tools']
        ignored_files = code_parse_result['ignoredFiles']
    
    return skill_name, skill_description, tools, snippets, ignored_files