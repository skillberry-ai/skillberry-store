// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

/**
 * Exporter for converting Skillberry skills to Anthropic skill format
 */

import JSZip from 'jszip';
import type { Skill, Tool, Snippet } from '@/types';

interface ExportOptions {
  skill: Skill;
  tools: Tool[];
  snippets: Snippet[];
  toolModules?: Array<{ name: string; module: string }>;
}

interface FileStructure {
  [path: string]: string;
}

/**
 * Extract file path from tags
 * Looks for tags in format "file:path/to/file.ext"
 */
function extractFilePathFromTags(tags?: string[]): string | null {
  if (!tags) return null;
  
  const fileTag = tags.find(tag => tag.startsWith('file:'));
  if (fileTag) {
    return fileTag.substring(5); // Remove "file:" prefix
  }
  
  return null;
}

/**
 * Generate SKILL.md content with frontmatter
 */
function generateSkillMd(skill: Skill, hasFileStructure: boolean, snippets: Snippet[]): string {
  let content = '---\n';
  content += `name: ${skill.name}\n`;
  content += `description: ${skill.description || 'No description provided'}\n`;
  
  // Check if there's a LICENSE.txt file in snippets
  const licenseSnippet = snippets.find(s => {
    const filePath = extractFilePathFromTags(s.tags);
    return filePath && filePath.toLowerCase().includes('license');
  });
  
  if (licenseSnippet) {
    content += `license: Proprietary. LICENSE.txt has complete terms\n`;
  }
  
  content += '---\n\n';
  
  if (!hasFileStructure) {
    content += `# ${skill.name}\n\n`;
    content += `${skill.description || 'No description provided'}\n\n`;
  }
  
  return content;
}

/**
 * Determine programming language from tool
 */
function getToolLanguage(tool: Tool): 'python' | 'bash' | 'other' {
  const lang = tool.programming_language?.toLowerCase();
  if (lang === 'python' || lang === 'py') return 'python';
  if (lang === 'bash' || lang === 'sh' || lang === 'shell') return 'bash';
  return 'other';
}

/**
 * Get file extension for tool based on language
 */
function getToolExtension(tool: Tool): string {
  const lang = getToolLanguage(tool);
  if (lang === 'python') return '.py';
  if (lang === 'bash') return '.sh';
  return '.txt';
}

/**
 * Normalize file path by removing skill name prefix if present
 */
function normalizeFilePath(filePath: string, skillName: string): string {
  // Remove leading skill name directory if present
  const skillPrefix = `${skillName}/`;
  if (filePath.startsWith(skillPrefix)) {
    return filePath.substring(skillPrefix.length);
  }
  return filePath;
}

/**
 * Build file structure from snippets with file: tags
 */
function buildFileStructureFromSnippets(snippets: Snippet[], skillName: string): FileStructure {
  const files: FileStructure = {};
  
  for (const snippet of snippets) {
    const filePath = extractFilePathFromTags(snippet.tags);
    if (filePath) {
      // Normalize the file path to remove skill name prefix
      const normalizedPath = normalizeFilePath(filePath, skillName);
      
      // Group snippets by file path
      if (files[normalizedPath]) {
        files[normalizedPath] += '\n\n' + snippet.content;
      } else {
        files[normalizedPath] = snippet.content;
      }
    }
  }
  
  return files;
}

/**
 * Build file structure from tools with file: tags
 */
function buildFileStructureFromTools(
  tools: Tool[],
  skillName: string,
  toolModules?: Array<{ name: string; module: string }>
): FileStructure {
  const files: FileStructure = {};
  
  for (const tool of tools) {
    const filePath = extractFilePathFromTags(tool.tags);
    if (filePath) {
      // Normalize the file path to remove skill name prefix
      const normalizedPath = normalizeFilePath(filePath, skillName);
      
      // Get module content from toolModules array
      const toolModule = toolModules?.find(tm => tm.name === tool.name);
      const content = toolModule?.module || '';
      
      // Group tools by file path
      if (files[normalizedPath]) {
        files[normalizedPath] += '\n\n' + content;
      } else {
        files[normalizedPath] = content;
      }
    }
  }
  
  return files;
}

/**
 * Export snippets without file: tags to SKILL.md
 */
function exportSnippetsToSkillMd(snippets: Snippet[]): string {
  let content = '';
  
  for (const snippet of snippets) {
    const filePath = extractFilePathFromTags(snippet.tags);
    if (!filePath) {
      // No file path, add to SKILL.md
      content += '\n\n' + snippet.content;
    }
  }
  
  return content;
}

/**
 * Export tools without file: tags to scripts folder
 */
function exportToolsToScripts(
  tools: Tool[],
  skillName: string,
  toolModules?: Array<{ name: string; module: string }>
): FileStructure {
  const files: FileStructure = {};
  
  for (const tool of tools) {
    const filePath = extractFilePathFromTags(tool.tags);
    if (!filePath) {
      // No file path, create in scripts folder
      const ext = getToolExtension(tool);
      const fileName = `scripts/${tool.name}${ext}`;
      // Get module content from toolModules array
      const toolModule = toolModules?.find(tm => tm.name === tool.name);
      const content = toolModule?.module || '';
      files[fileName] = content;
    }
  }
  
  return files;
}

/**
 * Merge file structures
 */
function mergeFileStructures(...structures: FileStructure[]): FileStructure {
  const merged: FileStructure = {};
  
  for (const structure of structures) {
    for (const [path, content] of Object.entries(structure)) {
      if (merged[path]) {
        merged[path] += '\n\n' + content;
      } else {
        merged[path] = content;
      }
    }
  }
  
  return merged;
}

/**
 * Export skill to Anthropic format as a ZIP file
 */
export async function exportSkillToAnthropicFormat(options: ExportOptions): Promise<Blob> {
  const { skill, tools, snippets, toolModules } = options;
  const zip = new JSZip();
  
  // Create root folder with skill name
  const rootFolder = zip.folder(skill.name);
  if (!rootFolder) {
    throw new Error('Failed to create root folder');
  }
  
  // Build file structures from tags
  const snippetFiles = buildFileStructureFromSnippets(snippets, skill.name);
  const toolFiles = buildFileStructureFromTools(tools, skill.name, toolModules);
  const scriptFiles = exportToolsToScripts(tools, skill.name, toolModules);
  
  // Merge all file structures
  const allFiles = mergeFileStructures(snippetFiles, toolFiles, scriptFiles);
  
  // Check if we have any file structure
  const hasFileStructure = Object.keys(allFiles).length > 0;
  
  // Generate SKILL.md
  let skillMdContent = generateSkillMd(skill, hasFileStructure, snippets);
  
  // Add snippets without file: tags to SKILL.md
  const additionalSnippets = exportSnippetsToSkillMd(snippets);
  if (additionalSnippets) {
    skillMdContent += additionalSnippets;
  }
  
  // Check if SKILL.md already exists in allFiles (from snippets with file:SKILL.md tag)
  const hasSKILLmdInFiles = Object.keys(allFiles).some(path =>
    path.toUpperCase() === 'SKILL.MD' || path.toUpperCase().endsWith('/SKILL.MD')
  );
  
  // Only add SKILL.md if it doesn't already exist in the file structure
  if (!hasSKILLmdInFiles) {
    rootFolder.file('SKILL.md', skillMdContent);
  } else {
    // If SKILL.md exists, prepend frontmatter to it
    for (const [path, content] of Object.entries(allFiles)) {
      if (path.toUpperCase() === 'SKILL.MD' || path.toUpperCase().endsWith('/SKILL.MD')) {
        allFiles[path] = skillMdContent + content;
        break;
      }
    }
  }
  
  // Add all files to the zip with trailing newline
  for (const [filePath, content] of Object.entries(allFiles)) {
    // Ensure content ends with a single newline (standard for text files)
    const normalizedContent = content.endsWith('\n') ? content : content + '\n';
    rootFolder.file(filePath, normalizedContent);
  }
  
  // Generate the ZIP file
  const blob = await zip.generateAsync({ type: 'blob' });
  return blob;
}

/**
 * Download a blob as a file
 */
export function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export and download skill as Anthropic format ZIP
 */
export async function exportAndDownloadSkill(options: ExportOptions): Promise<void> {
  const blob = await exportSkillToAnthropicFormat(options);
  const fileName = `${options.skill.name}.zip`;
  downloadBlob(blob, fileName);
}