// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

/**
 * Returns true if itemTags satisfies the filter.
 * - Wildcard filter "quality-score:*" matches any tag starting with "quality-score:"
 * - Plain filter "python" requires an exact tag match
 */
export function tagMatchesFilter(itemTags: string[], filter: string): boolean {
  if (filter.endsWith(':*')) {
    const prefix = filter.slice(0, -1); // "quality-score:"
    return itemTags.some(t => t.startsWith(prefix));
  }
  return itemTags.includes(filter);
}
