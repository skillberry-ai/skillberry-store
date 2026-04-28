// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0
//
// Runspace plugin client API. The backend endpoints live under the runspace
// plugin router; main services/api.ts has no knowledge of them.

const API_BASE = '/api';

export interface AiSettingsEnvVar {
  key: string;
  value: string;
}

export interface AiSettings {
  runspace_url: string;
  env_vars: AiSettingsEnvVar[];
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'An error occurred');
  }
  return response.json();
}

export const runspaceSettingsApi = {
  get: async (): Promise<AiSettings> => {
    const response = await fetch(`${API_BASE}/ai-settings`);
    return handleResponse<AiSettings>(response);
  },

  save: async (settings: AiSettings): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE}/ai-settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    return handleResponse<{ message: string }>(response);
  },
};

export const runspaceAgentApi = {
  buildStoreRequest: async (prompt: string, contextFiles?: File[]): Promise<Record<string, any>> => {
    const formData = new FormData();
    formData.append('prompt', prompt);
    if (contextFiles) {
      for (const file of contextFiles) {
        formData.append('context_files', file);
      }
    }
    const response = await fetch(`${API_BASE}/agent/store-request`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<Record<string, any>>(response);
  },
};

export const runspaceSkillApi = {
  exportAgentRequest: async (name: string): Promise<Record<string, any>> => {
    const response = await fetch(`${API_BASE}/skills/${name}/export-agent-request`, {
      method: 'POST',
    });
    return handleResponse<Record<string, any>>(response);
  },
};

export const DEFAULT_RUNSPACE_URL = 'http://localhost:6767';

export function envVarsToRecord(vars: AiSettingsEnvVar[]): Record<string, string> {
  const record: Record<string, string> = {};
  for (const v of vars) {
    const key = v.key.trim();
    const value = v.value.trim();
    if (key && value) {
      record[key] = value;
    }
  }
  return record;
}
