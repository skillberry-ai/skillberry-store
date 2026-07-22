// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { toolsApi, skillsApi, snippetsApi, vmcpApi, vnfsApi } from '@/services/api';
import type { Tool, Skill, Snippet, VMCPServer, VNFSServer } from '@/types';
import JSZip from 'jszip';

export interface ImportResult {
  importedCount: number;
  failures: { name: string; error: string }[];
}

/**
 * Export tools with their module content.
 *
 * The input list may have been fetched with a narrow field-selection
 * preset, so the full manifest is re-fetched via ``toolsApi.get`` (which
 * requests ``?fields=full``) before the module content is attached.
 */
export async function exportTools(tools: Tool[]): Promise<(Tool & { module_content?: string })[]> {
  return await Promise.all(
    tools.map(async (tool) => {
      let full: Tool = tool;
      try {
        full = await toolsApi.get(tool.uuid!);
      } catch (error) {
        console.error(`Failed to fetch full tool ${tool.name}:`, error);
      }
      try {
        const module = await toolsApi.getModule(full.name);
        return { ...full, module_content: module };
      } catch (error) {
        console.error(`Failed to fetch module for ${full.name}:`, error);
        return { ...full, module_content: undefined };
      }
    })
  );
}

/**
 * Import tools from exported data
 */
export async function importTools(tools: (Tool & { module_content?: string })[]): Promise<ImportResult> {
  let importedCount = 0;
  const failures: { name: string; error: string }[] = [];

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
      failures.push({ name: tool.name, error: error.message || String(error) });
    }
  }

  return { importedCount, failures };
}

/**
 * Export snippets. The list-page items are fetched with a narrow preset
 * (no ``content``), so each snippet is re-fetched via ``snippetsApi.get``
 * to obtain the full manifest before export.
 */
export async function exportSnippets(snippets: Snippet[]): Promise<Snippet[]> {
  return await Promise.all(
    snippets.map(async (s) => {
      try {
        return await snippetsApi.get(s.uuid!);
      } catch (error) {
        console.error(`Failed to fetch full snippet ${s.name}:`, error);
        return s;
      }
    })
  );
}

/**
 * Import snippets from exported data
 */
export async function importSnippets(snippets: Snippet[]): Promise<ImportResult> {
  let importedCount = 0;
  const failures: { name: string; error: string }[] = [];

  for (const snippet of snippets) {
    try {
      await snippetsApi.create(snippet);
      importedCount++;
    } catch (error: any) {
      failures.push({ name: snippet.name, error: error.message || String(error) });
    }
  }

  return { importedCount, failures };
}

/**
 * Export skills with tool and snippet UUIDs (matching backend format).
 * Each skill is fetched via ``skillsApi.get`` to obtain the full
 * manifest (list-page items use a narrow preset).
 */
export async function exportSkills(skills: Skill[]): Promise<any[]> {
  const full = await Promise.all(
    skills.map(async (skill) => {
      try {
        return await skillsApi.get(skill.uuid!);
      } catch (error) {
        console.error(`Failed to fetch full skill ${skill.name}:`, error);
        return skill as any;
      }
    })
  );
  return full.map(skill => ({
    name: skill.name,
    version: skill.version || '1.0.0',
    description: skill.description,
    tags: skill.tags || [],
    tool_uuids: skill.tool_uuids || [],
    snippet_uuids: skill.snippet_uuids || [],
  }));
}

/**
 * Import skills from exported data using query parameters
 */
export async function importSkills(skills: any[]): Promise<ImportResult> {
  let importedCount = 0;
  const failures: { name: string; error: string }[] = [];

  for (const skill of skills) {
    try {
      // Validate required fields
      if (!skill.name || !skill.description) {
        failures.push({
          name: skill.name || '(unnamed)',
          error: 'Missing required fields: name or description',
        });
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
        let errorText: string;
        try {
          const body = await response.json();
          errorText = body.detail
            ? (Array.isArray(body.detail)
              ? body.detail.map((e: any) => e.msg || JSON.stringify(e)).join('; ')
              : String(body.detail))
            : response.statusText;
        } catch {
          errorText = response.statusText;
        }
        failures.push({ name: skill.name, error: errorText });
      }
    } catch (error: any) {
      failures.push({ name: skill.name, error: error.message || String(error) });
    }
  }

  return { importedCount, failures };
}

/**
 * Export VMCP servers. Re-fetched via ``vmcpApi.get`` so the export
 * contains every field (list-page items use a narrow preset).
 */
export async function exportVMCPServers(servers: VMCPServer[]): Promise<VMCPServer[]> {
  return await Promise.all(
    servers.map(async (s) => {
      try {
        return await vmcpApi.get(s.uuid!);
      } catch (error) {
        console.error(`Failed to fetch full vmcp server ${s.name}:`, error);
        return s;
      }
    })
  );
}

/**
 * Import VMCP servers from exported data
 */
export async function importVMCPServers(servers: VMCPServer[]): Promise<ImportResult> {
  let importedCount = 0;
  const failures: { name: string; error: string }[] = [];

  for (const server of servers) {
    try {
      await vmcpApi.create(server);
      importedCount++;
    } catch (error: any) {
      failures.push({ name: server.name, error: error.message || String(error) });
    }
  }

  return { importedCount, failures };
}

/**
 * Download data as JSON file (legacy, uncompressed)
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
 * Export vNFS servers. Re-fetched via ``vnfsApi.get`` so the export
 * contains every field (list-page items use a narrow preset).
 */
export async function exportVNFSServers(servers: VNFSServer[]): Promise<VNFSServer[]> {
  return await Promise.all(
    servers.map(async (s) => {
      try {
        return await vnfsApi.get(s.uuid!);
      } catch (error) {
        console.error(`Failed to fetch full vnfs server ${s.name}:`, error);
        return s;
      }
    })
  );
}

/**
 * Import vNFS servers from exported data
 */
export async function importVNFSServers(servers: VNFSServer[]): Promise<ImportResult> {
  let importedCount = 0;
  const failures: { name: string; error: string }[] = [];

  for (const server of servers) {
    try {
      await vnfsApi.create(server);
      importedCount++;
    } catch (error: any) {
      failures.push({ name: server.name, error: error.message || String(error) });
    }
  }

  return { importedCount, failures };
}

// Made with Bob
