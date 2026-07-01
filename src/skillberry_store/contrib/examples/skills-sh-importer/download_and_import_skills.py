#!/usr/bin/env python3
"""
Download and Import Skills from skills.sh

This script implements a 6-phase process to:
1. Extract repository metadata from skills.sh
2. Clone repositories until finding N skills
3. Discover skills in /skills/ folders
4. Import via Anthropic API
5. Validate imports
6. Generate final report

Usage:
    python download_and_import_skills.py --max-skills 10
"""

import argparse
import json
import logging
import re
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

import requests

# Logging will be configured after output_dir is created in __init__
logger = logging.getLogger(__name__)


class SkillsImporter:
    """Main class for importing skills from skills.sh"""
    
    def __init__(self, args):
        self.args = args
        self.script_dir = Path(__file__).parent
        
        # Determine skills directory (where repos are cloned)
        if args.skills_dir:
            # User specified a directory - can be relative or absolute
            skills_path = Path(args.skills_dir)
            if not skills_path.is_absolute():
                # Relative to current working directory
                skills_path = Path.cwd() / skills_path
            self.repos_dir = skills_path
        else:
            # Default: use system temp directory
            temp_dir = Path(tempfile.gettempdir())
            self.repos_dir = temp_dir / 'skills-sh-repos'
        
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine output directory (where result files are saved)
        if args.output_dir:
            # User specified a directory - can be relative or absolute
            output_path = Path(args.output_dir)
            if not output_path.is_absolute():
                # Relative to current working directory
                output_path = Path.cwd() / output_path
            output_base = output_path
        else:
            # Default: current working directory
            output_base = Path.cwd()
        
        # Create timestamped subdirectory for this run
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = output_base / timestamp
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata = []
        self.cloned_repos = []
        self.discovered_skills = []
        self.transformed_skills = []
        self.import_results = []
        self.benchmark_data = []  # Benchmark data for each import
        
        # Set default for max_skills based on mode
        if args.max_skills is None:
            if args.import_only or getattr(args, 'sitemap_only', False):
                # import-only / sitemap-only: no limit (process all available skills)
                self.max_skills = None
            else:
                # clone-only or full mode: default to 10
                self.max_skills = 10
        else:
            # User explicitly specified max_skills
            self.max_skills = args.max_skills
        
        # Configure logging to write to timestamped output directory
        log_file = self.output_dir / 'import-skills.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ],
            force=True  # Reconfigure if already configured
        )
        
        logger.info(f"Initialized SkillsImporter")
        logger.info(f"Skills directory: {self.repos_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Max skills: {self.max_skills if self.max_skills is not None else 'unlimited'}")
        logger.info(f"SBS URL: {args.sbs_url}")
    
    # ========== PHASE 1: Extract Repository URLs ==========
    
    def _fetch_repos_from_sitemaps(self) -> List[str]:
        """
        Fetch all owner/repo sources from the skills.sh sitemap index.

        skills.sh publishes a sitemap-owners.xml that lists every known
        repository as  https://www.skills.sh/<owner>/<repo>  — one URL per
        <loc> element.  This is a fully public, plain-XML endpoint that
        contains the complete catalog (9 700+ repos as of mid-2026),
        compared to the ~81 repos embedded in the JavaScript-rendered HTML.

        Returns:
            Ordered list of "owner/repo" source strings, deduplicated.
        """
        base_url = self.args.skills_url.rstrip('/')  # e.g. "https://skills.sh"
        sitemap_url = f"{base_url}/sitemap-owners.xml"
        logger.info(f"  Fetching owners sitemap: {sitemap_url}")
        response = requests.get(sitemap_url, timeout=60)
        response.raise_for_status()
        logger.info(f"  Received {len(response.text)} bytes from sitemap")

        # Extract <loc> values: https://www.skills.sh/<owner>/<repo>
        # We strip the host prefix to get "owner/repo".
        loc_pattern = re.compile(r'<loc>(https?://[^/]+/([^/<]+/[^/<]+))</loc>')
        seen: set = set()
        sources: List[str] = []
        for m in loc_pattern.finditer(response.text):
            source = m.group(2)  # "owner/repo"
            if source not in seen:
                seen.add(source)
                sources.append(source)
        return sources

    def _fetch_skills_from_sitemaps(self) -> List[Dict[str, str]]:
        """
        Fetch every individual skill listed in the skills.sh skill sitemaps.

        skills.sh publishes up to two skill sitemaps (sitemap-skills-1.xml,
        sitemap-skills-2.xml), each capped at 10 000 entries.  Together they
        expose ~20 000 directly-downloadable skills with known owner/repo/slug
        triples, which is the complete set accessible without authentication.

        Returns:
            Ordered list of dicts with keys: 'owner', 'repo', 'slug', 'source'.
            Deduplicated; ordering matches sitemap appearance order.
        """
        base_url = self.args.skills_url.rstrip('/')
        # Extract three-segment paths: owner/repo/slug
        loc_pattern = re.compile(
            r'<loc>https?://[^/]+/([^/<]+)/([^/<]+)/([^/<\s]+)</loc>'
        )
        seen: set = set()
        skills: List[Dict[str, str]] = []
        for n in [1, 2]:
            sitemap_url = f"{base_url}/sitemap-skills-{n}.xml"
            logger.info(f"  Fetching skill sitemap: {sitemap_url}")
            try:
                response = requests.get(sitemap_url, timeout=60)
                response.raise_for_status()
                logger.info(f"  Received {len(response.text)} bytes")
            except Exception as e:
                logger.warning(f"  Could not fetch {sitemap_url}: {e}")
                continue
            for m in loc_pattern.finditer(response.text):
                owner, repo, slug = m.group(1), m.group(2), m.group(3).rstrip('/')
                key = f"{owner}/{repo}/{slug}"
                if key not in seen:
                    seen.add(key)
                    skills.append({
                        'owner': owner,
                        'repo': repo,
                        'slug': slug,
                        'source': f"{owner}/{repo}",
                    })
        return skills

    def extract_skills_metadata(self) -> List[Dict[str, Any]]:
        """
        Phase 1: Extract unique repository metadata from skills.sh

        Primary strategy: parse the public sitemap-owners.xml, which lists
        every repository in the catalog (~17 000+ repos).

        Fallback strategy: regex-scrape the JavaScript-rendered homepage HTML,
        which only contains the ~80 seed repos baked into the initial payload.

        Returns:
            List of repository metadata dictionaries
        """
        logger.info("=" * 60)
        logger.info("PHASE 1: Extracting repository URLs from skills.sh")
        logger.info("=" * 60)

        try:
            # --- Primary: sitemaps ---
            logger.info("Strategy: sitemap-owners.xml (full catalog)")
            matches = self._fetch_repos_from_sitemaps()
            if matches:
                logger.info(f"  Sitemap returned {len(matches)} unique repositories")
            else:
                logger.warning("  Sitemap returned no results, falling back to HTML scrape")
        except Exception as e:
            logger.warning(f"  Sitemap fetch failed ({e}), falling back to HTML scrape")
            matches = []

        # --- Fallback: HTML regex scrape ---
        if not matches:
            try:
                logger.info(f"Strategy: HTML scrape of {self.args.skills_url}")
                response = requests.get(self.args.skills_url, timeout=30)
                response.raise_for_status()
                html_content = response.text
                logger.info(f"  Received {len(html_content)} bytes")

                pattern = r'\\"source\\":\\"([^\\]+)\\"'
                raw = re.findall(pattern, html_content)
                if not raw:
                    pattern2 = r'"source":"([^"]+)"'
                    raw = re.findall(pattern2, html_content)

                seen: set = set()
                for source in raw:
                    if source not in seen:
                        seen.add(source)
                        matches.append(source)

                if not matches:
                    logger.error("Could not extract repository sources from HTML")
                    return []
                logger.info(f"  HTML scrape returned {len(matches)} unique repositories")
            except Exception as e:
                logger.error(f"Error extracting metadata: {e}", exc_info=True)
                return []

        # Build repo metadata records
        repos = []
        for source in matches:
            repo_name = source.replace('/', '__').replace(':', '_')
            repo_path = str(self.repos_dir / repo_name)
            repos.append({
                "source": source,
                "repo_name": repo_name,
                "repo_path": repo_path,
                "skills_count": None,
            })

        logger.info(f"\nTop 10 repositories by appearance order:")
        for i, repo in enumerate(repos[:10], 1):
            logger.info(f"  {i}. {repo['source']} -> {repo['repo_name']}")

        logger.info(f"\nTotal: {len(repos)} unique repositories")
        logger.info(f"Phase 2 will clone repos until finding {self.max_skills if self.max_skills is not None else 'all available'} actual skills (subfolders with SKILL.md)")

        self.metadata = repos
        return repos
    
    # ========== PHASE 2: Clone Repositories ==========
    
    def count_skills_in_repo(self, repo_path: Path) -> int:
        """
        Count skill subfolders with SKILL.md in /skills/ directory
        
        Args:
            repo_path: Path to cloned repository
            
        Returns:
            Number of valid skill subfolders found
        """
        skills_dir = repo_path / 'skills'
        if not skills_dir.exists() or not skills_dir.is_dir():
            return 0
        
        count = 0
        for subfolder in skills_dir.iterdir():
            if subfolder.is_dir() and (subfolder / 'SKILL.md').exists():
                count += 1
        
        return count
    
    def clone_repositories(self, metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Phase 2: Clone repositories until we find max_skills skill subfolders
        
        A "skill" is defined as a subfolder in /skills/ directory containing SKILL.md
        
        Args:
            metadata: List of all repo metadata from skills.sh (sorted by popularity)
            
        Returns:
            List of cloned repo info with skill counts
        """
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 2: Cloning repositories to find skills")
        logger.info("=" * 60)
        logger.info(f"Target: {self.max_skills} skills")
        logger.info(f"Strategy: Clone repos by popularity, count /skills/ subfolders with SKILL.md")
        
        # In clone mode, max_skills is always set (never None)
        assert self.max_skills is not None, "max_skills should be set in clone mode"
        
        cloned_repos = []
        skipped_repos = []
        failed_repos = []
        total_skills_found = 0
        repos_processed = 0
        
        for i, repo_meta in enumerate(metadata, 1):
            # Stop if we've found enough skills
            if total_skills_found >= self.max_skills:
                logger.info(f"\n✓ Reached target of {self.max_skills} skills!")
                logger.info(f"  Processed {repos_processed} repositories")
                break
            
            source = repo_meta['source']
            repo_name = repo_meta['repo_name']
            repo_path = Path(repo_meta['repo_path'])
            logger.info(f"\n[Repo {i}] Processing {source}...")
            repos_processed += 1
            
            try:
                
                # Check if already cloned
                already_existed = repo_path.exists()
                
                if already_existed:
                    logger.info(f"  Already exists: {repo_path}")
                else:
                    # Clone repository
                    git_url = f"https://github.com/{source}.git"
                    cmd = [
                        'git', 'clone',
                        '--depth', str(self.args.clone_depth),
                        git_url,
                        str(repo_path)
                    ]
                    
                    logger.info(f"  Running: {' '.join(cmd)}")
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    
                    if result.returncode != 0:
                        logger.error(f"  ✗ Failed to clone: {result.stderr}")
                        failed_repos.append({
                            'source': source,
                            'repo_name': repo_name,
                            'error': result.stderr
                        })
                        continue
                    
                    logger.info(f"  ✓ Successfully cloned to {repo_path}")
                
                # Count skills in /skills/ directory
                skill_count = self.count_skills_in_repo(repo_path)
                
                if skill_count == 0:
                    logger.info(f"  ⊘ No /skills/ folder or no SKILL.md files found - skipping")
                    skipped_repos.append({
                        'source': source,
                        'repo_name': repo_name,
                        'repo_path': str(repo_path),
                        'reason': 'No skills found'
                    })
                    continue
                
                # Found skills!
                total_skills_found += skill_count
                logger.info(f"  ✓ Found {skill_count} skill(s) in /skills/ folder")
                logger.info(f"  Progress: {total_skills_found}/{self.max_skills} skills found")
                
                cloned_repos.append({
                    'source': source,
                    'repo_name': repo_name,
                    'repo_path': str(repo_path),
                    'skills_count': skill_count,
                    'already_existed': already_existed,
                })
                    
            except subprocess.TimeoutExpired:
                logger.error(f"  ✗ Timeout cloning {source}")
                failed_repos.append({
                    'source': source,
                    'repo_name': repo_name,
                    'error': 'Timeout (120s)'
                })
            except Exception as e:
                logger.error(f"  ✗ Error processing {source}: {e}")
                failed_repos.append({
                    'source': source,
                    'repo_name': repo_name,
                    'error': str(e)
                })
        
        # Save results
        clone_results = {
            'cloned_repos': cloned_repos,
            'skipped_repos': skipped_repos,
            'failed_repos': failed_repos,
            'summary': {
                'repos_processed': repos_processed,
                'repos_cloned': len(cloned_repos),
                'repos_skipped': len(skipped_repos),
                'repos_failed': len(failed_repos),
                'total_skills_found': total_skills_found,
                'target_skills': self.max_skills
            }
        }
        
        results_file = self.output_dir / 'clone-results.json'
        with open(results_file, 'w') as f:
            json.dump(clone_results, f, indent=2)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Clone Summary:")
        logger.info(f"  Repositories processed: {repos_processed}")
        logger.info(f"  Repositories with skills: {len(cloned_repos)}")
        logger.info(f"  Repositories skipped (no skills): {len(skipped_repos)}")
        logger.info(f"  Repositories failed: {len(failed_repos)}")
        logger.info(f"  Total skills found: {total_skills_found}/{self.max_skills}")
        logger.info(f"  Results saved to: {results_file}")
        logger.info(f"{'='*60}")
        
        self.cloned_repos = cloned_repos
        return cloned_repos

    # ========== PHASE 2b: Sitemap Direct Download ==========

    def download_skills_from_sitemap(self) -> List[Dict[str, Any]]:
        """
        Alternative to clone_repositories: download skills directly from
        the skills.sh /api/download endpoint using the skill sitemaps.

        This avoids any git operations.  For each skill listed in
        sitemap-skills-1.xml and sitemap-skills-2.xml the method calls
            GET https://skills.sh/api/download/{owner}/{repo}/{slug}
        which returns a JSON snapshot of the skill's files.  Those files are
        written to disk under:
            <skills_dir>/<owner>__<repo>/skills/<slug>/

        That layout is identical to what a git clone produces, so Phase 3
        (discover_skills) works unchanged.

        Returns:
            List of repo-info dicts (same schema as clone_repositories).
        """
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 2 (sitemap): Downloading skills via /api/download")
        logger.info("=" * 60)

        base_url = self.args.skills_url.rstrip('/')
        skills_list = self._fetch_skills_from_sitemaps()

        if not skills_list:
            logger.error("No skills found in skill sitemaps")
            return []

        total_available = len(skills_list)
        target = self.max_skills if self.max_skills is not None else total_available
        logger.info(f"  Skills in sitemaps : {total_available}")
        logger.info(f"  Target             : {target}")

        # Apply limit up front to avoid unnecessary HTTP requests
        if self.max_skills is not None:
            skills_list = skills_list[:self.max_skills]

        # Track which repo dirs we've written to (for the Phase-3 handoff)
        repo_skill_counts: Dict[str, int] = {}  # repo_dir_name -> count

        succeeded = 0
        failed = 0

        for i, entry in enumerate(skills_list, 1):
            owner = entry['owner']
            repo  = entry['repo']
            slug  = entry['slug']
            source = entry['source']

            repo_dir_name = f"{owner}__{repo}"
            skill_dir = self.repos_dir / repo_dir_name / 'skills' / slug
            skill_md_path = skill_dir / 'SKILL.md'

            # Skip if already downloaded (idempotent re-runs)
            if skill_md_path.exists():
                logger.info(f"  [{i}/{len(skills_list)}] Already exists: {source}/{slug}")
                repo_skill_counts[repo_dir_name] = repo_skill_counts.get(repo_dir_name, 0) + 1
                succeeded += 1
                continue

            url = f"{base_url}/api/download/{owner}/{repo}/{slug}"
            logger.info(f"  [{i}/{len(skills_list)}] GET {url}")
            try:
                resp = requests.get(url, timeout=30)
                if resp.status_code == 404:
                    logger.warning(f"    ⊘ Not found (404) — skipping")
                    failed += 1
                    continue
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"    ✗ Request failed: {e}")
                failed += 1
                continue

            files = data.get('files', [])
            if not any(f['path'].upper() == 'SKILL.MD' for f in files):
                logger.warning(f"    ⊘ Response has no SKILL.md — skipping")
                failed += 1
                continue

            skill_dir.mkdir(parents=True, exist_ok=True)
            for file_entry in files:
                dest = skill_dir / file_entry['path']
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(file_entry['contents'], encoding='utf-8')

            repo_skill_counts[repo_dir_name] = repo_skill_counts.get(repo_dir_name, 0) + 1
            succeeded += 1
            logger.info(f"    ✓ Written {len(files)} file(s)")

        # Build the cloned_repos list expected by discover_skills / scan_existing_repos
        cloned_repos = []
        for repo_dir_name, count in repo_skill_counts.items():
            parts = repo_dir_name.split('__', 1)
            source = '/'.join(parts) if len(parts) == 2 else repo_dir_name
            cloned_repos.append({
                'source': source,
                'repo_name': repo_dir_name,
                'repo_path': str(self.repos_dir / repo_dir_name),
                'skills_count': count,
                'already_existed': False,
            })

        logger.info(f"\n{'='*60}")
        logger.info(f"Sitemap Download Summary:")
        logger.info(f"  Skills attempted : {len(skills_list)}")
        logger.info(f"  Skills downloaded: {succeeded}")
        logger.info(f"  Failures/skipped : {failed}")
        logger.info(f"  Repos with skills: {len(cloned_repos)}")
        logger.info(f"{'='*60}")

        self.cloned_repos = cloned_repos
        return cloned_repos

    # ========== PHASE 3: Auto-discover Skills ==========
    
    def scan_existing_repos(self) -> List[Dict[str, Any]]:
        """
        Scan output directory for existing cloned repositories.
        Used by --import-only mode to skip phases 1-2.
        
        Returns:
            List of repository info dictionaries similar to clone_repositories output
        """
        logger.info("\n" + "=" * 60)
        logger.info("IMPORT-ONLY MODE: Scanning existing repositories")
        logger.info("=" * 60)
        logger.info(f"Scanning directory: {self.repos_dir}")
        
        if not self.repos_dir.exists():
            logger.error(f"Output directory does not exist: {self.repos_dir}")
            return []
        
        cloned_repos = []
        
        # Scan for directories that look like cloned repos
        for repo_dir in self.repos_dir.iterdir():
            if not repo_dir.is_dir():
                continue
            
            # Check if it has a /skills/ directory
            skills_dir = repo_dir / 'skills'
            if not skills_dir.exists() or not skills_dir.is_dir():
                logger.debug(f"  Skipping {repo_dir.name} (no /skills/ directory)")
                continue
            
            # Count skills in this repo
            skill_count = self.count_skills_in_repo(repo_dir)
            
            if skill_count == 0:
                logger.debug(f"  Skipping {repo_dir.name} (no SKILL.md files)")
                continue
            
            logger.info(f"  Found: {repo_dir.name} with {skill_count} skill(s)")
            
            cloned_repos.append({
                'source': 'unknown',  # We don't know the original source
                'repo_name': repo_dir.name,
                'repo_path': str(repo_dir),
                'skills_count': skill_count,
                'already_existed': True,
            })
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Found {len(cloned_repos)} repositories with skills")
        logger.info(f"Total skills available: {sum(r['skills_count'] for r in cloned_repos)}")
        logger.info(f"{'='*60}")
        
        return cloned_repos
    
    def discover_skills(self, cloned_repos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Phase 3: Discover skills in /skills/ subfolders with SKILL.md
        
        A skill is a subfolder in /skills/ directory containing SKILL.md file
        
        Args:
            cloned_repos: List of cloned repository info
            
        Returns:
            List of discovered skills with their SKILL.md content
        """
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 3: Discovering skills in /skills/ folders")
        logger.info("=" * 60)
        
        discovered = []
        total_skills = 0
        
        for repo in cloned_repos:
            repo_path = Path(repo['repo_path'])
            repo_name = repo['repo_name']
            source = repo['source']
            
            logger.info(f"\nScanning {repo_name}...")
            logger.info(f"  Expected skills: {repo['skills_count']}")
            
            # Look for /skills/ directory
            skills_dir = repo_path / 'skills'
            if not skills_dir.exists() or not skills_dir.is_dir():
                logger.warning(f"  ✗ No /skills/ directory found (unexpected!)")
                continue
            
            # Find all subfolders with SKILL.md
            skills_found = 0
            for subfolder in skills_dir.iterdir():
                if not subfolder.is_dir():
                    continue
                
                skill_md = subfolder / 'SKILL.md'
                if not skill_md.exists():
                    logger.debug(f"  - Skipping {subfolder.name} (no SKILL.md)")
                    continue
                
                # Found a valid skill!
                skills_found += 1
                total_skills += 1
                
                try:
                    with open(skill_md, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    skill_info = {
                        'repo_source': source,
                        'repo_name': repo_name,
                        'skill_folder': subfolder.name,
                        'skill_path': str(subfolder.relative_to(repo_path)),
                        'skill_md_path': str(skill_md.relative_to(repo_path)),
                        'skill_name': subfolder.name,
                        'content': content,
                        'full_path': str(subfolder),
                        'skill_md_full_path': str(skill_md)
                    }
                    
                    discovered.append(skill_info)
                    logger.info(f"  ✓ Found skill: {subfolder.name}")
                    
                except Exception as e:
                    logger.warning(f"  ✗ Error reading {skill_md.name}: {e}")
            
            logger.info(f"  Total: {skills_found} skill(s) found")
            
            if skills_found != repo['skills_count']:
                logger.warning(f"  ⚠ Expected {repo['skills_count']} but found {skills_found}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Discovery Summary:")
        logger.info(f"  Total skills discovered: {total_skills}")
        logger.info(f"  From {len(cloned_repos)} repositories")
        logger.info(f"{'='*60}")
        
        # Save discovered skills
        discovered_file = self.output_dir / 'discovered-skills.json'
        with open(discovered_file, 'w') as f:
            json.dump(discovered, f, indent=2)
        logger.info(f"Saved to {discovered_file}")
        
        self.discovered_skills = discovered
        return discovered
    
    # ========== PHASE 4: Import via Anthropic API ==========
    
    def collect_skill_metadata(self, skill_folder_path: Path) -> Dict[str, Any]:
        """
        Collect metadata about a skill folder for benchmarking.
        
        Args:
            skill_folder_path: Path to the skill folder
            
        Returns:
            Dictionary with:
            - total_size_kb: Total size of all files in KB
            - file_count: Total number of files
            - tool_count: Number of Python scripts in /scripts/ folder
            - snippet_count: Number of .md files (INCLUDING SKILL.md)
        """
        total_size = 0
        file_count = 0
        tool_count = 0
        snippet_count = 0
        
        try:
            # Walk through all files in the skill folder
            for file_path in skill_folder_path.rglob('*'):
                if file_path.is_file():
                    file_count += 1
                    total_size += file_path.stat().st_size
                    
                    # Count tools (Python scripts in /scripts/ folder)
                    if file_path.suffix == '.py' and 'scripts' in file_path.parts:
                        tool_count += 1
                    
                    # Count snippets (all .md files, INCLUDING SKILL.md)
                    if file_path.suffix == '.md':
                        snippet_count += 1
            
            total_size_kb = total_size / 1024.0
            
        except Exception as e:
            logger.warning(f"Error collecting metadata for {skill_folder_path}: {e}")
            total_size_kb = 0.0
        
        return {
            'total_size_kb': round(total_size_kb, 2),
            'file_count': file_count,
            'tool_count': tool_count,
            'snippet_count': snippet_count
        }
    
    def import_skills_via_api(self, discovered_skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Phase 4: Import skills via skillberry-store Anthropic import API
        
        Uses the /skills/import-anthropic endpoint with folder source type.
        Each skill folder is imported separately. The API handles:
        - Parsing SKILL.md for metadata
        - Extracting tools from code files
        - Creating snippets from text files
        - Creating the skill with proper schema
        
        Args:
            discovered_skills: List of discovered skills from Phase 3
            
        Returns:
            List of import results
        """
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 4: Importing skills via Anthropic API")
        logger.info("=" * 60)
        logger.info("Using /skills/import-anthropic endpoint with folder source")
        
        results = []
        successful = 0
        failed = 0
        
        for i, skill in enumerate(discovered_skills, 1):
            skill_name = skill['skill_name']
            skill_folder_path = skill['full_path']  # Full path to skill folder
            
            logger.info(f"\n[{i}/{len(discovered_skills)}] Importing {skill_name}...")
            logger.info(f"  Folder: {skill_folder_path}")
            
            # Collect skill metadata for benchmarking
            metadata = self.collect_skill_metadata(Path(skill_folder_path))
            
            # Start timing the import
            start_time = time.time()
            
            try:
                # Use the Anthropic import API endpoint
                url = f"{self.args.sbs_url}/skills/import-anthropic"
                
                # Prepare form data
                data = {
                    'source_type': 'folder',
                    'folder_path': skill_folder_path,
                    'snippet_mode': 'file'  # Import text files as snippets
                }
                
                response = requests.post(
                    url,
                    data=data,
                    timeout=self.args.timeout
                )
                
                # Calculate import duration
                import_duration = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"  ✓ Successfully imported in {import_duration:.2f}s")
                    logger.info(f"    Skill: {result.get('skill_name', 'N/A')}")
                    logger.info(f"    Tools: {result.get('tools_created', 0)}")
                    logger.info(f"    Snippets: {result.get('snippets_created', 0)}")
                    successful += 1
                    results.append({
                        'skill': skill_name,
                        'status': 'success',
                        'response': result
                    })
                    
                    # Store benchmark data only for successful imports
                    self.benchmark_data.append({
                        'skill_name': skill_name,
                        'import_duration_seconds': round(import_duration, 3),
                        'total_size_kb': metadata['total_size_kb'],
                        'file_count': metadata['file_count'],
                        'tool_count': metadata['tool_count'],
                        'snippet_count': metadata['snippet_count'],
                        'status': 'success',
                        'folder_path': skill_folder_path
                    })
                else:
                    logger.error(f"  ✗ Failed in {import_duration:.2f}s: {response.status_code} - {response.text}")
                    failed += 1
                    results.append({
                        'skill': skill_name,
                        'status': 'failed',
                        'error': f"{response.status_code}: {response.text}",
                        'folder_path': skill_folder_path
                    })
                    
            except Exception as e:
                import_duration = time.time() - start_time
                logger.error(f"  ✗ Error after {import_duration:.2f}s: {e}")
                failed += 1
                results.append({
                    'skill': skill_name,
                    'status': 'error',
                    'error': str(e),
                    'folder_path': skill_folder_path
                })
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Import Summary:")
        logger.info(f"  Total: {len(discovered_skills)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"{'='*60}")
        
        # Save results
        import_file = self.output_dir / 'import-results.json'
        with open(import_file, 'w') as f:
            json.dump({
                'results': results,
                'summary': {
                    'total': len(discovered_skills),
                    'successful': successful,
                    'failed': failed
                }
            }, f, indent=2)
        
        logger.info(f"Saved to {import_file}")
        
        self.import_results = results
        return results
    
    # ========== PHASE 5: Validation ==========
    
    def validate_imports(self, import_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Phase 6: Validate imported skills
        
        Args:
            import_results: List of import results
            
        Returns:
            Validation report
        """
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 5: Validating imports")
        logger.info("=" * 60)
        
        validation = {
            'api_check': False,
            'skills_count': 0,
            'errors': []
        }
        
        try:
            # Check API is accessible
            url = f"{self.args.sbs_url}/skills/"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                validation['api_check'] = True
                skills = response.json()
                validation['skills_count'] = len(skills)
                logger.info(f"  ✓ API accessible")
                logger.info(f"  ✓ Found {len(skills)} skills in store")
            else:
                validation['errors'].append(f"API returned {response.status_code}")
                logger.error(f"  ✗ API check failed: {response.status_code}")
                
        except Exception as e:
            validation['errors'].append(str(e))
            logger.error(f"  ✗ Validation error: {e}")
        
        # Save validation report
        validation_file = self.output_dir / 'validation-report.json'
        with open(validation_file, 'w') as f:
            json.dump(validation, f, indent=2)
        
        logger.info(f"Saved to {validation_file}")
        
        return validation
    
    # ========== Benchmark Statistics ==========
    
    def calculate_benchmark_statistics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive benchmark statistics from collected data.
        
        Returns:
            Dictionary with benchmark statistics including:
            - Total import time
            - Average, median, stdev of import times
            - Min/max import times with skill details
            - Import speed metrics (KB/sec, skills/sec, objects/sec)
        """
        if not self.benchmark_data:
            return {
                'has_data': False,
                'message': 'No benchmark data available'
            }
        
        # Extract successful imports only
        successful_benchmarks = [b for b in self.benchmark_data if b['status'] == 'success']
        
        if not successful_benchmarks:
            return {
                'has_data': False,
                'message': 'No successful imports to benchmark'
            }
        
        # Calculate timing statistics
        durations = [b['import_duration_seconds'] for b in successful_benchmarks]
        total_time = sum(durations)
        avg_time = statistics.mean(durations)
        median_time = statistics.median(durations)
        stdev_time = statistics.stdev(durations) if len(durations) > 1 else 0.0
        
        # Find min and max
        min_benchmark = min(successful_benchmarks, key=lambda x: x['import_duration_seconds'])
        max_benchmark = max(successful_benchmarks, key=lambda x: x['import_duration_seconds'])
        
        # Calculate totals for throughput metrics
        total_skills = len(successful_benchmarks)
        total_size_kb = sum(b['total_size_kb'] for b in successful_benchmarks)
        total_tools = sum(b['tool_count'] for b in successful_benchmarks)
        total_snippets = sum(b['snippet_count'] for b in successful_benchmarks)
        total_objects = total_skills + total_tools + total_snippets
        
        # Calculate throughput metrics
        kb_per_sec = total_size_kb / total_time if total_time > 0 else 0.0
        skills_per_sec = total_skills / total_time if total_time > 0 else 0.0
        objects_per_sec = total_objects / total_time if total_time > 0 else 0.0
        
        return {
            'has_data': True,
            'total_imports': total_skills,
            'total_time_seconds': round(total_time, 2),
            'average_time_seconds': round(avg_time, 3),
            'median_time_seconds': round(median_time, 3),
            'stdev_time_seconds': round(stdev_time, 3),
            'min_import': {
                'time_seconds': round(min_benchmark['import_duration_seconds'], 3),
                'skill_name': min_benchmark['skill_name'],
                'size_kb': min_benchmark['total_size_kb'],
                'file_count': min_benchmark['file_count'],
                'tool_count': min_benchmark['tool_count'],
                'snippet_count': min_benchmark['snippet_count']
            },
            'max_import': {
                'time_seconds': round(max_benchmark['import_duration_seconds'], 3),
                'skill_name': max_benchmark['skill_name'],
                'size_kb': max_benchmark['total_size_kb'],
                'file_count': max_benchmark['file_count'],
                'tool_count': max_benchmark['tool_count'],
                'snippet_count': max_benchmark['snippet_count']
            },
            'throughput': {
                'kb_per_sec': round(kb_per_sec, 2),
                'skills_per_sec': round(skills_per_sec, 2),
                'objects_per_sec': round(objects_per_sec, 2),
                'total_size_kb': round(total_size_kb, 2),
                'total_tools': total_tools,
                'total_snippets': total_snippets,
                'total_objects': total_objects
            }
        }
    
    # ========== PHASE 6: Documentation ==========
    
    def generate_final_report(self, validation: Dict[str, Any]):
        """
        Phase 6: Generate final documentation and report
        
        Args:
            validation: Validation results
        """
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 6: Generating final report")
        logger.info("=" * 60)
        
        # Calculate benchmark statistics
        benchmark_stats = self.calculate_benchmark_statistics()
        
        report = {
            'execution_time': datetime.now(timezone.utc).isoformat(),
            'configuration': {
                'max_skills': self.max_skills,
                'sbs_url': self.args.sbs_url,
                'clone_depth': self.args.clone_depth,
                'skills_dir': str(self.repos_dir),
                'output_dir': str(self.output_dir),
                'clone_only_mode': self.args.clone_only,
                'import_only_mode': self.args.import_only
            },
            'phase_1_extract': {
                'total_repositories_found': len(self.metadata),
                'target_skills': self.max_skills
            },
            'phase_2_clone': {
                'repositories_cloned': len(self.cloned_repos),
                'unique_repos_cloned': len(set(s.get('repo_name', '') for s in self.cloned_repos))
            },
            'phase_3_discover': {
                'skills_discovered': len(self.discovered_skills)
            },
            'phase_4_import': {
                'successful': sum(1 for r in self.import_results if r['status'] == 'success'),
                'failed': sum(1 for r in self.import_results if r['status'] != 'success')
            },
            'phase_4_benchmarks': benchmark_stats,
            'phase_5_validation': validation,
            'success': validation.get('api_check', False)
        }
        
        # Save final report
        report_file = self.output_dir / 'final-report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save benchmark data separately
        if self.benchmark_data:
            benchmark_file = self.output_dir / 'benchmark-results.json'
            with open(benchmark_file, 'w') as f:
                json.dump({
                    'benchmarks': self.benchmark_data,
                    'statistics': benchmark_stats
                }, f, indent=2)
            logger.info(f"Benchmark data saved to: {benchmark_file}")
        
        logger.info(f"\n{'='*60}")
        logger.info("FINAL REPORT")
        logger.info(f"{'='*60}")
        logger.info(f"Repositories extracted: {report['phase_1_extract']['total_repositories_found']}")
        logger.info(f"Unique repos cloned: {report['phase_2_clone']['unique_repos_cloned']}")
        logger.info(f"Repositories cloned: {report['phase_2_clone']['repositories_cloned']}")
        logger.info(f"Skills discovered in repos: {report['phase_3_discover']['skills_discovered']}")
        logger.info(f"Skills imported: {report['phase_4_import']['successful']}")
        logger.info(f"Import failures: {report['phase_4_import']['failed']}")
        logger.info(f"Validation: {'✓ PASSED' if report['success'] else '✗ FAILED'}")
        logger.info(f"{'='*60}")
        
        # Display benchmark results
        if benchmark_stats.get('has_data'):
            logger.info(f"\n{'='*60}")
            logger.info("BENCHMARK RESULTS")
            logger.info(f"{'='*60}")
            logger.info(f"Total import time: {benchmark_stats['total_time_seconds']} seconds")
            logger.info(f"Average import time: {benchmark_stats['average_time_seconds']} seconds")
            logger.info(f"Median import time: {benchmark_stats['median_time_seconds']} seconds")
            logger.info(f"Std deviation: {benchmark_stats['stdev_time_seconds']} seconds")
            logger.info(f"")
            
            min_imp = benchmark_stats['min_import']
            logger.info(f"Fastest import: {min_imp['time_seconds']}s - {min_imp['skill_name']}")
            logger.info(f"  ({min_imp['size_kb']} KB, {min_imp['file_count']} files, "
                       f"{min_imp['tool_count']} tools, {min_imp['snippet_count']} snippets)")
            
            max_imp = benchmark_stats['max_import']
            logger.info(f"Slowest import: {max_imp['time_seconds']}s - {max_imp['skill_name']}")
            logger.info(f"  ({max_imp['size_kb']} KB, {max_imp['file_count']} files, "
                       f"{max_imp['tool_count']} tools, {max_imp['snippet_count']} snippets)")
            
            logger.info(f"")
            throughput = benchmark_stats['throughput']
            logger.info(f"Import throughput:")
            logger.info(f"  - {throughput['kb_per_sec']} KB/sec")
            logger.info(f"  - {throughput['skills_per_sec']} skills/sec")
            logger.info(f"  - {throughput['objects_per_sec']} objects/sec "
                       f"({throughput['total_objects']} total: {benchmark_stats['total_imports']} skills + "
                       f"{throughput['total_tools']} tools + {throughput['total_snippets']} snippets)")
            logger.info(f"{'='*60}")
        
        logger.info(f"\nFull report saved to: {report_file}")
    
    # ========== Main Execution ==========
    
    def run(self):
        """Execute all phases"""
        start_time = time.time()
        
        try:
            # Check for mutually exclusive modes
            exclusive = sum([
                bool(self.args.clone_only),
                bool(self.args.import_only),
                bool(getattr(self.args, 'sitemap_only', False)),
            ])
            if exclusive > 1:
                logger.error("--clone-only, --import-only, and --sitemap-only are mutually exclusive")
                return

            sitemap_only = getattr(self.args, 'sitemap_only', False)

            # Import-only mode: skip phases 1-2, scan existing local repos
            if self.args.import_only:
                logger.info("\n" + "="*60)
                logger.info("IMPORT-ONLY MODE: Using existing repositories")
                logger.info("="*60)
                cloned = self.scan_existing_repos()
                if not cloned:
                    logger.error("No existing repositories found. Aborting.")
                    return

            # Sitemap mode: download skills via /api/download (no git)
            elif sitemap_only:
                logger.info("\n" + "="*60)
                logger.info("SITEMAP MODE: Downloading skills via skills.sh API")
                logger.info("="*60)
                cloned = self.download_skills_from_sitemap()
                if not cloned:
                    logger.error("No skills downloaded. Aborting.")
                    return

            else:
                # Normal mode: Phase 1 + Phase 2 (git clone)
                metadata = self.extract_skills_metadata()
                if not metadata:
                    logger.error("Failed to extract metadata. Aborting.")
                    return
                cloned = self.clone_repositories(metadata)
                if not cloned:
                    logger.error("No repositories cloned. Aborting.")
                    return
                
                # If clone-only mode, stop here
                if self.args.clone_only:
                    logger.info("\n" + "="*60)
                    logger.info("CLONE-ONLY MODE: Stopping after Phase 2")
                    logger.info("="*60)
                    logger.info(f"Cloned {len(cloned)} repositories to {self.repos_dir}")
                    elapsed = time.time() - start_time
                    logger.info(f"Total execution time: {elapsed:.2f} seconds")
                    return
            
            # Phase 3: Discover skills
            discovered = self.discover_skills(cloned)
            if not discovered:
                logger.error("No skills discovered. Aborting.")
                return
            
            # Apply max-skills limit if set (in import-only mode, it may be None for unlimited)
            if self.max_skills is not None:
                if len(discovered) > self.max_skills:
                    logger.info(f"\nApplying --max-skills limit: {self.max_skills}")
                    logger.info(f"Discovered {len(discovered)} skills, will import first {self.max_skills}")
                    discovered = discovered[:self.max_skills]
            else:
                logger.info(f"\nNo max-skills limit set, will import all {len(discovered)} discovered skills")
            
            # Phase 4: Import via Anthropic API
            results = self.import_skills_via_api(discovered)
            
            # Phase 5: Validate
            validation = self.validate_imports(results)
            
            # Phase 6: Generate report
            self.generate_final_report(validation)
            
            elapsed = time.time() - start_time
            logger.info(f"\n{'='*60}")
            logger.info(f"Total execution time: {elapsed:.2f} seconds")
            logger.info(f"{'='*60}")
            
        except KeyboardInterrupt:
            logger.warning("\n\nInterrupted by user")
        except Exception as e:
            logger.error(f"\n\nFatal error: {e}", exc_info=True)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Download and import skills from skills.sh into skillberry-store'
    )
    
    parser.add_argument(
        '--max-skills',
        type=int,
        default=None,
        help='Maximum number of skills to import (default: 10 for clone/full mode, unlimited for import-only mode)'
    )
    
    parser.add_argument(
        '--sbs-url',
        type=str,
        default='http://localhost:8000',
        help='Skillberry Store URL (default: http://localhost:8000)'
    )
    
    parser.add_argument(
        '--skills-url',
        type=str,
        default='https://skills.sh',
        help='Skills.sh URL (default: https://skills.sh)'
    )
    
    parser.add_argument(
        '--clone-depth',
        type=int,
        default=1,
        help='Git clone depth (default: 1 for shallow clone)'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='API request timeout in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--skills-dir',
        type=str,
        default=None,
        help='Directory for cloned skill repositories (absolute or relative path). Default: <system-temp>/skills-sh-repos'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Directory for output files (absolute or relative path). A timestamped subdirectory will be created for each run. Default: current directory'
    )
    
    parser.add_argument(
        '--clone-only',
        action='store_true',
        help='Only clone repositories, skip discovery and import phases'
    )
    
    parser.add_argument(
        '--import-only',
        action='store_true',
        help='Skip phases 1-2, use existing downloaded skills from skills-dir and start from phase 3. If --max-skills specified, import up to that limit; otherwise import all discovered skills.'
    )

    parser.add_argument(
        '--sitemap-only',
        action='store_true',
        help=(
            'Download skills directly from the skills.sh /api/download endpoint '
            'using the public skill sitemaps (~20 000 skills). '
            'No git clone required. If --max-skills is specified, stop after that '
            'many skills; otherwise download all available skills.'
        )
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║  Skills.sh Importer for Skillberry Store                 ║
║  6-Phase Import Process with Benchmarking                ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    args = parse_arguments()
    
    # Check dependencies
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("Git is not installed or not in PATH")
        sys.exit(1)
    
    # Run importer
    importer = SkillsImporter(args)
    importer.run()


if __name__ == '__main__':
    main()

# Made with Bob
