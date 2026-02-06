// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

/**
 * Parser for text files (markdown, txt, etc.) to convert them into snippets
 */

export interface ParsedSnippet {
  name: string;
  description: string;
  content: string;
  tags: string[];
  version: string;
}

/**
 * Split text content into paragraphs
 * A paragraph is defined as text separated by double newlines
 */
function splitIntoParagraphs(content: string): string[] {
  // Split by double newlines (or more) and filter out empty strings
  const paragraphs = content
    .split(/\n\s*\n/)
    .map(p => p.trim())
    .filter(p => p.length > 0);
  
  return paragraphs;
}

/**
 * Generate a description from content (first 100 chars or first line)
 */
function generateDescription(content: string): string {
  const firstLine = content.split('\n')[0].trim();
  if (firstLine.length > 0 && firstLine.length <= 100) {
    return firstLine;
  }
  return content.substring(0, 100).trim() + (content.length > 100 ? '...' : '');
}

/**
 * Extract tags from filename and path
 */
function extractTags(filePath: string, fileName: string): string[] {
  const tags: string[] = [];
  
  // Add file extension as tag
  const ext = fileName.split('.').pop();
  if (ext) {
    tags.push(ext);
  }
  
  // Add directory names as tags (excluding common ones)
  const pathParts = filePath.split('/').filter(p => 
    p && p !== '.' && p !== '..' && p !== 'src' && p !== 'docs'
  );
  tags.push(...pathParts);
  
  // Add 'anthropic' tag to identify source
  tags.push('anthropic');
  
  return [...new Set(tags)]; // Remove duplicates
}

/**
 * Parse a text file into snippets (one per paragraph or complete file)
 */
export function parseTextFile(
  content: string,
  fileName: string,
  filePath: string,
  skillName: string,
  splitByParagraph: boolean = true
): ParsedSnippet[] {
  const tags = extractTags(filePath, fileName);
  const baseFileName = fileName.replace(/\.[^/.]+$/, ''); // Remove extension
  
  // Add file path tag in format file:complete_path_filename as the first tag
  const filePathTag = `file:${filePath}`;
  
  if (!splitByParagraph) {
    // Import as a single snippet (complete file)
    return [{
      name: `${skillName}_${baseFileName}`,
      description: generateDescription(content),
      content: content,
      tags: [filePathTag, ...tags],
      version: '1.0.0',
    }];
  }
  
  // Split by paragraphs
  const paragraphs = splitIntoParagraphs(content);
  
  return paragraphs.map((paragraph, index) => {
    const snippetName = paragraphs.length === 1
      ? `${skillName}_${baseFileName}`
      : `${skillName}_${baseFileName}_${index + 1}`;
    
    return {
      name: snippetName,
      description: generateDescription(paragraph),
      content: paragraph,
      tags: [filePathTag, ...tags], // File path tag first
      version: '1.0.0',
    };
  });
}

/**
 * Check if a file should be processed as a text file
 */
export function isTextFile(fileName: string): boolean {
  const textExtensions = [
    '.md', '.txt', '.rst', '.adoc', '.asciidoc',
    '.markdown', '.mdown', '.mkd', '.mkdn',
    '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',
    '.xml', '.html', '.htm', '.css',
  ];
  
  return textExtensions.some(ext => fileName.toLowerCase().endsWith(ext));
}

/**
 * Parse multiple text files from a skill
 */
export function parseTextFiles(
  files: Array<{ name: string; path: string; content: string }>,
  skillName: string,
  splitByParagraph: boolean = true
): ParsedSnippet[] {
  const allSnippets: ParsedSnippet[] = [];
  
  for (const file of files) {
    // In paragraph mode, only process text files
    // In file mode (splitByParagraph=false), process all files
    const shouldProcess = !splitByParagraph || isTextFile(file.name);
    
    if (shouldProcess) {
      try {
        const snippets = parseTextFile(file.content, file.name, file.path, skillName, splitByParagraph);
        allSnippets.push(...snippets);
      } catch (error) {
        console.error(`Failed to parse file ${file.name}:`, error);
      }
    }
  }
  
  return allSnippets;
}