# Anthropic Test Resources

This directory contains test resources for the Anthropic skill import/export functionality.

## Structure

```
anthropic/
├── README.md (this file)
└── sample_skill/
    ├── SKILL.md              # Skill metadata with frontmatter
    ├── README.md             # Additional documentation
    └── scripts/
        ├── utils.py          # Python functions for testing
        └── scripts.sh        # Bash functions for testing
```

## Sample Skill

The `sample_skill` directory contains a complete Anthropic skill structure used for testing:

- **SKILL.md**: Contains skill metadata in YAML frontmatter format
- **README.md**: Additional documentation that gets imported as snippets
- **scripts/utils.py**: Python file with two functions (`add_numbers`, `multiply_numbers`)
- **scripts/scripts.sh**: Bash file with two functions (`greet_user`, `sum_args`)

## Usage in Tests

These resources are used by:

1. **Unit tests** (`tests/tools/test_anthropic_parsers.py`):
   - Test individual parser functions
   - Verify text and code parsing logic
   - Check tag extraction and metadata handling

2. **E2E tests** (`tests/e2e/test_anthropic_api.py`):
   - Test complete import/export workflows
   - Verify API endpoints
   - Test roundtrip consistency (import → export → import)

## Test Coverage

The tests cover:

- ✅ Importing from ZIP files
- ✅ Importing with different snippet modes (file/paragraph)
- ✅ Exporting to Anthropic ZIP format
- ✅ Roundtrip consistency
- ✅ File tag preservation
- ✅ Python function parsing
- ✅ Bash function parsing
- ✅ Text file parsing
- ✅ SKILL.md frontmatter handling
- ✅ Error handling for invalid inputs