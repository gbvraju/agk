"""Proof per test area: the `[proof]` table of agk.toml (brief #305, ADR-0172). No toolchain.

Every case builds a git repository in `tmp_path`. An area's fake command is plain shell: it is red
until the change file of that area exists, and it lists the files it is given (`ls {files}`), so a
path that is not relative to the area's working folder, or not quoted, makes it fail.
"""

from __future__ import annotations

import json

import pytest

BASE_TOML = 'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'


def area(name: str, folder: str, pattern: str, change: str, cwd: str | None = None) -> str:
    """One area: tests under `<folder>/tests`, red until `<change>` exists at the root."""
    where = f'cwd = "{cwd}", ' if cwd is not None else ""
    command = f"test -f {change} && cd {cwd or '.'} && ls {{files}}"
    return (
        f'{name} = {{ dirs = ["{folder}/tests"], patterns = ["{pattern}"], {where}'
        f"command = '{command}' }}\n"
    )


TWO_AREAS = (
    "[proof]\n"
    + area("backend", "backend", "test_*.py", "be.txt", "backend")
    + area("frontend", "frontend", "*.test.ts", "fe.txt", "frontend")
)


def start(repo, extra: str = "", project_tests: str | None = "exit 1", files=None) -> None:
    text = BASE_TOML
    if project_tests is not None:
        text += f"project_tests = '{project_tests}'\n"
    base = {
        "agk.toml": text + extra,
        "src/code.txt": "base\n",
        "backend/tests/test_old.py": "# old\n",
        "frontend/tests/old.test.ts": "// old\n",
    }
    repo.commit({**base, **(files or {})}, "base")
    repo.branch("feature")


def proof(repo, *args: str):
    return repo.run("proof.py", *args)


def data(proc) -> dict:
    return json.loads(proc.stdout)


def by_name(doc: dict) -> dict:
    return {a["name"]: a for a in doc["areas"]}


def test_ac1_one_area_runs_only_its_own_files_and_is_proven(repo):
    """REQ-016 AC1: brief #305 answers 1 to 4 (one area, red on the base, green on the head)."""
    start(repo, TWO_AREAS)
    repo.commit({"be.txt": "change\n", "backend/tests/test_new.py": "# new\n"}, "change")
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: proven", proc.stdout + proc.stderr
    assert proc.returncode == 0
    doc = data(proof(repo, "--json"))
    assert doc["outcome"] == "proven" and doc["reason"] is None
    assert doc["test_files"] == ["backend/tests/test_new.py"]
    areas = by_name(doc)
    assert areas["backend"]["files"] == ["backend/tests/test_new.py"]
    assert areas["backend"]["outcome"] == "proven" and areas["backend"]["reason"] is None
    assert isinstance(areas["backend"]["seconds"], int) and areas["backend"]["seconds"] >= 0
    assert areas["frontend"]["files"] == [] and areas["frontend"]["outcome"] is None
    assert [a["name"] for a in doc["areas"]] == ["backend", "frontend"]


def test_ac1_the_command_gets_only_the_pull_requests_files_relative_and_quoted(repo):
    """REQ-016 AC1: brief #305 answer 3 (relative to the working folder, shell-quoted)."""
    start(repo, TWO_AREAS)
    repo.commit(
        {"be.txt": "x\n", "backend/tests/test_a b.py": "# a\n", "backend/tests/test_c.py": "#\n"},
        "change",
    )
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: proven", proc.stdout + proc.stderr
    assert "tests/test_a b.py" in proc.stderr and "tests/test_c.py" in proc.stderr
    assert "test_old.py" not in proc.stderr and "backend/tests" not in proc.stderr


def test_ac1_two_areas_one_red_and_one_not_is_not_proven_and_names_the_area(repo):
    """REQ-016 AC1: brief #305 answer 2 (every area with files must be proven)."""
    start(repo, TWO_AREAS, files={"fe.txt": "already there\n"})
    repo.commit(
        {
            "be.txt": "change\n",
            "backend/tests/test_new.py": "# new\n",
            "frontend/tests/new.test.ts": "// new\n",
        },
        "change",
    )
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: not-proven (frontend: green-on-base)", proc.stdout
    assert proc.returncode == 1
    doc = data(proof(repo, "--json"))
    assert doc["outcome"] == "not-proven" and doc["reason"] == "green-on-base"
    areas = by_name(doc)
    assert areas["backend"]["outcome"] == "proven"
    assert areas["frontend"]["outcome"] == "not-proven"
    assert areas["frontend"]["reason"] == "green-on-base"
    assert areas["frontend"]["files"] == ["frontend/tests/new.test.ts"]
    assert doc["test_files"] == ["backend/tests/test_new.py", "frontend/tests/new.test.ts"]


def test_ac1_a_front_end_only_change_is_proven_not_unknown(repo):
    """REQ-016 AC1: brief #305 sentence (a front-end change is never `unknown (no-test-files)`)."""
    start(repo, TWO_AREAS)
    repo.commit({"fe.txt": "change\n", "frontend/tests/new.test.ts": "// new\n"}, "change")
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: proven", proc.stdout + proc.stderr
    assert by_name(data(proof(repo, "--json")))["backend"]["outcome"] is None


def test_ac1_a_red_head_in_one_area_is_not_proven_naming_it(repo):
    """REQ-016 AC1: brief #305 answer 2 (red-on-head)."""
    start(repo, TWO_AREAS)
    repo.commit({"frontend/tests/new.test.ts": "// new\n"}, "a test without its change")
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: not-proven (frontend: red-on-head)"
    assert data(proof(repo, "--json"))["reason"] == "red-on-head"


def test_ac1_two_areas_not_proven_are_both_named(repo):
    """REQ-016 AC1: brief #305 answer 2."""
    start(repo, TWO_AREAS, files={"be.txt": "there\n"})
    repo.commit(
        {"backend/tests/test_new.py": "# new\n", "frontend/tests/new.test.ts": "// new\n"},
        "change",
    )
    line = proof(repo).stdout.strip()
    assert line == "proof: not-proven (backend: green-on-base; frontend: red-on-head)"


def test_ac1_a_timeout_in_one_area_makes_the_result_unknown(repo):
    """REQ-016 AC1: brief #305 answer 2 (an area not proven makes the whole result unknown)."""
    extra = (
        "proof_timeout = 1\n[proof]\n"
        + area("backend", "backend", "test_*.py", "be.txt", "backend")
        + 'frontend = { dirs = ["frontend/tests"], patterns = ["*.test.ts"], '
        "command = 'sleep 30; ls {files}' }\n"
    )
    start(repo, extra)
    repo.commit(
        {
            "be.txt": "x\n",
            "backend/tests/test_new.py": "# new\n",
            "frontend/tests/new.test.ts": "// new\n",
        },
        "change",
    )
    proc = proof(repo)
    assert proc.stdout.strip().startswith("proof: unknown (frontend: timeout after ")
    assert proc.stdout.strip().endswith(" s, setting: proof_timeout)")
    assert proc.returncode == 4
    doc = data(proof(repo, "--json"))
    assert doc["outcome"] == "unknown" and doc["reason"] == "timeout"
    assert by_name(doc)["backend"]["outcome"] == "proven"


def test_ac1_no_files_in_any_area_is_unknown(repo):
    """REQ-016 AC1: brief #305 answer 5 (no files; a file outside every area is not a test file)."""
    start(repo, TWO_AREAS)
    repo.commit({"src/code.txt": "changed\n", "tests/test_top.py": "# outside the areas\n"}, "x")
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: unknown (no-test-files)"
    assert proc.returncode == 4
    doc = data(proof(repo, "--json"))
    assert doc["test_files"] == [] and all(a["outcome"] is None for a in doc["areas"])


def test_ac1_an_area_with_only_deletions_is_not_run(repo):
    """REQ-016 AC1: brief #305 answer 2 (a deletion is placed, but gives the area no files)."""
    start(repo, TWO_AREAS)
    repo.commit(
        {
            "be.txt": "x\n",
            "backend/tests/test_new.py": "# new\n",
            "frontend/tests/old.test.ts": None,
        },
        "change",
    )
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: proven", proc.stdout + proc.stderr
    assert by_name(data(proof(repo, "--json")))["frontend"]["outcome"] is None
    repo.commit({"backend/tests/test_new.py": None, "be.txt": None}, "undo")
    assert proof(repo).stdout.strip() == "proof: unknown (no-test-files)"


def test_ac1_areas_do_not_need_project_tests(repo):
    """REQ-016 AC1: brief #305 answer 1 (with areas, each area's command is the test command)."""
    start(repo, TWO_AREAS, project_tests=None)
    repo.commit({"be.txt": "x\n", "backend/tests/test_new.py": "# new\n"}, "change")
    assert proof(repo).stdout.strip() == "proof: proven"


def test_ac1_the_declaration_still_skips_with_areas(repo):
    """REQ-016 AC1: SPEC-0010 rule 18 is unchanged with areas."""
    start(repo, TWO_AREAS)
    repo.commit({"backend/tests/test_new.py": "# new\n"}, "add a test")
    proc = proof(repo, "--body", "-")
    assert "not-proven" in proc.stdout
    proc = repo.run("proof.py", "--body", "-", stdin="Behaviour: unchanged\n")
    assert proc.stdout.strip() == "proof: skipped"


def refusal(repo, extra: str):
    start(repo, extra)
    repo.commit({"be.txt": "x\n", "backend/tests/test_new.py": "# new\n"}, "change")
    return proof(repo)


def test_ac1_a_template_without_files_is_refused_naming_the_setting(repo):
    """REQ-016 AC1: brief #305 answer 3 (refused, naming the setting and never its value)."""
    extra = (
        '[proof]\nbackend = { dirs = ["backend/tests"], patterns = ["test_*.py"], '
        "command = 'cd backend && run-the-suite' }\n"
    )
    proc = refusal(repo, extra)
    assert proc.returncode == 2
    assert proc.stdout.strip() == (
        "FAIL proof: the command of a proof area has no {files} (setting: proof.backend.command)"
    )
    assert "run-the-suite" not in proc.stdout + proc.stderr


MALFORMED = {
    '[proof]\nbackend = { patterns = ["t*"], command = "x {files}" }\n': "proof.backend.dirs",
    '[proof]\nbackend = { dirs = [], patterns = ["t*"], command = "x {files}" }\n': (
        "proof.backend.dirs"
    ),
    '[proof]\nbackend = { dirs = ["b"], command = "x {files}" }\n': "proof.backend.patterns",
    '[proof]\nbackend = { dirs = ["b"], patterns = [1], command = "x {files}" }\n': (
        "proof.backend.patterns"
    ),
    '[proof]\nbackend = { dirs = ["b"], patterns = ["t*"] }\n': "proof.backend.command",
    '[proof]\nbackend = { dirs = ["b"], patterns = ["t*"], command = "x {files}", cwd = 3 }\n': (
        "proof.backend.cwd"
    ),
    '[proof]\nbackend = { dirs = ["b"], patterns = ["t*"], command = "x {files}", other = 1 }\n': (
        "proof.backend"
    ),
    "[proof]\nbackend = 1\n": "proof.backend",
    "proof = 1\n": "proof",
    "[proof]\n": "proof",
}


@pytest.mark.parametrize("extra", list(MALFORMED))
def test_ac1_a_malformed_area_is_refused_naming_the_setting(repo, extra):
    """REQ-016 AC1: brief #305 answer 1 (dirs, patterns and command are required)."""
    proc = refusal(repo, extra)
    assert proc.returncode == 2, (proc.stdout, proc.stderr)
    assert proc.stdout.strip().startswith("FAIL proof: ")
    assert proc.stdout.strip().endswith(f"(setting: {MALFORMED[extra]})"), proc.stdout


def test_ac1_without_the_table_proof_works_exactly_as_before(repo):
    """REQ-016 AC1: brief #305 answer 1 (project_tests, test_dirs and test_patterns; no areas)."""
    repo.commit(
        {
            "agk.toml": BASE_TOML + "project_tests = 'test -f feature.txt'\n",
            "tests/test_old.py": "# old\n",
        },
        "base",
    )
    repo.branch("feature")
    repo.commit({"feature.txt": "x\n", "tests/test_new.py": "# new\n"}, "change")
    assert proof(repo).stdout.strip() == "proof: proven"
    doc = data(proof(repo, "--json"))
    assert set(doc) == {"outcome", "reason", "base", "head", "test_files"}
    assert doc["test_files"] == ["tests/test_new.py"]
