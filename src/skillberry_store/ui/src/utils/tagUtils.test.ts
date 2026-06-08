// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect } from 'vitest';
import { tagMatchesFilter } from './tagUtils';

describe('tagMatchesFilter', () => {
  describe('exact match (no wildcard)', () => {
    it('returns true when tag is present', () => {
      expect(tagMatchesFilter(['python', 'beta'], 'python')).toBe(true);
    });

    it('returns false when tag is absent', () => {
      expect(tagMatchesFilter(['python', 'beta'], 'java')).toBe(false);
    });

    it('returns false on empty tag list', () => {
      expect(tagMatchesFilter([], 'python')).toBe(false);
    });

    it('does not partially match plain tags', () => {
      expect(tagMatchesFilter(['python'], 'pyth')).toBe(false);
    });
  });

  describe('wildcard match (filter ends with :*)', () => {
    it('matches a tag with the given prefix', () => {
      expect(tagMatchesFilter(['quality-score:8'], 'quality-score:*')).toBe(true);
    });

    it('matches any value for the prefix', () => {
      expect(tagMatchesFilter(['quality-score:1'], 'quality-score:*')).toBe(true);
      expect(tagMatchesFilter(['quality-score:10'], 'quality-score:*')).toBe(true);
    });

    it('returns true if any tag in the list matches the prefix', () => {
      expect(tagMatchesFilter(['python', 'quality-score:7', 'beta'], 'quality-score:*')).toBe(true);
    });

    it('returns false when no tag matches the prefix', () => {
      expect(tagMatchesFilter(['performance-score:5', 'beta'], 'quality-score:*')).toBe(false);
    });

    it('does not match a tag that is exactly the prefix without a value', () => {
      expect(tagMatchesFilter(['quality-score'], 'quality-score:*')).toBe(false);
    });

    it('returns false on empty tag list', () => {
      expect(tagMatchesFilter([], 'quality-score:*')).toBe(false);
    });
  });
});
