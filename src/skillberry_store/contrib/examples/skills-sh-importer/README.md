# Skills.sh Import Tool

Automated tool to download and import skills from [skills.sh](https://skills.sh) into skillberry-store.

## Overview

This tool implements a 6-phase process to:
1. Extract all repository metadata from skills.sh (sorted by popularity)
2. Clone repositories iteratively until finding N skill subfolders with SKILL.md
3. Discover skills in /skills/ folders
4. Import skills via Anthropic API (handles transformation automatically)
5. Validate imports
6. Generate comprehensive reports

**Key Feature:** A "skill" is defined as a subfolder in `/skills/` directory containing a `SKILL.md` file. The tool clones repositories from skills.sh (by popularity) until it finds N such skills.

## Prerequisites

### System Requirements
- Python 3.8+
- Git installed and in PATH
- Network access to GitHub and skills.sh
- Skillberry-store running locally (for API imports)

### Python Dependencies
```bash
pip install requests
```

## Usage

### Basic Usage
```bash
# Import top 10 skills (default)
python3 download_and_import_skills.py

# Clone only (no discovery or import)
python3 download_and_import_skills.py --clone-only
```

### Advanced Usage
```bash
# Clone repos until finding 20 skills
python3 download_and_import_skills.py --max-skills 20

# Clone repos until finding 50 skills, without importing
python3 download_and_import_skills.py --max-skills 50 --clone-only

# Use custom SBS URL
python3 download_and_import_skills.py --sbs-url http://localhost:9000

# Full configuration with custom output directory (must be absolute)
python3 download_and_import_skills.py \
    --max-skills 15 \
    --sbs-url http://localhost:8000 \
    --clone-depth 1 \
    --timeout 60 \
    --output-dir /absolute/path/to/my-repos
```

**Note:** `--max-skills` limits the number of actual skills found (subfolders with SKILL.md in /skills/ directories). The tool clones repositories one at a time until reaching or exceeding this target. Repositories without /skills/ folders are skipped. The final count may exceed the target if the last repository cloned contains multiple skills.

### CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--max-skills` | 10 | Target number of skills (may exceed if last repo has multiple skills) |
| `--sbs-url` | http://localhost:8000 | Skillberry Store URL |
| `--skills-url` | https://skills.sh | Skills.sh marketplace URL |
| `--clone-depth` | 1 | Git clone depth (1 = shallow clone) |
| `--timeout` | 30 | API request timeout in seconds |
| `--output-dir` | `<temp>/skills-sh-repos` | Output directory (must be absolute path if specified) |
| `--clone-only` | false | Only clone repositories, skip phases 3-7 |

**Note on --output-dir:**
- **Default**: Uses system temp directory (e.g., `/tmp/skills-sh-repos` on Linux, `C:\Users\<user>\AppData\Local\Temp\skills-sh-repos` on Windows)
- **Custom**: Must provide an absolute path (e.g., `/home/user/my-skills` or `C:\skills`)
- **Relative paths are not allowed** to avoid confusion about working directory

## Clone-Only Mode

Use `--clone-only` to only clone repositories without discovering or importing skills. This is useful for:

- **Quick repository collection**: Clone repos until finding N skills for later analysis
- **Offline analysis**: Clone repos when you have good internet, analyze later
- **Manual review**: Inspect repositories before deciding what to import
- **Batch operations**: Clone repos for many skills without API overhead

### Example Usage

```bash
# Clone repos until finding 50 skills for later analysis
python3 download_and_import_skills.py --max-skills 50 --clone-only

# Clone to custom directory (must be absolute path)
python3 download_and_import_skills.py --clone-only --output-dir /home/user/my-skills-repos

# Clone with full history (not shallow)
python3 download_and_import_skills.py --clone-only --clone-depth 0
```

### Output in Clone-Only Mode

When using `--clone-only`, the script will:
1. ✅ Execute Phase 1 (Extract metadata)
2. ✅ Execute Phase 2 (Clone repositories)
3. ⏭️ Skip Phases 3-6 (Discovery, Import, Validate, Report)

**Files created in clone-only mode:**
- `clone-results.json` - Clone status (includes skill counts per repo)
- `<temp>/skills-sh-repos/` or custom directory - Cloned repositories (only those with skills)
- `import-skills.log` - Execution log

**Additional files created in full mode (without --clone-only):**
- `discovered-skills.json` - All discovered skills with SKILL.md content
- `import-results.json` - Import status for each skill
- `validation-report.json` - Validation results
- `final-report.json` - Complete execution summary

## Process Flow

### Phase 1: Extract Repository Metadata from skills.sh
- Fetches skills.sh homepage
- Parses HTML to extract ALL repository metadata
- Sorts by popularity (install count)
- **No limiting at this phase** - Phase 2 will clone until N skills found

**Example:** Extracts all ~500 repositories from skills.sh, sorted by popularity.

### Phase 2: Clone Repositories Until N Skills Found
- Clones repositories one at a time in popularity order
- After each clone, checks for `/skills/` directory
- Counts subfolders in `/skills/` that contain `SKILL.md`
- Accumulates skill count until reaching `--max-skills` target
- **Skips repositories without `/skills/` folder**
- Stops cloning once target is reached

**Skill Definition:** A skill = a subfolder in `/skills/` directory containing `SKILL.md` file

**Output:**
- `clone-results.json` - Contains:
  - `cloned_repos`: Repos with skills (includes skill count per repo)
  - `skipped_repos`: Repos without /skills/ folder
  - `failed_repos`: Repos that failed to clone
  - `summary`: Statistics
- `skills-sh-repos/` - Cloned repositories

**Example:** `--max-skills 10` clones repos until finding 10 skill subfolders. This might require cloning 5-15 repositories depending on how many skills each contains.

### Phase 3: Discover Skills in /skills/ Folders
- Scans cloned repositories for `/skills/` directory
- Iterates through all subfolders
- Checks each subfolder for `SKILL.md` file
- Extracts SKILL.md content and metadata

**Output:**
- `discovered-skills.json` - All discovered skills with their SKILL.md content

**Example Output:**
```json
{
  "repo_source": "vercel/ai",
  "repo_name": "vercel__ai",
  "skill_folder": "ai-sdk",
  "skill_path": "skills/ai-sdk",
  "skill_md_path": "skills/ai-sdk/SKILL.md",
  "skill_name": "ai-sdk",
  "content": "... full SKILL.md content ...",
  "full_path": "/path/to/repo/skills/ai-sdk"
}
```

### Phase 4: Import via Anthropic API
- Uses `/skills/import-anthropic` endpoint with folder source
- API automatically handles:
  - Parsing SKILL.md for metadata
  - Extracting tools from code files
  - Creating snippets from text files
  - Creating skill with proper schema
- Imports each skill folder separately

**Output:**
- `import-results.json` - Import status for each skill

### Phase 5: Validation
- Verifies API accessibility
- Checks imported skill count
- Validates data integrity

**Output:**
- `validation-report.json` - Validation results

### Phase 6: Documentation
- Generates comprehensive final report
- Summarizes all phases
- Provides success metrics

**Output:**
- `final-report.json` - Complete execution summary
- `import-skills.log` - Detailed execution log

## Output Files

After execution, the following files are created:

```
skill-scale-issue-analysis/
├── download_and_import_skills.py    # Main script
├── import-skills-from-skills-sh-plan.md  # Implementation plan
├── clone-results.json               # Repository clone results
├── discovered-skills.json           # Discovered skills
├── import-results.json              # Import results
├── validation-report.json           # Validation results
├── final-report.json                # Final summary report
├── import-skills.log                # Detailed execution log
└── skills-sh-repos/                 # Cloned repositories
    ├── vercel__ai/
    ├── anthropics__skills/
    └── ...
```

## Example Output

### Successful Execution
```
╔═══════════════════════════════════════════════════════════╗
║  Skills.sh Importer for Skillberry Store                  ║
║  6-Phase Import Process                                   ║
╚═══════════════════════════════════════════════════════════╝

============================================================
PHASE 1: Extracting repository URLs from skills.sh
============================================================
Fetching https://skills.sh/...
Received 1234567 bytes
Extracted 500 repositories
Sorted by popularity

Top 10 most popular repositories:
  1. nextjs (vercel/next.js) - 1,234,567 installs
  2. ai-sdk (vercel/ai) - 234,567 installs
  ...

============================================================
PHASE 2: Cloning repositories to find skills
============================================================
Target: 10 skills
Strategy: Clone repos by popularity, count /skills/ subfolders with SKILL.md

[Repo 1] Processing vercel/ai...
  ✓ Successfully cloned to skills-sh-repos/vercel__ai
  ✓ Found 3 skill(s) in /skills/ folder
  Progress: 3/10 skills found

[Repo 2] Processing anthropics/skills...
  ✓ Successfully cloned
  ✓ Found 5 skill(s) in /skills/ folder
  Progress: 8/10 skills found

[Repo 3] Processing nextlevelbuilder/ui-ux-pro-max-skill...
  ⊘ No /skills/ folder or no SKILL.md files found - skipping

[Repo 4] Processing someuser/another-repo...
  ✓ Successfully cloned
  ✓ Found 2 skill(s) in /skills/ folder
  Progress: 10/10 skills found

✓ Reached target of 10 skills!

Clone Summary:
  Repositories processed: 4
  Repositories with skills: 3
  Repositories skipped (no skills): 1
  Total skills found: 10/10

============================================================
PHASE 3: Discovering skills in /skills/ folders
============================================================
Scanning vercel__ai...
  Expected skills: 3
  ✓ Found skill: ai-sdk
  ✓ Found skill: streaming
  ✓ Found skill: tools
  Total: 3 skill(s) found

Discovery Summary:
  Total skills discovered: 45

============================================================
PHASE 4: Importing skills via Anthropic API
============================================================
[1/45] Importing vercel__ai__ai-sdk...
  ✓ Successfully imported

Import Summary:
  Total: 25
  Successful: 23
  Failed: 2

============================================================
PHASE 5: Validating imports
============================================================
  ✓ API accessible
  ✓ Found 42 skills in store

============================================================
PHASE 6: Generating final report
============================================================
FINAL REPORT
============================================================
Repos cloned: 3
Skills discovered: 25
Skills imported: 23
Import failures: 2
Validation: ✓ PASSED
============================================================

Total execution time: 123.45 seconds
```

## Troubleshooting

### Git Clone Failures
**Problem:** Repositories fail to clone
**Solution:**
- Check network connectivity
- Verify GitHub is accessible
- Try increasing timeout
- Check if repo is private (requires authentication)

### API Import Failures
**Problem:** Skills fail to import via API
**Solution:**
- Ensure skillberry-store is running: `http://localhost:8000`
- Check API logs for errors
- Verify skill schema is valid
- Try importing manually to debug

### No Skills Discovered
**Problem:** No skills found in cloned repositories
**Solution:**
- Check repository structure manually
- Verify search patterns match repo layout
- Look for skills in non-standard locations
- Adjust discovery logic if needed

### Validation Failures
**Problem:** Validation reports failures
**Solution:**
- Check API is accessible
- Verify imported skills exist
- Review validation-report.json for details
- Check skillberry-store logs

## Advanced Configuration

### Environment Variables
```bash
# Override SBS URL
export SKILLBERRY_SBS_URL=http://localhost:9000

# Run script
python3 download_and_import_skills.py
```

### Custom Skill Discovery
Edit the `discover_skills()` method to add custom search patterns:
```python
# Add custom directory
search_dirs.append(repo_path / 'custom' / 'skills')

# Add custom file extension
for ext in ['.md', '.py', '.js', '.ts', '.json', '.yaml']:
    skill_files.extend(search_dir.glob(f'*{ext}'))
```

### Retry Failed Imports
```bash
# Extract failed skills from import-results.json
# Re-run import for specific skills
python3 -c "
import json
import requests

with open('import-results.json') as f:
    data = json.load(f)
    
failed = [r for r in data['results'] if r['status'] != 'success']
print(f'Found {len(failed)} failed imports')
"
```

## Performance Tips

1. **Use shallow clones** (default): `--clone-depth 1`
2. **Start small**: Test with `--max-skills 5` first
3. **Increase timeout** for slow networks: `--timeout 60`
4. **Run in background**: `nohup python3 download_and_import_skills.py &`
5. **Monitor progress**: `tail -f import-skills.log`

## Integration with Skillberry Store

The imported skills are immediately available via:

```bash
# List all skills
curl http://localhost:8000/skills/

# Get specific skill
curl http://localhost:8000/skills/{uuid}

# Search skills
curl "http://localhost:8000/skills/search?query=ai"
```

## Contributing

To extend this tool:

1. Add new phases in the `SkillsImporter` class
2. Update the `run()` method to include new phases
3. Add CLI arguments as needed
4. Update documentation

## License

Same as skillberry-store project.

## Support

For issues or questions:
1. Check the `import-skills.log` file
2. Review `final-report.json` for summary
3. Check individual phase output files
4. Consult the implementation plan: `import-skills-from-skills-sh-plan.md`