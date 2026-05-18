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

interface NamespaceFilterProps {
  allNamespaces: string[];
  selectedNamespaces: string[];
  onNamespacesChange: (namespaces: string[]) => void;
  placeholder?: string;
}

export function NamespaceFilter({ 
  allNamespaces, 
  selectedNamespaces, 
  onNamespacesChange, 
  placeholder = 'Filter by namespace...' 
}: NamespaceFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredNamespaces = useMemo(() => {
    const lowerSearch = searchTerm.toLowerCase();
    return allNamespaces.filter(namespace =>
      namespace.toLowerCase().includes(lowerSearch) &&
      !selectedNamespaces.includes(namespace)
    );
  }, [allNamespaces, searchTerm, selectedNamespaces]);

  const handleSelectNamespace = (_event: React.MouseEvent | undefined, value: string | number | undefined) => {
    if (typeof value === 'string' && value && !selectedNamespaces.includes(value)) {
      onNamespacesChange([...selectedNamespaces, value]);
      setIsOpen(false);
      setSearchTerm('');
    }
  };

  const handleRemoveNamespace = (namespaceToRemove: string) => {
    onNamespacesChange(selectedNamespaces.filter(namespace => namespace !== namespaceToRemove));
  };

  const handleClearAll = () => {
    onNamespacesChange([]);
  };

  // Don't render if there are no namespaces available
  if (allNamespaces.length === 0) {
    return null;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', minWidth: '250px' }}>
      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <Select
          id="namespace-filter-select"
          isOpen={isOpen}
          selected={null}
          onSelect={handleSelectNamespace}
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
              placeholder="Search namespaces..."
              style={{
                width: '100%',
                padding: '0.5rem',
                border: 'none',
                borderBottom: '1px solid #d2d2d2',
                outline: 'none',
              }}
            />
            {filteredNamespaces.length === 0 ? (
              <SelectOption isDisabled>
                {searchTerm ? 'No namespaces found' : 'All namespaces selected'}
              </SelectOption>
            ) : (
              filteredNamespaces.map((namespace) => (
                <SelectOption key={namespace} value={namespace}>
                  {namespace}
                </SelectOption>
              ))
            )}
          </SelectList>
        </Select>
        {selectedNamespaces.length > 0 && (
          <Button variant="link" onClick={handleClearAll} style={{ padding: '0.25rem 0.5rem' }}>
            Clear all
          </Button>
        )}
      </div>
      {selectedNamespaces.length > 0 && (
        <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
          {selectedNamespaces.map((namespace) => (
            <Label
              key={namespace}
              color="blue"
              isCompact
              onClose={() => handleRemoveNamespace(namespace)}
            >
              {namespace}
            </Label>
          ))}
        </div>
      )}
    </div>
  );
}

// Made with Bob
