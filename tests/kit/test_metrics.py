"""Tests of scripts/agk/metrics.py (SPEC-0007 rules 1-16, 20-23). No network, no model, no `gh`."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest
from metrics import choose_action

FIXTURES = Path(__file__).parent / "fixtures" / "metrics"
TODAY = "2026-10-14"  # a Wednesday; the window is 2026-10-05 to 2026-10-12 (ISO week 2026-W41)
LAST = "<!-- agk-metrics 2026-W41 -->"


def metrics(repo, case: str | Path, *extra: str, today: str = TODAY, **env: str):
    api = FIXTURES / case if isinstance(case, str) else case
    return repo.run("metrics.py", "--api-dir", str(api), "--today", today, *extra, **env)


def table(body: str) -> dict[int, dict[str, str]]:
    lines = [ln for ln in body.splitlines() if ln.startswith("|")]
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = {}
    for ln in lines[2:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        rows[int(cells[0])] = dict(zip(header, cells, strict=True))
    return rows


def rows_of(repo, case: str, **kw) -> dict[int, dict[str, str]]:
    proc = metrics(repo, case, **kw)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return table(proc.stdout)


def test_ac1_title_and_window_are_the_iso_week_before_today(repo):
    """REQ-012 AC3: rule 12."""
    proc = repo.run("metrics.py", "--today", TODAY, "--print-title")
    assert proc.stdout == "agk metrics 2026-W41\n"
    proc = metrics(repo, "empty-week")
    assert proc.stdout.splitlines()[0] == "agk metrics 2026-W41 (window 2026-10-05 to 2026-10-12)"


@pytest.mark.parametrize(
    ("today", "title", "window"),
    [
        ("2026-10-12", "2026-W41", "2026-10-05 to 2026-10-12"),  # run on the Monday itself
        ("2026-10-18", "2026-W41", "2026-10-05 to 2026-10-12"),  # Sunday of the next week
        ("2027-01-04", "2026-W53", "2026-12-28 to 2027-01-04"),  # a year boundary
        ("2026-03-02", "2026-W09", "2026-02-23 to 2026-03-02"),  # a month boundary
    ],
)
def test_ac1_window_edges_and_boundaries(repo, today, title, window):
    """REQ-012 AC3: rule 12 (half-open ISO week, week label from the window's Monday)."""
    assert repo.run("metrics.py", "--today", today, "--print-title").stdout == (
        f"agk metrics {title}\n"
    )
    proc = repo.run("metrics.py", "--api-dir", str(FIXTURES / "empty-week"), "--today", today)
    assert f"(window {window})" in proc.stdout.splitlines()[0]


def test_ac1_a_different_today_in_the_same_week_gives_the_same_body(repo):
    """REQ-012 AC3: rule 21."""
    one = metrics(repo, "fix-lists-cleared", today="2026-10-12").stdout
    two = metrics(repo, "fix-lists-cleared", today="2026-10-18").stdout
    assert one == two


def test_ac1_two_runs_are_byte_identical_and_order_does_not_matter(repo, tmp_path):
    """REQ-012 AC3: rule 21 (the fixture is also run with its list reversed)."""
    one = metrics(repo, "cost-classes").stdout
    assert one == metrics(repo, "cost-classes").stdout
    shuffled = tmp_path / "shuffled"
    shutil.copytree(FIXTURES / "cost-classes", shuffled)
    pulls = json.loads((shuffled / "pulls.json").read_text())
    (shuffled / "pulls.json").write_text(json.dumps(list(reversed(pulls))))
    assert metrics(repo, shuffled).stdout == one


def test_ac1_empty_week_is_written(repo):
    """REQ-012 AC3: rule 14."""
    proc = metrics(repo, "empty-week")
    assert proc.returncode == 0
    assert "closed in window: 0; recorded: 0; unknown cells: 0" in proc.stdout
    assert proc.stdout.rstrip().endswith(LAST)
    assert "Derived from git and the GitHub REST API; no field is typed by an agent." in proc.stdout


def test_ac1_the_window_is_half_open(repo):
    """REQ-012 AC3: rule 12 and 20 (closed at the start is in; at the end or just before is out)."""
    proc = metrics(repo, "window-edges")
    assert sorted(table(proc.stdout)) == [141, 144]
    assert "closed in window: 2; recorded: 2" in proc.stdout


def test_ac1_merged_pr_without_verdicts_has_unknown_rounds_and_cost(repo):
    """REQ-012 AC2: rules 4, 5, 8, 9 and 10."""
    row = rows_of(repo, "no-verdict-merged")[101]
    assert row["state"] == "merged"
    assert row["source"] == "derived"
    assert row["rejected"] == "no"
    assert row["rejected_verdicts"] == "0"
    assert row["review_rounds"] == "unknown"
    assert row["merged_head_cleared"] == "unknown"
    assert row["cost_class"] == "unknown"
    assert row["hours_open_to_merge"] == "24.0"
    assert (row["additions"], row["deletions"], row["changed_files"]) == ("10", "2", "1")


def test_ac1_fix_lists_clear_and_hours(repo):
    """REQ-012 AC4: rules 3, 4, 5, 8 (rounds count fix-list comments; cleared names the head)."""
    row = rows_of(repo, "fix-lists-cleared")[102]
    assert row["review_rounds"] == "2"
    assert row["merged_head_cleared"] == "yes"
    assert row["rejected"] == "no"
    assert row["hours_open_to_merge"] == "30.0"
    assert row["cost_class"] == "M"


def test_ac1_a_verdict_line_with_trailing_text_is_not_a_verdict(repo):
    """REQ-012 AC1: rule 4 (the first line is exactly one of the three forms)."""
    row = rows_of(repo, "verdict-suffix")[171]
    assert row["review_rounds"] == "unknown"  # no verdict comment at all
    assert row["merged_head_cleared"] == "unknown"
    assert row["rejected"] == "no"
    assert row["rejected_verdicts"] == "0"
    assert row["cost_class"] == "unknown"


def test_ac1_cleared_naming_another_commit_is_no(repo):
    """REQ-012 AC2: rule 8."""
    row = rows_of(repo, "cleared-other-commit")[103]
    assert row["merged_head_cleared"] == "no"
    assert row["review_rounds"] == "0"


def test_ac1_rejected_verdict_makes_a_merged_pr_rejected(repo):
    """REQ-012 AC1: rule 4."""
    row = rows_of(repo, "verdict-rejected")[104]
    assert row["rejected"] == "yes"
    assert row["rejected_verdicts"] == "1"
    assert row["review_rounds"] == "1"
    assert row["merged_head_cleared"] == "yes"


def test_ac1_closed_unmerged_is_rejected_and_class_l(repo):
    """REQ-012 AC1: rules 4 and 9 (a closed unmerged pull request is L)."""
    row = rows_of(repo, "closed-unmerged")[105]
    assert row["state"] == "closed"
    assert row["rejected"] == "yes"
    assert row["cost_class"] == "L"
    assert row["hours_open_to_merge"] == "-"
    assert row["merged_head_cleared"] == "-"
    assert row["tests_before"] == "-"


def test_ac1_cost_classes_s_m_l_and_unknown(repo):
    """REQ-012 AC4: rule 9."""
    rows = rows_of(repo, "cost-classes")
    assert rows[111]["cost_class"] == "S"  # 0 rounds, 5 h
    assert rows[112]["cost_class"] == "M"  # 2 rounds, 48 h
    assert rows[113]["cost_class"] == "L"  # 3 rounds
    assert rows[114]["cost_class"] == "unknown"  # no verdict comment
    assert rows[115]["cost_class"] == "L"  # 0 rounds but 96 h
    proc = metrics(repo, "cost-classes")
    assert "cost S=1 M=1 L=2 unknown=1" in proc.stdout


def test_ac1_files_give_adrs_deviations_and_size(repo):
    """REQ-012 AC2: rules 7 and 8 (only added files count)."""
    row = rows_of(repo, "files")[121]
    assert row["adrs_added"] == "1"
    assert row["deviations"] == "1"
    assert (row["additions"], row["deletions"], row["changed_files"]) == ("300", "4", "5")


def test_ac1_blocked_weakenings_count_commits_whose_failing_step_is_in_the_set(repo):
    """REQ-012 AC1: rules 6 and 13."""
    row = rows_of(repo, "governance-split")[131]
    assert row["blocked_weakenings"] == "1"  # check_adrs blocked a head commit; Lint did not
    assert row["governance_failures"] == "2"


def test_ac1_unsplit_governance_step_is_unknown(repo):
    """REQ-012 AC2: rule 13 (until the workflow has one step per check)."""
    row = rows_of(repo, "governance-unsplit")[132]
    assert row["blocked_weakenings"] == "unknown"
    assert row["governance_failures"] == "1"


def test_ac1_missing_inputs_are_unknown_not_zero_or_no(repo):
    """REQ-012 AC2: rules 10 and 23."""
    proc = metrics(repo, "missing-comments")
    row = table(proc.stdout)[151]
    for field in ("rejected", "rejected_verdicts", "review_rounds", "cost_class"):
        assert row[field] == "unknown", field
    assert row["merged_head_cleared"] == "unknown"
    count = sum(1 for cell in row.values() if cell == "unknown")
    assert f"unknown cells: {count}" in proc.stdout
    assert count >= 6
    assert proc.returncode == 0


def test_ac1_unknown_cells_are_counted_in_the_totals_line(repo):
    """REQ-012 AC2: rule 10."""
    proc = metrics(repo, "no-verdict-merged")
    row = table(proc.stdout)[101]
    cells = sum(1 for c in row.values() if c == "unknown")
    assert f"unknown cells: {cells}" in proc.stdout


def test_ac1_incomplete_week_is_flagged_and_exits_1(repo):
    """REQ-012 AC3: rule 16."""
    proc = metrics(repo, "incomplete")
    assert proc.returncode == 1
    assert proc.stdout.splitlines()[0].startswith("INCOMPLETE")
    assert "closed in window: 2; recorded: 1" in proc.stdout
    assert sorted(table(proc.stdout)) == [161]


def test_ac1_complete_week_has_no_flag_line(repo):
    """REQ-012 AC3: rules 14 and 16."""
    proc = metrics(repo, "fix-lists-cleared")
    assert proc.stdout.startswith("agk metrics 2026-W41 (window")
    assert "INCOMPLETE" not in proc.stdout


def test_ac1_totals_line_counts_the_core_fields(repo):
    """REQ-012 AC3: rule 14."""
    proc = metrics(repo, "cost-classes")
    assert "totals: rejected=0 blocked_weakenings=0 deviations=0 cost S=1 M=1 L=2 unknown=1" in (
        proc.stdout
    )
    proc = metrics(repo, "closed-unmerged")
    assert "rejected=1" in proc.stdout


# --- git-derived fields: built on a real repository in tmp_path ---------------------------------


def git_case(repo, tmp_path: Path) -> Path:
    repo.commit(
        {
            "config/protected-paths.txt": "scripts/agk/\n.github/\ndocs/requirements.md\n",
            "tests/test_a.py": "def test_one():\n    pass\n\n\ndef test_two():\n    pass\n",
            "tests/test_b.py": "async def test_three():\n    pass\n",
            "tests/notes.txt": "def test_not_python():\n",
        },
        "base",
    )
    base = repo.git("rev-parse", "HEAD").strip()
    repo.commit({"tests/test_c.py": "def test_four():\n    pass\n"}, "squash merge")
    merged = repo.git("rev-parse", "HEAD").strip()
    api = tmp_path / "api"
    api.mkdir()
    pull = {
        "number": 7, "state": "closed", "merged": True, "merged_at": "2026-10-07T00:00:00Z",
        "created_at": "2026-10-06T00:00:00Z", "closed_at": "2026-10-07T00:00:00Z",
        "merge_commit_sha": merged, "head": {"sha": "1" * 40}, "base": {"sha": base},
        "additions": 1, "deletions": 0, "changed_files": 3,
    }  # fmt: skip
    (api / "pulls.json").write_text(json.dumps([{**pull, "updated_at": pull["closed_at"]}]))
    (api / "pull-7.json").write_text(json.dumps(pull))
    files = [
        ("scripts/agk/metrics.py", "added"),
        ("scripts/agk/common.py", "modified"),
        (".github/workflows/metrics.yml", "added"),
        ("README.md", "modified"),
    ]
    (api / "files-7.json").write_text(json.dumps([{"filename": f, "status": s} for f, s in files]))
    (api / "comments-7.json").write_text("[]")
    (api / "commits-7.json").write_text(json.dumps([{"sha": "1" * 40}]))
    return api


def test_ac1_protected_classes_and_test_counts_come_from_git(repo, tmp_path):
    """REQ-012 AC2: rule 8 (classes at the parent of the merge commit; static test counts)."""
    api = git_case(repo, tmp_path)
    row = table(metrics(repo, api).stdout)[7]
    assert row["protected_classes"] == ".github/, scripts/agk/"
    assert row["tests_before"] == "3"
    assert row["tests_after"] == "4"


def test_ac1_unknown_commits_give_unknown_git_fields(repo):
    """REQ-012 AC2: rule 10 (the merge commit is not in this repository)."""
    row = rows_of(repo, "no-verdict-merged")[101]
    assert row["protected_classes"] == "unknown"
    assert row["tests_before"] == "unknown"
    assert row["tests_after"] == "unknown"


# --- the issue action ---------------------------------------------------------------------------


def issue(number: int, week: str = "2026-W41", extra: str = "") -> dict:
    return {
        "number": number,
        "title": f"agk metrics {week}",
        "body": f"x\n<!-- agk-metrics {week} -->{extra}\n",
    }


def test_ac1_choose_action_creates_when_there_is_no_issue_for_the_week():
    """REQ-012 AC3: rule 15 and 22."""
    assert choose_action([], "2026-W41") == "create"
    assert choose_action([issue(3, "2026-W40")], "2026-W41") == "create"


def test_ac1_choose_action_updates_the_issue_of_the_week_never_none():
    """REQ-012 AC3: rule 15 and 22."""
    assert choose_action([issue(3, "2026-W40"), issue(4)], "2026-W41") == "update 4"


def test_ac1_choose_action_updates_the_lowest_of_duplicates():
    """REQ-012 AC3: rule 15 and 22."""
    assert choose_action([issue(9), issue(5)], "2026-W41") == "update 5"


def test_ac1_cli_print_action_and_duplicate_flag(repo, tmp_path):
    """REQ-012 AC3: rule 15 (--issues FILE, --print-action, duplicate line in the body)."""
    path = tmp_path / "issues.json"
    path.write_text(json.dumps([issue(9), issue(5)]))
    out = repo.run("metrics.py", "--today", TODAY, "--issues", str(path), "--print-action")
    assert out.stdout == "update 5\n"
    path.write_text("[]")
    out = repo.run("metrics.py", "--today", TODAY, "--issues", str(path), "--print-action")
    assert out.stdout == "create\n"
    path.write_text(json.dumps([issue(9), issue(5)]))
    body = metrics(repo, "empty-week", "--issues", str(path), "--print-body")
    assert body.stdout.splitlines()[0] == "duplicate metrics issues: #5,#9; #5 is the one updated"
    assert body.stdout.splitlines()[1].startswith("agk metrics 2026-W41 (window")


def test_ac1_usage_errors_exit_2(repo):
    """REQ-012 AC3: rule 15."""
    assert repo.run("metrics.py", "--today", "yesterday").returncode == 2
    assert repo.run("metrics.py", "--bogus").returncode == 2
    assert repo.run("metrics.py", "--print-action", "--print-title").returncode == 2


def test_ac1_the_script_writes_nothing_and_never_calls_gh(repo, tmp_path):
    """REQ-012 AC3: rules 12 and 17 (a stub `gh` on PATH records any call; there is none)."""
    stub = tmp_path / "bin"
    stub.mkdir()
    marker = tmp_path / "gh-called"
    gh = stub / "gh"
    gh.write_text(f"#!/bin/sh\ntouch {marker}\nexit 1\n")
    gh.chmod(0o755)
    before = sorted(p.name for p in repo.root.iterdir())
    proc = metrics(repo, "cost-classes", PATH=f"{stub}{os.pathsep}{os.environ['PATH']}")
    assert proc.returncode == 0
    assert not marker.exists()
    assert sorted(p.name for p in repo.root.iterdir()) == before
