"""Tests of the guard ladder, `lessons.py ladder` (brief #645, ADR-0309; REQ-037).

Every lesson carries a guard level on one ladder (lesson, rule, test, check, workflow); the
promotion rules are decided from the catch logs alone, and the read-only pass names every row due
to climb. The logs are written in tmp_path with invented rows only: no pilot or customer data.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import lessons
import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "lessons.py"
TODAY = "2026-11-06"

HEADER = (
    "# Conductor catches 1 (invented rows)\n\n"
    "Kinds (fixed list): `watch`, `kit-gap`.\n\n"
    "## The catches\n\n"
    "| # | Date | Kind | What happened | Cost | Cause | Guard |\n"
    "| --- | --- | --- | --- | --- | --- | --- |\n"
)
ROLE = "# Role\n\n## Operating lessons\n\n- Start the watch again on every wake (row 1).\n"


def row(n, date, kind, cost, cause, guard, what="a wait ended early"):
    return f"| {n} | {date} | {kind} | {what} | {cost} | {cause} | {guard} |\n"


def project(tmp_path: Path, rows: list[str], role: str = ROLE, name="conductor-catches-1.md") -> Path:
    runs = tmp_path / "docs" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / name).write_text(HEADER + "".join(rows), encoding="utf-8")
    (tmp_path / "role.md").write_text(role, encoding="utf-8")
    (tmp_path / "check_x.py").write_text("# invented check\n", encoding="utf-8")
    return tmp_path


def ladder(root: Path, capsys, today=TODAY) -> tuple[int, str]:
    code = lessons.main(["ladder", "--root", str(root), "--today", today])
    return code, capsys.readouterr().out


RULE = "rule `role.md`"
CHECK = "check `check_x.py`"


def test_each_row_prints_its_strongest_level(tmp_path, capsys):
    """REQ-037: a row's guard is the strongest level it holds; `pending` is the lesson level."""
    root = project(
        tmp_path,
        [
            row(1, "2026-11-05", "watch", "(unknown)", "no wake while idle", f"{RULE}; {CHECK} (in force)"),
            row(2, "2026-11-05", "kit-gap", "(unknown)", "a line matched exactly", "pending #12"),
            row(3, "2026-11-05", "kit-gap", "(unknown)", "a sha read only", "pending (to be filed)"),
            row(4, "2026-11-05", "kit-gap", "(unknown)", "a map built early", "lesson"),
            row(5, "2026-11-05", "watch", "(unknown)", "a name match", "workflow `check_x.py`"),
            row(6, "2026-11-05", "watch", "(unknown)", "a stale body", "test `check_x.py`"),
        ],
    )
    code, out = ladder(root, capsys)
    assert code == 0, out
    lines = out.splitlines()
    assert "row conductor-catches-1#1 check" in lines
    assert "row conductor-catches-1#2 lesson" in lines
    assert "row conductor-catches-1#3 lesson" in lines
    assert "row conductor-catches-1#4 lesson" in lines
    assert "row conductor-catches-1#5 workflow" in lines
    assert "row conductor-catches-1#6 test" in lines
    assert lines[-1] == (
        "lessons ladder: 6 rows (lesson 3, rule 0, test 1, check 1, workflow 1); due 0; missing 0; malformed 0"
    )


def test_a_lesson_is_due_to_become_a_rule_when_a_second_row_has_the_same_kind_and_cause(tmp_path, capsys):
    """REQ-037: answer 2, the first lesson rule (a repeat of kind and cause)."""
    root = project(
        tmp_path,
        [
            row(1, "2026-11-01", "kit-gap", "(unknown)", "A line matched exactly.", "pending #12"),
            row(2, "2026-11-03", "kit-gap", "(unknown)", "a line  matched exactly", "lesson"),
            row(3, "2026-11-03", "watch", "(unknown)", "a line matched exactly", "lesson"),
        ],
    )
    code, out = ladder(root, capsys)
    assert code == 0
    due = [ln for ln in out.splitlines() if ln.startswith("due ")]
    assert due == [
        "due conductor-catches-1#1 lesson -> rule: row conductor-catches-1#2 has the same kind and cause",
        "due conductor-catches-1#2 lesson -> rule: row conductor-catches-1#1 has the same kind and cause",
    ]
    assert "due 2;" in out.splitlines()[-1]


@pytest.mark.parametrize(("cost", "due"), [("1 h", True), ("60 min", True), ("1.5 h", True), ("59 min", False),
                                           ("(unknown): overnight", False), ("2 merges", False)])
def test_a_lesson_is_due_to_become_a_rule_when_its_cost_is_one_hour_or_more(tmp_path, capsys, cost, due):
    """REQ-037: answer 2, the second lesson rule (a cost of one hour or more); an unknown cost is never one."""
    root = project(tmp_path, [row(1, "2026-11-05", "watch", cost, "no wake while idle", "lesson")])
    code, out = ladder(root, capsys)
    assert code == 0
    expected = "due conductor-catches-1#1 lesson -> rule: its cost is one hour or more"
    assert (expected in out.splitlines()) is due


def test_a_rule_is_due_to_climb_when_a_later_row_repeats_its_kind_and_cause(tmp_path, capsys):
    """REQ-037: answer 2, a row of the same kind and cause dated after the rule; a same-day row is not after."""
    role = ROLE + "- Read the whole result (row 2).\n- Read it again (row 3).\n"
    root = project(
        tmp_path,
        [
            row(1, "2026-11-01", "watch", "(unknown)", "no wake while idle", RULE),
            row(2, "2026-11-01", "watch", "(unknown)", "no wake while idle", RULE),
            row(3, "2026-11-04", "watch", "(unknown)", "No wake while idle", RULE),
        ],
        role=role,
    )
    code, out = ladder(root, capsys)
    assert code == 0, out
    due = [ln for ln in out.splitlines() if ln.startswith("due ")]
    assert due == [
        "due conductor-catches-1#1 rule -> test or check: row conductor-catches-1#3 repeats its kind and cause after the rule",
        "due conductor-catches-1#2 rule -> test or check: row conductor-catches-1#3 repeats its kind and cause after the rule",
    ]


@pytest.mark.parametrize(("today", "due"), [("2026-11-30", False), ("2026-12-01", True), ("2027-01-15", True)])
def test_a_rule_is_due_to_climb_when_it_has_stood_30_days(tmp_path, capsys, today, due):
    """REQ-037: answer 2, a rule that has stood 30 days from the date of its row."""
    root = project(tmp_path, [row(1, "2026-11-01 (unverified)", "watch", "(unknown)", "no wake while idle", RULE)])
    code, out = ladder(root, capsys, today=today)
    assert code == 0
    expected = "due conductor-catches-1#1 rule -> test or check: the rule has stood 30 days (since 2026-11-01)"
    assert (expected in out.splitlines()) is due


def test_a_test_or_a_check_is_never_due_and_a_check_climbs_only_with_the_owners_yes(tmp_path, capsys):
    """REQ-037: answer 2, a check becomes a workflow only with the owner's yes, so the pass never names it."""
    root = project(
        tmp_path,
        [
            row(1, "2026-01-01", "watch", "5 h", "no wake while idle", CHECK),
            row(2, "2026-01-02", "watch", "5 h", "no wake while idle", "test `check_x.py`"),
            row(3, "2026-01-03", "watch", "5 h", "no wake while idle", CHECK),
        ],
    )
    code, out = ladder(root, capsys)
    assert code == 0
    assert not [ln for ln in out.splitlines() if ln.startswith("due ")]


def test_a_row_without_a_date_is_not_decided_by_the_date_rules(tmp_path, capsys):
    """REQ-037: a rule that has no date is listed as undecided, never as due or as fine."""
    root = project(tmp_path, [row(1, "(unknown)", "watch", "(unknown)", "no wake while idle", RULE)])
    code, out = ladder(root, capsys)
    assert code == 0
    assert "undecided conductor-catches-1#1: the date is not YYYY-MM-DD" in out.splitlines()
    assert not [ln for ln in out.splitlines() if ln.startswith("due ")]


def test_a_rule_row_whose_cited_line_is_missing_fails(tmp_path, capsys):
    """REQ-037: answer 3, a `rule` guard needs a line of its file that cites the row."""
    root = project(
        tmp_path,
        [
            row(1, "2026-11-05", "watch", "(unknown)", "no wake while idle", RULE),
            row(2, "2026-11-05", "watch", "(unknown)", "a name match", f"{CHECK}; {RULE}"),
        ],
    )
    code, out = ladder(root, capsys)
    assert code == 1
    assert "missing conductor-catches-1#2: no line of role.md cites (row 2)" in out.splitlines()
    assert not any("#1:" in ln for ln in out.splitlines() if ln.startswith("missing "))
    assert out.splitlines()[-1].endswith("missing 1; malformed 0")


def test_a_guard_whose_file_is_missing_fails(tmp_path, capsys):
    root = project(tmp_path, [row(1, "2026-11-05", "watch", "(unknown)", "a name match", "check `gone.py`")])
    code, out = ladder(root, capsys)
    assert code == 1
    assert "missing conductor-catches-1#1: gone.py does not exist" in out.splitlines()


@pytest.mark.parametrize(
    "guard", ["pending 601", "pending (later)", "guess `x`", "rule role.md", "rule `../role.md`", "", "check `/etc/x`"]
)
def test_a_malformed_guard_fails_and_names_the_row_not_the_cell(tmp_path, capsys, guard):
    """REQ-037: answer 3, a malformed guard fails so that the record stays checkable."""
    root = project(tmp_path, [row(1, "2026-11-05", "watch", "(unknown)", "no wake while idle", guard)])
    code, out = ladder(root, capsys)
    assert code == 1
    assert "malformed conductor-catches-1#1: the guard is not one of the ladder's forms" in out.splitlines()
    assert out.splitlines()[-1].endswith("malformed 1")


def test_a_log_without_a_guard_column_is_named_and_not_on_the_ladder(tmp_path, capsys):
    root = project(tmp_path, [row(1, "2026-11-05", "watch", "(unknown)", "no wake while idle", CHECK)])
    other = "# Architect catches 1\n\n## The catches\n\n| # | Date | Kind | What |\n| --- | --- | --- | --- |\n| 1 | x | y | z |\n"
    (root / "docs" / "runs" / "architect-catches-1.md").write_text(other, encoding="utf-8")
    code, out = ladder(root, capsys)
    assert code == 0
    assert "not on the ladder: architect-catches-1 (no Guard column)" in out.splitlines()
    assert out.splitlines()[-1].startswith("lessons ladder: 1 rows")


def test_a_project_without_catch_logs_has_nothing_to_list(tmp_path, capsys):
    code, out = ladder(tmp_path, capsys)
    assert code == 0
    assert out.splitlines() == ["lessons ladder: no catch logs under docs/runs"]


def test_usage_errors_exit_2_and_name_the_option(tmp_path, capsys):
    assert lessons.main([]) == 2
    assert lessons.main(["climb"]) == 2
    assert lessons.main(["ladder", "--today", "06-11-2026"]) == 2
    out = capsys.readouterr().out
    assert "(option: --today)" in out
    assert "06-11-2026" not in out


def test_the_pass_is_read_only_and_opens_no_socket(tmp_path):
    """REQ-037: answer 3, GET-free and read-only: no file is written, no network module is imported."""
    root = project(tmp_path, [row(1, "2026-11-05", "watch", "2 h", "no wake while idle", "lesson")])
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPT), "ladder", "--root", str(root), "--today", TODAY],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "due conductor-catches-1#1 lesson -> rule: its cost is one hour or more" in proc.stdout
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    source = SCRIPT.read_text(encoding="utf-8")
    for module in ("socket", "urllib", "http", "subprocess", "requests"):
        assert f"import {module}" not in source


def test_this_repositorys_own_catch_logs_are_on_the_ladder_and_checkable():
    """REQ-037: answer 3, the record of this repository has no malformed guard and no missing rule line."""
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPT), "ladder", "--root", str(KIT_ROOT)],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stdout
    assert "malformed 0" in proc.stdout.splitlines()[-1]
    assert "missing 0" in proc.stdout.splitlines()[-1]
