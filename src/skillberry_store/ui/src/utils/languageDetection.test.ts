// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect } from 'vitest';
import { detectLanguage } from './languageDetection';

describe('detectLanguage', () => {
  describe('content type detection', () => {
    it('should detect Python from content type', () => {
      expect(detectLanguage('text/x-python')).toBe('python');
    });

    it('should detect JavaScript from content type', () => {
      expect(detectLanguage('text/javascript')).toBe('javascript');
      expect(detectLanguage('application/javascript')).toBe('javascript');
    });

    it('should detect TypeScript from content type', () => {
      expect(detectLanguage('text/typescript')).toBe('typescript');
      expect(detectLanguage('application/typescript')).toBe('typescript');
    });

    it('should detect Java from content type', () => {
      expect(detectLanguage('text/x-java')).toBe('java');
    });

    it('should detect Go from content type', () => {
      expect(detectLanguage('text/x-go')).toBe('go');
    });

    it('should detect Bash from content type', () => {
      expect(detectLanguage('text/x-sh')).toBe('bash');
    });

    it('should detect YAML from content type', () => {
      expect(detectLanguage('text/x-yaml')).toBe('yaml');
    });

    it('should detect JSON from content type', () => {
      expect(detectLanguage('application/json')).toBe('json');
    });

    it('should detect HTML from content type', () => {
      expect(detectLanguage('text/html')).toBe('html');
    });

    it('should detect CSS from content type', () => {
      expect(detectLanguage('text/css')).toBe('css');
    });

    it('should detect C from content type', () => {
      expect(detectLanguage('text/x-c')).toBe('c');
    });

    it('should detect C++ from content type', () => {
      expect(detectLanguage('text/x-c++')).toBe('cpp');
    });

    it('should detect C# from content type', () => {
      expect(detectLanguage('text/x-csharp')).toBe('csharp');
    });

    it('should detect Ruby from content type', () => {
      expect(detectLanguage('text/x-ruby')).toBe('ruby');
    });

    it('should detect Rust from content type', () => {
      expect(detectLanguage('text/x-rust')).toBe('rust');
    });

    it('should detect SQL from content type', () => {
      expect(detectLanguage('text/x-sql')).toBe('sql');
    });

    it('should detect Markdown from content type', () => {
      expect(detectLanguage('text/markdown')).toBe('markdown');
    });

    it('should detect XML from content type', () => {
      expect(detectLanguage('text/xml')).toBe('xml');
    });

    it('should handle case-insensitive content types', () => {
      expect(detectLanguage('TEXT/X-PYTHON')).toBe('python');
      expect(detectLanguage('Application/JavaScript')).toBe('javascript');
    });
  });

  describe('file extension detection from fileName', () => {
    it('should detect Python from .py extension', () => {
      expect(detectLanguage(undefined, 'script.py')).toBe('python');
    });

    it('should detect JavaScript from .js extension', () => {
      expect(detectLanguage(undefined, 'app.js')).toBe('javascript');
    });

    it('should detect JavaScript from .jsx extension', () => {
      expect(detectLanguage(undefined, 'Component.jsx')).toBe('javascript');
    });

    it('should detect TypeScript from .ts extension', () => {
      expect(detectLanguage(undefined, 'utils.ts')).toBe('typescript');
    });

    it('should detect TypeScript from .tsx extension', () => {
      expect(detectLanguage(undefined, 'Component.tsx')).toBe('typescript');
    });

    it('should detect Java from .java extension', () => {
      expect(detectLanguage(undefined, 'Main.java')).toBe('java');
    });

    it('should detect Go from .go extension', () => {
      expect(detectLanguage(undefined, 'main.go')).toBe('go');
    });

    it('should detect Bash from .sh extension', () => {
      expect(detectLanguage(undefined, 'script.sh')).toBe('bash');
    });

    it('should detect Bash from .bash extension', () => {
      expect(detectLanguage(undefined, 'script.bash')).toBe('bash');
    });

    it('should detect YAML from .yaml extension', () => {
      expect(detectLanguage(undefined, 'config.yaml')).toBe('yaml');
    });

    it('should detect YAML from .yml extension', () => {
      expect(detectLanguage(undefined, 'config.yml')).toBe('yaml');
    });

    it('should detect JSON from .json extension', () => {
      expect(detectLanguage(undefined, 'package.json')).toBe('json');
    });

    it('should detect HTML from .html extension', () => {
      expect(detectLanguage(undefined, 'index.html')).toBe('html');
    });

    it('should detect HTML from .htm extension', () => {
      expect(detectLanguage(undefined, 'page.htm')).toBe('html');
    });

    it('should detect CSS from .css extension', () => {
      expect(detectLanguage(undefined, 'styles.css')).toBe('css');
    });

    it('should detect C from .c extension', () => {
      expect(detectLanguage(undefined, 'program.c')).toBe('c');
    });

    it('should detect C++ from various extensions', () => {
      expect(detectLanguage(undefined, 'program.cpp')).toBe('cpp');
      expect(detectLanguage(undefined, 'program.cc')).toBe('cpp');
      expect(detectLanguage(undefined, 'program.cxx')).toBe('cpp');
    });

    it('should detect C# from .cs extension', () => {
      expect(detectLanguage(undefined, 'Program.cs')).toBe('csharp');
    });

    it('should detect Ruby from .rb extension', () => {
      expect(detectLanguage(undefined, 'script.rb')).toBe('ruby');
    });

    it('should detect Rust from .rs extension', () => {
      expect(detectLanguage(undefined, 'main.rs')).toBe('rust');
    });

    it('should detect SQL from .sql extension', () => {
      expect(detectLanguage(undefined, 'query.sql')).toBe('sql');
    });

    it('should detect Markdown from .md extension', () => {
      expect(detectLanguage(undefined, 'README.md')).toBe('markdown');
    });

    it('should detect XML from .xml extension', () => {
      expect(detectLanguage(undefined, 'config.xml')).toBe('xml');
    });

    it('should detect PHP from .php extension', () => {
      expect(detectLanguage(undefined, 'index.php')).toBe('php');
    });

    it('should detect Swift from .swift extension', () => {
      expect(detectLanguage(undefined, 'App.swift')).toBe('swift');
    });

    it('should detect Kotlin from .kt extension', () => {
      expect(detectLanguage(undefined, 'Main.kt')).toBe('kotlin');
    });

    it('should detect Scala from .scala extension', () => {
      expect(detectLanguage(undefined, 'App.scala')).toBe('scala');
    });

    it('should detect R from .r extension', () => {
      expect(detectLanguage(undefined, 'analysis.r')).toBe('r');
    });

    it('should detect Perl from .pl extension', () => {
      expect(detectLanguage(undefined, 'script.pl')).toBe('perl');
    });

    it('should detect Lua from .lua extension', () => {
      expect(detectLanguage(undefined, 'config.lua')).toBe('lua');
    });

    it('should handle case-insensitive file extensions', () => {
      expect(detectLanguage(undefined, 'Script.PY')).toBe('python');
      expect(detectLanguage(undefined, 'App.JS')).toBe('javascript');
    });

    it('should handle files with multiple dots', () => {
      expect(detectLanguage(undefined, 'my.config.file.json')).toBe('json');
      expect(detectLanguage(undefined, 'test.spec.ts')).toBe('typescript');
    });

    it('should handle files without extension', () => {
      expect(detectLanguage(undefined, 'Makefile')).toBe('python');
    });
  });

  describe('file extension detection from tags', () => {
    it('should detect Python from file: tag', () => {
      expect(detectLanguage(undefined, undefined, ['file:script.py'])).toBe('python');
    });

    it('should detect JavaScript from file: tag', () => {
      expect(detectLanguage(undefined, undefined, ['file:app.js'])).toBe('javascript');
    });

    it('should detect TypeScript from file: tag', () => {
      expect(detectLanguage(undefined, undefined, ['file:utils.ts'])).toBe('typescript');
    });

    it('should detect language from file: tag with path', () => {
      expect(detectLanguage(undefined, undefined, ['file:src/components/App.tsx'])).toBe('typescript');
    });

    it('should handle multiple tags and find file: tag', () => {
      expect(detectLanguage(undefined, undefined, ['category:utility', 'file:helper.py', 'version:1.0'])).toBe('python');
    });

    it('should ignore non-file tags', () => {
      expect(detectLanguage(undefined, undefined, ['category:utility', 'version:1.0'])).toBe('python');
    });

    it('should handle file: tag without extension', () => {
      expect(detectLanguage(undefined, undefined, ['file:Makefile'])).toBe('python');
    });
  });

  describe('priority and fallback behavior', () => {
    it('should prioritize content type over fileName', () => {
      expect(detectLanguage('text/x-python', 'script.js')).toBe('python');
    });

    it('should prioritize content type over tags', () => {
      expect(detectLanguage('text/x-python', undefined, ['file:script.js'])).toBe('python');
    });

    it('should prioritize fileName over tags', () => {
      expect(detectLanguage(undefined, 'script.js', ['file:script.py'])).toBe('javascript');
    });

    it('should fall back to tags when content type and fileName are not provided', () => {
      expect(detectLanguage(undefined, undefined, ['file:script.py'])).toBe('python');
    });

    it('should default to python when no detection method works', () => {
      expect(detectLanguage()).toBe('python');
      expect(detectLanguage(undefined, undefined, [])).toBe('python');
      expect(detectLanguage('unknown/type')).toBe('python');
      expect(detectLanguage(undefined, 'file.unknown')).toBe('python');
    });

    it('should default to python for unrecognized content types', () => {
      expect(detectLanguage('application/octet-stream')).toBe('python');
      expect(detectLanguage('text/plain')).toBe('python');
    });

    it('should default to python for unrecognized extensions', () => {
      expect(detectLanguage(undefined, 'file.xyz')).toBe('python');
      expect(detectLanguage(undefined, 'file.unknown')).toBe('python');
    });
  });

  describe('edge cases', () => {
    it('should handle empty strings', () => {
      expect(detectLanguage('')).toBe('python');
      expect(detectLanguage(undefined, '')).toBe('python');
    });

    it('should handle whitespace', () => {
      expect(detectLanguage('  ')).toBe('python');
      expect(detectLanguage(undefined, '  ')).toBe('python');
    });

    it('should handle null-like values gracefully', () => {
      expect(detectLanguage(undefined, undefined, undefined)).toBe('python');
    });

    it('should handle empty arrays', () => {
      expect(detectLanguage(undefined, undefined, [])).toBe('python');
    });

    it('should handle tags array with empty strings', () => {
      expect(detectLanguage(undefined, undefined, ['', 'file:script.py', ''])).toBe('python');
    });

    it('should handle file: tag with just the prefix', () => {
      expect(detectLanguage(undefined, undefined, ['file:'])).toBe('python');
    });

    it('should handle file names with only dots', () => {
      expect(detectLanguage(undefined, '...')).toBe('python');
      expect(detectLanguage(undefined, '.')).toBe('python');
    });
  });
});
