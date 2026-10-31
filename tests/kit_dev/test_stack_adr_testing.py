"""Kit-only tests of the testing practices of the stack ADR (brief #418, ADR-0228; REQ-016).

The stack ADR template names two more practices: fast tests (a check, with its step) and test
selection (a judgement: the `[testing]` profile and the `always_full` paths each option proposes)
(answer 1). The stack skill says that the build which accepts the stack copies the chosen
option's `[testing]` values into `agk.toml` in the same pull request as the ADR, so one ADR sets
them (answer 2). Files and the local `engines.py` only; no network.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env
from test_playbook import started as playbook_started  # noqa: F401  (wrapped below)

TEMPLATE = KIT_ROOT / "kit" / "templates" / "stack-adr.md"
SKILL = KIT_ROOT / "skills" / "stack" / "SKILL.md"
ENGINES = KIT_ROOT / "scripts" / "agk" / "engines.py"

FAST_TESTS = (
    "   - fast tests: check (step: the full project suite runs in budget_seconds or less on the CI "
    "runner, with tests in parallel, a template database copied per test, no network in tests and "
    "cached dependencies)\n"
)
TEST_SELECTION = (
    "   - test selection: judgement (the [testing] profile and the always_full paths the option "
    "proposes, for example authentication, permissions, migrations and secrets handling)\n"
)


@pytest.fixture
def started(request):
    return request.getfixturevalue("playbook_started")


def engines(root, *args):
    return subprocess.run(
        [sys.executable, str(ENGINES), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


def practices(text: str) -> str:
    return text[text.index("2. **Practices**") : text.index("3. **Chosen**")]


def test_answer1_the_template_carries_the_fast_tests_practice():
    """REQ-016: brief #418 answer 1 (fast tests is a check with its step)."""
    assert FAST_TESTS in practices(TEMPLATE.read_text(encoding="utf-8"))


def test_answer1_the_template_carries_the_test_selection_practice():
    """REQ-016: brief #418 answer 1 (test selection is recorded judgement)."""
    assert TEST_SELECTION in practices(TEMPLATE.read_text(encoding="utf-8"))


def test_answer1_the_earlier_practices_are_kept():
    """REQ-016: brief #418 answer 1 (two lines added; local profile and fast CI stay)."""
    block = practices(TEMPLATE.read_text(encoding="utf-8"))
    assert "   - local profile: check (step: " in block
    assert "   - fast CI: check (step: " in block
    assert block.count("\n   - ") == 5


def test_answer3_the_template_renders_with_both_lines(started):
    """REQ-016: brief #418 answer 3 (`stack-write` writes the template with both lines)."""
    proc = engines(started, "stack-write", "--ref", "main", "--date", "2026-10-31")
    assert proc.returncode == 0, proc.stdout
    text = (started / "docs" / "adr" / "0002-stack-options.md").read_text(encoding="utf-8")
    assert FAST_TESTS in practices(text) and TEST_SELECTION in practices(text)


def test_answer3_a_stack_drafted_from_the_template_with_both_lines_passes(started):
    """REQ-016: brief #418 answers 1 and 3 (both lines are well-formed practices)."""
    engines(started, "stack-write", "--ref", "main", "--date", "2026-10-31")
    path = started / "docs" / "adr" / "0002-stack-options.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("- Requirements: TODO(architect)", "- Requirements: REQ-001")
    text = text.replace(
        "TODO(architect): what the product needs", "A reading list on a laptop; what it needs"
    )
    lines = []
    for line in text.splitlines(keepends=True):
        if "Option A — TODO" in line:
            line = (
                "   - Option A — plain scripts. Trade-offs: nothing to host. "
                "Practices: fast tests, test selection.\n"
            )
        elif "Option B — TODO" in line:
            line = (
                "   - Option B — a web framework. Trade-offs: a host to run. "
                "Practices: fast tests, test selection, local profile.\n"
            )
        elif "TODO(architect): check" in line:
            continue
        lines.append(line)
    path.write_text("".join(lines), encoding="utf-8")
    proc = engines(started, "stack-check")
    assert proc.stdout == "ok engines-stack\n", proc.stdout


def test_answer2_the_skill_names_the_copy_into_agk_toml_in_the_accepting_pull_request():
    """REQ-016: brief #418 answer 2 (one ADR sets the [testing] values)."""
    text = SKILL.read_text(encoding="utf-8")
    last = text[text.index("\n4. ") : text.index("\n5. ")]
    assert "`[testing]`" in last and "`agk.toml`" in last
    assert "same pull request" in last and "one ADR sets them" in last
    assert "chosen option" in last


def test_answer2_the_skill_has_each_option_name_its_testing_values():
    """REQ-016: brief #418 answers 1 and 2 (the values are in the ADR before they are copied)."""
    text = SKILL.read_text(encoding="utf-8")
    fill = text[text.index("\n2. ") : text.index("\n3. ")]
    for needle in ("`fast tests`", "`test selection`", "`[testing]`", "`always_full`"):
        assert needle in fill, needle
    assert "`agk.toml`" in fill


def test_answer2_the_accepting_prompt_names_the_copy():
    """REQ-016: brief #418 answer 2 (the printed prompt carries the step, so it is not lost)."""
    text = SKILL.read_text(encoding="utf-8")
    prompt = text[text.index("Accept option <X> of the stack ADR") :]
    prompt = prompt[: prompt.index("```")]
    assert "[testing]" in prompt and "agk.toml" in prompt and "second ordinary commit" in prompt
