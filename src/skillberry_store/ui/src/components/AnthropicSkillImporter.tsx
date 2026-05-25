// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useEffect } from 'react';
import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  TextInput,
  Alert,
  Spinner,
  Progress,
  ProgressSize,
  ProgressMeasureLocation,
  List,
  ListItem,
  Select,
  SelectOption,
  SelectList,
  MenuToggle,
  MenuToggleElement,
  Label,
} from '@patternfly/react-core';
import { skillsApi } from '@/services/api';

interface AnthropicSkillImporterProps {
  isOpen: boolean;
  onClose: () => void;
  onImportComplete: () => void;
}

interface ImportResult {
  success: boolean;
  message: string;
  skill_name?: string;
  tools_created?: number;
  snippets_created?: number;
  ignored_files?: string[];
}

type ImportSource = 'url' | 'zip' | 'folder';

export function AnthropicSkillImporter({
  isOpen,
  onClose,
  onImportComplete,
}: AnthropicSkillImporterProps) {
  const [importSource, setImportSource] = useState<ImportSource>('url');
  const [githubUrl, setGithubUrl] = useState('');
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [zipFileName, setZipFileName] = useState('');
  const [folderPath, setFolderPath] = useState('');
  const [snippetMode, setSnippetMode] = useState<'file' | 'paragraph'>('file');
  const [treatAllAsDocuments, setTreatAllAsDocuments] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [batchMode, setBatchMode] = useState(false);
  const [batchResults, setBatchResults] = useState<Array<ImportResult & { skillPath?: string }>>([]);
  
  // Namespace selection state
  const [selectedNamespaces, setSelectedNamespaces] = useState<string[]>([]);
  const [existingNamespaces, setExistingNamespaces] = useState<string[]>([]);
  const [isNamespaceSelectOpen, setIsNamespaceSelectOpen] = useState(false);
  const [namespaceInput, setNamespaceInput] = useState('');

  // Fetch existing namespaces from skills when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchExistingNamespaces();
    }
  }, [isOpen]);

  const fetchExistingNamespaces = async () => {
    try {
      const skills = await skillsApi.list();
      const namespaceSet = new Set<string>();
      
      skills.forEach(skill => {
        skill.tags?.forEach(tag => {
          if (tag.startsWith('namespace:')) {
            const namespace = tag.substring('namespace:'.length);
            namespaceSet.add(namespace);
          }
        });
      });
      
      setExistingNamespaces(Array.from(namespaceSet).sort());
    } catch (error) {
      console.error('Failed to fetch existing namespaces:', error);
    }
  };

  const resetState = () => {
    setGithubUrl('');
    setZipFile(null);
    setZipFileName('');
    setFolderPath('');
    setProgress(0);
    setResult(null);
    setSelectedNamespaces([]);
    setNamespaceInput('');
    setBatchMode(false);
    setBatchResults([]);
  };

  const handleClose = () => {
    if (!isImporting) {
      resetState();
      onClose();
    }
  };

  const handleSelectNamespace = (_event: React.MouseEvent | undefined, value: string | number | undefined) => {
    if (typeof value === 'string' && value && !selectedNamespaces.includes(value)) {
      setSelectedNamespaces([...selectedNamespaces, value]);
      setIsNamespaceSelectOpen(false);
      setNamespaceInput('');
    }
  };

  const handleAddCustomNamespace = () => {
    const trimmedInput = namespaceInput.trim();
    if (trimmedInput && !selectedNamespaces.includes(trimmedInput)) {
      setSelectedNamespaces([...selectedNamespaces, trimmedInput]);
      setNamespaceInput('');
      setIsNamespaceSelectOpen(false);
    }
  };

  const handleRemoveNamespace = (namespaceToRemove: string) => {
    setSelectedNamespaces(selectedNamespaces.filter(ns => ns !== namespaceToRemove));
  };

  const handleImport = async () => {
    setIsImporting(true);
    setResult(null);
    setBatchResults([]);
    setProgress(10);

    try {
      const namespacesToUse = selectedNamespaces.length > 0 ? selectedNamespaces : ['default'];
      const tags = namespacesToUse.map((namespace) => `namespace:${namespace}`);

      if (batchMode) {
        await handleBatchImport(tags);
      } else {
        await handleSingleImport(tags);
      }
      onImportComplete();
    } catch (error) {
      setResult({
        success: false,
        message: `Import failed: ${(error as Error).message}`,
      });
    } finally {
      setIsImporting(false);
    }
  };

  const handleBatchImport = async (tags: string[]) => {
    let sourcePath = '';
    
    if (importSource === 'url') {
      if (!githubUrl) {
        throw new Error('Please provide a GitHub URL');
      }
      sourcePath = githubUrl;
    } else if (importSource === 'folder') {
      if (!folderPath) {
        throw new Error('Please provide a folder path');
      }
      sourcePath = folderPath;
    } else {
      throw new Error('Batch import is only supported for GitHub URLs and local folders');
    }

    setProgress(20);

    // Detect subdirectories with SKILL.md files
    let subdirectories: Array<{ name: string; path: string; has_skill_md: boolean }> = [];

    if (importSource === 'folder') {
      // For local folders, use the backend endpoint to list subdirectories
      const response = await fetch('/api/admin/list-subdirectories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: sourcePath }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to list subdirectories: ${errorText}`);
      }

      const data = await response.json();
      subdirectories = data.subdirectories.filter((dir: any) => dir.has_skill_md);
    } else if (importSource === 'url') {
      // For GitHub URLs, we need to detect subdirectories from the URL
      // This is a simplified approach - in production, you'd want to use GitHub API
      throw new Error('Batch import from GitHub URLs is not yet implemented. Please use local folder for batch import.');
    }

    if (subdirectories.length === 0) {
      throw new Error('No subdirectories with SKILL.md files found');
    }

    setProgress(30);

    // Import each skill sequentially
    const results: Array<ImportResult & { skillPath?: string }> = [];
    const progressIncrement = 60 / subdirectories.length;

    for (let i = 0; i < subdirectories.length; i++) {
      const subdir = subdirectories[i];
      
      try {
        const formData = new FormData();
        formData.append('source_type', 'folder');
        formData.append('folder_path', subdir.path);
        formData.append('snippet_mode', snippetMode);
        formData.append('treat_all_as_documents', treatAllAsDocuments.toString());
        
        tags.forEach(tag => {
          formData.append('tags', tag);
        });

        const response = await fetch('/api/skills/import-anthropic', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const errorText = await response.text();
          results.push({
            success: false,
            message: `Failed to import ${subdir.name}: ${errorText}`,
            skillPath: subdir.path,
          });
        } else {
          const data = await response.json();
          results.push({
            success: true,
            message: data.message || 'Import successful',
            skill_name: data.skill_name,
            tools_created: data.tools_created,
            snippets_created: data.snippets_created,
            ignored_files: data.ignored_files || [],
            skillPath: subdir.path,
          });
        }
      } catch (error) {
        results.push({
          success: false,
          message: `Error importing ${subdir.name}: ${(error as Error).message}`,
          skillPath: subdir.path,
        });
      }

      setProgress(30 + (i + 1) * progressIncrement);
    }

    setBatchResults(results);
    setProgress(100);

    // Set overall result
    const successCount = results.filter(r => r.success).length;
    const totalTools = results.reduce((sum, r) => sum + (r.tools_created || 0), 0);
    const totalSnippets = results.reduce((sum, r) => sum + (r.snippets_created || 0), 0);

    setResult({
      success: successCount > 0,
      message: `Batch import completed: ${successCount}/${results.length} skills imported successfully. Total: ${totalTools} tools, ${totalSnippets} snippets.`,
    });
  };

  const handleSingleImport = async (tags: string[]) => {
    // Prepare form data
    const formData = new FormData();
    formData.append('source_type', importSource);
    formData.append('snippet_mode', snippetMode);
    formData.append('treat_all_as_documents', treatAllAsDocuments.toString());
    
    tags.forEach(tag => {
      formData.append('tags', tag);
    });

    if (importSource === 'url') {
      if (!githubUrl) {
        throw new Error('Please provide a GitHub URL');
      }
      formData.append('github_url', githubUrl);
    } else if (importSource === 'zip') {
      if (!zipFile) {
        throw new Error('Please select a ZIP file');
      }
      formData.append('zip_file', zipFile);
    } else if (importSource === 'folder') {
      if (!folderPath) {
        throw new Error('Please provide a folder path');
      }
      formData.append('folder_path', folderPath);
    }

    setProgress(30);

    // Call backend import endpoint
    const response = await fetch('/api/skills/import-anthropic', {
      method: 'POST',
      body: formData,
    });

    setProgress(80);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Import failed: ${response.statusText}`);
    }

    const data = await response.json();
    setProgress(100);

    setResult({
      success: true,
      message: data.message || 'Import successful',
      skill_name: data.skill_name,
      tools_created: data.tools_created,
      snippets_created: data.snippets_created,
      ignored_files: data.ignored_files || [],
    });
  };



  return (
    <Modal
      variant={ModalVariant.medium}
      title="Import Anthropic Skill"
      isOpen={isOpen}
      onClose={handleClose}
      actions={[
        <Button
          key="import"
          variant="primary"
          onClick={result ? handleClose : handleImport}
          isDisabled={!result && (isImporting || (importSource === 'url' ? !githubUrl : importSource === 'zip' ? !zipFile : !folderPath))}
        >
          {isImporting ? <Spinner size="md" /> : result ? 'Done' : 'Import'}
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose} isDisabled={isImporting}>
          Cancel
        </Button>,
      ]}
    >
      <Form>
        <FormGroup label="Import Source" isRequired>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
            <Button
              variant={importSource === 'url' ? 'primary' : 'secondary'}
              onClick={() => setImportSource('url')}
              isDisabled={isImporting}
            >
              GitHub URL
            </Button>
            <Button
              variant={importSource === 'zip' ? 'primary' : 'secondary'}
              onClick={() => setImportSource('zip')}
              isDisabled={isImporting}
            >
              ZIP File
            </Button>
            <Button
              variant={importSource === 'folder' ? 'primary' : 'secondary'}
              onClick={() => setImportSource('folder')}
              isDisabled={isImporting}
            >
              Local Folder
            </Button>
          </div>
        </FormGroup>

        <FormGroup label="Snippet Import Mode" isRequired>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
            <Button
              variant={snippetMode === 'paragraph' ? 'primary' : 'secondary'}
              onClick={() => setSnippetMode('paragraph')}
              isDisabled={isImporting}
            >
              Split by Paragraph
            </Button>
            <Button
              variant={snippetMode === 'file' ? 'primary' : 'secondary'}
              onClick={() => setSnippetMode('file')}
              isDisabled={isImporting}
            >
              Complete File
            </Button>
          </div>
          <div style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
            {snippetMode === 'paragraph'
              ? 'Text files will be split into multiple snippets, one per paragraph'
              : 'Each text file will be imported as a single snippet'}
          </div>
        </FormGroup>

        <FormGroup label="Code File Handling">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <input
              type="checkbox"
              id="treat-all-as-documents"
              checked={treatAllAsDocuments}
              onChange={(e) => setTreatAllAsDocuments(e.target.checked)}
              disabled={isImporting}
              style={{ cursor: isImporting ? 'not-allowed' : 'pointer' }}
            />
            <label 
              htmlFor="treat-all-as-documents" 
              style={{ 
                cursor: isImporting ? 'not-allowed' : 'pointer',
                userSelect: 'none'
              }}
            >
              Treat all files as documents (including code files)
            </label>
          </div>
          <div style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
            When enabled, code files (e.g., .py, .sh) will be imported as document snippets instead of being parsed as tools. This preserves the original file structure without code analysis.
          </div>
        </FormGroup>

        <FormGroup label="Batch Import Mode">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <input
              type="checkbox"
              id="batch-mode"
              checked={batchMode}
              onChange={(e) => setBatchMode(e.target.checked)}
              disabled={isImporting || importSource === 'zip'}
              style={{ cursor: (isImporting || importSource === 'zip') ? 'not-allowed' : 'pointer' }}
            />
            <label 
              htmlFor="batch-mode" 
              style={{ 
                cursor: (isImporting || importSource === 'zip') ? 'not-allowed' : 'pointer',
                userSelect: 'none'
              }}
            >
              Import multiple skills from subdirectories
            </label>
          </div>
          <div style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
            When enabled, the importer will scan for subdirectories containing SKILL.md files and import all skills in a single operation. Supported for GitHub URLs and local folders only.
          </div>
        </FormGroup>


        <FormGroup label="Namespaces (Optional)" fieldId="namespaces">
          <div style={{ fontSize: '0.875rem', color: '#6a6e73', marginBottom: '0.5rem' }}>
            Add one or more namespaces to label all imported objects (skills, tools, snippets). Select from existing namespaces or add new ones.
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <Select
              id="namespace-select"
              isOpen={isNamespaceSelectOpen}
              selected={null}
              onSelect={handleSelectNamespace}
              onOpenChange={(isOpen) => setIsNamespaceSelectOpen(isOpen)}
              toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                <MenuToggle
                  ref={toggleRef}
                  onClick={() => setIsNamespaceSelectOpen(!isNamespaceSelectOpen)}
                  isExpanded={isNamespaceSelectOpen}
                  isDisabled={isImporting}
                  style={{ width: '100%' }}
                >
                  {namespaceInput || 'Select or add namespace...'}
                </MenuToggle>
              )}
            >
              <SelectList>
                <TextInput
                  type="text"
                  value={namespaceInput}
                  onChange={(_, value) => setNamespaceInput(value)}
                  placeholder="Type to search or add new..."
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddCustomNamespace();
                    }
                  }}
                  style={{ padding: '0.5rem', borderBottom: '1px solid #d2d2d2' }}
                />
                {namespaceInput.trim() && !existingNamespaces.includes(namespaceInput.trim()) && (
                  <SelectOption value={namespaceInput.trim()}>
                    Add new: "{namespaceInput.trim()}"
                  </SelectOption>
                )}
                {existingNamespaces
                  .filter(ns =>
                    ns.toLowerCase().includes(namespaceInput.toLowerCase()) &&
                    !selectedNamespaces.includes(ns)
                  )
                  .map((namespace) => (
                    <SelectOption key={namespace} value={namespace}>
                      {namespace}
                    </SelectOption>
                  ))}
                {existingNamespaces.length === 0 && !namespaceInput.trim() && (
                  <SelectOption isDisabled>
                    No existing namespaces. Type to add new.
                  </SelectOption>
                )}
              </SelectList>
            </Select>
            {namespaceInput.trim() && (
              <Button
                variant="secondary"
                onClick={handleAddCustomNamespace}
                isDisabled={isImporting}
              >
                Add
              </Button>
            )}
          </div>
          {selectedNamespaces.length > 0 && (
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {selectedNamespaces.map((namespace) => (
                <Label
                  key={namespace}
                  color="blue"
                  isCompact
                  onClose={isImporting ? undefined : () => handleRemoveNamespace(namespace)}
                >
                  {namespace}
                </Label>
              ))}
            </div>
          )}
        </FormGroup>

        {importSource === 'url' ? (
          <FormGroup
            label="GitHub Repository URL"
            isRequired
            fieldId="github-url-input"
          >
            <div style={{ fontSize: '0.875rem', color: '#6a6e73', marginBottom: '0.5rem' }}>
              Example: https://github.com/anthropics/skills/tree/main/skills/pptx
            </div>
            <TextInput
              type="text"
              value={githubUrl}
              onChange={(_event, value) => setGithubUrl(value)}
              placeholder="https://github.com/anthropics/skills/tree/main/skills/pptx"
              isDisabled={isImporting}
            />
          </FormGroup>
        ) : importSource === 'zip' ? (
          <FormGroup label="ZIP File" isRequired fieldId="zip-file-upload">
            <input
              type="file"
              accept=".zip"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) {
                  setZipFile(file);
                  setZipFileName(file.name);
                }
              }}
              disabled={isImporting}
              style={{ display: 'block', marginTop: '0.5rem' }}
            />
            {zipFileName && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
                Selected: {zipFileName}
                {!isImporting && (
                  <Button
                    variant="link"
                    onClick={() => {
                      setZipFile(null);
                      setZipFileName('');
                    }}
                    style={{ marginLeft: '0.5rem', padding: 0 }}
                  >
                    Clear
                  </Button>
                )}
              </div>
            )}
          </FormGroup>
        ) : (
          <FormGroup
            label="Local Folder Path"
            isRequired
            fieldId="folder-path-input"
          >
            <div style={{ fontSize: '0.875rem', color: '#6a6e73', marginBottom: '0.5rem' }}>
              Provide the absolute path to the folder containing the Anthropic skill files
            </div>
            <TextInput
              type="text"
              value={folderPath}
              onChange={(_event, value) => setFolderPath(value)}
              placeholder="/path/to/skill/folder"
              isDisabled={isImporting}
            />
          </FormGroup>
        )}

        {isImporting && (
          <div style={{ marginTop: '1rem' }}>
            <Progress
              value={progress}
              title="Importing skill"
              size={ProgressSize.sm}
              measureLocation={ProgressMeasureLocation.top}
            />
          </div>
        )}

        {result && (
          <Alert
            variant={result.success ? 'success' : 'danger'}
            title={result.success ? 'Success' : 'Error'}
            style={{ marginTop: '1rem' }}
            isInline
          >
            <p>{result.message}</p>
            {result.success && !batchMode && result.tools_created !== undefined && (
              <List>
                <ListItem>Skill: {result.skill_name}</ListItem>
                <ListItem>Tools created: {result.tools_created}</ListItem>
                <ListItem>Snippets created: {result.snippets_created}</ListItem>
                {result.ignored_files && result.ignored_files.length > 0 && (
                  <ListItem>
                    Ignored files ({result.ignored_files.length}):{' '}
                    {result.ignored_files.join(', ')}
                  </ListItem>
                )}
              </List>
            )}
            {batchMode && batchResults.length > 0 && (
              <div style={{ marginTop: '1rem' }}>
                <h4 style={{ marginBottom: '0.5rem' }}>Detailed Results:</h4>
                <List>
                  {batchResults.map((batchResult, index) => (
                    <ListItem key={index}>
                      <span style={{ color: batchResult.success ? 'green' : 'red' }}>
                        {batchResult.success ? '✓' : '✗'}
                      </span>{' '}
                      <strong>{batchResult.skill_name || `Skill ${index + 1}`}</strong>
                      {batchResult.success && (
                        <>
                          {' - '}
                          {batchResult.tools_created || 0} tool(s), {batchResult.snippets_created || 0} snippet(s)
                        </>
                      )}
                      {!batchResult.success && (
                        <>
                          {' - '}
                          <span style={{ color: 'red' }}>{batchResult.message}</span>
                        </>
                      )}
                    </ListItem>
                  ))}
                </List>
              </div>
            )}
          </Alert>
        )}
      </Form>
    </Modal>
  );
}