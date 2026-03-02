# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""Parser for code files (Python, Bash) to convert them into tools."""

import re
from typing import List, Dict, Any, Optional, Tuple


class ParsedTool:
    """Represents a parsed tool from a code file."""
    
    def __init__(
        self,
        name: str,
        description: str,
        module_content: str,
        tags: List[str],
        version: str = "1.0.0",
        source_file_name: str = "",
        params: Optional[Dict[str, Any]] = None,
        returns: Optional[Dict[str, Any]] = None,
        programming_language: str = "python"
    ):
        self.name = name
        self.description = description
        self.module_content = module_content
        self.tags = tags
        self.version = version
        self.source_file_name = source_file_name
        self.params = params
        self.returns = returns
        self.programming_language = programming_language
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            'name': self.name,
            'description': self.description,
            'moduleContent': self.module_content,
            'tags': self.tags,
            'version': self.version,
            'sourceFileName': self.source_file_name,
            'programmingLanguage': self.programming_language,
        }
        if self.params:
            result['params'] = self.params
        if self.returns:
            result['returns'] = self.returns
        return result


def parse_python_function(function_code: str, function_name: str) -> Tuple[str, Optional[Dict], Optional[Dict]]:
    """Parse Python function to extract metadata.
    
    Args:
        function_code: The function code
        function_name: The function name
        
    Returns:
        Tuple of (description, params, returns)
    """
    lines = function_code.split('\n')
    description = ''
    params: Dict[str, Any] = {}
    required: List[str] = []
    returns: Optional[Dict[str, str]] = None
    
    # Extract docstring
    in_docstring = False
    docstring_lines: List[str] = []
    
    for line in lines:
        trimmed = line.strip()
        
        # Detect docstring start/end
        if trimmed.startswith('"""') or trimmed.startswith("'''"):
            if in_docstring:
                break  # End of docstring
            else:
                in_docstring = True
                content = trimmed[3:]
                if content and not (content.endswith('"""') or content.endswith("'''")):
                    docstring_lines.append(content)
                continue
        
        if in_docstring:
            docstring_lines.append(trimmed)
    
    # Parse docstring for description and parameters
    if docstring_lines:
        current_section = 'description'
        
        for line in docstring_lines:
            if 'args:' in line.lower() or 'parameters:' in line.lower():
                current_section = 'params'
                continue
            elif 'returns:' in line.lower():
                current_section = 'returns'
                continue
            
            if current_section == 'description' and line:
                description += (' ' if description else '') + line
            elif current_section == 'params' and line:
                # Parse parameter line: "param_name (type): description"
                param_match = re.match(r'^\s*(\w+)\s*(?:\(([^)]+)\))?\s*:\s*(.+)', line)
                if param_match:
                    param_name, param_type, param_desc = param_match.groups()
                    params[param_name] = {
                        'type': param_type or 'string',
                        'description': param_desc.strip(),
                    }
                    required.append(param_name)
            elif current_section == 'returns' and line:
                if not returns:
                    returns = {'type': 'string', 'description': ''}
                returns['description'] += (' ' if returns['description'] else '') + line
    
    # Parse function signature for parameters if not in docstring
    signature_match = re.search(r'def\s+\w+\s*\(([^)]*)\)', function_code)
    if signature_match:
        params_str = signature_match.group(1)
        params_list = [p.strip() for p in params_str.split(',') if p.strip() and p.strip() != 'self']
        
        for param in params_list:
            # Split by '=' to separate parameter from default value
            parts = param.split('=')
            param_part = parts[0].strip()
            default_value = parts[1].strip() if len(parts) > 1 else None
            
            # Split by ':' to separate name from type annotation
            if ':' in param_part:
                clean_name, type_annotation = param_part.split(':', 1)
                clean_name = clean_name.strip()
                type_annotation = type_annotation.strip()
            else:
                clean_name = param_part
                type_annotation = None
            
            if clean_name not in params:
                # Map Python type annotations to JSON schema types
                json_type = 'string'
                if type_annotation:
                    lower_type = type_annotation.lower()
                    if 'int' in lower_type:
                        json_type = 'integer'
                    elif 'float' in lower_type or 'number' in lower_type:
                        json_type = 'number'
                    elif 'bool' in lower_type:
                        json_type = 'boolean'
                    elif 'list' in lower_type or 'tuple' in lower_type:
                        json_type = 'array'
                    elif 'dict' in lower_type:
                        json_type = 'object'
                    elif 'str' in lower_type:
                        json_type = 'string'
                
                params[clean_name] = {
                    'type': json_type,
                    'description': f"Parameter {clean_name}" + (f" ({type_annotation})" if type_annotation else ""),
                }
                
                # Add to required list if no default value
                if not default_value:
                    required.append(clean_name)
            else:
                # Parameter was in docstring, update type if we have annotation
                if type_annotation:
                    lower_type = type_annotation.lower()
                    if 'int' in lower_type:
                        params[clean_name]['type'] = 'integer'
                    elif 'float' in lower_type or 'number' in lower_type:
                        params[clean_name]['type'] = 'number'
                    elif 'bool' in lower_type:
                        params[clean_name]['type'] = 'boolean'
                    elif 'list' in lower_type or 'tuple' in lower_type:
                        params[clean_name]['type'] = 'array'
                    elif 'dict' in lower_type:
                        params[clean_name]['type'] = 'object'
                    elif 'str' in lower_type:
                        params[clean_name]['type'] = 'string'
                
                # If has default value, remove from required
                if default_value and clean_name in required:
                    required.remove(clean_name)
    
    # Parse return type annotation from function signature
    return_type_match = re.search(r'def\s+\w+\s*\([^)]*\)\s*->\s*([^:]+):', function_code)
    if return_type_match:
        return_type_annotation = return_type_match.group(1).strip()
        return_json_type = 'string'
        
        lower_return_type = return_type_annotation.lower()
        if 'int' in lower_return_type:
            return_json_type = 'integer'
        elif 'float' in lower_return_type or 'number' in lower_return_type:
            return_json_type = 'number'
        elif 'bool' in lower_return_type:
            return_json_type = 'boolean'
        elif 'list' in lower_return_type or 'tuple' in lower_return_type:
            return_json_type = 'array'
        elif 'dict' in lower_return_type:
            return_json_type = 'object'
        elif 'str' in lower_return_type:
            return_json_type = 'string'
        elif lower_return_type == 'none':
            return_json_type = 'null'
        
        if not returns:
            returns = {'type': return_json_type, 'description': ''}
        else:
            returns['type'] = return_json_type
    
    params_result = None
    if params:
        params_result = {
            'type': 'object',
            'properties': params,
        }
        if required:
            params_result['required'] = required
    
    return (
        description or f"Function {function_name}",
        params_result,
        returns
    )


def parse_bash_function(function_code: str, function_name: str) -> Tuple[str, Optional[Dict], Optional[Dict]]:
    """Parse Bash function to extract metadata.
    
    Args:
        function_code: The function code
        function_name: The function name
        
    Returns:
        Tuple of (description, params, returns)
    """
    lines = function_code.split('\n')
    description = ''
    params: Dict[str, Any] = {}
    
    # Extract comments above function
    for line in lines:
        trimmed = line.strip()
        if trimmed.startswith('#'):
            comment = trimmed[1:].strip()
            if comment:
                description += (' ' if description else '') + comment
        elif trimmed.startswith('function') or '()' in trimmed:
            break
    
    # Look for parameter usage in function body
    param_matches = re.findall(r'\$\{?(\d+)\}?', function_code)
    param_numbers = set(int(m) for m in param_matches if int(m) > 0)
    
    # Create parameters based on usage
    for num in sorted(param_numbers):
        params[f'arg{num}'] = {
            'type': 'string',
            'description': f'Argument {num}',
        }
    
    params_result = None
    if params:
        params_result = {
            'type': 'object',
            'properties': params,
        }
    
    return (
        description or f"Function {function_name}",
        params_result,
        {'type': 'string', 'description': 'Command output'}
    )


def extract_python_functions(content: str) -> List[Dict[str, str]]:
    """Extract top-level functions from Python code.
    
    Only extracts functions defined at indentation level 0 to avoid extracting
    internal/nested helper functions. Internal functions remain part of their
    parent function's code.
    
    Args:
        content: The Python code content
        
    Returns:
        List of dictionaries with 'name' and 'code' keys
    """
    functions: List[Dict[str, str]] = []
    lines = content.split('\n')
    
    current_function: Optional[Dict[str, Any]] = None
    
    for line in lines:
        trimmed = line.strip()
        indent = len(line) - len(line.lstrip())
        
        # Detect function definition
        func_match = re.match(r'^def\s+(\w+)\s*\(', trimmed)
        if func_match:
            # Only process top-level functions (indent == 0)
            if indent == 0:
                # Save previous function if exists
                if current_function:
                    functions.append({'name': current_function['name'], 'code': current_function['code']})
                
                # Start new function
                current_function = {
                    'name': func_match.group(1),
                    'code': line + '\n',
                    'start_indent': indent,
                }
            elif current_function:
                # This is a nested function, include it in the parent function's code
                current_function['code'] += line + '\n'
        elif current_function:
            # Continue adding lines to current function
            if not line.strip() or indent > current_function['start_indent']:
                current_function['code'] += line + '\n'
            else:
                # Function ended (back to indent level 0 or less)
                functions.append({'name': current_function['name'], 'code': current_function['code']})
                current_function = None
    
    # Add last function if exists
    if current_function:
        functions.append({'name': current_function['name'], 'code': current_function['code']})
    
    return functions


def extract_bash_functions(content: str) -> List[Dict[str, str]]:
    """Extract functions from Bash code.
    
    Args:
        content: The Bash code content
        
    Returns:
        List of dictionaries with 'name' and 'code' keys
    """
    functions: List[Dict[str, str]] = []
    
    # Match both "function name() {" and "name() {" patterns
    function_regex = r'(?:^|\n)((?:#[^\n]*\n)*)\s*(?:function\s+)?(\w+)\s*\(\s*\)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}'
    
    for match in re.finditer(function_regex, content, re.MULTILINE):
        full_match = match.group(0)
        name = match.group(2)
        functions.append({
            'name': name,
            'code': full_match.strip(),
        })
    
    return functions


def parse_code_file(
    content: str,
    file_name: str,
    file_path: str,
    skill_name: str
) -> List[ParsedTool]:
    """Parse a code file into tools (one per function).
    
    Args:
        content: The file content
        file_name: The file name
        file_path: The file path
        skill_name: The skill name
        
    Returns:
        List of ParsedTool objects
    """
    tools: List[ParsedTool] = []
    ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
    
    if ext == 'py':
        functions = extract_python_functions(content)
        
        # If no functions found, treat the entire file as a standalone script
        if not functions:
            # Extract description from module docstring or first comment
            description = "Python script"
            lines = content.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    # Found docstring
                    docstring_lines = []
                    in_docstring = False
                    quote_char = '"""' if stripped.startswith('"""') else "'''"
                    
                    for doc_line in lines:
                        doc_stripped = doc_line.strip()
                        if quote_char in doc_stripped:
                            if in_docstring:
                                # End of docstring
                                break
                            else:
                                # Start of docstring
                                in_docstring = True
                                # Get text after opening quotes
                                after_quote = doc_stripped.split(quote_char, 1)[1]
                                if after_quote and not after_quote.startswith(quote_char):
                                    docstring_lines.append(after_quote)
                        elif in_docstring:
                            docstring_lines.append(doc_stripped)
                    
                    if docstring_lines:
                        description = ' '.join(docstring_lines).strip()
                    break
                elif stripped.startswith('#') and not stripped.startswith('#!'):
                    # Use first comment as description
                    description = stripped[1:].strip()
                    break
            
            # Create tool name from filename
            tool_name = file_name.rsplit('.', 1)[0].replace('-', '_').replace(' ', '_')
            
            tags = [
                f"file:{file_path}",
                f"skill:{skill_name}",
                'python',
                'anthropic',
                'script',
            ] + [p for p in file_path.split('/') if p and p not in ('.', '..')]
            
            tools.append(ParsedTool(
                name=tool_name,
                source_file_name=file_name,
                description=description,
                module_content=content,
                tags=list(dict.fromkeys(tags)),
                version='1.0.0',
                params=None,
                returns=None,
                programming_language='python'
            ))
            return tools
        
        # If there is exactly one function, use the entire file content as the module
        # so that imports and module-level globals are preserved.
        if len(functions) == 1:
            func = functions[0]
            description, params, returns = parse_python_function(func['code'], func['name'])
            tags = [
                f"file:{file_path}",
                f"skill:{skill_name}",
                'python',
                'anthropic',
            ] + [p for p in file_path.split('/') if p and p not in ('.', '..')]

            tools.append(ParsedTool(
                name=func['name'],
                source_file_name=file_name,
                description=description,
                module_content=content,  # Use full file content to preserve imports/globals
                tags=list(dict.fromkeys(tags)),
                version='1.0.0',
                params=params,
                returns=returns,
                programming_language='python'
            ))
        else:
            for func in functions:
                description, params, returns = parse_python_function(func['code'], func['name'])
                tags = [
                    f"file:{file_path}",
                    f"skill:{skill_name}",
                    'python',
                    'anthropic',
                ] + [p for p in file_path.split('/') if p and p not in ('.', '..')]

                tools.append(ParsedTool(
                    name=func['name'],
                    source_file_name=file_name,
                    description=description,
                    module_content=content,  # Use full file content so imports and globals are preserved
                    tags=list(dict.fromkeys(tags)),  # Remove duplicates while preserving order
                    version='1.0.0',
                    params=params,
                    returns=returns,
                    programming_language='python'
                ))
    
    elif ext in ('sh', 'bash'):
        functions = extract_bash_functions(content)
        
        # If no functions found, treat the entire file as a standalone script
        if not functions:
            # Extract description from first comment
            description = "Bash script"
            lines = content.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('#') and not stripped.startswith('#!'):
                    description = stripped[1:].strip()
                    break
            
            # Create tool name from filename
            tool_name = file_name.rsplit('.', 1)[0].replace('-', '_').replace(' ', '_')
            
            tags = [
                f"file:{file_path}",
                f"skill:{skill_name}",
                'bash',
                'anthropic',
                'script',
            ] + [p for p in file_path.split('/') if p and p not in ('.', '..')]
            
            tools.append(ParsedTool(
                name=tool_name,
                source_file_name=file_name,
                description=description,
                module_content=content,
                tags=list(dict.fromkeys(tags)),
                version='1.0.0',
                params=None,
                returns=None,
                programming_language='bash'
            ))
            return tools
        
        # If there is exactly one function, use the entire file content as the module
        # so that any preamble (shebang, sourced files, env vars) is preserved.
        if len(functions) == 1:
            func = functions[0]
            description, params, returns = parse_bash_function(func['code'], func['name'])
            tags = [
                f"file:{file_path}",
                f"skill:{skill_name}",
                'bash',
                'anthropic',
            ] + [p for p in file_path.split('/') if p and p not in ('.', '..')]

            tools.append(ParsedTool(
                name=func['name'],
                source_file_name=file_name,
                description=description,
                module_content=content,  # Use full file content to preserve preamble
                tags=list(dict.fromkeys(tags)),
                version='1.0.0',
                params=params,
                returns=returns,
                programming_language='bash'
            ))
        else:
            for func in functions:
                description, params, returns = parse_bash_function(func['code'], func['name'])
                tags = [
                    f"file:{file_path}",
                    f"skill:{skill_name}",
                    'bash',
                    'anthropic',
                ] + [p for p in file_path.split('/') if p and p not in ('.', '..')]

                tools.append(ParsedTool(
                    name=func['name'],
                    source_file_name=file_name,
                    description=description,
                    module_content=content,  # Use full file content so preamble and globals are preserved
                    tags=list(dict.fromkeys(tags)),  # Remove duplicates while preserving order
                    version='1.0.0',
                    params=params,
                    returns=returns,
                    programming_language='bash'
                ))
    
    return tools


def is_code_file(file_name: str) -> bool:
    """Check if a file should be processed as a code file.
    
    Args:
        file_name: The file name to check
        
    Returns:
        True if it's a code file, False otherwise
    """
    code_extensions = ['.py', '.sh', '.bash']
    file_name_lower = file_name.lower()
    return any(file_name_lower.endswith(ext) for ext in code_extensions)


def parse_code_files(
    files: List[Dict[str, str]],
    skill_name: str
) -> Dict[str, Any]:
    """Parse multiple code files from a skill.
    
    Args:
        files: List of file dictionaries with 'name', 'path', and 'content' keys
        skill_name: The skill name
        
    Returns:
        Dictionary with 'tools' and 'ignoredFiles' keys
    """
    tools: List[ParsedTool] = []
    ignored_files: List[str] = []
    
    for file in files:
        ext = file['name'].split('.')[-1].lower() if '.' in file['name'] else ''
        
        if is_code_file(file['name']):
            try:
                file_tools = parse_code_file(file['content'], file['name'], file['path'], skill_name)
                tools.extend(file_tools)
            except Exception as e:
                print(f"Failed to parse code file {file['name']}: {e}")
                ignored_files.append(file['name'])
        elif ext and ext not in ['md', 'txt', 'json', 'yaml', 'yml']:
            # Log non-text, non-supported code files
            print(f"Ignoring unsupported file type: {file['name']}")
            ignored_files.append(file['name'])
    
    return {'tools': tools, 'ignoredFiles': ignored_files}