// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

/**
 * Maps content types and file extensions to syntax highlighter language identifiers
 */
export function getLanguageFromContentType(contentType: string): string {
  const contentTypeMap: Record<string, string> = {
    'text/x-python': 'python',
    'text/javascript': 'javascript',
    'text/x-java': 'java',
    'text/x-go': 'go',
    'text/x-sh': 'bash',
    'text/x-yaml': 'yaml',
    'application/json': 'json',
    'text/html': 'html',
    'text/css': 'css',
    'text/x-c': 'c',
    'text/x-c++': 'cpp',
    'text/x-csharp': 'csharp',
    'text/x-ruby': 'ruby',
    'text/x-rust': 'rust',
    'text/x-typescript': 'typescript',
    'text/markdown': 'markdown',
    'text/xml': 'xml',
    'text/x-sql': 'sql',
    'text/plain': 'text',
  };

  return contentTypeMap[contentType] || 'text';
}

/**
 * Determines the language from a file extension
 */
export function getLanguageFromExtension(filename: string): string {
  const extensionMap: Record<string, string> = {
    'py': 'python',
    'js': 'javascript',
    'jsx': 'jsx',
    'ts': 'typescript',
    'tsx': 'tsx',
    'java': 'java',
    'go': 'go',
    'sh': 'bash',
    'bash': 'bash',
    'yaml': 'yaml',
    'yml': 'yaml',
    'json': 'json',
    'html': 'html',
    'htm': 'html',
    'css': 'css',
    'c': 'c',
    'cpp': 'cpp',
    'cc': 'cpp',
    'cxx': 'cpp',
    'cs': 'csharp',
    'rb': 'ruby',
    'rs': 'rust',
    'md': 'markdown',
    'xml': 'xml',
    'sql': 'sql',
    'txt': 'text',
  };

  const extension = filename.split('.').pop()?.toLowerCase();
  return extension ? (extensionMap[extension] || 'text') : 'text';
}

/**
 * Determines the best language identifier for syntax highlighting
 * Tries file extension first, then falls back to content type
 */
export function determineLanguage(
  filename?: string,
  contentType?: string,
  programmingLanguage?: string
): string {
  // First priority: explicit programming language
  if (programmingLanguage) {
    return programmingLanguage.toLowerCase();
  }

  // Second priority: file extension
  if (filename) {
    const lang = getLanguageFromExtension(filename);
    if (lang !== 'text') {
      return lang;
    }
  }

  // Third priority: content type
  if (contentType) {
    return getLanguageFromContentType(contentType);
  }

  // Default fallback
  return 'text';
}
