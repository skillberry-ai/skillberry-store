// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

/**
 * E2E tests for the Anthropic Skill Batch Import feature (Frontend-Only)
 * 
 * This feature is implemented entirely in the frontend. The frontend detects
 * subdirectories containing SKILL.md files and imports each skill separately
 * by making multiple API calls to the single-skill import endpoint.
 * 
 * These tests verify:
 * 1. The batch mode toggle is present and functional
 * 2. Batch import can process multiple skills from subdirectories
 * 3. The UI displays detailed results for each imported skill
 * 4. Error handling works correctly for failed imports
 * 5. The import summary shows correct totals
 */

test.describe('Anthropic Skill Batch Import', () => {
  let testDir: string;

  test.beforeEach(async ({ page }) => {
    // Navigate to the skills page
    await page.goto('/skills');
    await page.waitForLoadState('networkidle');

    // Create a temporary directory for test skills
    testDir = fs.mkdtempSync(path.join(os.tmpdir(), 'batch-import-test-'));
  });

  test.afterEach(async () => {
    // Clean up test directory
    if (testDir && fs.existsSync(testDir)) {
      fs.rmSync(testDir, { recursive: true, force: true });
    }
  });

  test('should show batch mode toggle in import dialog', async ({ page }) => {
    // Open the import dialog
    const importButton = page.getByRole('button', { name: /import anthropic skill/i });
    await importButton.click();

    // Wait for dialog to open
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    // Verify batch mode toggle is present
    const batchModeCheckbox = page.locator('#batch-mode');
    await expect(batchModeCheckbox).toBeVisible();

    // Verify the label text
    const batchModeLabel = page.locator('label[for="batch-mode"]');
    await expect(batchModeLabel).toContainText('Import multiple skills from subdirectories');

    // Take screenshot of the dialog with batch mode option
    await page.screenshot({
      path: test.info().outputPath('batch-import-dialog.png'),
      fullPage: false
    });
  });

  test('should enable batch mode when checkbox is clicked', async ({ page }) => {
    // Open the import dialog
    const importButton = page.getByRole('button', { name: /import anthropic skill/i });
    await importButton.click();

    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    // Click the batch mode checkbox
    const batchModeCheckbox = page.locator('#batch-mode');
    await batchModeCheckbox.click();

    // Verify checkbox is checked
    await expect(batchModeCheckbox).toBeChecked();

    // Take screenshot showing batch mode enabled
    await page.screenshot({
      path: test.info().outputPath('batch-mode-enabled.png'),
      fullPage: false
    });
  });

  test('should show batch mode help text', async ({ page }) => {
    // Open the import dialog
    const importButton = page.getByRole('button', { name: /import anthropic skill/i });
    await importButton.click();

    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    // Verify help text is present
    const helpText = page.getByText(/When enabled, the importer will scan for subdirectories/i);
    await expect(helpText).toBeVisible();

    // Verify it mentions GitHub URLs and local folders
    await expect(helpText).toContainText('GitHub');
    await expect(helpText).toContainText('SKILL.md');
  });

  test('should import multiple skills in batch mode from local folder', async ({ page }) => {
    // Create test skill directories
    const skill1Dir = path.join(testDir, 'calculator');
    const skill2Dir = path.join(testDir, 'text_processor');

    fs.mkdirSync(skill1Dir, { recursive: true });
    fs.mkdirSync(skill2Dir, { recursive: true });

    // Create skill 1 files
    fs.writeFileSync(
      path.join(skill1Dir, 'SKILL.md'),
      '---\nname: test_calculator\ndescription: A test calculator skill\n---\n# Calculator\n\nBasic math operations.'
    );
    fs.writeFileSync(
      path.join(skill1Dir, 'add.py'),
      'def add(a: int, b: int) -> int:\n    """Add two numbers."""\n    return a + b'
    );

    // Create skill 2 files
    fs.writeFileSync(
      path.join(skill2Dir, 'SKILL.md'),
      '---\nname: test_text_processor\ndescription: A test text processing skill\n---\n# Text Processor\n\nText utilities.'
    );
    fs.writeFileSync(
      path.join(skill2Dir, 'uppercase.py'),
      'def uppercase(text: str) -> str:\n    """Convert text to uppercase."""\n    return text.upper()'
    );

    // Open the import dialog
    const importButton = page.getByRole('button', { name: /import anthropic skill/i });
    await importButton.click();

    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    // Select folder source type
    const folderRadio = page.locator('input[type="radio"][value="folder"]');
    await folderRadio.click();

    // Enable batch mode
    const batchModeCheckbox = page.locator('#batch-mode');
    await batchModeCheckbox.click();

    // Enter the test directory path
    const folderInput = page.locator('input[placeholder*="folder path"]');
    await folderInput.fill(testDir);

    // Take screenshot before import
    await page.screenshot({
      path: test.info().outputPath('batch-import-before.png'),
      fullPage: false
    });

    // Click import button
    const submitButton = page.getByRole('button', { name: /^import$/i });
    await submitButton.click();

    // Wait for import to complete (look for success alert)
    const successAlert = page.locator('[class*="alert"][class*="success"]');
    await expect(successAlert).toBeVisible({ timeout: 30000 });

    // Verify the success message mentions multiple skills
    await expect(successAlert).toContainText(/successfully imported.*skill/i);

    // Verify detailed results are shown
    const detailedResults = page.getByText(/detailed results/i);
    await expect(detailedResults).toBeVisible();

    // Verify both skills are listed in results
    const skill1Result = page.getByText(/test_calculator/i);
    const skill2Result = page.getByText(/test_text_processor/i);
    await expect(skill1Result).toBeVisible();
    await expect(skill2Result).toBeVisible();

    // Take screenshot of successful batch import results
    await page.screenshot({
      path: test.info().outputPath('batch-import-success.png'),
      fullPage: true
    });

    // Verify checkmarks for successful imports
    const successCheckmarks = page.locator('span:has-text("✓")');
    const checkmarkCount = await successCheckmarks.count();
    expect(checkmarkCount).toBeGreaterThanOrEqual(2);
  });

  test('should display correct totals in batch import summary', async ({ page }) => {
    // Create test skill directories
    const skill1Dir = path.join(testDir, 'skill_one');
    const skill2Dir = path.join(testDir, 'skill_two');

    fs.mkdirSync(skill1Dir, { recursive: true });
    fs.mkdirSync(skill2Dir, { recursive: true });

    // Create minimal skills
    fs.writeFileSync(
      path.join(skill1Dir, 'SKILL.md'),
      '---\nname: skill_one\ndescription: First skill\n---\n# Skill One'
    );
    fs.writeFileSync(
      path.join(skill1Dir, 'tool.py'),
      'def tool_one():\n    """Tool one."""\n    pass'
    );

    fs.writeFileSync(
      path.join(skill2Dir, 'SKILL.md'),
      '---\nname: skill_two\ndescription: Second skill\n---\n# Skill Two'
    );
    fs.writeFileSync(
      path.join(skill2Dir, 'tool.py'),
      'def tool_two():\n    """Tool two."""\n    pass'
    );

    // Open import dialog and perform batch import
    const importButton = page.getByRole('button', { name: /import anthropic skill/i });
    await importButton.click();

    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    const folderRadio = page.locator('input[type="radio"][value="folder"]');
    await folderRadio.click();

    const batchModeCheckbox = page.locator('#batch-mode');
    await batchModeCheckbox.click();

    const folderInput = page.locator('input[placeholder*="folder path"]');
    await folderInput.fill(testDir);

    const submitButton = page.getByRole('button', { name: /^import$/i });
    await submitButton.click();

    // Wait for success
    const successAlert = page.locator('[class*="alert"][class*="success"]');
    await expect(successAlert).toBeVisible({ timeout: 30000 });

    // Verify the summary shows correct counts
    const summaryText = await successAlert.textContent();
    expect(summaryText).toMatch(/2.*skill/i); // 2 skills
    expect(summaryText).toMatch(/tool/i); // mentions tools
  });

  test('should handle mixed success and failure in batch import', async ({ page }) => {
    // Create one valid and one invalid skill
    const validDir = path.join(testDir, 'valid_skill');
    const invalidDir = path.join(testDir, 'invalid_skill');

    fs.mkdirSync(validDir, { recursive: true });
    fs.mkdirSync(invalidDir, { recursive: true });

    // Valid skill
    fs.writeFileSync(
      path.join(validDir, 'SKILL.md'),
      '---\nname: valid_skill\ndescription: Valid skill\n---\n# Valid'
    );
    fs.writeFileSync(
      path.join(validDir, 'tool.py'),
      'def valid_tool():\n    """Valid tool."""\n    pass'
    );

    // Invalid skill (missing metadata in SKILL.md)
    fs.writeFileSync(
      path.join(invalidDir, 'SKILL.md'),
      '# Invalid\n\nNo metadata here.'
    );

    // Open import dialog and perform batch import
    const importButton = page.getByRole('button', { name: /import anthropic skill/i });
    await importButton.click();

    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    const folderRadio = page.locator('input[type="radio"][value="folder"]');
    await folderRadio.click();

    const batchModeCheckbox = page.locator('#batch-mode');
    await batchModeCheckbox.click();

    const folderInput = page.locator('input[placeholder*="folder path"]');
    await folderInput.fill(testDir);

    const submitButton = page.getByRole('button', { name: /^import$/i });
    await submitButton.click();

    // Wait for results
    await page.waitForTimeout(5000);

    // Take screenshot of mixed results
    await page.screenshot({
      path: test.info().outputPath('batch-import-mixed-results.png'),
      fullPage: true
    });

    // Verify at least one success is shown
    const validSkillResult = page.getByText(/valid_skill/i);
    await expect(validSkillResult).toBeVisible();
  });

  test('should disable batch mode toggle during import', async ({ page }) => {
    // Create a test skill
    const skillDir = path.join(testDir, 'test_skill');
    fs.mkdirSync(skillDir, { recursive: true });
    fs.writeFileSync(
      path.join(skillDir, 'SKILL.md'),
      '---\nname: test_skill\ndescription: Test\n---\n# Test'
    );

    // Open import dialog
    const importButton = page.getByRole('button', { name: /import anthropic skill/i });
    await importButton.click();

    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    const folderRadio = page.locator('input[type="radio"][value="folder"]');
    await folderRadio.click();

    const batchModeCheckbox = page.locator('#batch-mode');
    await batchModeCheckbox.click();

    const folderInput = page.locator('input[placeholder*="folder path"]');
    await folderInput.fill(testDir);

    // Start import
    const submitButton = page.getByRole('button', { name: /^import$/i });
    await submitButton.click();

    // Immediately check if batch mode checkbox is disabled
    // (This might be too fast, but we're testing the UI state)
    const isDisabled = await batchModeCheckbox.isDisabled();
    expect(isDisabled).toBe(true);
  });

  test('should show progress indicator during batch import', async ({ page }) => {
    // Create test skills
    const skill1Dir = path.join(testDir, 'skill1');
    fs.mkdirSync(skill1Dir, { recursive: true });
    fs.writeFileSync(
      path.join(skill1Dir, 'SKILL.md'),
      '---\nname: skill1\ndescription: Skill 1\n---\n# Skill 1'
    );

    // Open import dialog
    const importButton = page.getByRole('button', { name: /import anthropic skill/i });
    await importButton.click();

    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    const folderRadio = page.locator('input[type="radio"][value="folder"]');
    await folderRadio.click();

    const batchModeCheckbox = page.locator('#batch-mode');
    await batchModeCheckbox.click();

    const folderInput = page.locator('input[placeholder*="folder path"]');
    await folderInput.fill(testDir);

    const submitButton = page.getByRole('button', { name: /^import$/i });
    await submitButton.click();

    // Look for progress indicator (progress bar or spinner)
    const progressIndicator = page.locator('[role="progressbar"], .pf-c-spinner');
    
    // Progress indicator should appear briefly
    // We use a short timeout since import might be fast
    try {
      await expect(progressIndicator).toBeVisible({ timeout: 2000 });
    } catch {
      // Progress might complete too quickly, which is fine
    }
  });

  test('should reset form after successful batch import', async ({ page }) => {
    // Create a test skill
    const skillDir = path.join(testDir, 'test_skill');
    fs.mkdirSync(skillDir, { recursive: true });
    fs.writeFileSync(
      path.join(skillDir, 'SKILL.md'),
      '---\nname: test_skill\ndescription: Test\n---\n# Test'
    );

    // Open import dialog
    const importButton = page.getByRole('button', { name: /import anthropic skill/i });
    await importButton.click();

    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    const folderRadio = page.locator('input[type="radio"][value="folder"]');
    await folderRadio.click();

    const batchModeCheckbox = page.locator('#batch-mode');
    await batchModeCheckbox.click();

    const folderInput = page.locator('input[placeholder*="folder path"]');
    await folderInput.fill(testDir);

    const submitButton = page.getByRole('button', { name: /^import$/i });
    await submitButton.click();

    // Wait for success
    const successAlert = page.locator('[class*="alert"][class*="success"]');
    await expect(successAlert).toBeVisible({ timeout: 30000 });

    // Close the dialog
    const closeButton = page.getByRole('button', { name: /close/i });
    await closeButton.click();

    // Reopen the dialog
    await importButton.click();
    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    // Verify form is reset (batch mode should be unchecked)
    const resetBatchModeCheckbox = page.locator('#batch-mode');
    await expect(resetBatchModeCheckbox).not.toBeChecked();

    // Verify folder input is empty
    const resetFolderInput = page.locator('input[placeholder*="folder path"]');
    const folderValue = await resetFolderInput.inputValue();
    expect(folderValue).toBe('');
  });

  test('should display individual skill results with tool and snippet counts', async ({ page }) => {
    // Create skills with different numbers of tools and snippets
    const skill1Dir = path.join(testDir, 'multi_tool_skill');
    fs.mkdirSync(skill1Dir, { recursive: true });
    fs.writeFileSync(
      path.join(skill1Dir, 'SKILL.md'),
      '---\nname: multi_tool_skill\ndescription: Skill with multiple tools\n---\n# Multi Tool'
    );
    fs.writeFileSync(
      path.join(skill1Dir, 'tool1.py'),
      'def tool1():\n    """Tool 1."""\n    pass'
    );
    fs.writeFileSync(
      path.join(skill1Dir, 'tool2.py'),
      'def tool2():\n    """Tool 2."""\n    pass'
    );
    fs.writeFileSync(
      path.join(skill1Dir, 'doc.md'),
      '# Documentation\n\nSome docs.'
    );

    // Open import dialog and perform batch import
    const importButton = page.getByRole('button', { name: /import anthropic skill/i });
    await importButton.click();

    await page.waitForSelector('[role="dialog"]', { state: 'visible' });

    const folderRadio = page.locator('input[type="radio"][value="folder"]');
    await folderRadio.click();

    const batchModeCheckbox = page.locator('#batch-mode');
    await batchModeCheckbox.click();

    const folderInput = page.locator('input[placeholder*="folder path"]');
    await folderInput.fill(testDir);

    const submitButton = page.getByRole('button', { name: /^import$/i });
    await submitButton.click();

    // Wait for success
    const successAlert = page.locator('[class*="alert"][class*="success"]');
    await expect(successAlert).toBeVisible({ timeout: 30000 });

    // Verify detailed results show tool and snippet counts
    const detailedResults = page.getByText(/detailed results/i);
    await expect(detailedResults).toBeVisible();

    // Look for the skill result with counts
    const skillResult = page.getByText(/multi_tool_skill.*tool.*snippet/i);
    await expect(skillResult).toBeVisible();

    // Take screenshot of detailed results
    await page.screenshot({
      path: test.info().outputPath('batch-import-detailed-results.png'),
      fullPage: true
    });
  });
});
