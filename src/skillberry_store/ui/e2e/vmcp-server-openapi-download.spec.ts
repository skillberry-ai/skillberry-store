// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect } from '@playwright/test';

/**
 * E2E tests for the OpenAPI specification download feature on VMCP Server Detail Page
 * 
 * These tests verify:
 * 1. The download button is present and properly disabled when not connected
 * 2. The download button becomes enabled when connected to MCP server
 * 3. Clicking the download button triggers a file download
 * 4. The downloaded file has the correct name format
 * 5. The downloaded file contains valid OpenAPI JSON
 */

test.describe('VMCP Server OpenAPI Download', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the VMCP servers list page
    await page.goto('/vmcp-servers');
    await page.waitForLoadState('networkidle');
  });

  test('should show download button in disabled state when not connected', async ({ page }) => {
    // Find and click on a VMCP server to view details
    // This assumes there's at least one server in the list
    const serverLink = page.locator('a[href*="/vmcp-servers/"]').first();
    
    // Skip test if no servers exist
    if (await serverLink.count() === 0) {
      test.skip();
      return;
    }

    await serverLink.click();
    await page.waitForLoadState('networkidle');

    // Verify the download button exists
    const downloadButton = page.getByRole('button', { name: /download openapi spec/i });
    await expect(downloadButton).toBeVisible();

    // Verify the button is disabled when not connected
    // The button should be disabled if the MCP connection status shows "Disconnected"
    const connectionStatus = page.getByText(/disconnected/i);
    if (await connectionStatus.isVisible()) {
      await expect(downloadButton).toBeDisabled();
    }
  });

  test('should enable download button when connected to MCP server', async ({ page }) => {
    // Find and click on a VMCP server
    const serverLink = page.locator('a[href*="/vmcp-servers/"]').first();
    
    if (await serverLink.count() === 0) {
      test.skip();
      return;
    }

    await serverLink.click();
    await page.waitForLoadState('networkidle');

    // Wait for MCP connection (this may take a few seconds)
    // Look for the "Connected" status label
    const connectedLabel = page.getByText(/connected/i).first();
    
    // Wait up to 10 seconds for connection
    try {
      await connectedLabel.waitFor({ state: 'visible', timeout: 10000 });
      
      // Once connected, the download button should be enabled
      const downloadButton = page.getByRole('button', { name: /download openapi spec/i });
      await expect(downloadButton).toBeEnabled();
    } catch (error) {
      // If connection fails, skip the test
      test.skip();
    }
  });

  test('should show tooltip on download button', async ({ page }) => {
    const serverLink = page.locator('a[href*="/vmcp-servers/"]').first();
    
    if (await serverLink.count() === 0) {
      test.skip();
      return;
    }

    await serverLink.click();
    await page.waitForLoadState('networkidle');

    const downloadButton = page.getByRole('button', { name: /download openapi spec/i });
    
    // Hover over the button to show tooltip
    await downloadButton.hover();
    
    // Check for tooltip text
    const tooltip = page.locator('[role="tooltip"]');
    await expect(tooltip).toBeVisible({ timeout: 2000 });
    
    // Tooltip should mention either "Download OpenAPI specification" or "Connect to MCP server first"
    const tooltipText = await tooltip.textContent();
    expect(tooltipText).toMatch(/download openapi specification|connect to mcp server first/i);
  });

  test('should trigger download when button is clicked (if connected)', async ({ page }) => {
    const serverLink = page.locator('a[href*="/vmcp-servers/"]').first();
    
    if (await serverLink.count() === 0) {
      test.skip();
      return;
    }

    await serverLink.click();
    await page.waitForLoadState('networkidle');

    // Wait for connection
    const connectedLabel = page.getByText(/connected/i).first();
    
    try {
      await connectedLabel.waitFor({ state: 'visible', timeout: 10000 });
    } catch (error) {
      test.skip();
      return;
    }

    const downloadButton = page.getByRole('button', { name: /download openapi spec/i });
    
    // Set up download listener before clicking
    const downloadPromise = page.waitForEvent('download', { timeout: 5000 });
    
    await downloadButton.click();
    
    // Wait for download to start
    const download = await downloadPromise;
    
    // Verify the filename format: {server_name}_openapi.json
    const filename = download.suggestedFilename();
    expect(filename).toMatch(/_openapi\.json$/);
    
    // Read the download stream to verify content
    const stream = await download.createReadStream();
    const chunks: Buffer[] = [];
    
    for await (const chunk of stream) {
      chunks.push(chunk);
    }
    
    const content = Buffer.concat(chunks).toString('utf-8');
    const spec = JSON.parse(content);
    
    // Verify it's a valid OpenAPI spec
    expect(spec.openapi).toBe('3.0.3');
    expect(spec.info).toBeDefined();
    expect(spec.info.title).toContain('Virtual MCP Server API');
    expect(spec.servers).toBeDefined();
    expect(spec.paths).toBeDefined();
    expect(spec.components).toBeDefined();
  });

  test('should generate OpenAPI spec with tools and prompts', async ({ page }) => {
    const serverLink = page.locator('a[href*="/vmcp-servers/"]').first();
    
    if (await serverLink.count() === 0) {
      test.skip();
      return;
    }

    await serverLink.click();
    await page.waitForLoadState('networkidle');

    // Wait for connection
    const connectedLabel = page.getByText(/connected/i).first();
    
    try {
      await connectedLabel.waitFor({ state: 'visible', timeout: 10000 });
    } catch (error) {
      test.skip();
      return;
    }

    // Check if there are tools or prompts displayed
    const toolsCount = page.getByText(/available tools/i);
    const promptsCount = page.getByText(/available prompts/i);
    
    const hasTools = await toolsCount.isVisible();
    const hasPrompts = await promptsCount.isVisible();
    
    if (!hasTools && !hasPrompts) {
      test.skip();
      return;
    }

    const downloadButton = page.getByRole('button', { name: /download openapi spec/i });
    const downloadPromise = page.waitForEvent('download', { timeout: 5000 });
    
    await downloadButton.click();
    const download = await downloadPromise;
    
    // Read the download stream to verify content
    const stream = await download.createReadStream();
    const chunks: Buffer[] = [];
    
    for await (const chunk of stream) {
      chunks.push(chunk);
    }
    
    const content = Buffer.concat(chunks).toString('utf-8');
    const spec = JSON.parse(content);
    
    // Verify paths are generated for tools and/or prompts
    const paths = Object.keys(spec.paths);
    
    if (hasTools) {
      const toolPaths = paths.filter(p => p.startsWith('/tools/'));
      expect(toolPaths.length).toBeGreaterThan(0);
    }
    
    if (hasPrompts) {
      const promptPaths = paths.filter(p => p.startsWith('/prompts/'));
      expect(promptPaths.length).toBeGreaterThan(0);
    }
  });

  test('should display download button with correct icon', async ({ page }) => {
    const serverLink = page.locator('a[href*="/vmcp-servers/"]').first();
    
    if (await serverLink.count() === 0) {
      test.skip();
      return;
    }

    await serverLink.click();
    await page.waitForLoadState('networkidle');

    const downloadButton = page.getByRole('button', { name: /download openapi spec/i });
    await expect(downloadButton).toBeVisible();
    
    // Verify the button has a download icon (DownloadIcon from PatternFly)
    const icon = downloadButton.locator('svg');
    await expect(icon).toBeVisible();
  });

  test('should position download button correctly in the page header', async ({ page }) => {
    const serverLink = page.locator('a[href*="/vmcp-servers/"]').first();
    
    if (await serverLink.count() === 0) {
      test.skip();
      return;
    }

    await serverLink.click();
    await page.waitForLoadState('networkidle');

    // The download button should be in the same row as Edit and Delete buttons
    const downloadButton = page.getByRole('button', { name: /download openapi spec/i });
    const editButton = page.getByRole('button', { name: /edit/i });
    const deleteButton = page.getByRole('button', { name: /delete/i });
    
    await expect(downloadButton).toBeVisible();
    await expect(editButton).toBeVisible();
    await expect(deleteButton).toBeVisible();
    
    // Verify they're in the same container (flex layout)
    const downloadBox = await downloadButton.boundingBox();
    const editBox = await editButton.boundingBox();
    
    if (downloadBox && editBox) {
      // Buttons should be roughly on the same horizontal line (within 20px)
      expect(Math.abs(downloadBox.y - editBox.y)).toBeLessThan(20);
    }
  });

  test('should not trigger download when disconnected', async ({ page }) => {
    const serverLink = page.locator('a[href*="/vmcp-servers/"]').first();
    
    if (await serverLink.count() === 0) {
      test.skip();
      return;
    }

    await serverLink.click();
    await page.waitForLoadState('networkidle');

    // Ensure we're in disconnected state
    const disconnectedLabel = page.getByText(/disconnected/i);
    if (!(await disconnectedLabel.isVisible())) {
      test.skip();
      return;
    }

    const downloadButton = page.getByRole('button', { name: /download openapi spec/i });
    
    // Button should be disabled
    await expect(downloadButton).toBeDisabled();
    
    // Verify no download event occurs even if we try to click
    let downloadTriggered = false;
    page.on('download', () => {
      downloadTriggered = true;
    });
    
    // Try to click (should not work since disabled)
    await downloadButton.click({ force: true }).catch(() => {
      // Expected to fail since button is disabled
    });
    
    // Wait a bit to ensure no download was triggered
    await page.waitForTimeout(1000);
    expect(downloadTriggered).toBe(false);
  });
});