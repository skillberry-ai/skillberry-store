#!/usr/bin/env python3
"""
Download and Import Skills from skills.sh

This script implements a 7-phase process to:
1. Extract repository URLs from skills.sh
2. Clone repositories
3. Auto-discover skills
4. Transform to skillberry format
5. Import via API
6. Validate imports
7. Generate documentation

Usage:
    python download_and_import_skills.py --max-repos 10
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('import_skills.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SkillsImporter:
    """Main class for importing skills from skills.sh"""
    
    def __init__(self, args):
        self.args = args
        self.script_dir = Path(__file__).parent
        
        # Determine output directory
        if args.output_dir:
            # User specified a directory - must be absolute
            output_path = Path(args.output_dir)
            if not output_path.is_absolute():
                raise ValueError(f"--output-dir must be an absolute path, got: {args.output_dir}")
            self.repos_dir = output_path
        else:
            # Default: use system temp directory
            temp_dir = Path(tempfile.gettempdir())
            self.repos_dir = temp_dir / 'skills-sh-repos'
        
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata = []
        self.cloned_repos = []
        self.discovered_skills = []
        self.transformed_skills = []
        self.import_results = []
        
        logger.info(f"Initialized SkillsImporter")
        logger.info(f"Output directory: {self.repos_dir}")
        logger.info(f"Max skills: {args.max_skills}")
        logger.info(f"API URL: {args.api_url}")
    
    # ========== PHASE 1: Extract Repository URLs ==========
    
    def extract_skills_metadata(self) -> List[Dict[str, Any]]:
        """
        Phase 1: Extract repository metadata from skills.sh
        
        Returns:
            List of skill metadata dictionaries
        """
        logger.info("=" * 60)
        logger.info("PHASE 1: Extracting repository URLs from skills.sh")
        logger.info("=" * 60)
        
        try:
            logger.info(f"Fetching {self.args.skills_url}...")
            response = requests.get(self.args.skills_url, timeout=30)
            response.raise_for_status()
            
            html_content = response.text
            logger.info(f"Received {len(html_content)} bytes")
            
            # Extract skills data using regex
            # The data is in escaped JSON format within the HTML
            pattern = r'\\"source\\":\\"([^\\]+)\\"[^}]*\\"skillId\\":\\"([^\\]+)\\"[^}]*\\"name\\":\\"([^\\]+)\\"[^}]*\\"installs\\":(\d+)(?:[^}]*\\"isOfficial\\":true)?'
            
            matches = re.findall(pattern, html_content)
            
            if not matches:
                logger.warning("No skills found with primary pattern, trying alternative...")
                # Try simpler pattern
                pattern2 = r'"source":"([^"]+)".*?"skillId":"([^"]+)".*?"name":"([^"]+)".*?"installs":(\d+)'
                matches = re.findall(pattern2, html_content)
            
            if not matches:
                logger.error("Could not extract skills from HTML")
                return []
            
            # Convert matches to dictionaries
            skills = []
            for source, skill_id, name, installs in matches:
                skill = {
                    "source": source,
                    "skillId": skill_id,
                    "name": name,
                    "installs": int(installs),
                    "isOfficial": True  # Assume official if on skills.sh
                }
                skills.append(skill)
            
            # Sort by installs (descending) - this determines clone order
            skills.sort(key=lambda x: x['installs'], reverse=True)
            
            logger.info(f"Extracted {len(skills)} total skills from skills.sh")
            logger.info(f"Sorted by popularity (installs)")
            
            # Save all metadata
            metadata_file = self.script_dir / 'skills-metadata.json'
            with open(metadata_file, 'w') as f:
                json.dump(skills, f, indent=2)
            logger.info(f"Saved metadata to {metadata_file}")
            
            # Show top skills
            logger.info(f"\nTop 10 most popular repositories:")
            for i, skill in enumerate(skills[:10], 1):
                logger.info(f"  {i}. {skill['name']} ({skill['source']}) - {skill['installs']:,} installs")
            
            # Count unique repositories
            unique_repos = set(skill['source'] for skill in skills)
            logger.info(f"\nTotal: {len(skills)} skill entries from {len(unique_repos)} unique repositories")
            logger.info(f"Phase 2 will clone repos until finding {self.args.max_skills} actual skills (subfolders with SKILL.md)")
            
            self.metadata = skills
            return skills
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}", exc_info=True)
            return []
    
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
        logger.info(f"Target: {self.args.max_skills} skills")
        logger.info(f"Strategy: Clone repos by popularity, count /skills/ subfolders with SKILL.md")
        
        cloned_repos = []
        skipped_repos = []
        failed_repos = []
        total_skills_found = 0
        repos_processed = 0
        
        for i, repo_meta in enumerate(metadata, 1):
            # Stop if we've found enough skills
            if total_skills_found >= self.args.max_skills:
                logger.info(f"\n✓ Reached target of {self.args.max_skills} skills!")
                logger.info(f"  Processed {repos_processed} repositories")
                break
            
            source = repo_meta['source']
            logger.info(f"\n[Repo {i}] Processing {source}...")
            repos_processed += 1
            
            # Sanitize repo name for filesystem
            repo_name = source.replace('/', '__').replace(':', '_')
            repo_path = self.repos_dir / repo_name
            
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
                logger.info(f"  Progress: {total_skills_found}/{self.args.max_skills} skills found")
                
                cloned_repos.append({
                    'source': source,
                    'repo_name': repo_name,
                    'repo_path': str(repo_path),
                    'skills_count': skill_count,
                    'already_existed': already_existed,
                    **repo_meta  # Include original metadata (installs, isOfficial, etc.)
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
                'target_skills': self.args.max_skills
            }
        }
        
        results_file = self.script_dir / 'clone_results.json'
        with open(results_file, 'w') as f:
            json.dump(clone_results, f, indent=2)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Clone Summary:")
        logger.info(f"  Repositories processed: {repos_processed}")
        logger.info(f"  Repositories with skills: {len(cloned_repos)}")
        logger.info(f"  Repositories skipped (no skills): {len(skipped_repos)}")
        logger.info(f"  Repositories failed: {len(failed_repos)}")
        logger.info(f"  Total skills found: {total_skills_found}/{self.args.max_skills}")
        logger.info(f"  Results saved to: {results_file}")
        logger.info(f"{'='*60}")
        
        self.cloned_repos = cloned_repos
        return cloned_repos
    
    # ========== PHASE 3: Auto-discover Skills ==========
    
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
        discovered_file = self.script_dir / 'discovered-skills.json'
        with open(discovered_file, 'w') as f:
            json.dump(discovered, f, indent=2)
        logger.info(f"Saved to {discovered_file}")
        
        self.discovered_skills = discovered
        return discovered
    
    # ========== PHASE 4: Transform to Skillberry Format ==========
    
    def transform_skills(self, discovered_skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Phase 4: Transform discovered skills to skillberry format
        
        Args:
            discovered_skills: List of discovered skills
            
        Returns:
            List of transformed skills
        """
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 4: Transforming to skillberry format")
        logger.info("=" * 60)
        
        transformed = []
        
        for skill in discovered_skills:
            try:
                # Generate UUID
                skill_uuid = str(uuid.uuid4())
                
                # Extract description from SKILL.md content
                content = skill['content']
                description = self._extract_description(content, 'md')  # All skills are SKILL.md files
                
                # Create skill schema matching ManifestSchema/SkillSchema
                skill_schema = {
                    'uuid': skill_uuid,
                    'name': f"{skill['repo_name']}__{skill['skill_name']}",
                    'description': description,
                    'tool_uuids': [],  # Will be populated if we extract tools
                    'snippet_uuids': [],  # Will be populated if we extract snippets
                    'state': 'approved',  # Use 'state' not 'lifecycle_state'
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'modified_at': datetime.now(timezone.utc).isoformat(),  # Use 'modified_at' not 'updated_at'
                    'extra': {  # Use 'extra' not 'metadata'
                        'source': skill['repo_source'],
                        'original_path': skill['skill_path'],
                        'skill_folder': skill['skill_folder'],
                        'file_type': 'md'  # All skills are SKILL.md files
                    }
                }
                
                transformed.append(skill_schema)
                logger.info(f"  ✓ Transformed: {skill_schema['name']}")
                
            except Exception as e:
                logger.error(f"  ✗ Error transforming {skill.get('skill_name', 'unknown')}: {e}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Transform Summary:")
        logger.info(f"  Total transformed: {len(transformed)}")
        logger.info(f"{'='*60}")
        
        # Save transformed skills
        transformed_dir = self.script_dir / 'transformed-skills'
        transformed_dir.mkdir(exist_ok=True)
        
        for skill in transformed:
            skill_file = transformed_dir / f"{skill['name']}.json"
            with open(skill_file, 'w') as f:
                json.dump(skill, f, indent=2)
        
        logger.info(f"Saved to {transformed_dir}")
        
        self.transformed_skills = transformed
        return transformed
    
    def _extract_description(self, content: str, file_type: str) -> str:
        """Extract description from content based on file type"""
        if file_type == 'md':
            # Extract first paragraph from markdown
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    return line[:500]
        elif file_type in ['py', 'js', 'ts']:
            # Extract docstring or first comment
            if '"""' in content:
                start = content.find('"""') + 3
                end = content.find('"""', start)
                if end > start:
                    return content[start:end].strip()[:500]
        
        # Default: first 200 chars
        return content[:200].strip()
    
    # ========== PHASE 5: Import via Anthropic API ==========
    
    def import_skills_via_api(self, discovered_skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Phase 5: Import skills via skillberry-store Anthropic import API
        
        Uses the /skills/import-anthropic endpoint with folder source type.
        Each skill folder is imported separately.
        
        Args:
            discovered_skills: List of discovered skills from Phase 3
            
        Returns:
            List of import results
        """
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 5: Importing skills via Anthropic API")
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
            
            try:
                # Use the Anthropic import API endpoint
                url = f"{self.args.api_url}/skills/import-anthropic"
                
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
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"  ✓ Successfully imported")
                    logger.info(f"    Skill: {result.get('skill_name', 'N/A')}")
                    logger.info(f"    Tools: {result.get('tools_created', 0)}")
                    logger.info(f"    Snippets: {result.get('snippets_created', 0)}")
                    successful += 1
                    results.append({
                        'skill': skill_name,
                        'status': 'success',
                        'response': result
                    })
                else:
                    logger.error(f"  ✗ Failed: {response.status_code} - {response.text}")
                    failed += 1
                    results.append({
                        'skill': skill_name,
                        'status': 'failed',
                        'error': f"{response.status_code}: {response.text}",
                        'folder_path': skill_folder_path
                    })
                    
            except Exception as e:
                logger.error(f"  ✗ Error: {e}")
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
        import_file = self.script_dir / 'import_results.json'
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
    
    # ========== PHASE 6: Validation ==========
    
    def validate_imports(self, import_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Phase 6: Validate imported skills
        
        Args:
            import_results: List of import results
            
        Returns:
            Validation report
        """
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 6: Validating imports")
        logger.info("=" * 60)
        
        validation = {
            'api_check': False,
            'skills_count': 0,
            'errors': []
        }
        
        try:
            # Check API is accessible
            url = f"{self.args.api_url}/skills/"
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
        validation_file = self.script_dir / 'validation_report.json'
        with open(validation_file, 'w') as f:
            json.dump(validation, f, indent=2)
        
        logger.info(f"Saved to {validation_file}")
        
        return validation
    
    # ========== PHASE 7: Documentation ==========
    
    def generate_final_report(self, validation: Dict[str, Any]):
        """
        Phase 7: Generate final documentation and report
        
        Args:
            validation: Validation results
        """
        logger.info("\n" + "=" * 60)
        logger.info("PHASE 7: Generating final report")
        logger.info("=" * 60)
        
        report = {
            'execution_time': datetime.now(timezone.utc).isoformat(),
            'configuration': {
                'max_skills': self.args.max_skills,
                'api_url': self.args.api_url,
                'clone_depth': self.args.clone_depth
            },
            'phase_1_extract': {
                'total_skills_found': len(self.metadata),
                'skills_selected': self.args.max_skills
            },
            'phase_2_clone': {
                'skills_cloned': len(self.cloned_repos),
                'unique_repos_cloned': len(set(s.get('repo_name', '') for s in self.cloned_repos))
            },
            'phase_3_discover': {
                'skills_discovered': len(self.discovered_skills)
            },
            'phase_4_transform': {
                'skills_transformed': len(self.transformed_skills)
            },
            'phase_5_import': {
                'successful': sum(1 for r in self.import_results if r['status'] == 'success'),
                'failed': sum(1 for r in self.import_results if r['status'] != 'success')
            },
            'phase_6_validation': validation,
            'success': validation.get('api_check', False)
        }
        
        # Save final report
        report_file = self.script_dir / 'FINAL_REPORT.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\n{'='*60}")
        logger.info("FINAL REPORT")
        logger.info(f"{'='*60}")
        logger.info(f"Skills selected: {report['phase_1_extract']['skills_selected']}")
        logger.info(f"Unique repos cloned: {report['phase_2_clone']['unique_repos_cloned']}")
        logger.info(f"Skills from cloned repos: {report['phase_2_clone']['skills_cloned']}")
        logger.info(f"Skills discovered in repos: {report['phase_3_discover']['skills_discovered']}")
        logger.info(f"Skills transformed: {report['phase_4_transform']['skills_transformed']}")
        logger.info(f"Skills imported: {report['phase_5_import']['successful']}")
        logger.info(f"Import failures: {report['phase_5_import']['failed']}")
        logger.info(f"Validation: {'✓ PASSED' if report['success'] else '✗ FAILED'}")
        logger.info(f"{'='*60}")
        logger.info(f"\nFull report saved to: {report_file}")
    
    # ========== Main Execution ==========
    
    def run(self):
        """Execute all phases"""
        start_time = time.time()
        
        try:
            # Phase 1: Extract metadata
            metadata = self.extract_skills_metadata()
            if not metadata:
                logger.error("Failed to extract metadata. Aborting.")
                return
            
            # Phase 2: Clone repositories
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
            
            # Phase 4: Skip transformation - use Anthropic import API directly
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 4: Skipped (using Anthropic import API)")
            logger.info("=" * 60)
            
            # Phase 5: Import via Anthropic API
            results = self.import_skills_via_api(discovered)
            
            # Phase 6: Validate
            validation = self.validate_imports(results)
            
            # Phase 7: Generate report
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
        default=10,
        help='Maximum number of skills to import (default: 10)'
    )
    
    parser.add_argument(
        '--api-url',
        type=str,
        default='http://localhost:8000',
        help='Skillberry API URL (default: http://localhost:8000)'
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
        '--output-dir',
        type=str,
        default=None,
        help='Output directory for cloned repos (must be absolute path). Default: <system-temp>/skills-sh-repos'
    )
    
    parser.add_argument(
        '--clone-only',
        action='store_true',
        help='Only clone repositories, skip discovery and import phases'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║  Skills.sh Importer for Skillberry Store                 ║
║  7-Phase Import Process                                   ║
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
