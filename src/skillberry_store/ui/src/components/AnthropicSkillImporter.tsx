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

interface BatchImportResult {
  success: boolean;
  message: string;
  total_skills: number;
  successful_imports: number;
  failed_imports: number;
  results: ImportResult[];
}

export function AnthropicSkillImporter({
  isOpen,
  onClose,
  onImportComplete,
}: AnthropicSkillImporterProps) {
  const [importSource, setImportSource] = useState<'url' | 'zip' | 'folder'>('url');
  const [githubUrl, setGithubUrl] = useState('');
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [zipFileName, setZipFileName] = useState('');
  const [folderPath, setFolderPath] = useState('');
  const [snippetMode, setSnippetMode] = useState<'file' | 'paragraph'>('file');
  const [treatAllAsDocuments, setTreatAllAsDocuments] = useState(false);
  const [batchMode, setBatchMode] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [batchResult, setBatchResult] = useState<BatchImportResult | null>(null);
  const [currentSkillImporting, setCurrentSkillImporting] = useState<string>('');
  
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
    setBatchResult(null);
    setCurrentSkillImporting('');
    setSelectedNamespaces([]);
    setNamespaceInput('');
    setBatchMode(false);
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

  /**
   * Detects child skill directories from a parent directory URL or path
   */
  const detectChildSkills = async (
    sourceType: 'url' | 'folder',
    sourcePath: string
  ): Promise<string[]> => {
    try {
      const formData = new FormData();
      formData.append('source_type', sourceType);
      
      if (sourceType === 'url') {
        formData.append('github_url', sourcePath);
      } else {
        formData.append('folder_path', sourcePath);
      }
      
      const response = await fetch('/api/skills/detect-anthropic-skills', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `Detection failed: ${response.statusText}`);
      }

      const data = await response.json();
      return data.skill_paths || [];
    } catch (error) {
      console.error('Failed to detect child skills:', error);
      throw error;
    }
  };

  /**
   * Imports a single skill
   */
  const importSingleSkill = async (
    sourceType: 'url' | 'zip' | 'folder',
    sourcePath: string,
    skillPath?: string
  ): Promise<ImportResult> => {
    const formData = new FormData();
    formData.append('source_type', sourceType);
    formData.append('snippet_mode', snippetMode);
    formData.append('treat_all_as_documents', treatAllAsDocuments.toString());
    
    // Add namespaces as additional tags with namespace: prefix
    const namespacesToUse = selectedNamespaces.length > 0 ? selectedNamespaces : ['default'];
    namespacesToUse.forEach(namespace => {
      formData.append('tags', `namespace:${namespace}`);
    });

    if (sourceType === 'url') {
      // For batch mode, append the skill_path to the base URL
      const fullUrl = skillPath ? `${sourcePath}/${skillPath}` : sourcePath;
      formData.append('github_url', fullUrl);
    } else if (sourceType === 'zip') {
      if (!zipFile) {
        throw new Error('ZIP file is required');
      }
      formData.append('zip_file', zipFile);
    } else if (sourceType === 'folder') {
      const fullPath = skillPath ? `${sourcePath}/${skillPath}` : sourcePath;
      formData.append('folder_path', fullPath);
    }

    const response = await fetch('/api/skills/import-anthropic', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Import failed: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      success: true,
      message: data.message || 'Import successful',
      skill_name: data.skill_name,
      tools_created: data.tools_created,
      snippets_created: data.snippets_created,
      ignored_files: data.ignored_files || [],
    };
  };

  /**
   * Handles batch import of multiple skills
   */
  const handleBatchImport = async () => {
    setIsImporting(true);
    setBatchResult(null);
    setProgress(5);

    try {
      // Validate input
      if (importSource === 'url' && !githubUrl) {
        throw new Error('Please provide a GitHub URL');
      } else if (importSource === 'folder' && !folderPath) {
        throw new Error('Please provide a folder path');
      } else if (importSource === 'zip') {
        throw new Error('Batch import is not supported for ZIP files. Please use URL or Local Folder.');
      }

      const sourcePath = importSource === 'url' ? githubUrl : folderPath;
      
      // Step 1: Detect child skills
      setProgress(10);
      const skillPaths = await detectChildSkills(importSource, sourcePath);
      
      if (skillPaths.length === 0) {
        throw new Error('No skills detected in the parent directory. Make sure subdirectories contain SKILL.md files.');
      }

      setProgress(20);

      // Step 2: Import each skill sequentially
      const results: ImportResult[] = [];
      let successCount = 0;
      let failCount = 0;

      for (let i = 0; i < skillPaths.length; i++) {
        const skillPath = skillPaths[i];
        setCurrentSkillImporting(skillPath);
        
        // Update progress: 20% to 90% for imports
        const importProgress = 20 + ((i / skillPaths.length) * 70);
        setProgress(Math.round(importProgress));

        try {
          const result = await importSingleSkill(importSource, sourcePath, skillPath);
          results.push(result);
          successCount++;
        } catch (error) {
          const errorResult: ImportResult = {
            success: false,
            message: `Failed to import ${skillPath}: ${(error as Error).message}`,
            skill_name: skillPath,
          };
          results.push(errorResult);
          failCount++;
        }
      }

      setProgress(100);
      setCurrentSkillImporting('');

      // Set batch result
      setBatchResult({
        success: successCount > 0,
        message: `Batch import completed: ${successCount} successful, ${failCount} failed`,
        total_skills: skillPaths.length,
        successful_imports: successCount,
        failed_imports: failCount,
        results,
      });

      if (successCount > 0) {
        onImportComplete();
      }
    } catch (error) {
      setBatchResult({
        success: false,
        message: `Batch import failed: ${(error as Error).message}`,
        total_skills: 0,
        successful_imports: 0,
        failed_imports: 0,
        results: [],
      });
    } finally {
      setIsImporting(false);
    }
  };

  /**
   * Handles single skill import
   */
  const handleSingleImport = async () => {
    setIsImporting(true);
    setResult(null);
    setProgress(10);

    try {
      // Validate input
      if (importSource === 'url' && !githubUrl) {
        throw new Error('Please provide a GitHub URL');
      } else if (importSource === 'zip' && !zipFile) {
        throw new Error('Please select a ZIP file');
      } else if (importSource === 'folder' && !folderPath) {
        throw new Error('Please provide a folder path');
      }

      setProgress(30);

      const sourcePath = importSource === 'url' ? githubUrl : importSource === 'folder' ? folderPath : '';
      const importResult = await importSingleSkill(importSource, sourcePath);

      setProgress(100);
      setResult(importResult);
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

  const handleImport = async () => {
    if (batchMode) {
      await handleBatchImport();
    } else {
      await handleSingleImport();
    }
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
          onClick={(result || batchResult) ? handleClose : handleImport}
          isDisabled={
            !(result || batchResult) && 
            (isImporting || 
              (importSource === 'url' ? !githubUrl : 
                importSource === 'zip' ? !zipFile : 
                !folderPath))
          }
        >
          {isImporting ? <Spinner size="md" /> : (result || batchResult) ? 'Done' : 'Import'}
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

        <FormGroup label="Import Mode">
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
              Batch Mode - Import multiple skills from parent directory
            </label>
          </div>
          <div style={{ fontSize: '0.875rem', color: '#6a6e73' }}>
            {batchMode 
              ? 'The system will detect all subdirectories containing SKILL.md files and import them sequentially.'
              : 'Import a single skill from the specified location.'}
            {importSource === 'zip' && ' (Batch mode is not available for ZIP files)'}
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
              {batchMode 
                ? 'Example (parent): https://github.com/anthropics/skills/tree/main/skills'
                : 'Example (single): https://github.com/anthropics/skills/tree/main/skills/pptx'}
            </div>
            <TextInput
              type="text"
              value={githubUrl}
              onChange={(_event, value) => setGithubUrl(value)}
              placeholder={batchMode 
                ? 'https://github.com/anthropics/skills/tree/main/skills'
                : 'https://github.com/anthropics/skills/tree/main/skills/pptx'}
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
              {batchMode 
                ? 'Provide the absolute path to the parent folder containing multiple skill subdirectories'
                : 'Provide the absolute path to the folder containing the Anthropic skill files'}
            </div>
            <TextInput
              type="text"
              value={folderPath}
              onChange={(_event, value) => setFolderPath(value)}
              placeholder={batchMode ? '/path/to/parent/folder' : '/path/to/skill/folder'}
              isDisabled={isImporting}
            />
          </FormGroup>
        )}

        {isImporting && (
          <div style={{ marginTop: '1rem' }}>
            <Progress
              value={progress}
              title={batchMode && currentSkillImporting 
                ? `Importing: ${currentSkillImporting}` 
                : batchMode 
                  ? 'Importing skills...' 
                  : 'Importing skill'}
              size={ProgressSize.sm}
              measureLocation={ProgressMeasureLocation.top}
            />
          </div>
        )}

        {/* Single import result */}
        {result && !batchMode && (
          <Alert
            variant={result.success ? 'success' : 'danger'}
            title={result.success ? 'Success' : 'Error'}
            style={{ marginTop: '1rem' }}
            isInline
          >
            <p>{result.message}</p>
            {result.success && result.tools_created !== undefined && (
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
          </Alert>
        )}

        {/* Batch import result */}
        {batchResult && batchMode && (
          <Alert
            variant={batchResult.success ? 'success' : 'danger'}
            title={batchResult.success ? 'Batch Import Completed' : 'Batch Import Failed'}
            style={{ marginTop: '1rem' }}
            isInline
          >
            <p>{batchResult.message}</p>
            {batchResult.total_skills > 0 && (
              <div style={{ marginTop: '1rem' }}>
                <strong>Summary:</strong>
                <List>
                  <ListItem>Total skills detected: {batchResult.total_skills}</ListItem>
                  <ListItem>Successful imports: {batchResult.successful_imports}</ListItem>
                  <ListItem>Failed imports: {batchResult.failed_imports}</ListItem>
                </List>
                
                {batchResult.results.length > 0 && (
                  <div style={{ marginTop: '1rem' }}>
                    <strong>Details:</strong>
                    <List>
                      {batchResult.results.map((res, idx) => (
                        <ListItem key={idx}>
                          {res.success ? '✓' : '✗'} {res.skill_name || `Skill ${idx + 1}`}
                          {res.success && res.tools_created !== undefined && (
                            <span style={{ marginLeft: '0.5rem', fontSize: '0.875rem', color: '#6a6e73' }}>
                              ({res.tools_created} tools, {res.snippets_created} snippets)
                            </span>
                          )}
                          {!res.success && (
                            <div style={{ marginLeft: '1rem', fontSize: '0.875rem', color: '#c9190b' }}>
                              {res.message}
                            </div>
                          )}
                        </ListItem>
                      ))}
                    </List>
                  </div>
                )}
              </div>
            )}
          </Alert>
        )}
      </Form>
    </Modal>
  );
}
