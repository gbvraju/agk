"""The test plan: which tests a change will run in proof, and why (brief #325, ADR-0185).

`scripts/agk/test_plan.py` reads git and files only and prints, before anything runs, the plan that
`proof.py` runs: for each `[proof]` area its added or changed test files, the command line with
`{files}` filled in and its working folder; the areas with nothing to run; and the test files in no
area, as "not run by proof". Without a `[proof]` table it prints `project_tests` and the files that
`test_dirs` and `test_patterns` select. Both scripts build the plan with one function
(`proof.plan`), and a test here proves they give the same commands for the same change.
"""

from __future__ import annotations

import json
from pathlib import Path

import proof
import pytest
from test_proof_areas import TWO_AREAS, area, start


def plan(repo, *args: str):
    return repo.run("test_plan.py", *args)


def data(repo, *args: str) -> dict:
    proc = plan(repo, "--json", *args)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def runs(doc: dict) -> dict:
    return {r["name"]: r for r in doc["runs"]}


def test_two_areas_each_with_its_files_command_and_folder(repo):
    """REQ-016: brief #325 answer 1 (two areas; the command line as proof fills it)."""
    start(repo, TWO_AREAS)
    repo.commit(
        {
            "backend/tests/test_new.py": "# new\n",
            "backend/tests/test_old.py": "# changed\n",
            "frontend/tests/new.test.ts": "// new\n",
        },
        "change",
    )
    doc = data(repo)
    assert doc["proof_table"] is True
    assert [r["name"] for r in doc["runs"]] == ["backend", "frontend"]
    backend, frontend = runs(doc)["backend"], runs(doc)["frontend"]
    assert backend["files"] == ["backend/tests/test_new.py", "backend/tests/test_old.py"]
    assert backend["cwd"] == "backend"
    assert backend["command"] == "test -f ../be.txt && ls tests/test_new.py tests/test_old.py"
    assert frontend["files"] == ["frontend/tests/new.test.ts"]
    assert frontend["command"] == "test -f ../fe.txt && ls tests/new.test.ts"
    assert doc["nothing_to_run"] == [] and doc["not_run_by_proof"] == []
    text = plan(repo)
    assert text.returncode == 0, text.stdout + text.stderr
    out = text.stdout
    assert "backend: runs 2 test files" in out and "frontend: runs 1 test file" in out
    assert "  command: test -f ../be.txt && ls tests/test_new.py tests/test_old.py\n" in out
    assert "  folder: backend\n" in out
    assert "  file: backend/tests/test_new.py\n" in out


def test_an_area_with_no_change_is_listed_as_nothing_to_run(repo):
    """REQ-016: brief #325 answer 1 (the areas with nothing to run)."""
    start(repo, TWO_AREAS)
    repo.commit({"backend/tests/test_new.py": "# new\n"}, "change")
    doc = data(repo)
    assert list(runs(doc)) == ["backend"]
    assert doc["nothing_to_run"] == ["frontend"]
    assert "frontend: nothing to run" in plan(repo).stdout


def test_a_test_file_in_no_area_is_listed_as_not_run_by_proof(repo):
    """REQ-016: brief #325 answer 1 (a missing area is visible)."""
    start(repo, TWO_AREAS)
    repo.commit(
        {"backend/tests/test_new.py": "# new\n", "tests/test_orphan.py": "# in no area\n"},
        "change",
    )
    doc = data(repo)
    assert doc["not_run_by_proof"] == ["tests/test_orphan.py"]
    assert all("tests/test_orphan.py" not in r["files"] for r in doc["runs"])
    out = plan(repo).stdout
    assert "not run by proof (in no [proof] area): tests/test_orphan.py\n" in out


def test_a_deletion_only_runs_nothing(repo):
    """REQ-016: brief #325 answer 1 (a deleted test is not run; proof reads no-test-files)."""
    start(repo, TWO_AREAS, files={"backend/pyproject.toml": "\n"})  # the folder stays
    repo.commit({"backend/tests/test_old.py": None}, "delete")
    doc = data(repo)
    assert doc["runs"] == []
    assert doc["nothing_to_run"] == ["backend", "frontend"]
    assert doc["deleted"] == ["backend/tests/test_old.py"]
    assert doc["not_run_by_proof"] == []
    out = plan(repo).stdout
    assert "deleted (removed on the base, not run): backend/tests/test_old.py\n" in out
    assert proof.prove(repo.root, *range_of(repo), "").reason == "no-test-files"


def test_without_a_table_it_prints_project_tests_and_the_selected_files(repo):
    """REQ-016: brief #325 answer 1 (no `[proof]` table)."""
    start(repo, project_tests="python3 -m pytest -q")
    repo.commit({"tests/test_new.py": "# new\n", "src/code.txt": "head\n"}, "change")
    doc = data(repo)
    assert doc["proof_table"] is False
    assert doc["runs"] == [
        {
            "name": "project_tests",
            "files": ["tests/test_new.py"],
            "command": "python3 -m pytest -q",
            "cwd": ".",
        }
    ]
    assert doc["nothing_to_run"] == [] and doc["not_run_by_proof"] == []
    out = plan(repo).stdout
    assert "project_tests: runs 1 test file" in out
    assert "  command: python3 -m pytest -q\n" in out
    assert "test_dirs" in out and "test_patterns" in out


def test_without_a_table_and_without_project_tests_nothing_runs_and_the_setting_is_named(repo):
    """REQ-016: brief #325 answer 1 (proof reads no-project-tests here)."""
    start(repo, project_tests=None)
    repo.commit({"tests/test_new.py": "# new\n"}, "change")
    doc = data(repo)
    assert doc["runs"] == [] and doc["nothing_to_run"] == ["project_tests"]
    assert "setting: project_tests" in plan(repo).stdout


def test_a_path_with_a_space_is_quoted_as_proof_quotes_it(repo):
    """REQ-016: brief #325 answer 4 (`{files}` quoting of a path with a space)."""
    start(repo, TWO_AREAS)
    repo.commit({"backend/tests/test_a b.py": "# a\n", "backend/tests/test_c.py": "#\n"}, "change")
    backend = runs(data(repo))["backend"]
    assert backend["command"] == "test -f ../be.txt && ls 'tests/test_a b.py' tests/test_c.py"
    assert backend["files"] == ["backend/tests/test_a b.py", "backend/tests/test_c.py"]


def test_without_cwd_the_files_are_relative_to_the_root(repo):
    """REQ-016: brief #325 answer 1 (the working folder defaults to the root)."""
    start(repo, "[proof]\n" + area("frontend", "frontend", "*.test.ts", "fe.txt"))
    repo.commit({"frontend/tests/new.test.ts": "// new\n"}, "change")
    frontend = runs(data(repo))["frontend"]
    assert frontend["cwd"] == "."
    assert frontend["command"] == "test -f fe.txt && ls frontend/tests/new.test.ts"


def range_of(repo) -> tuple[str, str]:
    """The range the script reads by default (the merge base with main), given explicitly: in
    CI the environment names a base ref of its own, which a repository in tmp_path lacks."""
    base = repo.git("merge-base", "main", "HEAD").strip()
    return proof.resolve_range(repo.root, base, "HEAD")


def recorded(repo, monkeypatch) -> list[tuple[str, str]]:
    """The (command, folder relative to its worktree) of every run proof makes, the base red and
    the head green, without running anything."""
    calls: list[tuple[str, str]] = []

    def fake(command, cwd, timeout, *args, **kwargs):
        tree = Path(cwd)
        top = next(p for p in (tree, *tree.parents) if p.name in ("base", "head"))
        rel = tree.relative_to(top).as_posix()
        calls.append((top.name, command, rel))
        return (1 if top.name == "base" else 0), "", 0

    monkeypatch.setattr(proof, "execute", fake)
    result = proof.prove(repo.root, *range_of(repo), "")
    assert result.outcome == "proven", result
    return calls


@pytest.mark.parametrize("table", [True, False])
def test_the_plan_shown_is_the_plan_proof_runs(repo, monkeypatch, table):
    """REQ-016: brief #325 answer 2 (one function builds both; the same commands, the same
    folders, for the same change)."""
    if table:
        start(repo, TWO_AREAS)
    else:
        start(repo, project_tests="python3 -m pytest -q")
    repo.commit(
        {
            "backend/tests/test_a b.py": "# a\n",
            "frontend/tests/new.test.ts": "// new\n",
            "tests/test_x.py": "# x\n",
        },
        "change",
    )
    shown = [(r["command"], r["cwd"]) for r in data(repo)["runs"]]
    calls = recorded(repo, monkeypatch)
    assert [(c, w) for kind, c, w in calls if kind == "base"] == shown
    assert [(c, w) for kind, c, w in calls if kind == "head"] == shown
    assert shown


def test_proof_and_the_plan_use_the_same_function():
    """REQ-016: brief #325 answer 2 (the plan is built in one place)."""
    import test_plan as script

    assert script.plan is proof.plan
    source = Path(proof.__file__).read_text(encoding="utf-8")
    assert "plan(root, base, head)" in source


def test_the_plan_is_read_only(repo):
    """REQ-016: brief #325 answer 1 (git and files only: no worktree, no change, nothing run)."""
    start(repo, "[proof]\n" + area("backend", "backend", "test_*.py", "be.txt").replace(
        "test -f be.txt && ls {files}", "touch RAN && ls {files}"))  # fmt: skip
    repo.commit({"backend/tests/test_new.py": "# new\n"}, "change")
    before = repo.git("status", "--porcelain", "--ignored"), repo.git("worktree", "list")
    assert plan(repo).returncode == 0
    assert (repo.git("status", "--porcelain", "--ignored"), repo.git("worktree", "list")) == before
    assert not (repo.root / "RAN").exists()


def test_a_cwd_missing_from_the_head_is_refused_as_proof_refuses_it(repo):
    """REQ-016: brief #325 answer 2 (the same refusal, naming the setting)."""
    extra = (
        '[proof]\nbackend = { dirs = ["backend/tests"], patterns = ["test_*.py"], '
        "cwd = \"nowhere\", command = 'ls {files}' }\n"
    )
    start(repo, extra)
    repo.commit({"backend/tests/test_new.py": "# new\n"}, "change")
    shown, ran = plan(repo), repo.run("proof.py")
    assert shown.returncode == ran.returncode == 2
    assert "setting: proof.backend.cwd" in shown.stdout
    assert shown.stdout.replace("test-plan", "proof") == ran.stdout
    assert "nowhere" not in shown.stdout


def test_base_and_head_can_be_given(repo):
    """REQ-016: brief #325 answer 1 (`--base REF --head REF`)."""
    start(repo, TWO_AREAS)
    repo.commit({"backend/tests/test_new.py": "# new\n"}, "one")
    first = repo.git("rev-parse", "HEAD").strip()
    repo.commit({"frontend/tests/new.test.ts": "// new\n"}, "two")
    doc = data(repo, "--base", first, "--head", "HEAD")
    assert list(runs(doc)) == ["frontend"] and doc["base"] == first
    assert data(repo, "--base", "main", "--head", first)["head"] == first


def test_usage_and_a_ref_that_does_not_resolve(repo):
    """REQ-016: brief #325 answer 1 (usage is exit 2; a bad ref names the path class, exit 3)."""
    start(repo, TWO_AREAS)
    repo.commit({"backend/tests/test_new.py": "# new\n"}, "change")
    proc = plan(repo, "--nope")
    assert proc.returncode == 2 and "usage: test_plan.py" in proc.stderr
    proc = plan(repo, "--base", "no-such-ref")
    assert proc.returncode == 3 and "path class: git ref" in proc.stdout
    assert "no-such-ref" not in proc.stdout
