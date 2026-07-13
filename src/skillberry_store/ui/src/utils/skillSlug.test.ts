// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect } from 'vitest';
import { suggestSlug, validateSkillSlug } from './skillSlug';

describe('validateSkillSlug', () => {
  it.each(['a', 'my-skill', 'abc123', 'web-design-guidelines'])(
    'accepts %s',
    (name: string) => {
      const result = validateSkillSlug(name);
      expect(result.ok).toBe(true);
      expect(result.suggested).toBe(name);
    }
  );

  it.each([
    ['My Skill', 'my-skill'],
    ['Foo_Bar', 'foo-bar'],
    ['UPPER', 'upper'],
    ['trailing-', 'trailing'],
    ['-leading', 'leading'],
  ])('rejects %s and suggests %s', (name: string, suggested: string) => {
    const result = validateSkillSlug(name);
    expect(result.ok).toBe(false);
    expect(result.suggested).toBe(suggested);
    expect(result.reason.length).toBeGreaterThan(0);
  });

  it('rejects empty name', () => {
    expect(validateSkillSlug('').ok).toBe(false);
    expect(validateSkillSlug(null).ok).toBe(false);
    expect(validateSkillSlug(undefined).ok).toBe(false);
  });
});

describe('suggestSlug', () => {
  it('returns empty for no alphanumerics', () => {
    expect(suggestSlug('---')).toBe('');
    expect(suggestSlug('')).toBe('');
  });

  it('trims dangling hyphens', () => {
    expect(suggestSlug('!Hello World!')).toBe('hello-world');
  });
});
