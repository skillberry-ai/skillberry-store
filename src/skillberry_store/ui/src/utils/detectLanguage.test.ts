// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import { describe, it, expect } from 'vitest';
import { detectLanguage } from './detectLanguage';

describe('detectLanguage', () => {
  describe('file extension detection', () => {
    it('should detect Python from .py extension', () => {
      expect(detectLanguage(['file:script.py'])).toBe('python');
      expect(detectLanguage(['file:path/to/module.py'])).toBe('python');
    });

    it('should detect JavaScript from .js extension', () => {
      expect(detectLanguage(['file:app.js'])).toBe('javascript');
    });

    it('should detect TypeScript from .ts extension', () => {
      expect(detectLanguage(['file:component.ts'])).toBe('typescript');
    });

    it('should detect JSX from .jsx extension', () => {
      expect(detectLanguage(['file:Component.jsx'])).toBe('jsx');
    });

    it('should detect TSX from .tsx extension', () => {
      expect(detectLanguage(['file:Component.tsx'])).toBe('tsx');
    });

    it('should detect Java from .java extension', () => {
      expect(detectLanguage(['file:Main.java'])).toBe('java');
    });

    it('should detect C++ from .cpp extension', () => {
      expect(detectLanguage(['file:program.cpp'])).toBe('cpp');
    });

    it('should detect C from .c extension', () => {
      expect(detectLanguage(['file:program.c'])).toBe('c');
    });

    it('should detect C# from .cs extension', () => {
      expect(detectLanguage(['file:Program.cs'])).toBe('csharp');
    });

    it('should detect Go from .go extension', () => {
      expect(detectLanguage(['file:main.go'])).toBe('go');
    });

    it('should detect Rust from .rs extension', () => {
      expect(detectLanguage(['file:main.rs'])).toBe('rust');
    });

    it('should detect Ruby from .rb extension', () => {
      expect(detectLanguage(['file:script.rb'])).toBe('ruby');
    });

    it('should detect PHP from .php extension', () => {
      expect(detectLanguage(['file:index.php'])).toBe('php');
    });

    it('should detect Swift from .swift extension', () => {
      expect(detectLanguage(['file:ViewController.swift'])).toBe('swift');
    });

    it('should detect Kotlin from .kt extension', () => {
      expect(detectLanguage(['file:MainActivity.kt'])).toBe('kotlin');
    });

    it('should detect Scala from .scala extension', () => {
      expect(detectLanguage(['file:Main.scala'])).toBe('scala');
    });

    it('should detect Bash from shell script extensions', () => {
      expect(detectLanguage(['file:script.sh'])).toBe('bash');
      expect(detectLanguage(['file:script.bash'])).toBe('bash');
      expect(detectLanguage(['file:script.zsh'])).toBe('bash');
    });

    it('should detect SQL from .sql extension', () => {
      expect(detectLanguage(['file:query.sql'])).toBe('sql');
    });

    it('should detect JSON from .json extension', () => {
      expect(detectLanguage(['file:config.json'])).toBe('json');
    });

    it('should detect YAML from .yaml and .yml extensions', () => {
      expect(detectLanguage(['file:config.yaml'])).toBe('yaml');
      expect(detectLanguage(['file:config.yml'])).toBe('yaml');
    });

    it('should detect XML from .xml extension', () => {
      expect(detectLanguage(['file:config.xml'])).toBe('xml');
    });

    it('should detect HTML from .html extension', () => {
      expect(detectLanguage(['file:index.html'])).toBe('html');
    });

    it('should detect CSS from .css extension', () => {
      expect(detectLanguage(['file:styles.css'])).toBe('css');
    });

    it('should detect SCSS from .scss extension', () => {
      expect(detectLanguage(['file:styles.scss'])).toBe('scss');
    });

    it('should detect Markdown from .md extension', () => {
      expect(detectLanguage(['file:README.md'])).toBe('markdown');
    });

    it('should detect text from .txt extension', () => {
      expect(detectLanguage(['file:notes.txt'])).toBe('text');
    });

    it('should handle case-insensitive extensions', () => {
      expect(detectLanguage(['file:Script.PY'])).toBe('python');
      expect(detectLanguage(['file:App.JS'])).toBe('javascript');
    });

    it('should handle complex file paths', () => {
      expect(detectLanguage(['file:/absolute/path/to/script.py'])).toBe('python');
      expect(detectLanguage(['file:../relative/path/app.js'])).toBe('javascript');
      expect(detectLanguage(['file:./current/dir/file.ts'])).toBe('typescript');
    });
  });

  describe('language tag detection', () => {
    it('should detect language from language: tag', () => {
      expect(detectLanguage(['language:python'])).toBe('python');
      expect(detectLanguage(['language:javascript'])).toBe('javascript');
      expect(detectLanguage(['language:typescript'])).toBe('typescript');
    });

    it('should handle case-insensitive language tags', () => {
      expect(detectLanguage(['language:Python'])).toBe('python');
      expect(detectLanguage(['language:JAVASCRIPT'])).toBe('javascript');
    });

    it('should prioritize file: tag over language: tag', () => {
      expect(detectLanguage(['file:script.py', 'language:javascript'])).toBe('python');
    });
  });

  describe('edge cases', () => {
    it('should return "text" for empty tags array', () => {
      expect(detectLanguage([])).toBe('text');
    });

    it('should return "text" for unknown file extension', () => {
      expect(detectLanguage(['file:unknown.xyz'])).toBe('text');
    });

    it('should return "text" for file without extension', () => {
      expect(detectLanguage(['file:Makefile'])).toBe('text');
      expect(detectLanguage(['file:README'])).toBe('text');
    });

    it('should handle tags without file: or language: prefix', () => {
      expect(detectLanguage(['tag1', 'tag2', 'tag3'])).toBe('text');
    });

    it('should handle multiple file: tags (uses first one)', () => {
      expect(detectLanguage(['file:script.py', 'file:app.js'])).toBe('python');
    });

    it('should handle file: tag with no path', () => {
      expect(detectLanguage(['file:'])).toBe('text');
    });

    it('should handle malformed tags gracefully', () => {
      expect(detectLanguage(['file', 'language', 'random'])).toBe('text');
    });
  });

  describe('real-world scenarios', () => {
    it('should handle typical snippet tags', () => {
      const tags = ['file:src/utils/helper.ts', 'utility', 'typescript'];
      expect(detectLanguage(tags)).toBe('typescript');
    });

    it('should handle tool module tags', () => {
      const tags = ['file:tools/calculator.py', 'tool', 'math'];
      expect(detectLanguage(tags)).toBe('python');
    });

    it('should handle config file tags', () => {
      const tags = ['file:config/settings.json', 'configuration'];
      expect(detectLanguage(tags)).toBe('json');
    });

    it('should handle script tags', () => {
      const tags = ['file:scripts/deploy.sh', 'deployment', 'automation'];
      expect(detectLanguage(tags)).toBe('bash');
    });
  });
});
