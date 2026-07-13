// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0
//
// Client-side mirror of skillberry_store.tools.anthropic.naming. Keep the
// rules in sync — see that Python module for the authoritative definition.

const SLUG_MAX_LEN = 64;
const SLUG_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;

export interface SlugValidation {
  ok: boolean;
  suggested: string;
  reason: string;
}

export function suggestSlug(name: string | undefined | null): string {
  if (!name) return '';
  const lowered = name.trim().toLowerCase();
  let slug = lowered.replace(/[^a-z0-9]+/g, '-');
  slug = slug.replace(/^-+|-+$/g, '');
  if (slug.length > SLUG_MAX_LEN) {
    slug = slug.slice(0, SLUG_MAX_LEN).replace(/-+$/g, '');
  }
  return slug;
}

export function validateSkillSlug(name: string | undefined | null): SlugValidation {
  if (!name) {
    return { ok: false, suggested: '', reason: 'Skill name is empty.' };
  }
  if (name.length > SLUG_MAX_LEN) {
    return {
      ok: false,
      suggested: suggestSlug(name),
      reason: `Skill name exceeds ${SLUG_MAX_LEN} characters.`,
    };
  }
  if (!SLUG_RE.test(name)) {
    return {
      ok: false,
      suggested: suggestSlug(name),
      reason:
        'Skill name must match [a-z0-9]+(-[a-z0-9]+)* (lowercase letters, digits, and single hyphens between them).',
    };
  }
  return { ok: true, suggested: name, reason: '' };
}
