// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

export type ManifestState = 'unknown' | 'any' | 'new' | 'checked' | 'approved' | 'broken';

export interface Tool {
  uuid: string;
  name: string;
  description: string;
  state?: ManifestState;
  tags?: string[];
  version?: string;
  module_name?: string;
  programming_language?: string;
  packaging_format?: string;
  dependencies?: string[];
  params?: {
    type?: string;
    properties?: Record<string, any>;
    required?: string[];
    optional?: string[];
  };
  returns?: {
    type?: string;
    description?: string;
  };
  extra?: Record<string, any>;
  author?: string;
  created_at?: string;
  modified_at?: string;
  // External MCPs feature
  mcp_url?: string | null;
  mcp_server?: string | null;
  mcp_dependencies?: string[];
  bundled_with_mcps?: boolean | null;
  broken_reason?: string | null;
}

export interface Skill {
  uuid: string;
  name: string;
  description: string;
  state?: ManifestState;
  tools?: Tool[];
  snippets?: Snippet[];
  tags?: string[];
  version?: string;
  extra?: Record<string, any>;
  author?: string;
  created_at?: string;
  modified_at?: string;
}

export interface Snippet {
  uuid: string;
  name: string;
  description: string;
  content: string;
  state?: ManifestState;
  content_type?: string;
  tags?: string[];
  version?: string;
  extra?: Record<string, any>;
  author?: string;
  created_at?: string;
  modified_at?: string;
}

export interface VMCPServer {
  uuid: string;
  name: string;
  description?: string;
  version?: string;
  state?: ManifestState;
  tags?: string[];
  port?: number;
  skill_uuid?: string;
  extra?: Record<string, any>;
  runtime?: {
    name: string;
    description: string;
    port: number;
    tools: string[];
  };
  running?: boolean;
  created_at?: string;
  modified_at?: string;
}

export interface SearchResult {
  name?: string;
  filename?: string;
  similarity_score: number;
}

export interface ExecutionResult {
  result?: any;
  error?: string;
  stdout?: string;
  stderr?: string;
  execution_time?: number;
}

export interface ApiError {
  detail: string;
  status?: number;
}