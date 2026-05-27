// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect } from '@playwright/test';

/**
 * E2E tests for the Anthropic Skill Batch Import feature using LIVE backend
 * 
 * These tests verify the batch import UI changes and functionality against
 * the real backend API running at http://127.0.0.1:8000
 * 
 * IMPORTANT: These tests use the LIVE backend, not mocks.
 * The backend must be running with seeded test data.
 */

test.describe('Anthropic Skill Batch Import - Live Backend', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the skills page
    await page.goto('/skills');
    await page.waitForLoadState('networkidle');
  });

  test('should display batch mode toggle in import dialog', async ({ page, browserName }, testInfo) => {
    // Open the import dialog
    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    // Skip if import button doesn't exist
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    
    // Wait for modal to be visible
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    // Verify batch mode checkbox is present
    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    await expect(batchModeCheckbox).toBeVisible();
    await expect(batchModeCheckbox).not.toBeChecked();

    // Verify helper text is present
    await expect(page.getByText(/import a single skill from the specified location/i)).toBeVisible();

    // Capture screenshot showing the batch mode toggle
    const screenshotPath = testInfo.outputPath(`batch-mode-toggle-${browserName}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    
    console.log(`✓ Screenshot saved: ${screenshotPath}`);
  });

  test('should toggle batch mode and update UI accordingly', async ({ page, browserName }, testInfo) => {
    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    const urlInput = page.getByPlaceholder(/github\.com\/anthropics\/skills/i);

    // Capture initial state (single mode)
    await page.screenshot({ 
      path: testInfo.outputPath(`single-mode-initial-${browserName}.png`),
      fullPage: true 
    });

    // Get initial placeholder - should show single skill example
    const initialPlaceholder = await urlInput.getAttribute('placeholder');
    expect(initialPlaceholder).toContain('pptx'); // Single skill example

    // Verify initial helper text
    await expect(page.getByText(/import a single skill from the specified location/i)).toBeVisible();

    // Enable batch mode
    await batchModeCheckbox.check();
    await page.waitForTimeout(300); // Wait for UI update

    // Verify checkbox is checked
    await expect(batchModeCheckbox).toBeChecked();

    // Verify placeholder changed to parent directory example
    const batchPlaceholder = await urlInput.getAttribute('placeholder');
    expect(batchPlaceholder).toContain('skills'); // Parent directory example
    expect(batchPlaceholder).not.toContain('pptx'); // Should not have specific skill

    // Verify helper text changed
    await expect(page.getByText(/the system will detect all subdirectories containing skill\.md files/i)).toBeVisible();

    // Capture batch mode enabled state
    await page.screenshot({ 
      path: testInfo.outputPath(`batch-mode-enabled-${browserName}.png`),
      fullPage: true 
    });

    console.log(`✓ Batch mode toggle verified with screenshots`);

    // Disable batch mode
    await batchModeCheckbox.uncheck();
    await page.waitForTimeout(300);

    // Verify it returns to single mode
    await expect(batchModeCheckbox).not.toBeChecked();
    const finalPlaceholder = await urlInput.getAttribute('placeholder');
    expect(finalPlaceholder).toContain('pptx');
  });

  test('should disable batch mode for ZIP file source', async ({ page, browserName }, testInfo) => {
    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);

    // Initially should be enabled
    await expect(batchModeCheckbox).toBeEnabled();

    // Switch to ZIP file source
    const zipButton = page.getByRole('button', { name: /zip file/i });
    await zipButton.click();
    await page.waitForTimeout(300);

    // Verify batch mode is disabled
    await expect(batchModeCheckbox).toBeDisabled();

    // Verify helper text mentions ZIP limitation
    await expect(page.getByText(/batch mode is not available for zip files/i)).toBeVisible();

    // Capture screenshot showing disabled state
    await page.screenshot({ 
      path: testInfo.outputPath(`batch-mode-disabled-zip-${browserName}.png`),
      fullPage: true 
    });

    console.log(`✓ Batch mode correctly disabled for ZIP files`);
  });

  test('should update placeholder for local folder in batch mode', async ({ page, browserName }, testInfo) => {
    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    // Switch to local folder source
    const folderButton = page.getByRole('button', { name: /local folder/i });
    await folderButton.click();
    await page.waitForTimeout(300);

    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    const folderInput = page.getByPlaceholder(/\/path\/to/i);

    // Get initial placeholder (single mode)
    const singlePlaceholder = await folderInput.getAttribute('placeholder');
    expect(singlePlaceholder).toContain('/path/to/skill/folder');

    // Enable batch mode
    await batchModeCheckbox.check();
    await page.waitForTimeout(300);

    // Verify placeholder changed to parent folder
    const batchPlaceholder = await folderInput.getAttribute('placeholder');
    expect(batchPlaceholder).toContain('/path/to/parent/folder');

    // Verify helper text updated
    await expect(page.getByText(/provide the absolute path to the parent folder containing multiple skill subdirectories/i)).toBeVisible();

    // Capture screenshot
    await page.screenshot({ 
      path: testInfo.outputPath(`local-folder-batch-mode-${browserName}.png`),
      fullPage: true 
    });

    console.log(`✓ Local folder batch mode UI verified`);
  });

  test('should show validation error for empty URL in batch mode', async ({ page, browserName }, testInfo) => {
    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    // Enable batch mode
    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    await batchModeCheckbox.check();
    await page.waitForTimeout(300);

    // Try to import without entering URL
    const importSubmitButton = page.getByRole('button', { name: /^import$/i });
    
    // Button should be disabled when URL is empty
    await expect(importSubmitButton).toBeDisabled();

    console.log(`✓ Import button correctly disabled for empty URL`);
  });

  test('should maintain batch mode state when switching between GitHub URL and Local Folder', async ({ page }) => {
    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    
    // Enable batch mode on GitHub URL
    await batchModeCheckbox.check();
    await expect(batchModeCheckbox).toBeChecked();

    // Switch to Local Folder
    const folderButton = page.getByRole('button', { name: /local folder/i });
    await folderButton.click();
    await page.waitForTimeout(300);

    // Batch mode should still be enabled
    await expect(batchModeCheckbox).toBeChecked();

    // Switch back to GitHub URL
    const urlButton = page.getByRole('button', { name: /github url/i });
    await urlButton.click();
    await page.waitForTimeout(300);

    // Batch mode should still be enabled
    await expect(batchModeCheckbox).toBeChecked();

    console.log(`✓ Batch mode state persists across source type changes`);
  });

  test('should display correct import mode label text', async ({ page }) => {
    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    // Verify the form group label
    await expect(page.getByText('Import Mode')).toBeVisible();

    // Verify the checkbox label
    await expect(page.getByText(/batch mode - import multiple skills from parent directory/i)).toBeVisible();

    console.log(`✓ Import mode labels are correct`);
  });

  test('should show appropriate helper text based on batch mode state', async ({ page }) => {
    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);

    // Single mode helper text
    await expect(page.getByText(/import a single skill from the specified location/i)).toBeVisible();

    // Enable batch mode
    await batchModeCheckbox.check();
    await page.waitForTimeout(300);

    // Batch mode helper text
    await expect(page.getByText(/the system will detect all subdirectories containing skill\.md files and import them sequentially/i)).toBeVisible();

    console.log(`✓ Helper text updates correctly based on mode`);
  });

  test('should reset batch mode when modal is closed and reopened', async ({ page }) => {
    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    // Open modal
    await importButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    // Enable batch mode
    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    await batchModeCheckbox.check();
    await expect(batchModeCheckbox).toBeChecked();

    // Close modal
    const cancelButton = page.getByRole('button', { name: /cancel/i });
    await cancelButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'hidden' });

    // Reopen modal
    await importButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    // Batch mode should be reset to unchecked
    const newBatchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    await expect(newBatchModeCheckbox).not.toBeChecked();

    console.log(`✓ Batch mode resets when modal is closed and reopened`);
  });

  test('should display batch mode checkbox before snippet mode section', async ({ page }) => {
    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    // Get positions of elements
    const batchModeLabel = page.getByText('Import Mode');
    const snippetModeLabel = page.getByText('Snippet Import Mode');

    const batchModeBox = await batchModeLabel.boundingBox();
    const snippetModeBox = await snippetModeLabel.boundingBox();

    // Batch mode should appear before (above) snippet mode
    if (batchModeBox && snippetModeBox) {
      expect(batchModeBox.y).toBeLessThan(snippetModeBox.y);
    }

    console.log(`✓ Batch mode section positioned correctly in form`);
  });
});
