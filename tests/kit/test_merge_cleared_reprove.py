"""The re-prove state and the hold (SPEC-0050 build (b), rules 6 and 8; brief #727, ADR-0339).

REQ-057. A pull request whose files a merged change touched since its merge base is in the
re-prove state (`session_plan.reprove_files`, local git only); `merge_cleared.py` holds it with
`held: re-prove (rule 6 of SPEC-0050)`, exit 3, nothing merged, after every hold it has today and
before the pre-merge governance run. `[flow] max_behind_merges`, opt-in, holds a head more
first-parent commits behind than it says. Every test runs on git repositories in `tmp_path`, a
fake `gh` answering from saved responses and a fake `make`; invented data only, no network.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_merge_cleared_after import makes, writes
from test_merge_cleared_pre_tests import bare_of, commit_in, merges
from test_merge_cleared_verdict import (
    AUTO_ISSUE,
    GIT_ENV,
    MERGE,
    ON,
    SCRIPTS,
    calls,
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
import session_plan  # noqa: E402

REPROVE = "held: re-prove (rule 6 of SPEC-0050)"
UNKNOWN = "held: re-prove (unknown)"
BEHIND = "held: behind the default branch (setting flow.max_behind_merges)"
SHARED = "scripts/agk/example.py"
LINES = "".join(f"# line {i}\n" for i in range(1, 6))
BASE_FILES = {SHARED: LINES, "docs/example.md": "a\n", "agk.toml": LINES}
FIRST = LINES.replace("line 1", "the branch")  # each side changes its own line: a clean merge
LAST = LINES.replace("line 5", "main")


def merge_commit(bare: Path, first: str, second: str, tree_of: str) -> str:
    """A merge commit of FIRST and SECOND (in that order) with the tree of TREE_OF."""
    env = {**os.environ, **GIT_ENV}
    tree = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "rev-parse", f"{tree_of}^{{tree}}"], cwd=bare, capture_output=True, text=True,
        check=True, env=env,
    ).stdout.strip()  # fmt: skip
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "commit-tree", tree, "-p", first, "-p", second, "-m", "merge main"], cwd=bare,
        capture_output=True, text=True, check=True, env=env,
    ).stdout.strip()  # fmt: skip


def reprove_world(
    tmp_path: Path, head_files: dict, main_files: list[dict], flow: str = "", merged: bool = False
):
    """A checkout whose default branch (agk.toml with FLOW in its flow table) and pull request #7
    each change a shared base X: the default branch by one commit per MAIN_FILES entry, the
    branch by HEAD_FILES; with MERGED the branch then merges the default branch. (The checkout,
    the head's sha.)"""
    root = repo(tmp_path, toml(ON + flow))
    bare = bare_of(root)
    base = commit_in(bare, BASE_FILES, MERGE, "x")
    main = base
    for i, files in enumerate(main_files):
        main = commit_in(bare, files, main, f"main{i}")
    head = commit_in(bare, head_files, base, "head")
    if merged:
        tip = commit_in(bare, {**main_files[-1], **head_files}, main, "tip") if main_files else main
        head = merge_commit(bare, head, main, tip)
    git(bare, "update-ref", "refs/heads/main", main)
    git(bare, "update-ref", "refs/pull/7/head", head)
    return root, head


def reprove_run(tmp_path: Path, head_files: dict, main_files: list[dict], **kw):
    """One run of the command: (the process, the gh calls, the make calls, the head)."""
    root, head = reprove_world(tmp_path, head_files, main_files, **kw)
    return one_run(tmp_path, root, head)


def one_run(tmp_path: Path, root: Path, head: str):
    pull = {**world()["pull"], "head": {"sha": head}}
    commits = [{"sha": head, "commit": {"message": "Example change\n"}}]
    bin_dir, log = fake_gh(
        tmp_path, pull=pull, comments=[cleared(head, extra="")], issues=[AUTO_ISSUE],
        commits=commits,
    )  # fmt: skip
    proc = run(root, bin_dir, "--pr", "7", "--sha", head)
    return proc, calls(log), makes(tmp_path), head


def checked(ran: list[dict]) -> bool:
    """The governance run before the merge (in its `agk-merge-check-` worktree) was reached."""
    return any(merge_cleared.CHECK_PREFIX in " ".join(c["args"]) for c in ran)


# --- rule 8: the re-prove hold -----------------------------------------------------------------


def test_a_file_both_changed_holds_with_the_re_prove_line_and_merges_nothing(tmp_path):
    """REQ-057 AC6: the branch and the default branch each change agk.toml; held, exit 3."""
    proc, made, ran, head = reprove_run(
        tmp_path, {"agk.toml": FIRST}, [{"agk.toml": LAST}]
    )
    assert one_line(proc) == f"merge-cleared #7 {head[:12]}: {REPROVE}"
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert merges(made) == [] and writes(made) == [], "nothing merged, recorded or filed"
    assert ran == [], "held before the pre-merge governance run"


def test_a_shared_file_of_the_code_holds_too(tmp_path):
    """REQ-057 AC6: no exemption in the re-prove state (Q-S0050-7)."""
    proc, made, _, head = reprove_run(tmp_path, {SHARED: FIRST}, [{SHARED: LAST}])
    assert one_line(proc) == f"merge-cleared #7 {head[:12]}: {REPROVE}"
    assert merges(made) == []


def test_a_conflict_and_a_fetch_that_fails_still_hold_as_before(tmp_path):
    """REQ-057 AC7: the would-be merge is built first, so its holds are as today (rule 8)."""
    proc, made, ran, head = reprove_run(tmp_path, {SHARED: "two\n"}, [{SHARED: "three\n"}])
    assert one_line(proc) == f"merge-cleared #7 {head[:12]}: held: conflict (rule 5)"
    assert merges(made) == [] and ran == []


def test_after_a_merge_of_the_default_branch_it_does_not_hold(tmp_path):
    """REQ-057 AC4, AC7: the merge base moved past the commit, so the state is left (rule 6)."""
    proc, made, ran, _ = reprove_run(
        tmp_path, {"agk.toml": FIRST}, [{"agk.toml": LAST}], merged=True
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert one_line(proc).endswith(f"merged {MERGE[:12]}")
    assert checked(ran) and len(merges(made)) == 1


def test_a_head_the_fetch_cannot_bring_never_passes(tmp_path):
    """REQ-057 AC6: a fetch that fails holds before any re-prove read, as today."""
    root, head = reprove_world(tmp_path, {"docs/example.md": "b\n"}, [{SHARED: "two\n"}])
    git(bare_of(root), "update-ref", "-d", "refs/pull/7/head")
    proc, made, ran, _ = one_run(tmp_path, root, head)
    assert one_line(proc).endswith("fails governance (fetch)")
    assert proc.returncode == 3 and merges(made) == [] and ran == []


@pytest.mark.parametrize("which", ["reprove_files", "behind_merges"])
def test_a_re_prove_read_that_fails_holds_as_unknown(tmp_path, monkeypatch, which):
    """REQ-057 AC6: a read that fails holds as `re-prove (unknown)`, never as a pass."""
    monkeypatch.setattr(session_plan, "reprove_files", lambda *a: [])
    monkeypatch.setattr(session_plan, "behind_merges", lambda *a: 0)
    monkeypatch.setattr(session_plan, which, lambda *a: None)
    with pytest.raises(merge_cleared.Held) as err:
        merge_cleared.reprove_check(tmp_path, "a" * 40, "b" * 40, 3)
    assert f"held: {err.value}" == UNKNOWN


def test_the_check_order_of_the_holds(tmp_path, monkeypatch):
    """REQ-057 AC6: re-prove before the count; no limit, no count read (Q-S0050-8)."""
    monkeypatch.setattr(session_plan, "reprove_files", lambda *a: ["agk.toml"])
    monkeypatch.setattr(session_plan, "behind_merges", lambda *a: 9)
    with pytest.raises(merge_cleared.Held, match=r"^re-prove \(rule 6 of SPEC-0050\)$"):
        merge_cleared.reprove_check(tmp_path, "a" * 40, "b" * 40, 3)
    monkeypatch.setattr(session_plan, "reprove_files", lambda *a: [])
    monkeypatch.setattr(session_plan, "behind_merges", lambda *a: None)
    assert merge_cleared.reprove_check(tmp_path, "a" * 40, "b" * 40, None) is None


# --- rule 8: the behind hold -------------------------------------------------------------------

FOUR = [{f"docs/main{i}.md": f"{i}\n"} for i in range(4)]


def test_four_behind_with_a_limit_of_three_holds_naming_the_setting(tmp_path):
    """REQ-057 AC6: `max_behind_merges = 3`, four first-parent commits behind."""
    proc, made, ran, head = reprove_run(
        tmp_path, {"docs/example.md": "b\n"}, FOUR, flow="max_behind_merges = 3\n"
    )
    assert one_line(proc) == f"merge-cleared #7 {head[:12]}: {BEHIND}"
    assert proc.returncode == 3 and merges(made) == [] and ran == []


def test_four_behind_with_a_limit_of_four_merges(tmp_path):
    """REQ-057 AC7: the limit holds as written (at the limit is not above it)."""
    proc, made, _, _ = reprove_run(
        tmp_path, {"docs/example.md": "b\n"}, FOUR, flow="max_behind_merges = 4\n"
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert len(merges(made)) == 1


def test_without_the_key_the_count_holds_nothing_and_the_governance_run_is_reached(tmp_path):
    """REQ-057 AC6, AC7: absent, there is no behind hold (Q-S0050-8)."""
    proc, made, ran, _ = reprove_run(tmp_path, {"docs/example.md": "b\n"}, FOUR)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert checked(ran), "the pre-merge governance run is reached"
    assert len(merges(made)) == 1


@pytest.mark.parametrize("value", ["-1", '"3"', "true", "2.5", "[3]"])
def test_a_malformed_limit_is_refused_naming_the_setting(tmp_path, value):
    """REQ-057 AC6: refused before anything is read or merged, naming the setting only."""
    proc, made, ran, _ = reprove_run(
        tmp_path, {"docs/example.md": "b\n"}, FOUR, flow=f"max_behind_merges = {value}\n"
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    line = one_line(proc)
    assert "refused:" in line and "max_behind_merges" in line
    assert value not in line.split("refused:")[1], "never the value"
    assert merges(made) == [] and ran == []


def test_the_reader_of_the_limit():
    """REQ-057 AC6: absent is None; an integer of at least 0 is itself; anything else refused."""
    assert merge_cleared.max_behind_setting({}) is None
    assert merge_cleared.max_behind_setting({"flow": {}}) is None
    assert merge_cleared.max_behind_setting({"flow": {"max_behind_merges": 0}}) == 0
    assert merge_cleared.max_behind_setting({"flow": {"max_behind_merges": 7}}) == 7
    for bad in (-1, "3", True, 2.5, None):
        with pytest.raises(merge_cleared.Refused, match="max_behind_merges"):
            merge_cleared.max_behind_setting({"flow": {"max_behind_merges": bad}})


# --- rule 8: the clean case and the hold lines ------------------------------------------------


def test_a_clean_branch_within_the_limit_reaches_governance_and_merges(tmp_path):
    """REQ-057 AC7: no shared changed file, within the limit: as today."""
    proc, made, ran, _ = reprove_run(
        tmp_path, {"docs/example.md": "b\n"}, [{SHARED: "two\n"}], flow="max_behind_merges = 3\n"
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert checked(ran) and len(merges(made)) == 1


def test_no_hold_line_names_a_file_a_count_or_a_sha():
    """REQ-057 AC6: principle 8 (Q-S0050-9)."""
    for line in (REPROVE, UNKNOWN, BEHIND):
        assert not any(c.isdigit() for c in line.replace("SPEC-0050", "").replace("rule 6", ""))
        assert "/" not in line and ".py" not in line and ".toml" not in line


# --- rule 6: the function in session_plan -----------------------------------------------------


def local(tmp_path: Path) -> Path:
    root = tmp_path / "local"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    for name, body in BASE_FILES.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(body, encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "x")
    return root


def change(root: Path, files: dict, message: str, remove: tuple = (), move: tuple = ()) -> str:
    for name, body in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(body, encoding="utf-8")
    for name in remove:
        git(root, "rm", "-q", name)
    for old, new in move:
        git(root, "mv", old, new)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD").strip()


def test_the_function_names_the_files_both_changed_sorted(tmp_path):
    """REQ-057 AC4: rule 6 (added, modified; sorted; unrelated files left out)."""
    root = local(tmp_path)
    git(root, "checkout", "-q", "-b", "feature")
    head = change(root, {"agk.toml": "# b\n", SHARED: "b\n", "docs/new.md": "n\n"}, "head")
    git(root, "checkout", "-q", "main")
    main = change(root, {SHARED: "m\n", "agk.toml": "# m\n", "docs/other.md": "o\n"}, "main")
    assert session_plan.reprove_files(root, main, head) == ["agk.toml", SHARED]


def test_a_removal_counts(tmp_path):
    """REQ-057 AC4: rule 6 (removed)."""
    root = local(tmp_path)
    git(root, "checkout", "-q", "-b", "feature")
    head = change(root, {}, "head", remove=(SHARED,))
    git(root, "checkout", "-q", "main")
    main = change(root, {SHARED: "m\n"}, "main")
    assert session_plan.reprove_files(root, main, head) == [SHARED]


def test_a_rename_counts_from_and_to(tmp_path):
    """REQ-057 AC4: rule 6 (renamed from or to)."""
    root = local(tmp_path)
    git(root, "checkout", "-q", "-b", "feature")
    head = change(root, {}, "head", move=((SHARED, "scripts/agk/renamed.py"),))
    git(root, "checkout", "-q", "main")
    main = change(root, {SHARED: "m\n"}, "main")
    assert session_plan.reprove_files(root, main, head) == [SHARED]


def test_an_unrelated_change_gives_none_and_a_merged_main_gives_none(tmp_path):
    """REQ-057 AC4: rule 6 (an empty list is a clean pull request)."""
    root = local(tmp_path)
    git(root, "checkout", "-q", "-b", "feature")
    head = change(root, {"docs/example.md": "b\n"}, "head")
    git(root, "checkout", "-q", "main")
    main = change(root, {SHARED: "m\n"}, "main")
    assert session_plan.reprove_files(root, main, head) == []
    git(root, "checkout", "-q", "feature")
    change(root, {SHARED: "f\n"}, "feature edits the shared file too")
    git(root, "merge", "-q", "-X", "ours", "--no-edit", "main")
    merged = git(root, "rev-parse", "HEAD").strip()
    assert session_plan.reprove_files(root, main, merged) == []


def test_an_unreadable_commit_gives_none(tmp_path):
    """REQ-057 AC4: a read that fails is None, never a clean empty list."""
    root = local(tmp_path)
    main = git(root, "rev-parse", "HEAD").strip()
    assert session_plan.reprove_files(root, main, "0" * 40) is None
    assert session_plan.behind_merges(root, main, "0" * 40) is None


def test_behind_counts_first_parent_commits_of_the_default_branch(tmp_path):
    """REQ-057 AC6: rule 8's count (`rev-list --count --first-parent <merge base>..<default>`)."""
    root = local(tmp_path)
    git(root, "checkout", "-q", "-b", "feature")
    head = change(root, {"docs/example.md": "b\n"}, "head")
    git(root, "checkout", "-q", "main")
    git(root, "checkout", "-q", "-b", "side")
    change(root, {"docs/side.md": "s\n"}, "side")
    git(root, "checkout", "-q", "main")
    change(root, {"docs/one.md": "1\n"}, "one")
    git(root, "merge", "-q", "--no-ff", "--no-edit", "side")
    main = git(root, "rev-parse", "HEAD").strip()
    assert session_plan.behind_merges(root, main, head) == 2
    assert session_plan.behind_merges(root, head, head) == 0
