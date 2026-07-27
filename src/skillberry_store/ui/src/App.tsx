// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { Routes, Route, useLocation } from 'react-router-dom';
import { AppLayout } from './components/AppLayout';
import { AuthGate } from './components/AuthGate';
import { LoginPage } from './pages/LoginPage';
import { HomePage } from './pages/HomePage';
import { ToolsPage } from './pages/ToolsPage';
import { ToolDetailPage } from './pages/ToolDetailPage';
import { SkillsPage } from './pages/SkillsPage';
import { SkillDetailPage } from './pages/SkillDetailPage';
import { SnippetsPage } from './pages/SnippetsPage';
import { SnippetDetailPage } from './pages/SnippetDetailPage';
import { VMCPServersPage } from './pages/VMCPServersPage';
import { VMCPServerDetailPage } from './pages/VMCPServerDetailPage';
import { VNFSServersPage } from './pages/VNFSServersPage';
import { VNFSServerDetailPage } from './pages/VNFSServerDetailPage';
import { PluginsPage } from './pages/PluginsPage';
import { AdminPage } from './pages/AdminPage';
import { ObservabilityPage } from './pages/ObservabilityPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { useChangesMonitor } from './hooks/useChangesMonitor';

function App() {
  useChangesMonitor();
  const location = useLocation();

  // The login page renders standalone (no AppLayout chrome), and it's the
  // only route that must remain reachable when the AuthGate is redirecting.
  if (location.pathname === '/login') {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    );
  }

  return (
    <AuthGate>
    <AppLayout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        
        {/* Tools routes */}
        <Route path="/tools" element={<ToolsPage />} />
        <Route path="/tools/:uuid" element={<ToolDetailPage />} />
        
        {/* Skills routes */}
        <Route path="/skills" element={<SkillsPage />} />
        <Route path="/skills/:uuid" element={<SkillDetailPage />} />
        
        {/* Snippets routes */}
        <Route path="/snippets" element={<SnippetsPage />} />
        <Route path="/snippets/:uuid" element={<SnippetDetailPage />} />
        
        {/* Virtual MCP Servers routes */}
        <Route path="/vmcp-servers" element={<VMCPServersPage />} />
        <Route path="/vmcp-servers/:uuid" element={<VMCPServerDetailPage />} />
        
        {/* Virtual NFS Servers routes */}
        <Route path="/vnfs-servers" element={<VNFSServersPage />} />
        <Route path="/vnfs-servers/:uuid" element={<VNFSServerDetailPage />} />

        {/* Plugins route */}
        <Route path="/plugins" element={<PluginsPage />} />

        {/* Admin route */}
        <Route path="/admin" element={<AdminPage />} />
        
        {/* Observability route */}
        <Route path="/observability" element={<ObservabilityPage />} />
        
        {/* 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppLayout>
    </AuthGate>
  );
}

export default App;

// Made with Bob
