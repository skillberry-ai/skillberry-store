"""Network-free tests for the GitHub provenance source (pure mappers)."""

from skillberry_plugin_provenance.sources.base import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    LICENSE_COPYLEFT,
    LICENSE_NONE,
    LICENSE_PERMISSIVE,
    license_category,
)
from skillberry_plugin_provenance.sources.github_source import (
    GitHubSource,
    assess_confidence,
    build_background,
    build_license,
    build_provenance,
    build_publisher,
    parse_github_origin,
)

# ── captured-shape API fixtures (trimmed) ────────────────────────────────────

_REPO_JSON = {
    "name": "skills",
    "stargazers_count": 4200,
    "forks_count": 300,
    "open_issues_count": 12,
    "archived": False,
    "created_at": "2020-01-01T00:00:00Z",
    "pushed_at": "2026-06-01T00:00:00Z",
    "owner": {"login": "anthropics", "type": "Organization"},
}

_LICENSE_JSON = {
    "name": "LICENSE",
    "license": {"spdx_id": "MIT", "name": "MIT License"},
}

_COMMIT_JSON = {
    "sha": "abc123def456",
    "commit": {
        "committer": {"date": "2026-05-20T10:00:00Z"},
        "verification": {"verified": True, "reason": "valid"},
    },
}


# ── url parsing ──────────────────────────────────────────────────────────────


def test_parse_github_origin_full_tree_url():
    o = parse_github_origin(
        "https://github.com/anthropics/skills/tree/main/document-skills/pptx"
    )
    assert o == {
        "owner": "anthropics",
        "repo": "skills",
        "ref": "main",
        "path": "document-skills/pptx",
    }


def test_parse_github_origin_bare_repo_defaults():
    o = parse_github_origin("https://github.com/octocat/Hello-World.git")
    assert o == {"owner": "octocat", "repo": "Hello-World", "ref": "main", "path": ""}


def test_parse_github_origin_non_github_returns_none():
    assert parse_github_origin("https://example.com/x/y") is None
    assert parse_github_origin("") is None


# ── license classification ───────────────────────────────────────────────────


def test_license_category_mapping():
    assert license_category("MIT") == LICENSE_PERMISSIVE
    assert license_category("Apache-2.0") == LICENSE_PERMISSIVE
    assert license_category("GPL-3.0") == LICENSE_COPYLEFT
    assert license_category("AGPL-3.0") == LICENSE_COPYLEFT
    assert license_category(None) == LICENSE_NONE
    assert license_category("NOASSERTION") == "unknown"


def test_build_license_none_when_missing():
    lic = build_license(None)
    assert lic["category"] == LICENSE_NONE
    assert lic["spdx_id"] is None
    assert "all rights reserved" in lic["note"].lower()


# ── section mappers ──────────────────────────────────────────────────────────


def test_build_provenance_pins_commit_and_permalink():
    origin = {"owner": "anthropics", "repo": "skills", "ref": "main", "path": "x"}
    prov = build_provenance(origin, _COMMIT_JSON)
    assert prov["status"] == "ok"
    assert prov["commit_sha"] == "abc123def456"
    assert prov["permalink"].endswith("/tree/abc123def456/x")
    assert prov["committed_at"] == "2026-05-20T10:00:00Z"


def test_build_publisher_extracts_signals():
    pub = build_publisher(_REPO_JSON)
    assert pub["status"] == "ok"
    assert pub["owner"] == "anthropics"
    assert pub["owner_type"] == "Organization"
    assert pub["stars"] == 4200
    assert pub["repo_age_days"] is not None and pub["repo_age_days"] > 0


def test_build_publisher_unavailable_when_missing():
    assert build_publisher(None)["status"] == "unavailable"


# ── confidence rollup ────────────────────────────────────────────────────────


def test_confidence_high_for_reputable_permissive_verified():
    bg = build_background(
        {"owner": "anthropics", "repo": "skills", "ref": "main", "path": ""},
        _REPO_JSON,
        _LICENSE_JSON,
        _COMMIT_JSON,
    )
    assert bg.confidence == CONFIDENCE_HIGH
    assert bg.license["category"] == LICENSE_PERMISSIVE
    assert bg.integrity["commit_verified"] is True


def test_confidence_low_when_no_license():
    bg = build_background(
        {"owner": "x", "repo": "y", "ref": "main", "path": ""},
        _REPO_JSON,
        None,  # no license file
        _COMMIT_JSON,
    )
    assert bg.confidence == CONFIDENCE_LOW
    assert any("license" in r for r in bg.confidence_reasons)


def test_confidence_medium_for_copyleft_reputable():
    gpl = {"name": "LICENSE", "license": {"spdx_id": "GPL-3.0", "name": "GPL 3"}}
    bg = build_background(
        {"owner": "x", "repo": "y", "ref": "main", "path": ""},
        _REPO_JSON,
        gpl,
        _COMMIT_JSON,
    )
    assert bg.confidence == CONFIDENCE_MEDIUM


def test_assess_confidence_new_anonymous_repo_is_low():
    fresh = {
        "stargazers_count": 0,
        "owner": {"login": "newbie", "type": "User"},
        "created_at": "2026-06-10T00:00:00Z",  # days old
        "pushed_at": "2026-06-12T00:00:00Z",
    }
    bg = build_background(
        {"owner": "newbie", "repo": "z", "ref": "main", "path": ""},
        fresh,
        _LICENSE_JSON,  # permissive, so legality doesn't cap
        {"sha": "s", "commit": {"verification": {"verified": False}}},
    )
    assert bg.confidence == CONFIDENCE_LOW


# ── source wiring (mocked HTTP) ──────────────────────────────────────────────


def test_github_source_matches():
    src = GitHubSource(header_resolver=lambda url: {})
    assert src.matches({"type": "github"})
    assert src.matches({"url": "https://github.com/a/b"})
    assert not src.matches({"url": "https://gitlab.com/a/b"})


def test_github_source_gather_with_mocked_requests(monkeypatch):
    """gather() should stitch the three API calls into a Background."""
    import skillberry_plugin_provenance.sources.github_source as gh

    class _Resp:
        def __init__(self, status, payload):
            self.status_code = status
            self.ok = 200 <= status < 300
            self.reason = "OK"
            self._payload = payload

        def json(self):
            return self._payload

    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/repos/anthropics/skills"):
            return _Resp(200, _REPO_JSON)
        if url.endswith("/license"):
            return _Resp(200, _LICENSE_JSON)
        if "/commits" in url:
            return _Resp(200, [_COMMIT_JSON])
        return _Resp(404, {})

    monkeypatch.setattr(gh.requests, "get", fake_get)
    src = GitHubSource(header_resolver=lambda url: {"Authorization": "Bearer x"})
    bg = src.gather(
        {"type": "github", "url": "https://github.com/anthropics/skills/tree/main/x"}
    )
    assert bg.provenance["commit_sha"] == "abc123def456"
    assert bg.publisher["owner"] == "anthropics"
    assert bg.license["spdx_id"] == "MIT"
    assert bg.confidence == CONFIDENCE_HIGH
