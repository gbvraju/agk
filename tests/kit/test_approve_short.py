"""Approving a spec without typing a commit id (SPEC-0032 rule 5, build (g)).

`Approve: SPEC-<n>` by a listed approver approves the spec at the moment of the comment: it counts
while no commit pushed after that moment changes the spec apart from its status line. The moment
comes from the server-side `created_at` of the `pull_request` workflow runs of the pull request
(`check_specs.py --runs FILE`: the approved text is the spec at the `head_sha` of the latest run
created before the comment; never a commit date). An approving review counts at its own
`commit_id`. The long line is unchanged. Fixtures in `tmp_path` with git; no network, no model.
REQ-039 AC4.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = "docs/specs/0001-thing.md"
SPEC2 = "docs/specs/0002-other.md"
CONFIG = "version: 1\nverdict_authors: [reviewer]\nspec_approvers: [maintainer]\n"


def spec(number: str, status: str, rule: str = "A rule.") -> str:
    return (
        f"# SPEC-{number}: Thing\n\n- Status: {status}\n- Owner: reviewers\n\n"
        f"## Rules\n\n1. {rule}\n"
    )


COMMENTED_AT = "2026-10-25T12:00:00Z"
BEFORE = "2026-10-25T10:00:00Z"
AFTER = "2026-10-25T12:30:00Z"


def short(who: str = "maintainer", n: str = "0001", cid: int = 7, at: str | None = COMMENTED_AT):
    comment = {"id": cid, "user": {"login": who}, "body": f"Approve: SPEC-{n}\n\nreads well"}
    if at is not None:
        comment["created_at"] = at
    return comment


def run_of(sha: str, at: str, event: str = "pull_request", dated: str = "2000-01-01T00:00:00Z"):
    """One workflow run as the API lists it; the commit's own date is set by its author."""
    return {
        "event": event,
        "head_sha": sha,
        "created_at": at,
        "head_commit": {"timestamp": dated},
    }


def review(state: str, sha: str, who: str = "maintainer", body: str = "") -> dict:
    return {"user": {"login": who}, "state": state, "commit_id": sha, "body": body}


def run(repo, comments, runs=None, reviews=None):
    repo.write("comments.json", json.dumps(comments))
    args = ["--base", "main", "--comments", "comments.json"]
    if runs is not None:
        page = {"total_count": len(runs), "workflow_runs": runs} if isinstance(runs, list) else runs
        repo.write("runs.json", json.dumps(page))
        args += ["--runs", "runs.json"]
    if reviews is not None:
        repo.write("reviews.json", json.dumps(reviews))
        args += ["--reviews", "reviews.json"]
    return repo.run("check_specs.py", *args)


def head(repo, rev: str = "HEAD") -> str:
    return repo.git("rev-parse", rev).strip()


@pytest.fixture
def drafted(repo):
    """main with a Draft spec; the branch has one reviewed commit (the text the person reads)."""
    repo.commit({"config/reviewers.yaml": CONFIG, SPEC: spec("0001", "Draft")}, "base")
    repo.branch()
    repo.commit({"docs/notes.md": "x\n"}, "reviewed")
    return repo, head(repo)


def ok(proc) -> bool:
    return proc.returncode == 0 and proc.stdout.splitlines()[-1] == "ok specs"


def test_the_short_line_with_no_later_change_to_the_spec_passes(drafted):
    """Rule 5 of SPEC-0032, build (g): only the status commit is pushed after the comment."""
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    runs = [run_of(reviewed, BEFORE), run_of(head(repo), AFTER)]
    proc = run(repo, [short()], runs)
    assert ok(proc), proc.stdout


def test_the_short_line_fails_when_a_later_push_changes_the_spec(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Draft", "A changed rule.")}, "edit")
    edited = head(repo)
    repo.commit({SPEC: spec("0001", "Approved", "A changed rule.")}, "flip")
    runs = [run_of(reviewed, BEFORE), run_of(edited, AFTER), run_of(head(repo), AFTER)]
    proc = run(repo, [short()], runs)
    assert proc.returncode == 1
    assert "SPEC-0001: rule 5: the spec changed after the approved sha" in proc.stdout


def test_a_back_dated_commit_pushed_after_the_comment_does_not_count(drafted):
    """Verdict on 077895f: the commit's own date is the author's; the run's created_at is GitHub's.

    The edit is dated before the comment (in the run's head commit) but pushed after it."""
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Draft", "Back-dated rule.")}, "edit")
    edited = head(repo)
    repo.commit({SPEC: spec("0001", "Approved", "Back-dated rule.")}, "flip")
    old = "2000-01-01T00:00:00Z"
    runs = [
        run_of(reviewed, BEFORE, dated=BEFORE),
        run_of(edited, AFTER, dated=old),
        run_of(head(repo), AFTER, dated=old),
    ]
    assert run(repo, [short()], runs).returncode == 1


def test_a_later_change_to_another_file_does_not_matter(drafted):
    repo, reviewed = drafted
    repo.commit({"docs/other.md": "y\n"}, "elsewhere")
    elsewhere = head(repo)
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    runs = [run_of(reviewed, BEFORE), run_of(elsewhere, AFTER), run_of(head(repo), AFTER)]
    assert ok(run(repo, [short()], runs))


def test_the_approved_text_is_the_head_of_the_latest_run_before_the_comment(drafted):
    repo, first = drafted
    repo.commit({SPEC: spec("0001", "Draft", "A reworked rule.")}, "rework")
    reworked = head(repo)
    repo.commit({SPEC: spec("0001", "Approved", "A reworked rule.")}, "flip")
    runs = [
        run_of(first, "2026-10-25T09:00:00Z"),
        run_of(reworked, BEFORE),
        run_of(head(repo), AFTER),
    ]
    assert ok(run(repo, [short()], runs))


def test_several_runs_of_one_head_and_runs_in_any_order_give_the_same_pin(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    runs = [
        run_of(head(repo), AFTER),
        run_of(reviewed, "2026-10-25T10:05:00Z"),
        run_of(reviewed, "2026-10-25T09:00:00Z"),
        run_of(reviewed, "2026-10-25T11:59:59Z"),
    ]
    assert ok(run(repo, [short()], runs))


def test_the_pages_of_gh_api_paginate_are_read_one_after_the_other(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    first = {"workflow_runs": [run_of(reviewed, BEFORE)]}
    second = {"workflow_runs": [run_of(head(repo), AFTER)]}
    repo.write("runs.json", json.dumps(first) + json.dumps(second))
    args = ["--base", "main", "--comments", "comments.json", "--runs", "runs.json"]
    repo.write("comments.json", json.dumps([short()]))
    assert ok(repo.run("check_specs.py", *args))


def test_a_run_of_another_event_or_a_run_created_after_the_comment_pins_nothing(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    runs = [run_of(reviewed, BEFORE, event="push"), run_of(head(repo), AFTER)]
    assert run(repo, [short()], runs).returncode == 1


@pytest.mark.parametrize(
    "case",
    [
        "no runs file",
        "no run before the comment",
        "comment without a time",
        "unreadable runs",
        "a sha that is not in this history",
    ],
)
def test_a_short_line_that_cannot_be_pinned_counts_for_nothing(drafted, case):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    flip = head(repo)
    comment = short(at=None) if case == "comment without a time" else short()
    runs = {
        "no runs file": None,
        "no run before the comment": [run_of(reviewed, AFTER), run_of(flip, AFTER)],
        "comment without a time": [run_of(reviewed, BEFORE), run_of(flip, AFTER)],
        "unreadable runs": "not a list",
        "a sha that is not in this history": [run_of("0" * 40, BEFORE), run_of(flip, AFTER)],
    }[case]
    proc = run(repo, [comment], runs)
    assert proc.returncode == 1
    assert "SPEC-0001: rule 5: no Approve line by an account in spec_approvers" in proc.stdout


def test_a_run_of_a_commit_outside_this_history_pins_nothing_even_if_the_text_is_equal(drafted):
    """A run of another pull request of the same branch name must not approve this one."""
    repo, reviewed = drafted
    repo.git("checkout", "-q", "-b", "elsewhere", "main")
    repo.commit({SPEC: spec("0001", "Draft"), "docs/other.md": "z\n"}, "same spec, other history")
    stranger = head(repo)
    repo.git("checkout", "-q", "feature")
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    runs = [run_of(stranger, BEFORE), run_of(head(repo), AFTER)]
    assert run(repo, [short()], runs).returncode == 1


def test_an_unlisted_account_or_another_spec_or_a_bad_form_counts_for_nothing(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    runs = [run_of(reviewed, BEFORE), run_of(head(repo), AFTER)]
    login = {"login": "maintainer"}
    bad = [
        short(who="intruder"),
        short(n="0002"),
        {"id": 7, "user": login, "created_at": COMMENTED_AT, "body": "Looks\nApprove: SPEC-0001"},
        {"id": 7, "user": login, "created_at": COMMENTED_AT, "body": "Approve: SPEC-1"},
        {"id": 7, "user": login, "created_at": COMMENTED_AT, "body": "approve: SPEC-0001"},
    ]
    for comment in bad:
        assert run(repo, [comment], runs).returncode == 1, comment


def test_the_long_line_works_as_before_with_runs_present(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    comment = {"id": 8, "user": {"login": "maintainer"}, "body": f"Approve: {reviewed} SPEC-0001"}
    runs = [run_of(reviewed, BEFORE), run_of(head(repo), AFTER)]
    assert ok(run(repo, [comment], runs))
    assert ok(run(repo, [comment]))


def test_an_approving_review_on_the_one_spec_counts_at_its_own_commit(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    assert ok(run(repo, [], reviews=[review("APPROVED", reviewed)]))


def test_an_approving_review_fails_when_the_spec_changed_after_its_commit(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Draft", "A changed rule.")}, "edit")
    repo.commit({SPEC: spec("0001", "Approved", "A changed rule.")}, "flip")
    proc = run(repo, [], reviews=[review("APPROVED", reviewed)])
    assert proc.returncode == 1
    assert "SPEC-0001: rule 5: the spec changed after the approved sha" in proc.stdout


@pytest.mark.parametrize("state", ["COMMENTED", "CHANGES_REQUESTED", "DISMISSED", "PENDING"])
def test_a_review_that_is_not_an_approval_counts_for_nothing(drafted, state):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    assert run(repo, [], reviews=[review(state, reviewed)]).returncode == 1


def test_an_approving_review_by_an_unlisted_account_counts_for_nothing(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    assert run(repo, [], reviews=[review("APPROVED", reviewed, who="intruder")]).returncode == 1


def test_an_approving_review_with_two_specs_and_no_line_fails(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC2: spec("0002", "Draft")}, "second draft")
    repo.commit({SPEC: spec("0001", "Approved"), SPEC2: spec("0002", "Approved")}, "flip both")
    proc = run(repo, [], reviews=[review("APPROVED", head(repo, "HEAD~1"))])
    assert proc.returncode == 1
    assert "SPEC-0001: rule 5: no Approve line by an account in spec_approvers" in proc.stdout
    assert "SPEC-0002: rule 5: no Approve line by an account in spec_approvers" in proc.stdout


def test_an_approving_review_with_two_specs_approves_the_one_its_body_names(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC2: spec("0002", "Draft")}, "second draft")
    repo.commit({SPEC: spec("0001", "Approved"), SPEC2: spec("0002", "Approved")}, "flip both")
    body = "Approve: SPEC-0001\n\nreads well"
    proc = run(repo, [], reviews=[review("APPROVED", head(repo, "HEAD~1"), body=body)])
    assert proc.returncode == 1
    assert "SPEC-0001: rule 5" not in proc.stdout
    assert "SPEC-0002: rule 5: no Approve line by an account in spec_approvers" in proc.stdout


def test_person_approvals_count_a_short_line_and_an_approving_review():
    """The clearance check and the router ask only whether a person approved a spec."""
    from reviewers import person_approvals

    approvers = ["maintainer"]
    assert person_approvals([short()], [], approvers) == {"SPEC-0001"}
    assert person_approvals([short(who="intruder")], [], approvers) == set()
    assert person_approvals([], [review("APPROVED", "a" * 40)], approvers) == set()
    named = review("APPROVED", "a" * 40, body="Approve: SPEC-0003")
    assert person_approvals([], [named], approvers) == {"SPEC-0003"}
    assert person_approvals([], [review("COMMENTED", "a" * 40, body="x")], approvers) == set()


def test_the_router_reads_the_approval_line_with_and_without_the_pasted_line():
    from route import asked_for

    old = "Approval: SPEC-0007 docs/specs/0007-x.md Draft -> Approved, waiting for a person"
    new = old + ': post "Approve: SPEC-0007"'
    assert asked_for(old) == {"SPEC-0007"}
    assert asked_for(new) == {"SPEC-0007"}
    assert asked_for(old + ': post "Approve: SPEC-0008"') == set()


def workflow() -> str:
    return (ROOT / ".github" / "workflows" / "governance.yml").read_text(encoding="utf-8")


def test_governance_saves_the_runs_of_the_pull_request_and_passes_them():
    """Verdict on 077895f: the pin is the server-side time of a pushed head, not the timeline."""
    text = workflow()
    assert "timeline" not in text
    assert "actions/runs?event=pull_request&branch=" in text
    assert "head.ref" in text
    assert '"$RUNNER_TEMP/approval-runs.json"' in text
    assert '--runs "$RUNNER_TEMP/approval-runs.json"' in text
    assert (
        "gh api --paginate --method GET" in text.split("actions/runs?event=pull_request")[0][-80:]
    )


def test_the_conductor_role_file_and_the_guide_show_the_short_line():
    role = (ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    line = 'waiting for a person: post "Approve: SPEC-<n>"'
    assert line in role
    assert "`Approve: SPEC-<n>`" in guide
