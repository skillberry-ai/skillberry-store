// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { AppLayout } from './components/AppLayout';
import { HomePage } from './pages/HomePage';
import { ToolsPage } from './pages/ToolsPage';
import { ToolDetailPage } from './pages/ToolDetailPage';
import { SkillsPage } from './pages/SkillsPage';
import { SkillDetailPage } from './pages/SkillDetailPage';
import { SnippetsPage } from './pages/SnippetsPage';
import { SnippetDetailPage } from './pages/SnippetDetailPage';
import { VMCPServersPage } from './pages/VMCPServersPage';
import { VMCPServerDetailPage } from './pages/VMCPServerDetailPage';
import { ExternalMCPsPage } from './pages/ExternalMCPsPage';
import { ExternalMCPDetailPage } from './pages/ExternalMCPDetailPage';
import { AdminPage } from './pages/AdminPage';
import { ObservabilityPage } from './pages/ObservabilityPage';
import { AgentConnectPage } from './pages/AgentConnectPage';
import { PluginsPage } from './pages/PluginsPage';

import { NotFoundPage } from './pages/NotFoundPage';
import { pluginsApi } from '@/services/api';
import { applyPluginsListFromBackend, useActiveManifests } from '@/plugins/registry';

function App() {
  const activeManifests = useActiveManifests();

  useEffect(() => {
    pluginsApi.list()
      .then((items) => applyPluginsListFromBackend(items))
      .catch(() => {
        // If /plugins isn't available, no plugins render — safe default.
      });
  }, []);

  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<HomePage />} />

        {/* Tools routes */}
        <Route path="/tools" element={<ToolsPage />} />
        <Route path="/tools/:name" element={<ToolDetailPage />} />

        {/* Skills routes */}
        <Route path="/skills" element={<SkillsPage />} />
        <Route path="/skills/:name" element={<SkillDetailPage />} />

        {/* Snippets routes */}
        <Route path="/snippets" element={<SnippetsPage />} />
        <Route path="/snippets/:name" element={<SnippetDetailPage />} />

        {/* Virtual MCP Servers routes */}
        <Route path="/vmcp-servers" element={<VMCPServersPage />} />
        <Route path="/vmcp-servers/:name" element={<VMCPServerDetailPage />} />

        {/* External MCPs routes (imported MCP servers the store consumes) */}
        <Route path="/external-mcps" element={<ExternalMCPsPage />} />
        <Route path="/external-mcps/:name" element={<ExternalMCPDetailPage />} />

        {/* Admin route */}
        <Route path="/admin" element={<AdminPage />} />

        {/* Observability route */}
        <Route path="/observability" element={<ObservabilityPage />} />

        {/* Agent Connect route */}
        <Route path="/agent-connect" element={<AgentConnectPage />} />

        {/* Plugins */}
        <Route path="/plugins" element={<PluginsPage />} />

        {/* Plugin-contributed routes */}
        {activeManifests.flatMap((m) =>
          m.routes.map((r) => (
            <Route key={`${m.id}:${r.path}`} path={r.path} element={r.element} />
          ))
        )}

        {/* 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppLayout>
  );
}

export default App;
