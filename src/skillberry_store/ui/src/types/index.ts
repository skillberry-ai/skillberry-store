// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

export interface Tool {
  uuid: string;
  name: string;
  description: string;
  state?: 'unknown' | 'any' | 'new' | 'checked' | 'approved';
  tags?: string[];
  version?: string;
  module_name?: string;
  programming_language?: string;
  packaging_format?: string;
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
  author?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Skill {
  uuid: string;
  name: string;
  description: string;
  tools?: Tool[];
  snippets?: Snippet[];
  tags?: string[];
  version?: string;
  author?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Snippet {
  uuid: string;
  name: string;
  description: string;
  content: string;
  state?: 'unknown' | 'any' | 'new' | 'checked' | 'approved';
  content_type?: string;
  tags?: string[];
  version?: string;
  author?: string;
  created_at?: string;
  updated_at?: string;
}

export interface VMCPServer {
  uuid: string;
  name: string;
  description?: string;
  version?: string;
  state?: 'unknown' | 'any' | 'new' | 'checked' | 'approved';
  tags?: string[];
  port?: number;
  skill_uuid?: string;
  runtime?: {
    name: string;
    description: string;
    port: number;
    tools: string[];
  };
  running?: boolean;
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