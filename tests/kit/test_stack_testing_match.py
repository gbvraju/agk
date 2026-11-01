"""Kit tests: `stack-check` says whether `[testing]` matches the chosen stack option (brief #450).

When the stack ADR is Accepted and its Chosen line names an option, `engines.py stack-check` prints
one information line after `ok engines-stack`: whether the `[testing]` profile and `always_full`
paths in `agk.toml` match what the chosen option's part of the `test selection` practice names
(ADR-0241). The line names a setting, never a value, and never changes the exit code. Invented
ADRs and `agk.toml` files under a temporary root; no network, no git.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
ENGINES = KIT_ROOT / "scripts" / "agk" / "engines.py"
SKILL = KIT_ROOT / "skills" / "stack" / "SKILL.md"
GUIDE = KIT_ROOT / "docs" / "guides" / "testing.md"
STACK = "docs/adr/0002-stack-options.md"
SELECTION = (
    "test selection: judgement (Option A: profile fast, always_full `app/auth/**`, "
    "`migrations/**`; Option B: profile thorough, always_full `src/secrets/**`)"
)
MATCH = 'profile = "fast"\nalways_full = ["app/auth/**", "migrations/**"]\n'


def stack_adr(
    status: str = "Accepted",
    chosen: str = "Option A — nothing to host suits a laptop.",
    selection: str | None = SELECTION,
) -> str:
    practice = f"   - {selection}\n" if selection is not None else ""
    names = ", test selection" if selection is not None else ""
    return f"""# ADR-0002: stack options

- Status: {status}
- Date: 2026-11-01
- Deciders: maintainers
- Related: ADR-0001
- Requirements: REQ-001

## Context

A reading list that runs on a laptop, for readers at example.com.

## Decision

1. **Options**
   - Option A — plain scripts. Trade-offs: nothing to host. Practices: pinned actions{names}.
   - Option B — a web framework. Trade-offs: a host to run. Practices: pinned actions{names}.
2. **Practices**
   - pinned actions: check (step: the workflow lint of the adopting build)
{practice}3. **Chosen**: {chosen}

## Consequences

The architect accepts one option; the ADR then locks it.

## Residual

None.
"""


def project(tmp_path: Path, adr: str, testing: str | None) -> Path:
    path = tmp_path / STACK
    path.parent.mkdir(parents=True)
    path.write_text(adr, encoding="utf-8")
    toml = 'default_branch = "main"\n'
    if testing is not None:
        toml += "\n[testing]\n" + testing
    (tmp_path / "agk.toml").write_text(toml, encoding="utf-8")
    return tmp_path


def stack_check(root: Path):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(ENGINES), "stack-check", "--root", str(root)],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def table_lines(stdout: str) -> list[str]:
    return [ln for ln in stdout.splitlines() if ln.startswith("info engines: [testing]")]


def run(tmp_path: Path, adr: str, testing: str | None) -> tuple[int, list[str], str]:
    proc = stack_check(project(tmp_path, adr, testing))
    return proc.returncode, table_lines(proc.stdout), proc.stdout


def test_answer2_a_copy_that_agrees_matches(tmp_path):
    """REQ-016: brief #450 answers 1 and 2 (profile and every named path agree)."""
    code, lines, out = run(tmp_path, stack_adr(), MATCH)
    assert (code, lines) == (0, ["info engines: [testing] matches option A"]), out


def test_answer1_the_line_follows_ok_engines_stack(tmp_path):
    """REQ-016: brief #450 answer 1 (one step after `ok engines-stack`)."""
    _, _, out = run(tmp_path, stack_adr(), MATCH)
    assert out.splitlines()[:2] == [
        "ok engines-stack",
        "info engines: [testing] matches option A",
    ], out


def test_answer2_a_profile_that_differs_names_the_setting(tmp_path):
    """REQ-016: brief #450 answer 2 (`profile` is named, never a value)."""
    testing = 'profile = "thorough"\nalways_full = ["app/auth/**", "migrations/**"]\n'
    code, lines, out = run(tmp_path, stack_adr(), testing)
    assert (code, lines) == (0, ["info engines: [testing] differs from option A: profile"]), out
    assert "thorough" not in out and "fast" not in out


def test_answer2_a_missing_path_names_the_setting(tmp_path):
    """REQ-016: brief #450 answer 2 (`always_full` is named, never the path)."""
    testing = 'profile = "fast"\nalways_full = ["app/auth/**"]\n'
    code, lines, out = run(tmp_path, stack_adr(), testing)
    assert (code, lines) == (0, ["info engines: [testing] differs from option A: always_full"]), out
    assert "migrations" not in out


def test_answer2_both_settings_that_differ_are_named(tmp_path):
    """REQ-016: brief #450 answer 2 (the line names each setting that differs)."""
    testing = 'profile = "balanced"\nalways_full = []\n'
    code, lines, out = run(tmp_path, stack_adr(), testing)
    want = ["info engines: [testing] differs from option A: profile, always_full"]
    assert (code, lines) == (0, want), out


def test_answer3_an_extra_path_in_agk_toml_is_not_a_difference(tmp_path):
    """REQ-016: brief #450 answer 3 (the bullet's paths must be a subset)."""
    testing = 'profile = "fast"\nalways_full = ["app/auth/**", "migrations/**", "app/pay/**"]\n'
    code, lines, out = run(tmp_path, stack_adr(), testing)
    assert (code, lines) == (0, ["info engines: [testing] matches option A"]), out


def test_answer1_only_the_chosen_options_part_is_read(tmp_path):
    """REQ-016: brief #450 answer 1 and out of scope (option B's values are never read)."""
    chosen = "Option B — a host suits a team."
    code, lines, out = run(tmp_path, stack_adr(chosen=chosen), MATCH)
    assert (code, lines) == (
        0,
        ["info engines: [testing] differs from option B: profile, always_full"],
    ), out
    testing = 'profile = "thorough"\nalways_full = ["src/secrets/**"]\n'
    code, lines, out = run(tmp_path / "b", stack_adr(chosen=chosen), testing)
    assert (code, lines) == (0, ["info engines: [testing] matches option B"]), out


def test_answer3_a_bullet_that_names_no_profile_is_not_compared(tmp_path):
    """REQ-016: brief #450 answers 2 and 3 (no profile is never read as a mismatch)."""
    selection = "test selection: judgement (Option A: always_full `app/auth/**`; Option B: none)"
    code, lines, out = run(tmp_path, stack_adr(selection=selection), 'profile = "thorough"\n')
    want = [
        "info engines: [testing] not compared: the test selection practice names no profile "
        "for option A"
    ]
    assert (code, lines) == (0, want), out


def test_answer3_the_template_wording_names_no_profile(tmp_path):
    """REQ-016: brief #450 answer 3 (the template's own parenthesis is never a mismatch)."""
    selection = (
        "test selection: judgement (the [testing] profile and the always_full paths the option "
        "proposes, for example authentication, permissions, migrations and secrets handling)"
    )
    code, lines, out = run(tmp_path, stack_adr(selection=selection), MATCH)
    assert code == 0 and len(lines) == 1 and "not compared" in lines[0], out


def test_answer2_an_adr_without_the_practice_is_not_compared(tmp_path):
    """REQ-016: brief #450 answer 2 (an older stack ADR without `test selection`)."""
    code, lines, out = run(tmp_path, stack_adr(selection=None), MATCH)
    want = ["info engines: [testing] not compared: the stack ADR has no test selection practice"]
    assert (code, lines) == (0, want), out


def test_answer2_no_testing_table_is_not_compared(tmp_path):
    """REQ-016: brief #450 answer 2 (the table is absent)."""
    code, lines, out = run(tmp_path, stack_adr(), None)
    assert (code, lines) == (0, ["info engines: [testing] not compared: no [testing] table"]), out


def test_answer2_a_table_that_cannot_be_read_is_not_compared_naming_the_setting(tmp_path):
    """REQ-016: brief #450 answer 2 (a refused table names the setting and fails nothing)."""
    code, lines, out = run(tmp_path, stack_adr(), 'profile = "quick"\n')
    assert code == 0 and len(lines) == 1, out
    assert (
        lines[0].startswith("info engines: [testing] not compared: ")
        and "testing.profile" in lines[0]
    )
    assert "quick" not in out


def test_answer2_no_chosen_option_yet_prints_no_testing_line(tmp_path):
    """REQ-016: brief #450 answers 1 and 2 (a Proposed ADR: output unchanged)."""
    proc = stack_check(project(tmp_path, stack_adr("Proposed", "none yet"), MATCH))
    assert (proc.returncode, proc.stdout) == (0, "ok engines-stack\n"), proc.stdout


@pytest.mark.parametrize(
    "testing",
    [MATCH, 'profile = "thorough"\n', None, 'profile = "quick"\n'],
)
def test_answer2_the_exit_code_stays_what_the_shape_check_gives(tmp_path, testing):
    """REQ-016: brief #450 answer 2 (never fails; a shape failure still does)."""
    code, _, out = run(tmp_path / "ok", stack_adr(), testing)
    assert code == 0, out
    broken = stack_adr().replace(
        "   - pinned actions: check (step: the workflow lint of the adopting build)\n", ""
    )
    code, lines, out = run(tmp_path / "bad", broken, testing)
    assert code == 1 and lines == [] and "FAIL engines" in out, out


def test_answer4_the_skill_says_stack_check_prints_whether_the_copy_matches():
    """REQ-016: brief #450 answer 4 (step 4 of the stack skill)."""
    text = SKILL.read_text(encoding="utf-8")
    step = " ".join(text[text.index("\n4. ") : text.index("\n5. ")].split())
    assert "after the second commit, `stack-check` prints whether the copy matches" in step


def test_answer4_the_testing_guide_says_the_same():
    """REQ-016: brief #450 answer 4 (the guide names the stack ADR and the same sentence)."""
    text = " ".join(GUIDE.read_text(encoding="utf-8").split())
    assert "stack ADR" in text
    assert "after the second commit, `stack-check` prints whether the copy matches" in text
