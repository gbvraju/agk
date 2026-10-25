"""Checkpoints, draft pull requests and the progress line (SPEC-0033 rules 1 to 3; REQ-040).

A draft pull request is ignored by the pull-request body check and the final-clearance check
until it is marked ready for review; the workflow gives both the draft flag. The rules file
states the checkpoint rule and the progress line, and `session.progress_of` reads the one
progress comment of a pull request. Files and git only. No network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from test_clearance_lateness import FINAL, accept, other
from test_final_clearance import check, comments_file, fix_list, scenario

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))
BAD_BODY = "no fields here\n"
GOOD_BODY = "Advances: REQ-001\nBuild-state row: 2026-10-25 | x | REQ-001\n"
SKIPPED = "skipped (draft pull request)\n"


# --- drafts are ignored (rule 2; AC2) --------------------------------------------------------


def test_ac2_the_body_check_skips_a_draft_and_checks_every_other_pull_request(repo):
    """REQ-040 AC2"""
    draft = repo.run("check_pr_body.py", "--draft", "true", "-", stdin=BAD_BODY)
    assert (draft.returncode, draft.stdout) == (0, SKIPPED)
    for flag in ("false", "", "maybe", "TRUE"):
        proc = repo.run("check_pr_body.py", "--draft", flag, "-", stdin=BAD_BODY)
        assert proc.returncode == 1 and "Advances:" in proc.stdout, flag
    assert repo.run("check_pr_body.py", "-", stdin=BAD_BODY).returncode == 1
    assert repo.run("check_pr_body.py", "--draft", "false", "-", stdin=GOOD_BODY).returncode == 0


def test_ac2_the_body_check_reads_the_draft_flag_before_a_file_name(repo):
    """REQ-040 AC2"""
    repo.write("body.md", BAD_BODY)
    assert repo.run("check_pr_body.py", "--draft", "true", "body.md").stdout == SKIPPED
    assert repo.run("check_pr_body.py", "body.md", "--draft", "true").returncode == 1  # usage
    assert repo.run("check_pr_body.py", "--draft").returncode == 1  # usage


def test_ac2_the_clearance_check_skips_a_late_draft_and_checks_a_ready_pull_request(repo, tmp_path):
    """REQ-040 AC2"""
    reviewed = scenario(repo)
    other(repo, "a.txt")
    other(repo, "b.txt")
    accept(repo)
    comments = comments_file(tmp_path, fix_list(reviewed, FINAL))
    late = check(repo, comments)
    assert late.returncode == 1 and "rule 7" in late.stdout
    draft = check(repo, comments, "--draft", "true")
    assert (draft.returncode, draft.stdout) == (0, SKIPPED)
    for flag in ("false", "", "maybe"):
        assert check(repo, comments, "--draft", flag).returncode == 1, flag


def test_ac2_a_draft_is_skipped_even_without_a_comments_file(repo):
    """REQ-040 AC2"""
    proc = repo.run("check_final_clearance.py", "--draft", "true")
    assert (proc.returncode, proc.stdout) == (0, SKIPPED)


def test_ac2_the_workflow_runs_on_ready_for_review_and_passes_the_draft_flag():
    """REQ-040 AC2"""
    text = (ROOT / ".github" / "workflows" / "governance.yml").read_text(encoding="utf-8")
    assert "ready_for_review" in text.split("jobs:")[0]
    assert text.count("PR_DRAFT: ${{ github.event.pull_request.draft }}") == 2
    assert 'check_pr_body.py --draft "$PR_DRAFT" -' in text
    assert '--author "$PR_AUTHOR" --draft "$PR_DRAFT"' in text


# --- the rules file (rule 1 and rule 3; AC1 and AC3) -----------------------------------------


def rules() -> str:
    return (ROOT / "config" / "session-rules.md").read_text(encoding="utf-8")


def test_ac1_the_rules_file_states_the_checkpoint_rule():
    """REQ-040 AC1"""
    text = rules()
    for phrase in (
        "every step that leaves",
        "green or expected-red",
        "checkpoint:",
        "opens the pull request as a draft",
        "never carries a `Final:` status line",
        "ready for review only when",
        "gh api repos/{owner}/{repo}/pulls -f draft=true",
        "`gh pr ready <n>` where GraphQL is available",
        "otherwise with the route that the runtime documents",
        "which some runtimes refuse",
    ):
        assert phrase in text, phrase


def test_ac3_the_rules_file_states_the_progress_line():
    """REQ-040 AC3"""
    text = rules()
    for phrase in (
        "Progress: <head> done <n>/<m>; next: <step>",
        "edits it in place",
        "never repeats it",
    ):
        assert phrase in text, phrase


# --- the progress comment (rule 3; AC3) ------------------------------------------------------


def comment(body: str, login: str = "builder", cid: int = 1) -> dict:
    return {"id": cid, "body": body, "user": {"login": login}}


LINE = "Progress: abc1234 done 2/5; next: the report lines"


def test_ac3_one_well_formed_progress_comment_has_no_problem_and_is_returned():
    """REQ-040 AC3"""
    import session

    found, problems = session.progress_of([comment(LINE), comment("hello", cid=2)], "builder")
    assert problems == [] and found == {
        "head": "abc1234",
        "done": 2,
        "total": 5,
        "next": "the report lines",
    }


def test_ac3_no_progress_comment_is_not_a_problem_and_is_none():
    """REQ-040 AC3"""
    import session

    assert session.progress_of([], "builder") == (None, [])
    assert session.progress_of([comment(LINE, login="someone")], "builder") == (None, [])
    assert session.progress_of([comment("note\n" + LINE)], "builder") == (None, [])


def test_ac3_a_repeated_progress_comment_is_a_problem():
    """REQ-040 AC3"""
    import session

    found, problems = session.progress_of([comment(LINE), comment(LINE, cid=2)], "builder")
    assert found is None and len(problems) == 1 and problems[0].startswith("rule 3: ")
    assert "abc1234" not in problems[0]


@pytest.mark.parametrize(
    "line",
    [
        "Progress: abc1234 done 2/5",
        "Progress: abc12 done 2/5; next: x",
        "Progress: abc1234 done 6/5; next: x",
        "Progress: abc1234 done 2/0; next: x",
        "Progress: abc1234 done two/5; next: x",
        "Progress: abc1234 done 2/5; next:",
        "Progress: abc1234 done 2/5; next: x\nProgress: def5678 done 3/5; next: y",
    ],
)
def test_ac3_a_malformed_progress_comment_is_a_problem_naming_the_rule(line):
    """REQ-040 AC3"""
    import session

    found, problems = session.progress_of([comment(line)], "builder")
    if "\n" in line:  # a second Progress line inside one comment is not the first line: ignored
        assert found == {"head": "abc1234", "done": 2, "total": 5, "next": "x"}
    else:
        assert found is None and problems and problems[0].startswith("rule 3: ")
