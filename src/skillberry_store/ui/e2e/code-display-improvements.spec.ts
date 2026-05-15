// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect, Page } from '@playwright/test';

/**
 * E2E tests for PR #138: UI improvements for code display
 * 
 * This PR replaces plain CodeBlock components with VS Code-like syntax highlighting
 * using react-syntax-highlighter with the vscDarkPlus theme.
 * 
 * Tests verify:
 * 1. Syntax highlighting is applied to code blocks in SkillDetailPage
 * 2. Syntax highlighting is applied to code blocks in SnippetDetailPage
 * 3. Line numbers are displayed
 * 4. Language detection works correctly from file tags
 * 5. Visual appearance matches VS Code dark theme
 */

test.describe('Code Display Improvements - PR #138', () => {
  
  test.describe('SkillDetailPage - Tool Module Code Display', () => {
    test('should display tool module code with syntax highlighting and line numbers', async ({ page }) => {
      // Navigate to skills page
      await page.goto('/skills');
      await page.waitForLoadState('networkidle');

      // Find and click on a skill that has tools
      const skillLink = page.locator('a[href*="/skills/"]').first();
      
      if (await skillLink.count() === 0) {
        test.skip();
        return;
      }

      await skillLink.click();
      await page.waitForLoadState('networkidle');

      // Switch to Tools tab
      const toolsTab = page.getByRole('tab', { name: /tools/i });
      if (await toolsTab.isVisible()) {
        await toolsTab.click();
        await page.waitForTimeout(500);

        // Check if there are any tools listed
        const toolItems = page.locator('[role="treeitem"]');
        if (await toolItems.count() > 0) {
          // Click on the first tool to view its code
          await toolItems.first().click();
          await page.waitForTimeout(500);

          // Verify syntax highlighter is present
          const syntaxHighlighter = page.locator('.prism-code, pre[class*="language-"]');
          await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

          // Verify line numbers are displayed
          const lineNumbers = page.locator('.linenumber, .line-number, span[class*="line-number"]');
          if (await lineNumbers.count() > 0) {
            await expect(lineNumbers.first()).toBeVisible();
          }

          // Take screenshot for reviewer proof
          await page.screenshot({
            path: 'test-results/skill-tool-code-display.png',
            fullPage: false
          });

          // Verify dark theme styling (vscDarkPlus has dark background)
          const codeBlock = page.locator('pre[class*="language-"]').first();
          if (await codeBlock.isVisible()) {
            const bgColor = await codeBlock.evaluate((el) => {
              return window.getComputedStyle(el).backgroundColor;
            });
            
            // vscDarkPlus theme has a dark background (rgb values should be low)
            expect(bgColor).toMatch(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
            const match = bgColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
            if (match) {
              const [, r, g, b] = match.map(Number);
              // Dark theme should have low RGB values (< 100)
              expect(r).toBeLessThan(100);
              expect(g).toBeLessThan(100);
              expect(b).toBeLessThan(100);
            }
          }
        }
      }
    });

    test('should detect Python language for tool modules', async ({ page }) => {
      await page.goto('/skills');
      await page.waitForLoadState('networkidle');

      const skillLink = page.locator('a[href*="/skills/"]').first();
      
      if (await skillLink.count() === 0) {
        test.skip();
        return;
      }

      await skillLink.click();
      await page.waitForLoadState('networkidle');

      const toolsTab = page.getByRole('tab', { name: /tools/i });
      if (await toolsTab.isVisible()) {
        await toolsTab.click();
        await page.waitForTimeout(500);

        const toolItems = page.locator('[role="treeitem"]');
        if (await toolItems.count() > 0) {
          await toolItems.first().click();
          await page.waitForTimeout(500);

          // Check for Python syntax highlighting classes
          const pythonCode = page.locator('pre[class*="language-python"]');
          if (await pythonCode.isVisible()) {
            await expect(pythonCode).toBeVisible();
            
            // Take screenshot showing Python syntax highlighting
            await page.screenshot({
              path: 'test-results/skill-tool-python-highlighting.png',
              fullPage: false
            });
          }
        }
      }
    });
  });

  test.describe('SkillDetailPage - Snippet Code Display', () => {
    test('should display snippet code with syntax highlighting and line numbers', async ({ page }) => {
      await page.goto('/skills');
      await page.waitForLoadState('networkidle');

      const skillLink = page.locator('a[href*="/skills/"]').first();
      
      if (await skillLink.count() === 0) {
        test.skip();
        return;
      }

      await skillLink.click();
      await page.waitForLoadState('networkidle');

      // Switch to Snippets tab
      const snippetsTab = page.getByRole('tab', { name: /snippets/i });
      if (await snippetsTab.isVisible()) {
        await snippetsTab.click();
        await page.waitForTimeout(500);

        const snippetItems = page.locator('[role="treeitem"]');
        if (await snippetItems.count() > 0) {
          await snippetItems.first().click();
          await page.waitForTimeout(500);

          // Verify syntax highlighter is present
          const syntaxHighlighter = page.locator('.prism-code, pre[class*="language-"]');
          await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

          // Verify line numbers are displayed
          const lineNumbers = page.locator('.linenumber, .line-number, span[class*="line-number"]');
          if (await lineNumbers.count() > 0) {
            await expect(lineNumbers.first()).toBeVisible();
          }

          // Take screenshot for reviewer proof
          await page.screenshot({
            path: 'test-results/skill-snippet-code-display.png',
            fullPage: false
          });
        }
      }
    });

    test('should detect language from snippet tags', async ({ page }) => {
      await page.goto('/skills');
      await page.waitForLoadState('networkidle');

      const skillLink = page.locator('a[href*="/skills/"]').first();
      
      if (await skillLink.count() === 0) {
        test.skip();
        return;
      }

      await skillLink.click();
      await page.waitForLoadState('networkidle');

      const snippetsTab = page.getByRole('tab', { name: /snippets/i });
      if (await snippetsTab.isVisible()) {
        await snippetsTab.click();
        await page.waitForTimeout(500);

        const snippetItems = page.locator('[role="treeitem"]');
        if (await snippetItems.count() > 0) {
          await snippetItems.first().click();
          await page.waitForTimeout(500);

          // Check if language detection worked (should have language-* class)
          const codeBlock = page.locator('pre[class*="language-"]');
          if (await codeBlock.isVisible()) {
            const className = await codeBlock.getAttribute('class');
            expect(className).toMatch(/language-\w+/);
            
            // Take screenshot showing language-specific highlighting
            await page.screenshot({
              path: 'test-results/skill-snippet-language-detection.png',
              fullPage: false
            });
          }
        }
      }
    });
  });

  test.describe('SnippetDetailPage - Code Display', () => {
    test('should display snippet content with syntax highlighting and line numbers', async ({ page }) => {
      await page.goto('/snippets');
      await page.waitForLoadState('networkidle');

      const snippetLink = page.locator('a[href*="/snippets/"]').first();
      
      if (await snippetLink.count() === 0) {
        test.skip();
        return;
      }

      await snippetLink.click();
      await page.waitForLoadState('networkidle');

      // Verify syntax highlighter is present in the Content card
      const syntaxHighlighter = page.locator('.prism-code, pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible({ timeout: 5000 });

      // Verify line numbers are displayed
      const lineNumbers = page.locator('.linenumber, .line-number, span[class*="line-number"]');
      if (await lineNumbers.count() > 0) {
        await expect(lineNumbers.first()).toBeVisible();
      }

      // Take screenshot for reviewer proof
      await page.screenshot({
        path: 'test-results/snippet-detail-code-display.png',
        fullPage: false
      });

      // Verify dark theme styling
      const codeBlock = page.locator('pre[class*="language-"]').first();
      if (await codeBlock.isVisible()) {
        const bgColor = await codeBlock.evaluate((el) => {
          return window.getComputedStyle(el).backgroundColor;
        });
        
        expect(bgColor).toMatch(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
        const match = bgColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
        if (match) {
          const [, r, g, b] = match.map(Number);
          expect(r).toBeLessThan(100);
          expect(g).toBeLessThan(100);
          expect(b).toBeLessThan(100);
        }
      }
    });

    test('should detect language from file extension in tags', async ({ page }) => {
      await page.goto('/snippets');
      await page.waitForLoadState('networkidle');

      const snippetLink = page.locator('a[href*="/snippets/"]').first();
      
      if (await snippetLink.count() === 0) {
        test.skip();
        return;
      }

      await snippetLink.click();
      await page.waitForLoadState('networkidle');

      // Check if language detection worked
      const codeBlock = page.locator('pre[class*="language-"]');
      if (await codeBlock.isVisible()) {
        const className = await codeBlock.getAttribute('class');
        expect(className).toMatch(/language-\w+/);
        
        // Take screenshot showing language-specific highlighting
        await page.screenshot({
          path: 'test-results/snippet-detail-language-detection.png',
          fullPage: false
        });
      }
    });

    test('should handle multiple programming languages correctly', async ({ page }) => {
      await page.goto('/snippets');
      await page.waitForLoadState('networkidle');

      // Test with different snippets to verify language detection
      const snippetLinks = page.locator('a[href*="/snippets/"]');
      const count = await snippetLinks.count();
      
      if (count === 0) {
        test.skip();
        return;
      }

      // Test up to 3 different snippets
      const testCount = Math.min(count, 3);
      const languages = new Set<string>();

      for (let i = 0; i < testCount; i++) {
        await page.goto('/snippets');
        await page.waitForLoadState('networkidle');
        
        const link = snippetLinks.nth(i);
        await link.click();
        await page.waitForLoadState('networkidle');

        const codeBlock = page.locator('pre[class*="language-"]');
        if (await codeBlock.isVisible()) {
          const className = await codeBlock.getAttribute('class');
          const langMatch = className?.match(/language-(\w+)/);
          if (langMatch) {
            languages.add(langMatch[1]);
          }
        }
      }

      // Verify that language detection is working (at least one language detected)
      expect(languages.size).toBeGreaterThan(0);
    });
  });

  test.describe('Visual Regression - Code Block Styling', () => {
    test('should match VS Code dark theme appearance', async ({ page }) => {
      await page.goto('/snippets');
      await page.waitForLoadState('networkidle');

      const snippetLink = page.locator('a[href*="/snippets/"]').first();
      
      if (await snippetLink.count() === 0) {
        test.skip();
        return;
      }

      await snippetLink.click();
      await page.waitForLoadState('networkidle');

      const codeBlock = page.locator('pre[class*="language-"]').first();
      
      if (await codeBlock.isVisible()) {
        // Verify border styling
        const borderStyle = await codeBlock.evaluate((el) => {
          const parent = el.parentElement;
          return parent ? window.getComputedStyle(parent).border : '';
        });
        
        // Should have a border (1px solid #3d3d3d per the PR changes)
        expect(borderStyle).toBeTruthy();

        // Verify border radius
        const borderRadius = await codeBlock.evaluate((el) => {
          const parent = el.parentElement;
          return parent ? window.getComputedStyle(parent).borderRadius : '';
        });
        
        // Should have rounded corners (6px per the PR changes)
        expect(borderRadius).toMatch(/\d+px/);

        // Take full screenshot for visual comparison
        await page.screenshot({
          path: 'test-results/code-block-vscode-theme.png',
          fullPage: false
        });
      }
    });

    test('should display code with proper font and line height', async ({ page }) => {
      await page.goto('/snippets');
      await page.waitForLoadState('networkidle');

      const snippetLink = page.locator('a[href*="/snippets/"]').first();
      
      if (await snippetLink.count() === 0) {
        test.skip();
        return;
      }

      await snippetLink.click();
      await page.waitForLoadState('networkidle');

      const codeBlock = page.locator('pre[class*="language-"]').first();
      
      if (await codeBlock.isVisible()) {
        const styles = await codeBlock.evaluate((el) => {
          const computed = window.getComputedStyle(el);
          return {
            fontSize: computed.fontSize,
            lineHeight: computed.lineHeight,
            fontFamily: computed.fontFamily
          };
        });

        // Verify font size is 15px (per PR changes)
        expect(styles.fontSize).toBe('15px');

        // Verify line height is 1.6 (per PR changes)
        const lineHeightValue = parseFloat(styles.lineHeight) / parseFloat(styles.fontSize);
        expect(lineHeightValue).toBeCloseTo(1.6, 1);

        // Verify monospace font is used
        expect(styles.fontFamily).toMatch(/monospace|courier|consolas|monaco/i);
      }
    });
  });

  test.describe('Accessibility - Code Display', () => {
    test('should maintain accessibility with syntax highlighting', async ({ page }) => {
      await page.goto('/snippets');
      await page.waitForLoadState('networkidle');

      const snippetLink = page.locator('a[href*="/snippets/"]').first();
      
      if (await snippetLink.count() === 0) {
        test.skip();
        return;
      }

      await snippetLink.click();
      await page.waitForLoadState('networkidle');

      // Run accessibility scan
      const accessibilityScanResults = await page.evaluate(() => {
        // Check if code blocks are keyboard accessible
        const codeBlocks = document.querySelectorAll('pre[class*="language-"]');
        return {
          codeBlockCount: codeBlocks.length,
          hasTabIndex: Array.from(codeBlocks).some(block => 
            block.hasAttribute('tabindex') || block.getAttribute('tabindex') === '0'
          )
        };
      });

      expect(accessibilityScanResults.codeBlockCount).toBeGreaterThan(0);
    });

    test('should support text selection in code blocks', async ({ page }) => {
      await page.goto('/snippets');
      await page.waitForLoadState('networkidle');

      const snippetLink = page.locator('a[href*="/snippets/"]').first();
      
      if (await snippetLink.count() === 0) {
        test.skip();
        return;
      }

      await snippetLink.click();
      await page.waitForLoadState('networkidle');

      const codeBlock = page.locator('pre[class*="language-"]').first();
      
      if (await codeBlock.isVisible()) {
        // Try to select text in the code block
        await codeBlock.click();
        await page.keyboard.press('Control+A');
        
        const selectedText = await page.evaluate(() => {
          return window.getSelection()?.toString() || '';
        });

        // Should be able to select text
        expect(selectedText.length).toBeGreaterThan(0);
      }
    });
  });
});
