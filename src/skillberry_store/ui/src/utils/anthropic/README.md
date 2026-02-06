# Anthropic Skill Importer

This module provides functionality to import Anthropic skills from GitHub repositories or ZIP files into the Skillberry Store.

## Overview

The Anthropic Skill Importer allows users to:
- Import skills from GitHub URLs (e.g., https://github.com/anthropics/skills/tree/main/skills/pptx)
- Import skills from ZIP files
- Automatically parse text files into snippets
- Automatically parse Python and Bash code files into tools
- Create a skill that groups all imported tools and snippets

## Architecture

The implementation consists of three main files:

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

### 3. `AnthropicSkillImporter.tsx`
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
- **Tags**: Automatically tagged with file extension, directory names, filename, and 'anthropic'

### Code Files
- **Supported languages**: Python (.py), Bash (.sh, .bash)
- **Processing**: Each function becomes a separate tool
- **Metadata extraction**:
  - Python: Docstrings for description, parameters, and return values
  - Bash: Comments above function for description
- **Tags**: Automatically tagged with language, directory names, filename, and 'anthropic'

### Ignored Files
- Binary files (images, executables, etc.)
- Unsupported script types (JavaScript, Ruby, etc.)
- These are logged but don't cause import failure

## API Integration

The importer uses the following Skillberry Store APIs:

- `POST /api/tools/` - Create tools
- `POST /api/snippets/` - Create snippets
- `POST /api/skills/` - Create skill

All operations are performed client-side with no backend changes required.

## Error Handling

- Network errors during GitHub fetch are caught and reported
- ZIP extraction errors are handled gracefully
- Individual file parsing errors don't stop the entire import
- Failed tool/snippet creation is logged but doesn't fail the import
- Detailed error messages are shown to the user

## Dependencies

- `jszip` - For ZIP file extraction
- `@patternfly/react-core` - UI components
- Existing Skillberry Store APIs

## Future Enhancements

Potential improvements:
- Support for more programming languages (JavaScript, Go, etc.)
- Better function signature parsing
- Support for classes and methods
- Batch import of multiple skills
- Import history and rollback
- Preview before import