"""Tests of scripts/agk/check_kit_tests.py: a test never pins its own ADR's status (brief #483).

A test file that a pull request adds or changes fails the check when it asserts that an ADR the same
pull request adds reads `Proposed` only: the status-only `Final:` commit makes that ADR Accepted and
the test then turns the default branch red. Fixture repositories only; no network.
"""

from __future__ import annotations

import json
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
CHECK = "scripts/agk/check_new.py"
NEW_ADR = "docs/adr/0900-a-new-decision.md"
OLD_ADR = "docs/adr/0800-an-old-decision.md"
TEST = "tests/kit/test_new_thing.py"
PROPOSED = "- Status: Proposed"


def adr(number: str, status: str) -> str:
    return (
        f"# ADR-{number}: A decision\n\n- Status: {status}\n- Date: 2026-11-04\n"
        "- Deciders: maintainers\n- Related: none\n- Requirements: REQ-009\n\n"
        "## Context\n\nx\n\n## Decision\n\nx\n\n## Consequences\n\nx\n\n## Residual\n\nx\n"
    )


def base(repo, extra: dict[str, str] | None = None) -> None:
    """A kit repository on main: one installed check with its test, then a feature branch."""
    manifest = {"kit_version": "0.0.0", "kit_tests": "tests/kit", "verbatim": [CHECK]}
    files = {
        "kit/manifest.json": json.dumps(manifest) + "\n",
        CHECK: "NAME = 'new'\n",
        "tests/kit/test_check_new.py": 'def test_a(repo):\n    repo.run("check_new.py")\n',
        OLD_ADR: adr("0800", "Proposed"),
    }
    files.update(extra or {})
    repo.commit(files, "base")
    repo.branch()


def pins(path: str, check: str) -> str:
    """A test file that reads the ADR at `path` and asserts `check` on its text."""
    return (
        '"""REQ-009 AC2."""\n\nfrom pathlib import Path\n\n'
        f'ADR = "{path}"\n\n\n'
        "def test_status():\n"
        "    text = Path(ADR).read_text()\n"
        f"    {check}\n"
    )


def test_a_new_test_pinning_a_new_adr_to_proposed_fails(repo):
    """REQ-009 AC2: brief #483 answer 1; the message names the test file and the ADR."""
    base(repo)
    repo.commit(
        {NEW_ADR: adr("0900", "Proposed"), TEST: pins(NEW_ADR, f'assert "{PROPOSED}" in text')}
    )
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1, proc.stdout
    assert "FAIL kit-tests" in proc.stdout
    assert TEST in proc.stdout and "ADR-0900" in proc.stdout


def test_a_status_read_and_compared_with_proposed_fails(repo):
    """REQ-009 AC2: brief #483 answer 1 (reads the status and compares it with Proposed)."""
    base(repo)
    check = 'assert text.split("Status: ")[1].split()[0] == "Proposed"'
    repo.commit({NEW_ADR: adr("0900", "Proposed"), TEST: pins("ADR-0900", check)})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1, proc.stdout
    assert TEST in proc.stdout and "ADR-0900" in proc.stdout


def test_a_changed_test_on_main_that_now_pins_a_new_adr_fails(repo):
    """REQ-009 AC2: a test file the pull request changes counts as well as one it adds."""
    base(repo, {TEST: "def test_x():\n    assert True\n"})
    repo.commit(
        {NEW_ADR: adr("0900", "Proposed"), TEST: pins(NEW_ADR, f'assert "{PROPOSED}" in text')}
    )
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1, proc.stdout
    assert TEST in proc.stdout


def test_a_test_accepting_proposed_or_accepted_passes(repo):
    """REQ-009 AC2: the form ADR-0250 chose, Proposed or Accepted, is allowed."""
    base(repo)
    check = f'assert "{PROPOSED}" in text or "- Status: Accepted" in text'
    repo.commit({NEW_ADR: adr("0900", "Proposed"), TEST: pins(NEW_ADR, check)})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.startswith("ok kit-tests")


def test_an_adr_already_on_main_is_not_affected(repo):
    """REQ-009 AC2: brief #483 answer 1; ADRs already on main are not affected."""
    base(repo)
    repo.commit(
        {NEW_ADR: adr("0900", "Proposed"), TEST: pins(OLD_ADR, f'assert "{PROPOSED}" in text')}
    )
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 0, proc.stdout


def test_an_unchanged_test_is_not_read(repo):
    """REQ-009 AC2: only test files that the pull request adds or changes are read."""
    base(repo, {TEST: pins(NEW_ADR, f'assert "{PROPOSED}" in text')})
    repo.commit({NEW_ADR: adr("0900", "Proposed")})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 0, proc.stdout


def test_a_mention_in_a_docstring_does_not_tie_the_test_to_the_adr(repo):
    """REQ-009 AC2: a docstring citing the new ADR does not make a fixture's status its own."""
    base(repo)
    test_text = (
        '"""REQ-009 AC2: ADR-0900."""\n\n\n'
        "def test_fixture():\n"
        '    """ADR-0900: a fixture ADR of its own."""\n'
        '    text = "docs/adr/0002-x.md"\n'
        f'    assert "{PROPOSED}" != text\n'
    )
    repo.commit({NEW_ADR: adr("0900", "Proposed"), TEST: test_text})
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 0, proc.stdout


def test_no_base_outside_ci_skips_only_the_status_rule(repo):
    """REQ-009 AC2: with no base ref the installed-test rule still runs."""
    manifest = {"kit_version": "0.0.0", "kit_tests": "tests/kit", "verbatim": [CHECK]}
    repo.commit({"kit/manifest.json": json.dumps(manifest) + "\n", CHECK: "x = 1\n"})
    repo.git("branch", "-m", "work")
    proc = repo.run("check_kit_tests.py")
    assert proc.returncode == 1
    assert "has no test file" in proc.stdout


def test_the_brief_template_says_a_test_never_pins_its_own_adr():
    """REQ-009 AC2: brief #483 answer 2; the template gains one line, the session rules none."""
    template = (KIT_ROOT / "docs" / "briefs" / "TEMPLATE.md").read_text(encoding="utf-8")
    assert "A test never pins its own ADR's status" in template
    rules = (KIT_ROOT / "config" / "session-rules.md").read_text(encoding="utf-8")
    assert "pins its own ADR" not in rules
