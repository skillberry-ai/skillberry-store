// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import type {
  Tool,
  Skill,
  Snippet,
  VMCPServer,
  VNFSServer,
  SearchResult,
  ExecutionResult,
  Plugin,
  PluginActionResult,
} from '@/types';

const API_BASE = '/api';

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
    const detail = error.detail;
    const message = Array.isArray(detail)
      ? detail.map((e: any) => e.msg || JSON.stringify(e)).join('; ')
      : typeof detail === 'string'
        ? detail
        : JSON.stringify(detail);
    throw new ApiError(message || 'An error occurred', response.status);
  }
  return response.json();
}

// Tools API
export const toolsApi = {
  list: async (): Promise<Tool[]> => {
    const response = await fetch(`${API_BASE}/tools/`);
    return handleResponse<Tool[]>(response);
  },

  get: async (uuid: string): Promise<Tool> => {
    const response = await fetch(`${API_BASE}/tools/${uuid}`);
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

  update: async (uuid: string, tool: Tool): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/tools/${uuid}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tool),
    });
    return handleResponse<{ message: string }>(response);
  },

  delete: async (uuid: string): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/tools/${uuid}`, {
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

  get: async (uuid: string): Promise<Skill> => {
    const response = await fetch(`${API_BASE}/skills/${uuid}`);
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

  delete: async (
    name: string,
    options?: { deleteTools?: boolean; deleteSnippets?: boolean }
  ): Promise<{ message: string }> => {
    const params = new URLSearchParams();
    if (options?.deleteTools) params.set('delete_tools', 'true');
    if (options?.deleteSnippets) params.set('delete_snippets', 'true');
    const query = params.toString() ? `?${params}` : '';
    const response = await fetch(`${API_BASE}/skills/${name}${query}`, {
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

  get: async (uuid: string): Promise<Snippet> => {
    const response = await fetch(`${API_BASE}/snippets/${uuid}`);
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
    uuid: string,
    snippet: Snippet
  ): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/snippets/${uuid}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(snippet),
    });
    return handleResponse<{ message: string }>(response);
  },

  delete: async (uuid: string): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/snippets/${uuid}`, {
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

  get: async (uuid: string): Promise<VMCPServer> => {
    const response = await fetch(`${API_BASE}/vmcp_servers/${uuid}`);
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
    uuid: string,
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

    const response = await fetch(`${API_BASE}/vmcp_servers/${uuid}?${params}`, {
      method: 'PUT',
    });
    return handleResponse<{ message: string }>(response);
  },

  delete: async (uuid: string): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/vmcp_servers/${uuid}`, {
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

// vNFS Servers API
export const vnfsApi = {
  list: async (): Promise<VNFSServer[]> => {
    const response = await fetch(`${API_BASE}/vnfs_servers/`);
    const data = await handleResponse<{ virtual_nfs_servers: Record<string, VNFSServer> }>(response);
    return Object.values(data.virtual_nfs_servers);
  },

  get: async (uuid: string): Promise<VNFSServer> => {
    const response = await fetch(`${API_BASE}/vnfs_servers/${uuid}`);
    return handleResponse<VNFSServer>(response);
  },

  create: async (
    server: Omit<VNFSServer, 'uuid' | 'running' | 'export_path'>
  ): Promise<{ message: string; name: string; uuid: string; port: number }> => {
    const params = new URLSearchParams();
    params.append('name', server.name);
    if (server.description) params.append('description', server.description);
    if (server.version) params.append('version', server.version);
    if (server.state) params.append('state', server.state);
    if (server.port) params.append('port', server.port.toString());
    if (server.skill_uuid) params.append('skill_uuid', server.skill_uuid);
    if (server.protocol) params.append('protocol', server.protocol);
    if (server.tags) {
      server.tags.forEach(tag => params.append('tags', tag));
    }
    if (server.extra && Object.keys(server.extra).length > 0) {
      params.append('extra', JSON.stringify(server.extra));
    }
    const response = await fetch(`${API_BASE}/vnfs_servers/?${params}`, { method: 'POST' });
    return handleResponse<{ message: string; name: string; uuid: string; port: number }>(response);
  },

  update: async (
    uuid: string,
    server: Partial<VNFSServer>
  ): Promise<{ message: string }> => {
    const params = new URLSearchParams();
    if (server.description) params.append('description', server.description);
    if (server.version) params.append('version', server.version);
    if (server.state) params.append('state', server.state);
    if (server.port) params.append('port', server.port.toString());
    if (server.skill_uuid) params.append('skill_uuid', server.skill_uuid);
    if (server.protocol) params.append('protocol', server.protocol);
    if (server.tags) {
      server.tags.forEach(tag => params.append('tags', tag));
    }
    const response = await fetch(`${API_BASE}/vnfs_servers/${uuid}?${params}`, { method: 'PUT' });
    return handleResponse<{ message: string }>(response);
  },

  delete: async (uuid: string): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/vnfs_servers/${uuid}`, { method: 'DELETE' });
    return handleResponse<{ message: string }>(response);
  },

  start: async (name: string): Promise<{ message: string; port: number }> => {
    const response = await fetch(`${API_BASE}/vnfs_servers/${name}/start`, { method: 'POST' });
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
    const response = await fetch(`${API_BASE}/search/vnfs_servers?${params}`);
    return handleResponse<SearchResult[]>(response);
  },
};

// Plugins API
export const pluginsApi = {
  list: async (): Promise<Plugin[]> => {
    const response = await fetch(`${API_BASE}/plugins/`);
    return handleResponse<Plugin[]>(response);
  },

  get: async (name: string): Promise<Plugin> => {
    const response = await fetch(`${API_BASE}/plugins/${name}`);
    return handleResponse<Plugin>(response);
  },

  executeAction: async (
    pluginName: string,
    action: string,
    params: Record<string, any>
  ): Promise<PluginActionResult> => {
    const response = await fetch(`${API_BASE}/plugins/${pluginName}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    return handleResponse<PluginActionResult>(response);
  },
};

export { ApiError };