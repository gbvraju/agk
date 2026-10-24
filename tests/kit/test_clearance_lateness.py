"""A covered fix list does not clear a head two or more commits late (SPEC-0030 rule 7).

`check_final_clearance.py` fails, naming the rule and never a value, when the latest verdict by a
listed author is a covered fix list and the head is two or more commits past its reviewed sha
(counted on the first-parent line, so a merge of the base branch is one commit). The head at the
reviewed sha, one commit after it, an uncovered fix list, a cleared verdict and no verdict are as
before. Git and a file only. No network. REQ-037 AC6.
"""

from __future__ import annotations

import json

import pytest
from test_final_clearance import ADR, check, comments_file, fix_list, scenario

FINAL = f"Final: {ADR} Proposed -> Accepted"


def accept(repo) -> None:
    repo.commit({ADR: "# ADR-0001: x\n\n- Status: Accepted\n- Date: 2026-10-22\n"}, "final")


def other(repo, name: str = "other.txt") -> None:
    repo.commit({name: "x\n"}, f"add {name}")


def outcome(repo, tmp_path, body: str, **kw):
    return check(repo, comments_file(tmp_path, body, **kw))


def test_ac6_a_head_at_the_reviewed_sha_passes(repo, tmp_path):
    """REQ-037 AC6"""
    reviewed = scenario(repo)
    proc = outcome(repo, tmp_path, fix_list(reviewed, FINAL))
    assert (proc.returncode, proc.stdout) == (0, "ok final-clearance\n")


def test_ac6_the_one_commit_after_is_checked_as_before(repo, tmp_path):
    """REQ-037 AC6"""
    reviewed = scenario(repo)
    accept(repo)
    assert outcome(repo, tmp_path, fix_list(reviewed, FINAL)).returncode == 0


def test_ac6_the_one_commit_after_that_is_not_the_named_lines_still_fails_rule_3(repo, tmp_path):
    """REQ-037 AC6"""
    reviewed = scenario(repo)
    other(repo)
    proc = outcome(repo, tmp_path, fix_list(reviewed, FINAL))
    assert proc.returncode == 1 and "rule 3" in proc.stdout


@pytest.mark.parametrize("extra", [1, 2])
def test_ac6_two_or_more_commits_after_fail_naming_rule_7_and_no_value(repo, tmp_path, extra):
    """REQ-037 AC6"""
    reviewed = scenario(repo)
    for i in range(extra):
        other(repo, f"late{i}.txt")
    accept(repo)
    proc = outcome(repo, tmp_path, fix_list(reviewed, FINAL))
    assert proc.returncode == 1 and proc.stdout.startswith("FAIL final-clearance: rule 7: ")
    assert reviewed[:7] not in proc.stdout and ADR not in proc.stdout


def test_ac6_a_merge_of_the_base_branch_is_one_commit_not_many(repo, tmp_path):
    """REQ-037 AC6: the first-parent line is counted."""
    reviewed = scenario(repo)
    repo.git("checkout", "-q", "-b", "side")
    other(repo, "s1.txt")
    other(repo, "s2.txt")
    repo.git("checkout", "-q", "main")
    repo.git("merge", "-q", "--no-ff", "-m", "merge side", "side")
    assert outcome(repo, tmp_path, fix_list(reviewed, FINAL)).returncode == 0
    other(repo, "after.txt")
    assert outcome(repo, tmp_path, fix_list(reviewed, FINAL)).returncode == 1


def test_ac6_an_uncovered_fix_list_a_cleared_verdict_and_no_verdict_are_unchanged(repo, tmp_path):
    """REQ-037 AC6"""
    reviewed = scenario(repo)
    other(repo, "a.txt")
    other(repo, "b.txt")
    numbered = fix_list(reviewed, FINAL, extra="1. an item")
    assert outcome(repo, tmp_path, numbered).returncode == 0
    assert outcome(repo, tmp_path, f"Verdict: cleared {reviewed[:7]}\n").returncode == 0
    assert outcome(repo, tmp_path, "just a comment\n").returncode == 0
    assert outcome(repo, tmp_path, fix_list(reviewed, FINAL), login="stranger").returncode == 0


def test_ac6_a_later_verdict_replaces_the_late_fix_list(repo, tmp_path):
    """REQ-037 AC6"""
    reviewed = scenario(repo)
    other(repo, "a.txt")
    other(repo, "b.txt")
    path = tmp_path / "comments.json"
    late = {"body": fix_list(reviewed, FINAL), "created_at": "2026-10-22T10:00:00Z"}
    clear = {"body": f"Verdict: cleared {reviewed[:7]}\n", "created_at": "2026-10-22T10:05:00Z"}
    path.write_text(
        json.dumps(
            [late | {"user": {"login": "reviewer"}}, clear | {"user": {"login": "reviewer"}}]
        )
    )
    assert check(repo, path).returncode == 0


def test_ac6_a_reviewed_sha_that_is_not_in_the_history_is_unchanged(repo, tmp_path):
    """REQ-037 AC6"""
    scenario(repo)
    other(repo, "a.txt")
    other(repo, "b.txt")
    assert outcome(repo, tmp_path, fix_list("0" * 40, FINAL)).returncode == 0
