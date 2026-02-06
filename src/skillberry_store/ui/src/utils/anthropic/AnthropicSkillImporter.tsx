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
import { parseTextFiles } from './textParser';
import { parseCodeFiles } from './codeParser';
import JSZip from 'jszip';

const API_BASE_URL = '/api';

interface ImportProgress {
  stage: string;
  current: number;
  total: number;
  message: string;
}

interface ImportResult {
  success: boolean;
  message: string;
  details?: {
    toolsCreated: number;
    snippetsCreated: number;
    skillCreated: boolean;
    ignoredFiles: string[];
  };
}

interface AnthropicSkillImporterProps {
  isOpen: boolean;
  onClose: () => void;
  onImportComplete: () => void;
}

export function AnthropicSkillImporter({
  isOpen,
  onClose,
  onImportComplete,
}: AnthropicSkillImporterProps) {
  const [importSource, setImportSource] = useState<'url' | 'zip' | 'folder'>('folder');
  const [githubUrl, setGithubUrl] = useState('');
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [zipFileName, setZipFileName] = useState('');
  const [folderFiles, setFolderFiles] = useState<FileList | null>(null);
  const [folderName, setFolderName] = useState('');
  const [snippetMode, setSnippetMode] = useState<'file' | 'paragraph'>('file');
  const [isImporting, setIsImporting] = useState(false);
  const [progress, setProgress] = useState<ImportProgress | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);

  const resetState = () => {
    setGithubUrl('');
    setZipFile(null);
    setZipFileName('');
    setFolderFiles(null);
    setFolderName('');
    setProgress(null);
    setResult(null);
  };

  const handleClose = () => {
    if (!isImporting) {
      resetState();
      onClose();
    }
  };

  /**
   * Extract skill name from GitHub URL or zip filename
   */
  const extractSkillName = (url: string, filename: string): string => {
    if (url) {
      // Extract from URL like: https://github.com/anthropics/skills/tree/main/skills/pptx
      const match = url.match(/\/skills\/([^/]+)\/?$/);
      if (match) {
        return match[1];
      }
      // Fallback: use last part of URL
      const parts = url.split('/').filter(p => p);
      return parts[parts.length - 1] || 'anthropic_skill';
    }
    // Extract from filename
    return filename.replace(/\.(zip|tar\.gz|tgz)$/i, '').replace(/[^a-zA-Z0-9_]/g, '_');
  };

  /**
   * Parse SKILL.md file to extract name and description from header
   */
  const parseSkillMetadata = (files: Array<{ name: string; path: string; content: string }>): { name: string; description: string } | null => {
    const skillFile = files.find(f => f.name.toUpperCase() === 'SKILL.MD');
    if (!skillFile) {
      return null;
    }

    try {
      const content = skillFile.content;
      const lines = content.split('\n');
      let name = '';
      let description = '';
      let inHeader = false;

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        
        // Check for YAML front matter
        if (i === 0 && line === '---') {
          inHeader = true;
          continue;
        }
        
        if (inHeader) {
          if (line === '---') {
            // End of header
            break;
          }
          
          // Parse name field
          const nameMatch = line.match(/^name:\s*(.+)$/i);
          if (nameMatch) {
            name = nameMatch[1].trim().replace(/^["']|["']$/g, '');
          }
          
          // Parse description field
          const descMatch = line.match(/^description:\s*(.+)$/i);
          if (descMatch) {
            description = descMatch[1].trim().replace(/^["']|["']$/g, '');
          }
        }
      }

      if (name || description) {
        return { name, description };
      }
    } catch (error) {
      console.warn('Failed to parse SKILL.md metadata:', error);
    }

    return null;
  };

  /**
   * Fetch files from GitHub repository
   */
  const fetchFromGitHub = async (url: string): Promise<Array<{ name: string; path: string; content: string }>> => {
    setProgress({ stage: 'Fetching from GitHub', current: 0, total: 100, message: 'Connecting to GitHub...' });

    try {
      // Convert GitHub URL to API URL
      // From: https://github.com/anthropics/skills/tree/main/skills/pptx
      // To: https://api.github.com/repos/anthropics/skills/contents/skills/pptx
      const apiUrl = url
        .replace('github.com', 'api.github.com/repos')
        .replace('/tree/main/', '/contents/')
        .replace('/tree/master/', '/contents/');

      console.log('Fetching from GitHub API URL:', apiUrl);

      const files: Array<{ name: string; path: string; content: string }> = [];

      const fetchDirectory = async (dirUrl: string, basePath = ''): Promise<void> => {
        try {
          const response = await fetch(dirUrl);
          if (!response.ok) {
            const errorText = await response.text().catch(() => response.statusText);
            throw new Error(`GitHub API returned ${response.status}: ${errorText || response.statusText}`);
          }

          const items = await response.json();
          
          for (const item of items) {
            if (item.type === 'file') {
              // Fetch file content
              try {
                const contentResponse = await fetch(item.download_url);
                if (contentResponse.ok) {
                  const content = await contentResponse.text();
                  const relativePath = basePath ? `${basePath}/${item.name}` : item.name;
                  files.push({
                    name: item.name,
                    path: relativePath,
                    content,
                  });
                } else {
                  console.warn(`Failed to fetch file ${item.name}: ${contentResponse.statusText}`);
                }
              } catch (error) {
                console.warn(`Error fetching file ${item.name}:`, error);
              }
            } else if (item.type === 'dir') {
              // Recursively fetch subdirectory
              const relativePath = basePath ? `${basePath}/${item.name}` : item.name;
              await fetchDirectory(item.url, relativePath);
            }
          }
        } catch (error) {
          throw new Error(`Failed to fetch directory ${dirUrl}: ${(error as Error).message}`);
        }
      };

      await fetchDirectory(apiUrl);
      return files;
    } catch (error) {
      const errorMessage = (error as Error).message || 'Unknown error';
      console.error('GitHub fetch error:', error);
      throw new Error(`Failed to fetch from GitHub: ${errorMessage}. Please check the URL and try again, or use a ZIP file instead.`);
    }
  };

  /**
   * Extract files from ZIP
   */
  const extractFromZip = async (file: File): Promise<Array<{ name: string; path: string; content: string }>> => {
    setProgress({ stage: 'Extracting ZIP', current: 0, total: 100, message: 'Reading ZIP file...' });

    const zip = new JSZip();
    const zipContent = await zip.loadAsync(file);
    const files: Array<{ name: string; path: string; content: string }> = [];

    const fileEntries = Object.entries(zipContent.files);
    let processed = 0;

    for (const [path, zipEntry] of fileEntries) {
      if (!zipEntry.dir && zipEntry.name) {
        try {
          const content = await zipEntry.async('text');
          const name = path.split('/').pop() || path;
          files.push({ name, path, content });
        } catch (error) {
          console.warn(`Failed to extract ${path}:`, error);
        }
      }
      processed++;
      setProgress({
        stage: 'Extracting ZIP',
        current: processed,
        total: fileEntries.length,
        message: `Extracted ${processed}/${fileEntries.length} files`,
      });
    }

    return files;
  };

  /**
   * Extract files from folder (FileList)
   */
  const extractFromFolder = async (fileList: FileList): Promise<Array<{ name: string; path: string; content: string }>> => {
    setProgress({ stage: 'Reading Folder', current: 0, total: fileList.length, message: 'Reading files...' });

    const files: Array<{ name: string; path: string; content: string }> = [];
    
    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      try {
        const content = await file.text();
        // webkitRelativePath gives us the full path including folder name
        const path = (file as any).webkitRelativePath || file.name;
        const name = file.name;
        files.push({ name, path, content });
      } catch (error) {
        console.warn(`Failed to read ${file.name}:`, error);
      }
      
      setProgress({
        stage: 'Reading Folder',
        current: i + 1,
        total: fileList.length,
        message: `Read ${i + 1}/${fileList.length} files`,
      });
    }

    return files;
  };

  /**
   * Create tools from parsed data
   * Returns array of successfully created tool UUIDs
   */
  const createTools = async (tools: any[]): Promise<string[]> => {
    const createdToolUuids: string[] = [];

    for (let i = 0; i < tools.length; i++) {
      const tool = tools[i];
      setProgress({
        stage: 'Creating Tools',
        current: i + 1,
        total: tools.length,
        message: `Creating tool: ${tool.name}`,
      });

      try {
        const formData = new FormData();
        const moduleBlob = new Blob([tool.moduleContent], { type: 'text/plain' });
        formData.append('module', moduleBlob, `${tool.name}.${tool.programmingLanguage === 'python' ? 'py' : 'sh'}`);

        // Build query parameters - tags need to be sent as individual parameters for FastAPI to parse as a list
        const params = new URLSearchParams({
          name: tool.name,
          version: tool.version,
          description: tool.description,
        });
        
        // Add each tag as a separate parameter so FastAPI parses it as a list
        if (tool.tags && Array.isArray(tool.tags)) {
          tool.tags.forEach((tag: string) => {
            params.append('tags', tag);
          });
        }

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
          const createdTool = await response.json();
          if (createdTool.uuid) {
            createdToolUuids.push(createdTool.uuid);
          }
        } else {
          const errorText = await response.text();
          console.error(`Failed to create tool ${tool.name}:`, errorText);
        }
      } catch (error) {
        console.error(`Error creating tool ${tool.name}:`, error);
      }
    }

    return createdToolUuids;
  };

  /**
   * Create snippets from parsed data
   * Returns array of successfully created snippet UUIDs
   */
  const createSnippets = async (snippets: any[]): Promise<string[]> => {
    const createdSnippetUuids: string[] = [];

    for (let i = 0; i < snippets.length; i++) {
      const snippet = snippets[i];
      setProgress({
        stage: 'Creating Snippets',
        current: i + 1,
        total: snippets.length,
        message: `Creating snippet: ${snippet.name}`,
      });

      try {
        // Build query parameters for form data
        const params = new URLSearchParams({
          name: snippet.name,
          version: snippet.version,
          description: snippet.description,
          content: snippet.content,
          content_type: 'text/plain',
          state: 'approved',
        });
        
        // Add each tag as a separate parameter
        if (snippet.tags && Array.isArray(snippet.tags)) {
          snippet.tags.forEach((tag: string) => {
            params.append('tags', tag);
          });
        }

        const response = await fetch(`${API_BASE_URL}/snippets/?${params}`, {
          method: 'POST',
        });

        if (response.ok) {
          const createdSnippet = await response.json();
          if (createdSnippet.uuid) {
            createdSnippetUuids.push(createdSnippet.uuid);
          }
        } else {
          const errorText = await response.text();
          console.error(`Failed to create snippet ${snippet.name}:`, errorText);
        }
      } catch (error) {
        console.error(`Error creating snippet ${snippet.name}:`, error);
      }
    }

    return createdSnippetUuids;
  };

  /**
   * Create skill with tool and snippet UUIDs
   */
  const createSkill = async (
    skillName: string,
    skillDescription: string,
    toolUuids: string[],
    snippetUuids: string[]
  ): Promise<boolean> => {
    setProgress({
      stage: 'Creating Skill',
      current: 1,
      total: 1,
      message: `Creating skill: ${skillName}`,
    });

    try {
      // Build query parameters for form data
      const params = new URLSearchParams({
        name: skillName,
        version: '1.0.0',
        description: skillDescription,
      });
      
      // Add tags
      params.append('tags', 'anthropic');
      params.append('tags', 'imported');
      
      // Add tool and snippet UUIDs
      toolUuids.forEach(uuid => params.append('tool_uuids', uuid));
      snippetUuids.forEach(uuid => params.append('snippet_uuids', uuid));

      const response = await fetch(`${API_BASE_URL}/skills/?${params}`, {
        method: 'POST',
      });

      return response.ok;
    } catch (error) {
      console.error('Error creating skill:', error);
      return false;
    }
  };

  /**
   * Main import handler
   */
  const handleImport = async () => {
    setIsImporting(true);
    setResult(null);

    try {
      // Step 1: Get files
      let files: Array<{ name: string; path: string; content: string }>;
      let skillName: string;

      if (importSource === 'url') {
        if (!githubUrl) {
          throw new Error('Please provide a GitHub URL');
        }
        skillName = extractSkillName(githubUrl, '');
        files = await fetchFromGitHub(githubUrl);
      } else if (importSource === 'zip') {
        if (!zipFile) {
          throw new Error('Please select a ZIP file');
        }
        skillName = extractSkillName('', zipFile.name);
        files = await extractFromZip(zipFile);
      } else {
        // folder
        if (!folderFiles || folderFiles.length === 0) {
          throw new Error('Please select a folder');
        }
        // Extract folder name from the first file's path
        const firstFilePath = (folderFiles[0] as any).webkitRelativePath || folderFiles[0].name;
        const folderNameFromPath = firstFilePath.split('/')[0];
        skillName = extractSkillName('', folderNameFromPath);
        files = await extractFromFolder(folderFiles);
      }

      if (files.length === 0) {
        throw new Error('No files found to import');
      }

      // Step 2: Parse SKILL.md metadata if available
      const skillMetadata = parseSkillMetadata(files);
      if (skillMetadata?.name) {
        skillName = skillMetadata.name;
      }
      const skillDescription = skillMetadata?.description || `Anthropic skill imported from ${importSource === 'url' ? 'GitHub' : 'ZIP file'}`;

      // Step 3: Parse files
      setProgress({
        stage: 'Parsing Files',
        current: 0,
        total: files.length,
        message: 'Analyzing files...',
      });

      // Parse files based on snippet mode
      let snippets: any[];
      let tools: any[];
      let ignoredFiles: string[];
      
      if (snippetMode === 'file') {
        // In file mode, import all non-code files as snippets
        const codeParseResult = parseCodeFiles(files, skillName);
        tools = codeParseResult.tools;
        
        // Get all files that weren't parsed as tools
        const toolFileNames = new Set(tools.map(t => t.sourceFileName));
        const nonCodeFiles = files.filter(f => !toolFileNames.has(f.name));
        
        // Import all non-code files as complete file snippets (no files are ignored in complete file mode)
        snippets = parseTextFiles(nonCodeFiles, skillName, false);
        ignoredFiles = []; // No files are ignored in complete file mode
      } else {
        // In paragraph mode, only parse text files and split by paragraph
        snippets = parseTextFiles(files, skillName, true);
        const codeParseResult = parseCodeFiles(files, skillName);
        tools = codeParseResult.tools;
        ignoredFiles = codeParseResult.ignoredFiles;
      }

      console.log(`Parsed ${tools.length} tools and ${snippets.length} snippets`);
      if (ignoredFiles.length > 0) {
        console.log('Ignored files:', ignoredFiles);
      }

      // Step 4: Create tools and get UUIDs of successfully created ones
      const createdToolUuids = tools.length > 0 ? await createTools(tools) : [];

      // Step 5: Create snippets and get UUIDs of successfully created ones
      const createdSnippetUuids = snippets.length > 0 ? await createSnippets(snippets) : [];

      // Step 6: Create skill with all successfully created tool and snippet UUIDs
      const skillCreated = await createSkill(skillName, skillDescription, createdToolUuids, createdSnippetUuids);

      setResult({
        success: true,
        message: `Successfully imported Anthropic skill "${skillName}"`,
        details: {
          toolsCreated: createdToolUuids.length,
          snippetsCreated: createdSnippetUuids.length,
          skillCreated,
          ignoredFiles,
        },
      });

      onImportComplete();
    } catch (error) {
      setResult({
        success: false,
        message: `Import failed: ${(error as Error).message}`,
      });
    } finally {
      setIsImporting(false);
      setProgress(null);
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
          isDisabled={!result && (isImporting || (importSource === 'url' ? !githubUrl : importSource === 'folder' ? !folderFiles : !zipFile))}
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
              variant={importSource === 'folder' ? 'primary' : 'secondary'}
              onClick={() => setImportSource('folder')}
              isDisabled={isImporting}
            >
              Local Folder
            </Button>
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

        {importSource === 'folder' ? (
          <FormGroup label="Local Folder" isRequired fieldId="folder-upload">
            <Button
              variant="secondary"
              onClick={() => document.getElementById('folder-input')?.click()}
              isDisabled={isImporting}
            >
              Choose Skill Folder
            </Button>
            <input
              id="folder-input"
              type="file"
              /* @ts-ignore - webkitdirectory is not in TypeScript types but is widely supported */
              webkitdirectory=""
              directory=""
              multiple
              onChange={(e) => {
                const files = e.target.files;
                if (files && files.length > 0) {
                  setFolderFiles(files);
                  const firstFilePath = (files[0] as any).webkitRelativePath || files[0].name;
                  const folderNameFromPath = firstFilePath.split('/')[0];
                  setFolderName(folderNameFromPath);
                }
              }}
              disabled={isImporting}
              style={{ display: 'none' }}
            />
            {folderName && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
                Selected: {folderName} ({folderFiles?.length || 0} files)
                {!isImporting && (
                  <Button
                    variant="link"
                    onClick={() => {
                      setFolderFiles(null);
                      setFolderName('');
                    }}
                    style={{ marginLeft: '0.5rem', padding: 0 }}
                  >
                    Clear
                  </Button>
                )}
              </div>
            )}
          </FormGroup>
        ) : importSource === 'url' ? (
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
        ) : (
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
        )}

        {progress && (
          <div style={{ marginTop: '1rem' }}>
            <Progress
              value={(progress.current / progress.total) * 100}
              title={progress.stage}
              size={ProgressSize.sm}
              measureLocation={ProgressMeasureLocation.top}
              label={progress.message}
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
            {result.details && (
              <List>
                <ListItem>Tools created: {result.details.toolsCreated}</ListItem>
                <ListItem>Snippets created: {result.details.snippetsCreated}</ListItem>
                <ListItem>Skill created: {result.details.skillCreated ? 'Yes' : 'No'}</ListItem>
                {result.details.ignoredFiles.length > 0 && (
                  <ListItem>
                    Ignored files ({result.details.ignoredFiles.length}):{' '}
                    {result.details.ignoredFiles.join(', ')}
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