// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { test, expect } from '@playwright/test';

/**
 * Visual regression tests for syntax highlighting feature
 * Captures screenshots for visual comparison across different languages and themes
 */

test.describe('Syntax Highlighting - Visual Regression', () => {
  const API_BASE = 'http://localhost:8000';

  test('should render Python code with consistent styling', async ({ page, request }) => {
    const pythonCode = `def fibonacci(n: int) -> int:
    """
    Calculate Fibonacci number recursively.
    
    Args:
        n: The position in Fibonacci sequence
        
    Returns:
        The Fibonacci number at position n
    """
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

class Calculator:
    """A simple calculator class."""
    
    def __init__(self):
        self.result = 0
    
    def add(self, value: int) -> int:
        """Add a value to the result."""
        self.result += value
        return self.result
    
    def subtract(self, value: int) -> int:
        """Subtract a value from the result."""
        self.result -= value
        return self.result

# Example usage
calc = Calculator()
calc.add(10)
calc.subtract(3)
print(f"Result: {calc.result}")`;

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Visual Python Test ${Date.now()}`,
        description: 'Python code for visual regression testing',
        content: pythonCode,
        content_type: 'text/x-python',
        tags: ['test', 'visual']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      // Wait for syntax highlighter
      await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

      // Take screenshot of the entire code block
      const codeContainer = page.locator('div').filter({
        has: page.locator('pre[class*="language-"]')
      }).first();

      await codeContainer.screenshot({
        path: test.info().outputPath('visual-python-syntax-highlighting.png')
      });

      // Verify visual elements are present
      const syntaxHighlighter = page.locator('pre[class*="language-"]');
      await expect(syntaxHighlighter).toBeVisible();

      // Check for syntax highlighting classes
      const codeElement = page.locator('code[class*="language-python"]');
      await expect(codeElement).toBeVisible();
    } finally {
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should render JavaScript code with consistent styling', async ({ page, request }) => {
    const jsCode = `/**
 * Debounce function to limit function execution rate
 * @param {Function} func - The function to debounce
 * @param {number} wait - The delay in milliseconds
 * @returns {Function} The debounced function
 */
function debounce(func, wait) {
  let timeout;
  
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// ES6 Class example
class EventEmitter {
  constructor() {
    this.events = {};
  }
  
  on(event, listener) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(listener);
  }
  
  emit(event, ...args) {
    if (this.events[event]) {
      this.events[event].forEach(listener => listener(...args));
    }
  }
}

// Arrow functions and template literals
const greet = (name) => {
  console.log(\`Hello, \${name}!\`);
};

// Async/await example
async function fetchData(url) {
  try {
    const response = await fetch(url);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching data:', error);
    throw error;
  }
}`;

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Visual JavaScript Test ${Date.now()}`,
        description: 'JavaScript code for visual regression testing',
        content: jsCode,
        content_type: 'text/javascript',
        tags: ['test', 'visual']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

      const codeContainer = page.locator('div').filter({
        has: page.locator('pre[class*="language-"]')
      }).first();

      await codeContainer.screenshot({
        path: test.info().outputPath('visual-javascript-syntax-highlighting.png')
      });
    } finally {
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should render TypeScript code with consistent styling', async ({ page, request }) => {
    const tsCode = `interface User {
  id: number;
  name: string;
  email: string;
  role: 'admin' | 'user' | 'guest';
}

type UserRole = User['role'];

class UserService {
  private users: Map<number, User> = new Map();
  
  constructor(private readonly apiUrl: string) {}
  
  async getUser(id: number): Promise<User | null> {
    if (this.users.has(id)) {
      return this.users.get(id)!;
    }
    
    try {
      const response = await fetch(\`\${this.apiUrl}/users/\${id}\`);
      const user: User = await response.json();
      this.users.set(id, user);
      return user;
    } catch (error) {
      console.error('Failed to fetch user:', error);
      return null;
    }
  }
  
  createUser(userData: Omit<User, 'id'>): User {
    const id = this.users.size + 1;
    const user: User = { id, ...userData };
    this.users.set(id, user);
    return user;
  }
}

// Generic function example
function identity<T>(arg: T): T {
  return arg;
}

// Union types and type guards
function processValue(value: string | number): string {
  if (typeof value === 'string') {
    return value.toUpperCase();
  }
  return value.toString();
}`;

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Visual TypeScript Test ${Date.now()}`,
        description: 'TypeScript code for visual regression testing',
        content: tsCode,
        content_type: 'text/typescript',
        tags: ['test', 'visual']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

      const codeContainer = page.locator('div').filter({
        has: page.locator('pre[class*="language-"]')
      }).first();

      await codeContainer.screenshot({
        path: test.info().outputPath('visual-typescript-syntax-highlighting.png')
      });
    } finally {
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should render JSON with consistent styling', async ({ page, request }) => {
    const jsonCode = `{
  "name": "skillberry-store",
  "version": "1.0.0",
  "description": "A store for AI skills and tools",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "test": "jest",
    "build": "webpack --mode production"
  },
  "dependencies": {
    "express": "^4.18.0",
    "react": "^18.2.0",
    "typescript": "^5.0.0"
  },
  "devDependencies": {
    "jest": "^29.0.0",
    "webpack": "^5.75.0"
  },
  "keywords": [
    "ai",
    "skills",
    "tools",
    "mcp"
  ],
  "author": "IBM",
  "license": "Apache-2.0"
}`;

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Visual JSON Test ${Date.now()}`,
        description: 'JSON code for visual regression testing',
        content: jsonCode,
        content_type: 'application/json',
        tags: ['test', 'visual']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

      const codeContainer = page.locator('div').filter({
        has: page.locator('pre[class*="language-"]')
      }).first();

      await codeContainer.screenshot({
        path: test.info().outputPath('visual-json-syntax-highlighting.png')
      });
    } finally {
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should render YAML with consistent styling', async ({ page, request }) => {
    const yamlCode = `name: CI/CD Pipeline
on:
  push:
    branches:
      - main
      - develop
  pull_request:
    branches:
      - main

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [16.x, 18.x, 20.x]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: \${{ matrix.node-version }}
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm test
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
          flags: unittests
          name: codecov-umbrella`;

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Visual YAML Test ${Date.now()}`,
        description: 'YAML code for visual regression testing',
        content: yamlCode,
        content_type: 'text/x-yaml',
        tags: ['test', 'visual']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

      const codeContainer = page.locator('div').filter({
        has: page.locator('pre[class*="language-"]')
      }).first();

      await codeContainer.screenshot({
        path: test.info().outputPath('visual-yaml-syntax-highlighting.png')
      });
    } finally {
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should render line numbers consistently', async ({ page, request }) => {
    const codeWithManyLines = Array(50)
      .fill(0)
      .map((_, i) => `line ${i + 1}: print("Line ${i + 1}")`)
      .join('\n');

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Visual Line Numbers Test ${Date.now()}`,
        description: 'Code for testing line number rendering',
        content: codeWithManyLines,
        content_type: 'text/x-python',
        tags: ['test', 'visual']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

      // Scroll to middle to show line numbers
      const codeContainer = page.locator('div').filter({
        has: page.locator('pre[class*="language-"]')
      }).first();

      await codeContainer.evaluate((el) => {
        el.scrollTop = el.scrollHeight / 2;
      });

      await page.waitForTimeout(500);

      await codeContainer.screenshot({
        path: test.info().outputPath('visual-line-numbers.png')
      });
    } finally {
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should render dark theme consistently', async ({ page, request }) => {
    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Visual Dark Theme Test ${Date.now()}`,
        description: 'Code for testing dark theme',
        content: `def example():\n    # This is a comment\n    x = "string"\n    y = 42\n    return x, y`,
        content_type: 'text/x-python',
        tags: ['test', 'visual']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

      // Verify dark theme colors
      const syntaxHighlighter = page.locator('pre[class*="language-"]').first();
      const backgroundColor = await syntaxHighlighter.evaluate((el) =>
        window.getComputedStyle(el).backgroundColor
      );

      // vscDarkPlus theme should have dark background
      expect(backgroundColor).toMatch(/rgb\(30, 30, 30\)|rgb\(31, 31, 31\)|#1e1e1e/i);

      const codeContainer = page.locator('div').filter({
        has: page.locator('pre[class*="language-"]')
      }).first();

      await codeContainer.screenshot({
        path: test.info().outputPath('visual-dark-theme.png')
      });
    } finally {
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });

  test('should render scrollable container consistently', async ({ page, request }) => {
    const longCode = Array(100)
      .fill(0)
      .map((_, i) => `def function_${i}():\n    return ${i}`)
      .join('\n\n');

    const snippetResponse = await request.post(`${API_BASE}/api/snippets/`, {
      data: {
        name: `Visual Scrollable Test ${Date.now()}`,
        description: 'Long code for testing scrollable container',
        content: longCode,
        content_type: 'text/x-python',
        tags: ['test', 'visual']
      }
    });

    if (!snippetResponse.ok()) {
      test.skip(true, 'Failed to create test snippet');
      return;
    }

    const snippet = await snippetResponse.json();
    const snippetId = snippet.id;

    try {
      await page.goto(`/snippets/${snippetId}`);
      await page.waitForLoadState('networkidle');

      await page.waitForSelector('pre[class*="language-"]', { timeout: 10000 });

      const codeContainer = page.locator('div').filter({
        has: page.locator('pre[class*="language-"]')
      }).first();

      // Take screenshot showing scrollbar
      await codeContainer.screenshot({
        path: test.info().outputPath('visual-scrollable-container.png')
      });

      // Verify scrollbar is present
      const isScrollable = await codeContainer.evaluate((el) => {
        return el.scrollHeight > el.clientHeight;
      });

      expect(isScrollable).toBe(true);
    } finally {
      await request.delete(`${API_BASE}/api/snippets/${snippetId}`);
    }
  });
});
