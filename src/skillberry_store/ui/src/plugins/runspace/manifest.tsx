// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import type { PluginManifest } from '../types';
import { RunspacePage } from './RunspacePage';
import { ExportWithAgentAction } from './ExportWithAgentAction';

export const runspaceManifest: PluginManifest = {
  id: 'runspace',
  name: 'Runspace',
  description:
    'Agent-driven skill export and a Runspace Store Agent chat, powered by the Runspace daemon (runspace-srv).',
  routes: [
    { path: '/runspace', element: <RunspacePage /> },
  ],
  navItems: [
    { id: 'runspace', label: 'Runspace', path: '/runspace' },
  ],
  slots: {
    'skill.detail.actions': [
      { id: 'runspace.export-with-agent', component: ExportWithAgentAction },
    ],
  },
};
