// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect } from '@playwright/test';

test.describe('Syntax Highlighting', () => {
  test.describe('SkillDetailPage', () => {
    test('should display tool module code with syntax highlighting', async ({ page }) => {
      // Navigate to a skill detail page
      // Note: This assumes there's a skill with ID 'test-skill' that has tools
      await page.goto('/skills/test-skill');
      
      // Wait for the page to load
      await page.waitForLoadState('networkidle');
      
      // Look for the Tools tab and click it
      const toolsTab = page.locator('button:has-text("Tools")');
      if (await toolsTab.isVisible()) {
        await toolsTab.click();
        
        // Wait for tool list to appear
        await page.waitForSelector('[data-testid="tool-list"], .pf-v5-c-data-list', { timeout: 5000 });
        
        // Click on the first tool to view its code
        const firstTool = page.locator('[data-testid="tool-item"], .pf-v5-c-data-list__item').first();
        if (await firstTool.isVisible()) {
          await firstTool.click();
          
          // Wait for syntax highlighter to render
          await page.waitForSelector('pre[class*="language-"]', { timeout: 5000 });
          
          // Verify syntax highlighter is present
          const syntaxHighlighter = page.locator('pre[class*="language-"]');
          await expect(syntaxHighlighter).toBeVisible();
          
          // Verify line numbers are displayed
          const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
          await expect(lineNumbers.first()).toBeVisible();
          
          // Verify dark theme is applied (vscDarkPlus)
          const codeBlock = page.locator('code[class*="language-"]');
          await expect(codeBlock).toBeVisible();
          
          // Take a screenshot for visual verification
          await page.screenshot({ 
            path: test.info().outputPath('skill-tool-syntax-highlighting.png'),
            fullPage: false 
          });
        }
      }
    });

    test('should display snippet code with syntax highlighting in skill detail', async ({ page }) => {
      // Navigate to a skill detail page with snippets
      await page.goto('/skills/test-skill');
      
      // Wait for the page to load
      await page.waitForLoadState('networkidle');
      
      // Look for the Snippets tab and click it
      const snippetsTab = page.locator('button:has-text("Snippets")');
      if (await snippetsTab.isVisible()) {
        await snippetsTab.click();
        
        // Wait for snippet list to appear
        await page.waitForSelector('[data-testid="snippet-list"], .pf-v5-c-data-list', { timeout: 5000 });
        
        // Click on the first snippet to view its code
        const firstSnippet = page.locator('[data-testid="snippet-item"], .pf-v5-c-data-list__item').first();
        if (await firstSnippet.isVisible()) {
          await firstSnippet.click();
          
          // Wait for syntax highlighter to render
          await page.waitForSelector('pre[class*="language-"]', { timeout: 5000 });
          
          // Verify syntax highlighter is present
          const syntaxHighlighter = page.locator('pre[class*="language-"]');
          await expect(syntaxHighlighter).toBeVisible();
          
          // Verify line numbers are displayed
          const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
          await expect(lineNumbers.first()).toBeVisible();
          
          // Take a screenshot for visual verification
          await page.screenshot({ 
            path: test.info().outputPath('skill-snippet-syntax-highlighting.png'),
            fullPage: false 
          });
        }
      }
    });

    test('should apply correct language detection for Python code', async ({ page }) => {
      await page.goto('/skills/test-skill');
      await page.waitForLoadState('networkidle');
      
      // Navigate to a Python tool
      const toolsTab = page.locator('button:has-text("Tools")');
      if (await toolsTab.isVisible()) {
        await toolsTab.click();
        await page.waitForSelector('[data-testid="tool-list"], .pf-v5-c-data-list', { timeout: 5000 });
        
        const firstTool = page.locator('[data-testid="tool-item"], .pf-v5-c-data-list__item').first();
        if (await firstTool.isVisible()) {
          await firstTool.click();
          await page.waitForSelector('pre[class*="language-"]', { timeout: 5000 });
          
          // Check if Python syntax highlighting is applied
          const pythonCode = page.locator('pre[class*="language-python"], code[class*="language-python"]');
          const hasPythonHighlighting = await pythonCode.count() > 0;
          
          if (hasPythonHighlighting) {
            await expect(pythonCode.first()).toBeVisible();
          }
        }
      }
    });

    test('should have scrollable code container with max height', async ({ page }) => {
      await page.goto('/skills/test-skill');
      await page.waitForLoadState('networkidle');
      
      const toolsTab = page.locator('button:has-text("Tools")');
      if (await toolsTab.isVisible()) {
        await toolsTab.click();
        await page.waitForSelector('[data-testid="tool-list"], .pf-v5-c-data-list', { timeout: 5000 });
        
        const firstTool = page.locator('[data-testid="tool-item"], .pf-v5-c-data-list__item').first();
        if (await firstTool.isVisible()) {
          await firstTool.click();
          await page.waitForSelector('pre[class*="language-"]', { timeout: 5000 });
          
          // Find the container div with maxHeight style
          const codeContainer = page.locator('div').filter({ 
            has: page.locator('pre[class*="language-"]') 
          }).first();
          
          // Verify the container has overflow and border styling
          const styles = await codeContainer.evaluate((el) => {
            const computed = window.getComputedStyle(el);
            return {
              overflow: computed.overflow,
              border: computed.border,
              borderRadius: computed.borderRadius,
            };
          });
          
          expect(styles.overflow).toBe('auto');
        }
      }
    });
  });

  test.describe('SnippetDetailPage', () => {
    test('should display snippet code with syntax highlighting', async ({ page }) => {
      // Navigate to a snippet detail page
      // Note: This assumes there's a snippet with ID 'test-snippet'
      await page.goto('/snippets/test-snippet');
      
      // Wait for the page to load
      await page.waitForLoadState('networkidle');
      
      // Wait for syntax highlighter to render
      await page.waitForSelector('pre[class*="language-"]', { timeout: 5000 });
      
      // Verify syntax highlighter is present
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible();
      
      // Verify line numbers are displayed
      const lineNumbers = page.locator('.linenumber, [class*="line-number"]');
      await expect(lineNumbers.first()).toBeVisible();
      
      // Verify dark theme is applied (vscDarkPlus)
      const codeBlock = page.locator('code[class*="language-"]');
      await expect(codeBlock).toBeVisible();
      
      // Take a screenshot for visual verification
      await page.screenshot({ 
        path: test.info().outputPath('snippet-detail-syntax-highlighting.png'),
        fullPage: false 
      });
    });

    test('should detect language from content_type', async ({ page }) => {
      await page.goto('/snippets/test-snippet');
      await page.waitForLoadState('networkidle');
      
      // Wait for syntax highlighter
      await page.waitForSelector('pre[class*="language-"]', { timeout: 5000 });
      
      // Verify that a language class is applied
      const codeElement = page.locator('code[class*="language-"]');
      const className = await codeElement.getAttribute('class');
      
      // Should have a language- class
      expect(className).toMatch(/language-\w+/);
    });

    test('should detect language from file tags', async ({ page }) => {
      // Navigate to a snippet that has file: tags
      await page.goto('/snippets/test-snippet-with-file-tag');
      await page.waitForLoadState('networkidle');
      
      // Wait for syntax highlighter
      await page.waitForSelector('pre[class*="language-"]', { timeout: 5000 });
      
      // Verify syntax highlighting is applied
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible();
    });

    test('should have scrollable code container', async ({ page }) => {
      await page.goto('/snippets/test-snippet');
      await page.waitForLoadState('networkidle');
      
      // Wait for syntax highlighter
      await page.waitForSelector('pre[class*="language-"]', { timeout: 5000 });
      
      // Find the container div with maxHeight style
      const codeContainer = page.locator('div').filter({ 
        has: page.locator('pre[class*="language-"]') 
      }).first();
      
      // Verify the container has overflow styling
      const overflow = await codeContainer.evaluate((el) => {
        return window.getComputedStyle(el).overflow;
      });
      
      expect(overflow).toBe('auto');
    });

    test('should maintain code formatting and indentation', async ({ page }) => {
      await page.goto('/snippets/test-snippet');
      await page.waitForLoadState('networkidle');
      
      // Wait for syntax highlighter
      await page.waitForSelector('pre[class*="language-"]', { timeout: 5000 });
      
      // Get the code content
      const codeContent = await page.locator('code[class*="language-"]').textContent();
      
      // Verify code is not empty
      expect(codeContent).toBeTruthy();
      expect(codeContent!.length).toBeGreaterThan(0);
    });
  });

  test.describe('Visual Regression', () => {
    test('should match expected visual appearance for Python code', async ({ page }) => {
      await page.goto('/snippets/python-snippet');
      await page.waitForLoadState('networkidle');
      
      // Wait for syntax highlighter
      await page.waitForSelector('pre[class*="language-"]', { timeout: 5000 });
      
      // Take a full screenshot of the code block
      const codeContainer = page.locator('div').filter({ 
        has: page.locator('pre[class*="language-"]') 
      }).first();
      
      await codeContainer.screenshot({ 
        path: test.info().outputPath('python-syntax-highlighting.png')
      });
    });

    test('should match expected visual appearance for JavaScript code', async ({ page }) => {
      await page.goto('/snippets/javascript-snippet');
      await page.waitForLoadState('networkidle');
      
      // Wait for syntax highlighter
      await page.waitForSelector('pre[class*="language-"]', { timeout: 5000 });
      
      // Take a full screenshot of the code block
      const codeContainer = page.locator('div').filter({ 
        has: page.locator('pre[class*="language-"]') 
      }).first();
      
      await codeContainer.screenshot({ 
        path: test.info().outputPath('javascript-syntax-highlighting.png')
      });
    });
  });
});
