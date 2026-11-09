"""SPEC-0041 build (d), first part: `personal.py api-view` and the confirm refusal (brief #894).

The view renders `forge/` and the product's git into the files the existing `--api-dir` readers
read (rule 7): the same records give the same bytes out of `metrics.py`, `facts.py` and
`check_final_clearance.py`. The saved responses no personal record holds (the CI's checks, jobs and
runs, and the files and commits of an invented sha no git can render) are laid beside the view, so
all the forge does hold goes through it. Invented data only; no network and no `gh`.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from forge import FilesForge  # noqa: E402

TODAY = "2026-10-14"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "Demo Dev",
    "GIT_AUTHOR_EMAIL": "dev@example.com",
    "GIT_COMMITTER_NAME": "Demo Dev",
    "GIT_COMMITTER_EMAIL": "dev@example.com",
    "GIT_AUTHOR_DATE": "2026-10-06T09:00:00+02:00",
    "GIT_COMMITTER_DATE": "2026-10-06T10:00:00+02:00",
}
HELD = ("pulls.json", "pulls-open.json", "pull-", "comments-", "issue-", "issues-")
# A pull request listed without its detail is a read GitHub did not answer; a files forge has one
# record per pull request, so it has no such failure to reproduce.
NOT_A_RECORD = {"incomplete"}


def env_of(**extra: str) -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CI")} | extra


def git(root: Path, *args: str) -> str:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, check=True, env=env_of(**GIT_ENV)
    ).stdout.strip()


def script(name: str, *args: str, cwd: Path, **env: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / name), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env_of(**env),
    )


@pytest.fixture
def world(tmp_path: Path) -> dict:
    """A product clone with one commit, attached to a sidecar under an invented `AGK_HOME`."""
    clone = tmp_path / "clone"
    clone.mkdir()
    git(clone, "init", "-q", "-b", "main")
    (clone / "app.txt").write_text("one\ntwo\n", encoding="utf-8")
    (clone / "old.txt").write_text("stays the same text here\n" * 20, encoding="utf-8")
    (clone / "gone.txt").write_text("to remove\n", encoding="utf-8")
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", "first")
    home = tmp_path / "home"
    proc = script(
        "personal_state.py", "attach", "--person", "demo-dev", cwd=clone, AGK_HOME=str(home)
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    side = next((home / "projects").iterdir())
    return {"clone": clone, "home": home, "side": side, "out": tmp_path / "view"}


def api_view(w: dict) -> subprocess.CompletedProcess:
    args = ("api-view", str(w["out"]), "--clone", str(w["clone"]))
    return script("personal.py", *args, cwd=w["clone"], AGK_HOME=str(w["home"]))


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def put(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def view_of_fixture(w: dict, api: Path) -> Path:
    """The fixture's records as the files forge keeps them, rendered, and the rest laid beside."""
    forge = w["side"] / "forge"
    for name in ("pulls.json", "pulls-open.json"):
        for item in read(api / name) if (api / name).is_file() else []:
            detail = api / f"pull-{item['number']}.json"
            put(
                forge / "pulls" / f"{item['number']}.json",
                read(detail) if detail.is_file() else item,
            )
    issues: dict[int, dict] = {}
    for path in sorted(api.glob("issues-*.json")):
        for item in read(path):
            kept = issues.setdefault(item["number"], {**item, "labels": []})
            kept["labels"].append({"name": path.stem.removeprefix("issues-")})
    for number, item in issues.items():
        put(forge / "issues" / f"{number}.json", item)
    for path in api.glob("comments-*.json"):
        shutil.copy(path, forge / path.name)
    proc = api_view(w)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for path in api.glob("*.json"):
        if not path.name.startswith(HELD):
            shutil.copy(path, w["out"] / path.name)
    for path in w["out"].glob("issues-*.json"):  # a list this fixture never saved stays unread
        if not (api / path.name).is_file():
            path.unlink()
    return w["out"]


def reviewers_file(root: Path) -> None:
    (root / "config").mkdir(exist_ok=True)
    (root / "config/reviewers.yaml").write_text(
        "version: 1\nverdict_authors: [reviewer, r]\n", encoding="utf-8"
    )


METRICS_CASES = sorted(
    p.name for p in (FIXTURES / "metrics").iterdir() if p.is_dir() and p.name not in NOT_A_RECORD
)
FACTS_CASES = sorted(p.name for p in (FIXTURES / "facts").iterdir() if read(p / "case.json")["api"])


@pytest.mark.parametrize("case", METRICS_CASES)
def test_req_048_metrics_is_byte_for_byte_through_the_view(world, case):
    """REQ-048: rule 7 (every metrics fixture: the output through the view equals the saved)."""
    api = FIXTURES / "metrics" / case
    view = view_of_fixture(world, api)
    reviewers_file(world["clone"])
    saved, viewed = (
        script("metrics.py", "--api-dir", str(d), "--today", TODAY, cwd=world["clone"])
        for d in (api, view)
    )
    assert saved.stdout and (viewed.returncode, viewed.stdout) == (saved.returncode, saved.stdout)


@pytest.mark.parametrize("case", FACTS_CASES)
def test_req_048_facts_is_byte_for_byte_through_the_view(world, tmp_path, case):
    """REQ-048: rule 7 (every facts fixture with saved responses)."""
    folder = FIXTURES / "facts" / case
    view = view_of_fixture(world, folder / "api")
    hidden = folder / "testdata" / "tree"
    product = tmp_path / "product"
    shutil.copytree(hidden if hidden.is_dir() else folder / "tree", product)
    git(product, "init", "-q", "-b", "main")
    git(product, "add", "-A")
    git(product, "commit", "-q", "-m", "fixture")
    meta = read(folder / "case.json")
    flags = ["--today", meta["today"], "--weeks", str(meta["weeks"]), *meta["args"]]
    saved, viewed = (
        script("facts.py", *flags, "--api-dir", str(d), str(product), cwd=product)
        for d in (folder / "api", view)
    )
    assert saved.returncode == 0, saved.stdout + saved.stderr
    assert (viewed.returncode, viewed.stdout) == (0, saved.stdout)


def test_req_048_final_clearance_reads_the_view(world):
    """REQ-048: rule 7 (`check_final_clearance.py --comments DIR/comments-<n>.json`)."""
    api = FIXTURES / "metrics" / "fix-lists-cleared"
    view = view_of_fixture(world, api)
    reviewers_file(world["clone"])
    head = git(world["clone"], "rev-parse", "HEAD")
    one, two = (
        script(
            "check_final_clearance.py",
            "--comments",
            str(d / "comments-102.json"),
            "--head",
            head,
            cwd=world["clone"],
        )
        for d in (api, view)
    )
    assert read(view / "comments-102.json") == read(api / "comments-102.json")
    assert (one.returncode, one.stdout) == (two.returncode, two.stdout)


def feature(w: dict) -> tuple[str, str]:
    """A branch of two commits: an add, a change, a rename and a delete."""
    clone = w["clone"]
    base = git(clone, "rev-parse", "HEAD")
    git(clone, "checkout", "-q", "-b", "feature")
    (clone / "app.txt").write_text("one\nTWO\nthree\n", encoding="utf-8")
    (clone / "new.txt").write_text("fresh\n", encoding="utf-8")
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", "second", "-m", "Body line")
    git(clone, "mv", "old.txt", "moved.txt")
    git(clone, "rm", "-q", "gone.txt")
    git(clone, "commit", "-q", "-m", "third")
    return base, git(clone, "rev-parse", "HEAD")


def snapshot(root: Path) -> dict[str, tuple[str, int]]:
    return {
        str(p.relative_to(root)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_req_048_files_and_commits_come_from_the_product_git_read_only(world):
    """REQ-048: rules 4 and 7 (GitHub's shapes; nothing changes in the clone or the sidecar)."""
    base, head = feature(world)
    number = FilesForge(world["side"], env={}).record_pull("T", "B", head, "feature", "main")
    clone_before, side_before = snapshot(world["clone"]), snapshot(world["side"])
    assert api_view(world).returncode == 0
    assert snapshot(world["clone"]) == clone_before and snapshot(world["side"]) == side_before
    files = {f["filename"]: f for f in read(world["out"] / f"files-{number}.json")}
    assert files["new.txt"] == {
        "additions": 1, "changes": 1, "deletions": 0, "filename": "new.txt", "status": "added",
    }  # fmt: skip
    assert (files["app.txt"]["status"], files["app.txt"]["additions"]) == ("modified", 2)
    assert files["app.txt"]["deletions"] == 1 and files["gone.txt"]["status"] == "removed"
    assert (files["moved.txt"]["status"], files["moved.txt"]["previous_filename"]) == (
        "renamed", "old.txt",
    )  # fmt: skip
    commits = read(world["out"] / f"commits-{number}.json")
    assert [c["commit"]["message"] for c in commits] == ["second\n\nBody line", "third"]
    assert commits[-1]["sha"] == head and commits[0]["parents"] == [{"sha": base}]
    assert commits[0]["commit"]["author"] == {
        "date": "2026-10-06T07:00:00Z", "email": "dev@example.com", "name": "Demo Dev",
    }  # fmt: skip
    assert commits[0]["commit"]["committer"]["date"] == "2026-10-06T08:00:00Z"


def test_req_048_git_rendered_records_read_byte_for_byte(world, tmp_path):
    """REQ-048: rule 7 (facts through the view equals facts through a saved copy of its files)."""
    _, head = feature(world)
    forge = FilesForge(world["side"], env={})
    number = forge.record_pull("Add", "Advances: REQ-048", head, "feature", "main")
    forge.comment(number, "A note")
    assert api_view(world).returncode == 0
    saved = tmp_path / "saved"
    saved.mkdir()
    for path in world["out"].glob("*.json"):
        (saved / path.name).write_text(json.dumps(read(path)), encoding="utf-8")
    clone = world["clone"]
    one, two = (
        script(
            "facts.py",
            "--today",
            TODAY,
            "--repo",
            "demo-org/demo-repo",
            "--api-dir",
            str(d),
            str(clone),
            cwd=clone,
        )
        for d in (world["out"], saved)
    )
    assert one.returncode == 0, one.stdout + one.stderr
    assert one.stdout == two.stdout and head in one.stdout


@pytest.mark.parametrize(("head", "base"), [("b" * 40, "main"), (None, "--output=escape.txt")])
def test_req_048_an_unreadable_record_leaves_files_unknown(world, head, base):
    """REQ-048: rules 4 and 7 (no file rather than an empty answer; no option from a record)."""
    head = head or git(world["clone"], "rev-parse", "HEAD")
    number = FilesForge(world["side"], env={}).record_pull("T", "B", head, "feature", base)
    assert api_view(world).returncode == 0
    assert (world["out"] / f"pull-{number}.json").is_file()
    assert not (world["out"] / f"files-{number}.json").exists()
    assert not (world["out"] / f"commits-{number}.json").exists()
    assert not (world["clone"] / "escape.txt").exists()


@pytest.mark.parametrize("where", ["view", ".git/view"])
def test_req_048_a_view_inside_the_clone_is_refused(world, where):
    """REQ-048: rule 7 (DIR is outside the clone; the refusal names the rule, not the path)."""
    world["out"] = world["clone"] / where
    proc = api_view(world)
    assert proc.returncode == 1 and "rule 7" in proc.stdout
    assert str(world["clone"]) not in proc.stdout and not world["out"].exists()


def test_req_048_a_non_empty_folder_and_an_unattached_clone_are_refused(world, tmp_path):
    """REQ-048: rules 3 and 7 (a view never mixes with other files; no sidecar, no view)."""
    world["out"].mkdir()
    (world["out"] / "mine.txt").write_text("keep\n", encoding="utf-8")
    proc = api_view(world)
    assert proc.returncode == 1 and "rule 7" in proc.stdout
    assert [p.name for p in world["out"].iterdir()] == ["mine.txt"]
    other = tmp_path / "other"
    other.mkdir()
    git(other, "init", "-q", "-b", "main")
    world["clone"], world["out"] = other, tmp_path / "view2"
    proc = api_view(world)
    assert proc.returncode == 1 and "not attached" in proc.stdout


def test_req_048_empty_lists_and_the_agent_mark_through_the_view(world):
    """REQ-048: rules 7 and 8 (no record is an empty list; the mark reaches the readers)."""
    forge = FilesForge(world["side"], env={"CLAUDECODE": "1"})
    number = forge.create_issue("T", "B", [])
    forge.comment(number, "Approve: SPEC-0001")
    assert api_view(world).returncode == 0
    for name in ("pulls", "pulls-open", "issues-agk-metrics", "issues-agk-brief"):
        assert read(world["out"] / f"{name}.json") == []
    comment = read(world["out"] / f"comments-{number}.json")[0]
    assert comment["performed_via_github_app"] == {"slug": "claude"}


@pytest.mark.parametrize(("env", "word"), [({"CLAUDECODE": "1"}, "CLAUDECODE"), ({}, "build (g)")])
def test_req_048_confirm_refused_in_a_session_and_later_otherwise(world, env, word):
    """REQ-048: rule 8 (refused as `local_mode.py --write` is; else it comes in build (g))."""
    before = snapshot(world["home"])
    proc = script("personal.py", "confirm", cwd=world["clone"], AGK_HOME=str(world["home"]), **env)
    assert proc.returncode == 1 and word in proc.stdout
    assert snapshot(world["home"]) == before


@pytest.mark.parametrize("args", [[], ["sync"], ["api-view"], ["api-view", "a", "--nope"]])
def test_req_048_bad_arguments_print_the_usage(world, args):
    """REQ-048: rule 7 (exit 2 and the usage; the other subcommands come in later builds)."""
    proc = script("personal.py", *args, cwd=world["clone"], AGK_HOME=str(world["home"]))
    assert proc.returncode == 2 and "usage: personal.py" in proc.stderr
