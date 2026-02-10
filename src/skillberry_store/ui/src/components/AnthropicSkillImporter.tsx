// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState } from 'react';
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
} from '@patternfly/react-core';

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
  const [isImporting, setIsImporting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<ImportResult | null>(null);

  const resetState = () => {
    setGithubUrl('');
    setZipFile(null);
    setZipFileName('');
    setFolderPath('');
    setProgress(0);
    setResult(null);
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