"""Tests of .github/workflows/product-report.yml (SPEC-0011 rules 15, 16, 17, 18)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess  # nosec B404 - fixed argument lists, and a stub `gh`
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "product-report.yml"
ALLOWED_GH = {"issue create", "issue edit", "label create"}
FIXTURE = Path(__file__).parent / "fixtures" / "report" / "kinds" / "facts.json"


def text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def top_block(name: str) -> str:
    """The indented lines under a top-level key."""
    match = re.search(rf"^{name}:\s*\n((?:[ \t]+.*\n|\n)*)", text(), flags=re.M)
    assert match, name
    return match.group(1)


def script() -> str:
    return text().split("run: |", 1)[1]


def test_ac1_name_and_triggers_are_only_schedule_and_workflow_dispatch():
    """REQ-018 AC1: rule 15."""
    assert re.search(r"^name: product-report$", text(), flags=re.M)
    keys = re.findall(r"^  ([a-z_]+):", top_block("on"), flags=re.M)
    assert sorted(keys) == ["schedule", "workflow_dispatch"]


def test_ac1_one_weekly_cron_monday_0713_utc():
    """REQ-018 AC1: rule 15 (after the metrics at 06:43, off the hour and half hour)."""
    crons = re.findall(r"^\s*-\s*cron:\s*[\"']([^\"']+)[\"']", text(), flags=re.M)
    assert crons == ["13 7 * * 1"]


def test_ac1_dispatch_takes_an_optional_today_input():
    """REQ-018 AC1: rule 15."""
    block = top_block("on").split("workflow_dispatch:", 1)[1]
    assert re.search(r"^      today:\s*$", block, flags=re.M)
    assert "required: false" in block


def test_ac1_the_input_reaches_the_script_through_env_not_inline():
    """REQ-018 AC1: no expression is interpolated into the shell."""
    assert "INPUT_TODAY: ${{ github.event.inputs.today }}" in text()
    assert "${{" not in script()


def test_ac1_permissions_are_exactly_the_five_of_rule_15():
    """REQ-018 AC1: rule 15 (contents, pull-requests, checks, actions read; issues write)."""
    lines = [ln.strip() for ln in top_block("permissions").splitlines() if ln.strip()]
    assert sorted(lines) == [
        "actions: read",
        "checks: read",
        "contents: read",
        "issues: write",
        "pull-requests: read",
    ]
    assert text().count("permissions:") == 1  # none per job


def test_ac1_every_action_is_pinned_to_a_full_commit_sha():
    """REQ-018 AC1: rule 15."""
    uses = re.findall(r"^\s*-?\s*uses:\s*(.+)$", text(), flags=re.M)
    assert uses
    for line in uses:
        assert re.fullmatch(r"\S+@[0-9a-f]{40}\s+# v\d+(\.\d+){1,2}", line.strip()), line


def test_ac1_checkout_is_full_and_the_job_runs_only_on_the_default_branch():
    """REQ-018 AC1: rule 15 (a single job, the default branch only, a full checkout)."""
    assert re.search(r"fetch-depth:\s*0", text())
    assert "github.ref_name == github.event.repository.default_branch" in text()
    assert len(re.findall(r"^  [a-z-]+:\s*$", top_block("jobs"), flags=re.M)) == 1


def test_ac1_no_pull_request_target_and_no_secret_but_the_token():
    """REQ-018 AC1: rule 18."""
    assert "pull_request_target" not in text()
    assert re.findall(r"secrets\.([A-Z_]+)", text()) == ["GITHUB_TOKEN"]


def test_ac1_only_the_allowed_gh_verbs_are_used():
    """REQ-018 AC1: rule 16 (create or edit the one issue, create the label)."""
    verbs = set(
        re.findall(r"\bgh ((?:issue|label|pr|api|repo|run|workflow|release) [a-z-]+)", text())
    )
    assert verbs
    assert verbs <= ALLOWED_GH, verbs - ALLOWED_GH


def test_ac1_nothing_else_writes():
    """REQ-018 AC1: rule 16 (no git write, no push, no comment, no close, no merge)."""
    code = "\n".join(ln for ln in text().splitlines() if not ln.lstrip().startswith("#"))
    for forbidden in (
        "git push",
        "git commit",
        "gh pr",
        "issue close",
        "issue comment",
        "--method",
    ):
        assert forbidden not in code, forbidden


def test_ac1_the_report_comes_from_the_facts_file_and_the_script_alone():
    """REQ-018 AC1: rule 15 (facts.py into a file, product_report.py --facts on it)."""
    run = script()
    assert 'scripts/agk/facts.py --today "$today"' in run
    assert 'scripts/agk/product_report.py --facts "$facts"' in run
    assert "--print-action" in run
    assert "gh issue list" not in run  # the issues come through the facts document


def test_ac1_a_missing_report_writes_nothing_and_fails():
    """REQ-018 AC1: rule 16."""
    run = script()
    assert "nothing written" in run
    assert run.count("exit 1") == 2


# --- the shell body, run against a stub `gh` and the facts of a fixture -------------------------


def body_with_facts(tmp_path: Path, issues: list[dict]) -> Path:
    """The run block with facts.py replaced by a copy of the fixture (issues set), and a stub gh."""
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc["issues"] = issues
    facts = tmp_path / "source.json"
    facts.write_text(json.dumps(doc), encoding="utf-8")
    lines = []
    for line in script().splitlines():
        if line.strip().startswith("python3 scripts/agk/facts.py"):
            line = f'cp "{facts}" "$facts"'
        lines.append(re.sub(r"^ {10}", "", line))
    (tmp_path / "run.sh").write_text("\n".join(lines) + "\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(f'#!/bin/sh\necho "$@" >> "{tmp_path}/gh-calls"\n', encoding="utf-8")
    gh.chmod(0o755)
    return tmp_path / "run.sh"


def run_body(tmp_path: Path, issues: list[dict], today: str = "2026-10-14"):
    script_file = body_with_facts(tmp_path, issues)
    (tmp_path / "scripts").symlink_to(ROOT / "scripts")
    env = {
        "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(tmp_path),
        "INPUT_TODAY": today,
        "GITHUB_REPOSITORY": "demo-org/demo-repo",
        "GH_TOKEN": "unused",
    }
    bash = shutil.which("bash") or "bash"
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell string
        [bash, "-eo", "pipefail", str(script_file)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    log = tmp_path / "gh-calls"
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return proc, calls


def test_ac1_with_no_issue_for_the_week_it_creates_the_label_and_the_issue(tmp_path):
    """REQ-018 AC1: rule 16 (create)."""
    proc, calls = run_body(tmp_path, [])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert calls[0].startswith("label create agk-product-report")
    assert calls[1].startswith(
        "issue create --title agk product report 2026-W41 --label agk-product-report --body-file"
    )
    assert len(calls) == 2


def test_ac1_with_an_issue_for_the_week_it_edits_that_issue_in_place(tmp_path):
    """REQ-018 AC1: rule 16 (update N, the body replaced)."""
    issues = [
        {"number": 31, "title": "agk product report 2026-W41", "label": "agk-product-report"},
        {"number": 30, "title": "agk product report 2026-W40", "label": "agk-product-report"},
    ]
    proc, calls = run_body(tmp_path, issues)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert len(calls) == 1
    assert calls[0].startswith("issue edit 31 --title agk product report 2026-W41 --body-file")


def test_ac1_two_issues_for_the_week_edit_the_lowest_and_print_the_notice(tmp_path):
    """REQ-018 AC1: rule 16 (as metrics)."""
    issues = [
        {"number": 31, "title": "agk product report 2026-W41", "label": "agk-product-report"},
        {"number": 30, "title": "agk product report 2026-W41", "label": "agk-product-report"},
    ]
    proc, calls = run_body(tmp_path, issues)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert calls[0].startswith("issue edit 30 ")
    assert "duplicate product report issues: #30,#31; #30 is the one updated" in proc.stdout


def test_ac1_a_dispatch_for_an_earlier_day_names_that_weeks_issue(tmp_path):
    """REQ-018 AC1: rule 15 (`today` backfills a week)."""
    proc, calls = run_body(tmp_path, [], today="2026-10-07")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "issue create --title agk product report 2026-W40 " in calls[1]
