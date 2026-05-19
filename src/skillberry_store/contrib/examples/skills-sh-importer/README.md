# Skills.sh Import Tool

Automated tool to download and import skills from [skills.sh](https://skills.sh) into skillberry-store with built-in benchmarking.

## Overview

This tool implements a 6-phase process to:
1. Extract all repository metadata from skills.sh (sorted by popularity)
2. Clone repositories iteratively until finding N skill subfolders with SKILL.md
3. Discover skills in /skills/ folders
4. Import skills via Anthropic API (handles transformation automatically) **with automatic benchmarking**
5. Validate imports
6. Generate comprehensive reports with benchmark statistics

**Key Features:**
- A "skill" is defined as a subfolder in `/skills/` directory containing a `SKILL.md` file
- The tool clones repositories from skills.sh (by popularity) until it finds N such skills
- **Automatic benchmarking** of all import operations (timing, size, file counts, throughput)
- **Clone-only mode** for downloading skills without importing (Phases 1-2)
- **Import-only mode** for importing downloaed skills (Phases 3-6) - can be used for repeated benchmarking over the same skill set

## Prerequisites

### System Requirements
- Python 3.8+
- Git installed and in PATH
- Network access to GitHub and skills.sh
- Skillberry-store running locally (for API imports)

### Python Dependencies

Install the required dependencies using the provided requirements.txt file:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage
```bash
# Import top 10 skills (default) with automatic benchmarking
python3 download_and_import_skills.py

# Clone only (no discovery or import)
python3 download_and_import_skills.py --clone-only

# Import only (use existing downloaded skills, benchmark again)
python3 download_and_import_skills.py --import-only
```

### Advanced Usage
```bash
# Clone repos until finding 20 skills
python3 download_and_import_skills.py --max-skills 20

# Clone repos until finding 50 skills, without importing
python3 download_and_import_skills.py --max-skills 50 --clone-only

# Import only first 10 skills from existing downloads (for benchmarking)
python3 download_and_import_skills.py --import-only --max-skills 10

# Use custom SBS URL
python3 download_and_import_skills.py --sbs-url http://localhost:9000

# Full configuration with custom directories
python3 download_and_import_skills.py \
    --max-skills 15 \
    --sbs-url http://localhost:8000 \
    --clone-depth 1 \
    --timeout 60 \
    --skills-dir /absolute/path/to/my-repos \
    --output-dir ./results
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
| `--skills-dir` | `<temp>/skills-sh-repos` | Directory for cloned skill repositories (absolute or relative path) |
| `--output-dir` | `.` (current directory) | Directory for output files (absolute or relative path). A timestamped subdirectory is created for each run |
| `--clone-only` | false | Only clone repositories, skip phases 3-6 |
| `--import-only` | false | Skip phases 1-2, use existing skills from skills-dir. If --max-skills specified, import up to that limit; otherwise import all |

**Note on directories:**
- **--skills-dir**: Where skill repositories are cloned
  - **Default**: System temp directory (e.g., `/tmp/skills-sh-repos` on Linux, `C:\Users\<user>\AppData\Local\Temp\skills-sh-repos` on Windows)
  - **Custom**: Can be absolute (e.g., `/home/user/my-skills`) or relative (e.g., `./my-skills`)
- **--output-dir**: Where result files are saved
  - **Default**: Current working directory
  - **Custom**: Can be absolute or relative
  - **Timestamped subdirectories**: Each run creates a subdirectory named `YYYYMMDD_HHMMSS` (e.g., `20260519_180804`)

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

# Clone to custom directory
python3 download_and_import_skills.py --clone-only --skills-dir /home/user/my-skills-repos

# Clone with full history (not shallow)
python3 download_and_import_skills.py --clone-only --clone-depth 0
```

### Output in Clone-Only Mode

When using `--clone-only`, the script will:
1. ✅ Execute Phase 1 (Extract metadata)
2. ✅ Execute Phase 2 (Clone repositories)
3. ⏭️ Skip Phases 3-6 (Discovery, Import, Validate, Report)

**Files created in clone-only mode:**
- `<output-dir>/<timestamp>/clone-results.json` - Clone status (includes skill counts per repo)
- `<output-dir>/<timestamp>/import-skills.log` - Execution log
- `<skills-dir>/` - Cloned repositories (only those with skills)

## Import-Only Mode

Use `--import-only` to skip cloning and use existing downloaded skills. This is ideal for:

- **Repeated benchmarking**: Test import performance multiple times on the same skill set
- **Performance optimization**: Benchmark after making changes to the import process
- **Selective importing**: Import a subset of previously downloaded skills
- **Development/testing**: Quickly test import logic without re-downloading

### Example Usage

```bash
# Import all skills from existing downloads (with benchmarking)
python3 download_and_import_skills.py --import-only

# Import only first 10 skills from existing downloads
python3 download_and_import_skills.py --import-only --max-skills 10

# Import from custom skills directory
python3 download_and_import_skills.py --import-only --skills-dir /home/user/my-skills-repos

# Benchmark with different SBS instance and save results to custom output directory
python3 download_and_import_skills.py --import-only --sbs-url http://localhost:9000 --output-dir ./benchmark-results
```

### Output in Import-Only Mode

When using `--import-only`, the script will:
1. ⏭️ Skip Phase 1 (Extract metadata)
2. ⏭️ Skip Phase 2 (Clone repositories)
3. ✅ Execute Phase 3 (Discover skills in existing repos)
4. ✅ Execute Phase 4 (Import with benchmarking)
5. ✅ Execute Phase 5 (Validate)
6. ✅ Execute Phase 6 (Report with benchmark statistics)

**Additional files created in full mode (without --clone-only or --import-only):**
All files are saved in `<output-dir>/<timestamp>/`:
- `discovered-skills.json` - All discovered skills with SKILL.md content
- `import-results.json` - Import status for each skill
- `validation-report.json` - Validation results
- `final-report.json` - Complete execution summary
- `benchmark-results.json` - Detailed benchmark data and statistics
- `import-skills.log` - Detailed execution log

## Process Flow

### Phase 1: Extract Repository Metadata from skills.sh
- Fetches skills.sh homepage
- Parses HTML to extract repository sources
- Prepares repository records for cloning
- **No limiting at this phase** - Phase 2 will clone until N skills found

**Example:** Extracts repository records from skills.sh for Phase 2 cloning.

### Phase 2: Clone Repositories Until N Skills Found
- Clones repositories one at a time from the extracted repository list
- After each clone, checks for `/skills/` directory
- Counts subfolders in `/skills/` that contain `SKILL.md`
- Accumulates skill count until reaching `--max-skills` target
- **Skips repositories without `/skills/` folder**
- Stops cloning once target is reached

**Skill Definition:** A skill = a subfolder in `/skills/` directory containing `SKILL.md` file

**Output:**
- `clone-results.json` - Contains:
  - `cloned_repos`: Repositories with skills
  - `skipped_repos`: Repositories without `/skills/` folder
  - `failed_repos`: Repositories that failed to clone
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

### Phase 4: Import via Anthropic API (with Benchmarking)
- Uses `/skills/import-anthropic` endpoint with folder source
- API automatically handles:
  - Parsing SKILL.md for metadata
  - Extracting tools from code files
  - Creating snippets from text files
  - Creating skill with proper schema
- Imports each skill folder separately
- **Automatically collects benchmark data for each successful import:**
  - Import duration (seconds)
  - Skill size (KB)
  - File count
  - Tool count (Python scripts in /scripts/)
  - Snippet count (all .md files including SKILL.md)

**Output:**
- `import-results.json` - Import status for each skill
- `benchmark-results.json` - Detailed benchmark data for all successful imports

### Phase 5: Validation
- Verifies API accessibility
- Checks the number of skills returned by the API
- Validates data integrity

**Output:**
- `validation-report.json` - Validation results

### Phase 6: Documentation and Benchmarking Report
- Generates comprehensive final report
- Summarizes all phases
- Provides success metrics
- **Calculates and displays benchmark statistics:**
  - Total import time
  - Average, median, and standard deviation of import times
  - Fastest and slowest imports with skill details
  - Import throughput (KB/sec, skills/sec, objects/sec)

**Output:**
- `final-report.json` - Complete execution summary with benchmark statistics
- `benchmark-results.json` - Detailed benchmark data for each import
- `import-skills.log` - Detailed execution log

## Output Files

After execution, files are organized into two directories:

### Skills Directory (--skills-dir)
Contains cloned skill repositories:
```
/tmp/skills-sh-repos/                # Default location on Linux
├── vercel__ai/
│   └── skills/
│       ├── ai-sdk/
│       ├── streaming/
│       └── ...
├── anthropics__skills/
│   └── skills/
│       └── ...
└── ...
```

### Output Directory (--output-dir)
Contains timestamped subdirectories with result files:
```
./                                   # Default: current directory
├── 20260519_180804/                 # Timestamped run folder
│   ├── clone-results.json           # Repository clone results
│   ├── discovered-skills.json       # Discovered skills
│   ├── import-results.json          # Import results
│   ├── benchmark-results.json       # Benchmark data and statistics
│   ├── validation-report.json       # Validation results
│   ├── final-report.json            # Final summary report with benchmarks
│   └── import-skills.log            # Detailed execution log
├── 20260519_181205/                 # Another run
│   └── ...
└── ...
```

## Example Output

### Successful Execution
```
╔═══════════════════════════════════════════════════════════╗
║  Skills.sh Importer for Skillberry Store                 ║
║  6-Phase Import Process with Benchmarking                ║
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
  Total skills discovered: 10

============================================================
PHASE 4: Importing skills via Anthropic API
============================================================
[1/10] Importing ai-sdk...
  Folder: /tmp/skills-sh-repos/vercel__ai/skills/ai-sdk
  ✓ Successfully imported in 1.23s
    Skill: ai-sdk
    Tools: 3
    Snippets: 2


## Benchmarking

The tool automatically collects benchmark data during Phase 4 (import operations) for all successful imports. This feature is always active and requires no configuration.

### What is Benchmarked

For each successful skill import, the following metrics are collected:
- **Import duration**: Time taken to import the skill (seconds)
- **Skill size**: Total size of all files in the skill folder (KB)
- **File count**: Total number of files in the skill folder
- **Tool count**: Number of Python scripts in the `/scripts/` subfolder
- **Snippet count**: Number of `.md` files (including SKILL.md)

### Benchmark Statistics

After all imports complete, Phase 6 calculates and reports:
- **Total import time**: Sum of all import durations
- **Average import time**: Mean import duration
- **Median import time**: Median import duration
- **Standard deviation**: Variability in import times
- **Fastest import**: Minimum import time with skill details
- **Slowest import**: Maximum import time with skill details
- **Import throughput**:
  - KB/sec: Total size divided by total time
  - Skills/sec: Total skills divided by total time
  - Objects/sec: (Skills + Tools + Snippets) divided by total time

### Benchmark Output Files

Benchmark data is saved to the timestamped output directory:
- `<output-dir>/<timestamp>/benchmark-results.json`: Detailed data for each import plus statistics
- `<output-dir>/<timestamp>/final-report.json`: Includes benchmark statistics in the report

### Use Cases

**Performance Testing:**
```bash
# Benchmark import performance on 20 skills
python3 download_and_import_skills.py --max-skills 20

# Review results in timestamped output directory
cat ./20260519_180804/benchmark-results.json
```

**Repeated Benchmarking:**
```bash
# First, download skills
python3 download_and_import_skills.py --max-skills 50 --clone-only

# Then benchmark multiple times (each creates a new timestamped directory)
python3 download_and_import_skills.py --import-only --max-skills 10
python3 download_and_import_skills.py --import-only --max-skills 20
python3 download_and_import_skills.py --import-only --max-skills 50

# Results are in separate timestamped directories:
# ./20260519_180804/benchmark-results.json
# ./20260519_180912/benchmark-results.json
# ./20260519_181023/benchmark-results.json
```

**Optimization Testing:**
```bash
# Benchmark before optimization
python3 download_and_import_skills.py --import-only --output-dir ./benchmarks

# Make changes to skillberry-store import logic

# Benchmark after optimization
python3 download_and_import_skills.py --import-only --output-dir ./benchmarks

# Compare benchmark results from timestamped directories:
# ./benchmarks/20260519_180804/benchmark-results.json (before)
# ./benchmarks/20260519_181205/benchmark-results.json (after)
```

[2/10] Importing streaming...
  Folder: /tmp/skills-sh-repos/vercel__ai/skills/streaming
  ✓ Successfully imported in 0.87s
    Skill: streaming
    Tools: 2
    Snippets: 1

Import Summary:
  Total: 10
  Successful: 10
  Failed: 0

============================================================
PHASE 5: Validating imports
============================================================
  ✓ API accessible
  ✓ Found 10 skills in store

============================================================
PHASE 6: Generating final report
============================================================
FINAL REPORT
============================================================
Repositories extracted: 500
Unique repos cloned: 3
Repositories cloned: 3
Skills discovered in repos: 10
Skills imported: 10
Import failures: 0
Validation: ✓ PASSED
============================================================

============================================================
BENCHMARK RESULTS
============================================================
Total import time: 12.45 seconds
Average import time: 1.245 seconds
Median import time: 1.180 seconds
Std deviation: 0.342 seconds

Fastest import: 0.87s - streaming
  (125.5 KB, 8 files, 2 tools, 1 snippets)
Slowest import: 2.15s - pdf-processing
  (450.2 KB, 25 files, 8 tools, 3 snippets)

Import throughput:
  - 198.4 KB/sec
  - 0.80 skills/sec
  - 4.82 objects/sec (60 total: 10 skills + 35 tools + 15 snippets)
============================================================

Full report saved to: final-report.json

Total execution time: 45.67 seconds
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
