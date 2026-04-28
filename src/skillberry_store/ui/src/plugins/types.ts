// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import type { ComponentType, ReactNode } from 'react';

export interface PluginRoute {
  path: string;
  element: ReactNode;
}

export interface PluginNavItem {
  id: string;
  label: string;
  path: string;
  badge?: string;
}

export interface PluginSlotContribution {
  id: string;
  component: ComponentType<any>;
}

export interface PluginManifest {
  id: string;
  name: string;
  description?: string;
  routes: PluginRoute[];
  navItems: PluginNavItem[];
  slots: Record<string, PluginSlotContribution[]>;
}

export interface PluginListItem {
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
