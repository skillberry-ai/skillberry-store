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
  FormSelect,
  FormSelectOption,
  Select,
  SelectOption,
  SelectList,
  MenuToggle,
  MenuToggleElement,
  Radio,
  CodeBlock,
  CodeBlockCode,
  ClipboardCopy,
} from '@patternfly/react-core';
import { EditIcon, TrashIcon } from '@patternfly/react-icons';
import { vnfsApi, skillsApi } from '@/services/api';
import type { VNFSServer } from '@/types';

export function VNFSServerDetailPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [editedServer, setEditedServer] = useState({
    name: '',
    version: '',
    description: '',
    state: 'approved' as 'unknown' | 'any' | 'new' | 'checked' | 'approved',
    tags: [] as string[],
    port: undefined as number | undefined,
    skill_uuid: '',
    protocol: 'webdav',
    extra: {} as Record<string, any>,
  });
  const [tagInput, setTagInput] = useState('');
  const [extraInput, setExtraInput] = useState('{}');
  const [editError, setEditError] = useState('');

  const [isSkillSelectOpen, setIsSkillSelectOpen] = useState(false);
  const [skillSearchTerm, setSkillSearchTerm] = useState('');

  const { data: server, isLoading, error } = useQuery({
    queryKey: ['vnfs-servers', name],
    queryFn: () => vnfsApi.get(name!),
    enabled: !!name,
  });

  const { data: allSkills } = useQuery({
    queryKey: ['skills'],
    queryFn: skillsApi.list,
  });

  const updateMutation = useMutation({
    mutationFn: (updatedServer: Omit<VNFSServer, 'uuid' | 'running' | 'export_path'>) =>
      vnfsApi.update(name!, updatedServer),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vnfs-servers', name] });
      queryClient.invalidateQueries({ queryKey: ['vnfs-servers'] });
      setIsEditModalOpen(false);
      setEditError('');
    },
    onError: (error: any) => {
      setEditError(error.message || 'Failed to update vNFS server');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => vnfsApi.delete(name!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vnfs-servers'] });
      navigate('/vnfs-servers');
    },
  });

  const filteredSkills = useMemo(() => {
    if (!allSkills) return [];
    if (!skillSearchTerm) return allSkills;
    const lower = skillSearchTerm.toLowerCase();
    return allSkills.filter(s =>
      s.name.toLowerCase().includes(lower) || s.description?.toLowerCase().includes(lower)
    );
  }, [allSkills, skillSearchTerm]);

  const handleSelectSkill = (_event: any, value: string | number | undefined) => {
    if (typeof value === 'string') {
      const selected = allSkills?.find(s => s.name === value);
      if (selected) {
        setEditedServer({ ...editedServer, skill_uuid: selected.uuid });
        setSkillSearchTerm(selected.name);
        setIsSkillSelectOpen(false);
      }
    }
  };

  const handleClearSkill = () => {
    setEditedServer({ ...editedServer, skill_uuid: '' });
    setSkillSearchTerm('');
  };

  const handleEditClick = () => {
    if (server) {
      setEditedServer({
        name: server.name,
        version: server.version || '',
        description: server.description || '',
        state: server.state || 'approved',
        tags: server.tags || [],
        port: server.port,
        skill_uuid: server.skill_uuid || '',
        protocol: server.protocol || 'webdav',
        extra: server.extra || {},
      });
      setExtraInput(JSON.stringify(server.extra || {}, null, 2));
      if (server.skill_uuid && allSkills) {
        const currentSkill = allSkills.find(s => s.uuid === server.skill_uuid);
        if (currentSkill) setSkillSearchTerm(currentSkill.name);
      }
      setIsEditModalOpen(true);
    }
  };

  const handleUpdateServer = () => {
    if (!editedServer.name || !editedServer.description) {
      setEditError('Please fill in all required fields');
      return;
    }
    let parsedExtra = {};
    try {
      parsedExtra = JSON.parse(extraInput);
      if (typeof parsedExtra !== 'object' || Array.isArray(parsedExtra)) {
        setEditError('Additional Information must be a valid JSON object');
        return;
      }
    } catch {
      setEditError('Additional Information must be valid JSON');
      return;
    }
    updateMutation.mutate({ ...editedServer, extra: Object.keys(parsedExtra).length > 0 ? parsedExtra : undefined });
  };

  const handleAddTag = () => {
    if (tagInput.trim() && !editedServer.tags.includes(tagInput.trim())) {
      setEditedServer({ ...editedServer, tags: [...editedServer.tags, tagInput.trim()] });
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setEditedServer({ ...editedServer, tags: editedServer.tags.filter(t => t !== tagToRemove) });
  };

  if (isLoading) {
    return <PageSection><div className="loading-container"><Spinner size="xl" /></div></PageSection>;
  }

  if (error || !server) {
    return (
      <PageSection>
        <Alert variant="danger" title="Error loading vNFS server">
          {(error as Error)?.message || 'Server not found'}
        </Alert>
      </PageSection>
    );
  }

  const skillName = server.name;
  const port = server.port;
  const protocol = server.protocol || 'webdav';

  const webdavUrl = `http://localhost:${port}/${skillName}`;
  const webdavRcloneCmd = `rclone mount :webdav: /mnt/skill --webdav-url=${webdavUrl} --read-only --daemon`;
  const webdavDavfsCmd = `sudo mount -t davfs ${webdavUrl} /mnt/skill`;
  const webdavWindowsCmd = `net use Z: ${webdavUrl}`;
  const nfsMountCmd = `sudo mount -t nfs localhost:/ /mnt/skill -o port=${port},mountport=${port},nfsvers=3,proto=tcp,nolock,soft`;
  const nfsSkillPath = `/mnt/skill/${skillName}/`;

  return (
    <>
      <PageSection variant="light">
        <Breadcrumb>
          <BreadcrumbItem to="/vnfs-servers" onClick={(e) => { e.preventDefault(); navigate('/vnfs-servers'); }}>
            Virtual NFS Servers
          </BreadcrumbItem>
          <BreadcrumbItem isActive>{server.name}</BreadcrumbItem>
        </Breadcrumb>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
          <Title headingLevel="h1" size="2xl">{server.name}</Title>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <Button variant="secondary" icon={<EditIcon />} onClick={handleEditClick}>Edit</Button>
            <Button variant="danger" icon={<TrashIcon />} onClick={() => setIsDeleteModalOpen(true)}>Delete</Button>
          </div>
        </div>
      </PageSection>

      <PageSection>
        {/* Server Information */}
        <Card>
          <CardTitle>Server Information</CardTitle>
          <CardBody>
            <DescriptionList isHorizontal>
              <DescriptionListGroup>
                <DescriptionListTerm>Name</DescriptionListTerm>
                <DescriptionListDescription>{server.name}</DescriptionListDescription>
              </DescriptionListGroup>

              <DescriptionListGroup>
                <DescriptionListTerm>Description</DescriptionListTerm>
                <DescriptionListDescription>{server.description || 'No description'}</DescriptionListDescription>
              </DescriptionListGroup>

              <DescriptionListGroup>
                <DescriptionListTerm>Protocol</DescriptionListTerm>
                <DescriptionListDescription>
                  <Label color={protocol === 'nfs' ? 'blue' : 'cyan'}>{protocol}</Label>
                </DescriptionListDescription>
              </DescriptionListGroup>

              {server.port && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Port</DescriptionListTerm>
                  <DescriptionListDescription>{server.port}</DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {server.version && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Version</DescriptionListTerm>
                  <DescriptionListDescription>{server.version}</DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {server.state && (
                <DescriptionListGroup>
                  <DescriptionListTerm>State</DescriptionListTerm>
                  <DescriptionListDescription>
                    <Label color={server.state === 'approved' ? 'green' : server.state === 'checked' ? 'blue' : server.state === 'new' ? 'cyan' : 'orange'}>
                      {server.state}
                    </Label>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              <DescriptionListGroup>
                <DescriptionListTerm>Status</DescriptionListTerm>
                <DescriptionListDescription>
                  {server.running ? <Label color="green">Running</Label> : <Label color="red">Stopped</Label>}
                </DescriptionListDescription>
              </DescriptionListGroup>

              {server.skill_uuid && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Skill UUID</DescriptionListTerm>
                  <DescriptionListDescription>
                    <Text component="small" style={{ fontFamily: 'monospace' }}>{server.skill_uuid}</Text>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {server.tags && server.tags.length > 0 && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Tags</DescriptionListTerm>
                  <DescriptionListDescription>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {server.tags.map(tag => <Label key={tag} color={getTagColor(tag)}>{tag}</Label>)}
                    </div>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {server.created_at && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Created</DescriptionListTerm>
                  <DescriptionListDescription>{new Date(server.created_at).toLocaleString()}</DescriptionListDescription>
                </DescriptionListGroup>
              )}

              {server.modified_at && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Last Modified</DescriptionListTerm>
                  <DescriptionListDescription>{new Date(server.modified_at).toLocaleString()}</DescriptionListDescription>
                </DescriptionListGroup>
              )}

              <DescriptionListGroup>
                <DescriptionListTerm>UUID</DescriptionListTerm>
                <DescriptionListDescription>
                  <Text component="small" style={{ fontFamily: 'monospace' }}>{server.uuid}</Text>
                </DescriptionListDescription>
              </DescriptionListGroup>

              {server.extra && Object.keys(server.extra).length > 0 && (
                <DescriptionListGroup>
                  <DescriptionListTerm>Additional Information</DescriptionListTerm>
                  <DescriptionListDescription>
                    <CodeBlock>
                      <CodeBlockCode>{JSON.stringify(server.extra, null, 2)}</CodeBlockCode>
                    </CodeBlock>
                  </DescriptionListDescription>
                </DescriptionListGroup>
              )}
            </DescriptionList>
          </CardBody>
        </Card>

        {/* Runtime Information */}
        {server.running && (
          <Card style={{ marginTop: '1rem' }}>
            <CardTitle>Runtime Information</CardTitle>
            <CardBody>
              <DescriptionList isHorizontal>
                <DescriptionListGroup>
                  <DescriptionListTerm>Running</DescriptionListTerm>
                  <DescriptionListDescription><Label color="green">Yes</Label></DescriptionListDescription>
                </DescriptionListGroup>
                {server.port && (
                  <DescriptionListGroup>
                    <DescriptionListTerm>Port</DescriptionListTerm>
                    <DescriptionListDescription>{server.port}</DescriptionListDescription>
                  </DescriptionListGroup>
                )}
                <DescriptionListGroup>
                  <DescriptionListTerm>Protocol</DescriptionListTerm>
                  <DescriptionListDescription>{protocol}</DescriptionListDescription>
                </DescriptionListGroup>
                {server.export_path && (
                  <DescriptionListGroup>
                    <DescriptionListTerm>Export Path</DescriptionListTerm>
                    <DescriptionListDescription>
                      <Text component="small" style={{ fontFamily: 'monospace' }}>{server.export_path}</Text>
                    </DescriptionListDescription>
                  </DescriptionListGroup>
                )}
              </DescriptionList>
            </CardBody>
          </Card>
        )}

        {/* Mount Instructions */}
        <Card style={{ marginTop: '1rem' }}>
          <CardTitle>Mount Instructions</CardTitle>
          <CardBody>
            <Text style={{ marginBottom: '1rem' }}>
              Use these commands to mount the skill filesystem on your machine.
              Ensure the server is running before mounting.
            </Text>

            {protocol === 'webdav' && (
              <>
                <Title headingLevel="h4" size="md" style={{ marginBottom: '0.5rem' }}>Via rclone (FUSE, no root required)</Title>
                <ClipboardCopy isReadOnly hoverTip="Copy" clickTip="Copied" style={{ marginBottom: '0.5rem' }}>
                  {webdavRcloneCmd}
                </ClipboardCopy>
                <Text component="small" style={{ display: 'block', marginBottom: '1.5rem', color: '#6a6e73' }}>
                  Install: <code>brew install rclone</code> / <code>apt install rclone</code> / <code>dnf install rclone</code>
                </Text>

                <Title headingLevel="h4" size="md" style={{ marginBottom: '0.5rem' }}>Via davfs2 (Linux)</Title>
                <ClipboardCopy isReadOnly hoverTip="Copy" clickTip="Copied" style={{ marginBottom: '0.5rem' }}>
                  {webdavDavfsCmd}
                </ClipboardCopy>
                <Text component="small" style={{ display: 'block', marginBottom: '1.5rem', color: '#6a6e73' }}>
                  Install: <code>apt install davfs2</code> / <code>dnf install davfs2</code>
                </Text>

                <Title headingLevel="h4" size="md" style={{ marginBottom: '0.5rem' }}>Via net use (Windows / PowerShell)</Title>
                <ClipboardCopy isReadOnly hoverTip="Copy" clickTip="Copied" style={{ marginBottom: '0.5rem' }}>
                  {webdavWindowsCmd}
                </ClipboardCopy>
                <Text component="small" style={{ display: 'block', color: '#6a6e73' }}>
                  Mounts as drive <code>Z:</code> — change the letter if already in use. To unmount: <code>net use Z: /delete</code>
                </Text>
              </>
            )}

            {protocol === 'nfs' && (
              <>
                <Title headingLevel="h4" size="md" style={{ marginBottom: '0.5rem' }}>NFSv3</Title>
                <ClipboardCopy isReadOnly hoverTip="Copy" clickTip="Copied" style={{ marginBottom: '0.5rem' }}>
                  {nfsMountCmd}
                </ClipboardCopy>
                <Text component="small" style={{ display: 'block', marginBottom: '1rem', color: '#6a6e73' }}>
                  Install: <code>apt install nfs-common</code> / <code>dnf install nfs-utils</code>
                </Text>
                <Text component="small" style={{ display: 'block', color: '#6a6e73' }}>
                  Skill files are at: <code>{nfsSkillPath}</code>
                </Text>
              </>
            )}
          </CardBody>
        </Card>
      </PageSection>

      {/* Edit Modal */}
      <Modal
        variant={ModalVariant.medium}
        title="Edit vNFS Server"
        isOpen={isEditModalOpen}
        onClose={() => { setIsEditModalOpen(false); setEditError(''); }}
        actions={[
          <Button key="save" variant="primary" onClick={handleUpdateServer} isLoading={updateMutation.isPending}>Save</Button>,
          <Button key="cancel" variant="link" onClick={() => { setIsEditModalOpen(false); setEditError(''); }}>Cancel</Button>,
        ]}
      >
        {editError && <Alert variant="danger" title="Error" isInline style={{ marginBottom: '1rem' }}>{editError}</Alert>}
        <Form>
          <FormGroup label="Skill" fieldId="edit-server-skill">
            <Select
              id="edit-server-skill-select"
              isOpen={isSkillSelectOpen}
              selected={null}
              onSelect={handleSelectSkill}
              onOpenChange={(isOpen) => setIsSkillSelectOpen(isOpen)}
              toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
                <MenuToggle ref={toggleRef} onClick={() => setIsSkillSelectOpen(!isSkillSelectOpen)} isExpanded={isSkillSelectOpen} style={{ width: '100%' }}>
                  {skillSearchTerm || 'Select a skill...'}
                </MenuToggle>
              )}
            >
              <SelectList>
                <TextInput
                  type="search"
                  value={skillSearchTerm}
                  onChange={(_, value) => setSkillSearchTerm(value)}
                  placeholder="Search skills..."
                  style={{ padding: '0.5rem', borderBottom: '1px solid #d2d2d2' }}
                />
                {filteredSkills.length === 0 ? (
                  <SelectOption isDisabled>{skillSearchTerm ? 'No skills found' : 'Start typing to search...'}</SelectOption>
                ) : (
                  filteredSkills.map(skill => (
                    <SelectOption key={skill.uuid} value={skill.name}>
                      {skill.name} {skill.description && `- ${skill.description}`}
                    </SelectOption>
                  ))
                )}
              </SelectList>
            </Select>
            {editedServer.skill_uuid && (
              <div style={{ marginTop: '0.5rem' }}>
                <Button variant="plain" onClick={handleClearSkill} style={{ padding: '0.25rem 0.5rem', backgroundColor: '#e7f1fa', border: '1px solid #bee1f4', borderRadius: '3px' }}>
                  {skillSearchTerm} ✕
                </Button>
              </div>
            )}
          </FormGroup>
          <FormGroup label="Protocol" isRequired fieldId="edit-server-protocol">
            <div style={{ display: 'flex', gap: '1.5rem' }}>
              <Radio id="edit-protocol-webdav" name="edit-protocol" label="WebDAV" value="webdav" isChecked={editedServer.protocol === 'webdav'} onChange={() => setEditedServer({ ...editedServer, protocol: 'webdav' })} />
              <Radio id="edit-protocol-nfs" name="edit-protocol" label="NFS" value="nfs" isChecked={editedServer.protocol === 'nfs'} onChange={() => setEditedServer({ ...editedServer, protocol: 'nfs' })} />
            </div>
          </FormGroup>
          <FormGroup label="Name" isRequired fieldId="edit-server-name">
            <TextInput isRequired type="text" id="edit-server-name" value={editedServer.name} onChange={(_, v) => setEditedServer({ ...editedServer, name: v })} />
          </FormGroup>
          <FormGroup label="Description" isRequired fieldId="edit-server-description">
            <TextArea isRequired id="edit-server-description" value={editedServer.description} onChange={(_, v) => setEditedServer({ ...editedServer, description: v })} rows={2} />
          </FormGroup>
          <FormGroup label="Version" fieldId="edit-server-version">
            <TextInput type="text" id="edit-server-version" value={editedServer.version} onChange={(_, v) => setEditedServer({ ...editedServer, version: v })} placeholder="e.g., 1.0.0" />
          </FormGroup>
          <FormGroup label="State" isRequired fieldId="edit-server-state">
            <FormSelect value={editedServer.state} onChange={(_, v) => setEditedServer({ ...editedServer, state: v as typeof editedServer.state })} id="edit-server-state">
              <FormSelectOption value="unknown" label="Unknown" />
              <FormSelectOption value="any" label="Any" />
              <FormSelectOption value="new" label="New" />
              <FormSelectOption value="checked" label="Checked" />
              <FormSelectOption value="approved" label="Approved" />
            </FormSelect>
          </FormGroup>
          <FormGroup label="Port" fieldId="edit-server-port">
            <TextInput type="number" id="edit-server-port" value={editedServer.port?.toString() || ''} onChange={(_, v) => setEditedServer({ ...editedServer, port: v ? parseInt(v) : undefined })} placeholder="Leave empty for auto-assignment" />
          </FormGroup>
          <FormGroup label="Tags" fieldId="edit-server-tags">
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <TextInput type="text" id="edit-server-tags" value={tagInput} onChange={(_, v) => setTagInput(v)} placeholder="Add a tag" onKeyPress={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddTag(); } }} />
              <Button variant="secondary" onClick={handleAddTag}>Add</Button>
            </div>
            {editedServer.tags.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {editedServer.tags.map(tag => (
                  <Button key={tag} variant="plain" onClick={() => handleRemoveTag(tag)} style={{ padding: '0.25rem 0.5rem', backgroundColor: '#f0f0f0', border: '1px solid #d2d2d2', borderRadius: '3px' }}>
                    {tag} ✕
                  </Button>
                ))}
              </div>
            )}
          </FormGroup>
          <FormGroup label="Additional Information (JSON)" fieldId="edit-server-extra">
            <TextArea id="edit-server-extra" value={extraInput} onChange={(_, v) => setExtraInput(v)} rows={4} style={{ fontFamily: 'monospace' }} />
          </FormGroup>
        </Form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Delete vNFS Server"
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        actions={[
          <Button key="delete" variant="danger" onClick={() => deleteMutation.mutate()} isLoading={deleteMutation.isPending}>Delete</Button>,
          <Button key="cancel" variant="link" onClick={() => setIsDeleteModalOpen(false)}>Cancel</Button>,
        ]}
      >
        <Text>
          Are you sure you want to delete vNFS server <strong>{server.name}</strong>? This action cannot be undone.
        </Text>
      </Modal>
    </>
  );
}
