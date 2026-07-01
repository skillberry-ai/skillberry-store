// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TagFilter } from '../components/TagFilter';
import { tagMatchesFilter } from '../utils/tagUtils';
import { NamespaceFilter } from '../components/NamespaceFilter';
import { SearchBox, SearchMode } from '../components/SearchBox';
import { exportSkills, importSkills, downloadJSON } from '../utils/exportImportHelpers';
import {
  PageSection,
  Title,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
  Button,
  Text,
  Spinner,
  EmptyState,
  EmptyStateIcon,
  EmptyStateBody,
  Alert,
  Modal,
  ModalVariant,
  Form,
  FormGroup,
  TextInput,
  TextArea,
  FileUpload,
  Select,
  SelectOption,
  SelectList,
  MenuToggle,
  MenuToggleElement,
  ToggleGroup,
  ToggleGroupItem,
  Checkbox,
} from '@patternfly/react-core';
import type { ThProps } from '@patternfly/react-table';
import { PlusIcon, CodeIcon, SearchIcon, TrashIcon, ExportIcon, ImportIcon, UploadIcon, ThLargeIcon, ListIcon } from '@patternfly/react-icons';
import { skillsApi, toolsApi, snippetsApi } from '@/services/api';
import type { Skill } from '@/types';
import { AnthropicSkillImporter } from '../components/AnthropicSkillImporter';
import { SkillCardView } from '../components/SkillCardView';
import { SkillListView } from '../components/SkillListView';


export function SkillsPage() {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>('text');
  const [maxResults, setMaxResults] = useState(10);
  const [similarityThreshold, setSimilarityThreshold] = useState(1);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedNamespaces, setSelectedNamespaces] = useState<string[]>([]);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newSkill, setNewSkill] = useState({
    name: '',
    version: '',
    description: '',
    tags: [] as string[],
    toolUuids: [] as string[],
    snippetUuids: [] as string[],
  });
  const [tagInput, setTagInput] = useState('');
  const [createError, setCreateError] = useState('');
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [deleteTools, setDeleteTools] = useState(true);
  const [deleteSnippets, setDeleteSnippets] = useState(true);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importError, setImportError] = useState('');
  const [isAnthropicImportModalOpen, setIsAnthropicImportModalOpen] = useState(false);
  const [activeSortIndex, setActiveSortIndex] = useState<number | null>(null);
  const [activeSortDirection, setActiveSortDirection] = useState<'asc' | 'desc'>('asc');
  const [viewMode, setViewMode] = useState<'cards' | 'list'>(() => {
    const stored = localStorage.getItem('skills-view-mode');
    return stored === 'cards' || stored === 'list' ? stored : 'cards';
  });

  // Select dropdown states
  const [isToolSelectOpen, setIsToolSelectOpen] = useState(false);
  const [isSnippetSelectOpen, setIsSnippetSelectOpen] = useState(false);
  const [toolSearchTerm, setToolSearchTerm] = useState('');
  const [snippetSearchTerm, setSnippetSearchTerm] = useState('');

  const { data: skills, isLoading, error } = useQuery({
    queryKey: ['skills'],
    queryFn: skillsApi.list,
  });

  // Semantic search skills (only when in semantic mode)
  const { data: searchResults } = useQuery({
    queryKey: ['skills', 'search', searchTerm, maxResults, similarityThreshold],
    queryFn: () => skillsApi.search(searchTerm, maxResults, similarityThreshold),
    enabled: searchTerm.length > 0 && searchMode === 'semantic',
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

  // Create skill mutation
  const createMutation = useMutation({
    mutationFn: (skill: Omit<Skill, 'uuid'>) =>
      skillsApi.create(skill),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills'] });
      setIsCreateModalOpen(false);
      setNewSkill({
        name: '',
        version: '',
        description: '',
        tags: [],
        toolUuids: [],
        snippetUuids: [],
      });
      setTagInput('');
      setToolSearchTerm('');
      setSnippetSearchTerm('');
      setCreateError('');
    },
    onError: (error: Error) => {
      setCreateError(error.message || 'Failed to create skill');
    },
  });

  // Delete skills mutation
  const deleteMutation = useMutation({
    mutationFn: async (names: string[]) => {
      await Promise.all(names.map(name => skillsApi.delete(name, { deleteTools, deleteSnippets })));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills'] });
      setSelectedSkills([]);
      setIsDeleteModalOpen(false);
      setDeleteError('');
    },
    onError: (error: any) => {
      setDeleteError(error.message || 'Failed to delete skill(s)');
    },
  });

  const handleCreateSkill = async () => {
    if (!newSkill.name || !newSkill.description) {
      setCreateError('Please fill in all required fields');
      return;
    }

    try {
      // Build query parameters — tool_uuids and snippet_uuids are already UUIDs
      const params = new URLSearchParams({
        name: newSkill.name,
        version: newSkill.version,
        description: newSkill.description,
      });

      newSkill.tags.forEach(tag => params.append('tags', tag));
      newSkill.toolUuids.forEach(uuid => params.append('tool_uuids', uuid));
      newSkill.snippetUuids.forEach(uuid => params.append('snippet_uuids', uuid));

      const response = await fetch(`/api/skills/?${params}`, { method: 'POST' });

      if (response.ok) {
        queryClient.invalidateQueries({ queryKey: ['skills'] });
        setIsCreateModalOpen(false);
        setNewSkill({ name: '', version: '1.0.0', description: '', tags: [], toolUuids: [], snippetUuids: [] });
        setCreateError('');
      } else {
        let detail: string;
        try {
          const body = await response.json();
          detail = body.detail
            ? (Array.isArray(body.detail)
              ? body.detail.map((e: any) => e.msg || JSON.stringify(e)).join('; ')
              : String(body.detail))
            : response.statusText;
        } catch {
          detail = response.statusText;
        }
        setCreateError(`Failed to create skill "${newSkill.name}": ${detail}`);
      }
    } catch (error: any) {
      setCreateError(error.message || 'Failed to create skill');
    }
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !newSkill.tags.includes(tagInput.trim())) {
      setNewSkill({
        ...newSkill,
        tags: [...newSkill.tags, tagInput.trim()],
      });
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setNewSkill({
      ...newSkill,
      tags: newSkill.tags.filter(tag => tag !== tagToRemove),
    });
  };

  // Filter tools based on search term - only when modal is open
  const filteredTools = useMemo(() => {
    if (!isCreateModalOpen || !allTools) return [];
    const lowerSearch = toolSearchTerm.toLowerCase();
    return allTools.filter(tool =>
      tool.name.toLowerCase().includes(lowerSearch) &&
      !newSkill.toolUuids.includes(tool.uuid)
    );
  }, [isCreateModalOpen, allTools, toolSearchTerm, newSkill.toolUuids]);

  // Filter snippets based on search term - only when modal is open
  const filteredSnippets = useMemo(() => {
    if (!isCreateModalOpen || !allSnippets) return [];
    const lowerSearch = snippetSearchTerm.toLowerCase();
    return allSnippets.filter(snippet =>
      snippet.name.toLowerCase().includes(lowerSearch) &&
      !newSkill.snippetUuids.includes(snippet.uuid)
    );
  }, [isCreateModalOpen, allSnippets, snippetSearchTerm, newSkill.snippetUuids]);

  const handleSelectTool = (_event: React.MouseEvent | undefined, value: string | number | undefined) => {
    if (typeof value === 'string' && value && !newSkill.toolUuids.includes(value)) {
      setNewSkill({
        ...newSkill,
        toolUuids: [...newSkill.toolUuids, value],
      });
      setIsToolSelectOpen(false);
      setToolSearchTerm('');
    }
  };

  const handleRemoveTool = (uuidToRemove: string) => {
    setNewSkill({
      ...newSkill,
      toolUuids: newSkill.toolUuids.filter(uuid => uuid !== uuidToRemove),
    });
  };

  const handleSelectSnippet = (_event: React.MouseEvent | undefined, value: string | number | undefined) => {
    if (typeof value === 'string' && value && !newSkill.snippetUuids.includes(value)) {
      setNewSkill({
        ...newSkill,
        snippetUuids: [...newSkill.snippetUuids, value],
      });
      setIsSnippetSelectOpen(false);
      setSnippetSearchTerm('');
    }
  };

  const handleRemoveSnippet = (uuidToRemove: string) => {
    setNewSkill({
      ...newSkill,
      snippetUuids: newSkill.snippetUuids.filter(uuid => uuid !== uuidToRemove),
    });
  };

  const handleSelectSkill = (skillName: string, isSelected: boolean) => {
    setSelectedSkills(prev =>
      isSelected
        ? [...prev, skillName]
        : prev.filter(name => name !== skillName)
    );
  };

  const handleSelectAll = (isSelected: boolean) => {
    setSelectedSkills(
      isSelected ? (filteredSkills?.map(s => s.name) || []) : []
    );
  };

  const handleDeleteSelected = () => {
    deleteMutation.mutate(selectedSkills);
  };

  const handleExport = async () => {
    const selectedSkillObjects = skills?.filter(s => selectedSkills.includes(s.name)) || [];
    
    // Use helper function to export skills with UUIDs (matching backend format)
    const skillsForExport = exportSkills(selectedSkillObjects);
    
    // Generate filename based on selected skills
    let filename: string;
    if (selectedSkillObjects.length === 1) {
      // Single skill: use skill name
      filename = `${selectedSkillObjects[0].name}.json`;
    } else {
      // Multiple skills: use date-based name
      filename = `skills-export-${new Date().toISOString().split('T')[0]}.json`;
    }
    
    // Download as JSON file
    downloadJSON(skillsForExport, filename);
  };

  const handleImport = async () => {
    if (!importFile) {
      setImportError('Please select a file to import');
      return;
    }

    try {
      const text = await importFile.text();
      const importedSkills = JSON.parse(text);

      if (!Array.isArray(importedSkills)) {
        setImportError('Invalid file format. Expected an array of skills.');
        return;
      }

      const result = await importSkills(importedSkills);
      queryClient.invalidateQueries({ queryKey: ['skills'] });

      if (result.failures.length > 0) {
        const summary = result.failures
          .map(f => `• ${f.name}: ${f.error}`)
          .join('\n');
        setImportError(
          `Imported ${result.importedCount} of ${importedSkills.length} skill(s). Failures:\n${summary}`
        );
      } else {
        setIsImportModalOpen(false);
        setImportFile(null);
        setImportError('');
      }
    } catch (error) {
      setImportError('Failed to parse JSON file. Please ensure it is valid JSON.');
    }
  };

  const getSortableRowValues = (skill: Skill): (string | number)[] => {
    return [
      skill.name,
      skill.description || '',
      skill.version || '',
    ];
  };

  // Get all unique tags from skills (excluding namespace tags)
  const allTags = useMemo(() => {
    if (!skills) return [];
    const tagSet = new Set<string>();
    skills.forEach(skill => {
      skill.tags?.forEach(tag => {
        if (!tag.startsWith('namespace:')) {
          tagSet.add(tag);
        }
      });
    });
    return Array.from(tagSet).sort();
  }, [skills]);

  // Get all unique namespaces from skills
  const allNamespaces = useMemo(() => {
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

  const filteredSkills = useMemo(() => {
    let filtered = skills;

    // Apply search filtering
    if (searchTerm && filtered) {
      if (searchMode === 'semantic' && searchResults) {
        // Semantic search: filter by backend results (handle both name and filename)
        filtered = filtered.filter((skill) =>
          searchResults.some((result) =>
            (result.name === skill.name) || (result.filename === skill.name)
          )
        );
      } else if (searchMode === 'text') {
        // Text search: filter by matching text in name or description
        const lowerSearch = searchTerm.toLowerCase();
        filtered = filtered.filter((skill) =>
          skill.name.toLowerCase().includes(lowerSearch) ||
          skill.description?.toLowerCase().includes(lowerSearch)
        );
      } else if (searchMode === 'uuid') {
        // UUID search: filter by matching UUID (partial match)
        const lowerSearch = searchTerm.toLowerCase();
        filtered = filtered.filter((skill) =>
          skill.uuid?.toLowerCase().includes(lowerSearch)
        );
      }
    }

    // Apply tag filtering (excluding namespace tags)
    if (filtered && selectedTags.length > 0) {
      filtered = filtered.filter(skill =>
        selectedTags.every(selectedTag =>
          tagMatchesFilter(skill.tags ?? [], selectedTag)
        )
      );
    }

    // Apply namespace filtering
    if (filtered && selectedNamespaces.length > 0) {
      filtered = filtered.filter(skill =>
        selectedNamespaces.every(selectedNamespace =>
          skill.tags?.includes(`namespace:${selectedNamespace}`)
        )
      );
    }

    if (filtered && activeSortIndex !== null) {
      filtered = [...filtered].sort((a, b) => {
        const aValue = getSortableRowValues(a)[activeSortIndex];
        const bValue = getSortableRowValues(b)[activeSortIndex];
        
        if (typeof aValue === 'string' && typeof bValue === 'string') {
          const comparison = aValue.localeCompare(bValue);
          return activeSortDirection === 'asc' ? comparison : -comparison;
        }
        
        return 0;
      });
    }

    return filtered;
  }, [skills, searchResults, searchTerm, searchMode, selectedTags, selectedNamespaces, activeSortIndex, activeSortDirection]);

  const getSortParams = (columnIndex: number): ThProps['sort'] => ({
    sortBy: {
      index: activeSortIndex ?? 0,
      direction: activeSortDirection,
    },
    onSort: (_event, index, direction) => {
      setActiveSortIndex(index);
      setActiveSortDirection(direction);
    },
    columnIndex,
  });


  if (isLoading) {
    return (
      <PageSection>
        <div className="loading-container">
          <Spinner size="xl" />
        </div>
      </PageSection>
    );
  }

  if (error) {
    return (
      <PageSection>
        <Alert variant="danger" title="Error loading skills">
          {(error as Error).message}
        </Alert>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection variant="light">
        <Title headingLevel="h1" size="2xl">
          Skills
        </Title>
        <Text>Organize collections of tools and snippets into reusable skills</Text>
      </PageSection>

      <PageSection>
        <Toolbar>
          <ToolbarContent>
            <ToolbarItem variant="search-filter" style={{ flexGrow: 1 }}>
              <SearchBox
                value={searchTerm}
                onChange={setSearchTerm}
                onClear={() => setSearchTerm('')}
                mode={searchMode}
                onModeChange={setSearchMode}
                placeholder="Search skills..."
                maxResults={maxResults}
                onMaxResultsChange={setMaxResults}
                similarityThreshold={similarityThreshold}
                onSimilarityThresholdChange={setSimilarityThreshold}
              />
            </ToolbarItem>
            <ToolbarItem>
              <NamespaceFilter
                allNamespaces={allNamespaces}
                selectedNamespaces={selectedNamespaces}
                onNamespacesChange={setSelectedNamespaces}
              />
            </ToolbarItem>
            <ToolbarItem>
              <TagFilter
                allTags={allTags}
                selectedTags={selectedTags}
                onTagsChange={setSelectedTags}
              />
            </ToolbarItem>
            <ToolbarItem>
              <Button
                variant="secondary"
                icon={<ExportIcon />}
                onClick={handleExport}
                isDisabled={selectedSkills.length === 0}
              >
                Export ({selectedSkills.length})
              </Button>
            </ToolbarItem>
            <ToolbarItem>
              <Button
                variant="secondary"
                icon={<ImportIcon />}
                onClick={() => setIsImportModalOpen(true)}
              >
                Import JSON
              </Button>
            </ToolbarItem>
            <ToolbarItem>
              <Button
                variant="secondary"
                icon={<UploadIcon />}
                onClick={() => setIsAnthropicImportModalOpen(true)}
              >
                Import Anthropic Skill
              </Button>
            </ToolbarItem>
            <ToolbarItem>
              <Button
                variant="danger"
                icon={<TrashIcon />}
                onClick={() => setIsDeleteModalOpen(true)}
                isDisabled={selectedSkills.length === 0}
              >
                Delete ({selectedSkills.length})
              </Button>
            </ToolbarItem>
            <ToolbarItem>
              <Button
                variant="primary"
                icon={<PlusIcon />}
                onClick={() => setIsCreateModalOpen(true)}
              >
                Create Skill
              </Button>
            </ToolbarItem>
            <ToolbarItem>
              <ToggleGroup aria-label="Skills view mode">
                <ToggleGroupItem
                  icon={<ThLargeIcon />}
                  text="Cards"
                  isSelected={viewMode === 'cards'}
                  onChange={(_event, isSelected) => {
                    if (isSelected) {
                      setViewMode('cards');
                      localStorage.setItem('skills-view-mode', 'cards');
                    }
                  }}
                />
                <ToggleGroupItem
                  icon={<ListIcon />}
                  text="List"
                  isSelected={viewMode === 'list'}
                  onChange={(_event, isSelected) => {
                    if (isSelected) {
                      setViewMode('list');
                      localStorage.setItem('skills-view-mode', 'list');
                    }
                  }}
                />
              </ToggleGroup>
            </ToolbarItem>
          </ToolbarContent>
        </Toolbar>

        {!filteredSkills || filteredSkills.length === 0 ? (
          <EmptyState>
            <EmptyStateIcon icon={searchTerm ? SearchIcon : CodeIcon} />
            <Title headingLevel="h4" size="lg">
              {searchTerm ? 'No skills found' : 'No skills yet'}
            </Title>
            <EmptyStateBody>
              {searchTerm
                ? 'Try adjusting your search criteria'
                : 'Create your first skill to get started'}
            </EmptyStateBody>
            {!searchTerm && (
              <Button
                variant="primary"
                icon={<PlusIcon />}
                onClick={() => setIsCreateModalOpen(true)}
              >
                Create Skill
              </Button>
            )}
          </EmptyState>
        ) : viewMode === 'cards' ? (
          <SkillCardView
            skills={filteredSkills}
            selectedSkills={selectedSkills}
            onSelectSkill={handleSelectSkill}
          />
        ) : (
          <SkillListView
            skills={filteredSkills}
            selectedSkills={selectedSkills}
            onSelectSkill={handleSelectSkill}
            onSelectAll={handleSelectAll}
            getSortParams={getSortParams}
          />
        )}
      </PageSection>

      {/* Create Skill Modal */}
      <Modal
        variant={ModalVariant.medium}
        title="Create New Skill"
        isOpen={isCreateModalOpen}
        onClose={() => {
          setIsCreateModalOpen(false);
          setNewSkill({
            name: '',
            version: '',
            description: '',
            tags: [],
            toolUuids: [],
            snippetUuids: [],
          });
          setTagInput('');
          setToolSearchTerm('');
          setSnippetSearchTerm('');
          setCreateError('');
        }}
        actions={[
          <Button
            key="create"
            variant="primary"
            onClick={handleCreateSkill}
            isLoading={createMutation.isPending}
          >
            Create
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => {
              setIsCreateModalOpen(false);
              setNewSkill({
                name: '',
                version: '',
                description: '',
                tags: [],
                toolUuids: [],
                snippetUuids: [],
              });
              setTagInput('');
              setToolSearchTerm('');
              setSnippetSearchTerm('');
              setCreateError('');
            }}
          >
            Cancel
          </Button>,
        ]}
      >
        {createError && (
          <Alert variant="danger" title="Error" isInline style={{ marginBottom: '1rem' }}>
            {createError}
          </Alert>
        )}
        <Form>
          <FormGroup label="Name" isRequired fieldId="skill-name">
            <TextInput
              isRequired
              type="text"
              id="skill-name"
              value={newSkill.name}
              onChange={(_, value) => setNewSkill({ ...newSkill, name: value })}
            />
          </FormGroup>
          <FormGroup label="Version" fieldId="skill-version">
            <TextInput
              type="text"
              id="skill-version"
              value={newSkill.version}
              onChange={(_, value) => setNewSkill({ ...newSkill, version: value })}
              placeholder="e.g., 1.0.0"
            />
          </FormGroup>
          <FormGroup label="Description" isRequired fieldId="skill-description">
            <TextArea
              isRequired
              id="skill-description"
              value={newSkill.description}
              onChange={(_, value) => setNewSkill({ ...newSkill, description: value })}
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
            {newSkill.tags.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {newSkill.tags.map((tag) => (
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
                  {'Select a tool...'}
                </MenuToggle>
              )}
            >
              <SelectList style={{ maxHeight: '300px', overflowY: 'auto' }}>
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
                    <SelectOption key={tool.uuid} value={tool.uuid}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <div style={{ fontWeight: 'bold' }}>{tool.name}</div>
                        <div style={{ fontSize: '0.85em', color: '#6a6e73', fontFamily: 'monospace' }}>
                          UUID: {tool.uuid}
                        </div>
                        {tool.description && (
                          <div style={{ fontSize: '0.9em', color: '#6a6e73' }}>
                            {tool.description}
                          </div>
                        )}
                      </div>
                    </SelectOption>
                  ))
                )}
              </SelectList>
            </Select>
            {newSkill.toolUuids.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {newSkill.toolUuids.map((uuid) => {
                  const tool = allTools?.find(t => t.uuid === uuid);
                  return (
                    <Button
                      key={uuid}
                      variant="plain"
                      onClick={() => handleRemoveTool(uuid)}
                      style={{
                        padding: '0.25rem 0.5rem',
                        backgroundColor: '#e7f1fa',
                        border: '1px solid #bee1f4',
                        borderRadius: '3px',
                      }}
                    >
                      {tool?.name || uuid} ✕
                    </Button>
                  );
                })}
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
                  {'Select a snippet...'}
                </MenuToggle>
              )}
            >
              <SelectList style={{ maxHeight: '300px', overflowY: 'auto' }}>
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
                    <SelectOption key={snippet.uuid} value={snippet.uuid}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <div style={{ fontWeight: 'bold' }}>{snippet.name}</div>
                        <div style={{ fontSize: '0.85em', color: '#6a6e73', fontFamily: 'monospace' }}>
                          UUID: {snippet.uuid}
                        </div>
                        {snippet.description && (
                          <div style={{ fontSize: '0.9em', color: '#6a6e73' }}>
                            {snippet.description}
                          </div>
                        )}
                      </div>
                    </SelectOption>
                  ))
                )}
              </SelectList>
            </Select>
            {newSkill.snippetUuids.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {newSkill.snippetUuids.map((uuid) => {
                  const snippet = allSnippets?.find(s => s.uuid === uuid);
                  return (
                    <Button
                      key={uuid}
                      variant="plain"
                      onClick={() => handleRemoveSnippet(uuid)}
                      style={{
                        padding: '0.25rem 0.5rem',
                        backgroundColor: '#f4e7f7',
                        border: '1px solid #d8bfd8',
                        borderRadius: '3px',
                      }}
                    >
                      {snippet?.name || uuid} ✕
                    </Button>
                  );
                })}
              </div>
            )}
          </FormGroup>
        </Form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Delete Skills"
        isOpen={isDeleteModalOpen}
        onClose={() => { setIsDeleteModalOpen(false); setDeleteTools(true); setDeleteSnippets(true); setDeleteError(''); }}
        actions={[
          <Button
            key="delete"
            variant="danger"
            onClick={handleDeleteSelected}
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
        {deleteError && (
          <Alert variant="danger" title="Delete failed" isInline style={{ marginBottom: '1rem' }}>
            {deleteError}
          </Alert>
        )}
        <Text>
          Are you sure you want to delete {selectedSkills.length} skill{selectedSkills.length > 1 ? 's' : ''}?
          This action cannot be undone.
        </Text>
        <ul style={{ marginTop: '1rem' }}>
          {selectedSkills.map(name => (
            <li key={name}>{name}</li>
          ))}
        </ul>
        <div style={{ marginTop: '1rem' }}>
          <Checkbox
            id="bulk-delete-tools-checkbox"
            label="Delete associated tools"
            isChecked={deleteTools}
            onChange={(_e, checked) => setDeleteTools(checked)}
          />
          <Checkbox
            id="bulk-delete-snippets-checkbox"
            label="Delete associated snippets"
            isChecked={deleteSnippets}
            onChange={(_e, checked) => setDeleteSnippets(checked)}
            style={{ marginTop: '0.5rem' }}
          />
          <Text component="small" style={{ color: '#6a6e73', marginTop: '0.5rem', display: 'block' }}>
            Tools or snippets shared with other skills will not be deleted.
          </Text>
        </div>
      </Modal>

      {/* Import Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Import Skills"
        isOpen={isImportModalOpen}
        onClose={() => {
          setIsImportModalOpen(false);
          setImportFile(null);
          setImportError('');
        }}
        actions={[
          <Button
            key="import"
            variant="primary"
            onClick={handleImport}
          >
            Import
          </Button>,
          <Button
            key="cancel"
            variant="link"
            onClick={() => {
              setIsImportModalOpen(false);
              setImportFile(null);
              setImportError('');
            }}
          >
            Cancel
          </Button>,
        ]}
      >
        {importError && (
          <Alert variant="danger" title="Error" isInline style={{ marginBottom: '1rem' }}>
            <span style={{ whiteSpace: 'pre-wrap' }}>{importError}</span>
          </Alert>
        )}
        <Text style={{ marginBottom: '1rem' }}>
          Select a JSON file containing an array of skill objects (with tool_uuids and snippet_uuids) to import.
        </Text>
        <FileUpload
          id="import-file"
          value={importFile || undefined}
          filename={importFile?.name}
          onFileInputChange={(_event, file: File) => setImportFile(file)}
          onClearClick={() => setImportFile(null)}
          hideDefaultPreview
          browseButtonText="Select JSON File"
          accept=".json"
        />
      </Modal>

      {/* Anthropic Skill Import Modal */}
      <AnthropicSkillImporter
        isOpen={isAnthropicImportModalOpen}
        onClose={() => setIsAnthropicImportModalOpen(false)}
        onImportComplete={() => {
          queryClient.invalidateQueries({ queryKey: ['skills'] });
          queryClient.invalidateQueries({ queryKey: ['tools'] });
          queryClient.invalidateQueries({ queryKey: ['snippets'] });
        }}
      />
    </>
  );
}