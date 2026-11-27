"""A cleared head merges on a full checkout: a shallow one is made full first, or held (REQ-046).

Brief #2058 (ADR-0856) answers 1, 2, 6 and 9 (SPEC-0039 rules 6 and 8): `merge_cleared` reads
`git rev-parse --is-shallow-repository` before it fetches for the would-be merge; a shallow
checkout runs `git fetch --unshallow` from `origin` once, and one that stays shallow holds with
the one line naming `git fetch --unshallow`, before any would-be merge, kept result or GitHub
write. A full checkout runs no fetch of history. The kept results carry the history field, so a
result kept before the build (by a shallow run) is never replayed. Git repositories in a
temporary folder (a full origin and a `--depth 1` clone of it); invented data, no network.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import conductor  # noqa: E402
import merge_cleared  # noqa: E402

SHALLOW = "the checkout is a shallow clone (setting: git fetch --unshallow)"


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def commit(root: Path, name: str) -> str:
    (root / name).write_text(f"{name}\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", name)
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def origin(tmp_path: Path) -> dict:
    """An origin with three commits on main and pull request 7's head one commit past it."""
    root = tmp_path / "origin"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    for name in ("a.txt", "b.txt", "c.txt"):
        base = commit(root, name)
    git(root, "checkout", "-q", "-b", "topic")
    head = commit(root, "d.txt")
    git(root, "update-ref", "refs/pull/7/head", head)
    git(root, "checkout", "-q", "main")
    return {"root": root, "base": base, "head": head}


def clone(origin: dict, tmp_path: Path, depth: bool = True) -> Path:
    where = tmp_path / ("shallow" if depth else "full")
    args = ["clone", "-q", *(["--depth", "1"] if depth else [])]
    git(tmp_path, *args, origin["root"].as_uri(), str(where))
    return where


def shallow(root: Path) -> str:
    return git(root, "rev-parse", "--is-shallow-repository")


def test_a_shallow_checkout_is_made_full_and_the_would_be_merge_runs(origin, tmp_path):
    root = clone(origin, tmp_path)
    assert shallow(root) == "true"
    commit_sha, base = merge_cleared.would_be_merge(root, "main", 7, origin["head"])
    assert shallow(root) == "false"
    assert base == origin["base"]
    assert commit_sha is not None and merge_cleared.SHA.fullmatch(commit_sha)


def test_a_failing_unshallow_holds_with_the_one_line_before_any_merge(origin, tmp_path):
    root = clone(origin, tmp_path)
    git(root, "remote", "set-url", "origin", (tmp_path / "gone").as_uri())
    with pytest.raises(merge_cleared.Held) as err:
        merge_cleared.would_be_merge(root, "main", 7, origin["head"])
    assert str(err.value) == SHALLOW == merge_cleared.SHALLOW
    assert shallow(root) == "true"
    assert not merge_cleared.checked_read(root)  # nothing is kept from a shallow run


def test_a_full_checkout_runs_no_history_fetch(origin, tmp_path, monkeypatch):
    root = clone(origin, tmp_path, depth=False)
    seen: list[tuple[str, ...]] = []
    real = merge_cleared.git_out

    def spy(where: Path, *args: str) -> tuple[int, str]:
        seen.append(args)
        return real(where, *args)

    monkeypatch.setattr(merge_cleared, "git_out", spy)
    assert merge_cleared.fetched_base(root, "main", 7, origin["head"]) == origin["base"]
    assert not [a for a in seen if "--unshallow" in a]
    assert ("rev-parse", "--is-shallow-repository") in seen


def test_a_folder_that_is_not_a_git_repository_holds_as_fetch_as_today(tmp_path):
    (tmp_path / "plain").mkdir()
    assert merge_cleared.would_be_merge(tmp_path / "plain", "main", 7, "0" * 40) == (None, "fetch")


def old_key(sha: str, base: str, text: str, pre: dict | None, limit: int | None) -> str:
    seen = json.dumps([sha, base, text, pre, limit], sort_keys=True, default=str)
    return hashlib.sha256(seen.encode("utf-8")).hexdigest()


def test_a_tests_fail_kept_under_the_old_key_is_not_replayed(origin, tmp_path, monkeypatch):
    root = clone(origin, tmp_path, depth=False)
    sha, base = origin["head"], origin["base"]
    kept = f"{merge_cleared.TESTS_FAIL} (tests/kit_dev/test_kit_hashes.py::test_ac1)"
    merge_cleared.checked_write(root, old_key(sha, base, "body", None, None), kept)
    ran: list[str] = []
    monkeypatch.setattr(merge_cleared, "merge_check", lambda *a, **k: ran.append("run"))
    assert merge_cleared.merge_check_once(root, "main", 7, sha, 0.0, "body") is None
    assert ran == ["run"]


def test_the_kept_key_carries_the_history_field():
    one = merge_cleared.checked_key("a" * 40, "b" * 40, "x", None, None)
    assert one != old_key("a" * 40, "b" * 40, "x", None, None)
    assert '"history": "full"' in inspect.getsource(merge_cleared.checked_key)


def test_every_would_be_merge_reads_the_history_first():
    """Answer 9: the class stays closed: the one fetch the would-be merge and the kept result
    read goes through `full_history` first."""
    fetched = inspect.getsource(merge_cleared.fetched_base)
    assert fetched.index("full_history(root)") < fetched.index('"fetch"')
    for caller in (merge_cleared.would_be_merge, merge_cleared.merge_check_once):
        assert "fetched_base(root" in inspect.getsource(caller)
    source = inspect.getsource(merge_cleared)
    assert source.count('"merge-tree", "--write-tree"') == 1  # only would_be_merge builds one


def test_the_reprove_hold_names_a_shallow_hold_and_never_raises(monkeypatch):
    def held(*_a):
        raise merge_cleared.Held(SHALLOW)

    monkeypatch.setattr(merge_cleared, "fetched_base", held)
    assert conductor.reprove_hold(Path("."), "main", 7, "a" * 40) == SHALLOW
