"""The heavy checks run once for a batch of ready pull requests (brief #436, ADR-0235).

`scripts/agk/batch.py PR [PR...] [--command CMD] [--base REF] [--json] [--record FILE]` fetches
each pull request's head (`refs/pull/<n>/head`, git only), merges the heads in the given order
onto the default branch in a detached worktree in a temporary folder, leaves out a head that does
not merge cleanly as `conflict`, and runs CMD once under the heavy-step lock. When that passes
each included pull request is `batch-green <sha12>`; when it fails, CMD runs on each pull
request's own head merged onto the base and the red ones are named. It only reports.

Each fixture is a local clone of a bare repository whose `refs/pull/<n>/head` refs stand in for
GitHub's. The check command is a small script that fails when a `values/*.txt` file says `red`
and logs each run, so a test can count the heavy runs. The lock folder, the log and the
temporary folder live outside the work tree.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
CHECK = """import os, pathlib, sys
names = sorted(p.name for p in pathlib.Path("values").glob("*.txt"))
red = [n for n in names if "red" in pathlib.Path("values", n).read_text()]
with open(os.environ["BATCH_LOG"], "a", encoding="utf-8") as log:
    log.write(" ".join(names) + "\\n")
print("CHECK_OUTPUT_TEXT", names)
sys.exit(1 if red else 0)
"""
LINE = re.compile(r"^#(\d+) (batch-green|green|red|conflict|not-fetched) ([0-9a-f]{12}|-)$", re.M)
EVIDENCE = re.compile(
    r"^Evidence: batch schema 1, head ([0-9a-f]{12}), (\d+) steps ok, record ([0-9a-f]{12})$",
    re.M,
)


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("outside")


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )
    return proc.stdout


def base(repo, outside: Path) -> Path:
    """The default branch with the check script, pushed to a bare `origin`."""
    origin = outside / "origin.git"
    git(outside, "init", "-q", "--bare", "-b", "main", str(origin))
    repo.commit(
        {
            "agk.toml": f"default_branch = \"main\"\nlock_dir = '{outside / 'locks'}'\n",
            "agk.mk": f"agk-project-test:\n\t@{shlex.quote(sys.executable)} check.py\n",
            "check.py": CHECK,
            "values/base.txt": "green\n",
            "shared.txt": "base\n",
        },
        "base",
    )
    repo.git("remote", "add", "origin", str(origin))
    repo.git("push", "-q", "origin", "main")
    repo.git("fetch", "-q", "origin")
    return origin


def pull(repo, number: int, files: dict[str, str]) -> str:
    """Push a pull request's head to `refs/pull/<n>/head`; return its sha."""
    repo.git("checkout", "-q", "-b", f"pr-{number}", "main")
    repo.commit(files, f"pr {number}")
    sha = repo.git("rev-parse", "HEAD").strip()
    repo.git("push", "-q", "origin", f"HEAD:refs/pull/{number}/head")
    repo.git("checkout", "-q", "main")
    return sha


def batch(repo, outside: Path, *args: str, command: bool = True):
    extra = ["--command", f"{shlex.quote(sys.executable)} check.py"] if command else []
    return repo.run(
        "batch.py",
        *args,
        *extra,
        BATCH_LOG=str(outside / "ran.log"),
        TMPDIR=str(scratch(outside)),
    )


def scratch(outside: Path) -> Path:
    folder = outside / "tmp"
    folder.mkdir(exist_ok=True)
    return folder


def runs(outside: Path) -> list[str]:
    log = outside / "ran.log"
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def results(out: str) -> dict[int, tuple[str, str]]:
    return {int(n): (status, sha) for n, status, sha in LINE.findall(out)}


def left_behind(repo, outside: Path) -> None:
    """No worktree, temporary folder or lock is left after a run."""
    trees = [line for line in repo.git("worktree", "list", "--porcelain").splitlines()]
    assert sum(1 for line in trees if line.startswith("worktree ")) == 1, trees
    assert list(scratch(outside).iterdir()) == []
    assert not (outside / "locks" / "agk-lock-heavy").exists()


def test_three_pull_requests_green_together_cost_one_heavy_run(repo, outside):
    """REQ-039: brief #436 answers 1, 2 and 5 (three pull requests green together)."""
    base(repo, outside)
    shas = {n: pull(repo, n, {f"values/pr{n}.txt": "green\n"}) for n in (11, 12, 13)}
    proc = batch(repo, outside, "11", "12", "13")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert runs(outside) == ["base.txt pr11.txt pr12.txt pr13.txt"]
    assert results(proc.stdout) == {n: ("batch-green", sha[:12]) for n, sha in shas.items()}
    assert [int(n) for n, _, _ in LINE.findall(proc.stdout)] == [11, 12, 13]
    assert "CHECK_OUTPUT_TEXT" not in proc.stdout
    left_behind(repo, outside)


def test_one_red_among_three_is_found_by_the_per_pull_request_runs(repo, outside):
    """REQ-039: brief #436 answers 2 and 5 (one red among three)."""
    base(repo, outside)
    green1 = pull(repo, 21, {"values/pr21.txt": "green\n"})
    red = pull(repo, 22, {"values/pr22.txt": "red\n"})
    green2 = pull(repo, 23, {"values/pr23.txt": "green\n"})
    proc = batch(repo, outside, "21", "22", "23")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert runs(outside) == [
        "base.txt pr21.txt pr22.txt pr23.txt",
        "base.txt pr21.txt",
        "base.txt pr22.txt",
        "base.txt pr23.txt",
    ]
    assert results(proc.stdout) == {
        21: ("green", green1[:12]),
        22: ("red", red[:12]),
        23: ("green", green2[:12]),
    }
    # The red run's own output is shown, so a person sees why without running it again.
    assert "CHECK_OUTPUT_TEXT" in proc.stdout
    left_behind(repo, outside)


def test_a_conflict_is_left_out_and_the_rest_go_on(repo, outside):
    """REQ-039: brief #436 answers 1 and 5 (a conflict left out)."""
    base(repo, outside)
    first = pull(repo, 31, {"shared.txt": "first\n", "values/pr31.txt": "green\n"})
    clash = pull(repo, 32, {"shared.txt": "second\n", "values/pr32.txt": "green\n"})
    third = pull(repo, 33, {"values/pr33.txt": "green\n"})
    proc = batch(repo, outside, "31", "32", "33")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert runs(outside) == ["base.txt pr31.txt pr33.txt"]
    assert results(proc.stdout) == {
        31: ("batch-green", first[:12]),
        32: ("conflict", clash[:12]),
        33: ("batch-green", third[:12]),
    }
    left_behind(repo, outside)


def test_a_single_pull_request_is_one_run(repo, outside):
    """REQ-039: brief #436 answer 5 (a single pull request; Q-436-2: its batch run is its own)."""
    base(repo, outside)
    green = pull(repo, 41, {"values/pr41.txt": "green\n"})
    proc = batch(repo, outside, "41")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert runs(outside) == ["base.txt pr41.txt"]
    assert results(proc.stdout) == {41: ("batch-green", green[:12])}
    red = pull(repo, 42, {"values/pr42.txt": "red\n"})
    (outside / "ran.log").unlink()
    proc = batch(repo, outside, "42")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert runs(outside) == ["base.txt pr42.txt"]
    assert results(proc.stdout) == {42: ("red", red[:12])}


def test_the_worktree_is_removed_after_a_failure(repo, outside):
    """REQ-039: brief #436 answer 5 (the worktree removed after a failure)."""
    base(repo, outside)
    pull(repo, 51, {"values/pr51.txt": "red\n"})
    pull(repo, 52, {"values/pr52.txt": "green\n"})
    proc = batch(repo, outside, "51", "52")
    assert proc.returncode == 1
    left_behind(repo, outside)
    # A command that cannot start is a red run, and the worktree still goes.
    proc = repo.run(
        "batch.py",
        "52",
        "--command",
        "no-such-command-agk-batch",
        BATCH_LOG=str(outside / "ran.log"),
        TMPDIR=str(scratch(outside)),
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert results(proc.stdout)[52][0] == "red"
    left_behind(repo, outside)


def test_the_default_command_is_the_project_test_target(repo, outside):
    """REQ-039: brief #436 answer 2 (default CMD `make -f agk.mk agk-project-test`)."""
    base(repo, outside)
    pull(repo, 61, {"values/pr61.txt": "green\n"})
    proc = batch(repo, outside, "61", command=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert runs(outside) == ["base.txt pr61.txt"]


def test_a_head_that_cannot_be_fetched_is_named_and_the_rest_go_on(repo, outside):
    """REQ-039: brief #436 answer 1 (Q-436-3: an unknown pull request is left out)."""
    base(repo, outside)
    green = pull(repo, 71, {"values/pr71.txt": "green\n"})
    proc = batch(repo, outside, "71", "79")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert results(proc.stdout) == {71: ("batch-green", green[:12]), 79: ("not-fetched", "-")}
    assert runs(outside) == ["base.txt pr71.txt"]


def test_json_prints_one_object_and_nothing_else(repo, outside):
    """REQ-039: brief #436 answer 1 (`--json`)."""
    base(repo, outside)
    green = pull(repo, 81, {"values/pr81.txt": "green\n"})
    red = pull(repo, 82, {"values/pr82.txt": "red\n"})
    proc = batch(repo, outside, "81", "82", "--json")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    shown = json.loads(proc.stdout)
    main = repo.git("rev-parse", "origin/main").strip()
    assert shown["base"] == main
    assert shown["batch"]["outcome"] == "FAIL"
    assert [(p["number"], p["status"], p["head"]) for p in shown["pulls"]] == [
        (81, "green", green),
        (82, "red", red),
    ]


def test_record_writes_the_schema_of_the_local_run_record(repo, outside):
    """REQ-039: brief #436 answer 3 (`--record FILE`, the schema of brief #374)."""
    base(repo, outside)
    pull(repo, 91, {"values/pr91.txt": "green\n"})
    pull(repo, 92, {"values/pr92.txt": "red\n"})
    record = outside / "record.json"
    proc = repo.run(
        "batch.py",
        "91",
        "92",
        "--command",
        f"{shlex.quote(sys.executable)} check.py",
        "--record",
        str(record),
        BATCH_LOG=str(outside / "ran.log"),
        TMPDIR=str(scratch(outside)),
        AGK_PLANTED="planted-value-that-must-not-leak",
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    data = record.read_bytes()
    found = EVIDENCE.search(proc.stdout)
    assert found and found.group(3) == hashlib.sha256(data).hexdigest()[:12]
    shown = json.loads(data)
    assert shown["schema"] == 1 and shown["kind"] == "batch"
    assert shown["base"] == repo.git("rev-parse", "origin/main").strip()
    assert re.fullmatch(r"[0-9a-f]{40}", shown["head"]) and found.group(1) == shown["head"][:12]
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", shown["started"])
    assert shown["tree_clean"] is True and "python3" in shown["versions"]
    assert [s["name"] for s in shown["steps"]] == ["batch", "pr-91", "pr-92"]
    assert [s["outcome"] for s in shown["steps"]] == ["FAIL", "ok", "FAIL"]
    assert int(found.group(2)) == 1
    for step in shown["steps"]:
        assert set(step) >= {"name", "argv", "cwd", "exit", "seconds", "output_sha256"}
        assert step["argv"] == ["python3", "check.py"] and step["cwd"] == "."
    assert [p["status"] for p in shown["pulls"]] == ["green", "red"]
    assert shown["result"] == "failed"
    text = data.decode()
    assert "CHECK_OUTPUT_TEXT" not in text and "planted-value" not in text
    assert str(outside) not in text and str(repo.root) not in text


@pytest.mark.parametrize(
    "args",
    [[], ["x"], ["0"], ["5", "5"], ["5", "--command"], ["5", "--command", ""], ["5", "--bogus"]],
)
def test_a_bad_argument_is_a_usage_error(repo, outside, args):
    """REQ-039: brief #436 answer 1 (the command line)."""
    base(repo, outside)
    proc = repo.run("batch.py", *args, TMPDIR=str(scratch(outside)))
    assert proc.returncode == 2
    assert "usage: batch.py" in proc.stderr


def test_a_base_that_does_not_resolve_is_refused(repo, outside):
    """REQ-039: brief #436 answer 1 (the base names the setting, never a value)."""
    base(repo, outside)
    proc = repo.run("batch.py", "5", "--base", "no-such-ref", TMPDIR=str(scratch(outside)))
    assert proc.returncode == 2
    assert "(setting: --base, AGK_BASE, default_branch)" in proc.stdout
    assert "no-such-ref" not in proc.stdout


def test_it_only_reports(repo, outside):
    """REQ-039: brief #436 answer 3 (it labels, merges and posts nothing)."""
    base(repo, outside)
    pull(repo, 95, {"values/pr95.txt": "green\n"})
    before = (repo.git("rev-parse", "main"), repo.git("status", "--porcelain"))
    refs = repo.git("for-each-ref", "--format=%(refname)")
    assert batch(repo, outside, "95").returncode == 0
    assert (repo.git("rev-parse", "main"), repo.git("status", "--porcelain")) == before
    assert repo.git("for-each-ref", "--format=%(refname)") == refs
    source = (SCRIPTS / "batch.py").read_text(encoding="utf-8")
    for needle in ("urllib", "http.client", '"gh"', "'gh'", "requests", '"push"'):
        assert needle not in source, needle
