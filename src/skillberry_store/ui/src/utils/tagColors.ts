// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

/**
 * Generate a consistent color for a tag based on its content hash
 */
export function getTagColor(tag: string): 'blue' | 'cyan' | 'green' | 'orange' | 'purple' | 'red' | 'grey' {
  // Simple hash function
  let hash = 0;
  for (let i = 0; i < tag.length; i++) {
    hash = ((hash << 5) - hash) + tag.charCodeAt(i);
    hash = hash & hash; // Convert to 32-bit integer
  }
  
  // Map hash to PatternFly Label colors
  const colors: Array<'blue' | 'cyan' | 'green' | 'orange' | 'purple' | 'red' | 'grey'> = [
    'blue',
    'cyan', 
    'green',
    'orange',
    'purple',
    'red',
    'grey'
  ];
  
  const index = Math.abs(hash) % colors.length;
  return colors[index];
}