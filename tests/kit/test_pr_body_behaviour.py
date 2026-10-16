"""The optional `Behaviour: unchanged` line of a pull request body (SPEC-0010 rule 18)."""

from __future__ import annotations

from pathlib import Path

GOOD = "Advances: REQ-001\n\nBuild-state row: 2026-10-14 | skeleton | REQ-001\n"
ROOT = Path(__file__).resolve().parents[2]


def check(repo, body: str):
    return repo.run("check_pr_body.py", "-", stdin=body)


def test_ac1_the_exact_line_is_accepted_and_a_body_without_it_passes(repo):
    """REQ-016 AC1: rule 18 (optional)."""
    assert check(repo, GOOD).returncode == 0
    assert check(repo, GOOD + "\nBehaviour: unchanged\n").returncode == 0


def test_ac1_any_other_value_fails_with_a_message_that_names_the_label_only(repo):
    """REQ-016 AC1: rule 18 (a typo is not a silent escape)."""
    for value in ("unchaged", "changed", "", "Unchanged", "unchanged (optional; delete the line)"):
        proc = check(repo, GOOD + f"\nBehaviour: {value}\n")
        assert proc.returncode == 1, value
        assert proc.stdout.splitlines() == ["FAIL pr-body: 'Behaviour:' must be 'unchanged'"]


def test_ac1_a_behaviour_line_inside_a_code_fence_or_indented_is_not_checked(repo):
    """REQ-016 AC1: rule 18 (the same reading as the facts and the proof check)."""
    assert check(repo, GOOD + "\n```\nBehaviour: whatever\n```\n").returncode == 0
    assert check(repo, GOOD + "\n  Behaviour: whatever\n").returncode == 0


def test_ac1_the_template_carries_the_optional_line_after_the_issue_line():
    """REQ-016 AC1: rule 18."""
    text = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    line = "Behaviour: unchanged (optional; delete the line for a change in behaviour)"
    assert line in text and text.index("Issue:") < text.index(line) < text.index("Build-state row:")
    # an unedited template line is not the declaration: it fails the check, so it must be deleted
    # or edited by the author
    assert "Behaviour: unchanged" != line
