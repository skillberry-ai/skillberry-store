// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0
//
// UI plugin registry. Main code never references a plugin by id — it reads
// active plugins from here and iterates. The set of installed plugins is the
// hand-maintained `manifests` list below; which ones are "active" is fetched
// from the backend `/plugins` endpoint and stored in a small hook.

import { useSyncExternalStore } from 'react';
import type { PluginManifest, PluginListItem } from './types';
import { runspaceManifest } from './runspace/manifest';

export const manifests: PluginManifest[] = [runspaceManifest];

type Listener = () => void;

let activeIds: Set<string> = new Set();
let loaded = false;
const listeners = new Set<Listener>();

function emit() {
  for (const l of listeners) l();
}

export function getActiveManifests(): PluginManifest[] {
  return manifests.filter((m) => activeIds.has(m.id));
}

export function getActiveIds(): Set<string> {
  return new Set(activeIds);
}

export function isActive(id: string): boolean {
  return activeIds.has(id);
}

export function setActiveIds(ids: Iterable<string>) {
  activeIds = new Set(ids);
  loaded = true;
  emit();
}

export function isLoaded(): boolean {
  return loaded;
}

function subscribe(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

const ACTIVE_SNAPSHOT = { current: activeIds } as { current: Set<string> };
function syncSnapshot() {
  if (ACTIVE_SNAPSHOT.current !== activeIds) {
    ACTIVE_SNAPSHOT.current = activeIds;
  }
  return ACTIVE_SNAPSHOT.current;
}

export function useActivePlugins(): Set<string> {
  return useSyncExternalStore(
    (listener) => subscribe(() => { syncSnapshot(); listener(); }),
    syncSnapshot,
    syncSnapshot,
  );
}

export function useActiveManifests(): PluginManifest[] {
  const ids = useActivePlugins();
  return manifests.filter((m) => ids.has(m.id));
}

export function applyPluginsListFromBackend(items: PluginListItem[]) {
  setActiveIds(items.filter((p) => p.enabled).map((p) => p.id));
}

export function getInstalledManifests(): PluginManifest[] {
  return manifests;
}
