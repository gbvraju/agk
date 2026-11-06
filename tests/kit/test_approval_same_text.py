"""A spec approval stays valid on a later head while the approved text is unchanged (brief #628).

Amendment 124 (SPEC-0039 rule 5, SPEC-0032 rule 5), ADR-0304, REQ-046. An `Approve: <sha> SPEC-<n>`
by an account in `spec_approvers` counts for the current head when the spec file's text at the head
equals its text at the approved sha, apart from the one `- Status: Draft` line becoming
`- Status: Approved`. Files other than the spec may change (a merge of the default branch). An
unreadable blob, a renamed spec or an approved sha outside the head's history counts as
unapproved. Local git repositories in `tmp_path` and saved comments only; no network; invented
logins at example.com.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import common  # noqa: E402
import merge_cleared  # noqa: E402

SPEC = "docs/specs/0042-thing.md"
OWNER = "owner-three"
APPROVERS = [f"@{OWNER}"]
BODY = "Brief: #500\nApproval: SPEC-0042 docs/specs/0042-x.md Draft -> Approved\n"
UNKNOWN = "0f9e8d7c6b" * 4


def spec(status: str, rule: str = "A rule.") -> str:
    head = f"# SPEC-0042: Thing\n\n- Status: {status}\n"
    return head + f"- Owner: reviewers\n\n## Rules\n\n1. {rule}\n"


# --- the text rule ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("old", "new", "same"),
    [
        (spec("Draft"), spec("Draft"), True),
        (spec("Approved"), spec("Approved"), True),
        (spec("Draft"), spec("Approved"), True),
        (spec("Approved"), spec("Draft"), False),
        (spec("Draft"), spec("Rejected"), False),
        (spec("Draft"), spec("Approved", "A changed rule."), False),
        (spec("Draft"), spec("Draft", "A changed rule."), False),
        (spec("Draft"), spec("Approved") + "\n", False),
        (spec("Draft"), spec("Approved").replace("\n", "\r\n"), False),
        (spec("Draft") + "- Status: Draft\n", spec("Draft") + "- Status: Approved\n", False),
    ],
)  # fmt: skip
def test_only_the_status_flip_from_draft_to_approved_is_allowed(old, new, same):
    """REQ-046 AC4: amendment 124, the one allowed difference."""
    assert common.status_flip_only(old, new) is same


# --- merge_cleared.py (SPEC-0039 rule 5) --------------------------------------------------------


def git(root: Path, *args: str) -> str:
    env_args = ["-c", "user.email=example@example.com", "-c", "user.name=Example"]
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *env_args, "-c", "commit.gpgsign=false", *args],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout.strip()  # fmt: skip


def commit(root: Path, files: dict[str, str | None], msg: str) -> str:
    for rel, text in files.items():
        path = root / rel
        if text is None:
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", msg)
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def world(tmp_path):
    """A work repository: `main` has the Draft spec; `feature` has the reviewed commit A (its sha
    is what the person approved). Returns (root, A)."""
    root = tmp_path / "work"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    commit(root, {SPEC: spec("Draft"), "README.md": "x\n"}, "base")
    git(root, "checkout", "-q", "-b", "feature")
    approved = commit(root, {"docs/notes.md": "reviewed\n"}, "reviewed")
    return root, approved


def approve(sha: str, login: str = OWNER) -> dict:
    return {"user": {"login": login}, "body": f"Approve: {sha} SPEC-0042", "created_at": ""}


def unapproved(root: Path, head: str, comments: list[dict], body: str = BODY) -> bool:
    pull = {"body": body, "labels": []}
    return merge_cleared.unapproved(pull, comments, head, APPROVERS, root, 7)


def test_a_merge_of_main_keeps_the_approval(world):
    """REQ-046 AC4: brief #628 answer 5, head B with only a merge of the default branch."""
    root, approved = world
    git(root, "checkout", "-q", "main")
    commit(root, {"README.md": "main moved\n"}, "main moved")
    git(root, "checkout", "-q", "feature")
    git(root, "merge", "-q", "--no-edit", "main")
    head = git(root, "rev-parse", "HEAD")
    assert not unapproved(root, head, [approve(approved)])


def test_the_status_flip_alone_keeps_the_approval(world):
    """REQ-046 AC4: brief #628 answer 5, head B with the Status flip only (and a ruling file)."""
    root, approved = world
    head = commit(root, {SPEC: spec("Approved"), "docs/runs/decisions/x.md": "| row |\n"}, "flip")
    assert not unapproved(root, head, [approve(approved)])
    assert not unapproved(root, head, [approve(approved[:12])])


@pytest.mark.parametrize(
    "files",
    [
        {SPEC: spec("Approved", "A changed rule.")},
        {SPEC: spec("Draft", "A changed rule.")},
        {SPEC: spec("Draft") + "\n"},
    ],
)
def test_any_other_change_of_the_spec_needs_a_new_approval(world, files):
    """REQ-046 AC4: brief #628 answer 1."""
    root, approved = world
    head = commit(root, files, "edit")
    assert unapproved(root, head, [approve(approved)])
    assert not unapproved(root, head, [approve(head)])


def test_a_renamed_spec_needs_a_new_approval(world):
    """REQ-046 AC4: brief #628 answer 3, a renamed spec."""
    root, approved = world
    head = commit(root, {SPEC: None, "docs/specs/0042-other-name.md": spec("Draft")}, "rename")
    assert unapproved(root, head, [approve(approved)])


def test_an_unknown_sha_or_one_outside_the_history_needs_a_new_approval(world):
    """REQ-046 AC4: brief #628 answer 3, an approved sha not in the pull request's history."""
    root, _ = world
    git(root, "checkout", "-q", "-b", "elsewhere", "main")
    outside = commit(root, {"docs/other.md": "y\n"}, "outside")  # the same spec text
    git(root, "checkout", "-q", "feature")
    head = git(root, "rev-parse", "HEAD")
    assert unapproved(root, head, [approve(UNKNOWN)])
    assert unapproved(root, head, [approve(outside)])


def test_an_approval_by_another_account_or_for_another_spec_never_counts(world):
    """REQ-046 AC4: the approvers and the spec number are unchanged."""
    root, approved = world
    head = commit(root, {SPEC: spec("Approved")}, "flip")
    assert unapproved(root, head, [approve(approved, "builder-one")])
    other = {"user": {"login": OWNER}, "body": f"Approve: {approved} SPEC-0041"}
    assert unapproved(root, head, [other])


def test_two_specs_with_one_number_or_none_at_the_head_fail_closed(world):
    """REQ-046 AC4: brief #628 answer 3, a spec file that cannot be found once."""
    root, approved = world
    head = commit(root, {"docs/specs/0042-twin.md": spec("Draft")}, "twin")
    assert unapproved(root, head, [approve(approved)])


def test_a_head_missing_locally_is_fetched_from_the_pull_request_ref(world, tmp_path):
    """REQ-046 AC4: the head is read from `refs/pull/<n>/head` of origin, the ref the check
    already fetches for the merge before the merge (amendment 123)."""
    root, approved = world
    head = commit(root, {SPEC: spec("Approved")}, "flip")
    bare = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", str(bare))
    git(root, "push", "-q", str(bare), f"{head}:refs/pull/7/head", "main:main")
    checkout = tmp_path / "checkout"
    git(tmp_path, "clone", "-q", "-b", "main", str(bare), str(checkout))
    git(checkout, "fetch", "-q", "origin", f"{approved}:refs/approved")  # A only, not the head
    assert git(checkout, "cat-file", "-t", approved) == "commit"
    assert not unapproved(checkout, head, [approve(approved)])


def test_a_head_that_cannot_be_read_is_unapproved(world, tmp_path):
    """REQ-046 AC4: brief #628 answer 3, an unreadable blob is never a pass."""
    root, approved = world
    other = tmp_path / "other"
    other.mkdir()
    git(other, "init", "-q", "-b", "main")
    assert unapproved(other, "1" * 40, [approve(approved)])
    assert unapproved(root, "2" * 40, [approve(approved)])


def test_the_approve_label_still_holds(world):
    """REQ-046 AC4: SPEC-0039 rule 5, the label of a spec waiting for a person."""
    root, approved = world
    head = commit(root, {SPEC: spec("Approved")}, "flip")
    pull = {"body": BODY, "labels": [{"name": "agk:approve"}]}
    assert merge_cleared.unapproved(pull, [approve(approved)], head, APPROVERS, root, 7)


# --- check_specs.py (SPEC-0032 rule 5, the CI reader) -------------------------------------------

CONFIG = "version: 1\nverdict_authors: [reviewer]\nspec_approvers: [maintainer]\n"


def line(sha: str) -> dict:
    return {"user": {"login": "maintainer"}, "body": f"Approve: {sha} SPEC-0042"}


@pytest.fixture
def drafted(repo):
    repo.commit({"config/reviewers.yaml": CONFIG, SPEC: spec("Draft")}, "base")
    repo.branch()
    repo.commit({"docs/notes.md": "x\n"}, "reviewed")
    return repo, repo.git("rev-parse", "HEAD").strip()


def check(repo, comments: list[dict]):
    repo.write("comments.json", json.dumps(comments))
    return repo.run("check_specs.py", "--base", "main", "--comments", "comments.json")


def test_ci_a_merge_of_main_and_the_flip_keep_the_approval(drafted):
    """REQ-046 AC4: SPEC-0032 rule 5 as amended, read by check_specs.py."""
    repo, approved = drafted
    repo.git("checkout", "-q", "main")
    repo.commit({"README.md": "main moved\n"}, "main moved")
    repo.git("checkout", "-q", "feature")
    repo.git("merge", "-q", "--no-edit", "main")
    repo.commit({SPEC: spec("Approved")}, "flip")
    proc = check(repo, [line(approved)])
    assert (proc.returncode, proc.stdout.splitlines()[-1]) == (0, "ok specs"), proc.stdout


def test_ci_an_approved_sha_outside_the_history_fails(drafted):
    """REQ-046 AC4: brief #628 answer 3, in the CI reader too."""
    repo, _ = drafted
    repo.git("checkout", "-q", "-b", "elsewhere", "main")
    repo.commit({"docs/other.md": "y\n"}, "outside")  # the same spec text, another history
    outside = repo.git("rev-parse", "HEAD").strip()
    repo.git("checkout", "-q", "feature")
    repo.commit({SPEC: spec("Approved")}, "flip")
    proc = check(repo, [line(outside)])
    assert proc.returncode == 1
    assert "SPEC-0042: rule 5: the spec changed after the approved sha" in proc.stdout


def test_ci_a_status_line_other_than_draft_to_approved_fails(drafted):
    """REQ-046 AC4: the one allowed difference, in the CI reader too."""
    repo, approved = drafted
    repo.commit({SPEC: spec("Approved").replace("- Status: Approved", "- Status:  Approved")}, "x")
    proc = check(repo, [line(approved)])
    assert proc.returncode == 1, proc.stdout
