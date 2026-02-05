// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

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
import { NotFoundPage } from './pages/NotFoundPage';

function App() {
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
        
        {/* VMCP Servers routes */}
        <Route path="/vmcp-servers" element={<VMCPServersPage />} />
        <Route path="/vmcp-servers/:name" element={<VMCPServerDetailPage />} />
        
        {/* 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppLayout>
  );
}

export default App;