"""Red-then-green: scripts/agk/proof.py (SPEC-0010 rules 7 to 15 and 19). No language toolchain.

Every case builds a git repository in `tmp_path` and uses a fake `project_tests` command that is
plain shell (`test -f feature.txt`): it exits 1 unless the named file exists.
"""

from __future__ import annotations

import json


def toml(command: str | None, extra: str = "") -> str:
    text = 'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
    if command is not None:
        text += f"project_tests = '{command}'\n"
    return text + extra


def start(repo, command: str | None = "test -f feature.txt", extra: str = "", files=None) -> None:
    """The base commit on main, then a branch for the pull request."""
    base = {
        "agk.toml": toml(command, extra),
        "src/code.txt": "base\n",
        "tests/test_old.py": "# an old test\n",
        "other/test_elsewhere.py": "# outside the test directories\n",
    }
    repo.commit({**base, **(files or {})}, "base")
    repo.branch("feature")


def proof(repo, *args: str, **env: str):
    return repo.run("proof.py", *args, **env)


def data(proc) -> dict:
    return json.loads(proc.stdout)


def line(proc) -> str:
    assert proc.stdout.count("\n") == 1, proc.stdout
    return proc.stdout.strip()


def test_ac1_a_seeded_test_that_passes_on_the_base_is_not_proven(repo):
    """REQ-016 AC1: rule 12 (the new test passes without the change: green-on-base)."""
    start(repo, files={"feature.txt": "already there\n"})
    repo.commit({"tests/test_new.py": "# new\n"}, "add a test")
    proc = proof(repo)
    assert line(proc) == "proof: not-proven (green-on-base)"
    assert proc.returncode == 1


def test_ac1_a_real_change_with_its_test_is_proven(repo):
    """REQ-016 AC1: rule 12 (red on the base with the tests, green on the head)."""
    start(repo)
    repo.commit({"feature.txt": "the change\n", "tests/test_new.py": "# new\n"}, "change and test")
    proc = proof(repo)
    assert line(proc) == "proof: proven"
    assert proc.returncode == 0


def test_ac1_a_build_failure_on_the_base_counts_as_red(repo):
    """REQ-016 AC1: rule 11 (a command that exits 2 until the change exists)."""
    start(repo, "test -f feature.txt || exit 2")
    repo.commit({"feature.txt": "x\n", "tests/test_new.py": "# new\n"}, "change and test")
    assert proof(repo).stdout.strip() == "proof: proven"


def test_ac1_the_declaration_skips_the_check(repo):
    """REQ-016 AC1: rules 12 and 18."""
    start(repo, files={"feature.txt": "x\n"})
    repo.commit({"tests/test_new.py": "# new\n"}, "add a test")
    body = "Advances: x\n\nBehaviour: unchanged\n"
    proc = proof(repo, "--body", "-", stdin=body)
    assert line(proc) == "proof: skipped" and proc.returncode == 0
    inside_a_fence = "```\nBehaviour: unchanged\n```\n"
    assert "skipped" not in proof(repo, "--body", "-", stdin=inside_a_fence).stdout
    body_file = repo.root / "body.md"
    body_file.write_text(body, encoding="utf-8")
    assert "skipped" in proof(repo, "--body", str(body_file)).stdout


def test_ac3_without_project_tests_the_outcome_is_unknown_never_ok(repo):
    """REQ-016 AC3: rule 12 (no-project-tests), exit 4."""
    start(repo, None)
    repo.commit({"tests/test_new.py": "# new\n"}, "add a test")
    proc = proof(repo)
    assert line(proc) == "proof: unknown (no-project-tests)" and proc.returncode == 4
    empty = repo.root / "agk.toml"
    empty.write_text(toml("   "), encoding="utf-8")
    assert "no-project-tests" in proof(repo).stdout


def test_ac1_a_change_with_no_test_file_is_unknown(repo):
    """REQ-016 AC1: rule 12 (no-test-files); a file outside the test directories is ignored."""
    start(repo)
    repo.commit({"feature.txt": "x\n", "other/test_elsewhere.py": "# changed\n"}, "no test change")
    proc = proof(repo)
    assert line(proc) == "proof: unknown (no-test-files)" and proc.returncode == 4
    assert data(proof(repo, "--json"))["test_files"] == []


def test_ac1_a_helper_outside_the_patterns_is_not_a_test_file(repo):
    """REQ-016 AC1: rule 9 (a changed fixture or helper is part of the change, not of the tests)."""
    start(repo)
    repo.commit({"tests/conftest.py": "# helper\n", "tests/data.json": "{}\n"}, "helpers only")
    assert "no-test-files" in proof(repo).stdout


def test_ac1_only_deleted_tests_are_unknown(repo):
    """REQ-016 AC1: rule 12."""
    start(repo)
    repo.commit({"tests/test_old.py": None}, "delete the test")
    proc = proof(repo)
    assert "no-test-files" in proc.stdout and proc.returncode == 4


def test_ac1_a_deleted_test_is_removed_from_the_base_and_a_rename_is_both(repo):
    """REQ-016 AC1: rule 10 (the base keeps no stale file). `test ! -e` passes only if removed."""
    start(
        repo,
        "test ! -e tests/test_old.py && test ! -e tests/test_a.py",
        files={"tests/test_a.py": "# a\n"},
    )
    repo.git("mv", "tests/test_a.py", "tests/test_b.py")
    repo.commit({"tests/test_old.py": None}, "rename one test, delete another")
    proc = proof(repo, "--json")
    result = data(proc)
    assert result["test_files"] == ["tests/test_a.py", "tests/test_b.py", "tests/test_old.py"]
    # the stale files are gone from the base, so the command passes there: the tests are green
    assert (result["outcome"], result["reason"]) == ("not-proven", "green-on-base")


def test_ac1_a_red_head_is_not_proven(repo):
    """REQ-016 AC1: rule 12 (red-on-head)."""
    start(repo)
    repo.commit({"tests/test_new.py": "# new\n"}, "a test, no change")
    proc = proof(repo)
    assert line(proc) == "proof: not-proven (red-on-head)" and proc.returncode == 1


def test_ac1_a_dirty_work_tree_cannot_change_the_answer(repo):
    """REQ-016 AC1: rule 11 (the head is its own worktree, not ROOT)."""
    start(repo)
    repo.commit({"tests/test_new.py": "# new\n"}, "a test, no change")
    repo.write("feature.txt", "uncommitted\n")
    assert "red-on-head" in proof(repo).stdout
    assert (repo.root / "feature.txt").read_text() == "uncommitted\n"


def test_ac1_a_timeout_is_unknown_and_kills_the_run(repo):
    """REQ-016 AC1: rule 15 (`proof_timeout = 1`; the process group is killed)."""
    start(repo, "sleep 20", "proof_timeout = 1\n")
    repo.commit({"tests/test_new.py": "# new\n"}, "add a test")
    proc = proof(repo)
    assert line(proc) == "proof: unknown (timeout)" and proc.returncode == 4


def test_ac1_an_invalid_timeout_is_a_refusal_naming_the_setting(repo):
    """REQ-016 AC1: rule 15."""
    for value in ("0", '"soon"', "-5", "1.5", "true"):
        repo.commit({"agk.toml": toml("true", f"proof_timeout = {value}\n")}, f"timeout {value}")
        proc = proof(repo, "--base", "HEAD")
        assert proc.returncode == 2 and "proof_timeout" in proc.stdout, (value, proc.stdout)
        assert value not in proc.stdout.replace("proof_timeout", "")


def test_ac1_the_work_tree_worktrees_and_temporary_files_are_left_clean(repo, tmp_path_factory):
    """REQ-016 AC1: rule 8 (two worktrees added and removed, also after a failure)."""
    start(repo)
    repo.commit({"feature.txt": "x\n", "tests/test_new.py": "# new\n"}, "change and test")
    before = sorted(p.name for p in repo.root.iterdir())
    scratch = tmp_path_factory.mktemp("scratch")
    proc = proof(repo, TMPDIR=str(scratch))
    assert proc.returncode == 0
    assert sorted(p.name for p in repo.root.iterdir()) == before
    assert repo.git("status", "--porcelain") == ""
    assert len(repo.git("worktree", "list").splitlines()) == 1
    assert list(scratch.iterdir()) == []
    failing = proof(repo, "--base", "no-such-ref", TMPDIR=str(scratch))
    assert failing.returncode == 3 and "path class" in failing.stdout
    assert len(repo.git("worktree", "list").splitlines()) == 1 and list(scratch.iterdir()) == []


def test_ac1_the_last_forty_lines_of_each_run_are_shown_and_never_stored(repo):
    """REQ-016 AC1: rule 11."""
    start(repo, "for i in $(seq 1 60); do echo out-$i; done; test -f feature.txt")
    repo.commit({"feature.txt": "x\n", "tests/test_new.py": "# new\n"}, "change and test")
    proc = proof(repo)
    assert "out-60" in proc.stderr and "out-21" in proc.stderr and "out-20\n" not in proc.stderr
    assert proc.stderr.count("out-60") == 2  # each run shows its own last lines
    assert proc.stdout.strip() == "proof: proven"
    assert not list(repo.root.glob("**/*.log"))


def test_ac1_the_command_runs_with_the_callers_environment(repo):
    """REQ-016 AC1: rule 11 (same environment, no extra variables)."""
    start(repo, 'test "$PROOF_PROBE" = yes && test -f feature.txt')
    repo.commit({"feature.txt": "x\n", "tests/test_new.py": "# new\n"}, "change and test")
    assert proof(repo, PROOF_PROBE="yes").returncode == 0
    assert proof(repo).returncode == 1  # not set: run 2 fails (and run 1 too: red-on-head)


def test_ac1_json_has_the_outcome_reason_refs_and_the_sorted_test_files(repo):
    """REQ-016 AC1: rule 13."""
    start(repo, files={"feature.txt": "x\n"})
    repo.commit({"tests/test_z.py": "# z\n", "tests/test_b.py": "# b\n"}, "add tests")
    result = data(proof(repo, "--json"))
    assert set(result) == {"outcome", "reason", "base", "head", "test_files"}
    assert result["test_files"] == ["tests/test_b.py", "tests/test_z.py"]
    assert result["base"] == repo.git("rev-parse", "main").strip()
    assert result["head"] == repo.git("rev-parse", "HEAD").strip()
    assert (result["outcome"], result["reason"]) == ("not-proven", "green-on-base")


def test_ac1_the_base_defaults_to_the_merge_base_and_agk_base_overrides_it(repo):
    """REQ-016 AC1: rule 7."""
    start(repo)
    repo.commit({"feature.txt": "x\n", "tests/test_new.py": "# new\n"}, "change and test")
    first = repo.git("rev-parse", "HEAD").strip()
    repo.commit({"src/code.txt": "more\n"}, "a later change")
    assert data(proof(repo, "--json"))["base"] == repo.git("rev-parse", "main").strip()
    explicit = proof(repo, "--base", first, "--head", "HEAD", "--json")
    assert data(explicit)["base"] == first
    via_env = proof(repo, "--json", AGK_BASE=first)
    assert data(via_env)["base"] == first


def test_ac1_usage_errors_exit_two(repo):
    """REQ-016 AC1: rule 13."""
    start(repo)
    for args in (["--nope"], ["--base"], ["one", "two"]):
        proc = proof(repo, *args)
        assert proc.returncode == 2 and "usage: proof.py" in proc.stderr


def test_ac1_a_directory_that_is_not_a_work_tree_is_an_io_error(repo, tmp_path):
    """REQ-016 AC1: rule 13 (exit 3)."""
    plain = tmp_path / "plain"
    plain.mkdir()
    assert proof(repo, str(plain)).returncode == 3


def test_ac1_the_script_reads_no_language():
    """REQ-016 AC1: rule 24 (nothing in proof.py names a language or a test runner)."""
    from pathlib import Path

    source = (Path(__file__).resolve().parents[2] / "scripts" / "agk" / "proof.py").read_text()
    for word in ("pytest", "python3", "go test", "npm", "cargo", "mvn", '.py"', '.go"'):
        assert word not in source.replace("proof.py", ""), word
