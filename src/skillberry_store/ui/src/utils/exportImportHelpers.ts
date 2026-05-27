// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { toolsApi, snippetsApi, vmcpApi, vnfsApi } from '@/services/api';
import type { Tool, Snippet, Skill, VMCPServer, VNFSServer } from '@/types';

/**
 * Export tools with their module content
 */
export async function exportTools(tools: Tool[]): Promise<(Tool & { module_content?: string })[]> {
  return await Promise.all(
    tools.map(async (tool) => {
      try {
        const module = await toolsApi.getModule(tool.name);
        return { ...tool, module_content: module };
      } catch (error) {
        console.error(`Failed to fetch module for ${tool.name}:`, error);
        return { ...tool, module_content: undefined };
      }
    })
  );
}

/**
 * Import tools from exported data
 */
export async function importTools(tools: (Tool & { module_content?: string })[]): Promise<number> {
  let importedCount = 0;
  
  for (const tool of tools) {
    try {
      if (tool.module_content) {
        // Determine file extension and MIME type based on programming language
        const lang = tool.programming_language?.toLowerCase() || 'python';
        const ext = lang === 'python' ? '.py' : lang === 'bash' || lang === 'sh' ? '.sh' : '.txt';
        const mimeType = lang === 'python' ? 'text/x-python' : 'text/plain';
        
        // Create a File object from the module content
        const moduleBlob = new Blob([tool.module_content], { type: mimeType });
        const moduleFile = new File([moduleBlob], `${tool.name}${ext}`, { type: mimeType });
        
        // Create the tool with the module file (this will auto-parse and create the tool)
        await toolsApi.create(moduleFile, tool.name, true);
        
        // Update the tool with all the original metadata to preserve description, tags, params, returns, etc.
        // Remove module_content from the update payload as it's not part of the Tool schema
        const { module_content, ...toolMetadata } = tool;
        await toolsApi.update(tool.name, toolMetadata as Tool);
        
        importedCount++;
      }
    } catch (error: any) {
      console.error(`Failed to import tool ${tool.name}:`, error);
    }
  }
  
  return importedCount;
}

/**
 * Export snippets (they already contain content in the schema)
 */
export function exportSnippets(snippets: Snippet[]): Snippet[] {
  return snippets;
}

/**
 * Import snippets from exported data
 */
export async function importSnippets(snippets: Snippet[]): Promise<number> {
  let importedCount = 0;
  
  for (const snippet of snippets) {
    try {
      await snippetsApi.create(snippet);
      importedCount++;
    } catch (error: any) {
      console.error(`Failed to import snippet ${snippet.name}:`, error);
    }
  }
  
  return importedCount;
}

/**
 * Export skills with tool and snippet UUIDs (matching backend format)
 */
export function exportSkills(skills: any[]): any[] {
  return skills.map(skill => {
    // If the skill already has tool_uuids and snippet_uuids (from backend), use them
    // Otherwise, extract from the populated tools and snippets arrays
    const tool_uuids = skill.tool_uuids || skill.tools?.map((t: any) => t.uuid) || [];
    const snippet_uuids = skill.snippet_uuids || skill.snippets?.map((s: any) => s.uuid) || [];
    
    return {
      name: skill.name,
      version: skill.version || '1.0.0',
      description: skill.description,
      tags: skill.tags || [],
      tool_uuids,
      snippet_uuids,
    };
  });
}

/**
 * Import skills from exported data using query parameters
 */
export async function importSkills(skills: any[]): Promise<number> {
  let importedCount = 0;
  
  for (const skill of skills) {
    try {
      // Validate required fields
      if (!skill.name || !skill.description) {
        console.error(`Skipping skill with missing name or description:`, skill);
        continue;
      }

      // Build query parameters
      const params = new URLSearchParams({
        name: skill.name,
        version: skill.version || '1.0.0',
        description: skill.description,
      });
      
      // Add tags
      if (skill.tags && Array.isArray(skill.tags)) {
        skill.tags.forEach((tag: string) => params.append('tags', tag));
      }
      
      // Add tool and snippet UUIDs
      if (skill.tool_uuids && Array.isArray(skill.tool_uuids)) {
        skill.tool_uuids.forEach((uuid: string) => params.append('tool_uuids', uuid));
      }
      if (skill.snippet_uuids && Array.isArray(skill.snippet_uuids)) {
        skill.snippet_uuids.forEach((uuid: string) => params.append('snippet_uuids', uuid));
      }
      
      // Call API with query parameters
      const response = await fetch(`/api/skills/?${params}`, {
        method: 'POST',
      });
      
      if (response.ok) {
        importedCount++;
      } else {
        const errorText = await response.text();
        console.error(`Failed to import skill ${skill.name}: ${errorText}`);
      }
    } catch (error: any) {
      console.error(`Failed to import skill ${skill.name}:`, error);
    }
  }
  
  return importedCount;
}

/**
 * Export VMCP servers
 */
export function exportVMCPServers(servers: VMCPServer[]): VMCPServer[] {
  return servers;
}

/**
 * Import VMCP servers from exported data
 */
export async function importVMCPServers(servers: VMCPServer[]): Promise<number> {
  let importedCount = 0;
  
  for (const server of servers) {
    try {
      await vmcpApi.create(server);
      importedCount++;
    } catch (error: any) {
      console.error(`Failed to import VMCP server ${server.name}:`, error);
    }
  }
  
  return importedCount;
}

/**
 * Download data as JSON file
 */
export function downloadJSON(data: any, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export vNFS servers
 */
export function exportVNFSServers(servers: VNFSServer[]): VNFSServer[] {
  return servers;
}

/**
 * Import vNFS servers from exported data
 */
export async function importVNFSServers(servers: VNFSServer[]): Promise<number> {
  let importedCount = 0;
  for (const server of servers) {
    try {
      await vnfsApi.create(server);
      importedCount++;
    } catch (error: any) {
      console.error(`Failed to import vNFS server ${server.name}:`, error);
    }
  }
  return importedCount;
}

// Made with Bob
