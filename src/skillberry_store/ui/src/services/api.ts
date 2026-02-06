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
    const response = await fetch(`${API_BASE}/vmcp/servers`);
    return handleResponse<VMCPServer[]>(response);
  },

  get: async (name: string): Promise<VMCPServer> => {
    const response = await fetch(`${API_BASE}/vmcp/servers/${name}`);
    return handleResponse<VMCPServer>(response);
  },

  create: async (server: Omit<VMCPServer, 'status' | 'created_at'>): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/vmcp/servers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(server),
    });
    return handleResponse<{ message: string }>(response);
  },

  delete: async (name: string): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/vmcp/servers/${name}`, {
      method: 'DELETE',
    });
    return handleResponse<{ message: string }>(response);
  },

  createFromSearch: async (
    searchTerm: string,
    name: string,
    description: string,
    port: number,
    maxResults = 10
  ): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/vmcp/servers/from-search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        search_term: searchTerm,
        name,
        description,
        port,
        max_results: maxResults,
      }),
    });
    return handleResponse<{ message: string }>(response);
  },
};

export { ApiError };