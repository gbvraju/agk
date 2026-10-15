"""Tests of scripts/agk/drift_audit.py (SPEC-0004 rules 5-12, 13-15, 18-20, 23)."""

from __future__ import annotations

import ast
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import drift_fixtures as fx
import pytest
from drift_audit import choose_action

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "agk" / "drift_audit.py"
TODAY = "2026-10-15"
SUMMARY = re.compile(
    r"^agk drift audit (\d{4}-\d{2}-\d{2}) \(window (\S+) to (\S+)\): findings=(\d+)"
    r" D1=(\d+) D2=(\d+) D3=(\d+) D4=(\d+) D5=(\d+) D6=(\d+)$"
)
FINDING = re.compile(r"^- (D\d) (.+?) \| (.+?) \| (.+)$")


def audit(root: Path, *extra: str, today: str | None = TODAY):
    args = [sys.executable, str(SCRIPT), *extra]
    if today:
        args += ["--today", today]
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        args, cwd=root, capture_output=True, text=True, env=fx.clean_env()
    )


def findings(root: Path, *extra: str, today: str | None = TODAY) -> list[tuple[str, str, str, str]]:
    proc = audit(root, *extra, today=today)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return [m.groups() for line in proc.stdout.splitlines() if (m := FINDING.match(line))]


def codes(root: Path, *extra: str, today: str | None = TODAY) -> list[str]:
    return [f[0] for f in findings(root, *extra, today=today)]


@pytest.fixture
def repo(tmp_path):
    return fx.base(tmp_path / "repo")


# --- the report ---------------------------------------------------------------------------------


def test_ac1_clean_repository_has_no_findings(repo):
    """REQ-011 AC1: rule 18 (a clean repository)."""
    proc = audit(repo.root)
    lines = proc.stdout.splitlines()
    summary = SUMMARY.match(lines[0])
    assert summary, lines[0]
    assert summary.group(1) == TODAY and summary.group(4) == "0"
    assert summary.group(2) == "2026-10-08"
    assert summary.group(3) == TODAY
    assert not [ln for ln in lines if FINDING.match(ln)]


def test_ac1_report_counts_residual_bullets_without_a_due_date(repo):
    """REQ-011 AC1: rule 9. They are counted, not findings."""
    out = audit(repo.root).stdout
    assert "Residual bullets without a due date: 1 (not findings)." in out


def test_ac1_report_ends_with_the_inactivity_note_and_the_marker(repo):
    """REQ-011 AC1: rules 13 and 23."""
    lines = audit(repo.root).stdout.rstrip("\n").splitlines()
    assert lines[-1] == "<!-- agk-drift-audit -->"
    assert "inactivity" in lines[-2] and "workflow_dispatch" in lines[-2]


def test_ac1_same_repository_and_date_give_byte_identical_reports(repo):
    """REQ-011 AC1: rule 19."""
    fx.add_protected_change(repo, 3)
    fx.draft_spec(repo, 30)
    first, second = audit(repo.root), audit(repo.root)
    assert first.stdout == second.stdout and first.stdout


def test_ac1_findings_are_sorted_by_code_then_subject(repo):
    """REQ-011 AC1: rules 11 and 19."""
    fx.add_protected_change(repo, 2)
    fx.add_protected_change(repo, 3)
    fx.draft_spec(repo, 30)
    fx.proposed_adr(repo, "2026-09-20")
    found = findings(repo.root)
    assert found == sorted(found, key=lambda f: (f[0], f[1], f[3]))
    assert [f[0] for f in found].count("D1") == 2


def test_ac1_the_script_writes_nothing(repo):
    """REQ-011 AC1: rules 2 and 19 (before and after snapshot)."""
    fx.add_protected_change(repo, 3)
    before = fx.snapshot(repo.root)
    assert audit(repo.root).returncode == 0
    assert fx.snapshot(repo.root) == before


def test_ac1_the_script_has_no_network_or_process_imports():
    """REQ-011 AC1: rules 3 and 19."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    forbidden = {"subprocess", "socket", "urllib", "http", "ftplib", "smtplib", "requests", "ssl"}
    assert not names & forbidden
    assert names <= set(sys.stdlib_module_names) | {"common", "reviewers"}


def test_ac1_findings_never_quote_file_content(repo):
    """REQ-011 AC1: rule 11 (principle 8)."""
    mark = "UNIQUE-RESIDUAL-WORDS-NOT-TO-BE-ECHOED"
    repo.edit("docs/adr/0001-demo.md", "open item", f"{mark} (due 2026-01-01)")
    repo.commit(1)
    out = audit(repo.root).stdout
    assert any(f[0] == "D4" for f in findings(repo.root))
    assert mark not in out


def test_ac1_usage_errors_exit_2(repo):
    """REQ-011 AC1: rule 5."""
    assert audit(repo.root, "--nope").returncode == 2
    assert audit(repo.root, today="15-10-2026").returncode == 2
    assert audit(repo.root, "--open-issues", "x").returncode == 2


# --- D1 -----------------------------------------------------------------------------------------


def test_ac1_d1_protected_change_without_an_adr_is_found(repo):
    """REQ-011 AC1: rules 6 and 18."""
    sha = fx.add_protected_change(repo, 3)
    found = findings(repo.root)
    assert [f[:2] for f in found if f[0] == "D1"] == [("D1", sha[:12])]
    assert "`.claude/`" in [f for f in found if f[0] == "D1"][0][3]


def test_ac1_d1_outside_the_window_is_not_found(repo):
    """REQ-011 AC1: rules 5 and 18."""
    fx.add_protected_change(repo, 20)
    assert "D1" not in codes(repo.root)


def test_ac1_d1_covered_by_an_adr_in_the_same_commit_is_not_found(repo):
    """REQ-011 AC1: rules 6 and 18."""
    fx.add_protected_change(repo, 3, covered=True)
    assert "D1" not in codes(repo.root)


def test_ac1_d1_adr_naming_only_another_class_does_not_cover(repo):
    """REQ-011 AC1: rule 6. The ADR must name every touched class."""
    repo.write(".claude/settings.json", '{"n": 1}\n')
    repo.write("scripts/agk/tool.py", "x = 2\n")
    repo.write(
        "docs/adr/0091-partial.md", "# ADR-0091: P\n\n- Status: Accepted\n\n`.claude/` only\n"
    )
    repo.commit(3)
    found = [f for f in findings(repo.root) if f[0] == "D1"]
    assert len(found) == 2  # no single ADR names every touched class, as in the per-PR check
    assert {c for c in (".claude/", "scripts/agk/") if any(f"`{c}`" in f[3] for f in found)} == {
        ".claude/",
        "scripts/agk/",
    }


def test_ac1_d1_status_only_edit_of_requirements_is_exempt(repo):
    """REQ-011 AC1: rule 6 (the Status-only exemption)."""
    repo.edit("docs/requirements.md", "- Status: planned", "- Status: in-progress")
    repo.commit(2)
    assert "D1" not in codes(repo.root)
    repo.edit("docs/requirements.md", "AC1 another", "AC1 changed")
    repo.commit(1)
    assert "D1" in codes(repo.root)


def test_ac1_d1_status_only_edit_of_an_adr_does_not_cover(repo):
    """REQ-011 AC1: rule 6 (not a Status-only edit)."""
    repo.edit("docs/adr/0001-demo.md", "Status: Accepted", "Status: Superseded")
    repo.write(".claude/settings.json", '{"n": 5}\n')
    repo.commit(3)
    assert "D1" in codes(repo.root)


@pytest.mark.parametrize(("days_ago", "expected"), [(7, True), (8, False), (0, True)])
def test_ac1_window_boundary_day_is_tested_on_both_sides(tmp_path, days_ago, expected):
    """REQ-011 AC1: rules 5 and 19. Seven days back is inside, eight is outside."""
    repo = fx.base(tmp_path / "r")
    fx.add_protected_change(repo, days_ago)
    assert ("D1" in codes(repo.root)) is expected


def test_ac1_d1_only_looks_at_first_parent_commits_of_the_default_branch(repo):
    """REQ-011 AC1: rule 6 (first-parent) and 4 (default branch only)."""
    repo.git("checkout", "-q", "-b", "side")
    fx.add_protected_change(repo, 3)
    repo.git("checkout", "-q", "main")
    assert "D1" not in codes(repo.root)


# --- D2, D3 -------------------------------------------------------------------------------------


def test_ac1_d2_done_requirement_without_a_marker_is_found(repo):
    """REQ-011 AC1: rules 7 and 18."""
    repo.edit("docs/requirements.md", "- Status: planned", "- Status: done")
    repo.commit(30)
    found = [f for f in findings(repo.root) if f[0] == "D2"]
    assert [f[1] for f in found] == ["REQ-002"]
    repo.write("tests/test_more.py", '"""REQ-002 AC1"""\n')
    repo.commit(30)
    assert "D2" not in codes(repo.root)


def test_ac1_d3_stale_draft_spec_and_proposed_adr_are_found(repo):
    """REQ-011 AC1: rules 8 and 18."""
    fx.draft_spec(repo, 30)
    fx.proposed_adr(repo, "2026-09-25")
    found = {(f[0], f[1]) for f in findings(repo.root) if f[0] == "D3"}
    assert found == {("D3", "docs/specs/0002-draft.md"), ("D3", "docs/adr/0002-proposed.md")}


@pytest.mark.parametrize(("age", "stale"), [(14, False), (15, True)])
def test_ac1_d3_limit_is_fourteen_days_for_both_kinds(tmp_path, age, stale):
    """REQ-011 AC1: rule 8 (N = 14, older than N)."""
    repo = fx.base(tmp_path / "r")
    fx.draft_spec(repo, age)
    adr_date = fx.TODAY.fromordinal(fx.TODAY.toordinal() - age).isoformat()
    fx.proposed_adr(repo, adr_date)
    assert [f[1] for f in findings(repo.root) if f[0] == "D3"] == (
        ["docs/adr/0002-proposed.md", "docs/specs/0002-draft.md"] if stale else []
    )


def test_ac1_d3_fresh_or_decided_documents_are_not_found(repo):
    """REQ-011 AC1: rule 8. Approved specs and Accepted ADRs are never stale."""
    assert "D3" not in codes(repo.root)


# --- D4 -----------------------------------------------------------------------------------------


def test_ac1_d4_overdue_residual_in_an_adr_is_found(repo):
    """REQ-011 AC1: rules 9 and 18."""
    fx.overdue_adr_residual(repo)
    found = [f for f in findings(repo.root) if f[0] == "D4"]
    assert [f[1] for f in found] == ["docs/adr/0001-demo.md"]


def test_ac1_d4_future_due_date_is_not_found_and_the_boundary_is_the_run_date(repo):
    """REQ-011 AC1: rule 9. A date before the run date is overdue; the run date itself is not."""
    repo.edit("docs/adr/0001-demo.md", "open item", "open item (due 2026-10-14)")
    repo.commit(1)
    assert "D4" in codes(repo.root)
    assert "D4" not in codes(repo.root, today="2026-10-14")
    repo.edit("docs/adr/0001-demo.md", "(due 2026-10-14)", "(due 2026-10-15)")
    repo.commit(0)
    assert "D4" not in codes(repo.root)


def test_ac1_d4_register_lines_past_future_and_malformed(repo):
    """REQ-011 AC1: rules 9 and 18 (amendments 5)."""
    fx.register(
        repo,
        [
            "- docs/adr/0003-x.md 2026-10-01 | an old item | (due 2026-01-01) | open",
            "- docs/adr/0004-y.md 2026-10-01 | a later item | (due 2027-01-01) | open",
            "- this line has no fields",
            "- a | b | (due 2026-13-45) | open",
        ],
    )
    found = [f for f in findings(repo.root) if f[0] == "D4"]
    subjects = sorted(f[1] for f in found)
    assert subjects == [
        "docs/adr/0003-x.md 2026-10-01",
        "docs/runs/residuals.md:7",
        "docs/runs/residuals.md:8",
    ]
    by_subject = {f[1]: f[3] for f in found}
    assert "malformed" in by_subject["docs/runs/residuals.md:7"]
    assert "overdue" in by_subject["docs/adr/0003-x.md 2026-10-01"]


def test_ac1_d4_register_text_with_a_pipe_still_parses(repo):
    """REQ-011 AC1: rule 9. Source is the first field, status the last, the date the one before."""
    fx.register(repo, ["- docs/adr/0003-x.md 2026-10-01 | has | a pipe | (due 2027-02-02) | open"])
    assert "D4" not in codes(repo.root)


def test_ac1_d4_without_a_register_reads_only_adr_and_spec_bullets(repo):
    """REQ-011 AC1: rule 9."""
    (repo.root / "docs" / "runs" / "residuals.md").unlink()
    repo.commit(1)
    assert audit(repo.root).returncode == 0


# --- D5, D6 -------------------------------------------------------------------------------------


def test_ac1_d5_hand_edited_codeowners_is_found(repo):
    """REQ-011 AC1: rules 10 and 18."""
    repo.write(".github/CODEOWNERS", "/docs/ @someone\n")
    repo.commit(1)
    assert [f[1] for f in findings(repo.root) if f[0] == "D5"] == [".github/CODEOWNERS"]


def test_ac1_d5_placeholder_team_is_found(repo):
    """REQ-011 AC1: rules 10 and 18."""
    repo.edit("config/reviewers.yaml", "@demo-org/maintainers", "@REPLACE-ME")
    repo.commit(1)
    repo.write(
        ".github/CODEOWNERS",
        fx.reviewers.render_codeowners(
            fx.reviewers.parse((repo.root / "config/reviewers.yaml").read_text(encoding="utf-8"))
        ),
    )
    repo.commit(1)
    found = [f for f in findings(repo.root) if f[0] == "D5"]
    assert [f[1] for f in found] == ["config/reviewers.yaml"]
    assert "placeholder" in found[0][3]


def test_ac1_d5_protected_class_differing_from_the_list_is_found(repo):
    """REQ-011 AC1: rule 10."""
    repo.write("config/protected-paths.txt", ".claude/\ndocs/requirements.md\n")
    repo.commit(1)
    found = [f for f in findings(repo.root) if f[0] == "D5"]
    assert found and "protected-paths" in found[0][3]


def test_ac1_d5_missing_codeowners_is_found(repo):
    """REQ-011 AC1: rule 10."""
    (repo.root / ".github" / "CODEOWNERS").unlink()
    repo.commit(1)
    assert "D5" in codes(repo.root)


def test_ac1_d5_adopt_mode_compares_only_the_marked_block(repo):
    """REQ-011 AC1: rule 10 (an adopted repository)."""
    own = fx.BASE_FILES[".github/CODEOWNERS"]
    repo.write("agk.toml", 'mode = "adopt"\ndefault_branch = "main"\ntest_dirs = ["tests"]\n')
    repo.write(".github/CODEOWNERS", "* @owner\n# >>> agk\n" + own + "# <<< agk\n")
    repo.commit(1)
    assert "D5" not in codes(repo.root)


def test_ac2_d6_duplicate_audit_issues_are_reported_in_the_body(repo):
    """REQ-011 AC2: rule 15."""
    found = [f for f in findings(repo.root, "--open-issues", "7 3") if f[0] == "D6"]
    assert len(found) == 1 and found[0][1] == "#3,#7"
    assert "duplicate audit issues" in found[0][3]
    assert not [f for f in findings(repo.root, "--open-issues", "7") if f[0] == "D6"]


# --- the issue (rules 13-15, 20) -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("open_issues", "has_findings", "expected"),
    [
        ([], True, "create"),
        ([5], True, "update 5"),
        ([9, 4], True, "update 4"),
        ([], False, "none"),
        ([5], False, "none"),
        ([9, 4], False, "none"),
    ],
)
def test_ac2_choose_action(open_issues, has_findings, expected):
    """REQ-011 AC2: rules 14, 15 and 20."""
    assert choose_action(open_issues, has_findings) == expected


def test_ac2_print_action_follows_the_report(repo):
    """REQ-011 AC2: rules 13-15. A clean run prints none, a run with findings prints the action."""
    assert audit(repo.root, "--print-action").stdout.strip() == "none"
    assert audit(repo.root, "--print-action", "--open-issues", "4").stdout.strip() == "none"
    fx.add_protected_change(repo, 3)
    assert audit(repo.root, "--print-action").stdout.strip() == "create"
    assert audit(repo.root, "--print-action", "--open-issues", "9 4").stdout.strip() == "update 4"


def test_ac2_print_title_is_the_run_date(repo):
    """REQ-011 AC2: rule 13."""
    assert audit(repo.root, "--print-title").stdout.strip() == f"agk drift audit {TODAY}"


def test_ac2_two_open_issues_alone_make_a_run_with_findings(repo):
    """REQ-011 AC2: rule 15. The duplicate finding is itself a finding, so the lowest is updated."""
    out = audit(repo.root, "--print-action", "--open-issues", "9 4").stdout.strip()
    assert out == "update 4"


def test_ac1_default_branch_comes_from_agk_toml(tmp_path):
    """REQ-011 AC1: rule 4. A repository whose default branch is not main."""
    repo = fx.Repo(tmp_path / "r")
    repo.git("symbolic-ref", "HEAD", "refs/heads/trunk")
    for rel, text in fx.BASE_FILES.items():
        repo.write(rel, text)
    repo.write("agk.toml", 'default_branch = "trunk"\ntest_dirs = ["tests"]\n')
    repo.commit(60, "base")
    fx.add_protected_change(repo, 3)
    assert "D1" in codes(repo.root)
