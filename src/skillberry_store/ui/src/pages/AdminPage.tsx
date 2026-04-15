import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  PageSection,
  Title,
  Card,
  CardBody,
  Button,
  Alert,
  Modal,
  ModalVariant,
  Spinner,
  Divider,
} from '@patternfly/react-core';
import {
  TrashIcon,
  DownloadIcon,
  UploadIcon,
  CodeIcon,
} from '@patternfly/react-icons';
import { AnthropicSkillImporter } from '../components/AnthropicSkillImporter';
import {
  exportTools,
  importTools,
  exportSnippets,
  importSnippets,
  exportSkills,
  importSkills,
  exportVMCPServers,
  importVMCPServers,
  downloadJSON,
} from '../utils/exportImportHelpers';

const API_BASE_URL = '/api';

export function AdminPage() {
  const queryClient = useQueryClient();
  const [purgeModalOpen, setPurgeModalOpen] = useState(false);
  const [isPurging, setIsPurging] = useState(false);
  const [purgeResult, setPurgeResult] = useState<{ success: boolean; message: string } | null>(null);
  
  const [isExporting, setIsExporting] = useState(false);
  const [exportResult, setExportResult] = useState<{ success: boolean; message: string } | null>(null);
  
  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState<{ success: boolean; message: string } | null>(null);
  
  const [anthropicImportModalOpen, setAnthropicImportModalOpen] = useState(false);

  const handlePurgeAll = async () => {
    setIsPurging(true);
    setPurgeResult(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/admin/purge-all`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        const data = await response.json();
        setPurgeResult({
          success: true,
          message: `Successfully purged all data. Deleted ${data.total_deleted} directories.`,
        });
        
        // Invalidate all query caches to refresh the views
        queryClient.invalidateQueries({ queryKey: ['skills'] });
        queryClient.invalidateQueries({ queryKey: ['tools'] });
        queryClient.invalidateQueries({ queryKey: ['snippets'] });
        queryClient.invalidateQueries({ queryKey: ['vmcp-servers'] });
      } else {
        const error = await response.json();
        setPurgeResult({
          success: false,
          message: `Failed to purge data: ${error.detail?.message || 'Unknown error'}`,
        });
      }
    } catch (error) {
      setPurgeResult({
        success: false,
        message: `Error: ${(error as Error).message}`,
      });
    } finally {
      setIsPurging(false);
      setPurgeModalOpen(false);
    }
  };

  const handleExportAll = async () => {
    setIsExporting(true);
    setExportResult(null);
    
    try {
      // Fetch all skills, tools, snippets, and VMCP servers
      const [skillsRes, toolsRes, snippetsRes, vmcpRes] = await Promise.all([
        fetch(`${API_BASE_URL}/skills/`),
        fetch(`${API_BASE_URL}/tools/`),
        fetch(`${API_BASE_URL}/snippets/`),
        fetch(`${API_BASE_URL}/vmcp_servers/`),
      ]);

      if (!skillsRes.ok || !toolsRes.ok || !snippetsRes.ok || !vmcpRes.ok) {
        throw new Error('Failed to fetch data');
      }

      const [skillsData, toolsData, snippetsData, vmcpData] = await Promise.all([
        skillsRes.json(),
        toolsRes.json(),
        snippetsRes.json(),
        vmcpRes.json(),
      ]);

      // Use helper functions to export data (reusing logic from individual pages)
      const toolsWithContent = await exportTools(toolsData);
      const snippetsForExport = exportSnippets(snippetsData);
      const skillsForExport = exportSkills(skillsData);
      const vmcpForExport = exportVMCPServers(vmcpData);

      // Create export data
      const exportData = {
        skills: skillsForExport,
        tools: toolsWithContent,
        snippets: snippetsForExport,
        vmcp_servers: vmcpForExport,
        exported_at: new Date().toISOString(),
      };

      // Download as JSON file
      downloadJSON(exportData, `skillberry-export-${new Date().toISOString().split('T')[0]}.json`);

      setExportResult({
        success: true,
        message: `Successfully exported ${skillsData.length} skills, ${toolsData.length} tools, ${snippetsData.length} snippets, and ${vmcpData?.length || 0} VMCP servers.`,
      });
    } catch (error) {
      setExportResult({
        success: false,
        message: `Export failed: ${(error as Error).message}`,
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handleImportAll = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsImporting(true);
    setImportResult(null);

    try {
      const text = await file.text();
      const importData = JSON.parse(text);

      let importedTools = 0;
      let importedSnippets = 0;
      let importedSkills = 0;
      let importedVMCP = 0;

      // Import tools first (with their modules) - reusing logic from ToolsPage
      if (importData.tools && Array.isArray(importData.tools)) {
        importedTools = await importTools(importData.tools);
      }

      // Import snippets - reusing logic from SnippetsPage
      if (importData.snippets && Array.isArray(importData.snippets)) {
        importedSnippets = await importSnippets(importData.snippets);
      }

      // Import skills last (after tools and snippets exist) - reusing logic from SkillsPage
      if (importData.skills && Array.isArray(importData.skills)) {
        importedSkills = await importSkills(importData.skills);
      }

      // Import VMCP servers - reusing logic from VMCPServersPage
      if (importData.vmcp_servers && Array.isArray(importData.vmcp_servers)) {
        importedVMCP = await importVMCPServers(importData.vmcp_servers);
      }

      // Invalidate all query caches to refresh the views
      queryClient.invalidateQueries({ queryKey: ['skills'] });
      queryClient.invalidateQueries({ queryKey: ['tools'] });
      queryClient.invalidateQueries({ queryKey: ['snippets'] });
      queryClient.invalidateQueries({ queryKey: ['vmcp-servers'] });

      setImportResult({
        success: true,
        message: `Successfully imported ${importedSkills} skills, ${importedTools} tools, ${importedSnippets} snippets, and ${importedVMCP} VMCP servers.`,
      });
    } catch (error) {
      setImportResult({
        success: false,
        message: `Import failed: ${(error as Error).message}`,
      });
    } finally {
      setIsImporting(false);
      // Reset file input
      event.target.value = '';
    }
  };

  return (
    <>
      <PageSection>
        <Title headingLevel="h1" size="2xl">
          Admin
        </Title>
      </PageSection>

      <PageSection>
        <Card>
          <CardBody>
            <Title headingLevel="h2" size="lg" style={{ marginBottom: '1rem' }}>
              Data Management
            </Title>
            
            {purgeResult && (
              <Alert
                variant={purgeResult.success ? 'success' : 'danger'}
                title={purgeResult.success ? 'Success' : 'Error'}
                style={{ marginBottom: '1rem' }}
                isInline
              >
                {purgeResult.message}
              </Alert>
            )}

            {exportResult && (
              <Alert
                variant={exportResult.success ? 'success' : 'danger'}
                title={exportResult.success ? 'Success' : 'Error'}
                style={{ marginBottom: '1rem' }}
                isInline
              >
                {exportResult.message}
              </Alert>
            )}

            {importResult && (
              <Alert
                variant={importResult.success ? 'success' : 'danger'}
                title={importResult.success ? 'Success' : 'Error'}
                style={{ marginBottom: '1rem' }}
                isInline
              >
                {importResult.message}
              </Alert>
            )}

            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              <Button
                variant="danger"
                icon={<TrashIcon />}
                onClick={() => setPurgeModalOpen(true)}
                isDisabled={isPurging || isExporting || isImporting}
              >
                Purge All Data
              </Button>

              <Button
                variant="primary"
                icon={<DownloadIcon />}
                onClick={handleExportAll}
                isDisabled={isPurging || isExporting || isImporting}
              >
                {isExporting ? <Spinner size="md" /> : 'Export All'}
              </Button>

              <Button
                variant="secondary"
                icon={<UploadIcon />}
                onClick={() => document.getElementById('import-file-input')?.click()}
                isDisabled={isPurging || isExporting || isImporting}
              >
                {isImporting ? <Spinner size="md" /> : 'Import All'}
              </Button>
              <input
                id="import-file-input"
                type="file"
                accept=".json"
                style={{ display: 'none' }}
                onChange={handleImportAll}
              />

              <Button
                variant="tertiary"
                icon={<CodeIcon />}
                onClick={() => setAnthropicImportModalOpen(true)}
                isDisabled={isPurging || isExporting || isImporting}
              >
                Import Anthropic Skill
              </Button>
            </div>

            <Divider style={{ margin: '2rem 0' }} />

            <Title headingLevel="h3" size="md" style={{ marginBottom: '0.5rem' }}>
              About These Actions
            </Title>
            <ul style={{ marginLeft: '1.5rem' }}>
              <li><strong>Purge All Data:</strong> Permanently deletes all skills, tools, snippets, and Virtual MCP servers. This action cannot be undone.</li>
              <li><strong>Export All:</strong> Downloads all skills, tools, snippets, and VMCP servers as a JSON file for backup or migration.</li>
              <li><strong>Import All:</strong> Imports skills, tools, snippets, and VMCP servers from a previously exported JSON file.</li>
              <li><strong>Import Anthropic Skill:</strong> Imports an Anthropic skill from a GitHub URL or ZIP file. Text files are converted to snippets, and Python/Bash functions are converted to tools.</li>
            </ul>
          </CardBody>
        </Card>
      </PageSection>

      <Modal
        variant={ModalVariant.small}
        title="Confirm Purge All Data"
        isOpen={purgeModalOpen}
        onClose={() => setPurgeModalOpen(false)}
        actions={[
          <Button
            key="confirm"
            variant="danger"
            onClick={handlePurgeAll}
            isDisabled={isPurging}
          >
            {isPurging ? <Spinner size="md" /> : 'Yes, Purge All'}
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => setPurgeModalOpen(false)}
            isDisabled={isPurging}
          >
            Cancel
          </Button>,
        ]}
      >
        <Alert variant="warning" title="Warning" isInline style={{ marginBottom: '1rem' }}>
          This action will permanently delete ALL data including:
        </Alert>
        <ul style={{ marginLeft: '1.5rem' }}>
          <li>All skills</li>
          <li>All tools and their code</li>
          <li>All snippets</li>
          <li>All Virtual MCP servers</li>
          <li>All descriptions and indexes</li>
        </ul>
        <p style={{ marginTop: '1rem', fontWeight: 'bold' }}>
          This action cannot be undone. Are you sure you want to continue?
        </p>
      </Modal>

      <AnthropicSkillImporter
        isOpen={anthropicImportModalOpen}
        onClose={() => setAnthropicImportModalOpen(false)}
        onImportComplete={() => {
          // Optionally refresh the page or show a success message
          console.log('Anthropic skill import completed');
        }}
      />
    </>
  );
}