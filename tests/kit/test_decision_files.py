"""One file per decisions-log entry (brief #557 item 2, ADR-0277, amendment 118).

New decisions-log rows go to `docs/runs/decisions/<YYYY-MM-DD>-<id>.md`, one table row per file, so
two pull requests that each record a decision never touch the same lines. Every reader of the log
(`common.log_lines`, so `find_questions`, `check_specs.py` and `facts.py`) reads the old file and
then the folder in sorted order; the old file is never rewritten. `check_specs.py` fails a file of
the folder that is misnamed or does not hold exactly one row. No network.
"""

from __future__ import annotations

from pathlib import Path

LOG = "docs/runs/decisions-log.md"
HEAD = (
    "# Decisions log\n\n| Date | Decision | Reason | Recorded in | By |\n"
    "| --- | --- | --- | --- | --- |\n"
)
ROW_A = "| 2026-11-01 | Q-X1-1 ruled as read | a | this log | reviewer |\n"
ROW_B = "| 2026-11-05 | Q-X1-2 ruled as read | b | this log | reviewer |\n"
ROW_C = "| 2026-11-05 | Q-X1-3 ruled as read | c | this log | reviewer |\n"


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_log_lines_reads_the_old_file_then_the_folder_in_sorted_order(tmp_path):
    """REQ-018: SPEC-0009 rule 13 as amended (the old file plus the folder)."""
    from common import log_lines

    write(tmp_path, LOG, HEAD + ROW_A)
    write(tmp_path, "docs/runs/decisions/2026-11-05-q-x1-3.md", ROW_C)
    write(tmp_path, "docs/runs/decisions/2026-11-05-q-x1-2.md", ROW_B)
    lines = log_lines(tmp_path)
    assert lines is not None
    assert lines[-3:] == [ROW_A.strip(), ROW_B.strip(), ROW_C.strip()]


def test_the_folder_alone_is_a_log_and_neither_is_none(tmp_path):
    """REQ-018: SPEC-0009 rule 13 as amended (no log at all stays unknown)."""
    from common import log_lines

    assert log_lines(tmp_path) is None
    write(tmp_path, "docs/runs/decisions/2026-11-05-q-x1-2.md", ROW_B)
    assert log_lines(tmp_path) == [ROW_B.strip()]


def test_a_ruling_in_a_decision_file_rules_the_question(tmp_path):
    """REQ-018: find_questions reads the folder (so check_specs and facts do too)."""
    from common import find_questions

    write(tmp_path, LOG, HEAD + ROW_A)
    write(tmp_path, "docs/specs/0001-x.md", "Q-X1-1 and Q-X1-2 and Q-X1-9\n")
    write(tmp_path, "docs/runs/decisions/2026-11-05-q-x1-2.md", ROW_B)
    state = {q["id"]: q["ruled"] for q in find_questions(tmp_path) or []}
    assert state == {"Q-X1-1": True, "Q-X1-2": True, "Q-X1-9": False}


def test_each_decision_file_is_named_by_date_and_id_and_holds_one_row(tmp_path):
    """REQ-018: amendment 118 item 2 (one row per file, `<date>-<id>.md`)."""
    from common import decision_file_problems

    write(tmp_path, "docs/runs/decisions/2026-11-05-q-x1-2.md", ROW_B)
    assert decision_file_problems(tmp_path) == []
    write(tmp_path, "docs/runs/decisions/2026-11-05-two.md", ROW_B + ROW_C)
    write(tmp_path, "docs/runs/decisions/2026-11-05-none.md", "prose only\n")
    write(tmp_path, "docs/runs/decisions/notes.md", ROW_B)
    write(tmp_path, "docs/runs/decisions/2026-11-05-Upper.md", ROW_B)
    problems = decision_file_problems(tmp_path)
    assert len(problems) == 4
    assert all(p.startswith("docs/runs/decisions/") for p in problems)
    assert sum("one table row" in p for p in problems) == 2
    assert sum("<YYYY-MM-DD>-<id>.md" in p for p in problems) == 2


def test_check_specs_fails_a_decision_file_with_two_rows(repo):
    """REQ-018: check_specs.py runs the folder rule in governance."""
    repo.commit({LOG: HEAD + ROW_A}, "base")
    repo.branch()
    repo.commit({"docs/runs/decisions/2026-11-05-two.md": ROW_B + ROW_C})
    proc = repo.run("check_specs.py", "--base", "main")
    assert proc.returncode == 1
    assert "docs/runs/decisions/2026-11-05-two.md" in proc.stdout
    repo.commit({"docs/runs/decisions/2026-11-05-two.md": ROW_B})
    proc = repo.run("check_specs.py", "--base", "main")
    assert proc.returncode == 0, proc.stdout


def test_a_spec_only_body_may_carry_decision_files_beside():
    """REQ-018: check_pr_body's `Brief: none (spec)` shares the folder like the old log."""
    from check_pr_body import NONE_RULE, NONE_SHARED

    assert "docs/runs/decisions/" in NONE_SHARED
    assert "docs/runs/decisions/" in NONE_RULE
