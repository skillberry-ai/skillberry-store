// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState, useMemo } from 'react';
import {
  Select,
  SelectOption,
  SelectList,
  MenuToggle,
  MenuToggleElement,
  Label,
  Button,
} from '@patternfly/react-core';
import { getTagColor } from '../utils/tagColors';

interface TagFilterProps {
  allTags: string[];
  selectedTags: string[];
  onTagsChange: (tags: string[]) => void;
  placeholder?: string;
}

export function TagFilter({ allTags, selectedTags, onTagsChange, placeholder = 'Filter by tags...' }: TagFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredTags = useMemo(() => {
    const lowerSearch = searchTerm.toLowerCase();
    return allTags.filter(tag =>
      tag.toLowerCase().includes(lowerSearch) &&
      !selectedTags.includes(tag)
    );
  }, [allTags, searchTerm, selectedTags]);

  const handleSelectTag = (_event: React.MouseEvent | undefined, value: string | number | undefined) => {
    if (typeof value === 'string' && value && !selectedTags.includes(value)) {
      onTagsChange([...selectedTags, value]);
      setIsOpen(false);
      setSearchTerm('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    onTagsChange(selectedTags.filter(tag => tag !== tagToRemove));
  };

  const handleClearAll = () => {
    onTagsChange([]);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', minWidth: '250px' }}>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <Select
          id="tag-filter-select"
          isOpen={isOpen}
          selected={null}
          onSelect={handleSelectTag}
          onOpenChange={(isOpen) => setIsOpen(isOpen)}
          toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
            <MenuToggle
              ref={toggleRef}
              onClick={() => setIsOpen(!isOpen)}
              isExpanded={isOpen}
              style={{ width: '200px' }}
            >
              {placeholder}
            </MenuToggle>
          )}
        >
          <SelectList>
            <input
              type="search"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search tags..."
              style={{
                width: '100%',
                padding: '0.5rem',
                border: 'none',
                borderBottom: '1px solid #d2d2d2',
                outline: 'none',
              }}
            />
            {filteredTags.length === 0 ? (
              <SelectOption isDisabled>
                {searchTerm ? 'No tags found' : allTags.length === 0 ? 'No tags available' : 'All tags selected'}
              </SelectOption>
            ) : (
              filteredTags.map((tag) => (
                <SelectOption key={tag} value={tag}>
                  {tag}
                </SelectOption>
              ))
            )}
          </SelectList>
        </Select>
        {selectedTags.length > 0 && (
          <Button variant="link" onClick={handleClearAll} style={{ padding: '0.25rem 0.5rem' }}>
            Clear all
          </Button>
        )}
      </div>
      {selectedTags.length > 0 && (
        <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
          {selectedTags.map((tag) => (
            <Label
              key={tag}
              color={getTagColor(tag)}
              isCompact
              onClose={() => handleRemoveTag(tag)}
            >
              {tag}
            </Label>
          ))}
        </div>
      )}
    </div>
  );
}