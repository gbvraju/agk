"""`session.py tidy`: finished builder worktrees and branches are listed, and removed with `--apply`
(brief #548, ADR-0272).

REQ-040. Fixture repositories with real worktrees, recorded GitHub responses (a reader stub, or the
`gh` stub of test_session on `PATH`), invented data, no network. Written before the code (answer 6).
"""

from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path

import pytest
import session as session_module
from test_session import REPO, session
from test_session import proj as session_proj  # noqa: F401  (the fixtures of test_session)
from test_session import stub as session_stub  # noqa: F401

PULLS = f"repos/{REPO}/pulls"  # the stub ignores the query (`head=` and `state=all`)
OLD = time.time() - 3 * 3600  # older than the 60 idle minutes of `[tidy] min_idle_minutes`


@pytest.fixture
def stub(request):
    return request.getfixturevalue("session_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("session_proj")


def started(repo, tidy: str = "") -> None:
    """A first commit; the lock folder is the test's own, so a real lock never keeps an item.
    TIDY is the body of a `[tidy]` table of agk.toml, if any."""
    locks = (repo.root.parent / f"{repo.root.name}-locks").as_posix()
    table = f"[tidy]\n{tidy}\n" if tidy else ""
    repo.commit({"README.md": "x\n", "agk.toml": f'lock_dir = "{locks}"\n{table}'}, "start")


def worktree(
    repo, name: str, commit: bool = True, branch: str | None = None, files: dict | None = None
) -> tuple[Path, str]:
    """A worktree on BRANCH (a builder's `claude/<name>` by default) with one commit, then FILES
    left on disk uncommitted; the commit and every file are three hours old (`aged`). Returns
    its path and tip."""
    path = repo.root / "wt" / name
    repo.git("worktree", "add", "-q", "-b", branch or f"claude/{name}", str(path), "main")
    if commit:
        (path / f"{name}.txt").write_text("work\n", encoding="utf-8")
        repo_git(path, "add", "-A")
        repo_git(path, "commit", "-q", "-m", "work", old=True)
    for rel, text in (files or {}).items():
        (path / rel).parent.mkdir(parents=True, exist_ok=True)
        (path / rel).write_text(text, encoding="utf-8")
    aged(path)
    return path, repo_git(path, "rev-parse", "HEAD").strip()


def aged(path: Path, when: float = OLD) -> None:
    """Every file and folder of the worktree PATH last changed at WHEN."""
    for folder, dirs, names in os.walk(path):
        for entry in [*dirs, *names]:
            os.utime(Path(folder) / entry, (when, when), follow_symlinks=False)
    os.utime(path, (when, when))


def repo_git(path: Path, *args: str, old: bool = False) -> str:
    import subprocess  # nosec B404 - fixed argument lists only, no shell

    stamp = f"@{int(OLD)} +0000"
    env = {**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp} if old else None
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=path, capture_output=True, text=True, check=True, env=env
    ).stdout


def pull(number: int, branch: str, sha: str, state: str = "closed", merged: bool = True) -> dict:
    return {
        "number": number,
        "state": state,
        "merged_at": "2026-11-01T10:00:00Z" if merged and state == "closed" else None,
        "head": {"ref": branch, "sha": sha},
    }


def reader(table: dict[str, object]):
    """A recorded response per branch; a branch not in the table is a read failure."""
    return lambda branch: table.get(branch)


def plan(repo, table, records=(), here=None) -> dict[str, session_module.TidyItem]:
    items = session_module.tidy_items(repo.root, reader(table), list(records), here or repo.root)
    return {i.branch: i for i in items}


def branches(repo) -> set[str]:
    return set(repo.git("branch", "--format=%(refname:short)").split())


# --- answer 2: the candidates, and answer 3: what is kept -----------------------------------------


def test_merged_and_clean_is_removed(repo):
    """REQ-040: brief #548 answers 2 and 4: a merged pull request at the tip, clean: removed."""
    started(repo)
    path, tip = worktree(repo, "brief-1")
    items = plan(repo, {"claude/brief-1": [pull(11, "claude/brief-1", tip)]})
    item = items["claude/brief-1"]
    assert item.kept is None and item.state == "merged" and item.pr == 11
    assert session_module.tidy_apply(repo.root, [item]) == [
        f"removed {item.path} claude/brief-1 #11 merged"
    ]
    assert not path.exists() and "claude/brief-1" not in branches(repo)


def test_closed_and_clean_is_removed(repo):
    """REQ-040: brief #548 answer 2: a closed pull request counts as finished."""
    started(repo)
    _, tip = worktree(repo, "brief-2")
    item = plan(repo, {"claude/brief-2": [pull(12, "claude/brief-2", tip, merged=False)]})[
        "claude/brief-2"
    ]
    assert item.kept is None and item.state == "closed"


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        ([pull(13, "claude/brief-3", "0" * 40, state="open", merged=False)], "open pull request"),
        ([], "no pull request"),
        (None, "could not read GitHub"),
        ({"message": "Bad credentials"}, "could not read GitHub"),
    ],
)
def test_open_missing_or_unreadable_pull_request_is_kept(repo, response, reason):
    """REQ-040: brief #548 answer 3: a read failure keeps the item; it never counts as merged."""
    started(repo)
    worktree(repo, "brief-3")
    assert plan(repo, {"claude/brief-3": response})["claude/brief-3"].kept == reason


def test_an_open_pull_request_beside_a_closed_one_keeps_the_branch(repo):
    """REQ-040: brief #548 answer 3: any open pull request of the branch keeps it."""
    started(repo)
    _, tip = worktree(repo, "brief-4")
    table = {
        "claude/brief-4": [
            pull(14, "claude/brief-4", tip),
            pull(15, "claude/brief-4", tip, "open", False),
        ]
    }
    assert plan(repo, table)["claude/brief-4"].kept == "open pull request"


def test_a_commit_after_the_head_is_kept(repo):
    """REQ-040: brief #548 answer 2: the tip must equal the pull request's last head."""
    started(repo)
    path, tip = worktree(repo, "brief-5")
    (path / "more.txt").write_text("later\n", encoding="utf-8")
    repo_git(path, "add", "-A")
    repo_git(path, "commit", "-q", "-m", "later")
    item = plan(repo, {"claude/brief-5": [pull(16, "claude/brief-5", tip)]})["claude/brief-5"]
    assert item.kept == "commits after the pull request's head"


@pytest.mark.parametrize("dirty", ["untracked", "modified"])
def test_uncommitted_or_untracked_files_are_kept(repo, dirty):
    """REQ-040: brief #548 answer 2: `git status --porcelain` must be empty."""
    started(repo)
    path, tip = worktree(repo, "brief-6")
    target = path / ("new.txt" if dirty == "untracked" else "brief-6.txt")
    target.write_text("unsaved\n", encoding="utf-8")
    item = plan(repo, {"claude/brief-6": [pull(17, "claude/brief-6", tip)]})["claude/brief-6"]
    assert item.kept == "uncommitted files"


def test_a_locked_worktree_is_kept(repo):
    """REQ-040: brief #548 answer 2: `git worktree lock` keeps it."""
    started(repo)
    path, tip = worktree(repo, "brief-7")
    repo.git("worktree", "lock", str(path))
    item = plan(repo, {"claude/brief-7": [pull(18, "claude/brief-7", tip)]})["claude/brief-7"]
    assert item.kept == "locked"


def test_the_current_worktree_and_the_main_clone_are_kept(repo):
    """REQ-040: brief #548 answer 2: never the current worktree, never the main clone."""
    started(repo)
    path, tip = worktree(repo, "brief-8")
    table = {"claude/brief-8": [pull(19, "claude/brief-8", tip)], "main": [pull(1, "main", tip)]}
    items = plan(repo, table, here=path)
    assert items["claude/brief-8"].kept == "current worktree"
    assert items["main"].kept == "main clone"


@pytest.mark.parametrize(
    "record",
    [
        {"session": "b9"},  # a lock owner record naming the session (its brief number)
        {"session": "brief-9"},  # ... or the worktree's own name
        {"session": ""},  # a live record of an unknown session keeps everything
        {"session": "s-other", "branch": "claude/brief-9"},  # a queue job of the branch
    ],
)
def test_a_running_session_is_kept(repo, record):
    """REQ-040: brief #548 answer 2: no lock or queue file names its session as running."""
    started(repo)
    _, tip = worktree(repo, "brief-9")
    item = plan(repo, {"claude/brief-9": [pull(20, "claude/brief-9", tip)]}, [record])[
        "claude/brief-9"
    ]
    assert item.kept == "running"


def test_a_record_of_another_session_does_not_keep_it(repo):
    """REQ-040: brief #548 answer 2: a lock held by another named session is not this one's."""
    started(repo)
    _, tip = worktree(repo, "brief-10")
    records = [{"session": "conductor"}, {"session": "b77"}]
    item = plan(repo, {"claude/brief-10": [pull(21, "claude/brief-10", tip)]}, records)[
        "claude/brief-10"
    ]
    assert item.kept is None


def test_live_lock_owner_records_are_read_and_stale_ones_ignored(tmp_path):
    """REQ-040: brief #548 answer 2: lock.py's owner record of a live holder counts as running."""
    live = tmp_path / "agk-lock-heavy"
    live.mkdir()
    owner = {"session": "b5", "pid": os.getpid(), "host": socket.gethostname(),
             "started": "2099-01-01T00:00:00Z", "token": "t"}  # fmt: skip
    (live / "owner.json").write_text(json.dumps(owner), encoding="utf-8")
    dead = tmp_path / "agk-lock-heavy.2"
    dead.mkdir()
    (dead / "owner.json").write_text(json.dumps({**owner, "session": "b6", "pid": 2**22 + 7}),
                                     encoding="utf-8")  # fmt: skip
    jobs = tmp_path / ".agk-lock-heavy.queue" / "jobs"
    jobs.mkdir(parents=True)
    job = {"ticket": "heavy-1", "seq": 1, "session": "b8", "branch": "claude/brief-8"}
    (jobs / "1.json").write_text(json.dumps(job), encoding="utf-8")
    records = session_module.running_records(tmp_path, 120)
    assert sorted(r.get("session") for r in records) == ["b5", "b8"]


# --- the fix list of 0085062: ignored files, other people's branches, an idle builder ----------


GITIGNORE = ".env\ndata/\n__pycache__/\n.pytest_cache/\n"


def test_ignored_files_that_are_not_caches_are_kept(repo):
    """REQ-040: fix list item 1: `git worktree remove` deletes ignored files, so an ignored
    `.env` or `data/db` keeps the item."""
    started(repo)
    repo.commit({".gitignore": GITIGNORE}, "ignore")
    path, tip = worktree(repo, "brief-101", files={".env": "KEY=x\n", "data/db": "rows\n"})
    item = plan(repo, {"claude/brief-101": [pull(101, "claude/brief-101", tip)]})[
        "claude/brief-101"
    ]
    assert item.kept == "ignored files"
    assert session_module.tidy_apply(repo.root, [item]) == []
    assert (path / ".env").exists() and (path / "data" / "db").exists()


def test_ignored_caches_alone_do_not_keep_it(repo):
    """REQ-040: fix list item 1: only known caches are ignored files that may go."""
    started(repo)
    repo.commit({".gitignore": GITIGNORE}, "ignore")
    caches = {"__pycache__/a.pyc": "x", "pkg/__pycache__/b.pyc": "x", ".pytest_cache/v": "x"}
    path, tip = worktree(repo, "brief-102", files=caches)
    item = plan(repo, {"claude/brief-102": [pull(102, "claude/brief-102", tip)]})[
        "claude/brief-102"
    ]
    assert item.kept is None
    session_module.tidy_apply(repo.root, [item])
    assert not path.exists()


def test_the_caches_setting_replaces_the_known_list(repo):
    """REQ-040: fix list item 1: `[tidy] caches` names the caches that may go."""
    started(repo, 'caches = ["__pycache__/"]')
    repo.commit({".gitignore": GITIGNORE}, "ignore")
    _, tip = worktree(repo, "brief-103", files={".pytest_cache/v": "x"})
    item = plan(repo, {"claude/brief-103": [pull(103, "claude/brief-103", tip)]})[
        "claude/brief-103"
    ]
    assert item.kept == "ignored files"


def test_a_branch_that_is_not_a_builders_is_kept(repo):
    """REQ-040: fix list item 2: a person's own `feature/x` worktree with a merged pull request
    is never touched."""
    started(repo)
    path, tip = worktree(repo, "x", branch="feature/x")
    repo.git("branch", "claude/brief-x")
    table = {"feature/x": [pull(104, "feature/x", tip)], "claude/brief-x": [pull(105, "a", tip)]}
    items = plan(repo, table)
    assert items["feature/x"].kept == "not a builder branch"
    assert items["claude/brief-x"].kept == "not a builder branch"  # the prefix and a number
    assert session_module.tidy_apply(repo.root, list(items.values())) == []
    assert path.exists() and "feature/x" in branches(repo)


def test_the_branch_prefix_setting_names_the_builders(repo):
    """REQ-040: fix list item 2: `[tidy] branch_prefix` replaces the builders' prefix."""
    started(repo, 'branch_prefix = "agent/"')
    _, tip = worktree(repo, "106", branch="agent/106")
    _, other = worktree(repo, "brief-107")
    table = {"agent/106": [pull(106, "agent/106", tip)],
             "claude/brief-107": [pull(107, "claude/brief-107", other)]}  # fmt: skip
    items = plan(repo, table)
    assert items["agent/106"].kept is None
    assert items["claude/brief-107"].kept == "not a builder branch"


@pytest.mark.parametrize("fresh", ["file", "commit", "folder"])
def test_a_recently_active_worktree_is_kept(repo, fresh):
    """REQ-040: fix list item 3: a builder still open in its worktree after the merge has no
    lock; a file, folder or commit younger than `[tidy] min_idle_minutes` (60) keeps it."""
    started(repo)
    path, tip = worktree(repo, "brief-108")
    if fresh == "file":
        aged(path, time.time() - 30 * 60)
    elif fresh == "folder":
        os.utime(path, None)
    else:
        (path / "brief-108.txt").write_text("again\n", encoding="utf-8")
        repo_git(path, "commit", "-q", "-am", "now")
        aged(path)
        tip = repo_git(path, "rev-parse", "HEAD").strip()
    item = plan(repo, {"claude/brief-108": [pull(108, "claude/brief-108", tip)]})[
        "claude/brief-108"
    ]
    assert item.kept == "recently active"


def test_min_idle_minutes_is_read(repo):
    """REQ-040: fix list item 3: `[tidy] min_idle_minutes` replaces the 60 minutes."""
    started(repo, "min_idle_minutes = 240")
    _, tip = worktree(repo, "brief-109")
    item = plan(repo, {"claude/brief-109": [pull(109, "claude/brief-109", tip)]})[
        "claude/brief-109"
    ]
    assert item.kept == "recently active"


@pytest.mark.parametrize(
    "body",
    ["min_idle_minutes = 0", 'min_idle_minutes = "60"', "branch_prefix = \"\"", "caches = 3",
     "other = 1"],  # fmt: skip
)
def test_a_wrong_tidy_setting_is_refused_by_name(repo, body):
    """REQ-040: fix list items 1 to 3: a wrong `[tidy]` value is refused, naming the setting."""
    started(repo, body)
    with pytest.raises(session_module.CheckError, match=r"setting: \[tidy\]"):
        plan(repo, {})


# --- answer 1 and 4: dry run by default, removal --------------------------------------------------


def test_without_apply_nothing_changes(proj, stub):
    """REQ-040: brief #548 answer 1: the dry run prints `remove ...` and changes nothing."""
    started(proj)
    path, tip = worktree(proj, "brief-11")
    stub.serve(PULLS, [pull(22, "claude/brief-11", tip)])
    before = (proj.git("worktree", "list", "--porcelain"), branches(proj))
    out = session(proj, stub, "tidy")
    assert out.returncode == 0, out.stdout
    assert any(line.startswith("remove ") and line.endswith("claude/brief-11 #22 merged")
               for line in out.stdout.splitlines()), out.stdout  # fmt: skip
    assert (proj.git("worktree", "list", "--porcelain"), branches(proj)) == before
    assert path.exists()


def test_json_lists_each_item(proj, stub):
    """REQ-040: brief #548 answer 1: `--json` gives the same items as one JSON object."""
    started(proj)
    _, tip = worktree(proj, "brief-12")
    stub.serve(PULLS, [pull(23, "claude/brief-12", tip)])
    out = session(proj, stub, "tidy", "--json")
    data = json.loads(out.stdout)
    assert data["apply"] is False
    found = {i["branch"]: i for i in data["items"]}
    assert found["claude/brief-12"]["action"] == "remove"
    assert found["main"]["action"] == "kept"


def test_a_squash_merged_branch_is_deleted_with_capital_d(repo):
    """REQ-040: brief #548 answer 4: `-d` refuses a squash-merged branch; `-D` after the tip check
    of answer 2."""
    started(repo)
    _, tip = worktree(repo, "brief-13")
    repo.git("merge", "--squash", "-q", "claude/brief-13")
    repo.git("commit", "-q", "-m", "squash")
    item = plan(repo, {"claude/brief-13": [pull(24, "claude/brief-13", tip)]})["claude/brief-13"]
    assert item.kept is None
    commands = session_module.removal_commands(str(repo.root), item)
    assert commands[-1] == ["git", "-C", str(repo.root), "branch", "-D", "claude/brief-13"]
    assert all("--force" not in c and "-f" not in c for c in commands)
    session_module.tidy_apply(repo.root, [item])
    assert "claude/brief-13" not in branches(repo)


def test_a_branch_moved_after_the_plan_is_not_deleted(repo):
    """REQ-040: brief #548 answer 4: the tip is checked again just before `-D`."""
    started(repo)
    path, tip = worktree(repo, "brief-14")
    item = plan(repo, {"claude/brief-14": [pull(25, "claude/brief-14", tip)]})["claude/brief-14"]
    (path / "late.txt").write_text("late\n", encoding="utf-8")
    repo_git(path, "add", "-A")
    repo_git(path, "commit", "-q", "-m", "late")
    lines = session_module.tidy_apply(repo.root, [item])
    assert lines == [f"kept: commits after the pull request's head ({item.path} claude/brief-14)"]
    assert path.exists() and "claude/brief-14" in branches(repo)


def test_a_branch_without_a_worktree_is_a_candidate_too(repo):
    """REQ-040: brief #548 answer 1: local branches whose pull request finished go as well."""
    started(repo)
    repo.git("branch", "claude/brief-15")
    tip = repo.git("rev-parse", "claude/brief-15").strip()
    item = plan(repo, {"claude/brief-15": [pull(26, "claude/brief-15", tip)]})["claude/brief-15"]
    assert item.kept is None and item.path is None
    assert session_module.tidy_apply(repo.root, [item]) == ["removed - claude/brief-15 #26 merged"]


@pytest.mark.parametrize(
    "path",
    [
        "C:/Users/someone/project/.claude/worktrees/brief-16",
        "C:\\PROGRA~1\\project\\wt\\brief-16",
        "\\\\?\\C:\\Users\\someone\\" + "very-long-folder-name\\" * 12 + "brief-16",
        "C:/Users/some one/wt/brief 16",
    ],
)
def test_argument_lists_on_a_fake_windows_platform(path):
    """REQ-040: brief #548 answer 4 (#508): one argument list per removal, the path unchanged."""
    item = session_module.TidyItem(
        path=path, branch="claude/brief-16", pr=27, state="merged", head="a" * 40
    )
    root = "C:\\PROGRA~1\\project"
    commands = session_module.removal_commands(root, item)
    assert commands == [
        ["git", "-C", root, "worktree", "remove", path],
        ["git", "-C", root, "worktree", "prune"],
        ["git", "-C", root, "branch", "-D", "claude/brief-16"],
    ]
    assert all(isinstance(c, list) and all(isinstance(w, str) for w in c) for c in commands)


def test_paused_refuses_tidy(proj, stub):
    """REQ-040: session rule 33: nothing is deleted while paused."""
    started(proj)
    proj.commit({"agk.toml": "paused = true\n"}, "pause")
    proj.git("update-ref", "refs/remotes/origin/main", "HEAD")
    out = session(proj, stub, "tidy", "--apply")
    assert out.returncode == 5 and out.stdout.startswith("agk paused")


# --- answer 5: the doctor's line ---------------------------------------------------------------


def finished(repo, count: int, api: Path) -> None:
    """`count` merged worktrees, each with its recorded pull request in the doctor's api-dir."""
    api.mkdir(exist_ok=True)
    for n in range(count):
        _, tip = worktree(repo, f"brief-{40 + n}")
        data = [pull(40 + n, f"claude/brief-{40 + n}", tip)]
        (api / f"tidy-pulls-claude-brief-{40 + n}.json").write_text(json.dumps(data), "utf-8")


@pytest.mark.parametrize(("count", "line"), [(6, "tidy: 6 finished worktrees"), (5, None)])
def test_doctor_prints_the_tidy_line_above_five(repo, tmp_path_factory, count, line):
    """REQ-040: brief #548 answer 5: `doctor` names the finished worktrees when n is above 5."""
    import doctor

    started(repo)
    api = tmp_path_factory.mktemp("api")
    finished(repo, count, api)
    found = doctor.tidy_line(repo.root, doctor.Reads(REPO, api))
    expected = f"{line}; run session.py tidy" if line else None
    assert found == expected
    assert doctor.render_text([], "0.0.0", found).splitlines()[-2:-1] == (
        [expected] if line else ["agk doctor 0.0.0"]
    )


def test_doctor_counts_no_unreadable_worktree(repo, tmp_path_factory):
    """REQ-040: brief #548 answer 3: a missing recorded response keeps the item, so it is not
    counted."""
    import doctor

    started(repo)
    api = tmp_path_factory.mktemp("api")
    finished(repo, 6, api)
    (api / "tidy-pulls-claude-brief-40.json").unlink()
    assert doctor.tidy_line(repo.root, doctor.Reads(REPO, api)) is None


# --- answer 5: the conductor runs `tidy --apply`, and only that form ----------------------------


@pytest.mark.parametrize(
    ("words", "allowed"),
    [
        ("tidy --apply", True),
        ("tidy", False),
        ("tidy --json", False),
        ("tidy --apply --json", False),
        ("tidy --apply --apply", False),
        ("tidy --apply; git push origin main", False),
    ],
)
def test_the_conductor_guard_allows_exactly_tidy_apply(tmp_path, words, allowed):
    """REQ-040: brief #548 answer 5: the conductor's guard lets exactly `tidy --apply` through."""
    from test_conductor_guard_queue import SCRIPT, reason, run_hook

    project = tmp_path / "project"
    (project / "scripts" / "agk").mkdir(parents=True)
    (project / SCRIPT).write_text("print('the project script')\n", encoding="utf-8")
    out = run_hook(f"python3 {SCRIPT} {words}", project)
    assert (reason(out.stdout) is None) is allowed, out.stdout
    assert reason(run_hook(f"python3 {SCRIPT} {words}", project, shadow=True).stdout) is not None
