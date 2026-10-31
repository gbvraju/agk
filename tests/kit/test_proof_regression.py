"""Proof also runs the selected regression tests on the head (brief #442, ADR-0238). No toolchain.

Off by default: only `[testing] proof_regression = true` turns the third run on, and the spec change
that allows it is a proposal until a person approves it. Every case builds a git repository in
`tmp_path`. The one `[proof]` area runs each file it is given as a shell script, so a test file's
text is its own check: the pull request's test is red until `src/be.txt` exists, and the old
neighbour `tests/test_old.py` is red once `src/broken.txt` exists.
"""

from __future__ import annotations

import json
from pathlib import Path

import impact
import pytest
from common import CheckError

BASE_TOML = 'default_branch = "main"\ntest_dirs = ["tests"]\ntest_patterns = ["test_*.py"]\n'
AREA = (
    '[proof]\nunit = { dirs = ["tests"], patterns = ["test_*.py"], '
    "command = 'echo AT=$(pwd); for f in {files}; do sh \"$f\" || exit 1; done' }\n"
)
MAP = '[[testing.map]]\ncode = "src/**"\ntests = ["tests/test_old.py"]\n'


def table_toml(setting: str | None = "true", profile: str = "balanced", extra: str = "") -> str:
    lines = f'[testing]\nprofile = "{profile}"\n{extra}'
    if setting is not None:
        lines += f"proof_regression = {setting}\n"
    return lines + MAP


def start(repo, toml: str, old: str = "test ! -f src/broken.txt\n", patterns=None, files=None):
    head = BASE_TOML
    if patterns is not None:
        head = head.replace('["test_*.py"]', patterns)
    repo.commit(
        {
            "agk.toml": head + "project_tests = 'exit 1'\n" + toml,
            "src/code.txt": "base\n",
            "tests/test_old.py": old,
            **(files or {}),
        },
        "base",
    )
    repo.branch("feature")


def change(repo, broken: bool = False) -> None:
    files = {"src/be.txt": "change\n", "tests/test_new.py": "test -f src/be.txt\n"}
    if broken:
        files["src/broken.txt"] = "a regression\n"
    repo.commit(files, "change")


def proof(repo, *args: str):
    return repo.run("proof.py", *args)


def data(repo) -> dict:
    return json.loads(proof(repo, "--json").stdout)


def test_ac1_a_green_regression_run_keeps_the_outcome_proven(repo):
    """REQ-016 AC1: brief #442 answers 1 and 3 (regression green: proven, the run listed)."""
    start(repo, AREA + table_toml())
    change(repo)
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: proven", proc.stdout + proc.stderr
    assert proc.returncode == 0
    doc = data(repo)
    assert doc["outcome"] == "proven" and doc["reason"] is None
    reg = doc["regression"]
    assert reg["reason"] is None and reg["not_run"] == []
    [run] = reg["runs"]
    assert run["name"] == "unit" and run["files"] == ["tests/test_old.py"]
    assert run["outcome"] == "passed"
    assert isinstance(run["seconds"], int) and run["seconds"] >= 0


def test_ac1_a_red_regression_run_makes_the_outcome_not_proven_naming_the_area(repo):
    """REQ-016 AC1: brief #442 answer 1 (regression red: `not-proven (regression)`)."""
    start(repo, AREA + table_toml())
    change(repo, broken=True)
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: not-proven (regression: unit)", proc.stdout + proc.stderr
    assert proc.returncode == 1
    doc = data(repo)
    assert doc["outcome"] == "not-proven" and doc["reason"] == "regression"
    assert doc["regression"]["runs"][0]["outcome"] == "failed"
    assert doc["areas"][0]["outcome"] == "proven"  # the pull request's own tests stay proven


def test_ac1_the_third_run_is_on_the_head_only(repo):
    """REQ-016 AC1: brief #442 answer 1 (never on the base) and Q-442-1 (only the selection)."""
    start(repo, AREA + table_toml())
    change(repo)
    proc = proof(repo)
    places = [ln.split("AT=", 1)[1] for ln in proc.stderr.splitlines() if ln.startswith("AT=")]
    assert len(places) == 3, proc.stderr
    assert places[0].endswith("/base") and places[1].endswith("/head")
    assert places[2].endswith("/head")
    assert "run 3 (unit): regression tests on the head" in proc.stderr
    third = proc.stderr.split("run 3 (unit)", 1)[1]
    assert "test_new.py" not in third


def test_ac1_a_full_selection_runs_nothing_extra(repo):
    """REQ-016 AC1: brief #442 answer 1 (`full`: governance runs the full suite)."""
    start(repo, AREA + table_toml(extra='always_full = ["src/**"]\n'), old="exit 1\n")
    change(repo)
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: proven", proc.stdout + proc.stderr
    assert "run 3" not in proc.stderr
    reg = data(repo)["regression"]
    assert reg["runs"] == []
    assert reg["reason"].startswith("full (always_full src/** matches ")
    assert reg["reason"].endswith("): governance runs the full suite")


def test_ac1_nothing_selected_runs_nothing_extra(repo):
    """REQ-016 AC1: brief #442 answer 1 (an empty selection has no third run)."""
    start(repo, AREA + table_toml(profile="fast").replace('code = "src/**"', 'code = "lib/**"'))
    change(repo)
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: proven", proc.stdout + proc.stderr
    reg = data(repo)["regression"]
    assert reg["runs"] == [] and reg["reason"] == "nothing selected"


@pytest.mark.parametrize("setting", [None, "false"])
def test_ac1_with_the_key_off_proof_is_exactly_as_today(repo, setting):
    """REQ-016 AC1: brief #442 answer 2 (false or absent: no third run, no new output)."""
    start(repo, AREA + table_toml(setting))
    change(repo, broken=True)
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: proven", proc.stdout + proc.stderr
    assert "run 3" not in proc.stderr
    assert "regression" not in data(repo)


def test_ac1_without_a_testing_table_proof_is_exactly_as_today(repo):
    """REQ-016 AC1: brief #442 answer 2 (no table: off)."""
    start(repo, AREA)
    change(repo, broken=True)
    assert proof(repo).stdout.strip() == "proof: proven"
    assert "regression" not in data(repo)


def test_ac1_without_a_proof_table_the_head_run_already_ran_every_test(repo):
    """REQ-016 AC1: Q-442-2 (without `[proof]`, run 2 is `project_tests`, the whole suite)."""
    repo.commit(
        {
            "agk.toml": BASE_TOML + "project_tests = 'test -f src/be.txt'\n" + table_toml(),
            "src/code.txt": "base\n",
            "tests/test_old.py": "#\n",
        },
        "base",
    )
    repo.branch("feature")
    change(repo)
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: proven", proc.stdout + proc.stderr
    assert "run 3" not in proc.stderr
    reg = data(repo)["regression"]
    assert reg["runs"] == []
    assert reg["reason"] == "no [proof] table: project_tests ran every test on the head"


def test_ac1_the_third_run_waits_for_the_pull_requests_own_tests_to_be_proven(repo):
    """REQ-016 AC1: Q-442-3 (a not-proven own run is not changed and no third run is made)."""
    start(repo, AREA + table_toml())
    repo.commit({"src/broken.txt": "x\n", "tests/test_new.py": "exit 0\n"}, "change")
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: not-proven (unit: green-on-base)", proc.stdout
    assert "run 3" not in proc.stderr
    reg = data(repo)["regression"]
    assert reg["runs"] == []
    assert reg["reason"] == "the pull request's own tests are not proven"


def test_ac1_a_selected_file_in_no_proof_area_is_listed_as_not_run(repo):
    """REQ-016 AC1: Q-442-4 (no area command can take it, so it is listed, never run)."""
    toml = AREA + table_toml().replace(
        'tests = ["tests/test_old.py"]', 'tests = ["tests/test_old.py", "tests/x_e2e.py"]'
    )
    start(repo, toml, patterns='["test_*.py", "*_e2e.py"]', files={"tests/x_e2e.py": "exit 1\n"})
    change(repo)
    proc = proof(repo)
    assert proc.stdout.strip() == "proof: proven", proc.stdout + proc.stderr
    reg = data(repo)["regression"]
    assert [r["files"] for r in reg["runs"]] == [["tests/test_old.py"]]
    assert reg["not_run"] == ["tests/x_e2e.py"]


def test_ac1_proof_timeout_applies_to_the_third_run_separately(repo):
    """REQ-016 AC1: brief #442 answer 3 (a slow regression run is unknown, never proven)."""
    start(repo, "proof_timeout = 1\n" + AREA + table_toml(), old="sleep 5\n")
    change(repo)
    proc = proof(repo)
    out = proc.stdout.strip()
    assert out.startswith("proof: unknown (regression: unit: timeout after "), out + proc.stderr
    assert out.endswith(" s, setting: proof_timeout)")
    assert proc.returncode == 4
    doc = data(repo)
    assert doc["reason"] == "timeout"
    assert doc["regression"]["runs"][0]["outcome"] == "timeout"


def test_ac1_the_manifest_lists_the_regression_run(repo, tmp_path):
    """REQ-016 AC1: brief #442 answer 3 (the run, its files and seconds, also in the manifest)."""
    start(repo, AREA + table_toml())
    change(repo)
    target = tmp_path / "manifest.md"
    assert proof(repo, "--manifest", str(target)).returncode == 0
    text = target.read_text(encoding="utf-8")
    assert "#### regression: unit" in text
    assert "- files: 1\n  - `tests/test_old.py`" in text
    part = text.split("#### regression: unit", 1)[1]
    assert "- seconds: head " in part and "base" not in part.split("###", 1)[0]


def test_ac1_the_manifest_says_why_no_regression_ran(repo, tmp_path):
    """REQ-016 AC1: brief #442 answer 3 (an empty third run names its reason under Not run)."""
    start(repo, AREA + table_toml(extra='always_full = ["src/**"]\n'))
    change(repo)
    target = tmp_path / "manifest.md"
    proof(repo, "--manifest", str(target))
    text = target.read_text(encoding="utf-8")
    assert "- regression: full (always_full src/** matches " in text


@pytest.mark.parametrize("value", ['"yes"', "1", "[true]"])
def test_ac1_impact_refuses_a_proof_regression_that_is_not_a_boolean(repo, value):
    """REQ-016 AC1: brief #442 answer 2 (a boolean; the refusal names the setting)."""
    start(repo, AREA + table_toml(value))
    with pytest.raises(CheckError) as caught:
        impact.proof_regression(repo.root)
    assert "(setting: testing.proof_regression)" in str(caught.value)
    assert value not in str(caught.value)
    proc = proof(repo)
    assert proc.returncode == 2 and "(setting: testing.proof_regression)" in proc.stdout


def test_ac1_impact_reads_proof_regression_with_false_by_default(repo):
    """REQ-016 AC1: brief #442 answer 2 (default false; the table's settings are unchanged)."""
    start(repo, AREA + table_toml(None))
    assert impact.proof_regression(repo.root) is False
    assert "proof_regression" not in impact.testing_table(repo.root)
    assert impact.proof_regression(repo.root.parent / "absent") is False


def test_ac1_impact_reads_proof_regression_true(repo):
    """REQ-016 AC1: brief #442 answer 2."""
    start(repo, AREA + table_toml("true"))
    assert impact.proof_regression(repo.root) is True


def test_this_repository_keeps_the_setting_off_until_a_person_approves_it():
    """REQ-016 AC1: brief #442 (the spec change is only a proposal; nothing turns on)."""
    root = Path(__file__).resolve().parents[2]
    assert impact.proof_regression(root) is False
    proposals = list((root / "docs" / "runs").glob("proposed-spec-amendments-*.md"))
    texts = [p.read_text(encoding="utf-8") for p in proposals]
    assert any("proof_regression" in t and "SPEC-0010" in t for t in texts)
