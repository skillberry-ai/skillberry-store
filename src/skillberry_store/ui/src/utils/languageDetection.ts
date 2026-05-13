// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

/**
 * Detects the programming language from content type or file extension
 * Returns a language identifier compatible with react-syntax-highlighter
 */
export function detectLanguage(contentType?: string, fileName?: string, tags?: string[]): string {
  // Check content type first
  if (contentType) {
    const contentTypeMap: Record<string, string> = {
      'text/x-python': 'python',
      'text/javascript': 'javascript',
      'application/javascript': 'javascript',
      'text/typescript': 'typescript',
      'application/typescript': 'typescript',
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
      'text/x-sql': 'sql',
      'text/markdown': 'markdown',
      'text/xml': 'xml',
    };
    
    const language = contentTypeMap[contentType.toLowerCase()];
    if (language) return language;
  }
  
  // Check file extension from fileName or tags
  let extension = '';
  
  if (fileName) {
    const parts = fileName.split('.');
    if (parts.length > 1) {
      extension = parts[parts.length - 1].toLowerCase();
    }
  }
  
  // If no extension from fileName, check tags for file: prefix
  if (!extension && tags) {
    const fileTag = tags.find(tag => tag.startsWith('file:'));
    if (fileTag) {
      const filePath = fileTag.substring(5); // Remove 'file:' prefix
      const parts = filePath.split('.');
      if (parts.length > 1) {
        extension = parts[parts.length - 1].toLowerCase();
      }
    }
  }
  
  if (extension) {
    const extensionMap: Record<string, string> = {
      'py': 'python',
      'js': 'javascript',
      'jsx': 'javascript',
      'ts': 'typescript',
      'tsx': 'typescript',
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
      'sql': 'sql',
      'md': 'markdown',
      'xml': 'xml',
      'php': 'php',
      'swift': 'swift',
      'kt': 'kotlin',
      'scala': 'scala',
      'r': 'r',
      'pl': 'perl',
      'lua': 'lua',
    };
    
    const language = extensionMap[extension];
    if (language) return language;
  }
  
  // Default to python as it's the most common in this system
  return 'python';
}
