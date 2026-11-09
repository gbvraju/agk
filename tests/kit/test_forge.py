"""SPEC-0041 build (d), first part: one forge interface for personal mode (brief #894, REQ-048).

`GithubForge` wraps the existing `metrics.Gh` and `metrics.ApiDir`; `FilesForge` keeps GitHub-shaped
JSON under `forge/` of the sidecar (rule 6) and marks a comment written in an agent session as an
agent app's (rule 8). Invented data only; no network and no `gh`.
"""

from __future__ import annotations

import json
import re
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import forge as forge_module  # noqa: E402
import metrics  # noqa: E402
import personal_state as ps  # noqa: E402
import reviewers  # noqa: E402
from common import CheckError  # noqa: E402
from forge import FilesForge, GithubForge  # noqa: E402

PERSON = "demo-dev"
WRITES = ("create_issue", "comment", "record_pull")
SHA = "a" * 40


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def sidecar(tmp_path: Path) -> Path:
    path = tmp_path / "sidecar"
    ps.make_sidecar(path, PERSON)
    return path


@pytest.fixture
def files(sidecar: Path) -> FilesForge:
    return FilesForge(sidecar, env={})


def pull(forge: FilesForge) -> int:
    return forge.record_pull("Add a page", "The body", SHA, "feature", "main")


def test_req_048_the_two_forges_answer_the_same_names(tmp_path, files):
    """REQ-048: rule 6 (one interface; the same names, the same answers)."""
    for name in ("get", *WRITES):
        assert callable(getattr(GithubForge, name)) and callable(getattr(FilesForge, name))
    number = pull(files)
    files.comment(number, "A note")
    issue = files.create_issue("A brief", "Text", ["agk-brief"])
    names = {
        f"pull-{number}": "x",
        f"comments-{number}": "x",
        f"issue-{issue}": "x",
        "pulls-open": "repos/{repo}/pulls?state=open",
        "issues-agk-brief": "repos/{repo}/issues?state=all&labels=agk-brief",
    }
    for name, endpoint in names.items():
        answer = files.get(name, endpoint)
        assert answer, name
        (tmp_path / f"{name}.json").write_text(json.dumps(answer), encoding="utf-8")
        assert GithubForge.saved(tmp_path).get(name, endpoint) == answer
    for name in ("pull-99", "comments-99", "issue-99", f"checks-{SHA}", "jobs-7"):
        assert GithubForge.saved(tmp_path).get(name, "x") is None and files.get(name, "x") is None


def test_req_048_github_forge_wraps_the_metrics_pair_unchanged(tmp_path):
    """REQ-048: rule 6 (name, endpoint and `until` reach the wrapped reader as given)."""
    seen = []

    class Reader:
        def get(self, name, endpoint, until=None):
            seen.append((name, endpoint, until))
            return "answer"

    assert GithubForge(Reader()).get("pulls", "e", until=print) == "answer"
    assert seen == [("pulls", "e", print)]
    assert isinstance(GithubForge.saved(tmp_path).source, metrics.ApiDir)
    assert isinstance(GithubForge.live("demo-org/demo-repo").source, metrics.Gh)


@pytest.mark.parametrize("write", WRITES)
def test_req_048_github_forge_refuses_every_write(tmp_path, write):
    """REQ-048: rule 1 (personal mode never writes to GitHub; the refusal names the setting)."""
    with pytest.raises(CheckError, match=r"setting: forge"):
        getattr(GithubForge.saved(tmp_path), write)()


def test_req_048_one_number_sequence_and_github_shapes(files, sidecar):
    """REQ-048: rule 6 (one sequence that outlives the object; one person; the UTC clock)."""
    assert files.create_issue("One", "A", ["agk-brief"]) == 1
    assert pull(files) == 2
    assert FilesForge(sidecar, env={}).create_issue("Three", "C", []) == 3
    assert (sidecar / "forge/issues/3.json").is_file() and (
        sidecar / "forge/pulls/2.json"
    ).is_file()
    record = files.get("pull-2", "x")
    assert record["user"]["login"] == PERSON and record["state"] == "open"
    assert record["head"] == {"ref": "feature", "sha": SHA} and record["base"]["ref"] == "main"
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", record["created_at"])
    assert files.get("issue-1", "x")["labels"] == [{"name": "agk-brief"}]
    assert files.get("pulls", "repos/{repo}/pulls?state=closed") == []


def test_req_048_comments_append_with_rising_ids(files):
    """REQ-048: rule 6 (`comments-<n>.json`; a comment belongs to an issue or a pull)."""
    number = pull(files)
    assert files.get(f"comments-{number}", "x") == []
    files.comment(number, "First")
    files.comment(number, "Second")
    stored = files.get(f"comments-{number}", "x")
    assert [c["body"] for c in stored] == ["First", "Second"] and stored[0]["id"] < stored[1]["id"]
    assert stored[0]["user"]["login"] == PERSON
    with pytest.raises(CheckError, match="forge"):
        files.comment(41, "Nowhere")


def test_req_048_a_write_is_atomic(files, sidecar, monkeypatch):
    """REQ-048: rule 6 (a failed rename leaves the old file whole and no stray file)."""
    number = pull(files)
    target = sidecar / "forge" / f"comments-{number}.json"
    before = target.read_bytes()

    def broken(*_args):
        raise OSError("rename failed")

    monkeypatch.setattr(forge_module.os, "replace", broken)
    with pytest.raises(OSError):
        files.comment(number, "Lost")
    assert target.read_bytes() == before
    assert not list(target.parent.glob("tmp*"))


def test_req_048_each_write_is_committed_alone(files, sidecar):
    """REQ-048: rule 6 (committed by the command; the person's staged change is left alone)."""
    (sidecar / "docs" / "note.md").write_text("mine\n", encoding="utf-8")
    git(sidecar, "add", "docs/note.md")
    before = int(git(sidecar, "rev-list", "--count", "HEAD"))
    number = pull(files)
    files.comment(number, "Note")
    assert int(git(sidecar, "rev-list", "--count", "HEAD")) == before + 2
    assert git(sidecar, "status", "--porcelain") == "A  docs/note.md"
    assert git(sidecar, "log", "-1", "--format=%an") == PERSON
    assert "docs/note.md" not in git(sidecar, "show", "--name-only", "--format=", "HEAD")


def test_req_048_a_failed_commit_is_a_refusal(files, monkeypatch):
    """REQ-048: rule 6 (a sidecar commit that fails never reads as a success)."""

    def failing(args, **_kw):
        return subprocess.CompletedProcess(args, 1, "", "")

    monkeypatch.setattr(forge_module.subprocess, "run", failing)
    with pytest.raises(CheckError, match="sidecar"):
        pull(files)


def test_req_048_files_forge_runs_no_gh_and_opens_no_socket(files, monkeypatch):
    """REQ-048: rule 6 (a sentinel on the subprocess call and on the socket)."""
    real, seen = subprocess.run, []

    def sentinel(args, **kw):
        seen.append(args[0])
        return real(args, **kw)

    def no_socket(*_args, **_kw):
        raise AssertionError("FilesForge opened a socket")

    monkeypatch.setattr(forge_module.subprocess, "run", sentinel)
    monkeypatch.setattr(socket, "socket", no_socket)
    number = pull(files)
    files.comment(number, "Note")
    for name in ("pulls", f"pull-{number}", f"comments-{number}", f"files-{number}"):
        files.get(name, "repos/{repo}/pulls?state=all")
    assert set(seen) == {"git"}


@pytest.mark.parametrize(("env", "marked"), [({"CLAUDECODE": "1"}, True), ({}, False)])
def test_req_048_the_agent_mark(sidecar, env, marked):
    """REQ-048: rule 8 (`CLAUDECODE` set: the comment is an agent app's, not a person's)."""
    forge = FilesForge(sidecar, env=env)
    number = pull(forge)
    forge.comment(number, "Confirmed: maybe")
    comment = forge.get(f"comments-{number}", "x")[0]
    assert comment["performed_via_github_app"] == ({"slug": "claude"} if marked else None)
    assert reviewers.via_agent(comment, ["claude"]) is marked


@pytest.mark.parametrize("value", ["[]", '["other-app"]'])
def test_req_048_removing_claude_from_agent_apps_is_refused(sidecar, value):
    """REQ-048: rule 8 (refused naming the setting, never the value)."""
    path = sidecar / "agk.toml"
    path.write_text(f"agent_apps = {value}\n" + path.read_text("utf-8"), encoding="utf-8")
    with pytest.raises(CheckError, match="setting: agent_apps") as caught:
        FilesForge(sidecar, env={})
    assert "other-app" not in str(caught.value)


def test_req_048_a_root_without_the_personal_table_is_refused(tmp_path):
    """REQ-048: rule 1 (a files forge exists only in a sidecar; the refusal names the setting)."""
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    with pytest.raises(CheckError, match="setting: personal"):
        FilesForge(tmp_path, env={})


def hold_and_die(sidecar: Path) -> None:
    """A real process takes the lock and ends without releasing it, as a killed one does."""
    code = (
        "import os, sys; from pathlib import Path\n"
        f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
        "from forge import FilesForge\n"
        f"held = FilesForge(Path({str(sidecar)!r}), env={{}}).locked()\n"
        "held.__enter__()\n"
        "os._exit(0)\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)  # nosec B603 - fixed list, no shell


def test_req_048_a_lock_left_by_a_dead_process_is_cleared(files, sidecar):
    """REQ-048: rule 6 (ADR-0295: a holder that no longer runs blocks no later write)."""
    hold_and_die(sidecar)
    assert (sidecar / "cache/forge.lock").exists()
    assert files.create_issue("After", "A", []) == 1
    assert not (sidecar / "cache/forge.lock").exists()


def test_req_048_a_lock_whose_holder_runs_is_kept(files, sidecar, monkeypatch):
    """REQ-048: rule 6 (a live holder is never cleared; the refusal names the path class)."""
    monkeypatch.setattr(forge_module, "LOCK_WAIT", 0.1)
    with files.locked():
        with pytest.raises(CheckError, match=r"path class: cache/forge\.lock"):
            FilesForge(sidecar, env={}).create_issue("Second", "B", [])
        assert (sidecar / "cache/forge.lock").exists()
    assert files.numbers("issues") == []


def test_req_048_two_writers_keep_both_numbers_and_comments(files, sidecar, monkeypatch):
    """REQ-048: rule 6 (writers that overlap each keep their number and their comment)."""
    number = pull(files)

    def slowly(real):
        def wrapped(*args):
            answer = real(*args)
            time.sleep(0.1)  # the gap in which a second writer would read the same state
            return answer

        return wrapped

    monkeypatch.setattr(FilesForge, "next_number", slowly(FilesForge.next_number))
    monkeypatch.setattr(FilesForge, "load", slowly(FilesForge.load))

    def writer(text):
        forge = FilesForge(sidecar, env={})
        made = forge.create_issue(text, "B", [])
        forge.comment(number, text)
        return made

    with ThreadPoolExecutor(2) as pool:
        made = list(pool.map(writer, ("One", "Two")))
    assert sorted(made) == [number + 1, number + 2]
    assert sorted(c["body"] for c in files.get(f"comments-{number}", "x")) == ["One", "Two"]


def test_req_048_a_bad_lock_setting_is_refused_naming_it(sidecar):
    """REQ-048: rule 6 (a malformed setting is a refusal that names the setting)."""
    path = sidecar / "agk.toml"
    path.write_text("lock_stale_minutes = 0\n" + path.read_text("utf-8"), encoding="utf-8")
    with pytest.raises(CheckError, match="setting: lock_stale_minutes"):
        FilesForge(sidecar, env={}).create_issue("One", "A", [])
