// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AnthropicSkillImporter } from './AnthropicSkillImporter';
import * as api from '@/services/api';

// Mock the API
vi.mock('@/services/api', () => ({
  skillsApi: {
    list: vi.fn(),
  },
}));

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('AnthropicSkillImporter', () => {
  const mockOnClose = vi.fn();
  const mockOnImportComplete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock skillsApi.list to return empty array by default
    vi.mocked(api.skillsApi.list).mockResolvedValue([]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Batch Mode Toggle', () => {
    it('should render batch mode checkbox', () => {
      render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      const batchModeCheckbox = screen.getByLabelText(/Batch Mode - Import multiple skills/i);
      expect(batchModeCheckbox).toBeDefined();
      expect(batchModeCheckbox).not.toBeChecked();
    });

    it('should toggle batch mode when checkbox is clicked', () => {
      render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      const batchModeCheckbox = screen.getByLabelText(/Batch Mode - Import multiple skills/i) as HTMLInputElement;
      
      // Initially unchecked
      expect(batchModeCheckbox.checked).toBe(false);

      // Click to enable batch mode
      fireEvent.click(batchModeCheckbox);
      expect(batchModeCheckbox.checked).toBe(true);

      // Click again to disable
      fireEvent.click(batchModeCheckbox);
      expect(batchModeCheckbox.checked).toBe(false);
    });

    it('should disable batch mode for ZIP file source', () => {
      render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      // Switch to ZIP file source
      const zipButton = screen.getByText('ZIP File');
      fireEvent.click(zipButton);

      const batchModeCheckbox = screen.getByLabelText(/Batch Mode - Import multiple skills/i) as HTMLInputElement;
      expect(batchModeCheckbox.disabled).toBe(true);
    });

    it('should update placeholder text based on batch mode', () => {
      render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      const urlInput = screen.getByPlaceholderText(/github.com\/anthropics\/skills\/tree\/main\/skills\/pptx/i);
      expect(urlInput).toBeDefined();

      // Enable batch mode
      const batchModeCheckbox = screen.getByLabelText(/Batch Mode - Import multiple skills/i);
      fireEvent.click(batchModeCheckbox);

      // Check for parent directory placeholder
      const parentUrlInput = screen.getByPlaceholderText(/github.com\/anthropics\/skills\/tree\/main\/skills$/i);
      expect(parentUrlInput).toBeDefined();
    });
  });

  describe('Single Skill Import', () => {
    it('should import a single skill successfully', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'Import successful',
          skill_name: 'test-skill',
          tools_created: 3,
          snippets_created: 5,
          ignored_files: [],
        }),
      });

      render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      // Enter GitHub URL
      const urlInput = screen.getByPlaceholderText(/github.com\/anthropics\/skills/i);
      fireEvent.change(urlInput, { target: { value: 'https://github.com/anthropics/skills/tree/main/skills/pptx' } });

      // Click import button
      const importButton = screen.getByRole('button', { name: /Import/i });
      fireEvent.click(importButton);

      // Wait for import to complete
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/skills/import-anthropic',
          expect.objectContaining({
            method: 'POST',
          })
        );
      });

      // Check success message
      await waitFor(() => {
        expect(screen.getByText(/Import successful/i)).toBeDefined();
        expect(screen.getByText(/test-skill/i)).toBeDefined();
      });

      expect(mockOnImportComplete).toHaveBeenCalled();
    });

    it('should handle single skill import error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Bad Request',
        text: async () => 'Invalid skill format',
      });

      render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      const urlInput = screen.getByPlaceholderText(/github.com\/anthropics\/skills/i);
      fireEvent.change(urlInput, { target: { value: 'https://github.com/invalid/url' } });

      const importButton = screen.getByRole('button', { name: /Import/i });
      fireEvent.click(importButton);

      await waitFor(() => {
        expect(screen.getByText(/Import failed/i)).toBeDefined();
      });

      expect(mockOnImportComplete).not.toHaveBeenCalled();
    });
  });

  describe('Batch Import', () => {
    it('should detect and import multiple skills successfully', async () => {
      // Mock detection response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          skill_paths: ['skill1', 'skill2', 'skill3'],
        }),
      });

      // Mock import responses for each skill
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'Import successful',
          skill_name: 'skill1',
          tools_created: 2,
          snippets_created: 3,
        }),
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'Import successful',
          skill_name: 'skill2',
          tools_created: 1,
          snippets_created: 2,
        }),
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'Import successful',
          skill_name: 'skill3',
          tools_created: 3,
          snippets_created: 4,
        }),
      });

      render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      // Enable batch mode
      const batchModeCheckbox = screen.getByLabelText(/Batch Mode - Import multiple skills/i);
      fireEvent.click(batchModeCheckbox);

      // Enter parent directory URL
      const urlInput = screen.getByPlaceholderText(/github.com\/anthropics\/skills\/tree\/main\/skills$/i);
      fireEvent.change(urlInput, { target: { value: 'https://github.com/anthropics/skills/tree/main/skills' } });

      // Click import button
      const importButton = screen.getByRole('button', { name: /Import/i });
      fireEvent.click(importButton);

      // Wait for detection call
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          '/api/skills/detect-anthropic-skills',
          expect.objectContaining({
            method: 'POST',
          })
        );
      });

      // Wait for all imports to complete
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(4); // 1 detection + 3 imports
      });

      // Check batch result summary
      await waitFor(() => {
        expect(screen.getAllByText(/Batch Import Completed/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/3 successful, 0 failed/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/Total skills detected: 3/i).length).toBeGreaterThan(0);
      });

      expect(mockOnImportComplete).toHaveBeenCalled();
    });

    it('should handle partial batch import failures', async () => {
      // Mock detection response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          skill_paths: ['skill1', 'skill2'],
        }),
      });

      // Mock successful import for skill1
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'Import successful',
          skill_name: 'skill1',
          tools_created: 2,
          snippets_created: 3,
        }),
      });

      // Mock failed import for skill2
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Internal Server Error',
        text: async () => 'Failed to parse skill',
      });

      render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      // Enable batch mode
      const batchModeCheckbox = screen.getByLabelText(/Batch Mode - Import multiple skills/i);
      fireEvent.click(batchModeCheckbox);

      // Enter parent directory URL
      const urlInput = screen.getByPlaceholderText(/github.com\/anthropics\/skills\/tree\/main\/skills$/i);
      fireEvent.change(urlInput, { target: { value: 'https://github.com/anthropics/skills/tree/main/skills' } });

      // Click import button
      const importButton = screen.getByRole('button', { name: /Import/i });
      fireEvent.click(importButton);

      // Wait for batch import to complete
      await waitFor(() => {
        expect(screen.getByText(/1 successful, 1 failed/i)).toBeDefined();
      });

      // Should still call onImportComplete if at least one succeeded
      expect(mockOnImportComplete).toHaveBeenCalled();
    });

    it('should handle detection failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Not Found',
        text: async () => 'Repository not found',
      });

      render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      // Enable batch mode
      const batchModeCheckbox = screen.getByLabelText(/Batch Mode - Import multiple skills/i);
      fireEvent.click(batchModeCheckbox);

      // Enter parent directory URL
      const urlInput = screen.getByPlaceholderText(/github.com\/anthropics\/skills\/tree\/main\/skills$/i);
      fireEvent.change(urlInput, { target: { value: 'https://github.com/invalid/repo' } });

      // Click import button
      const importButton = screen.getByRole('button', { name: /Import/i });
      fireEvent.click(importButton);

      await waitFor(() => {
        expect(screen.getAllByText(/Batch import failed/i).length).toBeGreaterThan(0);
      });

      expect(mockOnImportComplete).not.toHaveBeenCalled();
    });

    it('should handle no skills detected', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          skill_paths: [],
        }),
      });

      render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      // Enable batch mode
      const batchModeCheckbox = screen.getByLabelText(/Batch Mode - Import multiple skills/i);
      fireEvent.click(batchModeCheckbox);

      // Enter parent directory URL
      const urlInput = screen.getByPlaceholderText(/github.com\/anthropics\/skills\/tree\/main\/skills$/i);
      fireEvent.change(urlInput, { target: { value: 'https://github.com/anthropics/empty' } });

      // Click import button
      const importButton = screen.getByRole('button', { name: /Import/i });
      fireEvent.click(importButton);

      await waitFor(() => {
        expect(screen.getByText(/No skills detected/i)).toBeDefined();
      });

      expect(mockOnImportComplete).not.toHaveBeenCalled();
    });

    it('should show progress for current skill being imported', async () => {
      // Mock detection response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          skill_paths: ['skill1', 'skill2'],
        }),
      });

      // Mock import responses with delays
      mockFetch.mockImplementation(() => 
        new Promise(resolve => {
          setTimeout(() => {
            resolve({
              ok: true,
              json: async () => ({
                message: 'Import successful',
                skill_name: 'test-skill',
                tools_created: 1,
                snippets_created: 1,
              }),
            });
          }, 100);
        })
      );

      render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      // Enable batch mode
      const batchModeCheckbox = screen.getByLabelText(/Batch Mode - Import multiple skills/i);
      fireEvent.click(batchModeCheckbox);

      // Enter parent directory URL
      const urlInput = screen.getByPlaceholderText(/github.com\/anthropics\/skills\/tree\/main\/skills$/i);
      fireEvent.change(urlInput, { target: { value: 'https://github.com/anthropics/skills/tree/main/skills' } });

      // Click import button
      const importButton = screen.getByRole('button', { name: /Import/i });
      fireEvent.click(importButton);

      // Check that progress is shown
      await waitFor(() => {
        const progressElement = screen.getByText(/Importing:/i);
        expect(progressElement).toBeDefined();
      });
    });
  });

  describe('Local Folder Batch Import', () => {
    it('should support batch import from local folder', async () => {
      // Mock detection response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          skill_paths: ['skill1', 'skill2'],
        }),
      });

      // Mock import responses
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'Import successful',
          skill_name: 'skill1',
          tools_created: 1,
          snippets_created: 1,
        }),
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'Import successful',
          skill_name: 'skill2',
          tools_created: 1,
          snippets_created: 1,
        }),
      });

      render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      // Switch to local folder
      const folderButton = screen.getByText('Local Folder');
      fireEvent.click(folderButton);

      // Enable batch mode
      const batchModeCheckbox = screen.getByLabelText(/Batch Mode - Import multiple skills/i);
      fireEvent.click(batchModeCheckbox);

      // Enter folder path
      const folderInput = screen.getByPlaceholderText(/\/path\/to\/parent\/folder/i);
      fireEvent.change(folderInput, { target: { value: '/home/user/skills' } });

      // Click import button
      const importButton = screen.getByRole('button', { name: /Import/i });
      fireEvent.click(importButton);

      // Wait for batch import to complete
      await waitFor(() => {
        expect(screen.getByText(/2 successful, 0 failed/i)).toBeDefined();
      });

      expect(mockOnImportComplete).toHaveBeenCalled();
    });
  });

  describe('UI State Management', () => {
    it('should disable import button during import', async () => {
      mockFetch.mockImplementation(() => 
        new Promise(resolve => {
          setTimeout(() => {
            resolve({
              ok: true,
              json: async () => ({
                message: 'Import successful',
                skill_name: 'test-skill',
                tools_created: 1,
                snippets_created: 1,
              }),
            });
          }, 100);
        })
      );

      render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      const urlInput = screen.getByPlaceholderText(/github.com\/anthropics\/skills/i);
      fireEvent.change(urlInput, { target: { value: 'https://github.com/anthropics/skills/tree/main/skills/pptx' } });

      const importButton = screen.getByRole('button', { name: /Import/i });
      fireEvent.click(importButton);

      // Button should be disabled during import
      await waitFor(() => {
        expect(importButton).toBeDisabled();
      });
    });

    it('should reset state when modal is closed', () => {
      const { rerender } = render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      // Enter some data
      const urlInput = screen.getByPlaceholderText(/github.com\/anthropics\/skills/i);
      fireEvent.change(urlInput, { target: { value: 'https://github.com/test/repo' } });

      const batchModeCheckbox = screen.getByLabelText(/Batch Mode - Import multiple skills/i);
      fireEvent.click(batchModeCheckbox);

      // Close modal by calling onClose
      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      fireEvent.click(cancelButton);

      // Verify onClose was called
      expect(mockOnClose).toHaveBeenCalled();

      // Reopen modal with fresh render
      const { rerender: newRerender } = render(
        <AnthropicSkillImporter
          isOpen={true}
          onClose={mockOnClose}
          onImportComplete={mockOnImportComplete}
        />
      );

      // State should be reset
      const newUrlInput = screen.getByPlaceholderText(/github.com\/anthropics\/skills/i) as HTMLInputElement;
      expect(newUrlInput.value).toBe('');

      const newBatchModeCheckbox = screen.getByLabelText(/Batch Mode - Import multiple skills/i) as HTMLInputElement;
      expect(newBatchModeCheckbox.checked).toBe(false);
    });
  });
});
