// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import type { Skill } from '@/types';
import { SkillCard } from './SkillCard';

interface SkillCardViewProps {
  skills: Skill[];
  selectedSkills: string[];
  onSelectSkill: (name: string, isSelected: boolean) => void;
}

export function SkillCardView({ skills, selectedSkills, onSelectSkill }: SkillCardViewProps) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
      gap: '14px',
    }}>
      {skills.map(skill => (
        <SkillCard
          key={skill.uuid}
          skill={skill}
          isSelected={selectedSkills.includes(skill.name)}
          onSelect={(isSelected) => onSelectSkill(skill.name, isSelected)}
        />
      ))}
    </div>
  );
}
