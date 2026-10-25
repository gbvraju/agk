"""A person approves every spec (SPEC-0032 rules 2, 5 and 6; REQ-039 AC4 and AC1).

`spec_approvers` of config/reviewers.yaml, the clearance check reading `Approve: <sha> SPEC-<n>`
from comments and from reviews, the router setting `agk:approve` on the conductor's `Approval:`
line, and the conductor role file. Fixtures in `tmp_path` with git. No network, no model.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import reviewers
import route
from test_final_clearance import ADR, accept_adr, adr, check, fix_list
from test_route import HEAD, facts, ok, said

ROOT = Path(__file__).resolve().parents[2]
SPEC = "docs/specs/0001-x.md"
CONFIG = "version: 1\nverdict_authors: [reviewer]\nspec_approvers: [maintainer]\n"


def spec(status: str) -> str:
    return f"# SPEC-0001: x\n\n- Status: {status}\n- Owner: reviewers\n"


# --- spec_approvers (rule 5) ---------------------------------------------------------------------


def test_ac4_spec_approvers_are_the_listed_user_handles_without_the_placeholder():
    """REQ-039 AC4: rule 5 (lower case, no @; the installed placeholder is never listed)."""
    data = reviewers.parse("version: 1\nspec_approvers: [@Alice, bob, '@REPLACE-ME']\n")
    assert reviewers.approvers_of(data) == ["alice", "bob"]


@pytest.mark.parametrize(
    "text",
    [
        "version: 1\n",
        "version: 1\nspec_approvers: []\n",
        "version: 1\nspec_approvers: ['@org/team']\n",
        "version: 1\nspec_approvers: [a/b]\n",
    ],
)
def test_ac4_an_absent_empty_or_team_list_approves_nobody(text):
    """REQ-039 AC4: rule 5 (a team handle is not a person; nothing listed means nobody)."""
    assert reviewers.approvers_of(reviewers.parse(text)) == []


def test_ac4_spec_approvers_of_a_repository_is_read_from_its_config(repo):
    """REQ-039 AC4: rule 5 (unreadable means nobody)."""
    assert reviewers.spec_approvers(repo.root) == []
    repo.write("config/reviewers.yaml", CONFIG)
    assert reviewers.spec_approvers(repo.root) == ["maintainer"]


def test_ac4_reviewers_check_rejects_a_bad_list_naming_the_setting_and_accepts_none(repo):
    """REQ-039 AC4: rule 5 (the message names the setting, never a handle)."""
    base = (ROOT / "config" / "reviewers.yaml").read_text(encoding="utf-8")
    protected = (ROOT / "config" / "protected-paths.txt").read_text(encoding="utf-8")
    repo.write("config/protected-paths.txt", protected)
    repo.write("config/reviewers.yaml", base + "verdict_authors: [boss]\n")
    assert repo.run("reviewers.py", "--check").returncode == 0
    repo.write("config/reviewers.yaml", base + "verdict_authors: [boss]\nspec_approvers: [a b]\n")
    proc = repo.run("reviewers.py", "--check")
    assert proc.returncode == 1 and "spec_approvers" in proc.stdout and "a b" not in proc.stdout
    repo.write("config/reviewers.yaml", base + "verdict_authors: [boss]\nspec_approvers: [boss]\n")
    assert repo.run("reviewers.py", "--check").returncode == 0


def test_ac4_this_repository_lists_its_approvers():
    """REQ-039 AC4: rule 5 (a list of people, in the file of this repository)."""
    assert reviewers.spec_approvers(ROOT)


def test_ac4_an_approve_line_counts_from_a_listed_person_in_a_comment_or_a_review():
    """REQ-039 AC4: rule 5 (`Approve: <sha> SPEC-<n>` on the first line, comment or review)."""
    comment = said(1, "maintainer", "Approve: 80e4898 SPEC-0032")
    review = {"user": {"login": "Maintainer"}, "body": "Approve: 1234567 SPEC-0007\n\nreads well"}
    found = reviewers.person_approvals([comment], [review], ["maintainer"])
    assert found == {"SPEC-0032", "SPEC-0007"}


def test_ac4_an_approve_line_does_not_count_from_anyone_else_or_in_another_shape():
    """REQ-039 AC4: rule 5 (an unlisted account, a later line, a short sha, a wrong form)."""
    people = ["maintainer"]
    other = said(1, "stranger", "Approve: 80e4898 SPEC-0032")
    later = said(2, "maintainer", "I think so.\nApprove: 80e4898 SPEC-0032")
    short = said(3, "maintainer", "Approve: 80e SPEC-0032")
    form = said(4, "maintainer", "Approved: 80e4898 SPEC-0032")
    assert reviewers.person_approvals([other, later, short, form], [], people) == set()
    assert reviewers.person_approvals([other], [], []) == set()


# --- the clearance check (rule 5; AC4) -----------------------------------------------------------


def scenario(repo) -> str:
    repo.commit({"config/reviewers.yaml": CONFIG, ADR: adr("Proposed"), SPEC: spec("Draft")}, "r")
    return repo.git("rev-parse", "HEAD").strip()


def approve_spec(repo) -> None:
    repo.commit({SPEC: spec("Approved")}, "final")


def files(tmp_path: Path, comments: list[dict], reviews: list[dict] | None = None):
    c, r = tmp_path / "comments.json", tmp_path / "reviews.json"
    c.write_text(json.dumps(comments), encoding="utf-8")
    r.write_text(json.dumps(reviews or []), encoding="utf-8")
    return c, r


def verdict(reviewed: str, *finals: str) -> dict:
    return {
        "body": fix_list(reviewed, *finals),
        "created_at": "2026-10-25T10:00:00Z",
        "user": {"login": "reviewer"},
    }


def person(login: str = "maintainer", body: str = "Approve: 1234567 SPEC-0001") -> dict:
    return {"body": body, "created_at": "2026-10-25T10:05:00Z", "user": {"login": login}}


def run_check(repo, comments: Path, reviews: Path | None = None):
    extra = ("--reviews", str(reviews)) if reviews else ()
    return repo.run("check_final_clearance.py", "--comments", str(comments), *extra)


FINAL = f"Final: {SPEC} Draft -> Approved"


def test_ac4_a_spec_set_approved_with_no_approve_line_fails_naming_the_setting(repo, tmp_path):
    """REQ-039 AC4: rule 5 (a Final line of a conductor never approves a spec by itself)."""
    reviewed = scenario(repo)
    approve_spec(repo)
    comments, reviews = files(tmp_path, [verdict(reviewed, FINAL)])
    proc = run_check(repo, comments, reviews)
    assert proc.returncode == 1, proc.stdout
    assert proc.stdout.startswith("FAIL final-clearance: rule 5")
    assert "spec_approvers" in proc.stdout and "SPEC-0001" not in proc.stdout


def test_ac4_an_approve_comment_by_a_listed_person_lets_the_spec_pass(repo, tmp_path):
    """REQ-039 AC4: rule 5 (the person's line stands for the Final line of the spec)."""
    reviewed = scenario(repo)
    approve_spec(repo)
    comments, reviews = files(tmp_path, [verdict(reviewed, FINAL), person()])
    proc = run_check(repo, comments, reviews)
    assert (proc.returncode, proc.stdout) == (0, "ok final-clearance\n"), proc.stdout


def test_ac4_an_approve_review_by_a_listed_person_counts_the_same_way(repo, tmp_path):
    """REQ-039 AC4: rule 5 (a person often approves in a review, not in an issue comment)."""
    reviewed = scenario(repo)
    approve_spec(repo)
    review = {"body": "Approve: 1234567 SPEC-0001", "user": {"login": "maintainer"}}
    comments, reviews = files(tmp_path, [verdict(reviewed, FINAL)], [review])
    proc = run_check(repo, comments, reviews)
    assert (proc.returncode, proc.stdout) == (0, "ok final-clearance\n"), proc.stdout


@pytest.mark.parametrize(
    "line",
    [
        person("stranger"),
        person(body="Approve: 1234567 SPEC-0002"),
        person(body="Approve: SPEC-0001"),
    ],
)
def test_ac4_an_approve_line_by_an_unlisted_account_or_for_another_spec_does_not_count(
    repo, tmp_path, line
):
    """REQ-039 AC4: rule 5 (only a listed person, only for the spec named)."""
    reviewed = scenario(repo)
    approve_spec(repo)
    comments, reviews = files(tmp_path, [verdict(reviewed, FINAL), line])
    assert run_check(repo, comments, reviews).returncode == 1


def test_ac4_an_adr_final_line_needs_no_person(repo, tmp_path):
    """REQ-039 AC4: rule 5 (the conductor's Final lines for the ADRs stay as they are)."""
    reviewed = scenario(repo)
    accept_adr(repo)
    final = f"Final: {ADR} Proposed -> Accepted"
    comments, reviews = files(tmp_path, [verdict(reviewed, final)])
    assert run_check(repo, comments, reviews).returncode == 0
    assert check(repo, comments).returncode == 0


def test_ac4_the_reviews_file_is_optional_and_a_bad_one_is_an_error(repo, tmp_path):
    """REQ-039 AC4: rule 5 (without --reviews only the comments are read)."""
    reviewed = scenario(repo)
    approve_spec(repo)
    comments, reviews = files(tmp_path, [verdict(reviewed, FINAL), person()])
    assert check(repo, comments).returncode == 0
    reviews.write_text("not json", encoding="utf-8")
    assert run_check(repo, comments, reviews).returncode == 1


# --- the router and the Approval: line (rule 2; AC1) ---------------------------------------------

APPROVAL = "Approval: SPEC-0032 docs/specs/0032-x.md Draft -> Approved, waiting for a person"


def conductor(body: str, cid: int = 1, login: str = "boss") -> dict:
    return said(cid, login, body)


def test_ac1_an_approval_line_of_a_verdict_naming_the_head_sets_approve_even_for_a_fix_list():
    """REQ-039 AC1: rule 2 (it set agk:fix on #196: the person is waited for first)."""
    fix = conductor(f"Verdict: fix list {HEAD[:7]}\n\nPush the ADR.\n\n{APPROVAL}\n")
    assert route.decide(facts(comments=[fix])) == "agk:approve"
    cleared = conductor(f"Verdict: cleared {HEAD[:7]}\n\n{APPROVAL}\n")
    assert route.decide(facts(comments=[cleared])) == "agk:approve"


def test_ac1_the_approve_of_a_listed_person_ends_the_wait_and_the_verdict_decides_again():
    """REQ-039 AC1: rule 2 (comment or review; the label follows the verdict afterwards)."""
    fix = conductor(f"Verdict: fix list {HEAD[:7]}\n\n1. x\n\n{APPROVAL}\n")
    by = said(2, "maintainer", "Approve: 80e4898 SPEC-0032")
    assert route.decide(facts(comments=[fix, by])) == "agk:fix"
    review = {"user": {"login": "maintainer"}, "body": "Approve: 80e4898 SPEC-0032"}
    assert route.decide(facts(comments=[fix], reviews=[review])) == "agk:fix"
    cleared = conductor(f"Verdict: cleared {HEAD[:7]}\n\n{APPROVAL}\n")
    assert route.decide(facts(comments=[cleared, by])) == "agk:ready"


def test_ac1_an_approval_line_of_an_unlisted_author_or_for_another_head_is_ignored():
    """REQ-039 AC1: rule 2 (only a verdict by a listed author that names the head)."""
    other = conductor(f"Verdict: fix list {HEAD[:7]}\n\n1. x\n\n{APPROVAL}\n", login="stranger")
    assert route.decide(facts(comments=[other])) == "agk:review"
    old = conductor(f"Verdict: fix list 0123456\n\n1. x\n\n{APPROVAL}\n")
    assert route.decide(facts(comments=[old])) == "agk:review"


def test_ac1_a_red_check_or_a_conflict_comes_before_the_wait_for_a_person():
    """REQ-039 AC1: rule 2 (the order: conflict, ci-running, ci-red, approve, fix, ...)."""
    fix = conductor(f"Verdict: fix list {HEAD[:7]}\n\n1. x\n\n{APPROVAL}\n")
    bad = {"name": "proof", "status": "completed", "conclusion": "failure"}
    assert route.decide(facts(comments=[fix], checks=[ok("a"), bad])) == "agk:ci-red"
    assert route.decide(facts(comments=[fix], mergeable_state="dirty")) == "agk:conflict"


def test_ac1_the_approver_list_is_the_one_of_the_reviewers_module():
    """REQ-039 AC1: rule 2 (one reader of spec_approvers, not two)."""
    assert route.spec_approvers is reviewers.spec_approvers
    assert route.approved_by_a_person is reviewers.person_approvals


# --- the conductor role file (rule 5 and 6; AC4) -------------------------------------------------

CONDUCTOR = ROOT / ".claude" / "agents" / "conductor.md"


def test_ac4_the_conductor_ends_an_intake_verdict_with_an_approval_line_and_never_writes_approve():
    """REQ-039 AC4: rules 5 and 6 (the role file; the check cannot tell accounts apart yet)."""
    text = " ".join(CONDUCTOR.read_text(encoding="utf-8").split())
    assert "Approval: SPEC-<n> <path> Draft -> Approved, waiting for a person" in text
    assert "never write `Approve:`" in text
    assert "no `Final:` line for a spec" in text
    assert "`spec_approvers`" in text
