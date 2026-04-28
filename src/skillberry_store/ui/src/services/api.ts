// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import type {
  Tool,
  Skill,
  Snippet,
  VMCPServer,
  SearchResult,
  ExecutionResult,
} from '@/types';

const API_BASE = '/api';

// Anthropic Agent Skills naming format — used for skill, VMCP, external MCP,
// and tool names. Source: https://code.claude.com/docs/en/skills frontmatter.
export const STORE_NAME_PATTERN = /^[a-z0-9-]{1,64}$/;
export const STORE_NAME_HINT =
  "Lowercase letters, digits, and hyphens (-) only; 1 to 64 characters. No spaces, underscores, or uppercase. Examples: 'docs-research', 'context7', 'pdf-to-markdown'.";
export function isValidStoreName(name: string): boolean {
  return STORE_NAME_PATTERN.test(name);
}

class ApiError extends Error {
  constructor(
    message: string,
    public status?: number
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({
      detail: response.statusText,
    }));
    throw new ApiError(error.detail || 'An error occurred', response.status);
  }
  return response.json();
}

// Tools API
export const toolsApi = {
  list: async (): Promise<Tool[]> => {
    const response = await fetch(`${API_BASE}/tools/`);
    return handleResponse<Tool[]>(response);
  },

  get: async (name: string): Promise<Tool> => {
    const response = await fetch(`${API_BASE}/tools/${name}`);
    return handleResponse<Tool>(response);
  },

  getModule: async (name: string): Promise<string> => {
    const response = await fetch(`${API_BASE}/tools/${name}/module`);
    if (!response.ok) {
      throw new ApiError('Failed to fetch module', response.status);
    }
    return response.text();
  },

  create: async (moduleFile: File, toolName?: string, update = false): Promise<Tool> => {
    const formData = new FormData();
    formData.append('tool', moduleFile);
    
    // Add optional parameters as query params
    const params = new URLSearchParams();
    if (toolName) {
      params.append('tool_name', toolName);
    }
    params.append('update', String(update));

    const response = await fetch(`${API_BASE}/tools/add?${params.toString()}`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<Tool>(response);
  },

  update: async (name: string, tool: Tool): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/tools/${name}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tool),
    });
    return handleResponse<{ message: string }>(response);
  },

  updateModule: async (name: string, content: string): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/tools/${name}/module`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    return handleResponse<{ message: string }>(response);
  },

  delete: async (name: string): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/tools/${name}`, {
      method: 'DELETE',
    });
    return handleResponse<{ message: string }>(response);
  },

  execute: async (
    name: string,
    parameters?: Record<string, any>
  ): Promise<ExecutionResult> => {
    const response = await fetch(`${API_BASE}/tools/${name}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parameters || {}),
    });
    return handleResponse<ExecutionResult>(response);
  },

  search: async (
    searchTerm: string,
    maxResults = 5,
    threshold = 1
  ): Promise<SearchResult[]> => {
    const params = new URLSearchParams({
      search_term: searchTerm,
      max_number_of_results: maxResults.toString(),
      similarity_threshold: threshold.toString(),
    });
    const response = await fetch(`${API_BASE}/search/tools?${params}`);
    return handleResponse<SearchResult[]>(response);
  },
};

// Skills API
export const skillsApi = {
  list: async (): Promise<Skill[]> => {
    const response = await fetch(`${API_BASE}/skills/`);
    return handleResponse<Skill[]>(response);
  },

  get: async (name: string): Promise<Skill> => {
    const response = await fetch(`${API_BASE}/skills/${name}`);
    return handleResponse<Skill>(response);
  },

  create: async (skill: Omit<Skill, 'uuid'>): Promise<Skill> => {
    const response = await fetch(`${API_BASE}/skills/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(skill),
    });
    return handleResponse<Skill>(response);
  },

  update: async (name: string, skill: Skill): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/skills/${name}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(skill),
    });
    return handleResponse<{ message: string }>(response);
  },

  delete: async (name: string): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/skills/${name}`, {
      method: 'DELETE',
    });
    return handleResponse<{ message: string }>(response);
  },

  search: async (
    searchTerm: string,
    maxResults = 5,
    threshold = 1
  ): Promise<SearchResult[]> => {
    const params = new URLSearchParams({
      search_term: searchTerm,
      max_number_of_results: maxResults.toString(),
      similarity_threshold: threshold.toString(),
    });
    const response = await fetch(`${API_BASE}/search/skills?${params}`);
    return handleResponse<SearchResult[]>(response);
  },
};

// Snippets API
export const snippetsApi = {
  list: async (): Promise<Snippet[]> => {
    const response = await fetch(`${API_BASE}/snippets/`);
    return handleResponse<Snippet[]>(response);
  },

  get: async (name: string): Promise<Snippet> => {
    const response = await fetch(`${API_BASE}/snippets/${name}`);
    return handleResponse<Snippet>(response);
  },

  create: async (snippet: Omit<Snippet, 'uuid'>): Promise<Snippet> => {
    // Build query parameters for form data
    const params = new URLSearchParams({
      name: snippet.name,
      description: snippet.description,
      content: snippet.content,
      version: snippet.version || '1.0.0',
      content_type: snippet.content_type || 'text/plain',
      state: snippet.state || 'approved',
    });
    
    // Add tags as separate parameters
    if (snippet.tags && Array.isArray(snippet.tags)) {
      snippet.tags.forEach(tag => params.append('tags', tag));
    }
    
    // Add extra field as JSON string if present
    if (snippet.extra && Object.keys(snippet.extra).length > 0) {
      params.append('extra', JSON.stringify(snippet.extra));
    }
    
    const response = await fetch(`${API_BASE}/snippets/?${params}`, {
      method: 'POST',
    });
    return handleResponse<Snippet>(response);
  },

  update: async (
    name: string,
    snippet: Snippet
  ): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/snippets/${name}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(snippet),
    });
    return handleResponse<{ message: string }>(response);
  },

  delete: async (name: string): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/snippets/${name}`, {
      method: 'DELETE',
    });
    return handleResponse<{ message: string }>(response);
  },

  search: async (
    searchTerm: string,
    maxResults = 5,
    threshold = 1
  ): Promise<SearchResult[]> => {
    const params = new URLSearchParams({
      search_term: searchTerm,
      max_number_of_results: maxResults.toString(),
      similarity_threshold: threshold.toString(),
    });
    const response = await fetch(`${API_BASE}/search/snippets?${params}`);
    return handleResponse<SearchResult[]>(response);
  },
};

// VMCP Servers API
export const vmcpApi = {
  list: async (): Promise<VMCPServer[]> => {
    const response = await fetch(`${API_BASE}/vmcp_servers/`);
    const data = await handleResponse<{ virtual_mcp_servers: Record<string, VMCPServer> }>(response);
    // Convert the object to an array
    return Object.values(data.virtual_mcp_servers);
  },

  get: async (name: string): Promise<VMCPServer> => {
    const response = await fetch(`${API_BASE}/vmcp_servers/${name}`);
    return handleResponse<VMCPServer>(response);
  },

  create: async (
    server: Omit<VMCPServer, 'uuid' | 'runtime' | 'running'>
  ): Promise<{ message: string; name: string; uuid: string; port: number }> => {
    const params = new URLSearchParams();
    params.append('name', server.name);
    if (server.description) params.append('description', server.description);
    if (server.version) params.append('version', server.version);
    if (server.state) params.append('state', server.state);
    if (server.port) params.append('port', server.port.toString());
    if (server.skill_uuid) params.append('skill_uuid', server.skill_uuid);
    if (server.tags) {
      server.tags.forEach(tag => params.append('tags', tag));
    }
    // Add extra field as JSON string if present
    if (server.extra && Object.keys(server.extra).length > 0) {
      params.append('extra', JSON.stringify(server.extra));
    }

    const response = await fetch(`${API_BASE}/vmcp_servers/?${params}`, {
      method: 'POST',
    });
    return handleResponse<{ message: string; name: string; uuid: string; port: number }>(response);
  },

  update: async (
    name: string,
    server: Partial<VMCPServer>
  ): Promise<{ message: string }> => {
    const params = new URLSearchParams();
    if (server.description) params.append('description', server.description);
    if (server.version) params.append('version', server.version);
    if (server.state) params.append('state', server.state);
    if (server.port) params.append('port', server.port.toString());
    if (server.skill_uuid) params.append('skill_uuid', server.skill_uuid);
    if (server.tags) {
      server.tags.forEach(tag => params.append('tags', tag));
    }

    const response = await fetch(`${API_BASE}/vmcp_servers/${name}?${params}`, {
      method: 'PUT',
    });
    return handleResponse<{ message: string }>(response);
  },

  delete: async (name: string): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/vmcp_servers/${name}`, {
      method: 'DELETE',
    });
    return handleResponse<{ message: string }>(response);
  },

  start: async (name: string): Promise<{ message: string; port: number }> => {
    const response = await fetch(`${API_BASE}/vmcp_servers/${name}/start`, {
      method: 'POST',
    });
    return handleResponse<{ message: string; port: number }>(response);
  },

  search: async (
    searchTerm: string,
    maxResults = 5,
    threshold = 1
  ): Promise<SearchResult[]> => {
    const params = new URLSearchParams({
      search_term: searchTerm,
      max_number_of_results: maxResults.toString(),
      similarity_threshold: threshold.toString(),
    });
    const response = await fetch(`${API_BASE}/search/vmcp_servers?${params}`);
    return handleResponse<SearchResult[]>(response);
  },
};

// External MCPs API — manage imported MCP servers the store consumes
export type ExternalMCPTransport = 'stdio' | 'sse' | 'http';

export interface ExternalMCPConfig {
  name: string;
  transport: ExternalMCPTransport;
  command?: string | null;
  args?: string[];
  env?: Record<string, string>;
  url?: string | null;
  headers?: Record<string, string>;
  enabled?: boolean;
}

export interface ExternalMCPStatus {
  name: string;
  transport: ExternalMCPTransport;
  enabled: boolean;
  status: 'running' | 'stopped' | 'error' | 'starting';
  last_error: string | null;
  tool_count: number;
  config: ExternalMCPConfig & { created_at?: string; modified_at?: string };
}

export interface ExternalMCPStartResult {
  name: string;
  status: string;
  error?: string;
  reconcile?: { added: string[]; updated: string[]; removed: string[] };
  health?: { broken: Array<{ name: string; reason: string }>; unbroken: string[]; iterations: number };
}

export const externalMcpsApi = {
  list: async (): Promise<ExternalMCPStatus[]> => {
    const response = await fetch(`${API_BASE}/external-mcps`);
    return handleResponse<ExternalMCPStatus[]>(response);
  },

  get: async (name: string): Promise<ExternalMCPStatus> => {
    const response = await fetch(`${API_BASE}/external-mcps/${encodeURIComponent(name)}`);
    return handleResponse<ExternalMCPStatus>(response);
  },

  // Accepts any of the five input shapes — pass raw JSON straight through.
  create: async (
    config: unknown,
  ): Promise<{ count: number; results: ExternalMCPStartResult[] }> => {
    const response = await fetch(`${API_BASE}/external-mcps`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    return handleResponse<{ count: number; results: ExternalMCPStartResult[] }>(response);
  },

  remove: async (name: string): Promise<{
    name: string;
    removed_primitives: string[];
    health?: { broken: Array<{ name: string; reason: string }>; unbroken: string[] };
  }> => {
    const response = await fetch(`${API_BASE}/external-mcps/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    });
    return handleResponse(response);
  },

  restart: async (name: string): Promise<ExternalMCPStartResult> => {
    const response = await fetch(`${API_BASE}/external-mcps/${encodeURIComponent(name)}/restart`, {
      method: 'POST',
    });
    return handleResponse<ExternalMCPStartResult>(response);
  },

  listRemoteTools: async (
    name: string,
  ): Promise<Array<{ name: string; description: string; inputSchema: Record<string, unknown> }>> => {
    const response = await fetch(
      `${API_BASE}/external-mcps/${encodeURIComponent(name)}/remote-tools`,
    );
    return handleResponse(response);
  },

  dependents: async (name: string): Promise<{ name: string; dependents: string[] }> => {
    const response = await fetch(
      `${API_BASE}/external-mcps/${encodeURIComponent(name)}/dependents`,
    );
    return handleResponse(response);
  },
};

// Per-tool: toggle bundled_with_mcps
export const toolsExtrasApi = {
  setBundledWithMcps: async (
    name: string,
    value: boolean,
  ): Promise<{ name: string; bundled_with_mcps: boolean }> => {
    const response = await fetch(
      `${API_BASE}/tools/${encodeURIComponent(name)}/bundled-with-mcps?value=${value}`,
      { method: 'PUT' },
    );
    return handleResponse(response);
  },
};

// Bulk-add tools to a skill from their MCP association
export type BulkAddMode = 'primitives' | 'related' | 'bundled_related';

export interface BulkAddResult {
  skill: string;
  mode: BulkAddMode;
  requested_mcps: string[];
  added: Array<{ name: string; uuid: string }>;
  skipped_duplicate: string[];
  skipped_broken: Array<{ name: string; reason: string }>;
  skipped_unbundled: string[];
}

export const skillsExtrasApi = {
  bulkAddFromMcps: async (
    skillName: string,
    body: { mcps: string[]; mode: BulkAddMode },
  ): Promise<BulkAddResult> => {
    const response = await fetch(
      `${API_BASE}/skills/${encodeURIComponent(skillName)}/bulk-add-tools-from-mcps`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
    );
    return handleResponse(response);
  },
};

// Admin API
export interface ServerInfo {
  host: string;
  port: number;
  agent_mcp_port: number;
  agent_mcp_url: string | null;
  control_mcp_url: string;
  api_docs: string;
}

export const adminApi = {
  getServerInfo: async (): Promise<ServerInfo> => {
    const response = await fetch(`${API_BASE}/admin/server-info`);
    return handleResponse<ServerInfo>(response);
  },
};

// Plugins API
export interface PluginInfo {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  requires_restart: boolean;
  ui_manifest: {
    routes?: Array<{ path: string; component: string }>;
    nav_items?: Array<{ id: string; label: string; path: string }>;
    slots?: Record<string, Array<{ component: string }>>;
  } | null;
}

export interface PluginToggleResponse {
  plugin_id: string;
  enabled: boolean;
  restart_required: boolean;
}

export const pluginsApi = {
  list: async (): Promise<PluginInfo[]> => {
    const response = await fetch(`${API_BASE}/plugins`);
    const data = await handleResponse<{ plugins: PluginInfo[] }>(response);
    return data.plugins;
  },

  enable: async (id: string): Promise<PluginToggleResponse> => {
    const response = await fetch(`${API_BASE}/plugins/${id}/enable`, { method: 'POST' });
    return handleResponse<PluginToggleResponse>(response);
  },

  disable: async (id: string): Promise<PluginToggleResponse> => {
    const response = await fetch(`${API_BASE}/plugins/${id}/disable`, { method: 'POST' });
    return handleResponse<PluginToggleResponse>(response);
  },
};

export { ApiError };