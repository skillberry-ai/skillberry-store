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
import { AnthropicSkillImporter } from '../utils/anthropic/AnthropicSkillImporter';

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
      // Fetch all skills, tools, and snippets
      const [skillsRes, toolsRes, snippetsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/skills/`),
        fetch(`${API_BASE_URL}/tools/`),
        fetch(`${API_BASE_URL}/snippets/`),
      ]);

      if (!skillsRes.ok || !toolsRes.ok || !snippetsRes.ok) {
        throw new Error('Failed to fetch data');
      }

      const [skillsData, toolsData, snippetsData] = await Promise.all([
        skillsRes.json(),
        toolsRes.json(),
        snippetsRes.json(),
      ]);

      // Fetch full tool objects with module content
      const toolsWithContent = await Promise.all(
        toolsData.map(async (tool: any) => {
          try {
            const moduleRes = await fetch(`${API_BASE_URL}/tools/${tool.name}/module`);
            if (moduleRes.ok) {
              const moduleContent = await moduleRes.text();
              return { ...tool, module_content: moduleContent };
            }
            return tool;
          } catch {
            return tool;
          }
        })
      );

      // Fetch full snippet objects with content
      const snippetsWithContent = await Promise.all(
        snippetsData.map(async (snippet: any) => {
          try {
            const contentRes = await fetch(`${API_BASE_URL}/snippets/${snippet.name}/content`);
            if (contentRes.ok) {
              const content = await contentRes.text();
              return { ...snippet, content };
            }
            return snippet;
          } catch {
            return snippet;
          }
        })
      );

      // Convert skills to export format with only tool and snippet names
      const skillsForExport = skillsData.map((skill: any) => ({
        name: skill.name,
        version: skill.version,
        description: skill.description,
        tags: skill.tags,
        toolNames: skill.tools?.map((t: any) => t.name) || [],
        snippetNames: skill.snippets?.map((s: any) => s.name) || [],
      }));

      // Create export data
      const exportData = {
        skills: skillsForExport,
        tools: toolsWithContent,
        snippets: snippetsWithContent,
        exported_at: new Date().toISOString(),
      };

      // Download as JSON file
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `skillberry-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setExportResult({
        success: true,
        message: `Successfully exported ${skillsData.length} skills, ${toolsData.length} tools, and ${snippetsData.length} snippets.`,
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

      // Import tools first (with their modules)
      if (importData.tools && Array.isArray(importData.tools)) {
        for (const tool of importData.tools) {
          try {
            const formData = new FormData();
            
            // Create a blob from module_content
            if (tool.module_content) {
              const moduleBlob = new Blob([tool.module_content], { type: 'text/plain' });
              formData.append('module', moduleBlob, `${tool.name}.py`);
            }

            // Add tool metadata as query parameters
            const params = new URLSearchParams({
              name: tool.name,
              version: tool.version || '1.0.0',
              description: tool.description || '',
              tags: JSON.stringify(tool.tags || []),
            });

            if (tool.params) {
              formData.append('params', JSON.stringify(tool.params));
            }
            if (tool.returns) {
              formData.append('returns', JSON.stringify(tool.returns));
            }

            const response = await fetch(`${API_BASE_URL}/tools/?${params}`, {
              method: 'POST',
              body: formData,
            });

            if (response.ok) {
              importedTools++;
            }
          } catch (error) {
            console.error(`Failed to import tool ${tool.name}:`, error);
          }
        }
      }

      // Import snippets
      if (importData.snippets && Array.isArray(importData.snippets)) {
        for (const snippet of importData.snippets) {
          try {
            const formData = new FormData();
            
            if (snippet.content) {
              const contentBlob = new Blob([snippet.content], { type: 'text/plain' });
              formData.append('content', contentBlob, `${snippet.name}.txt`);
            }

            const params = new URLSearchParams({
              name: snippet.name,
              version: snippet.version || '1.0.0',
              description: snippet.description || '',
              tags: JSON.stringify(snippet.tags || []),
            });

            const response = await fetch(`${API_BASE_URL}/snippets/?${params}`, {
              method: 'POST',
              body: formData,
            });

            if (response.ok) {
              importedSnippets++;
            }
          } catch (error) {
            console.error(`Failed to import snippet ${snippet.name}:`, error);
          }
        }
      }

      // Import skills last (after tools and snippets exist)
      if (importData.skills && Array.isArray(importData.skills)) {
        for (const skill of importData.skills) {
          try {
            const response = await fetch(`${API_BASE_URL}/skills/`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(skill),
            });

            if (response.ok) {
              importedSkills++;
            }
          } catch (error) {
            console.error(`Failed to import skill ${skill.name}:`, error);
          }
        }
      }

      setImportResult({
        success: true,
        message: `Successfully imported ${importedSkills} skills, ${importedTools} tools, and ${importedSnippets} snippets.`,
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
              <li><strong>Export All:</strong> Downloads all skills, tools, and snippets as a JSON file for backup or migration.</li>
              <li><strong>Import All:</strong> Imports skills, tools, and snippets from a previously exported JSON file.</li>
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