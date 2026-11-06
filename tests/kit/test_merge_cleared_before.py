"""merge_cleared.py runs governance on the would-be merge before it merges, and may merge the one
pull request that fixes a red default branch.

Brief #610 (priority 0, incidents #598 and #609), ADR-0297, amendment 123 of SPEC-0039 rules 5
and 6, REQ-046. After every other hold passes, the command builds the merge of the cleared head
onto the fetched default branch (`git merge-tree --write-tree`, as one squash commit on the
default branch), runs the same governance run as after the merge in a detached worktree outside
the checkout, and merges only when it is green; red holds with `held: the merge with the default
branch fails governance (<step>)`, exit 3. While the default branch is red, only the pull request
whose `Brief:` line names the one open red-branch issue may merge, and a green run after its merge
closes that issue with one comment naming the merge commit. Every test runs on a checkout in
`tmp_path` whose origin is a local bare repository, a fake `gh` answering from saved responses and
a fake `make`; no network, invented logins, addresses at example.com.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_merge_cleared_after import (
    MERGED,
    RED_TITLE,
    STOPPED,
    after_run,
    body_of,
    in_process,
    main_in,
    makes,
    red_writes,
    worktrees,
    writes,
)
from test_merge_cleared_verdict import (
    AUTO_ISSUE,
    BASE,
    GIT_ENV,
    HEAD,
    MERGE,
    ON,
    REPO,
    SCRIPTS,
    SHA12,
    cleared,
    fake_gh,
    git,
    one_line,
    repo,
    run,
    toml,
    world,
)

sys.path.insert(0, str(SCRIPTS))

import merge_cleared  # noqa: E402

FAILS = "held: the merge with the default branch fails governance"
PRE_BASE = f"AGK_BASE={MERGE}"  # the run before the merge: the fetched default branch is its base
AFTER_BASE = f"AGK_BASE={BASE}"  # the run after the merge: the merge commit's parent
ROUTER = {"login": "github-actions[bot]"}
RED_BODY = 'Sentence: "The default branch is red."\nPriority: 0\nAdvances: none\n'


def red_issue(number: int = 95) -> dict:
    """The router's open red-branch issue (SPEC-0032 rule 7)."""
    return {"number": number, "title": RED_TITLE, "body": RED_BODY, "user": ROUTER,
            "labels": [{"name": "agk-brief"}]}  # fmt: skip


def pull_with(body: str) -> dict:
    return {**world()["pull"], "body": body}


def fix_run(tmp_path: Path, body: str = "Brief: #95\nAdvances: none\n", reds=None, **saved):
    """A run on a red default branch for a pull request whose body is BODY."""
    issues = [red_issue()] if reds is None else reds
    return after_run(tmp_path, issues=[*issues, AUTO_ISSUE], pull=pull_with(body), **saved)


def before(ran: list[dict]) -> list[dict]:
    return [r for r in ran if r["args"][-1] == PRE_BASE]


def after(ran: list[dict]) -> list[dict]:
    return [r for r in ran if r["args"][-1] == AFTER_BASE]


def merges(made: list[list[str]]) -> list[list[str]]:
    return [c for c in made if "PUT" in c]


def closes(made: list[list[str]]) -> list[list[str]]:
    return [c for c in writes(made) if c[2] == "PATCH" and "state=closed" in c]


def scratch_left(tmp_path: Path) -> list[str]:
    temp = tmp_path / "temp"
    if not temp.exists():
        return []
    return sorted(p.name for p in temp.iterdir() if p.name.startswith("agk-merge-"))


# --- answer 1: governance on the would-be merge, before the merge ------------------------------


def test_a_stale_head_whose_merge_fails_governance_is_held_and_not_merged(tmp_path):
    """REQ-046 AC6: brief #610 answer 1 (red on the merge: held, exit 3, nothing merged)."""
    proc, made, ran, root = after_run(tmp_path, premerge_exit=2)
    assert one_line(proc) == f"merge-cleared #7 {SHA12}: {FAILS} (make governance)"
    assert proc.returncode == 3
    assert merges(made) == [] and writes(made) == [], "nothing merged, recorded or filed"
    assert len(ran) == 1 and before(ran) == ran
    assert not Path(ran[0]["args"][1]).exists() and worktrees(root) == [str(root)]
    assert scratch_left(tmp_path) == []


def test_a_green_merge_check_merges_and_governance_runs_again_after(tmp_path):
    """REQ-046 AC6: brief #610 answer 1 (green: merge, as today)."""
    proc, made, ran, root = after_run(tmp_path)
    assert one_line(proc) == MERGED and proc.returncode == 0, proc.stdout + proc.stderr
    assert len(merges(made)) == 1
    assert [r["args"][-1] for r in ran] == [PRE_BASE, AFTER_BASE], "before, then after"
    first = ran[0]["args"]
    assert first[0] == "-C" and first[2:] == ["governance", PRE_BASE]
    tree = Path(first[1])
    assert not tree.is_relative_to(root), "the worktree is outside the checkout"
    assert not tree.exists() and worktrees(root) == [str(root)]
    assert git(root, "status", "--porcelain") == "", "no file of the checkout is written"


def test_the_check_is_the_same_bounded_run_as_after_the_merge(tmp_path):
    """REQ-046 AC6: brief #610 answer 1 (`env -i`, the body file; no token reaches it)."""
    pull = pull_with("Brief: #500\nAdvances: REQ-046\nCovered-by: ADR-0261\n")
    proc, _, ran, _ = after_run(tmp_path, pull=pull)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    first, last = before(ran)[0]["env"], after(ran)[0]["env"]
    assert set(first) - {"LC_CTYPE"} == {"PATH", "HOME", "AGK_PR_BODY"}, sorted(first)
    assert set(first) == set(last)
    assert Path(first["HOME"]) != Path(last["HOME"]), "each run has its own scratch home"
    assert Path(first["AGK_PR_BODY"]).parent == Path(first["HOME"])


PROBE = """
import json, os, subprocess, sys
tree = sys.argv[sys.argv.index('-C') + 1]
def rev(spec):
    out = subprocess.run(['git', '-C', tree, 'rev-parse', '--verify', '-q', spec],
                         capture_output=True, text=True)
    return out.stdout.strip() or None
body = os.environ.get('AGK_PR_BODY')
seen = {'args': sys.argv[1:], 'parent': rev('HEAD^1'), 'second': rev('HEAD^2'),
        'tree': rev('HEAD^{tree}'), 'body': open(body, encoding='utf-8').read()}
with open(LOG, 'a', encoding='utf-8') as fh:
    fh.write(json.dumps(seen) + '\\n')
"""


def test_the_check_runs_on_one_squash_commit_onto_the_fetched_default_branch(tmp_path):
    """REQ-046 AC6: brief #610 answer 1 (`git merge-tree --write-tree` of the head onto the
    fetched default branch, in a detached worktree; one parent, as the squash merge has)."""
    root = repo(tmp_path, toml(ON))
    bin_dir, _ = fake_gh(tmp_path, comments=[cleared(HEAD, extra="")])
    log = tmp_path / "make-calls.jsonl"
    (bin_dir / "make").write_text(f"#!{sys.executable}\nLOG = {str(log)!r}\n" + PROBE,
                                  encoding="utf-8")  # fmt: skip
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert one_line(proc) == MERGED, proc.stdout + proc.stderr
    seen = makes(tmp_path)
    first = before(seen)[0]
    assert first["parent"] == MERGE and first["second"] is None
    expected = git(root, "merge-tree", "--write-tree", MERGE, HEAD).splitlines()[0]
    assert first["tree"] == expected
    assert first["body"] == world()["pull"]["body"], "the body read before the merge"
    assert git(root, "rev-parse", "refs/remotes/origin/main").strip() == MERGE, "fetched"


def plumb(bare: Path, args: list[str], data: bytes) -> str:
    env = {**os.environ, **GIT_ENV}
    return (
        subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", *args], cwd=bare, input=data, capture_output=True, check=True, env=env
        )
        .stdout.decode()
        .strip()
    )


def commit_with(bare: Path, text: str, parent: str, message: str) -> str:
    blob = plumb(bare, ["hash-object", "-w", "--stdin"], text.encode())
    tree = plumb(bare, ["mktree"], f"100644 blob {blob}\texample.txt\n".encode())
    return plumb(bare, ["commit-tree", tree, "-p", parent, "-m", message], b"")


def test_a_conflict_with_the_default_branch_holds_as_today(tmp_path):
    """REQ-046 AC4: brief #610 answer 1 (a conflict holds as today; no governance runs)."""
    root = repo(tmp_path, toml(ON))
    bare = tmp_path / "remote" / "github.com" / f"{REPO}.git"
    main = commit_with(bare, "one\n", MERGE, "main changes the file")
    head = commit_with(bare, "two\n", MERGE, "the head changes it otherwise")
    git(bare, "update-ref", "refs/heads/main", main)
    git(bare, "update-ref", "refs/pull/7/head", head)
    pull = {**world()["pull"], "head": {"sha": head}}
    bin_dir, log = fake_gh(tmp_path, pull=pull, comments=[cleared(head, extra="")])
    proc = run(root, bin_dir, "--pr", "7", "--sha", head)
    assert one_line(proc) == f"merge-cleared #7 {head[:12]}: held: conflict (rule 5)"
    assert proc.returncode == 3
    made = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert writes(made) == [] and makes(tmp_path) == []
    assert worktrees(root) == [str(root)] and scratch_left(tmp_path) == []


def test_a_head_the_fetch_cannot_bring_is_held(tmp_path):
    """REQ-046 AC6: brief #610 answer 1 (a check that cannot run never reads as green)."""
    root = repo(tmp_path, toml(ON))
    bare = tmp_path / "remote" / "github.com" / f"{REPO}.git"
    git(bare, "update-ref", "-d", "refs/pull/7/head")
    bin_dir, log = fake_gh(tmp_path, comments=[cleared(HEAD, extra="")])
    proc = run(root, bin_dir, "--pr", "7", "--sha", HEAD)
    assert one_line(proc) == f"merge-cleared #7 {SHA12}: {FAILS} (fetch)"
    assert proc.returncode == 3 and makes(tmp_path) == []
    made = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert writes(made) == []


def test_the_check_comes_after_every_other_hold(tmp_path):
    """REQ-046 AC4: brief #610 answer 1 (after every existing hold passes)."""
    proc, made, ran, _ = after_run(tmp_path, pull={**world()["pull"], "draft": True})
    assert one_line(proc) == f"merge-cleared #7 {SHA12}: held: draft (rule 5)"
    assert ran == [] and writes(made) == []


@pytest.mark.parametrize("raised", [KeyboardInterrupt, OSError, RuntimeError])
def test_an_interrupt_or_error_in_the_check_holds_and_removes_the_worktree(
    tmp_path, monkeypatch, capsys, raised
):
    """REQ-046 AC6: brief #610 answer 1 (a run that cannot finish is not green; nothing merges)."""
    root = in_process(tmp_path, monkeypatch)
    real = merge_cleared.run_governance

    def cut(root_, tree, home, body, base, wait):
        assert tree.exists(), "the worktree is there while the run runs"
        if base == MERGE:
            raise raised
        return real(root_, tree, home, body, base, wait)

    monkeypatch.setattr(merge_cleared, "run_governance", cut)
    code, lines, made = main_in(root, capsys)
    assert lines == [f"merge-cleared #7 {SHA12}: {FAILS} (governance not finished)"]
    assert code == 3 and merges(made) == [] and writes(made) == []
    assert worktrees(root) == [str(root)] and scratch_left(tmp_path) == []


def test_the_check_runs_before_the_merge_call(tmp_path, monkeypatch, capsys):
    """REQ-046 AC6: brief #610 answer 1 (the order: the check, the merge, the run after it)."""
    root = in_process(tmp_path, monkeypatch)
    order: list[str] = []
    real_run, real_merge = merge_cleared.run_governance, merge_cleared.merge_pull

    def runs(root_, tree, home, body, base, wait):
        order.append("before" if base == MERGE else "after")
        return real_run(root_, tree, home, body, base, wait)

    def merging(*args):
        order.append("merge")
        return real_merge(*args)

    monkeypatch.setattr(merge_cleared, "run_governance", runs)
    monkeypatch.setattr(merge_cleared, "merge_pull", merging)
    code, lines, _ = main_in(root, capsys)
    assert lines == [MERGED] and code == 0
    assert order == ["before", "merge", "after"]


@pytest.mark.parametrize(
    ("name", "saved", "code"),
    [("green", {}, 0), ("red before", {"premerge_exit": 1}, 3), ("red after", {"make_exit": 1}, 1)],
)
def test_the_worktree_is_removed_in_every_case(tmp_path, name, saved, code):
    """REQ-046 AC6: brief #610 answer 4 (the worktree is removed in every case)."""
    proc, _, ran, root = after_run(tmp_path, **saved)
    assert proc.returncode == code, name + proc.stdout + proc.stderr
    assert ran and all(not Path(r["args"][1]).exists() for r in ran), name
    assert worktrees(root) == [str(root)] and scratch_left(tmp_path) == [], name


# --- answer 2: the red-branch fix ---------------------------------------------------------------


def test_when_red_the_red_fix_merges_and_closes_the_issue_after_a_green_run(tmp_path):
    """REQ-046 AC6: brief #610 answer 2 (the pull request whose `Brief:` names the open
    red-branch issue merges when its check is green; the green run after closes the issue with
    one comment naming the merge commit)."""
    proc, made, ran, _ = fix_run(tmp_path)
    assert one_line(proc) == MERGED and proc.returncode == 0, proc.stdout + proc.stderr
    assert len(merges(made)) == 1 and [r["args"][-1] for r in ran] == [PRE_BASE, AFTER_BASE]
    said = [c for c in writes(made) if c[3] == f"repos/{REPO}/issues/95/comments"]
    assert len(said) == 1, made
    assert MERGE in body_of(said[0]) and "#7" in body_of(said[0])
    assert closes(made) == [["api", "--method", "PATCH", f"repos/{REPO}/issues/95",
                             "-f", "state=closed", "-f", "state_reason=completed"]]  # fmt: skip
    record = [c for c in writes(made) if c[3] == f"repos/{REPO}/issues/41/comments"]
    assert len(record) == 1, "the merge is still recorded"
    order = [c[3] for c in writes(made)]
    assert order.index(said[0][3]) < order.index(f"repos/{REPO}/issues/95"), "comment, then close"


def test_when_red_an_unrelated_pull_request_is_held(tmp_path):
    """REQ-046 AC4: brief #610 answer 2 (every other pull request stays held)."""
    proc, made, ran, _ = fix_run(tmp_path, body="Brief: #500\nAdvances: REQ-046\n")
    assert one_line(proc) == f"merge-cleared #7 {SHA12}: held: the default branch is red (rule 5)"
    assert proc.returncode == 3 and ran == [] and writes(made) == []


@pytest.mark.parametrize(
    "body",
    [
        "Advances: none\n",  # no Brief: line
        "Brief: #96\nAdvances: none\n",  # another issue
        "Brief: #95, and more\nAdvances: none\n",  # more on the line
        "Brief: #500\nBrief: #95\n",  # the first Brief: line counts
        "Fixes the red branch: Brief: #95\n",  # not a Brief: line
    ],
)
def test_when_red_only_a_brief_line_naming_the_red_issue_counts(tmp_path, body):
    """REQ-046 AC4: brief #610 answer 2 (only the `Brief:` line naming the open red issue)."""
    proc, made, ran, _ = fix_run(tmp_path, body=body)
    assert one_line(proc) == f"merge-cleared #7 {SHA12}: held: the default branch is red (rule 5)"
    assert ran == [] and writes(made) == []


def test_when_two_red_issues_are_open_nothing_merges(tmp_path):
    """REQ-046 AC4: brief #610 answer 2, Q-610-1 (the one open red-branch issue)."""
    proc, made, ran, _ = fix_run(tmp_path, reds=[red_issue(95), red_issue(97)])
    assert one_line(proc) == f"merge-cleared #7 {SHA12}: held: the default branch is red (rule 5)"
    assert ran == [] and writes(made) == []


def test_when_red_the_red_fix_whose_merge_fails_governance_is_held(tmp_path):
    """REQ-046 AC6: brief #610 answer 2 (only when the run before the merge is green)."""
    proc, made, ran, _ = fix_run(tmp_path, premerge_exit=2)
    assert one_line(proc) == f"merge-cleared #7 {SHA12}: {FAILS} (make governance)"
    assert proc.returncode == 3 and merges(made) == [] and writes(made) == []
    assert len(ran) == 1


def test_a_red_fix_whose_run_after_the_merge_is_red_leaves_the_issue_open(tmp_path):
    """REQ-046 AC6: brief #610 answer 2 (closed only when the run after the merge is green)."""
    proc, made, _, _ = fix_run(tmp_path, make_exit=2)
    assert one_line(proc) == STOPPED and proc.returncode == 1
    assert closes(made) == []
    updated = [c for c in writes(made) if c[2] == "PATCH" and c[3] == f"repos/{REPO}/issues/95"]
    assert len(updated) == 1 and "Failing check: make governance" in body_of(updated[0])
    assert red_writes(made) == [], "the one open issue is updated, not a second one opened"


def test_a_merge_on_a_green_branch_closes_no_issue(tmp_path):
    """REQ-046 AC6: brief #610 answer 2 (only the red-branch fix closes the issue)."""
    proc, made, _, _ = after_run(tmp_path)
    assert proc.returncode == 0
    assert closes(made) == [] and [c for c in writes(made) if c[2] == "PATCH"] == []


def test_a_red_issue_that_cannot_be_closed_is_said(tmp_path, monkeypatch, capsys):
    """REQ-046 AC6: brief #610 answer 2 (the merge stands; the line says the issue is open)."""
    root = in_process(tmp_path, monkeypatch, issues=[red_issue(), AUTO_ISSUE],
                      pull=pull_with("Brief: #95\nAdvances: none\n"))  # fmt: skip
    monkeypatch.setattr(merge_cleared, "close_red", lambda *args: False)
    code, lines, _ = main_in(root, capsys)
    assert lines == [f"{MERGED}: the red-branch issue cannot be closed (rule 6)"] and code == 1
