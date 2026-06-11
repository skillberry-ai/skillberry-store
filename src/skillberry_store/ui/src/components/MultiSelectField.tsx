// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState } from 'react';
import {
  Select,
  SelectList,
  SelectOption,
  MenuToggle,
} from '@patternfly/react-core';
import type { MenuToggleElement } from '@patternfly/react-core';

interface MultiSelectFieldProps {
  /** Fixed set of selectable option values. */
  options: string[];
  /** Currently selected values. */
  value: string[];
  /** Called with the new selected values. */
  onChange: (values: string[]) => void;
}

/**
 * Checkbox multi-select dropdown over a fixed option set. Used to render
 * plugin params_schema array fields that carry an `items.enum` (e.g. the SAST
 * engines list) instead of a comma-separated text box.
 */
export function MultiSelectField({ options, value, onChange }: MultiSelectFieldProps) {
  const [isOpen, setIsOpen] = useState(false);

  const toggle = (selected: string) => {
    if (value.includes(selected)) {
      onChange(value.filter((v) => v !== selected));
    } else {
      onChange([...value, selected]);
    }
  };

  const toggleText =
    value.length === 0 ? 'Select…' : value.join(', ');

  return (
    <Select
      id="multiselect-field"
      isOpen={isOpen}
      selected={value}
      onSelect={(_event, selectedValue) => toggle(String(selectedValue))}
      onOpenChange={(open) => setIsOpen(open)}
      popperProps={{ appendTo: () => document.body, width: 'trigger', enableFlip: true }}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          onClick={() => setIsOpen(!isOpen)}
          isExpanded={isOpen}
          isDisabled={options.length === 0}
          style={{ width: '100%' }}
        >
          {options.length === 0 ? 'No engines available' : toggleText}
        </MenuToggle>
      )}
    >
      <SelectList style={{ maxHeight: '16rem', overflowY: 'auto' }}>
        {options.map((opt) => (
          <SelectOption
            key={opt}
            value={opt}
            hasCheckbox
            isSelected={value.includes(opt)}
          >
            {opt}
          </SelectOption>
        ))}
      </SelectList>
    </Select>
  );
}
