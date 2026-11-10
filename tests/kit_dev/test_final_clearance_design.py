"""Tests of the design sign-off rows in `check_final_clearance.py` (SPEC-0037 rules 3 and 9;
REQ-044 AC5, brief #459).

A row that the pull request adds to `docs/design/signoffs.md` (against its merge base with the
default branch, in any of its commits) counts only with an `Approve: design v<n>
<full head ID>` (or `Approve: inventory <full head ID>`) line by an account of `spec_approvers`
that names the row's head, never through an app of `agent_apps`; in solo mode the line counts
inside the person's `Confirmed:` comment too. Each commit adding a row that changes any other file
fails. Invented data and accounts only, in throwaway git repositories; no network.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "check_final_clearance.py"
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import reviewers  # noqa: E402

OWNER = "example-owner"
OTHER = "example-other"
CONDUCTOR = "example-conductor"
SIGNOFFS = "docs/design/signoffs.md"
NO_LINE = "rule 9: a design sign-off row has no Approve line by an account in spec_approvers"
MORE = "rule 9: the sign-off commit changes more than docs/design/signoffs.md"
LINK = "https://example.com/acme/books/pull/12#issuecomment-345"
AT = "2026-11-10T12:00:00Z"
HEADER = (
    "# Design sign-offs\n\n| kind | version | digest | head | date | comment |\n"
    "|---|---|---|---|---|---|\n"
)


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-c", "user.name=Example", "-c", "user.email=a@example.com", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def put(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit(root: Path, msg: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "--no-gpg-sign", "-m", msg)
    return git(root, "rev-parse", "HEAD")


def project(root: Path, solo: bool = False) -> str:
    """A repository on `main` whose head is the prototype's head, the one the person's line names;
    the pull request's branch `feature` starts there."""
    git(root, "init", "-q", "-b", "main")
    if solo:
        roles = f"version: 1\nverdict_authors: [{OWNER}]\nspec_approvers: [{OWNER}]\n"
        put(root, "config/reviewers.yaml", roles)
        put(root, "agk.toml", 'review_mode = "solo"\n')
    else:
        roles = f"version: 1\nverdict_authors: [{CONDUCTOR}]\nspec_approvers: [{OWNER}]\n"
        put(root, "config/reviewers.yaml", roles)
        put(root, "agk.toml", 'agent_apps = ["claude"]\n')
    put(root, SIGNOFFS, HEADER)
    put(root, "docs/design/prototype/v1/index.html", "<!doctype html><title>Books</title>\n")
    head = commit(root, "prototype v1")
    git(root, "checkout", "-q", "-b", "feature")
    return head


def add_row(root: Path, head: str, kind: str = "design", extra: bool = False) -> str:
    version = "v1" if kind == "design" else "-"
    row = f"| {kind} | {version} | {'a' * 64} | {head} | 2026-11-10 | {LINK} |\n"
    put(root, SIGNOFFS, HEADER + row)
    if extra:
        put(root, "README.md", "invented\n")
    return commit(root, "sign-off row")


def comment(body: str, login: str = OWNER, app: str | None = None) -> dict:
    item = {"body": body, "created_at": AT, "user": {"login": login}}
    if app:
        item["performed_via_github_app"] = {"slug": app}
    return item


def confirmed(head: str, line: str) -> dict:
    body = "\n".join(
        [
            f"Confirmed: {head}",
            f"Verdict: cleared {head}",
            line,
            "Shown:",
            "the prototype v1",
            "every screen and state",
            "signed off",
            f"confirmed by {OWNER} in a session at {AT}",
        ]
    )
    return comment(body)


def run(root: Path, *comments: dict):
    path = root.parent / "comments.json"
    path.write_text(json.dumps(list(comments)), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "CI")}
    env["AGK_BASE"] = "main"
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--comments", str(path), "--head", "HEAD"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def root(tmp_path: Path) -> Path:
    folder = tmp_path / "repo"
    folder.mkdir()
    return folder


def test_ac5_the_lines_are_read_by_listed_accounts_only():
    """REQ-044 AC5: `design_approvals` gives (kind, version, head) of listed, non-app lines."""
    head = "1" * 40
    items = [
        comment(f"Approve: design v2 {head}"),
        comment(f"Approve: inventory {head}"),
        comment(f"Approve: design v3 {head}", login=OTHER),
        comment(f"Approve: design v4 {head}", app="claude"),
        comment(f"Approve: design v5 {head[:7]}"),
        comment(f"note\nApprove: design v6 {head}"),
    ]
    found = reviewers.design_approvals(items, [OWNER], ["claude"])
    assert found == {("design", "v2", head), ("inventory", "-", head)}


def test_ac5_a_listed_account_on_the_named_head_counts(root):
    """REQ-044 AC5: the row counts with the person's line on the head it names."""
    head = project(root)
    add_row(root, head)
    proc = run(root, comment(f"Approve: design v1 {head}"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok final-clearance" in proc.stdout


def test_ac5_an_inventory_row_counts_with_its_line(root):
    """REQ-044 AC5 (rule 3): an `inventory` row counts with `Approve: inventory <head>`."""
    head = project(root)
    add_row(root, head, kind="inventory")
    assert run(root, comment(f"Approve: inventory {head}")).returncode == 0
    proc = run(root, comment(f"Approve: design v1 {head}"))
    assert proc.returncode == 1 and NO_LINE in proc.stdout


def test_ac5_a_solo_confirmed_comment_counts(root):
    """REQ-044 AC5: in solo mode the line counts inside the person's `Confirmed:` comment."""
    head = project(root, solo=True)
    add_row(root, head)
    proc = run(root, confirmed(head, f"Approve: design v1 {head}"))
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_ac5_a_solo_confirmed_line_on_another_head_does_not_count(root):
    """REQ-044 AC5: inside a confirmation the line must name the confirmed head."""
    head = project(root, solo=True)
    add_row(root, head)
    proc = run(root, confirmed("2" * 40, f"Approve: design v1 {head}"))
    assert proc.returncode == 1 and NO_LINE in proc.stdout


@pytest.mark.parametrize(
    "case",
    ["unlisted", "other head", "app", "no line", "other version"],
)
def test_ac5_a_row_without_the_persons_line_fails(root, case):
    """REQ-044 AC5: another account, another head, an app or no line does not count."""
    head = project(root)
    add_row(root, head)
    items = {
        "unlisted": [comment(f"Approve: design v1 {head}", login=OTHER)],
        "other head": [comment(f"Approve: design v1 {'3' * 40}")],
        "app": [comment(f"Approve: design v1 {head}", app="claude")],
        "no line": [comment("Looks good to me.")],
        "other version": [comment(f"Approve: design v2 {head}")],
    }[case]
    proc = run(root, *items)
    assert proc.returncode == 1
    assert NO_LINE in proc.stdout
    assert head not in proc.stdout


def test_ac5_an_extra_file_in_the_row_commit_fails(root):
    """REQ-044 AC5: the sign-off commit changes only docs/design/signoffs.md."""
    head = project(root)
    add_row(root, head, extra=True)
    proc = run(root, comment(f"Approve: design v1 {head}"))
    assert proc.returncode == 1
    assert MORE in proc.stdout


def later(root: Path, n: int = 2) -> None:
    for i in range(n):
        put(root, f"notes/{i}.md", "invented\n")
        commit(root, f"later {i}")


def test_ac5_a_row_two_commits_before_the_head_needs_its_line(root):
    """REQ-044 AC5 (rule 9): every row the pull request adds is read, not only the head's."""
    head = project(root)
    add_row(root, head)
    later(root)
    proc = run(root, comment("Looks good to me."))
    assert proc.returncode == 1 and NO_LINE in proc.stdout
    assert run(root, comment(f"Approve: design v1 {head}")).returncode == 0


def test_ac5_an_extra_file_two_commits_before_the_head_fails(root):
    """REQ-044 AC5 (rule 9): each commit of the pull request that adds a row is one-file."""
    head = project(root)
    add_row(root, head, extra=True)
    later(root)
    proc = run(root, comment(f"Approve: design v1 {head}"))
    assert proc.returncode == 1 and MORE in proc.stdout


def test_ac5_rows_on_the_default_branch_are_not_read(root):
    """REQ-044 AC5: a row already at the merge base is not the pull request's; nothing is read."""
    head = project(root)
    git(root, "checkout", "-q", "main")
    add_row(root, head)
    git(root, "checkout", "-q", "feature")
    git(root, "merge", "-q", "--no-edit", "main")
    later(root)
    assert run(root).returncode == 0


def test_ac5_without_comments_it_stays_skipped(root):
    """REQ-044 AC5: without `--comments` the check prints skipped and passes."""
    head = project(root)
    add_row(root, head)
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT)], cwd=root, capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0 and "skipped (no comments file)" in proc.stdout
