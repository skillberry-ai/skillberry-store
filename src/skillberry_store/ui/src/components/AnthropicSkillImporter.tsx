// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
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
  const [isImporting, setIsImporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [selectedNamespaces, setSelectedNamespaces] = useState<string[]>([]);
  const [isNamespaceSelectOpen, setIsNamespaceSelectOpen] = useState(false);
  const [namespaceSearchTerm, setNamespaceSearchTerm] = useState('');
  const [newNamespaceInput, setNewNamespaceInput] = useState('');

  // Fetch all skills to extract existing namespaces
  const { data: skills } = useQuery({
    queryKey: ['skills'],
    queryFn: skillsApi.list,
  });

  // Extract unique namespaces from skills' tags (tags starting with "namespace:")
  const existingNamespaces = useMemo(() => {
    if (!skills) return [];
    const namespaceSet = new Set<string>();
    skills.forEach(skill => {
      skill.tags?.forEach(tag => {
        if (tag.startsWith('namespace:')) {
          const namespace = tag.substring('namespace:'.length);
          namespaceSet.add(namespace);
        }
      });
    });
    return Array.from(namespaceSet).sort();
  }, [skills]);

  // Filter namespaces based on search term
  const filteredNamespaces = useMemo(() => {
    const lowerSearch = namespaceSearchTerm.toLowerCase();
    return existingNamespaces.filter(namespace =>
      namespace.toLowerCase().includes(lowerSearch) &&
      !selectedNamespaces.includes(namespace)
    );
  }, [existingNamespaces, namespaceSearchTerm, selectedNamespaces]);

  const resetState = () => {
    setGithubUrl('');
    setZipFile(null);
    setZipFileName('');
    setFolderPath('');
    setProgress(0);
    setResult(null);
    setSelectedNamespaces([]);
    setNewNamespaceInput('');
    setNamespaceSearchTerm('');
  };

  const handleClose = () => {
    if (!isImporting) {
      resetState();
      onClose();
    }
  };

  const handleImport = async () => {
    setIsImporting(true);
    setResult(null);
    setProgress(10);

    try {
      // Prepare form data
      const formData = new FormData();
      formData.append('source_type', importSource);
      formData.append('snippet_mode', snippetMode);
      formData.append('treat_all_as_documents', treatAllAsDocuments.toString());
      
      // Add namespaces as tags (prefixed with "namespace:")
      selectedNamespaces.forEach(namespace => {
        formData.append('namespaces', namespace);
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

        <FormGroup label="Namespaces (Optional)">
          <div style={{ fontSize: '0.875rem', color: '#6a6e73', marginBottom: '0.5rem' }}>
            Add one or more namespaces to label all imported objects (skills, tools, snippets). If no namespaces are specified, objects will be imported without namespace labels.
          </div>
          
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <Select
              id="namespace-select"
              isOpen={isNamespaceSelectOpen}
              selected={null}
              onSelect={(_event, value) => {
                if (typeof value === 'string' && value && !selectedNamespaces.includes(value)) {
                  setSelectedNamespaces([...selectedNamespaces, value]);
                  setIsNamespaceSelectOpen(false);
                  setNamespaceSearchTerm('');
                }
              }}
              onOpenChange={(isOpen) => setIsNamespaceSelectOpen(isOpen)}
              toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                <MenuToggle
                  ref={toggleRef}
                  onClick={() => setIsNamespaceSelectOpen(!isNamespaceSelectOpen)}
                  isExpanded={isNamespaceSelectOpen}
                  isDisabled={isImporting}
                  style={{ width: '200px' }}
                >
                  Select existing namespace
                </MenuToggle>
              )}
            >
              <SelectList>
                <input
                  type="search"
                  value={namespaceSearchTerm}
                  onChange={(e) => setNamespaceSearchTerm(e.target.value)}
                  placeholder="Search namespaces..."
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    border: 'none',
                    borderBottom: '1px solid #d2d2d2',
                    outline: 'none',
                  }}
                />
                {filteredNamespaces.length === 0 ? (
                  <SelectOption isDisabled>
                    {namespaceSearchTerm ? 'No namespaces found' : existingNamespaces.length === 0 ? 'No existing namespaces' : 'All namespaces selected'}
                  </SelectOption>
                ) : (
                  filteredNamespaces.map((namespace) => (
                    <SelectOption key={namespace} value={namespace}>
                      {namespace}
                    </SelectOption>
                  ))
                )}
              </SelectList>
            </Select>
            
            <div style={{ display: 'flex', gap: '0.5rem', flex: 1 }}>
              <TextInput
                type="text"
                value={newNamespaceInput}
                onChange={(_event, value) => setNewNamespaceInput(value)}
                placeholder="Or add new namespace"
                isDisabled={isImporting}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    if (newNamespaceInput.trim() && !selectedNamespaces.includes(newNamespaceInput.trim())) {
                      setSelectedNamespaces([...selectedNamespaces, newNamespaceInput.trim()]);
                      setNewNamespaceInput('');
                    }
                  }
                }}
              />
              <Button
                variant="secondary"
                onClick={() => {
                  if (newNamespaceInput.trim() && !selectedNamespaces.includes(newNamespaceInput.trim())) {
                    setSelectedNamespaces([...selectedNamespaces, newNamespaceInput.trim()]);
                    setNewNamespaceInput('');
                  }
                }}
                isDisabled={isImporting || !newNamespaceInput.trim()}
              >
                Add
              </Button>
            </div>
          </div>
          
          {selectedNamespaces.length > 0 && (
            <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
              {selectedNamespaces.map((namespace) => (
                <Label
                  key={namespace}
                  color="blue"
                  isCompact
                  onClose={isImporting ? undefined : () => {
                    setSelectedNamespaces(selectedNamespaces.filter(ns => ns !== namespace));
                  }}
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
      </Form>
    </Modal>
  );
}