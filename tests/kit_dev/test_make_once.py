"""Kit-only tests: `make test` here runs the kit suite once; the status-only rule is written.

`agk.toml` `project_tests` is the same command as `agk-test` on purpose (the CI proof job runs
the kit's tests as the project's tests), so the installed `Makefile` runs the suite twice. The kit
repository's `GNUmakefile` (never installed) runs it once and leaves `Makefile`, `agk.mk`,
`kit/agk-kit.mk`, `agk.toml` and the proof job as they are. No network, no model.
"""

from __future__ import annotations

import re
import subprocess  # nosec B404 - fixed argument lists, no shell

from conftest import KIT_ROOT, clean_env, manifest

GNU = KIT_ROOT / "GNUmakefile"
PROJECT_RECIPE = "scripts/agk/project_tests.py"


def dry_run(*args: str) -> str:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["make", "-n", *args],
        cwd=KIT_ROOT,
        capture_output=True,
        text=True,
        env=clean_env(),
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout


def test_ac1_make_test_in_this_repository_runs_the_kit_suite_once():
    """REQ-009 AC1: `make test` here runs `agk-test` and not `agk-project-test`."""
    out = dry_run("test")
    assert out.count("pytest -c tests/kit/pytest.ini") == 1
    assert PROJECT_RECIPE not in out


def test_ac1_the_installed_makefile_still_runs_both_targets():
    """REQ-009 AC1: the template is untouched (`make -f Makefile test` is what a project gets)."""
    out = dry_run("-f", "Makefile", "test")
    assert "pytest -c tests/kit/pytest.ini" in out and PROJECT_RECIPE in out
    assert "test: agk-test agk-project-test" in (KIT_ROOT / "Makefile").read_text(encoding="utf-8")


def test_ac1_the_project_test_target_is_still_available_here():
    """REQ-009 AC1: `make agk-project-test` and the CI proof's command are unchanged."""
    assert PROJECT_RECIPE in dry_run("agk-project-test")


def aliases(path) -> dict[str, str]:
    found = re.findall(r"(?m)^(governance|lint|traceability|test): (.*)$", path.read_text("utf-8"))
    return {name: rest.strip() for name, rest in found}


def test_ac1_the_gnumakefile_has_the_same_aliases_as_the_makefile_except_test():
    """REQ-009 AC1: no drift between the two files (`test` is the one difference)."""
    here, template = aliases(GNU), aliases(KIT_ROOT / "Makefile")
    assert here.pop("test") == "agk-test"
    assert template.pop("test") == "agk-test agk-project-test"
    assert here == template and len(here) == 3


def test_ac1_the_gnumakefile_is_not_installed():
    """REQ-009 AC1: repository only (never in the manifest)."""
    listed = json_text(manifest())
    assert "GNUmakefile" not in listed


def json_text(data) -> str:
    import json

    return json.dumps(data)


def test_ac1_the_status_only_rule_is_written_in_an_adr_and_the_decisions_log():
    """REQ-009 AC1: the maintainers' rule of 2026-10-24 (a status-only commit needs governance)."""
    adrs = sorted((KIT_ROOT / "docs" / "adr").glob("*status-only*.md"))
    assert len(adrs) == 1
    text = " ".join(adrs[0].read_text(encoding="utf-8").split())
    for needle in (
        "ADR-0050",
        "only `Final:` status lines",
        "`make governance`",
        "not the full `make test`",
        "CI's proof still runs",
    ):
        assert needle in text, needle
    log = (KIT_ROOT / "docs" / "runs" / "decisions-log.md").read_text(encoding="utf-8")
    assert "status-only rule" in log and adrs[0].name in log
