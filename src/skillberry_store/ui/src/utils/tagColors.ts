// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

/**
 * Generate a consistent color for a tag based on its content hash
 * Using colors with better contrast on white backgrounds
 */
export function getTagColor(tag: string): 'blue' | 'green' | 'orange' | 'purple' | 'red' | 'grey' | 'gold' {
  // Simple hash function
  let hash = 0;
  for (let i = 0; i < tag.length; i++) {
    hash = ((hash << 5) - hash) + tag.charCodeAt(i);
    hash = hash & hash; // Convert to 32-bit integer
  }
  
  // Map hash to PatternFly Label colors with good contrast
  // Removed 'cyan' as it has poor contrast on white backgrounds
  const colors: Array<'blue' | 'green' | 'orange' | 'purple' | 'red' | 'grey' | 'gold'> = [
    'blue',
    'green',
    'orange',
    'purple',
    'red',
    'grey',
    'gold'
  ];
  
  const index = Math.abs(hash) % colors.length;
  return colors[index];
}