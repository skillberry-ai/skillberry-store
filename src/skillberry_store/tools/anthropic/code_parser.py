# Copyright 2025 IBM Corp.
# Licensed under the Apache License, Version 2.0

"""Parser for code files (Python, Bash) to convert them into tools."""

import ast
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


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


def _ast_annotation_to_json_type(annotation: Optional[ast.expr]) -> str:
    """Convert AST type annotation to JSON schema type.
    
    Args:
        annotation: AST annotation node
        
    Returns:
        JSON schema type string
    """
    if annotation is None:
        return 'string'
    
    # Handle simple types like str, int, bool, etc.
    if isinstance(annotation, ast.Name):
        type_name = annotation.id.lower()
        if type_name in ('int', 'integer'):
            return 'integer'
        elif type_name in ('float', 'number'):
            return 'number'
        elif type_name in ('bool', 'boolean'):
            return 'boolean'
        elif type_name in ('str', 'string'):
            return 'string'
        elif type_name in ('list', 'tuple'):
            return 'array'
        elif type_name in ('dict', 'dictionary'):
            return 'object'
        elif type_name == 'none':
            return 'null'
    
    # Handle subscripted types like List[str], Optional[int], etc.
    elif isinstance(annotation, ast.Subscript):
        if isinstance(annotation.value, ast.Name):
            base_type = annotation.value.id.lower()
            if base_type in ('list', 'tuple', 'sequence'):
                return 'array'
            elif base_type in ('dict', 'mapping'):
                return 'object'
            elif base_type == 'optional':
                # For Optional[T], extract T
                if isinstance(annotation.slice, ast.Name):
                    return _ast_annotation_to_json_type(annotation.slice)
    
    # Handle Union types
    elif isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        # This handles Union types with | operator (Python 3.10+)
        # For now, just return string as default
        return 'string'
    
    # Default to string for unknown types
    return 'string'


def parse_python_function(function_code: str, function_name: str) -> Tuple[str, Optional[Dict], Optional[Dict]]:
    """Parse Python function to extract metadata using AST only.
    
    Args:
        function_code: The function code
        function_name: The function name
        
    Returns:
        Tuple of (description, params, returns)
        
    Raises:
        SyntaxError: If the function code cannot be parsed
    """
    description = ''
    params: Dict[str, Any] = {}
    required: List[str] = []
    returns: Optional[Dict[str, str]] = None
    
    # First, try to fix common syntax issues in the function code
    # Handle cases like "param: 0" which should be "param=0" (default without type)
    # This is invalid Python syntax but may appear in user code
    fixed_code = function_code
    
    # Pattern to match parameter definitions like "param: value," where value is not a type
    # This handles cases like "total_baggages: 0," which should be "total_baggages=0,"
    import_pattern = r'(\w+):\s*(\d+|"[^"]*"|\'[^\']*\'|True|False|None)\s*([,)])'
    
    def fix_param(match):
        param_name = match.group(1)
        value = match.group(2)
        separator = match.group(3)
        # Check if this looks like a default value (number, string, bool, None)
        # rather than a type annotation
        return f'{param_name}={value}{separator}'
    
    # Try to fix the syntax
    fixed_code = re.sub(import_pattern, fix_param, function_code)
    
    # Additional fix: reorder parameters to put those with defaults at the end
    # This handles cases where non-default params come after default params
    def reorder_params(code: str) -> str:
        """Reorder function parameters to put defaults at the end."""
        # Find function signature
        func_pattern = r'(def\s+\w+\s*\()([^)]+)(\):)'
        match = re.search(func_pattern, code, re.DOTALL)
        if not match:
            return code
        
        prefix = match.group(1)
        params_str = match.group(2)
        suffix = match.group(3)
        
        # Split parameters
        params = [p.strip() for p in params_str.split(',') if p.strip()]
        
        # Separate params with and without defaults
        params_no_default = []
        params_with_default = []
        
        for param in params:
            if '=' in param:
                params_with_default.append(param)
            else:
                params_no_default.append(param)
        
        # Reorder: no defaults first, then with defaults
        reordered = params_no_default + params_with_default
        new_params_str = ',\n    '.join(reordered)
        
        # Reconstruct function
        return code[:match.start()] + prefix + new_params_str + suffix + code[match.end():]
    
    fixed_code = reorder_params(fixed_code)
    
    # Parse function using AST
    try:
        tree = ast.parse(fixed_code)
    except SyntaxError:
        # If fixing didn't work, try original code
        try:
            tree = ast.parse(function_code)
        except SyntaxError as e:
            # Last resort: try to parse with reordering only (no value fixes)
            reordered_only = reorder_params(function_code)
            tree = ast.parse(reordered_only)
    
    # Find the function definition
    func_def = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            func_def = node
            break
    
    if not func_def:
        raise ValueError(f"Function '{function_name}' not found in code")
    
    # Extract docstring using AST
    docstring = ast.get_docstring(func_def)
    docstring_params: Dict[str, str] = {}
    
    if docstring:
        # Parse docstring for description and parameter descriptions
        lines = docstring.split('\n')
        current_section = 'description'
        
        for line in lines:
            line_stripped = line.strip()
            
            if 'args:' in line_stripped.lower() or 'parameters:' in line_stripped.lower():
                current_section = 'params'
                continue
            elif 'returns:' in line_stripped.lower():
                current_section = 'returns'
                continue
            
            if current_section == 'description' and line_stripped:
                description += (' ' if description else '') + line_stripped
            elif current_section == 'params' and line_stripped:
                # Parse parameter line: "param_name (type): description"
                param_match = re.match(r'^\s*(\w+)\s*(?:\(([^)]+)\))?\s*:\s*(.+)', line_stripped)
                if param_match:
                    param_name, param_type, param_desc = param_match.groups()
                    docstring_params[param_name] = param_desc.strip()
            elif current_section == 'returns' and line_stripped:
                if not returns:
                    returns = {'type': 'string', 'description': ''}
                returns['description'] += (' ' if returns['description'] else '') + line_stripped
    
    # Extract parameters from AST
    for arg in func_def.args.args:
        if arg.arg == 'self':
            continue
        
        param_name = arg.arg
        
        # Get type from annotation
        json_type = _ast_annotation_to_json_type(arg.annotation)
        
        # Get description from docstring if available
        param_desc = docstring_params.get(param_name, f"Parameter {param_name}")
        
        params[param_name] = {
            'type': json_type,
            'description': param_desc,
        }
    
    # Check for default values
    num_defaults = len(func_def.args.defaults)
    num_args = len(func_def.args.args)
    
    # Parameters without defaults are required
    for i, arg in enumerate(func_def.args.args):
        if arg.arg == 'self':
            continue
        
        # If this parameter has a default value, it's optional
        has_default = i >= (num_args - num_defaults)
        if not has_default:
            required.append(arg.arg)
    
    # Extract return type annotation
    if func_def.returns:
        return_json_type = _ast_annotation_to_json_type(func_def.returns)
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
            try:
                description, params, returns = parse_python_function(func['code'], func['name'])
            except (SyntaxError, ValueError) as e:
                # If parsing individual function fails, try parsing the whole file
                logger.warning(f"Failed to parse function '{func['name']}' individually: {e}")
                logger.info(f"Attempting to parse entire file instead...")
                try:
                    description, params, returns = parse_python_function(content, func['name'])
                except Exception as e2:
                    logger.error(f"Failed to parse function '{func['name']}': {e2}")
                    description = f"Function {func['name']}"
                    params = None
                    returns = None
            
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
                try:
                    description, params, returns = parse_python_function(func['code'], func['name'])
                except (SyntaxError, ValueError) as e:
                    # If parsing individual function fails, try parsing the whole file
                    logger.warning(f"Failed to parse function '{func['name']}' individually: {e}")
                    logger.info(f"Attempting to parse entire file instead...")
                    try:
                        description, params, returns = parse_python_function(content, func['name'])
                    except Exception as e2:
                        logger.error(f"Failed to parse function '{func['name']}': {e2}")
                        description = f"Function {func['name']}"
                        params = None
                        returns = None
                
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