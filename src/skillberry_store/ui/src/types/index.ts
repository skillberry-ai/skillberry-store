// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

export type ManifestState = 'unknown' | 'any' | 'new' | 'checked' | 'approved';

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

export interface VNFSServer {
  uuid: string;
  name: string;
  description?: string;
  version?: string;
  state?: ManifestState;
  tags?: string[];
  port?: number;
  skill_uuid?: string;
  protocol?: string;
  extra?: Record<string, any>;
  running?: boolean;
  export_path?: string;
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

export type PluginType = 'creator' | 'evaluator' | 'optimizer';

export interface PluginAction {
  label: string;
  description?: string;
  endpoint: string;
  method: string;
  params_schema: {
    type: string;
    properties: Record<string, any>;
    required?: string[];
  };
}

export interface PluginNotificationAction {
  label: string;
  endpoint: string;
  method: string;
  variant: 'primary' | 'secondary' | 'danger';
}

export interface PluginNotificationsConfig {
  poll_endpoint: string;
  item_schema: {
    title_field: string;
    body_fields: string[];
    actions: PluginNotificationAction[];
  };
}

export interface PluginUIConfig {
  icon: string;
  color: string;
  actions: PluginAction[];
  settings_schema?: Record<string, any>;
  notifications?: PluginNotificationsConfig;
}

export interface Plugin {
  slug: string;  // Entry point name used in URLs
  name: string;
  description: string;
  version: string;
  plugin_type: PluginType;
  author?: string;
  homepage?: string;
  enabled: boolean;
  status: string;
  has_router: boolean;
  has_cli: boolean;
  has_ui: boolean;
  ui_config?: PluginUIConfig;
}

export interface PluginActionResult {
  success: boolean;
  content_type?: string;
  message?: string;
  error?: string;
  data?: any;
}