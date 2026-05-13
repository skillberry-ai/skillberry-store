// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useNavigate } from 'react-router-dom';
import { Label } from '@patternfly/react-core';
import { getTagColor } from '../utils/tagColors';
import type { Skill } from '@/types';

interface SkillCardProps {
  skill: Skill;
  isSelected: boolean;
  onSelect: (isSelected: boolean) => void;
}

const STATE_COLORS: Record<string, { background: string; color: string }> = {
  approved: { background: '#d3f7d3', color: '#1e4620' },
  checked:  { background: '#bee1f4', color: '#002952' },
  new:      { background: '#d2f4ea', color: '#0d5738' },
  unknown:  { background: '#f2f2f2', color: '#555555' },
  any:      { background: '#f2f2f2', color: '#555555' },
};

export function SkillCard({ skill, isSelected, onSelect }: SkillCardProps) {
  const navigate = useNavigate();
  const stateColor = STATE_COLORS[skill.state ?? 'unknown'] ?? STATE_COLORS.unknown;
  const visibleTags = skill.tags?.filter(t => !t.startsWith('namespace:')) ?? [];

  return (
    <div
      style={{
        background: '#fff',
        border: isSelected ? '2px solid #0f62fe' : '1px solid #d2d2d2',
        borderRadius: '6px',
        overflow: 'hidden',
        boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
      }}
      onClick={() => navigate(`/skills/${skill.name}`)}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 14px 10px',
          background: isSelected ? '#f0f7ff' : '#fff',
        }}
      >
        {/* Checkbox + name + state badge */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '6px' }}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={e => {
              e.stopPropagation();
              onSelect(e.target.checked);
            }}
            onClick={e => e.stopPropagation()}
            style={{ marginTop: '2px', flexShrink: 0, cursor: 'pointer' }}
          />
          <div style={{ flex: 1, minWidth: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span style={{ fontWeight: 600, fontSize: '14px', color: isSelected ? '#0f62fe' : '#151515' }}>
              {skill.name}
            </span>
            {skill.state && (
              <span style={{
                background: stateColor.background,
                color: stateColor.color,
                fontSize: '11px',
                padding: '2px 6px',
                borderRadius: '10px',
                flexShrink: 0,
                marginLeft: '6px',
                whiteSpace: 'nowrap',
              }}>
                {skill.state}
              </span>
            )}
          </div>
        </div>

        {/* Description — 2-line clamp */}
        <p style={{
          color: '#444',
          margin: '0 0 8px',
          lineHeight: '1.4',
          fontSize: '13px',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          paddingLeft: '22px',
        }}>
          {skill.description || 'No description'}
        </p>

        {/* Tags */}
        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', paddingLeft: '22px', minHeight: '20px' }}>
          {visibleTags.length > 0
            ? visibleTags.map(tag => (
                <Label key={tag} color={getTagColor(tag)} isCompact>{tag}</Label>
              ))
            : <span style={{ fontSize: '12px', color: '#aaa' }}>no tags</span>
          }
        </div>
      </div>

      {/* Footer strip */}
      <div style={{
        background: '#f5f5f5',
        borderTop: '1px solid #e0e0e0',
        padding: '8px 14px',
        display: 'flex',
        gap: '12px',
        color: '#555',
        fontSize: '12px',
        alignItems: 'center',
        marginTop: 'auto',
      }}>
        <span>
          {skill.tools && skill.tools.length > 0
            ? `🔧 ${skill.tools.length} tools`
            : '— tools'}
        </span>
        <span>
          {skill.snippets && skill.snippets.length > 0
            ? `📄 ${skill.snippets.length} snippets`
            : '— snippets'}
        </span>
        {skill.version && (
          <span style={{ marginLeft: 'auto', color: '#6a6e73' }}>{skill.version}</span>
        )}
      </div>
    </div>
  );
}
