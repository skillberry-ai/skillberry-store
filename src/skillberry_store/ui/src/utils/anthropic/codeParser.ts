// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

/**
 * Parser for code files (Python, Bash) to convert them into tools
 */

export interface ParsedTool {
  name: string;
  description: string;
  moduleContent: string;
  tags: string[];
  version: string;
  sourceFileName: string;
  params?: {
    type: string;
    properties: Record<string, any>;
    required?: string[];
  };
  returns?: {
    type: string;
    description: string;
  };
  programmingLanguage: string;
}

/**
 * Parse Python function to extract metadata
 */
function parsePythonFunction(
  functionCode: string,
  functionName: string
): { description: string; params: any; returns: any } {
  const lines = functionCode.split('\n');
  let description = '';
  const params: Record<string, any> = {};
  const required: string[] = [];
  let returns = { type: 'string', description: '' };
  
  // Extract docstring
  let inDocstring = false;
  let docstringLines: string[] = [];
  
  for (const line of lines) {
    const trimmed = line.trim();
    
    // Detect docstring start/end
    if (trimmed.startsWith('"""') || trimmed.startsWith("'''")) {
      if (inDocstring) {
        break; // End of docstring
      } else {
        inDocstring = true;
        const content = trimmed.substring(3);
        if (content && !content.endsWith('"""') && !content.endsWith("'''")) {
          docstringLines.push(content);
        }
        continue;
      }
    }
    
    if (inDocstring) {
      docstringLines.push(trimmed);
    }
  }
  
  // Parse docstring for description and parameters
  if (docstringLines.length > 0) {
    let currentSection = 'description';
    
    for (const line of docstringLines) {
      if (line.toLowerCase().includes('args:') || line.toLowerCase().includes('parameters:')) {
        currentSection = 'params';
        continue;
      } else if (line.toLowerCase().includes('returns:')) {
        currentSection = 'returns';
        continue;
      }
      
      if (currentSection === 'description' && line) {
        description += (description ? ' ' : '') + line;
      } else if (currentSection === 'params' && line) {
        // Parse parameter line: "param_name (type): description"
        const paramMatch = line.match(/^\s*(\w+)\s*(?:\(([^)]+)\))?\s*:\s*(.+)/);
        if (paramMatch) {
          const [, paramName, paramType, paramDesc] = paramMatch;
          params[paramName] = {
            type: paramType || 'string',
            description: paramDesc.trim(),
          };
          required.push(paramName);
        }
      } else if (currentSection === 'returns' && line) {
        returns.description += (returns.description ? ' ' : '') + line;
      }
    }
  }
  
  // Parse function signature for parameters if not in docstring
  const signatureMatch = functionCode.match(/def\s+\w+\s*\(([^)]*)\)/);
  if (signatureMatch) {
    const paramsStr = signatureMatch[1];
    const paramsList = paramsStr.split(',').map(p => p.trim()).filter(p => p && p !== 'self');
    
    for (const param of paramsList) {
      const [paramName, defaultValue] = param.split('=').map(s => s.trim());
      const cleanName = paramName.split(':')[0].trim();
      
      if (!params[cleanName]) {
        params[cleanName] = {
          type: 'string',
          description: `Parameter ${cleanName}`,
        };
      }
      
      // If has default value, it's optional
      if (defaultValue && required.includes(cleanName)) {
        required.splice(required.indexOf(cleanName), 1);
      }
    }
  }
  
  return {
    description: description || `Function ${functionName}`,
    params: Object.keys(params).length > 0 ? {
      type: 'object',
      properties: params,
      required: required.length > 0 ? required : undefined,
    } : undefined,
    returns: returns.description ? returns : undefined,
  };
}

/**
 * Parse Bash function to extract metadata
 */
function parseBashFunction(
  functionCode: string,
  functionName: string
): { description: string; params: any; returns: any } {
  const lines = functionCode.split('\n');
  let description = '';
  const params: Record<string, any> = {};
  
  // Extract comments above function
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('#')) {
      const comment = trimmed.substring(1).trim();
      if (comment) {
        description += (description ? ' ' : '') + comment;
      }
    } else if (trimmed.startsWith('function') || trimmed.includes('()')) {
      break;
    }
  }
  
  // Look for parameter usage in function body
  const paramMatches = functionCode.matchAll(/\$\{?(\d+)\}?/g);
  const paramNumbers = new Set<number>();
  for (const match of paramMatches) {
    const num = parseInt(match[1]);
    if (num > 0) {
      paramNumbers.add(num);
    }
  }
  
  // Create parameters based on usage
  Array.from(paramNumbers).sort().forEach(num => {
    params[`arg${num}`] = {
      type: 'string',
      description: `Argument ${num}`,
    };
  });
  
  return {
    description: description || `Function ${functionName}`,
    params: Object.keys(params).length > 0 ? {
      type: 'object',
      properties: params,
    } : undefined,
    returns: { type: 'string', description: 'Command output' },
  };
}

/**
 * Extract functions from Python code
 */
function extractPythonFunctions(content: string): Array<{ name: string; code: string }> {
  const functions: Array<{ name: string; code: string }> = [];
  const lines = content.split('\n');
  
  let currentFunction: { name: string; code: string; startIndent: number } | null = null;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();
    
    // Detect function definition
    const funcMatch = trimmed.match(/^def\s+(\w+)\s*\(/);
    if (funcMatch) {
      // Save previous function if exists
      if (currentFunction) {
        functions.push({ name: currentFunction.name, code: currentFunction.code });
      }
      
      // Start new function
      const indent = line.length - line.trimStart().length;
      currentFunction = {
        name: funcMatch[1],
        code: line + '\n',
        startIndent: indent,
      };
    } else if (currentFunction) {
      const indent = line.length - line.trimStart().length;
      
      // Continue adding lines to current function
      if (line.trim() === '' || indent > currentFunction.startIndent) {
        currentFunction.code += line + '\n';
      } else {
        // Function ended
        functions.push({ name: currentFunction.name, code: currentFunction.code });
        currentFunction = null;
      }
    }
  }
  
  // Add last function if exists
  if (currentFunction) {
    functions.push({ name: currentFunction.name, code: currentFunction.code });
  }
  
  return functions;
}

/**
 * Extract functions from Bash code
 */
function extractBashFunctions(content: string): Array<{ name: string; code: string }> {
  const functions: Array<{ name: string; code: string }> = [];
  
  // Match both "function name() {" and "name() {" patterns
  const functionRegex = /(?:^|\n)((?:#[^\n]*\n)*)\s*(?:function\s+)?(\w+)\s*\(\s*\)\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}/gm;
  
  let match;
  while ((match = functionRegex.exec(content)) !== null) {
    const [fullMatch, , name] = match;
    functions.push({
      name,
      code: fullMatch.trim(),
    });
  }
  
  return functions;
}

/**
 * Parse a code file into tools (one per function)
 */
export function parseCodeFile(
  content: string,
  fileName: string,
  filePath: string,
  skillName: string
): ParsedTool[] {
  const tools: ParsedTool[] = [];
  const ext = fileName.split('.').pop()?.toLowerCase();
  
  if (ext === 'py') {
    const functions = extractPythonFunctions(content);
    
    for (const func of functions) {
      const metadata = parsePythonFunction(func.code, func.name);
      const tags = [
        `file:${filePath}`,
        'python',
        'anthropic',
        ...filePath.split('/').filter(p => p && p !== '.' && p !== '..'),
      ];
      
      tools.push({
        name: `${skillName}_${func.name}`,
        sourceFileName: fileName,
        description: metadata.description,
        moduleContent: func.code,
        tags: [...new Set(tags)],
        version: '1.0.0',
        params: metadata.params,
        returns: metadata.returns,
        programmingLanguage: 'python',
      });
    }
  } else if (ext === 'sh' || ext === 'bash') {
    const functions = extractBashFunctions(content);
    
    for (const func of functions) {
      const metadata = parseBashFunction(func.code, func.name);
      const tags = [
        `file:${filePath}`,
        'bash',
        'anthropic',
        ...filePath.split('/').filter(p => p && p !== '.' && p !== '..'),
      ];
      
      tools.push({
        name: `${skillName}_${func.name}`,
        sourceFileName: fileName,
        description: metadata.description,
        moduleContent: func.code,
        tags: [...new Set(tags)],
        version: '1.0.0',
        params: metadata.params,
        returns: metadata.returns,
        programmingLanguage: 'bash',
      });
    }
  }
  
  return tools;
}

/**
 * Check if a file should be processed as a code file
 */
export function isCodeFile(fileName: string): boolean {
  const codeExtensions = ['.py', '.sh', '.bash'];
  return codeExtensions.some(ext => fileName.toLowerCase().endsWith(ext));
}

/**
 * Parse multiple code files from a skill
 */
export function parseCodeFiles(
  files: Array<{ name: string; path: string; content: string }>,
  skillName: string
): { tools: ParsedTool[]; ignoredFiles: string[] } {
  const tools: ParsedTool[] = [];
  const ignoredFiles: string[] = [];
  
  for (const file of files) {
    const ext = file.name.split('.').pop()?.toLowerCase();
    
    if (isCodeFile(file.name)) {
      try {
        const fileTool = parseCodeFile(file.content, file.name, file.path, skillName);
        tools.push(...fileTool);
      } catch (error) {
        console.error(`Failed to parse code file ${file.name}:`, error);
        ignoredFiles.push(file.name);
      }
    } else if (ext && !['md', 'txt', 'json', 'yaml', 'yml'].includes(ext)) {
      // Log non-text, non-supported code files
      console.log(`Ignoring unsupported file type: ${file.name}`);
      ignoredFiles.push(file.name);
    }
  }
  
  return { tools, ignoredFiles };
}