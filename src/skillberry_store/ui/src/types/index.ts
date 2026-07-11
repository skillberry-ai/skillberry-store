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
  // Slim list-view responses expose tool_uuids/snippet_uuids only.
  // Detail (GET /skills/{uuid}) additionally populates tools/snippets.
  tool_uuids?: string[];
  snippet_uuids?: string[];
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
  // `content` is absent on slim list-view responses (fields=list); the
  // detail endpoint (GET /snippets/{uuid}) still returns it.
  content?: string;
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

export interface PluginAsyncActionConfig {
  // Endpoint polled while a job is pending. `{job_id}` is interpolated from the
  // submit result's `data.job_id`.
  status_endpoint: string;
  poll_interval_ms?: number; // default 2000
  timeout_ms?: number; // default 180000
  // When set, the named field from the status payload is rendered as Markdown
  // beneath the ready alert once the job completes.
  result_markdown_field?: string;
  // Optional external link rendered on success when `field` is present in the
  // status payload (e.g. a link to the run's session on a remote server).
  result_link?: {
    field: string;
    label: string;
  };
  // Optional post-result action. When the job is ready and `when_field` is
  // present in the status payload, a button (labelled `label`) POSTs to
  // `endpoint` (`{job_id}` interpolated) — e.g. to delete a kept workspace.
  cleanup_action?: {
    endpoint: string;
    label: string;
    when_field: string;
  };
  // All user-facing strings come from the plugin — the form has none baked in.
  labels: {
    pending: string; // alert title shown while polling
    ready: string; // success alert title
    failed: string; // error alert title
    timeout: string; // shown if the job never resolves
    done?: string; // submit-button label on success (default "Done")
  };
}

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
  // Opt-in: when present and a submit returns `{ job_id, status: "pending" }`,
  // the form polls `status_endpoint` until the job is ready/failed/timed out.
  async_action?: PluginAsyncActionConfig;
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

// ── Generic custom-UI archetypes ─────────────────────────────────────────────
// A plugin may ship a declarative `custom_ui` spec that the core UI renders with
// a generic archetype component (dispatched by `custom_ui.type`). No core UI code
// is specific to any single plugin.

export interface CatalogItemDetail { label: string; value: string; href?: string; }
export interface CatalogItemBadge { label: string; color?: string; }

/** One row in a catalog-import result table, normalized by the plugin backend. */
export interface CatalogItem {
  id: string;
  title: string;
  subtitle?: string | null;
  source?: string | null;
  description?: string | null;
  details?: CatalogItemDetail[];
  badges?: CatalogItemBadge[];
}

export interface PluginSetupStep { label: string; description: string; }
export interface PluginSetupInstructions {
  title: string;
  steps: PluginSetupStep[];
  docs_url?: string;
}

/** Declarative spec for the generic "search catalog → select → import" archetype. */
export interface CatalogImportConfig {
  type: 'catalog-import';
  title: string;
  description?: string;
  search_endpoint: string;
  detail_endpoint?: string;
  import_endpoint: string;
  search_placeholder?: string;
  min_query_chars?: number;
  import_button_label?: string;
  import_extra_params?: Record<string, any>;
  columns?: { primary?: string; secondary?: string; description?: string };
  setup_instructions?: PluginSetupInstructions;
}

export interface PluginUIConfig {
  icon: string;
  color: string;
  actions: PluginAction[];
  settings_schema?: Record<string, any>;
  notifications?: PluginNotificationsConfig;
  /** When set, PluginsPage renders a generic custom-UI archetype (dispatched by custom_ui.type). */
  custom_ui?: CatalogImportConfig;
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
  admin_enabled: boolean;
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