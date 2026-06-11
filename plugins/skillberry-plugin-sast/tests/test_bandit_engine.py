"""Tests for the Bandit SAST engine."""

import json

import pytest

from skillberry_plugin_sast.engines.bandit_engine import BanditEngine, parse_bandit_json
from skillberry_plugin_sast.engines.base import SEVERITY_HIGH, SEVERITY_MEDIUM

# A captured bandit JSON report (trimmed) — lets us test parsing without bandit.
_BANDIT_SAMPLE = json.dumps(
    {
        "results": [
            {
                "test_id": "B307",
                "test_name": "blacklist",
                "issue_severity": "MEDIUM",
                "issue_text": "Use of possibly insecure function - consider using safer ast.literal_eval.",
                "line_number": 2,
                "code": "1 x = input()\n2 eval(x)\n",
            },
            {
                "test_id": "B602",
                "test_name": "subprocess_popen_with_shell_equals_true",
                "issue_severity": "HIGH",
                "issue_text": "subprocess call with shell=True identified, security issue.",
                "line_number": 4,
                "code": "4 subprocess.call(cmd, shell=True)\n",
            },
        ]
    }
)


def test_parse_bandit_json_maps_fields_and_severity():
    findings = parse_bandit_json(_BANDIT_SAMPLE)
    assert len(findings) == 2

    f0 = findings[0]
    assert f0.engine == "bandit"
    assert f0.rule_id == "B307"
    assert f0.severity == SEVERITY_MEDIUM
    assert "ast.literal_eval" in f0.message
    assert f0.line == 2
    assert "eval(x)" in f0.snippet

    f1 = findings[1]
    assert f1.rule_id == "B602"
    assert f1.severity == SEVERITY_HIGH
    assert f1.line == 4


def test_parse_bandit_json_empty_results():
    assert parse_bandit_json(json.dumps({"results": []})) == []
    assert parse_bandit_json(json.dumps({})) == []


def test_parse_bandit_json_unknown_severity_defaults_medium():
    raw = json.dumps(
        {
            "results": [
                {
                    "test_id": "X",
                    "issue_severity": "WAT",
                    "issue_text": "",
                    "line_number": 1,
                }
            ]
        }
    )
    assert parse_bandit_json(raw)[0].severity == SEVERITY_MEDIUM


def test_engine_metadata():
    eng = BanditEngine()
    assert eng.name == "bandit"
    assert eng.supports("python") is True
    assert eng.supports("javascript") is False
    assert eng.supports(None) is True  # unknown language => attempt anyway


# ── live bandit run (skipped if bandit not installed) ────────────────────────

_engine_available = BanditEngine().is_available()


@pytest.mark.skipif(not _engine_available, reason="bandit not installed")
def test_scan_flags_dangerous_python():
    code = "import subprocess\nx = input()\neval(x)\nsubprocess.call(x, shell=True)\n"
    findings = BanditEngine().scan(code, filename="tool.py", language="python")
    assert findings, "expected bandit to flag eval/shell=True"
    rule_ids = {f.rule_id for f in findings}
    # B307 (eval) and/or B602 (shell=True) should appear.
    assert rule_ids & {"B307", "B602", "B604"}


@pytest.mark.skipif(not _engine_available, reason="bandit not installed")
def test_scan_clean_code_no_findings():
    findings = BanditEngine().scan(
        "x = 1 + 1\nprint(x)\n", filename="ok.py", language="python"
    )
    assert findings == []
