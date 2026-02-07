# Anthropic Skills Integration

This module provides functionality to import and export Anthropic skills, enabling seamless integration between Skillberry Store and Anthropic skill format.

## Overview

The Anthropic Skills Integration allows users to:
- **Import** skills from GitHub URLs or ZIP files into Skillberry Store
- **Export** skills from Skillberry Store to Anthropic skill format
- Automatically parse text files into snippets
- Automatically parse Python and Bash code files into tools
- Preserve file structure using `file:` tags

---

# Anthropic Skill Importer

## Features

- Import skills from GitHub URLs (e.g., https://github.com/anthropics/skills/tree/main/skills/pptx)
- Import skills from ZIP files
- Automatically parse text files into snippets
- Automatically parse Python and Bash code files into tools
- Create a skill that groups all imported tools and snippets

## Architecture

The importer consists of three main files:

### 1. `textParser.ts`
Handles parsing of text files (markdown, txt, json, yaml, etc.) into snippets.

**Key Features:**
- Splits text files into paragraphs (separated by double newlines)
- Each paragraph becomes a separate snippet
- Automatically generates descriptions from content
- Extracts tags from file paths and names
- Supports multiple text file formats

**Functions:**
- `parseTextFile()` - Parse a single text file into snippets
- `parseTextFiles()` - Parse multiple text files
- `isTextFile()` - Check if a file should be processed as text

### 2. `codeParser.ts`
Handles parsing of Python and Bash code files into tools.

**Key Features:**
- Extracts functions from Python and Bash files
- Parses docstrings to extract descriptions and parameters
- Parses function signatures to identify parameters
- Creates tools with proper metadata (params, returns, tags)
- Logs and ignores unsupported file types

**Functions:**
- `parseCodeFile()` - Parse a single code file into tools
- `parseCodeFiles()` - Parse multiple code files
- `isCodeFile()` - Check if a file should be processed as code
- `parsePythonFunction()` - Extract metadata from Python functions
- `parseBashFunction()` - Extract metadata from Bash functions

### 3. `importer.tsx`
React component providing the UI for importing Anthropic skills.

**Key Features:**
- Modal dialog with two import modes: GitHub URL and ZIP file
- Progress tracking during import
- Detailed result reporting (tools created, snippets created, ignored files)
- Error handling and user feedback
- Integration with existing Skillberry Store APIs

**Import Process:**
1. Fetch files from GitHub or extract from ZIP
2. Parse text files into snippets
3. Parse code files into tools
4. Create tools via API
5. Create snippets via API
6. Create skill linking tools and snippets

## Usage

### From Admin Page

1. Navigate to the Admin page
2. Click "Import Anthropic Skill" button
3. Choose import source:
   - **GitHub URL**: Enter the URL to an Anthropic skill repository
   - **ZIP File**: Upload a ZIP file containing the skill
4. Click "Import"
5. Monitor progress and view results

### Example GitHub URLs

```
https://github.com/anthropics/skills/tree/main/skills/pptx
https://github.com/anthropics/skills/tree/main/skills/pdf
https://github.com/anthropics/skills/tree/main/skills/web-search
```

## File Processing Rules

### Text Files
- **Supported formats**: .md, .txt, .rst, .json, .yaml, .yml, .toml, .ini, .cfg, .xml, .html, .css
- **Processing**: Split into paragraphs, each becomes a snippet
- **Tags**: Automatically tagged with `file:path/to/file.ext`, file extension, directory names, filename, and 'anthropic'

### Code Files
- **Supported languages**: Python (.py), Bash (.sh, .bash)
- **Processing**: Each function becomes a separate tool
- **Metadata extraction**:
  - Python: Docstrings for description, parameters, and return values
  - Bash: Comments above function for description
- **Tags**: Automatically tagged with `file:path/to/file.ext`, language, directory names, filename, and 'anthropic'

### Ignored Files
- Binary files (images, executables, etc.)
- Unsupported script types (JavaScript, Ruby, etc.)
- These are logged but don't cause import failure

---

# Anthropic Skill Exporter

## Features

- Export skills from the Skill Detail page
- Create ZIP files with proper Anthropic skill structure
- Preserve file structure from `file:` tags in snippets and tools
- Generate SKILL.md with frontmatter
- Export tools to scripts folder when no file structure is defined

## Architecture

### `exporter.ts`
Main export logic that handles the conversion from Skillberry format to Anthropic format.

**Key Functions:**
- `exportSkillToAnthropicFormat()` - Main export function that creates the ZIP
- `exportAndDownloadSkill()` - Convenience function that exports and triggers download
- `buildFileStructureFromSnippets()` - Rebuilds file structure from snippet tags
- `buildFileStructureFromTools()` - Rebuilds file structure from tool tags
- `exportToolsToScripts()` - Exports tools without file tags to scripts folder
- `generateSkillMd()` - Creates SKILL.md with frontmatter

## Usage

### From Skill Detail Page

1. Navigate to any skill detail page
2. Click the "Export to Anthropic" button
3. A ZIP file will be downloaded with the skill name

### Export Format

The exported ZIP file follows this structure:

```
skill-name/
├── SKILL.md                 # Skill metadata with frontmatter
├── file1.md                 # Reconstructed from snippets with file: tags
├── file2.py                 # Reconstructed from tools with file: tags
└── scripts/                 # Tools without file: tags
    ├── tool1.py
    └── tool2.sh
```

### SKILL.md Format

```markdown
---
name: skill-name
description: "Skill description"
---

# Additional content from snippets without file: tags
```

## File Reconstruction Logic

### Snippets with `file:` tags
- Tag format: `file:path/to/file.ext`
- Multiple snippets with the same file path are concatenated
- Original file structure is preserved

### Tools with `file:` tags
- Tag format: `file:path/to/file.ext`
- Multiple tools with the same file path are concatenated
- Tool module content is fetched from the API

### Snippets without `file:` tags
- Appended to SKILL.md content
- Separated by double newlines

### Tools without `file:` tags
- Exported to `scripts/` folder
- File extension determined by programming language:
  - Python → `.py`
  - Bash → `.sh`
  - Other → `.txt`

## Integration

The exporter integrates with:
- **SkillDetailPage** - Provides the export button and handler
- **toolsApi.getModule()** - Fetches tool module content
- **JSZip** - Creates ZIP files
- **Skill, Tool, Snippet types** - Uses existing type definitions

---

# Technical Details

## API Integration

The module uses the following Skillberry Store APIs:

- `POST /api/tools/` - Create tools (import)
- `POST /api/snippets/` - Create snippets (import)
- `POST /api/skills/` - Create skill (import)
- `GET /api/tools/{name}/module` - Fetch tool module content (export)

All operations are performed client-side with no backend changes required.

## Dependencies

- `jszip` - For ZIP file creation and extraction
- `@patternfly/react-core` - UI components
- `@/types` - Type definitions for Skill, Tool, Snippet
- `@/services/api` - API integration
- Existing Skillberry Store APIs

## File Path Tags

Both import and export use `file:` tags to preserve file structure:
- Format: `file:path/to/file.ext`
- First tag starting with `file:` is used
- Path is extracted by removing the `file:` prefix
- Multiple items with same path are grouped together

### Content Merging
When multiple snippets or tools share the same file path:
- Content is concatenated with double newlines (`\n\n`)
- Order is preserved from the original arrays

## Error Handling

### Import
- Network errors during GitHub fetch are caught and reported
- ZIP extraction errors are handled gracefully
- Individual file parsing errors don't stop the entire import
- Failed tool/snippet creation is logged but doesn't fail the import
- Detailed error messages are shown to the user

### Export
- Missing tool modules are handled gracefully
- Export errors are caught and displayed to user
- Invalid file paths are logged but don't stop export
- Empty content is allowed

---

# Future Enhancements

Potential improvements for both import and export:

## Import
- Support for more programming languages (JavaScript, Go, etc.)
- Better function signature parsing
- Support for classes and methods
- Batch import of multiple skills
- Import history and rollback
- Preview before import

## Export
- Preview before export
- Custom export options (include/exclude certain files)
- Export multiple skills at once
- Validate exported structure
- Support for more file types

## Round-trip
- Ensure import → export → import produces identical results
- Automated testing of round-trip conversions
- Validation of file structure preservation