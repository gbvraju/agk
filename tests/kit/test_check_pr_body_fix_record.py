"""Tests of the fix record lines of scripts/agk/check_pr_body.py (SPEC-0046 rule 7, build (c))."""

from __future__ import annotations

import pytest

BASE = (
    "Advances: REQ-053\n\nBuild-state row: 2026-11-06 | fix record | REQ-053\n"
    "Summary: A change that a person can read.\n"
)
RECORD = {
    "Symptom:": "the report step fails with a missing column on a clean checkout",
    "Cause:": "the reader assumed a header row that the example.com fixture does not have",
    "Reproduce:": "python3 -m pytest -q tests/test_report.py::test_columns",
    "Fixed-by:": "read the header only when the first row names one",
}
LABELS = tuple(RECORD)
CARD = "4111111111111111"  # the Visa test number the card networks publish (Luhn-valid)


def body(record: dict[str, list[str]] | None = None, fixes: tuple[str, ...] = ("#41",)) -> str:
    """BASE with the `Fixes-failure:` lines and each record line as given (a list per label)."""
    lines = [f"Fixes-failure: {f}" for f in fixes]
    rec = {k: [v] for k, v in RECORD.items()} if record is None else record
    for label, values in rec.items():
        lines += [f"{label} {v}".rstrip() for v in values]
    return BASE + "\n".join(lines) + "\n"


def with_line(label: str, values: list[str]) -> dict[str, list[str]]:
    rec = {k: [v] for k, v in RECORD.items()}
    if values:
        rec[label] = values
    else:
        del rec[label]
    return rec


def test_ac4_a_body_without_fixes_failure_is_checked_as_today(repo):
    """REQ-053 AC4: rule 7 (no `Fixes-failure:` line, record-like lines are not checked)."""
    assert repo.run("check_pr_body.py", "-", stdin=BASE).returncode == 0
    stray = BASE + "Cause: \nSymptom: " + "x" * 400 + "\n"
    assert repo.run("check_pr_body.py", "-", stdin=stray).returncode == 0


def test_ac4_a_full_fix_record_passes(repo):
    """REQ-053 AC4: rule 7 (one `Fixes-failure:` line and the four record lines)."""
    proc = repo.run("check_pr_body.py", "-", stdin=body())
    assert proc.returncode == 0, proc.stdout
    edge = with_line("Cause:", ["c" * 300])
    assert repo.run("check_pr_body.py", "-", stdin=body(edge)).returncode == 0


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize(
    "case, values, value",
    [
        ("missing", [], None),
        ("repeated", ["first plain text", "second plain text"], "second plain text"),
        ("empty", [""], None),
        ("too long", ["z" * 301], "z" * 301),
        ("finding", [f"seen with card {CARD} in the log"], CARD),
    ],
)
def test_ac4_each_bad_record_line_fails_naming_the_line_not_the_value(
    repo, label, case, values, value
):
    """REQ-053 AC4: rule 7 (missing, repeated, empty, over 300 characters, a guard finding)."""
    proc = repo.run("check_pr_body.py", "-", stdin=body(with_line(label, values)))
    assert proc.returncode == 1, proc.stdout
    fails = [x for x in proc.stdout.splitlines() if x.startswith("FAIL")]
    assert len(fails) == 1, proc.stdout
    assert "SPEC-0046 rule 7" in fails[0] and f"'{label}'" in fails[0]
    assert case in fails[0]
    if value is not None:
        assert value not in proc.stdout


@pytest.mark.parametrize("fixes", [("41",), ("#41", "#42"), ("",), ("#41 and more",)])
def test_ac4_the_fixes_failure_line_names_one_issue_number(repo, fixes):
    """REQ-053 AC4: rule 7 (`Fixes-failure: #<issue>`, once; the issue's kind is not checked)."""
    proc = repo.run("check_pr_body.py", "-", stdin=body(fixes=fixes))
    assert proc.returncode == 1, proc.stdout
    assert "SPEC-0046 rule 7" in proc.stdout and "'Fixes-failure:'" in proc.stdout
    assert "and more" not in proc.stdout


def test_ac4_a_finding_in_the_fixes_failure_body_is_not_echoed(repo):
    """REQ-053 AC4: rule 7 (a refusal names the line, never a word of the body)."""
    rec = with_line("Symptom:", [f"card {CARD}"])
    rec["Cause:"] = []
    proc = repo.run("check_pr_body.py", "-", stdin=body(rec))
    assert proc.returncode == 1
    assert CARD not in proc.stdout and "'Symptom:'" in proc.stdout and "'Cause:'" in proc.stdout
