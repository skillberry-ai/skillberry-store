"""GitHub provenance source.

Resolves a github.com skill URL into the four "background" dimensions a source
can answer remotely (provenance, publisher, license, integrity), using the
GitHub REST API. Auth headers are resolved through the store's existing
per-endpoint resolver so the gh-CLI token / configured tokens are reused.

The JSON -> Background mapping is kept in standalone, network-free functions
(``build_*``) so they can be unit-tested against captured API fixtures.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from skillberry_store.tools.anthropic.importer import parse_github_origin

from .base import (
    Background,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    LICENSE_COPYLEFT,
    LICENSE_NONE,
    LICENSE_UNKNOWN,
    ProvenanceSource,
    license_category,
)

logger = logging.getLogger(__name__)

_API = "https://api.github.com"
_TIMEOUT = 30  # match importer.py's GitHub timeout


def _age_days(iso_ts: Optional[str]) -> Optional[int]:
    """Whole days between an ISO-8601 GitHub timestamp and ``now`` (UTC)."""
    if not iso_ts:
        return None
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - ts).days


# ── pure mappers (no network; unit-tested against fixtures) ──────────────────


def build_provenance(
    origin: Dict[str, Any], commit: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Provenance section from origin + the resolved HEAD commit for the path."""
    owner, repo = origin.get("owner"), origin.get("repo")
    ref, path = origin.get("ref"), origin.get("path") or ""
    sha = (commit or {}).get("sha")
    out: Dict[str, Any] = {
        "status": "ok" if owner and repo else "error",
        "type": "github",
        "owner": owner,
        "repo": repo,
        "ref": ref,
        "path": path,
        "commit_sha": sha,
        "committed_at": (
            ((commit or {}).get("commit") or {}).get("committer") or {}
        ).get("date"),
        "url": f"https://github.com/{owner}/{repo}/tree/{ref}/{path}".rstrip("/"),
    }
    if sha:
        out["permalink"] = (
            f"https://github.com/{owner}/{repo}/tree/{sha}/{path}".rstrip("/")
        )
    return out


def build_publisher(repo_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Publisher / repository-reputation section from `GET /repos/{o}/{r}`."""
    if not repo_json:
        return {"status": "unavailable"}
    owner = repo_json.get("owner") or {}
    pushed_at = repo_json.get("pushed_at")
    return {
        "status": "ok",
        "owner": owner.get("login"),
        "owner_type": owner.get("type"),  # "User" | "Organization"
        "stars": repo_json.get("stargazers_count"),
        "forks": repo_json.get("forks_count"),
        "open_issues": repo_json.get("open_issues_count"),
        "archived": repo_json.get("archived"),
        "created_at": repo_json.get("created_at"),
        "repo_age_days": _age_days(repo_json.get("created_at")),
        "last_pushed_at": pushed_at,
        "days_since_push": _age_days(pushed_at),
    }


def build_license(license_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """License / legality section from `GET /repos/{o}/{r}/license`.

    A 404 (no license file) is represented by passing ``None`` here, which maps
    to the "none" category — i.e. all rights reserved, not safe to redistribute.
    """
    if not license_json:
        return {
            "status": "ok",
            "spdx_id": None,
            "category": LICENSE_NONE,
            "note": "No license detected — treat as all rights reserved.",
        }
    lic = license_json.get("license") or {}
    spdx = lic.get("spdx_id")
    return {
        "status": "ok",
        "spdx_id": spdx,
        "name": lic.get("name"),
        "category": license_category(spdx),
        "detected_in": license_json.get("name"),  # e.g. "LICENSE"
    }


def build_integrity(commit: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Authenticity section from the commit's signature verification block.

    Per-file content hashing is added by the plugin (it owns the stored bytes);
    here we surface whether the pinned commit is cryptographically verified.
    """
    if not commit:
        return {"status": "unavailable", "commit_verified": None}
    verification = (commit.get("commit") or {}).get("verification") or {}
    return {
        "status": "ok",
        "commit_sha": commit.get("sha"),
        "commit_verified": verification.get("verified"),
        "verification_reason": verification.get("reason"),
    }


def assess_confidence(bg: Background) -> Tuple[str, List[str]]:
    """Roll the sections up into high/medium/low with human-readable reasons.

    Conservative by design: anything legally or authenticity-wise unclear caps
    confidence. Reputation nudges within the remaining band.
    """
    reasons: List[str] = []
    lic_cat = bg.license.get("category")
    publisher = bg.publisher
    verified = bg.integrity.get("commit_verified")

    # Legality is a hard cap.
    if lic_cat in (LICENSE_NONE, LICENSE_UNKNOWN):
        reasons.append(
            "no/unclear license — redistribution may be restricted"
        )
        ceiling = CONFIDENCE_LOW if lic_cat == LICENSE_NONE else CONFIDENCE_MEDIUM
    elif lic_cat == LICENSE_COPYLEFT:
        reasons.append("copyleft license — carries redistribution obligations")
        ceiling = CONFIDENCE_MEDIUM
    else:
        ceiling = CONFIDENCE_HIGH

    # Reputation signals.
    rep = CONFIDENCE_LOW
    if publisher.get("status") == "ok":
        stars = publisher.get("stars") or 0
        age = publisher.get("repo_age_days")
        is_org = publisher.get("owner_type") == "Organization"
        if (stars >= 100 or is_org) and (age is not None and age >= 180):
            rep = CONFIDENCE_HIGH
            reasons.append(
                f"established source ({'org, ' if is_org else ''}{stars}★)"
            )
        elif age is not None and age >= 30:
            rep = CONFIDENCE_MEDIUM
            reasons.append("moderately established source")
        else:
            reasons.append("new or low-signal source")
    else:
        reasons.append("publisher info unavailable")

    if verified:
        reasons.append("commit signature verified")
    elif verified is False:
        reasons.append("commit not signature-verified")

    order = {CONFIDENCE_LOW: 0, CONFIDENCE_MEDIUM: 1, CONFIDENCE_HIGH: 2}
    final = min(ceiling, rep, key=lambda c: order[c])
    return final, reasons


def build_background(
    origin: Dict[str, Any],
    repo_json: Optional[Dict[str, Any]],
    license_json: Optional[Dict[str, Any]],
    commit: Optional[Dict[str, Any]],
) -> Background:
    """Assemble a full Background (minus the plugin-owned behavior section)."""
    bg = Background(source="github")
    bg.provenance = build_provenance(origin, commit)
    bg.publisher = build_publisher(repo_json)
    bg.license = build_license(license_json)
    bg.integrity = build_integrity(commit)
    bg.confidence, bg.confidence_reasons = assess_confidence(bg)
    return bg


class GitHubSource(ProvenanceSource):
    """Gather background for github.com origins via the GitHub REST API."""

    name = "github"

    def __init__(self, header_resolver=None):
        """``header_resolver(url) -> dict`` supplies Authorization headers.

        Defaults to the store's per-endpoint resolver; injectable for tests.
        """
        self._resolve_headers = header_resolver or _default_header_resolver

    def matches(self, origin: Dict[str, Any]) -> bool:
        if not origin:
            return False
        if origin.get("type") == "github":
            return True
        url = origin.get("url") or ""
        host = (urlparse(url).hostname or "").lower()
        return host == "github.com" or host.endswith(".github.com")

    def _normalize_origin(self, origin: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ensure owner/repo/ref/path are present, parsing from url if needed."""
        if origin.get("owner") and origin.get("repo"):
            return {
                "owner": origin["owner"],
                "repo": origin["repo"],
                "ref": origin.get("ref") or "main",
                "path": (origin.get("path") or "").strip("/"),
            }
        return parse_github_origin(origin.get("url") or "")

    def _get_json(self, url: str, headers: Dict[str, str]) -> Tuple[Optional[Any], Optional[str]]:
        """GET ``url`` and return (json, error). Never raises on HTTP/network."""
        try:
            resp = requests.get(url, headers=headers, timeout=_TIMEOUT)
        except requests.RequestException as e:
            return None, str(e)
        if resp.status_code == 404:
            return None, "404"
        if not resp.ok:
            return None, f"{resp.status_code}: {resp.reason}"
        try:
            return resp.json(), None
        except ValueError as e:
            return None, f"bad json: {e}"

    def gather(self, origin: Dict[str, Any]) -> Background:
        norm = self._normalize_origin(origin)
        if not norm:
            bg = Background(source="github")
            bg.provenance = {"status": "error", "error": "unparseable github origin"}
            bg.confidence_reasons = ["could not parse origin URL"]
            return bg

        owner, repo = norm["owner"], norm["repo"]
        ref, path = norm["ref"], norm["path"]
        url_for_auth = f"https://github.com/{owner}/{repo}"
        try:
            headers = self._resolve_headers(url_for_auth)
        except Exception as e:  # forced-reauth etc. — degrade, don't crash
            logger.info("provenance: header resolution failed: %s", e)
            headers = {}
        headers = {**(headers or {}), "Accept": "application/vnd.github+json"}

        repo_json, repo_err = self._get_json(f"{_API}/repos/{owner}/{repo}", headers)
        license_json, _lic_err = self._get_json(
            f"{_API}/repos/{owner}/{repo}/license", headers
        )
        commits_url = (
            f"{_API}/repos/{owner}/{repo}/commits"
            f"?path={path}&sha={ref}&per_page=1"
        )
        commits_json, _commit_err = self._get_json(commits_url, headers)
        commit = (
            commits_json[0]
            if isinstance(commits_json, list) and commits_json
            else None
        )

        bg = build_background(norm, repo_json, license_json, commit)
        if repo_err and repo_err != "404":
            bg.publisher = {"status": "error", "error": repo_err}
            # re-roll confidence now that publisher is unknown
            bg.confidence, bg.confidence_reasons = assess_confidence(bg)
        return bg


def _default_header_resolver(url: str) -> Dict[str, str]:
    """Resolve auth headers via the store's per-endpoint resolver (gh CLI etc.).

    Imported lazily so the plugin/source can be unit-tested without the store
    package importable.
    """
    from skillberry_store.tools.endpoint_auth import resolve_auth_headers

    try:
        return resolve_auth_headers(url)
    except Exception:
        # ReauthRequired / OAuthRequired / missing config -> anonymous.
        return {}
