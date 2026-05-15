// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

/**
 * Detects programming language from file tags
 * Used for syntax highlighting in code blocks
 */
export const detectLanguage = (tags: string[]): string => {
  // Check for file: tag to extract extension
  const fileTag = tags.find(tag => tag.startsWith('file:'));
  if (fileTag) {
    const filePath = fileTag.substring(5);
    const extension = filePath.split('.').pop()?.toLowerCase();
    
    const languageMap: Record<string, string> = {
      'py': 'python',
      'js': 'javascript',
      'ts': 'typescript',
      'jsx': 'jsx',
      'tsx': 'tsx',
      'java': 'java',
      'cpp': 'cpp',
      'c': 'c',
      'cs': 'csharp',
      'go': 'go',
      'rs': 'rust',
      'rb': 'ruby',
      'php': 'php',
      'swift': 'swift',
      'kt': 'kotlin',
      'scala': 'scala',
      'sh': 'bash',
      'bash': 'bash',
      'zsh': 'bash',
      'sql': 'sql',
      'json': 'json',
      'yaml': 'yaml',
      'yml': 'yaml',
      'xml': 'xml',
      'html': 'html',
      'css': 'css',
      'scss': 'scss',
      'md': 'markdown',
      'txt': 'text',
    };
    
    if (extension && languageMap[extension]) {
      return languageMap[extension];
    }
  }
  
  // Check for language: tag
  const langTag = tags.find(tag => tag.startsWith('language:'));
  if (langTag) {
    return langTag.substring(9).toLowerCase();
  }
  
  // Default to text
  return 'text';
};
