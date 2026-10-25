"""Every flip of a spec to Approved needs a person, for one text (SPEC-0032 rule 5, build (f)).

`check_specs.py --comments FILE [--reviews FILE]` fails a pull request whose diff sets a spec
`Status: Approved`, whether through a `Final:` line or an ordinary commit, unless a comment or a
review by an account in `spec_approvers` has the first line `Approve: <sha> SPEC-<n>`, and the spec
file at the head is the one at `<sha>` apart from its status line. Fixtures in `tmp_path` with git;
no network, no model. REQ-039 AC4.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

SPEC = "docs/specs/0001-thing.md"
CONFIG = "version: 1\nverdict_authors: [reviewer]\nspec_approvers: [maintainer]\n"
WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "governance.yml"


def spec(status: str, rule: str = "A rule.") -> str:
    return (
        f"# SPEC-0001: Thing\n\n- Status: {status}\n- Owner: reviewers\n\n## Rules\n\n1. {rule}\n"
    )


def line(sha: str, who: str = "maintainer", n: str = "0001") -> dict:
    return {"user": {"login": who}, "body": f"Approve: {sha} SPEC-{n}\n\nreads well"}


def run(repo, comments: list | None, reviews: list | None = None):
    args = ["--base", "main"]
    if comments is not None:
        repo.write("comments.json", json.dumps(comments))
        args += ["--comments", "comments.json"]
    if reviews is not None:
        repo.write("reviews.json", json.dumps(reviews))
        args += ["--reviews", "reviews.json"]
    return repo.run("check_specs.py", *args)


@pytest.fixture
def drafted(repo):
    """main with a Draft spec; the branch has the drafted text on its first commit (its sha)."""
    repo.commit({"config/reviewers.yaml": CONFIG, SPEC: spec("Draft")}, "base")
    repo.branch()
    repo.commit({"docs/notes.md": "x\n"}, "reviewed")
    return repo, repo.git("rev-parse", "HEAD").strip()


def test_ac4_an_ordinary_commit_that_flips_a_spec_without_an_approval_fails(drafted):
    """REQ-039 AC4: rule 5, the case a covered fix list does not reach."""
    repo, _ = drafted
    repo.commit({SPEC: spec("Approved")}, "flip")
    proc = run(repo, [])
    assert proc.returncode == 1
    assert "FAIL specs: SPEC-0001: rule 5: no Approve line by an account in spec_approvers" in (
        proc.stdout
    )


def test_ac4_a_listed_person_who_approved_the_text_lets_the_flip_pass(drafted):
    """REQ-039 AC4: rule 5, the sha is the reviewed commit and only the status line differs."""
    repo, sha = drafted
    repo.commit({SPEC: spec("Approved")}, "flip")
    for comments, reviews in (([line(sha[:9])], None), ([], [line(sha)])):
        proc = run(repo, comments, reviews)
        assert (proc.returncode, proc.stdout.splitlines()[-1]) == (0, "ok specs"), proc.stdout


def test_ac4_an_approval_of_an_older_text_fails_once_the_spec_changed(drafted):
    """REQ-039 AC4: an approval is for one text; a new text needs a new line."""
    repo, sha = drafted
    repo.commit({SPEC: spec("Draft", "A changed rule.")}, "edit")
    repo.commit({SPEC: spec("Approved", "A changed rule.")}, "flip")
    proc = run(repo, [line(sha)])
    assert proc.returncode == 1
    assert "SPEC-0001: rule 5: the spec changed after the approved sha" in proc.stdout
    now = repo.git("rev-parse", "HEAD~1").strip()
    assert run(repo, [line(sha), line(now)]).returncode == 0


def test_ac4_a_text_change_in_the_flip_commit_itself_fails(drafted):
    """REQ-039 AC4"""
    repo, sha = drafted
    repo.commit({SPEC: spec("Approved", "Sneaked in.")}, "flip")
    assert run(repo, [line(sha)]).returncode == 1


@pytest.mark.parametrize(
    "comment",
    [
        line("{sha}", who="intruder"),
        line("{sha}", n="0002"),
        {"user": {"login": "maintainer"}, "body": "Looks good\nApprove: {sha} SPEC-0001"},
        {"user": {"login": "maintainer"}, "body": "Approve: {sha}"},
        line("{nosuchsha}"),
    ],
)
def test_ac4_other_accounts_specs_forms_and_unknown_shas_count_for_nothing(drafted, comment):
    """REQ-039 AC4"""
    repo, sha = drafted
    repo.commit({SPEC: spec("Approved")}, "flip")
    text = json.dumps(comment).replace("{sha}", sha).replace("{nosuchsha}", "0" * 40)
    assert run(repo, [json.loads(text)]).returncode == 1


def test_ac4_a_new_spec_added_as_approved_needs_the_approval_too(repo):
    """REQ-039 AC4"""
    repo.commit({"config/reviewers.yaml": CONFIG, "docs/notes.md": "x\n"}, "base")
    repo.branch()
    repo.commit({SPEC: spec("Approved")}, "new")
    assert run(repo, []).returncode == 1


def test_ac4_a_spec_that_is_already_approved_and_not_flipped_is_not_asked_again(repo):
    """REQ-039 AC4: the amendment rule still guards its text; this rule is about the flip."""
    repo.commit({"config/reviewers.yaml": CONFIG, SPEC: spec("Approved"), "a": "1\n"}, "base")
    repo.branch()
    repo.commit({"a": "2\n"}, "change")
    assert run(repo, []).returncode == 0


def test_ac4_without_a_comments_file_the_approval_is_not_checked_and_the_run_says_so(drafted):
    """REQ-039 AC4: a local run has no saved comments; the pull request run always has them."""
    repo, _ = drafted
    repo.commit({SPEC: spec("Approved")}, "flip")
    proc = run(repo, None)
    assert proc.returncode == 0 and "no comments file" in proc.stdout


def test_ac4_a_failure_names_the_spec_and_never_a_handle_or_a_sha(drafted):
    """REQ-039 AC4"""
    repo, sha = drafted
    repo.commit({SPEC: spec("Approved")}, "flip")
    out = run(repo, [line(sha, who="intruder")])
    assert "intruder" not in out.stdout + out.stderr and sha[:9] not in out.stdout + out.stderr


def test_ac4_the_workflow_gives_check_specs_the_saved_comments_on_pull_requests_only():
    """REQ-039 AC4: on a push there is no comment to read, so the check is not asked for one."""
    text = WORKFLOW.read_text(encoding="utf-8")
    start = text.index("      - name: check_specs")
    block = text[start : text.index("      - name:", start + 10)]
    assert '--comments "$RUNNER_TEMP/comments.json"' in block
    assert '--reviews "$RUNNER_TEMP/reviews.json"' in block
