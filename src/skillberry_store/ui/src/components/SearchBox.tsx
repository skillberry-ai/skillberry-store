// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { useState } from 'react';
import {
  SearchInput,
  ToggleGroup,
  ToggleGroupItem,
  Popover,
  Button,
  Form,
  FormGroup,
  NumberInput,
  TextContent,
  Text,
} from '@patternfly/react-core';
import { CogIcon } from '@patternfly/react-icons';

export type SearchMode = 'text' | 'semantic';

interface SearchBoxProps {
  value: string;
  onChange: (value: string) => void;
  onClear: () => void;
  mode: SearchMode;
  onModeChange: (mode: SearchMode) => void;
  placeholder?: string;
  // Semantic search configuration
  maxResults?: number;
  onMaxResultsChange?: (value: number) => void;
  similarityThreshold?: number;
  onSimilarityThresholdChange?: (value: number) => void;
}

export function SearchBox({
  value,
  onChange,
  onClear,
  mode,
  onModeChange,
  placeholder = 'Search...',
  maxResults = 10,
  onMaxResultsChange,
  similarityThreshold = 1,
  onSimilarityThresholdChange,
}: SearchBoxProps) {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  return (
    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
      <div style={{ flex: '1', minWidth: '200px' }}>
        <SearchInput
          placeholder={placeholder}
          value={value}
          onChange={(_, val) => onChange(val)}
          onClear={onClear}
        />
      </div>
      
      <ToggleGroup aria-label="Search mode">
        <ToggleGroupItem
          text="Text"
          buttonId="text-search"
          isSelected={mode === 'text'}
          onChange={() => onModeChange('text')}
        />
        <ToggleGroupItem
          text="Semantic"
          buttonId="semantic-search"
          isSelected={mode === 'semantic'}
          onChange={() => onModeChange('semantic')}
        />
      </ToggleGroup>

      {mode === 'semantic' && (
        <Popover
          aria-label="Semantic search settings"
          headerContent={<div>Semantic Search Settings</div>}
          bodyContent={
            <Form>
              <FormGroup label="Max Results" fieldId="max-results">
                <TextContent>
                  <Text component="small" style={{ display: 'block', marginBottom: '0.5rem', color: '#6a6e73' }}>
                    Maximum number of results to return (1-50)
                  </Text>
                </TextContent>
                <NumberInput
                  value={maxResults}
                  min={1}
                  max={50}
                  onMinus={() => onMaxResultsChange?.(Math.max(1, maxResults - 1))}
                  onPlus={() => onMaxResultsChange?.(Math.min(50, maxResults + 1))}
                  onChange={(event) => {
                    const val = Number((event.target as HTMLInputElement).value);
                    if (!isNaN(val) && val >= 1 && val <= 50) {
                      onMaxResultsChange?.(val);
                    }
                  }}
                  inputName="max-results"
                  inputAriaLabel="max results"
                  minusBtnAriaLabel="minus"
                  plusBtnAriaLabel="plus"
                />
              </FormGroup>
              
              <FormGroup label="Similarity Threshold" fieldId="similarity-threshold">
                <TextContent>
                  <Text component="small" style={{ display: 'block', marginBottom: '0.5rem', color: '#6a6e73' }}>
                    Lower values = more similar results (0.0-2.0)
                  </Text>
                </TextContent>
                <NumberInput
                  value={similarityThreshold}
                  min={0}
                  max={2}
                  step={0.1}
                  onMinus={() => onSimilarityThresholdChange?.(Math.max(0, similarityThreshold - 0.1))}
                  onPlus={() => onSimilarityThresholdChange?.(Math.min(2, similarityThreshold + 0.1))}
                  onChange={(event) => {
                    const val = Number((event.target as HTMLInputElement).value);
                    if (!isNaN(val) && val >= 0 && val <= 2) {
                      onSimilarityThresholdChange?.(val);
                    }
                  }}
                  inputName="similarity-threshold"
                  inputAriaLabel="similarity threshold"
                  minusBtnAriaLabel="minus"
                  plusBtnAriaLabel="plus"
                />
              </FormGroup>
            </Form>
          }
          isVisible={isSettingsOpen}
          shouldClose={() => setIsSettingsOpen(false)}
        >
          <Button
            variant="plain"
            aria-label="Semantic search settings"
            onClick={() => setIsSettingsOpen(!isSettingsOpen)}
          >
            <CogIcon />
          </Button>
        </Popover>
      )}
    </div>
  );
}