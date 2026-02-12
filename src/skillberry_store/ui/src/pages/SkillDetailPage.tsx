// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTagColor } from '../utils/tagColors';
import {
  PageSection,
  Title,
  Breadcrumb,
  BreadcrumbItem,
  Card,
  CardBody,
  CardTitle,
  Spinner,
  Alert,
  DescriptionList,
  DescriptionListGroup,
  DescriptionListTerm,
  DescriptionListDescription,
  Label,
  Text,
  Button,
  Modal,
  ModalVariant,
  Form,
  FormGroup,
  TextInput,
  TextArea,
  Tabs,
  Tab,
  TabTitleText,
  CodeBlock,
  CodeBlockCode,
  Select,
  SelectOption,
  SelectList,
  MenuToggle,
  MenuToggleElement,
  TreeView,
  TreeViewDataItem,
} from '@patternfly/react-core';
import { EditIcon, TrashIcon, FolderIcon, FileIcon, FileCodeIcon, ExportIcon } from '@patternfly/react-icons';
import { skillsApi, toolsApi, snippetsApi } from '@/services/api';
import type { Skill } from '@/types';

export function SkillDetailPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [activeTabKey, setActiveTabKey] = useState<string | number>(0);
  const [editedSkill, setEditedSkill] = useState({
    name: '',
    version: '',
    description: '',
    tags: [] as string[],
    toolNames: [] as string[],
    snippetNames: [] as string[],
  });
  const [tagInput, setTagInput] = useState('');
  const [editError, setEditError] = useState('');
  
  // Select dropdown states
  const [isToolSelectOpen, setIsToolSelectOpen] = useState(false);
  const [isSnippetSelectOpen, setIsSnippetSelectOpen] = useState(false);
  const [toolSearchTerm, setToolSearchTerm] = useState('');
  const [snippetSearchTerm, setSnippetSearchTerm] = useState('');
  
  // Tree view states
  const [selectedToolItem, setSelectedToolItem] = useState<string | null>(null);
  const [selectedSnippetItem, setSelectedSnippetItem] = useState<string | null>(null);

  const { data: skill, isLoading, error } = useQuery({
    queryKey: ['skills', name],
    queryFn: () => skillsApi.get(name!),
    enabled: !!name,
  });

  // Fetch all tools for the dropdown
  const { data: allTools } = useQuery({
    queryKey: ['tools'],
    queryFn: toolsApi.list,
  });

  // Fetch all snippets for the dropdown
  const { data: allSnippets } = useQuery({
    queryKey: ['snippets'],
    queryFn: snippetsApi.list,
  });

  // Fetch tool modules for all tools in the skill
  const { data: toolModules } = useQuery({
    queryKey: ['skill-tools-modules', name, skill?.tools],
    queryFn: async () => {
      if (!skill?.tools || skill.tools.length === 0) return [];
      const modules = await Promise.all(
        skill.tools.map(async (tool) => {
          try {
            const module = await toolsApi.getModule(tool.name);
            return { name: tool.name, module };
          } catch (error) {
            return { name: tool.name, module: `// Error loading module for ${tool.name}` };
          }
        })
      );
      return modules;
    },
    enabled: !!skill?.tools && skill.tools.length > 0,
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (updatedSkill: Skill) =>
      skillsApi.update(name!, updatedSkill),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills', name] });
      queryClient.invalidateQueries({ queryKey: ['skills'] });
      setIsEditModalOpen(false);
      setEditError('');
    },
    onError: (error: any) => {
      setEditError(error.message || 'Failed to update skill');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => skillsApi.delete(name!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills'] });
      navigate('/skills');
    },
  });

  const handleEditClick = () => {
    if (skill) {
      setEditedSkill({
        name: skill.name,
        version: skill.version || '',
        description: skill.description,
        tags: skill.tags || [],
        toolNames: skill.tools?.map(t => t.name) || [],
        snippetNames: skill.snippets?.map(s => s.name) || [],
      });
      setIsEditModalOpen(true);
    }
  };

  const handleUpdateSkill = async () => {
    if (!editedSkill.name || !editedSkill.description) {
      setEditError('Please fill in all required fields');
      return;
    }
    
    try {
      // Fetch tool and snippet UUIDs
      const toolPromises = editedSkill.toolNames.map(name =>
        fetch(`/api/tools/${name}`).then(r => r.json())
      );
      const snippetPromises = editedSkill.snippetNames.map(name =>
        fetch(`/api/snippets/${name}`).then(r => r.json())
      );
      
      const tools = await Promise.all(toolPromises);
      const snippets = await Promise.all(snippetPromises);
      
      // Build skill object for request body
      const updatedSkill = {
        uuid: skill!.uuid,
        name: editedSkill.name,
        version: editedSkill.version,
        description: editedSkill.description,
        tags: editedSkill.tags,
        tool_uuids: tools.map(t => t.uuid),
        snippet_uuids: snippets.map(s => s.uuid),
        state: skill!.state,
      };
      
      // Call API with JSON body
      const response = await fetch(`/api/skills/${name}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedSkill),
      });
      
      if (response.ok) {
        queryClient.invalidateQueries({ queryKey: ['skills'] });
        queryClient.invalidateQueries({ queryKey: ['skills', name] });
        setIsEditModalOpen(false);
      } else {
        const errorText = await response.text();
        setEditError(`Failed to update skill: ${errorText}`);
      }
    } catch (error) {
      setEditError('Failed to fetch tools or snippets. Please ensure they exist.');
    }
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !editedSkill.tags.includes(tagInput.trim())) {
      setEditedSkill({
        ...editedSkill,
        tags: [...editedSkill.tags, tagInput.trim()],
      });
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setEditedSkill({
      ...editedSkill,
      tags: editedSkill.tags.filter(tag => tag !== tagToRemove),
    });
  };

  // Filter tools based on search term - only when modal is open
  const filteredTools = useMemo(() => {
    if (!isEditModalOpen || !allTools) return [];
    const lowerSearch = toolSearchTerm.toLowerCase();
    return allTools.filter(tool =>
      tool.name.toLowerCase().includes(lowerSearch) &&
      !editedSkill.toolNames.includes(tool.name)
    );
  }, [isEditModalOpen, allTools, toolSearchTerm, editedSkill.toolNames]);

  // Filter snippets based on search term - only when modal is open
  const filteredSnippets = useMemo(() => {
    if (!isEditModalOpen || !allSnippets) return [];
    const lowerSearch = snippetSearchTerm.toLowerCase();
    return allSnippets.filter(snippet =>
      snippet.name.toLowerCase().includes(lowerSearch) &&
      !editedSkill.snippetNames.includes(snippet.name)
    );
  }, [isEditModalOpen, allSnippets, snippetSearchTerm, editedSkill.snippetNames]);

  const handleSelectTool = (_event: React.MouseEvent | undefined, value: string | number | undefined) => {
    if (typeof value === 'string' && value && !editedSkill.toolNames.includes(value)) {
      setEditedSkill({
        ...editedSkill,
        toolNames: [...editedSkill.toolNames, value],
      });
      setIsToolSelectOpen(false);
      setToolSearchTerm('');
    }
  };

  const handleRemoveTool = (toolToRemove: string) => {
    setEditedSkill({
      ...editedSkill,
      toolNames: editedSkill.toolNames.filter(tool => tool !== toolToRemove),
    });
  };

  const handleSelectSnippet = (_event: React.MouseEvent | undefined, value: string | number | undefined) => {
    if (typeof value === 'string' && value && !editedSkill.snippetNames.includes(value)) {
      setEditedSkill({
        ...editedSkill,
        snippetNames: [...editedSkill.snippetNames, value],
      });
      setIsSnippetSelectOpen(false);
      setSnippetSearchTerm('');
    }
  };

  const handleRemoveSnippet = (snippetToRemove: string) => {
    setEditedSkill({
      ...editedSkill,
      snippetNames: editedSkill.snippetNames.filter(snippet => snippet !== snippetToRemove),
    });
  };

  const handleExportToAnthropic = async () => {
    if (!skill) return;
    
    try {
      // Call backend export endpoint
      const response = await fetch(`/api/skills/${skill.name}/export-anthropic`);
      
      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }
      
      // Download the ZIP file
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${skill.name}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export skill:', error);
      alert('Failed to export skill. Please try again.');
    }
  };

  // Helper function to extract file path from tags
  const getFilePathFromTags = (tags: string[]): string | null => {
    const fileTag = tags.find(tag => tag.startsWith('file:'));
    return fileTag ? fileTag.substring(5) : null; // Remove 'file:' prefix
  };

  // Build tree structure for tools
  const buildToolsTree = useMemo((): TreeViewDataItem[] => {
    if (!skill?.tools || !toolModules) return [];
    
    const tree: { [key: string]: TreeViewDataItem } = {};
    const rootItems: TreeViewDataItem[] = [];
    
    toolModules.forEach((toolModule) => {
      const tool = skill.tools?.find(t => t.name === toolModule.name);
      if (!tool) return;
      
      const filePath = getFilePathFromTags(tool.tags || []);
      
      if (filePath) {
        // Split path into parts
        const parts = filePath.split('/');
        let currentPath = '';
        let parentNode: TreeViewDataItem[] = rootItems;
        
        // Build directory structure
        for (let i = 0; i < parts.length - 1; i++) {
          currentPath += (currentPath ? '/' : '') + parts[i];
          
          if (!tree[currentPath]) {
            const dirNode: TreeViewDataItem = {
              name: parts[i],
              id: `dir-${currentPath}`,
              icon: <FolderIcon />,
              children: [],
            };
            tree[currentPath] = dirNode;
            parentNode.push(dirNode);
          }
          
          parentNode = tree[currentPath].children!;
        }
        
        // Add file node with tool name and filename in brackets
        const fileName = parts[parts.length - 1];
        const fileNode: TreeViewDataItem = {
          name: `${tool.name} (${fileName})`,
          id: `tool-${tool.name}`,
          icon: <FileCodeIcon />,
        };
        parentNode.push(fileNode);
      } else {
        // No file tag - add to root
        rootItems.push({
          name: tool.name,
          id: `tool-${tool.name}`,
          icon: <FileCodeIcon />,
        });
      }
    });
    
    return rootItems;
  }, [skill?.tools, toolModules]);

  // Build tree structure for snippets
  const buildSnippetsTree = useMemo((): TreeViewDataItem[] => {
    if (!skill?.snippets) return [];
    
    const tree: { [key: string]: TreeViewDataItem } = {};
    const rootItems: TreeViewDataItem[] = [];
    
    skill.snippets.forEach((snippet) => {
      const filePath = getFilePathFromTags(snippet.tags || []);
      
      if (filePath) {
        // Split path into parts
        const parts = filePath.split('/');
        let currentPath = '';
        let parentNode: TreeViewDataItem[] = rootItems;
        
        // Build directory structure
        for (let i = 0; i < parts.length - 1; i++) {
          currentPath += (currentPath ? '/' : '') + parts[i];
          
          if (!tree[currentPath]) {
            const dirNode: TreeViewDataItem = {
              name: parts[i],
              id: `dir-${currentPath}`,
              icon: <FolderIcon />,
              children: [],
            };
            tree[currentPath] = dirNode;
            parentNode.push(dirNode);
          }
          
          parentNode = tree[currentPath].children!;
        }
        
        // Add file node with snippet name and filename in brackets
        const fileName = parts[parts.length - 1];
        const fileNode: TreeViewDataItem = {
          name: `${snippet.name} (${fileName})`,
          id: `snippet-${snippet.name}`,
          icon: <FileIcon />,
        };
        parentNode.push(fileNode);
      } else {
        // No file tag - add to root
        rootItems.push({
          name: snippet.name,
          id: `snippet-${snippet.name}`,
          icon: <FileIcon />,
        });
      }
    });
    
    return rootItems;
  }, [skill?.snippets]);

  // Get selected tool module
  const selectedToolModule = useMemo(() => {
    if (!selectedToolItem || !toolModules) return null;
    const toolName = selectedToolItem.replace('tool-', '');
    return toolModules.find(tm => tm.name === toolName);
  }, [selectedToolItem, toolModules]);

  // Get selected snippet
  const selectedSnippet = useMemo(() => {
    if (!selectedSnippetItem || !skill?.snippets) return null;
    const snippetName = selectedSnippetItem.replace('snippet-', '');
    return skill.snippets.find(s => s.name === snippetName);
  }, [selectedSnippetItem, skill?.snippets]);

  // Helper to find tree item by ID
  const findTreeItem = (items: TreeViewDataItem[], id: string): TreeViewDataItem | null => {
    for (const item of items) {
      if (item.id === id) return item;
      if (item.children) {
        const found = findTreeItem(item.children, id);
        if (found) return found;
      }
    }
    return null;
  };

  // Get active tree items
  const activeToolItems = useMemo(() => {
    if (!selectedToolItem) return undefined;
    const item = findTreeItem(buildToolsTree, selectedToolItem);
    return item ? [item] : undefined;
  }, [selectedToolItem, buildToolsTree]);

  const activeSnippetItems = useMemo(() => {
    if (!selectedSnippetItem) return undefined;
    const item = findTreeItem(buildSnippetsTree, selectedSnippetItem);
    return item ? [item] : undefined;
  }, [selectedSnippetItem, buildSnippetsTree]);

  if (isLoading) {
    return (
      <PageSection>
        <div className="loading-container">
          <Spinner size="xl" />
        </div>
      </PageSection>
    );
  }

  if (error || !skill) {
    return (
      <PageSection>
        <Alert variant="danger" title="Error loading skill">
          {(error as Error)?.message || 'Skill not found'}
        </Alert>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection variant="light">
        <Breadcrumb>
          <BreadcrumbItem to="/skills" onClick={(e) => { e.preventDefault(); navigate('/skills'); }}>
            Skills
          </BreadcrumbItem>
          <BreadcrumbItem isActive>{skill.name}</BreadcrumbItem>
        </Breadcrumb>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
          <Title headingLevel="h1" size="2xl">
            {skill.name}
          </Title>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <Button variant="primary" icon={<ExportIcon />} onClick={handleExportToAnthropic}>
              Export to Anthropic
            </Button>
            <Button variant="secondary" icon={<EditIcon />} onClick={handleEditClick}>
              Edit
            </Button>
            <Button variant="danger" icon={<TrashIcon />} onClick={() => setIsDeleteModalOpen(true)}>
              Delete
            </Button>
          </div>
        </div>
      </PageSection>

      <PageSection>
        <Card>
          <CardTitle>Skill Information</CardTitle>
          <CardBody>
            <DescriptionList isHorizontal>
              <DescriptionListGroup>
                <DescriptionListTerm>Name</DescriptionListTerm>
                <DescriptionListDescription>{skill.name}</DescriptionListDescription>
              </DescriptionListGroup>
              
              <DescriptionListGroup>
                <DescriptionListTerm>Description</DescriptionListTerm>
                <DescriptionListDescription>
                  {skill.description || 'No description'}
                </DescriptionListDescription>
              </DescriptionListGroup>

              {skill.version && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Version</DescriptionListTerm>
                  <DescriptionListDescription>{skill.version}</DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {skill.tags && skill.tags.length > 0 && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Tags</DescriptionListTerm>
                  <DescriptionListDescription>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {skill.tags.map((tag) => (
                        <Label key={tag} color={getTagColor(tag)}>{tag}</Label>
                      ))}
                    </div>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {skill.tools && skill.tools.length > 0 && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Tools</DescriptionListTerm>
                  <DescriptionListDescription>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {skill.tools.map((tool) => (
                        <Label 
                          key={tool.name} 
                          color="blue"
                          onClick={() => navigate(`/tools/${tool.name}`)}
                          style={{ cursor: 'pointer' }}
                        >
                          {tool.name}
                        </Label>
                      ))}
                    </div>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {skill.snippets && skill.snippets.length > 0 && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Snippets</DescriptionListTerm>
                  <DescriptionListDescription>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {skill.snippets.map((snippet) => (
                        <Label 
                          key={snippet.name} 
                          color="purple"
                          onClick={() => navigate(`/snippets/${snippet.name}`)}
                          style={{ cursor: 'pointer' }}
                        >
                          {snippet.name}
                        </Label>
                      ))}
                    </div>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {skill.author && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Author</DescriptionListTerm>
                  <DescriptionListDescription>{skill.author}</DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {skill.created_at && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Created</DescriptionListTerm>
                  <DescriptionListDescription>
                    {new Date(skill.created_at).toLocaleString()}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {skill.updated_at && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Last Updated</DescriptionListTerm>
                  <DescriptionListDescription>
                    {new Date(skill.updated_at).toLocaleString()}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              <DescriptionListGroup>
                <DescriptionListTerm>UUID</DescriptionListTerm>
                <DescriptionListDescription>
                  <Text component="small" style={{ fontFamily: 'monospace' }}>
                    {skill.uuid}
                  </Text>
                </DescriptionListDescription>
              </DescriptionListGroup>
            </DescriptionList>
          </CardBody>
        </Card>

        {/* Tabs for Tools and Snippets Content */}
        {((skill.tools && skill.tools.length > 0) || (skill.snippets && skill.snippets.length > 0)) && (
          <Card style={{ marginTop: '1rem' }}>
            <CardTitle>Content</CardTitle>
            <CardBody>
              <Tabs
                activeKey={activeTabKey}
                onSelect={(_event, tabIndex) => setActiveTabKey(tabIndex)}
              >
                {skill.tools && skill.tools.length > 0 && (
                  <Tab eventKey={0} title={<TabTitleText>Tools Code</TabTitleText>}>
                    <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem', minHeight: '500px' }}>
                      {/* Tree View */}
                      <div style={{
                        flex: '0 0 25%',
                        minWidth: '300px',
                        borderRight: '1px solid #d2d2d2',
                        paddingRight: '1rem',
                        overflowY: 'auto',
                        maxHeight: '600px'
                      }}>
                        {toolModules ? (
                          buildToolsTree.length > 0 ? (
                            <TreeView
                              data={buildToolsTree}
                              activeItems={activeToolItems}
                              onSelect={(_event, item) => {
                                if (item.id?.startsWith('tool-')) {
                                  setSelectedToolItem(item.id);
                                }
                              }}
                            />
                          ) : (
                            <Text>No tools with file tags found</Text>
                          )
                        ) : (
                          <Spinner size="lg" />
                        )}
                      </div>
                      
                      {/* Code Display */}
                      <div style={{ flex: 1, overflowY: 'auto', maxHeight: '600px' }}>
                        {selectedToolModule ? (
                          <div>
                            <Title headingLevel="h4" size="md" style={{ marginBottom: '0.5rem' }}>
                              {selectedToolModule.name}
                            </Title>
                            <CodeBlock>
                              <CodeBlockCode
                                style={{
                                  backgroundColor: '#f5f5f5',
                                  color: '#151515',
                                  padding: '1rem',
                                  borderRadius: '4px',
                                  fontSize: '14px',
                                  lineHeight: '1.5'
                                }}
                              >
                                {selectedToolModule.module}
                              </CodeBlockCode>
                            </CodeBlock>
                          </div>
                        ) : (
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            height: '100%',
                            color: '#6a6e73'
                          }}>
                            <Text>Select a tool from the tree to view its code</Text>
                          </div>
                        )}
                      </div>
                    </div>
                  </Tab>
                )}
                {skill.snippets && skill.snippets.length > 0 && (
                  <Tab eventKey={1} title={<TabTitleText>Snippets Content</TabTitleText>}>
                    <div style={{ marginTop: '1rem', display: 'flex', gap: '1rem', minHeight: '500px' }}>
                      {/* Tree View */}
                      <div style={{
                        flex: '0 0 25%',
                        minWidth: '300px',
                        borderRight: '1px solid #d2d2d2',
                        paddingRight: '1rem',
                        overflowY: 'auto',
                        maxHeight: '600px'
                      }}>
                        {buildSnippetsTree.length > 0 ? (
                          <TreeView
                            data={buildSnippetsTree}
                            activeItems={activeSnippetItems}
                            onSelect={(_event, item) => {
                              if (item.id?.startsWith('snippet-')) {
                                setSelectedSnippetItem(item.id);
                              }
                            }}
                          />
                        ) : (
                          <Text>No snippets with file tags found</Text>
                        )}
                      </div>
                      
                      {/* Content Display */}
                      <div style={{ flex: 1, overflowY: 'auto', maxHeight: '600px' }}>
                        {selectedSnippet ? (
                          <div>
                            <Title headingLevel="h4" size="md" style={{ marginBottom: '0.5rem' }}>
                              {selectedSnippet.name}
                            </Title>
                            <CodeBlock>
                              <CodeBlockCode
                                style={{
                                  backgroundColor: '#f5f5f5',
                                  color: '#151515',
                                  padding: '1rem',
                                  borderRadius: '4px',
                                  fontSize: '14px',
                                  lineHeight: '1.5'
                                }}
                              >
                                {selectedSnippet.content}
                              </CodeBlockCode>
                            </CodeBlock>
                          </div>
                        ) : (
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            height: '100%',
                            color: '#6a6e73'
                          }}>
                            <Text>Select a snippet from the tree to view its content</Text>
                          </div>
                        )}
                      </div>
                    </div>
                  </Tab>
                )}
              </Tabs>
            </CardBody>
          </Card>
        )}
      </PageSection>

      {/* Edit Modal */}
      <Modal
        variant={ModalVariant.large}
        title="Edit Skill"
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditError('');
          setTagInput('');
          setToolSearchTerm('');
          setSnippetSearchTerm('');
        }}
        actions={[
          <Button
            key="save"
            variant="primary"
            onClick={handleUpdateSkill}
            isLoading={updateMutation.isPending}
          >
            Save Changes
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => {
              setIsEditModalOpen(false);
              setEditError('');
              setTagInput('');
              setToolSearchTerm('');
              setSnippetSearchTerm('');
            }}
          >
            Cancel
          </Button>,
        ]}
      >
        {editError && (
          <Alert variant="danger" title="Error" isInline style={{ marginBottom: '1rem' }}>
            {editError}
          </Alert>
        )}
        <Form>
          <FormGroup label="Name" isRequired fieldId="skill-name">
            <TextInput
              isRequired
              type="text"
              id="skill-name"
              value={editedSkill.name}
              onChange={(_, value) => setEditedSkill({ ...editedSkill, name: value })}
            />
          </FormGroup>
          <FormGroup label="Version" fieldId="skill-version">
            <TextInput
              type="text"
              id="skill-version"
              value={editedSkill.version}
              onChange={(_, value) => setEditedSkill({ ...editedSkill, version: value })}
              placeholder="e.g., 1.0.0"
            />
          </FormGroup>
          <FormGroup label="Description" isRequired fieldId="skill-description">
            <TextArea
              isRequired
              id="skill-description"
              value={editedSkill.description}
              onChange={(_, value) => setEditedSkill({ ...editedSkill, description: value })}
              rows={3}
            />
          </FormGroup>
          <FormGroup label="Tags" fieldId="skill-tags">
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <TextInput
                type="text"
                id="skill-tags"
                value={tagInput}
                onChange={(_, value) => setTagInput(value)}
                placeholder="Add a tag"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddTag();
                  }
                }}
              />
              <Button variant="secondary" onClick={handleAddTag}>
                Add
              </Button>
            </div>
            {editedSkill.tags.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {editedSkill.tags.map((tag) => (
                  <Button
                    key={tag}
                    variant="plain"
                    onClick={() => handleRemoveTag(tag)}
                    style={{
                      padding: '0.25rem 0.5rem',
                      backgroundColor: '#f0f0f0',
                      border: '1px solid #d2d2d2',
                      borderRadius: '3px',
                    }}
                  >
                    {tag} ✕
                  </Button>
                ))}
              </div>
            )}
          </FormGroup>
          <FormGroup label="Tools" fieldId="skill-tools">
            <Text component="small" style={{ display: 'block', marginBottom: '0.5rem', color: '#6a6e73' }}>
              Search and select tools to include in this skill
            </Text>
            <Select
              id="skill-tools-select"
              isOpen={isToolSelectOpen}
              selected={null}
              onSelect={handleSelectTool}
              onOpenChange={(isOpen) => setIsToolSelectOpen(isOpen)}
              toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                <MenuToggle
                  ref={toggleRef}
                  onClick={() => setIsToolSelectOpen(!isToolSelectOpen)}
                  isExpanded={isToolSelectOpen}
                  style={{ width: '100%' }}
                >
                  {toolSearchTerm || 'Select a tool...'}
                </MenuToggle>
              )}
            >
              <SelectList>
                <TextInput
                  type="search"
                  value={toolSearchTerm}
                  onChange={(_, value) => setToolSearchTerm(value)}
                  placeholder="Search tools..."
                  style={{ padding: '0.5rem', borderBottom: '1px solid #d2d2d2' }}
                />
                {filteredTools.length === 0 ? (
                  <SelectOption isDisabled>
                    {toolSearchTerm ? 'No tools found' : 'Start typing to search...'}
                  </SelectOption>
                ) : (
                  filteredTools.map((tool) => (
                    <SelectOption key={tool.name} value={tool.name}>
                      {tool.name}
                    </SelectOption>
                  ))
                )}
              </SelectList>
            </Select>
            {editedSkill.toolNames.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {editedSkill.toolNames.map((tool) => (
                  <Button
                    key={tool}
                    variant="plain"
                    onClick={() => handleRemoveTool(tool)}
                    style={{
                      padding: '0.25rem 0.5rem',
                      backgroundColor: '#e7f1fa',
                      border: '1px solid #bee1f4',
                      borderRadius: '3px',
                    }}
                  >
                    {tool} ✕
                  </Button>
                ))}
              </div>
            )}
          </FormGroup>
          <FormGroup label="Snippets" fieldId="skill-snippets">
            <Text component="small" style={{ display: 'block', marginBottom: '0.5rem', color: '#6a6e73' }}>
              Search and select snippets to include in this skill
            </Text>
            <Select
              id="skill-snippets-select"
              isOpen={isSnippetSelectOpen}
              selected={null}
              onSelect={handleSelectSnippet}
              onOpenChange={(isOpen) => setIsSnippetSelectOpen(isOpen)}
              toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                <MenuToggle
                  ref={toggleRef}
                  onClick={() => setIsSnippetSelectOpen(!isSnippetSelectOpen)}
                  isExpanded={isSnippetSelectOpen}
                  style={{ width: '100%' }}
                >
                  {snippetSearchTerm || 'Select a snippet...'}
                </MenuToggle>
              )}
            >
              <SelectList>
                <TextInput
                  type="search"
                  value={snippetSearchTerm}
                  onChange={(_, value) => setSnippetSearchTerm(value)}
                  placeholder="Search snippets..."
                  style={{ padding: '0.5rem', borderBottom: '1px solid #d2d2d2' }}
                />
                {filteredSnippets.length === 0 ? (
                  <SelectOption isDisabled>
                    {snippetSearchTerm ? 'No snippets found' : 'Start typing to search...'}
                  </SelectOption>
                ) : (
                  filteredSnippets.map((snippet) => (
                    <SelectOption key={snippet.name} value={snippet.name}>
                      {snippet.name}
                    </SelectOption>
                  ))
                )}
              </SelectList>
            </Select>
            {editedSkill.snippetNames.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {editedSkill.snippetNames.map((snippet) => (
                  <Button
                    key={snippet}
                    variant="plain"
                    onClick={() => handleRemoveSnippet(snippet)}
                    style={{
                      padding: '0.25rem 0.5rem',
                      backgroundColor: '#f4e7f7',
                      border: '1px solid #d8bfd8',
                      borderRadius: '3px',
                    }}
                  >
                    {snippet} ✕
                  </Button>
                ))}
              </div>
            )}
          </FormGroup>
        </Form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Delete Skill"
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        actions={[
          <Button
            key="delete"
            variant="danger"
            onClick={() => deleteMutation.mutate()}
            isLoading={deleteMutation.isPending}
          >
            Delete
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => setIsDeleteModalOpen(false)}
          >
            Cancel
          </Button>,
        ]}
      >
        <Text>
          Are you sure you want to delete the skill "{skill?.name}"? This action cannot be undone.
        </Text>
      </Modal>
    </>
  );
}