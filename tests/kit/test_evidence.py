"""The conductor checks a local evidence record against the head (brief #434, ADR-0233).

`scripts/agk/evidence.py check RECORD [--head SHA] [--sample N] [--json]` reads a record that
`prepush.py --record` wrote (schema 1, brief #374). It reports `stale` when the record names
another head, `dirty` when its tree was not clean and `failed` when a recorded step did not exit
0. Otherwise it adds a detached worktree of the head in a temporary folder (removed afterwards,
also on a failure), runs `make -f agk.mk agk-governance` there and re-runs a sample of the
recorded steps, chosen from the head sha, comparing exit codes under the heavy-step lock. A
different output digest is a note, never a failure. Exit 0 agrees, 1 differs, 2 usage or a bad
record, 3 an I/O error.

The fixture repositories are those of `test_prepush.py`: a stand-in `agk.mk`, `Makefile` and
`gitleaks`, with the lock folder outside the repository.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pytest
from test_prepush import LINT_FAIL, LINT_OK, MK_FAIL, MK_OK, TOML, path_with, scanner

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

LINE = re.compile(r"^Evidence check: (agrees|differs), head ([0-9a-f]{12}), record ([0-9a-f]{12})")


@pytest.fixture
def outside(tmp_path_factory) -> Path:
    """A folder outside the fixture repository: the record, the lock folder, the temp folder."""
    return tmp_path_factory.mktemp("outside")


def toml(outside: Path) -> str:
    return TOML + f"lock_dir = '{outside / 'locks'}'\n"


def project(repo, outside: Path, mk: str = MK_OK, makefile: str = LINT_OK) -> None:
    files = {"agk.toml": toml(outside), "agk.mk": mk, "Makefile": makefile, "src/a.txt": "a\n"}
    repo.commit(files, "base")
    repo.branch("feature")
    repo.commit({"src/a.txt": "b\n", "tests/test_new.py": "# new\n"}, "change")


def step(name: str, argv: list[str], code: int | None = 0, out: str = "") -> dict:
    data = out.encode()
    return {
        "name": name,
        "outcome": "ok" if code == 0 else ("skipped" if code is None else "FAIL"),
        "not_run": False,
        "argv": argv,
        "cwd": ".",
        "exit": code,
        "seconds": 0.1,
        "output_sha256": hashlib.sha256(data).hexdigest(),
        "output_bytes": len(data),
    }


def write(path: Path, repo, steps: list[dict] | None = None, **fields) -> Path:
    """A schema 1 record of the repository's head, as prepush writes it, with `fields` changed."""
    record = {
        "schema": 1,
        "head": repo.git("rev-parse", "HEAD").strip(),
        "base": repo.git("rev-parse", "main").strip(),
        "started": "2026-10-31T00:00:00Z",
        "tree_clean": True,
        "versions": {"python3": "3.12.0"},
        "steps": steps if steps is not None else [step("lint", ["make", "lint"])],
        "not_run": [],
        "result": "passed",
    }
    record.update(fields)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def check(repo, outside: Path, *args: str, scan: Path | None = None):
    temp = outside / "tmp"
    temp.mkdir(exist_ok=True)
    return repo.run(
        "evidence.py", "check", *args, PATH=path_with(scan), TMPDIR=str(temp), TMP=str(temp)
    )


def worktrees(repo) -> int:
    return repo.git("worktree", "list", "--porcelain").count("worktree ")


def left_over(outside: Path) -> list[str]:
    temp = outside / "tmp"
    return sorted(p.name for p in temp.iterdir()) if temp.is_dir() else []


def test_a_record_that_agrees_exits_0_with_one_line_to_quote(repo, outside):
    """REQ-039: brief #434 answers 2, 4 and 6 (a record that agrees, written by prepush)."""
    project(repo, outside)
    record = outside / "record.json"
    scan = scanner(outside / "bin", 0)
    made = repo.run("prepush.py", "--record", str(record), PATH=path_with(scan))
    assert made.returncode == 0, made.stdout + made.stderr
    proc = check(repo, outside, str(record), "--sample", "10", scan=scan)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    found = LINE.search(proc.stdout)
    assert found and found.group(1) == "agrees", proc.stdout
    assert found.group(2) == repo.git("rev-parse", "HEAD").strip()[:12]
    assert found.group(3) == hashlib.sha256(record.read_bytes()).hexdigest()[:12]
    assert "governance ok" in proc.stdout
    assert re.search(r"^evidence: re-ran lint: exit 0 \(recorded 0\) same", proc.stdout, re.M)
    assert worktrees(repo) == 1 and left_over(outside) == []


def test_a_record_of_another_head_is_stale(repo, outside):
    """REQ-039: brief #434 answers 1 and 6 (a stale head; no worktree is made)."""
    project(repo, outside)
    record = write(outside / "record.json", repo)
    repo.commit({"src/a.txt": "c\n"}, "later")
    proc = check(repo, outside, str(record))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert re.search(r"^evidence: stale: ", proc.stdout, re.M)
    assert LINE.search(proc.stdout).group(1) == "differs"
    assert "governance" not in proc.stdout  # nothing was re-run
    # --head names the head explicitly: the earlier one agrees.
    earlier = repo.git("rev-parse", "HEAD~1").strip()
    proc = check(repo, outside, str(record), "--head", earlier)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_a_dirty_tree_is_reported(repo, outside):
    """REQ-039: brief #434 answers 1 and 6 (a dirty tree)."""
    project(repo, outside)
    record = write(outside / "record.json", repo, tree_clean=False)
    proc = check(repo, outside, str(record))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert re.search(r"^evidence: dirty: .*\(field: tree_clean\)", proc.stdout, re.M)
    assert "governance" not in proc.stdout


def test_a_recorded_step_that_did_not_exit_0_is_failed(repo, outside):
    """REQ-039: brief #434 answer 1 (a recorded step, or a test run, that did not exit 0)."""
    project(repo, outside)
    bad = step("lint", ["make", "lint"], 2)
    record = write(outside / "record.json", repo, [bad], result="failed")
    proc = check(repo, outside, str(record))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert re.search(r"^evidence: failed: step lint exited 2$", proc.stdout, re.M)
    tests = step("tests", ["python3", "scripts/agk/test_plan.py"])
    tests["runs"] = [{"name": "project_tests", "command": "true", "cwd": ".", "exit": None}]
    record = write(outside / "record.json", repo, [tests])
    proc = check(repo, outside, str(record))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert re.search(r"^evidence: failed: run tests/project_tests exited none", proc.stdout, re.M)


def test_a_step_that_now_fails_differs(repo, outside):
    """REQ-039: brief #434 answers 2 and 6 (the re-run exits otherwise than the record says)."""
    project(repo, outside, makefile=LINT_FAIL)
    record = write(outside / "record.json", repo)  # it says lint exited 0
    proc = check(repo, outside, str(record))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert re.search(r"^evidence: re-ran lint: exit 1 \(recorded 0\) DIFFERS", proc.stdout, re.M)
    assert LINE.search(proc.stdout).group(1) == "differs"


def test_governance_that_fails_in_the_worktree_differs_and_the_worktree_is_removed(repo, outside):
    """REQ-039: brief #434 answers 2 and 6 (governance re-run; the worktree removed after a
    failure)."""
    project(repo, outside, mk=MK_FAIL)
    record = write(outside / "record.json", repo)
    proc = check(repo, outside, str(record))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert re.search(r"^evidence: governance FAIL", proc.stdout, re.M)
    assert "a number is used twice" in proc.stdout  # governance's own message
    assert worktrees(repo) == 1
    assert left_over(outside) == []


def test_the_worktree_is_removed_when_a_re_run_cannot_start(repo, outside):
    """REQ-039: brief #434 answer 2 (removed afterwards, also on a failure)."""
    project(repo, outside)
    gone = step("missing", ["no-such-tool-for-agk-evidence"])
    record = write(outside / "record.json", repo, [gone])
    proc = check(repo, outside, str(record))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert re.search(r"^evidence: re-ran missing: exit 127 \(recorded 0\) DIFFERS", proc.stdout, re.M)
    assert worktrees(repo) == 1 and left_over(outside) == []


def test_the_worktree_is_of_the_head_not_the_work_tree(repo, outside):
    """REQ-039: brief #434 answer 2 (a clean worktree of the head: local edits do not count)."""
    project(repo, outside, makefile=LINT_FAIL)
    record = write(outside / "record.json", repo, [step("lint", ["make", "lint"], 0)])
    (repo.root / "Makefile").write_text(LINT_OK, encoding="utf-8")  # uncommitted fix
    proc = check(repo, outside, str(record))
    assert proc.returncode == 1, proc.stdout + proc.stderr


def test_a_different_output_digest_is_a_note_not_a_failure(repo, outside):
    """REQ-039: brief #434 answer 2 (outputs carry timings)."""
    project(repo, outside)
    record = write(outside / "record.json", repo, [step("lint", ["make", "lint"], 0, "other")])
    proc = check(repo, outside, str(record))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert re.search(r"^evidence: re-ran lint: .* same; output digest differs \(a note\)", proc.stdout, re.M)


def test_the_same_head_gives_the_same_sample(repo, outside):
    """REQ-039: brief #434 answers 2 and 6 (the sample is chosen from the head sha)."""
    project(repo, outside)
    steps = [step(f"s{i}", ["true"]) for i in range(6)]
    record = write(outside / "record.json", repo, steps)
    first = check(repo, outside, str(record), "--sample", "2", "--json")
    second = check(repo, outside, str(record), "--sample", "2", "--json")
    assert first.returncode == 0 and second.returncode == 0, first.stdout + first.stderr
    one = [s["name"] for s in json.loads(first.stdout)["sample"]]
    two = [s["name"] for s in json.loads(second.stdout)["sample"]]
    assert one == two and len(one) == 2
    import evidence

    head = repo.git("rev-parse", "HEAD").strip()
    assert one == evidence.sample(head, [f"s{i}" for i in range(6)], 2)


def test_the_sample_is_a_pure_function_of_the_head():
    """REQ-039: brief #434 answer 2 (default one step; the same sha, the same steps; another sha
    may pick others; the order of the record does not matter)."""
    names = [f"step{i}" for i in range(8)]
    sha = "a" * 40
    assert evidence.sample(sha, names, 1) == evidence.sample(sha, list(reversed(names)), 1)
    assert len(evidence.sample(sha, names, 1)) == 1
    assert evidence.sample(sha, names, 20) == evidence.sample(sha, names, 8)
    assert sorted(evidence.sample(sha, names, 8)) == sorted(names)
    picks = {tuple(evidence.sample(hashlib.sha1(str(i).encode()).hexdigest(), names, 1)) for i in range(40)}
    assert len(picks) > 1
    assert evidence.sample(sha, [], 1) == []
    assert evidence.DEFAULT_SAMPLE == 1


def test_a_step_that_names_a_path_outside_the_repository_is_not_re_run(repo, outside):
    """REQ-039: brief #434 answer 2 (a body file outside the repository cannot be repeated)."""
    project(repo, outside)
    body = step("pr-body", ["python3", "scripts/agk/check_pr_body.py", "--draft", "false", "<outside>/body.md"])
    record = write(outside / "record.json", repo, [body])
    proc = check(repo, outside, str(record), "--sample", "5")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert re.search(r"^evidence: not repeatable: pr-body \(a path outside the repository\)", proc.stdout, re.M)
    assert "re-ran pr-body" not in proc.stdout


def test_the_re_runs_hold_the_heavy_step_lock(repo, outside):
    """REQ-039: brief #434 answer 3 (the re-runs take lock.py's `heavy` lock)."""
    seen = outside / "seen.txt"
    mk = f"agk-governance:\n\t@ls '{outside / 'locks'}' > '{seen}'\n"
    project(repo, outside, mk=mk)
    record = write(outside / "record.json", repo)
    proc = check(repo, outside, str(record))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "agk-lock-heavy" in seen.read_text(encoding="utf-8")
    assert not (outside / "locks" / "agk-lock-heavy").exists()  # released afterwards


def test_governance_gets_the_recorded_base(repo, outside):
    """REQ-039: brief #434 answer 2 (governance runs as prepush ran it, AGK_BASE the record's base)."""
    seen = outside / "base.txt"
    project(repo, outside, mk=f"agk-governance:\n\t@echo \"$$AGK_BASE\" > '{seen}'\n")
    record = write(outside / "record.json", repo)
    proc = check(repo, outside, str(record))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert seen.read_text(encoding="utf-8").strip() == repo.git("rev-parse", "main").strip()


def test_json_gives_the_whole_answer(repo, outside):
    """REQ-039: brief #434 answer 4 (`--json`)."""
    project(repo, outside)
    record = write(outside / "record.json", repo)
    proc = check(repo, outside, str(record), "--json")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads(proc.stdout)
    assert data["result"] == "agrees"
    assert data["head"] == repo.git("rev-parse", "HEAD").strip()
    assert data["record_sha256"] == hashlib.sha256(record.read_bytes()).hexdigest()
    assert data["problems"] == [] and data["governance"]["exit"] == 0
    assert data["sample"][0] == {
        "name": "lint",
        "recorded_exit": 0,
        "exit": 0,
        "same_exit": True,
        "same_output": True,
    }


@pytest.mark.parametrize(
    "fields,named",
    [
        ({"schema": 2}, "schema"),
        ({"schema": None}, "schema"),
        ({"head": "not-a-sha"}, "head"),
        ({"tree_clean": "yes"}, "tree_clean"),
        ({"steps": {}}, "steps"),
    ],
)
def test_an_unknown_schema_or_a_bad_record_exits_2(repo, outside, fields, named):
    """REQ-039: brief #434 answers 1, 4 and 6 (an unknown schema; the field is named, never the
    value)."""
    project(repo, outside)
    record = write(outside / "record.json", repo, **fields)
    proc = check(repo, outside, str(record))
    assert proc.returncode == 2, proc.stdout + proc.stderr
    out = proc.stdout + proc.stderr
    assert f"(field: {named})" in out
    assert "not-a-sha" not in out


def test_a_step_without_its_fields_is_a_bad_record(repo, outside):
    """REQ-039: brief #434 answer 4 (a bad record)."""
    project(repo, outside)
    record = write(outside / "record.json", repo, [{"name": "lint"}])
    proc = check(repo, outside, str(record))
    assert proc.returncode == 2
    assert "(field: steps)" in proc.stdout + proc.stderr


def test_text_that_is_not_json_is_a_bad_record(repo, outside):
    project(repo, outside)
    record = outside / "record.json"
    record.write_text("{not json", encoding="utf-8")
    proc = check(repo, outside, str(record))
    assert proc.returncode == 2


@pytest.mark.parametrize(
    "args",
    [[], ["record.json", "--sample", "x"], ["record.json", "--sample", "0"], ["record.json", "--what"]],
)
def test_usage_errors_exit_2(repo, outside, args):
    """REQ-039: brief #434 answer 4 (usage)."""
    project(repo, outside)
    proc = check(repo, outside, *args)
    assert proc.returncode == 2
    assert "usage: evidence.py" in proc.stdout + proc.stderr
    proc = repo.run("evidence.py")
    assert proc.returncode == 2


def test_a_head_that_does_not_resolve_exits_2(repo, outside):
    project(repo, outside)
    record = write(outside / "record.json", repo)
    proc = check(repo, outside, str(record), "--head", "0" * 40)
    assert proc.returncode == 2
    assert "(option: --head)" in proc.stdout + proc.stderr


def test_a_record_that_cannot_be_read_exits_3(repo, outside):
    """REQ-039: brief #434 answer 4 (an I/O error)."""
    project(repo, outside)
    proc = check(repo, outside, str(outside / "missing.json"))
    assert proc.returncode == 3
    assert "(option: RECORD)" in proc.stdout + proc.stderr


def test_it_posts_nothing_and_needs_no_network():
    """REQ-039: brief #434 answer 4 (it posts nothing)."""
    source = (SCRIPTS / "evidence.py").read_text(encoding="utf-8")
    for word in ("urllib", "http.client", "requests", '"gh"', "socket.create_connection"):
        assert word not in source


def test_the_local_mode_guide_uses_the_record_in_both_roles():
    """REQ-039: brief #434 answer 5."""
    guide = (SCRIPTS.parents[1] / "docs" / "guides" / "local-mode.md").read_text(encoding="utf-8")
    builder = guide.split("## What a builder runs before asking for review", 1)[1].split("\n## ", 1)[0]
    conductor = guide.split("## What the conductor checks instead of CI", 1)[1].split("\n## ", 1)[0]
    assert "prepush.py --record" in builder and "Evidence:" in builder
    assert "evidence.py check" in conductor


def test_the_kit_installs_it():
    manifest = json.loads((SCRIPTS.parents[1] / "kit" / "manifest.json").read_text(encoding="utf-8"))
    assert "scripts/agk/evidence.py" in manifest["verbatim"]
