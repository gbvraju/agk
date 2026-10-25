"""Approving a spec without typing a commit id (SPEC-0032 rule 5, build (g)).

`Approve: SPEC-<n>` by a listed approver approves the spec at the moment of the comment: it counts
while no commit pushed after that moment changes the spec apart from its status line. The moment
comes from the pull request's timeline (`check_specs.py --timeline FILE`, the order of the events,
never a commit date). An approving review counts at its own `commit_id`. The long line is
unchanged. Fixtures in `tmp_path` with git; no network, no model. REQ-039 AC4.
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


def short(who: str = "maintainer", n: str = "0001", cid: int = 7) -> dict:
    return {"id": cid, "user": {"login": who}, "body": f"Approve: SPEC-{n}\n\nreads well"}


def commit_event(sha: str, date: str = "2026-10-25T10:00:00Z") -> dict:
    return {"event": "committed", "sha": sha, "committer": {"date": date}}


def comment_event(cid: int = 7) -> dict:
    return {"event": "commented", "id": cid, "created_at": "2026-10-25T12:00:00Z"}


def review(state: str, sha: str, who: str = "maintainer", body: str = "") -> dict:
    return {"user": {"login": who}, "state": state, "commit_id": sha, "body": body}


def run(repo, comments, timeline=None, reviews=None):
    repo.write("comments.json", json.dumps(comments))
    args = ["--base", "main", "--comments", "comments.json"]
    if timeline is not None:
        repo.write("timeline.json", json.dumps(timeline))
        args += ["--timeline", "timeline.json"]
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
    """Rule 5 of SPEC-0032, build (g): only the status commit follows the comment."""
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    timeline = [commit_event(reviewed), comment_event(), commit_event(head(repo))]
    proc = run(repo, [short()], timeline)
    assert ok(proc), proc.stdout


def test_the_short_line_fails_when_a_later_commit_changes_the_spec(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Draft", "A changed rule.")}, "edit")
    edited = head(repo)
    repo.commit({SPEC: spec("0001", "Approved", "A changed rule.")}, "flip")
    timeline = [
        commit_event(reviewed),
        comment_event(),
        commit_event(edited),
        commit_event(head(repo)),
    ]
    proc = run(repo, [short()], timeline)
    assert proc.returncode == 1
    assert "SPEC-0001: rule 5: the spec changed after the approved sha" in proc.stdout


def test_a_later_change_to_another_file_does_not_matter(drafted):
    repo, reviewed = drafted
    repo.commit({"docs/other.md": "y\n"}, "elsewhere")
    elsewhere = head(repo)
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    timeline = [
        commit_event(reviewed),
        comment_event(),
        commit_event(elsewhere),
        commit_event(head(repo)),
    ]
    assert ok(run(repo, [short()], timeline))


def test_a_commit_before_the_comment_is_part_of_the_approved_text(drafted):
    """The approved text is the spec at the last commit before the comment, not at the first."""
    repo, first = drafted
    repo.commit({SPEC: spec("0001", "Draft", "A reworked rule.")}, "rework")
    reworked = head(repo)
    repo.commit({SPEC: spec("0001", "Approved", "A reworked rule.")}, "flip")
    timeline = [
        commit_event(first),
        commit_event(reworked),
        comment_event(),
        commit_event(head(repo)),
    ]
    assert ok(run(repo, [short()], timeline))


def test_commit_dates_are_not_trusted_only_the_order_of_the_timeline(drafted):
    """A commit pushed after the comment with an old committer date still counts as later."""
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Draft", "A changed rule.")}, "edit")
    edited = head(repo)
    repo.commit({SPEC: spec("0001", "Approved", "A changed rule.")}, "flip")
    timeline = [
        commit_event(reviewed, "2026-10-25T11:00:00Z"),
        comment_event(),
        commit_event(edited, "2000-01-01T00:00:00Z"),
        commit_event(head(repo), "2000-01-01T00:00:00Z"),
    ]
    assert run(repo, [short()], timeline).returncode == 1


@pytest.mark.parametrize(
    "case",
    ["no timeline file", "comment missing", "comment before every commit", "unreadable timeline"],
)
def test_a_short_line_that_cannot_be_pinned_counts_for_nothing(drafted, case):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    flip = head(repo)
    timeline = {
        "no timeline file": None,
        "comment missing": [commit_event(reviewed), commit_event(flip)],
        "comment before every commit": [comment_event(), commit_event(reviewed)],
        "unreadable timeline": "not a list",
    }[case]
    proc = run(repo, [short()], timeline)
    assert proc.returncode == 1
    assert "SPEC-0001: rule 5: no Approve line by an account in spec_approvers" in proc.stdout


def test_an_unlisted_account_or_another_spec_or_a_bad_form_counts_for_nothing(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    timeline = [commit_event(reviewed), comment_event(), commit_event(head(repo))]
    bad = [
        short(who="intruder"),
        short(n="0002"),
        {"id": 7, "user": {"login": "maintainer"}, "body": "Looks good\nApprove: SPEC-0001"},
        {"id": 7, "user": {"login": "maintainer"}, "body": "Approve: SPEC-1"},
        {"id": 7, "user": {"login": "maintainer"}, "body": "approve: SPEC-0001"},
    ]
    for comment in bad:
        assert run(repo, [comment], timeline).returncode == 1, comment


def test_the_long_line_works_as_before_with_a_timeline_present(drafted):
    repo, reviewed = drafted
    repo.commit({SPEC: spec("0001", "Approved")}, "flip")
    comment = {"id": 8, "user": {"login": "maintainer"}, "body": f"Approve: {reviewed} SPEC-0001"}
    timeline = [commit_event(reviewed), commit_event(head(repo))]
    assert ok(run(repo, [comment], timeline))
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


def test_governance_saves_the_timeline_beside_the_comments_and_passes_it():
    text = workflow()
    assert "issues/$PR_NUMBER/timeline" in text
    assert '"$RUNNER_TEMP/timeline.json"' in text
    assert '--timeline "$RUNNER_TEMP/timeline.json"' in text
    assert "gh api --paginate --method GET" in text.split("issues/$PR_NUMBER/timeline")[0][-80:]


def test_the_conductor_role_file_and_the_guide_show_the_short_line():
    role = (ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    guide = (ROOT / "docs" / "guides" / "getting-started.md").read_text(encoding="utf-8")
    line = 'waiting for a person: post "Approve: SPEC-<n>"'
    assert line in role
    assert "`Approve: SPEC-<n>`" in guide
