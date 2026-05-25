// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect } from '@playwright/test';

/**
 * E2E tests for the Anthropic Skill Batch Import feature
 * 
 * These tests verify:
 * 1. Batch mode toggle is present and functional
 * 2. UI updates correctly when batch mode is enabled/disabled
 * 3. Batch import detects and imports multiple skills
 * 4. Progress tracking during batch import
 * 5. Summary displays correct results
 * 6. Error handling for failed imports
 * 
 * This test suite provides visual proof for reviewers through screenshots.
 */

test.describe('Anthropic Skill Batch Import', () => {
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
    await page.waitForTimeout(500); // Wait for modal animation

    // Verify batch mode checkbox is present
    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    await expect(batchModeCheckbox).toBeVisible();
    await expect(batchModeCheckbox).not.toBeChecked();

    // Capture screenshot showing the batch mode toggle
    const screenshotPath = testInfo.outputPath(`batch-mode-toggle-${browserName}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    
    console.log(`Screenshot saved: ${screenshotPath}`);
  });

  test('should toggle batch mode and update UI accordingly', async ({ page, browserName }, testInfo) => {
    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForTimeout(500);

    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    const urlInput = page.getByPlaceholder(/github\.com\/anthropics\/skills/i);

    // Capture initial state (single mode)
    await page.screenshot({ 
      path: testInfo.outputPath(`single-mode-${browserName}.png`),
      fullPage: true 
    });

    // Get initial placeholder
    const initialPlaceholder = await urlInput.getAttribute('placeholder');
    expect(initialPlaceholder).toContain('pptx'); // Single skill example

    // Enable batch mode
    await batchModeCheckbox.check();
    await page.waitForTimeout(300);

    // Verify checkbox is checked
    await expect(batchModeCheckbox).toBeChecked();

    // Verify placeholder changed to parent directory example
    const batchPlaceholder = await urlInput.getAttribute('placeholder');
    expect(batchPlaceholder).toContain('skills'); // Parent directory example
    expect(batchPlaceholder).not.toContain('pptx'); // Should not have specific skill

    // Capture batch mode enabled state
    await page.screenshot({ 
      path: testInfo.outputPath(`batch-mode-enabled-${browserName}.png`),
      fullPage: true 
    });

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
    await page.waitForTimeout(500);

    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);

    // Switch to ZIP file source
    const zipButton = page.getByRole('button', { name: /zip file/i });
    await zipButton.click();
    await page.waitForTimeout(300);

    // Verify batch mode is disabled
    await expect(batchModeCheckbox).toBeDisabled();

    // Capture screenshot showing disabled state
    await page.screenshot({ 
      path: testInfo.outputPath(`batch-mode-disabled-zip-${browserName}.png`),
      fullPage: true 
    });

    // Verify helper text mentions ZIP limitation
    const helperText = page.getByText(/batch mode is not available for zip files/i);
    await expect(helperText).toBeVisible();
  });

  test('should perform batch import with mocked backend', async ({ page, browserName }, testInfo) => {
    // Mock the detection endpoint
    await page.route('**/api/skills/detect-anthropic-skills', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          skill_paths: ['skill-one', 'skill-two', 'skill-three']
        })
      });
    });

    // Mock the import endpoint for each skill
    let importCount = 0;
    await page.route('**/api/skills/import-anthropic', async (route) => {
      importCount++;
      const skillName = `skill-${['one', 'two', 'three'][importCount - 1]}`;
      
      // Simulate processing time
      await new Promise(resolve => setTimeout(resolve, 500));
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Import successful',
          skill_name: skillName,
          tools_created: importCount,
          snippets_created: importCount * 2
        })
      });
    });

    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForTimeout(500);

    // Enable batch mode
    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    await batchModeCheckbox.check();
    await page.waitForTimeout(300);

    // Enter parent directory URL
    const urlInput = page.getByPlaceholder(/github\.com\/anthropics\/skills\/tree\/main\/skills$/i);
    await urlInput.fill('https://github.com/anthropics/skills/tree/main/skills');

    // Capture state before import
    await page.screenshot({ 
      path: testInfo.outputPath(`before-batch-import-${browserName}.png`),
      fullPage: true 
    });

    // Click import button
    const submitButton = page.getByRole('button', { name: /^import$/i });
    await submitButton.click();

    // Wait for progress indicator
    await page.waitForSelector('text=/importing:/i', { timeout: 5000 });

    // Capture progress state
    await page.screenshot({ 
      path: testInfo.outputPath(`batch-import-progress-${browserName}.png`),
      fullPage: true 
    });

    // Wait for completion (all 3 skills imported)
    await page.waitForSelector('text=/batch import completed/i', { timeout: 10000 });

    // Verify success message
    const successAlert = page.getByText(/batch import completed/i);
    await expect(successAlert).toBeVisible();

    // Verify summary shows correct counts
    await expect(page.getByText(/3 successful, 0 failed/i)).toBeVisible();
    await expect(page.getByText(/total skills detected: 3/i)).toBeVisible();

    // Verify individual skill results are shown
    await expect(page.getByText(/skill-one/i)).toBeVisible();
    await expect(page.getByText(/skill-two/i)).toBeVisible();
    await expect(page.getByText(/skill-three/i)).toBeVisible();

    // Capture final success state
    await page.screenshot({ 
      path: testInfo.outputPath(`batch-import-success-${browserName}.png`),
      fullPage: true 
    });

    // Verify import count matches expected
    expect(importCount).toBe(3);
  });

  test('should handle partial batch import failures', async ({ page, browserName }, testInfo) => {
    // Mock detection endpoint
    await page.route('**/api/skills/detect-anthropic-skills', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          skill_paths: ['skill-success', 'skill-fail']
        })
      });
    });

    // Mock import endpoint with one success and one failure
    let importCount = 0;
    await page.route('**/api/skills/import-anthropic', async (route) => {
      importCount++;
      
      if (importCount === 1) {
        // First import succeeds
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            message: 'Import successful',
            skill_name: 'skill-success',
            tools_created: 2,
            snippets_created: 3
          })
        });
      } else {
        // Second import fails
        await route.fulfill({
          status: 500,
          contentType: 'text/plain',
          body: 'Failed to parse skill manifest'
        });
      }
    });

    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForTimeout(500);

    // Enable batch mode and enter URL
    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    await batchModeCheckbox.check();
    
    const urlInput = page.getByPlaceholder(/github\.com\/anthropics\/skills\/tree\/main\/skills$/i);
    await urlInput.fill('https://github.com/anthropics/skills/tree/main/skills');

    // Start import
    const submitButton = page.getByRole('button', { name: /^import$/i });
    await submitButton.click();

    // Wait for completion
    await page.waitForSelector('text=/batch import completed/i', { timeout: 10000 });

    // Verify partial success message
    await expect(page.getByText(/1 successful, 1 failed/i)).toBeVisible();

    // Verify success indicator for first skill
    await expect(page.getByText(/✓.*skill-success/i)).toBeVisible();

    // Verify failure indicator for second skill
    await expect(page.getByText(/✗.*skill-fail/i)).toBeVisible();
    await expect(page.getByText(/failed to parse skill manifest/i)).toBeVisible();

    // Capture partial failure state
    await page.screenshot({ 
      path: testInfo.outputPath(`batch-import-partial-failure-${browserName}.png`),
      fullPage: true 
    });
  });

  test('should handle detection failure gracefully', async ({ page, browserName }, testInfo) => {
    // Mock detection endpoint to fail
    await page.route('**/api/skills/detect-anthropic-skills', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'text/plain',
        body: 'Repository not found'
      });
    });

    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForTimeout(500);

    // Enable batch mode and enter invalid URL
    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    await batchModeCheckbox.check();
    
    const urlInput = page.getByPlaceholder(/github\.com\/anthropics\/skills\/tree\/main\/skills$/i);
    await urlInput.fill('https://github.com/invalid/repository');

    // Start import
    const submitButton = page.getByRole('button', { name: /^import$/i });
    await submitButton.click();

    // Wait for error message
    await page.waitForSelector('text=/batch import failed/i', { timeout: 5000 });

    // Verify error alert is shown
    const errorAlert = page.locator('[class*="alert"][class*="danger"]');
    await expect(errorAlert).toBeVisible();

    // Verify error message mentions detection failure
    await expect(page.getByText(/repository not found/i)).toBeVisible();

    // Capture error state
    await page.screenshot({ 
      path: testInfo.outputPath(`batch-import-detection-error-${browserName}.png`),
      fullPage: true 
    });
  });

  test('should handle no skills detected scenario', async ({ page, browserName }, testInfo) => {
    // Mock detection endpoint returning empty array
    await page.route('**/api/skills/detect-anthropic-skills', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          skill_paths: []
        })
      });
    });

    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForTimeout(500);

    // Enable batch mode
    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    await batchModeCheckbox.check();
    
    const urlInput = page.getByPlaceholder(/github\.com\/anthropics\/skills\/tree\/main\/skills$/i);
    await urlInput.fill('https://github.com/anthropics/empty-repo');

    // Start import
    const submitButton = page.getByRole('button', { name: /^import$/i });
    await submitButton.click();

    // Wait for error message
    await page.waitForSelector('text=/no skills detected/i', { timeout: 5000 });

    // Verify appropriate error message
    await expect(page.getByText(/no skills detected/i)).toBeVisible();

    // Capture no skills state
    await page.screenshot({ 
      path: testInfo.outputPath(`batch-import-no-skills-${browserName}.png`),
      fullPage: true 
    });
  });

  test('should work with local folder source in batch mode', async ({ page, browserName }, testInfo) => {
    // Mock detection endpoint
    await page.route('**/api/skills/detect-anthropic-skills', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          skill_paths: ['local-skill-1', 'local-skill-2']
        })
      });
    });

    // Mock import endpoint
    let importCount = 0;
    await page.route('**/api/skills/import-anthropic', async (route) => {
      importCount++;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Import successful',
          skill_name: `local-skill-${importCount}`,
          tools_created: 1,
          snippets_created: 2
        })
      });
    });

    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForTimeout(500);

    // Switch to local folder source
    const folderButton = page.getByRole('button', { name: /local folder/i });
    await folderButton.click();
    await page.waitForTimeout(300);

    // Enable batch mode
    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    await batchModeCheckbox.check();

    // Enter folder path
    const folderInput = page.getByPlaceholder(/\/path\/to\/parent\/folder/i);
    await folderInput.fill('/home/user/anthropic-skills');

    // Capture state before import
    await page.screenshot({ 
      path: testInfo.outputPath(`local-folder-batch-before-${browserName}.png`),
      fullPage: true 
    });

    // Start import
    const submitButton = page.getByRole('button', { name: /^import$/i });
    await submitButton.click();

    // Wait for completion
    await page.waitForSelector('text=/batch import completed/i', { timeout: 10000 });

    // Verify success
    await expect(page.getByText(/2 successful, 0 failed/i)).toBeVisible();

    // Capture success state
    await page.screenshot({ 
      path: testInfo.outputPath(`local-folder-batch-success-${browserName}.png`),
      fullPage: true 
    });

    expect(importCount).toBe(2);
  });

  test('should disable import button during batch import', async ({ page, browserName }, testInfo) => {
    // Mock with delay to observe disabled state
    await page.route('**/api/skills/detect-anthropic-skills', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          skill_paths: ['skill-1']
        })
      });
    });

    await page.route('**/api/skills/import-anthropic', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Import successful',
          skill_name: 'skill-1',
          tools_created: 1,
          snippets_created: 1
        })
      });
    });

    const importButton = page.getByRole('button', { name: /import.*anthropic/i });
    
    if (await importButton.count() === 0) {
      test.skip();
      return;
    }

    await importButton.click();
    await page.waitForTimeout(500);

    // Enable batch mode and enter URL
    const batchModeCheckbox = page.getByLabel(/batch mode.*import multiple skills/i);
    await batchModeCheckbox.check();
    
    const urlInput = page.getByPlaceholder(/github\.com\/anthropics\/skills\/tree\/main\/skills$/i);
    await urlInput.fill('https://github.com/anthropics/skills/tree/main/skills');

    // Start import
    const submitButton = page.getByRole('button', { name: /^import$/i });
    await submitButton.click();

    // Verify button is disabled during import
    await page.waitForTimeout(500);
    await expect(submitButton).toBeDisabled();

    // Capture disabled state
    await page.screenshot({ 
      path: testInfo.outputPath(`import-button-disabled-${browserName}.png`),
      fullPage: true 
    });

    // Wait for completion
    await page.waitForSelector('text=/batch import completed/i', { timeout: 10000 });

    // Verify button changes to "Done"
    const doneButton = page.getByRole('button', { name: /done/i });
    await expect(doneButton).toBeVisible();
    await expect(doneButton).toBeEnabled();
  });
});
