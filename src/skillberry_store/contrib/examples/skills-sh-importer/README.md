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
- **Clone mode** clones repositories from skills.sh until it finds N such skills (up to ~9,700 repos)
- **Sitemap mode** downloads skills directly from the skills.sh API without git (up to ~20,000 skills)
- **Automatic benchmarking** of all import operations (timing, size, file counts, throughput)
- **Clone-only mode** for downloading skills without importing (Phases 1-2)
- **Sitemap-only mode** for downloading ~20K skills via HTTP without any git clone
- **Import-only mode** for importing downloaded skills (Phases 3-6) — useful for repeated benchmarking

## How skills.sh exposes its catalog

skills.sh publishes two public XML sitemaps that the tool uses to discover repositories and skills:

| Sitemap | Contents | Used by |
|---------|----------|---------|
| `sitemap-owners.xml` | ~9,700 `owner/repo` entries — every GitHub repository skills.sh knows about | Clone mode (Phase 1) |
| `sitemap-skills-1.xml` + `sitemap-skills-2.xml` | ~20,000 individual `owner/repo/slug` skill entries — skills pre-snapshotted by skills.sh | Sitemap mode |

The skill sitemaps are a **subset** of the owners sitemap: the ~20,000 snapshotted skills come from 2,462 of the 9,700 repos. The remaining ~7,200 repos are only reachable by cloning.

**Estimated total coverage:**

| Mode | Skills accessible | Requires git |
|------|-------------------|--------------|
| `--sitemap-only` | ~20,000 (guaranteed) | No |
| Clone (default) | ~38,000–79,000 (estimated) | Yes |

## Prerequisites

### System Requirements
- Python 3.8+
- Git installed and in PATH (not required for `--sitemap-only`)
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

# Clone only — download repos without importing
python3 download_and_import_skills.py --clone-only

# Sitemap only — download ~20K skills via HTTP (no git required)
python3 download_and_import_skills.py --sitemap-only --skills-dir ./skills

# Import only — use existing downloaded skills, skip phases 1-2
python3 download_and_import_skills.py --import-only
```

### Advanced Usage
```bash
# Clone repos until finding 1000 skills
python3 download_and_import_skills.py --max-skills 1000

# Clone repos until finding 50 skills, without importing
python3 download_and_import_skills.py --max-skills 50 --clone-only

# Download all ~20K sitemap skills to a custom directory
python3 download_and_import_skills.py --sitemap-only --skills-dir ./skills2

# Download first 500 sitemap skills, then import
python3 download_and_import_skills.py --sitemap-only --max-skills 500 --skills-dir ./skills2

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

**Note on `--max-skills`:** limits the number of actual skills found (subfolders with SKILL.md). In clone mode the tool stops cloning once the target is reached; the final count may slightly exceed the target if the last cloned repository contains multiple skills. In sitemap mode the list is truncated exactly before downloading begins.

### CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--max-skills` | 10 (clone/full mode), unlimited (import-only / sitemap-only) | Target number of skills |
| `--sbs-url` | `http://localhost:8000` | Skillberry Store URL |
| `--skills-url` | `https://skills.sh` | Skills.sh URL |
| `--clone-depth` | `1` | Git clone depth (1 = shallow clone) |
| `--timeout` | `30` | API request timeout in seconds |
| `--skills-dir` | `<temp>/skills-sh-repos` | Directory for skill repositories (absolute or relative) |
| `--output-dir` | `.` (current directory) | Directory for output files. A timestamped subdirectory is created per run |
| `--clone-only` | false | Run only Phases 1-2 (extract + clone); skip discovery and import |
| `--sitemap-only` | false | Download ~20K skills via `/api/download` (no git). Replaces Phases 1-2 |
| `--import-only` | false | Skip Phases 1-2; use existing skills from `--skills-dir` |

`--clone-only`, `--sitemap-only`, and `--import-only` are mutually exclusive.

**Note on directories:**
- **--skills-dir**: Where skill repositories are stored
  - **Default**: System temp directory (e.g., `/tmp/skills-sh-repos` on Linux)
  - **Custom**: Absolute (e.g., `/home/user/my-skills`) or relative (e.g., `./my-skills`)
- **--output-dir**: Where result files (JSON, logs) are saved
  - **Default**: Current working directory
  - Each run creates a subdirectory named `YYYYMMDD_HHMMSS` (e.g., `20260702_001751`)

## Clone-Only Mode

Use `--clone-only` to clone repositories without discovering or importing skills. Useful for:

- **Offline analysis**: Clone repos with good internet, analyze later
- **Manual review**: Inspect repositories before deciding what to import
- **Batch operations**: Clone repos for many skills without API overhead

### Example Usage

```bash
# Clone repos until finding 1000 skills (uses ~9,700-repo catalog from sitemap-owners.xml)
python3 download_and_import_skills.py --max-skills 1000 --clone-only --skills-dir ./skills2

# Clone to custom directory with full history
python3 download_and_import_skills.py --clone-only --clone-depth 0 --skills-dir ./skills2
```

### Output in Clone-Only Mode

When using `--clone-only`, the script will:
1. ✅ Execute Phase 1 (Extract repo list from `sitemap-owners.xml`)
2. ✅ Execute Phase 2 (Clone repositories until N skills found)
3. ⏭️ Skip Phases 3-6 (Discovery, Import, Validate, Report)

**Files created:**
- `<output-dir>/<timestamp>/clone-results.json` — Clone status with skill counts per repo
- `<output-dir>/<timestamp>/import-skills.log` — Execution log
- `<skills-dir>/` — Cloned repositories (only those containing skills)

## Sitemap-Only Mode

Use `--sitemap-only` to download skills directly from the skills.sh `/api/download` endpoint, without cloning any git repositories. This covers all ~20,000 skills pre-snapshotted by skills.sh.

### How it works

1. Fetches `sitemap-skills-1.xml` and `sitemap-skills-2.xml` — the complete list of ~20,000 `owner/repo/slug` triples
2. For each skill, calls `GET https://skills.sh/api/download/{owner}/{repo}/{slug}`, which returns a JSON snapshot of the skill's files
3. Writes the files to `<skills-dir>/<owner>__<repo>/skills/<slug>/` — the same layout a git clone produces
4. Hands off to Phase 3 (discover), which works identically for both clone and sitemap modes

Re-runs are **idempotent**: already-downloaded skills are skipped.

### Example Usage

```bash
# Download all ~20K skills (no git required)
python3 download_and_import_skills.py --sitemap-only --skills-dir ./skills2

# Download first 500 skills, then import into Skillberry Store
python3 download_and_import_skills.py --sitemap-only --max-skills 500 --skills-dir ./skills2

# Re-run safely — existing skills are skipped
python3 download_and_import_skills.py --sitemap-only --skills-dir ./skills2
```

### Output in Sitemap-Only Mode

When using `--sitemap-only`, the script will:
1. ⏭️ Skip Phase 1 (HTML scrape / sitemap-owners)
2. ✅ Execute Phase 2b (Download via `/api/download` from skill sitemaps)
3. ✅ Execute Phase 3 (Discover skills in downloaded folders)
4. ✅ Execute Phase 4 (Import with benchmarking)
5. ✅ Execute Phase 5 (Validate)
6. ✅ Execute Phase 6 (Report with benchmark statistics)

To stop after downloading without importing, combine with `--import-only` on a subsequent run:
```bash
# Step 1: download only
python3 download_and_import_skills.py --sitemap-only --skills-dir ./skills2

# Step 2: import from what was downloaded
python3 download_and_import_skills.py --import-only --skills-dir ./skills2
```

## Import-Only Mode

Use `--import-only` to skip cloning/downloading and use existing skills already on disk. Ideal for:

- **Repeated benchmarking**: Test import performance multiple times on the same skill set
- **Performance optimization**: Benchmark after making changes to the import process
- **Selective importing**: Import a subset of previously downloaded skills

### Example Usage

```bash
# Import all skills from existing downloads
python3 download_and_import_skills.py --import-only --skills-dir ./skills2

# Import only first 10 skills
python3 download_and_import_skills.py --import-only --max-skills 10 --skills-dir ./skills2

# Benchmark with a different SBS instance
python3 download_and_import_skills.py --import-only --sbs-url http://localhost:9000 --output-dir ./benchmarks
```

### Output in Import-Only Mode

When using `--import-only`, the script will:
1. ⏭️ Skip Phase 1 (Extract metadata)
2. ⏭️ Skip Phase 2 (Clone/download repositories)
3. ✅ Execute Phase 3 (Discover skills in existing repos)
4. ✅ Execute Phase 4 (Import with benchmarking)
5. ✅ Execute Phase 5 (Validate)
6. ✅ Execute Phase 6 (Report with benchmark statistics)

## Process Flow

### Phase 1: Extract Repository List from skills.sh

Reads `sitemap-owners.xml` to obtain the full catalog of ~9,700 `owner/repo` pairs (sorted by popularity order on skills.sh). Falls back to HTML scraping if the sitemap is unavailable.

> **Before this fix**, Phase 1 scraped the skills.sh homepage HTML, which only embedded ~81 seed repositories in its JavaScript payload. The sitemap approach returns the full ~9,700-repo catalog.

**No limiting at this phase** — Phase 2 clones repositories one by one and stops when the skill target is reached.

### Phase 2: Clone Repositories Until N Skills Found

- Clones repositories from the list produced by Phase 1
- After each clone, counts subfolders in `/skills/` that contain `SKILL.md`
- Accumulates the count until reaching `--max-skills`
- Skips repositories without a `/skills/` folder
- Already-cloned repositories are reused (idempotent re-runs)

**Output:**
- `clone-results.json` — `cloned_repos`, `skipped_repos`, `failed_repos`, `summary`
- `<skills-dir>/` — Cloned repositories

### Phase 2b (Sitemap Mode): Download Skills via `/api/download`

Used instead of Phase 2 when `--sitemap-only` is passed.

- Reads `sitemap-skills-1.xml` and `sitemap-skills-2.xml` (~20,000 skills)
- For each skill, fetches `https://skills.sh/api/download/{owner}/{repo}/{slug}`
- Writes files to `<skills-dir>/<owner>__<repo>/skills/<slug>/`
- Skips skills already downloaded (idempotent)

### Phase 3: Discover Skills in /skills/ Folders

Scans the skill directories on disk (produced by Phase 2 or 2b), finds every subfolder containing `SKILL.md`, and loads content and metadata.

**Output:** `discovered-skills.json`

### Phase 4: Import via Anthropic API (with Benchmarking)

- Uses the `/skills/import-anthropic` endpoint
- Automatically parses SKILL.md, extracts tools and snippets
- Collects per-import benchmark data: duration, size, file count, tool count, snippet count

**Output:** `import-results.json`, `benchmark-results.json`

### Phase 5: Validation

Verifies API accessibility and checks the number of skills returned by the store.

**Output:** `validation-report.json`

### Phase 6: Documentation and Benchmarking Report

Generates a comprehensive report including benchmark statistics (total time, average, median, std dev, fastest/slowest, throughput).

**Output:** `final-report.json`, updated `benchmark-results.json`, `import-skills.log`

## Output Files

### Skills Directory (--skills-dir)
```
./skills2/                           # Example: --skills-dir ./skills2
├── anthropics__skills/
│   └── skills/
│       ├── frontend-design/
│       │   └── SKILL.md
│       └── ...
├── vercel-labs__agent-skills/
│   └── skills/
│       └── vercel-react-best-practices/
│           ├── SKILL.md
│           └── rules/
└── ...
```

### Output Directory (--output-dir)
```
./                                   # Default: current directory
├── 20260702_001751/                 # Timestamped run folder
│   ├── clone-results.json           # Repository clone/download results
│   ├── discovered-skills.json       # Discovered skills
│   ├── import-results.json          # Import results
│   ├── benchmark-results.json       # Benchmark data and statistics
│   ├── validation-report.json       # Validation results
│   ├── final-report.json            # Final summary report with benchmarks
│   └── import-skills.log            # Detailed execution log
├── 20260702_010523/                 # Another run
│   └── ...
└── ...
```

## Benchmarking

The tool automatically collects benchmark data during Phase 4 for all successful imports. No configuration required.

### What is Benchmarked

For each successful skill import:
- **Import duration** — time taken (seconds)
- **Skill size** — total size of all files in the skill folder (KB)
- **File count** — total number of files
- **Tool count** — Python scripts in `/scripts/`
- **Snippet count** — `.md` files including SKILL.md

### Benchmark Statistics (Phase 6)

- Total, average, median, and std dev of import times
- Fastest and slowest imports with skill details
- Throughput: KB/sec, skills/sec, objects/sec

### Use Cases

**Repeated benchmarking with clone:**
```bash
# Download once
python3 download_and_import_skills.py --max-skills 50 --clone-only --skills-dir ./skills2

# Benchmark multiple times
python3 download_and_import_skills.py --import-only --max-skills 10 --skills-dir ./skills2
python3 download_and_import_skills.py --import-only --max-skills 50 --skills-dir ./skills2
```

**Repeated benchmarking with sitemap:**
```bash
# Download once (no git)
python3 download_and_import_skills.py --sitemap-only --max-skills 50 --skills-dir ./skills2

# Benchmark multiple times
python3 download_and_import_skills.py --import-only --max-skills 10 --skills-dir ./skills2
python3 download_and_import_skills.py --import-only --max-skills 50 --skills-dir ./skills2
```

**Optimization testing:**
```bash
# Benchmark before optimization
python3 download_and_import_skills.py --import-only --output-dir ./benchmarks --skills-dir ./skills2

# Make changes to skillberry-store import logic

# Benchmark after optimization
python3 download_and_import_skills.py --import-only --output-dir ./benchmarks --skills-dir ./skills2

# Compare: ./benchmarks/<timestamp-before>/ vs ./benchmarks/<timestamp-after>/
```
