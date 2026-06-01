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
  ExclamationTriangleIcon,
} from '@patternfly/react-icons';
import {
  exportTools,
  importTools,
  exportSnippets,
  importSnippets,
  exportSkills,
  importSkills,
  exportVMCPServers,
  importVMCPServers,
  exportVNFSServers,
  importVNFSServers,
  downloadCompressedJSON,
  readCompressedJSON,
} from '../utils/exportImportHelpers';

const API_BASE_URL = '/api';

export function AdminPage() {
  const queryClient = useQueryClient();
  const [purgeModalOpen, setPurgeModalOpen] = useState(false);
  const [isPurging, setIsPurging] = useState(false);
  const [purgeResult, setPurgeResult] = useState<{ success: boolean; message: string } | null>(null);
  
  const [isBackingUp, setIsBackingUp] = useState(false);
  const [backupResult, setBackupResult] = useState<{ success: boolean; message: string } | null>(null);
  
  const [restoreModalOpen, setRestoreModalOpen] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [restoreResult, setRestoreResult] = useState<{ success: boolean; message: string } | null>(null);
  const [pendingRestoreFile, setPendingRestoreFile] = useState<File | null>(null);

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
        queryClient.invalidateQueries({ queryKey: ['vnfs-servers'] });
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

  const handleBackupAll = async () => {
    setIsBackingUp(true);
    setBackupResult(null);
    
    try {
      // Fetch all skills, tools, snippets, VMCP servers, and vNFS servers
      const [skillsRes, toolsRes, snippetsRes, vmcpRes, vnfsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/skills/`),
        fetch(`${API_BASE_URL}/tools/`),
        fetch(`${API_BASE_URL}/snippets/`),
        fetch(`${API_BASE_URL}/vmcp_servers/`),
        fetch(`${API_BASE_URL}/vnfs_servers/`),
      ]);

      if (!skillsRes.ok || !toolsRes.ok || !snippetsRes.ok || !vmcpRes.ok || !vnfsRes.ok) {
        throw new Error('Failed to fetch data');
      }

      const [skillsData, toolsData, snippetsData, vmcpData, vnfsData] = await Promise.all([
        skillsRes.json(),
        toolsRes.json(),
        snippetsRes.json(),
        vmcpRes.json(),
        vnfsRes.json(),
      ]);

      // Use helper functions to export data (reusing logic from individual pages)
      const toolsWithContent = await exportTools(toolsData);
      const snippetsForExport = exportSnippets(snippetsData);
      const skillsForExport = exportSkills(skillsData);
      const vmcpForExport = exportVMCPServers(vmcpData.virtual_mcp_servers ? Object.values(vmcpData.virtual_mcp_servers) : []);
      const vnfsForExport = exportVNFSServers(vnfsData.virtual_nfs_servers ? Object.values(vnfsData.virtual_nfs_servers) : []);

      // Create backup data
      const backupData = {
        skills: skillsForExport,
        tools: toolsWithContent,
        snippets: snippetsForExport,
        vmcp_servers: vmcpForExport,
        vnfs_servers: vnfsForExport,
        exported_at: new Date().toISOString(),
      };

      // Download as compressed JSON file (.json.zip)
      await downloadCompressedJSON(backupData, `skillberry-backup-${new Date().toISOString().split('T')[0]}.json`);

      setBackupResult({
        success: true,
        message: `Successfully backed up ${skillsData.length} skills, ${toolsData.length} tools, ${snippetsData.length} snippets, ${vmcpForExport.length} VMCP servers, and ${vnfsForExport.length} vNFS servers.`,
      });
    } catch (error) {
      setBackupResult({
        success: false,
        message: `Backup failed: ${(error as Error).message}`,
      });
    } finally {
      setIsBackingUp(false);
    }
  };

  const handleRestoreFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Store the file and show confirmation modal
    setPendingRestoreFile(file);
    setRestoreModalOpen(true);
    
    // Reset file input
    event.target.value = '';
  };

  const handleRestoreAll = async () => {
    if (!pendingRestoreFile) return;

    setIsRestoring(true);
    setRestoreResult(null);

    try {
      // Read and decompress the backup file
      const importData = await readCompressedJSON(pendingRestoreFile);

      // Validate that we have valid data
      if (!importData || typeof importData !== 'object') {
        throw new Error('Invalid backup file format');
      }

      // First, purge all existing data
      const purgeResponse = await fetch(`${API_BASE_URL}/admin/purge-all`, {
        method: 'DELETE',
      });

      if (!purgeResponse.ok) {
        throw new Error('Failed to purge existing data before restore');
      }

      let importedTools = 0;
      let importedSnippets = 0;
      let importedSkills = 0;
      let importedVMCP = 0;
      let importedVNFS = 0;

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

      // Import vNFS servers
      if (importData.vnfs_servers && Array.isArray(importData.vnfs_servers)) {
        importedVNFS = await importVNFSServers(importData.vnfs_servers);
      }

      // Force refetch all query caches to refresh the views immediately
      await Promise.all([
        queryClient.refetchQueries({ queryKey: ['skills'] }),
        queryClient.refetchQueries({ queryKey: ['tools'] }),
        queryClient.refetchQueries({ queryKey: ['snippets'] }),
        queryClient.refetchQueries({ queryKey: ['vmcp-servers'] }),
        queryClient.refetchQueries({ queryKey: ['vnfs-servers'] }),
      ]);

      setRestoreResult({
        success: true,
        message: `Successfully restored ${importedSkills} skills, ${importedTools} tools, ${importedSnippets} snippets, ${importedVMCP} VMCP servers, and ${importedVNFS} vNFS servers.`,
      });
    } catch (error) {
      setRestoreResult({
        success: false,
        message: `Restore failed: ${(error as Error).message}`,
      });
    } finally {
      setIsRestoring(false);
      setRestoreModalOpen(false);
      setPendingRestoreFile(null);
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

            {backupResult && (
              <Alert
                variant={backupResult.success ? 'success' : 'danger'}
                title={backupResult.success ? 'Success' : 'Error'}
                style={{ marginBottom: '1rem' }}
                isInline
              >
                {backupResult.message}
              </Alert>
            )}

            {restoreResult && (
              <Alert
                variant={restoreResult.success ? 'success' : 'danger'}
                title={restoreResult.success ? 'Success' : 'Error'}
                style={{ marginBottom: '1rem' }}
                isInline
              >
                {restoreResult.message}
              </Alert>
            )}

            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
              {/* Backup/Restore Group */}
              <div style={{ display: 'flex', gap: '0.5rem', padding: '0.5rem', border: '1px solid #d2d2d2', borderRadius: '4px', backgroundColor: '#f5f5f5' }}>
                <Button
                  variant="primary"
                  icon={<DownloadIcon />}
                  onClick={handleBackupAll}
                  isDisabled={isPurging || isBackingUp || isRestoring}
                >
                  {isBackingUp ? <Spinner size="md" /> : 'Backup All Data'}
                </Button>

                <Button
                  variant="warning"
                  icon={<UploadIcon />}
                  isDanger
                  onClick={() => document.getElementById('restore-file-input')?.click()}
                  isDisabled={isPurging || isBackingUp || isRestoring}
                  style={{ color: '#c9190b' }}
                >
                  {isRestoring ? <Spinner size="md" /> : 'Restore All Data'}
                </Button>
                <input
                  id="restore-file-input"
                  type="file"
                  accept=".zip,.json.zip"
                  style={{ display: 'none' }}
                  onChange={handleRestoreFileSelect}
                />
              </div>

              <Divider orientation={{ default: 'vertical' }} style={{ height: '40px' }} />

              {/* Hazardous Operations */}
              <Button
                variant="danger"
                icon={<TrashIcon />}
                onClick={() => setPurgeModalOpen(true)}
                isDisabled={isPurging || isBackingUp || isRestoring}
              >
                Purge All Data
              </Button>
            </div>

            <Divider style={{ margin: '2rem 0' }} />

            <Title headingLevel="h3" size="md" style={{ marginBottom: '0.5rem' }}>
              About These Actions
            </Title>
            <ul style={{ marginLeft: '1.5rem' }}>
              <li><strong>Backup All Data:</strong> Downloads all skills, tools, snippets, VMCP servers, and vNFS servers as a compressed JSON file (.json.zip) for backup or migration.</li>
              <li><strong>Restore All Data:</strong> Restores all data from a compressed backup file (.json.zip). <span style={{ color: '#c9190b', fontWeight: 'bold' }}>Warning:</span> This will first purge all existing data before restoring from the backup.</li>
              <li><strong>Purge All Data:</strong> Permanently deletes all skills, tools, snippets, Virtual MCP servers, and vNFS servers. This action cannot be undone.</li>
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
          <li>All Virtual NFS servers</li>
          <li>All descriptions and indexes</li>
        </ul>
        <p style={{ marginTop: '1rem', fontWeight: 'bold' }}>
          This action cannot be undone. Are you sure you want to continue?
        </p>
      </Modal>

      <Modal
        variant={ModalVariant.small}
        title="Confirm Restore All Data"
        isOpen={restoreModalOpen}
        onClose={() => {
          setRestoreModalOpen(false);
          setPendingRestoreFile(null);
        }}
        actions={[
          <Button
            key="confirm"
            variant="danger"
            onClick={handleRestoreAll}
            isDisabled={isRestoring}
          >
            {isRestoring ? <Spinner size="md" /> : 'Yes, Restore All'}
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => {
              setRestoreModalOpen(false);
              setPendingRestoreFile(null);
            }}
            isDisabled={isRestoring}
          >
            Cancel
          </Button>,
        ]}
      >
        <Alert variant="danger" title="Warning: Data Will Be Reset" isInline style={{ marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ExclamationTriangleIcon />
            <span>This action will first PURGE ALL existing data before restoring from the backup file.</span>
          </div>
        </Alert>
        <p style={{ marginBottom: '1rem' }}>
          The restore operation will:
        </p>
        <ul style={{ marginLeft: '1.5rem', marginBottom: '1rem' }}>
          <li>Delete all existing skills, tools, snippets, VMCP servers, and vNFS servers</li>
          <li>Clear all descriptions and indexes</li>
          <li>Restore data from the backup file: <strong>{pendingRestoreFile?.name}</strong></li>
        </ul>
        <p style={{ fontWeight: 'bold', color: '#c9190b' }}>
          This action cannot be undone. Are you sure you want to continue?
        </p>
      </Modal>
    </>
  );
}

// Made with Bob
