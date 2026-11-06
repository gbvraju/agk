"""A requirement's status follows its evidence: `req_status.py report` and `apply` (brief #668,
ADR-0321, proposed spec amendments 133 to SPEC-0010).

Every case builds a git repository in `tmp_path` with an invented requirements file and a fake
test runner that needs only `python3`: a test file passes unless it holds the word `BROKEN`.
Test data writes `@` for `REQ-`, so that no line of this file is itself a marker.
REQ-003 AC4
"""

from __future__ import annotations

import json

CRITERIA = "AC1 given a, when b, then c; AC2 given d, when e, then f"
RUNNER = """import sys, time
from pathlib import Path
Path("runs.log").open("a").write(" ".join(sys.argv[1:]) + "\\n")
for name in sys.argv[1:]:
    text = Path(name).read_text()
    if "SLOW" in text:
        time.sleep(5)
    if "BROKEN" in text:
        sys.exit(1)
"""
AREA = (
    '[proof.t]\ndirs = ["tests"]\npatterns = ["test_*.py"]\n'
    'command = "python3 run.py {files}"\ncwd = "."\n'
)


def requirement(rid: str, status: str, acceptance: str = CRITERIA) -> str:
    return f"### {rid} — Thing\n\n- Acceptance: {acceptance}\n- Status: {status}\n\n"


def real(text: str) -> str:
    return text.replace("@", "REQ-")


def shown(proc) -> str:
    return (proc.stdout + proc.stderr).replace("REQ-", "@")


def setup(repo, requirements: str, tests: dict[str, str], area: bool = True, extra: str = ""):
    toml = 'default_branch = "main"\ntest_dirs = ["tests"]\n' + extra + (AREA if area else "")
    files = {
        "agk.toml": toml,
        "run.py": RUNNER,
        ".gitignore": "runs.log\n",
        "docs/requirements.md": "# Requirements\n\n" + real(requirements),
    }
    files.update({path: real(text) for path, text in tests.items()})
    repo.commit(files)


def report(repo, *args: str):
    return repo.run("req_status.py", "report", *args)


def runs(repo) -> list[str]:
    log = repo.root / "runs.log"
    return log.read_text().splitlines() if log.is_file() else []


def test_ac4_a_planned_requirement_whose_proof_passes_is_reported_to_done(repo):
    """REQ-003 AC4: answer 1, the `planned -> done` line; nothing is edited by `report`."""
    setup(
        repo,
        requirement("@010", "planned"),
        {"tests/test_a.py": "# @010 AC1\n", "tests/test_b.py": "# @010 AC2\n"},
    )
    before = (repo.root / "docs/requirements.md").read_text()
    proc = report(repo)
    assert proc.returncode == 0, shown(proc)
    assert "@010 planned -> done (proof: 2 tests pass)" in shown(proc)
    assert (repo.root / "docs/requirements.md").read_text() == before
    assert "given a" not in shown(proc)  # a criterion's text is never printed


def test_ac4_an_in_progress_requirement_whose_proof_passes_is_reported_to_done(repo):
    """REQ-003 AC4: the status that disagrees is named as it is."""
    setup(repo, requirement("@013", "in-progress"), {"tests/test_a.py": "# @013 AC1\n# @013 AC2\n"})
    proc = report(repo)
    assert proc.returncode == 0, shown(proc)
    assert "@013 in-progress -> done (proof: 1 tests pass)" in shown(proc)


def test_ac4_a_done_requirement_whose_proof_fails_is_flagged_and_exits_1(repo):
    """REQ-003 AC4: answer 1, `done but proof fails (<test>)` and exit 1."""
    setup(
        repo,
        requirement("@011", "done"),
        {"tests/test_a.py": "# @011 AC1\n", "tests/test_b.py": "# @011 AC2\nBROKEN\n"},
    )
    proc = report(repo)
    assert proc.returncode == 1, shown(proc)
    assert "@011 done but proof fails (tests/test_b.py)" in shown(proc)


def test_ac4_a_requirement_with_an_unmarked_criterion_has_no_proof_mapped(repo):
    """REQ-003 AC4: answer 2; a criterion with no marker means no proof, and nothing runs."""
    setup(
        repo,
        requirement("@012", "planned") + requirement("@014", "planned", "the old free text"),
        {"tests/test_a.py": "# @012 AC1\n# @014\n"},
    )
    proc = report(repo)
    assert proc.returncode == 0, shown(proc)
    assert "@012: no proof mapped" in shown(proc)
    assert "@014: no proof mapped" in shown(proc)
    assert "-> done" not in shown(proc)
    assert runs(repo) == []


def test_ac4_without_a_proof_table_or_area_no_proof_is_mapped(repo):
    """REQ-003 AC4: a test file no `[proof]` area runs cannot be proof on its own."""
    setup(repo, requirement("@010", "planned"), {"tests/test_a.py": "# @010 AC1\n# @010 AC2\n"}, area=False)
    proc = report(repo)
    assert proc.returncode == 0, shown(proc)
    assert "@010: no proof mapped" in shown(proc)
    other = AREA.replace('dirs = ["tests"]', 'dirs = ["tests/unit"]')
    setup(repo, requirement("@010", "planned"), {"tests/test_a.py": "# @010 AC1\n# @010 AC2\n"}, False, other)
    proc = report(repo)
    assert "@010: no proof mapped" in shown(proc)
    assert runs(repo) == []


def test_ac4_a_status_that_agrees_with_its_proof_prints_no_line_of_its_own(repo):
    """REQ-003 AC4: done and passing, planned and failing, retired: only the summary counts them."""
    setup(
        repo,
        requirement("@020", "done")
        + requirement("@021", "planned")
        + requirement("@022", "retired"),
        {
            "tests/test_a.py": "# @020 AC1\n# @020 AC2\n",
            "tests/test_b.py": "# @021 AC1\n# @021 AC2\nBROKEN\n",
        },
    )
    proc = report(repo)
    assert proc.returncode == 0, shown(proc)
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("REQ-")]
    assert lines == []
    assert (
        "req-status: 0 to done, 0 proof fails, 0 unknown, 0 no proof mapped, 2 agree "
        "(3 requirements)" in proc.stdout
    )


def test_ac4_each_test_file_runs_once_however_many_requirements_it_proves(repo):
    """REQ-003 AC4: one run per test file, through the area's own command."""
    setup(
        repo,
        requirement("@010", "planned") + requirement("@011", "planned"),
        {"tests/test_a.py": "# @010 @011 AC1\n# @010 @011 AC2\n"},
    )
    proc = report(repo)
    assert proc.returncode == 0, shown(proc)
    assert runs(repo) == ["tests/test_a.py"]


def test_ac4_a_timeout_is_unknown_never_a_pass(repo):
    """REQ-003 AC4: SPEC-0010 rule 15; a slow file is no evidence either way (exit 4)."""
    setup(
        repo,
        requirement("@010", "planned"),
        {"tests/test_a.py": "# @010 AC1\n# @010 AC2\nSLOW\n"},
        extra="proof_timeout = 1\n",
    )
    proc = report(repo)
    assert proc.returncode == 4, shown(proc)
    assert "@010 proof unknown (tests/test_a.py timed out)" in shown(proc)
    assert "-> done" not in shown(proc)


def test_ac4_json_lists_each_requirement_with_its_outcome(repo):
    """REQ-003 AC4: `--json` is one object for the conductor to read."""
    setup(
        repo,
        requirement("@010", "planned") + requirement("@011", "done") + requirement("@012", "planned"),
        {"tests/test_a.py": "# @010 AC1\n# @010 AC2\n", "tests/test_b.py": "# @011 AC1\n# @011 AC2\nBROKEN\n"},
    )
    proc = report(repo, "--json")
    assert proc.returncode == 1, shown(proc)
    data = json.loads(proc.stdout)
    found = {r["id"].replace("REQ-", "@"): r for r in data["requirements"]}
    assert found["@010"]["outcome"] == "to-done"
    assert found["@010"]["files"] == ["tests/test_a.py"]
    assert found["@011"]["outcome"] == "proof-fails"
    assert found["@011"]["failing"] == ["tests/test_b.py"]
    assert found["@012"]["outcome"] == "no-proof"


def test_ac4_req_limits_the_run_to_the_named_requirements(repo):
    """REQ-003 AC4: `--req REQ-nnn` evaluates only that requirement."""
    setup(
        repo,
        requirement("@010", "planned") + requirement("@011", "planned"),
        {"tests/test_a.py": "# @010 AC1\n# @010 AC2\n", "tests/test_b.py": "# @011 AC1\n# @011 AC2\n"},
    )
    proc = report(repo, "--req", real("@011"))
    assert proc.returncode == 0, shown(proc)
    assert "@011 planned -> done" in shown(proc)
    assert "@010" not in shown(proc)
    assert runs(repo) == ["tests/test_b.py"]


def test_ac4_apply_edits_only_the_status_lines_that_disagree(repo):
    """REQ-003 AC4: answer 1; `apply` changes `- Status:` lines to `done` and nothing else."""
    setup(
        repo,
        requirement("@010", "planned")
        + requirement("@011", "done")
        + requirement("@012", "planned")
        + requirement("@013", "in-progress"),
        {
            "tests/test_a.py": "# @010 AC1\n# @010 AC2\n",
            "tests/test_b.py": "# @011 AC1\n# @011 AC2\nBROKEN\n",
            "tests/test_c.py": "# @013 AC1\n# @013 AC2\n",
        },
    )
    proc = repo.run("req_status.py", "apply")
    assert proc.returncode == 1, shown(proc)  # the flagged done requirement still exits 1
    assert "edited @010: planned -> done" in shown(proc)
    assert "edited @013: in-progress -> done" in shown(proc)
    diff = repo.git("diff", "-U0", "--", "docs/requirements.md").splitlines()
    changed = [ln for ln in diff if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
    assert sorted(changed) == sorted(
        ["-- Status: planned", "+- Status: done", "-- Status: in-progress", "+- Status: done"]
    )
    text = (repo.root / "docs/requirements.md").read_text()
    assert real("### @011 — Thing\n\n- Acceptance: " + CRITERIA + "\n- Status: done") in text
    assert real("### @012 — Thing\n\n- Acceptance: " + CRITERIA + "\n- Status: planned") in text


def test_ac4_apply_refuses_a_requirements_file_already_changed_in_the_work_tree(repo):
    """REQ-003 AC4: the edit is the one change; the refusal names the path class."""
    setup(repo, requirement("@010", "planned"), {"tests/test_a.py": "# @010 AC1\n# @010 AC2\n"})
    path = repo.root / "docs/requirements.md"
    path.write_text(path.read_text() + "\n")
    proc = repo.run("req_status.py", "apply")
    assert proc.returncode == 2, shown(proc)
    assert "path class: docs/requirements.md" in shown(proc)
    assert runs(repo) == []


def test_ac4_usage_errors_exit_2(repo):
    """REQ-003 AC4: no subcommand, an unknown one, or `--req` without a value."""
    setup(repo, requirement("@010", "planned"), {"tests/test_a.py": "# @010 AC1\n# @010 AC2\n"})
    assert repo.run("req_status.py").returncode == 2
    assert repo.run("req_status.py", "promote").returncode == 2
    assert report(repo, "--req").returncode == 2
