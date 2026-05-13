// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useNavigate } from 'react-router-dom';
import { getTagColor } from '../utils/tagColors';
import { Label } from '@patternfly/react-core';
import { Table, Thead, Tr, Th, Tbody, Td, ThProps } from '@patternfly/react-table';
import type { Skill } from '@/types';

interface SkillListViewProps {
  skills: Skill[];
  selectedSkills: string[];
  onSelectSkill: (name: string, isSelected: boolean) => void;
  onSelectAll: (isSelected: boolean) => void;
  getSortParams: (columnIndex: number) => ThProps['sort'];
}

export function SkillListView({
  skills,
  selectedSkills,
  onSelectSkill,
  onSelectAll,
  getSortParams,
}: SkillListViewProps) {
  const navigate = useNavigate();

  return (
    <Table aria-label="Skills table" variant="compact">
      <Thead>
        <Tr>
          <Th
            select={{
              onSelect: (_event, isSelected) => onSelectAll(isSelected),
              isSelected: selectedSkills.length === skills.length && skills.length > 0,
            }}
          />
          <Th sort={getSortParams(0)}>Name</Th>
          <Th sort={getSortParams(1)}>Description</Th>
          <Th>Tags</Th>
          <Th>Tools</Th>
          <Th>Snippets</Th>
          <Th sort={getSortParams(2)}>Version</Th>
        </Tr>
      </Thead>
      <Tbody>
        {skills.map((skill, index) => (
          <Tr key={skill.uuid}>
            <Td
              select={{
                rowIndex: index,
                onSelect: (_event, isSelected) => onSelectSkill(skill.name, isSelected),
                isSelected: selectedSkills.includes(skill.name),
              }}
            />
            <Td
              dataLabel="Name"
              onClick={() => navigate(`/skills/${skill.name}`)}
              style={{ cursor: 'pointer' }}
            >
              {skill.name}
            </Td>
            <Td
              dataLabel="Description"
              onClick={() => navigate(`/skills/${skill.name}`)}
              style={{ cursor: 'pointer' }}
            >
              {skill.description || 'No description'}
            </Td>
            <Td
              dataLabel="Tags"
              onClick={() => navigate(`/skills/${skill.name}`)}
              style={{ cursor: 'pointer' }}
            >
              {skill.tags && skill.tags.filter(tag => !tag.startsWith('namespace:')).length > 0 ? (
                <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                  {skill.tags
                    .filter(tag => !tag.startsWith('namespace:'))
                    .map((tag) => (
                      <Label key={tag} color={getTagColor(tag)} isCompact>{tag}</Label>
                    ))}
                </div>
              ) : '-'}
            </Td>
            <Td
              dataLabel="Tools"
              onClick={() => navigate(`/skills/${skill.name}`)}
              style={{ cursor: 'pointer' }}
            >
              {skill.tools && skill.tools.length > 0 ? skill.tools.length : '-'}
            </Td>
            <Td
              dataLabel="Snippets"
              onClick={() => navigate(`/skills/${skill.name}`)}
              style={{ cursor: 'pointer' }}
            >
              {skill.snippets && skill.snippets.length > 0 ? skill.snippets.length : '-'}
            </Td>
            <Td
              dataLabel="Version"
              onClick={() => navigate(`/skills/${skill.name}`)}
              style={{ cursor: 'pointer' }}
            >
              {skill.version || '-'}
            </Td>
          </Tr>
        ))}
      </Tbody>
    </Table>
  );
}
