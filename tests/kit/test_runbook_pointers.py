"""The three failure messages point to their runbook page (SPEC-0056 rule 13, brief #865).

`route.py`'s red-branch issue, `minutes.py`'s warning and `95%` line and `prepush.py`'s
`secret-scan` failure each name a page of `docs/runbooks/`: a path and never a value. No workflow
changes (rule 14). Saved responses and stand-in tools only, no network, invented data
(`example.com`). REQ-063 AC5.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_minutes import billed, case, minutes
from test_prepush import prepush, project, scanner, steps
from test_route import route  # the module, with `scripts/agk` on the path

ROOT = Path(__file__).resolve().parents[2]
RED = "docs/runbooks/red-default-branch.md"
BLOCKED = "docs/runbooks/actions-blocked.md"
LEAKED = "docs/runbooks/leaked-secret.md"
RUN = "https://example.com/run"


def test_the_red_issue_has_one_runbook_line():
    """REQ-063 AC5: rule 13, the one line of `red_body`."""
    lines = route.red_body("Lint", "abc1234", RUN).splitlines()
    assert [ln for ln in lines if ln.startswith("Runbook:")] == [f"Runbook: {RED}"]


def test_the_warning_names_the_blocked_page(repo, tmp_path):
    """REQ-063 AC5: rule 13, the warning past `minutes_warn`."""
    proc = minutes(repo, case(tmp_path))
    warning = [ln for ln in proc.stdout.splitlines() if ln.startswith("warning:")]
    assert len(warning) == 1 and BLOCKED in warning[0]


def test_the_95_percent_line_names_the_blocked_page(repo, tmp_path):
    """REQ-063 AC5: rule 13, the `95%` line."""
    proc = minutes(repo, billed(tmp_path, 1900), "--line", today="2026-10-19")
    assert "level 95%" in proc.stdout and BLOCKED in proc.stdout


def test_a_lower_level_line_names_no_page(repo, tmp_path):
    """REQ-063 AC5: rule 13 names the `95%` line, so the line of a lower level is unchanged."""
    proc = minutes(repo, billed(tmp_path, 1000), "--line", today="2026-10-19")
    assert "level 50%" in proc.stdout and BLOCKED not in proc.stdout


def test_a_scan_finding_names_the_leaked_page(repo, tmp_path):
    """REQ-063 AC5: rule 13, the `secret-scan` failure names the page and the run still stops."""
    project(repo)
    proc = prepush(repo, scan=scanner(tmp_path / "bin", 1))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert steps(proc.stdout)["secret-scan"] == "FAIL"
    assert LEAKED in proc.stdout


def test_a_clean_scan_names_no_page(repo, tmp_path):
    """REQ-063 AC5: rule 13, only a failure points to the page."""
    project(repo)
    proc = prepush(repo, scan=scanner(tmp_path / "bin", 0))
    assert steps(proc.stdout)["secret-scan"] == "ok"
    assert LEAKED not in proc.stdout


def test_a_missing_scanner_is_not_a_leak(repo):
    """REQ-063 AC5: the page applies to a finding (Q-865-1), and no scanner found none."""
    project(repo)
    proc = prepush(repo, scan=None)
    assert steps(proc.stdout)["secret-scan"] == "FAIL"
    assert LEAKED not in proc.stdout


@pytest.mark.parametrize("page", [RED, BLOCKED, LEAKED])
def test_each_page_named_exists_and_is_installed(page):
    """REQ-063 AC5: a message points to a page that a project has (rule 3)."""
    assert (ROOT / page).is_file()
    assert page in (ROOT / "kit" / "manifest.json").read_text(encoding="utf-8")


def test_no_workflow_names_a_page():
    """REQ-063 AC5: rule 14, the pointers live in the scripts and no workflow changes."""
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows
    assert not [w.name for w in workflows if "docs/runbooks/" in w.read_text(encoding="utf-8")]
