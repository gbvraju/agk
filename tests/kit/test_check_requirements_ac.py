"""Every acceptance criterion of a `done` requirement needs a test marker (SPEC-0010 rules 1-6)."""

from __future__ import annotations

import re
from pathlib import Path

import common

ROOT = Path(__file__).resolve().parents[2]
CRITERIA = "AC1 given a, when b, then c; AC2 given d, when e, then f"


def requirement(rid: str, status: str, acceptance: str = CRITERIA) -> str:
    return f"### {rid} — Thing\n\n- Acceptance: {acceptance}\n- Status: {status}\n\n"


def out(proc) -> str:
    """The output with `REQ-` shown as `@`, as the test data is written (see `setup`)."""
    return proc.stdout.replace("REQ-", "@")


def setup(repo, requirements: str, tests: str, mode: str | None = None) -> None:
    """Test data writes `@` for `REQ-`, so that no line of this file is itself a marker."""
    requirements, tests = requirements.replace("@", "REQ-"), tests.replace("@", "REQ-")
    toml = 'default_branch = "main"\ntest_dirs = ["tests"]\n'
    if mode is not None:
        toml += f'ac_coverage = "{mode}"\n'
    repo.commit(
        {
            "agk.toml": toml,
            "docs/requirements.md": "# Requirements\n\n" + requirements,
            "tests/test_t.py": tests,
        }
    )


def check(repo):
    return repo.run("check_requirements.py")


def test_ac1_a_done_requirement_with_an_untested_second_criterion_fails_in_block(repo):
    """REQ-003 AC4, REQ-015 AC1: rule 1 (the fixture of criterion b)."""
    setup(repo, requirement("@007", "done"), "# @007 AC1\n", "block")
    proc = check(repo)
    assert proc.returncode == 1
    assert "FAIL requirements: @007: done requires a test marker for AC2" in out(proc)
    assert "given d" not in out(proc)  # the criterion's text is never printed


def test_ac1_the_same_shortfall_is_a_warning_in_warn_and_by_default(repo):
    """REQ-015 AC1: rule 5."""
    for mode in ("warn", None):
        setup(repo, requirement("@007", "done"), "# @007 AC1\n", mode)
        proc = check(repo)
        assert proc.returncode == 0, out(proc)
        assert "warn requirements: @007: done requires a test marker for AC2" in out(proc)
        assert "FAIL" not in out(proc)


def test_ac1_a_covered_done_requirement_and_a_requirement_not_done_pass_in_block(repo):
    """REQ-015 AC1: rule 1 (only `done` is checked)."""
    text = requirement("@001", "done") + requirement("@002", "in-progress")
    setup(repo, text, "# @001 AC1\n# @001 AC2\n", "block")
    proc = check(repo)
    assert proc.returncode == 0 and "warn" not in out(proc) and out(proc).startswith("ok")


def test_ac1_a_bare_marker_satisfies_the_old_rule_and_not_this_one(repo):
    """REQ-015 AC1: rule 2."""
    setup(repo, requirement("@001", "done"), "# @001\n", "block")
    proc = check(repo)
    assert proc.returncode == 1
    assert "@001: done requires a test marker for AC1" in out(proc)
    assert "@001: done requires a test marker for AC2" in out(proc)
    assert "under the test directories" not in out(proc)  # the old rule is satisfied


def test_ac1_a_run_of_requirements_attaches_the_criterion_to_each(repo):
    """REQ-015 AC1: rule 2 (the marker grammar of the shared parser)."""
    text = requirement("@001", "done") + requirement("@002", "done")
    setup(repo, text, "# @001 @002 AC1\n# @001/@002 AC2\n", "block")
    assert check(repo).returncode == 0


def test_ac1_an_unstructured_or_repeating_acceptance_line_fails_a_done_requirement(repo):
    """REQ-015 AC1: rule 3."""
    text = requirement("@001", "done", "it works") + requirement(
        "@002", "done", "AC1 a; AC2 b; AC2 c"
    )
    setup(repo, text, "# @001 AC1\n# @002 AC1\n# @002 AC2\n", "block")
    proc = check(repo)
    assert proc.returncode == 1
    assert "@001: done requires an acceptance line with AC1, AC2, ..." in out(proc)
    assert "@002: acceptance repeats AC2" in out(proc)
    assert "it works" not in out(proc)


def test_ac1_a_stray_marker_does_not_fail_the_check_but_is_a_finding_d7(repo):
    """REQ-015 AC1: rules 4 and 5 (the drift audit reports it; the check never blocks on it)."""
    setup(
        repo,
        requirement("@001", "done"),
        "# @001 AC1\n# @001 AC2\n# @001 AC9\n# @077 AC1\n",
        "block",
    )
    assert check(repo).returncode == 0
    proc = repo.run("drift_audit.py", "--today", "2026-10-15")
    lines = [ln for ln in out(proc).splitlines() if ln.startswith("- D7 ")]
    assert len(lines) == 2 and all("does not have" in ln for ln in lines)
    assert any("tests/test_t.py:3" in ln and "@001 AC9" in ln for ln in lines)
    assert any("tests/test_t.py:4" in ln and "@077 AC1" in ln for ln in lines)


def test_ac1_in_warn_the_audit_reports_each_shortfall_and_in_block_the_check_does(repo):
    """REQ-015 AC1: rule 5."""
    setup(repo, requirement("@001", "done"), "# @001 AC1\n", "warn")
    warn = out(repo.run("drift_audit.py", "--today", "2026-10-15"))
    assert re.search(r"^- D7 @001 \| .*@001: done requires a test marker for AC2", warn, re.M)
    setup(repo, requirement("@001", "done"), "# @001 AC1\n", "block")
    block = out(repo.run("drift_audit.py", "--today", "2026-10-15"))
    assert "- D7 " not in block


def test_ac1_an_unknown_value_is_a_refusal_that_names_the_setting_not_the_value(repo):
    """REQ-015 AC1: rule 5."""
    setup(repo, requirement("@001", "planned"), "# @001 AC1\n", "strict-ish")
    proc = check(repo)
    assert proc.returncode == 1
    assert "ac_coverage" in out(proc) and "strict-ish" not in out(proc)
    assert repo.run("drift_audit.py", "--today", "2026-10-15").returncode == 1


def test_ac1_the_output_names_the_requirement_and_the_criterion_only(repo):
    """REQ-015 AC1: rule 1."""
    setup(repo, requirement("@001", "done"), "# @001 AC1\n", "block")
    line = next(ln for ln in out(check(repo)).splitlines() if ln.startswith("FAIL"))
    assert line == "FAIL requirements: @001: done requires a test marker for AC2"


def test_ac3_this_repositorys_done_requirements_all_comply():
    """REQ-015 AC3: rule 6 (the real file and the real markers; skipped where there is none)."""
    path = ROOT / "docs" / "requirements.md"
    if not path.is_file() or not (ROOT / "kit" / "manifest.json").is_file():
        return
    reqs = common.parse_requirements(path.read_text(encoding="utf-8"))
    assert any(r["status"] == "done" for r in reqs)
    assert common.ac_shortfalls(reqs, common.ac_markers_for(ROOT)) == []


def test_ac1_shortfalls_and_strays_are_computed_once_in_common():
    """REQ-015 AC1: rule 2 (no second parse in the check or the audit)."""
    for name in ("check_requirements.py", "drift_audit.py"):
        source = (ROOT / "scripts" / "agk" / name).read_text(encoding="utf-8")
        assert "parse_acceptance" not in source and "find_ac_markers" not in source


def test_ac1_d7_leaves_out_the_kit_tests_in_an_adopted_repository_only(repo):
    """REQ-015 AC1: rule 4 (the search of `adopt` mode leaves out `tests/kit`, and so does D7)."""
    requirements = "# Requirements\n\n" + requirement("@001", "planned").replace("@", "REQ-")
    files = {
        "docs/requirements.md": requirements,
        "tests/test_t.py": "# @001 AC1\n".replace("@", "REQ-"),
        "tests/kit/test_k.py": "# @077 AC1\n".replace("@", "REQ-"),
    }
    base = 'default_branch = "main"\ntest_dirs = ["tests"]\nac_coverage = "block"\n'
    repo.commit({"agk.toml": base + 'mode = "init"\n', **files})
    init = [ln for ln in repo.run("drift_audit.py", "--today", "2026-10-15").stdout.splitlines()]
    assert (
        [ln for ln in init if ln.startswith("- D7 ")]
        == [ln for ln in init if ln.startswith("- D7 ") and "tests/kit/test_k.py:1" in ln]
        != []
    )
    repo.commit({"agk.toml": base + 'mode = "adopt"\n'})
    adopted = repo.run("drift_audit.py", "--today", "2026-10-15").stdout
    assert "- D7 " not in adopted
    assert check(repo).returncode == 0
