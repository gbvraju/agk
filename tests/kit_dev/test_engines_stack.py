"""Kit-only tests of `/agk:stack` (SPEC-0029 rule 5; REQ-036 AC4).

`engines.py` writes the skeleton of the stack ADR and checks its shape: two or three options, each
with trade-offs and the practices it brings, the practices told apart as checked or judged, and
the lock (`Chosen`). No model, no network.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest
from conftest import KIT_ROOT, clean_env
from test_playbook import started as playbook_started  # noqa: F401  (wrapped below)


@pytest.fixture
def started(request):
    return request.getfixturevalue("playbook_started")


SCRIPT = KIT_ROOT / "scripts" / "agk" / "engines.py"


def engines(root, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )


# --- the stack ---------------------------------------------------------------------------------

OPTION_A = (
    "   - Option A — plain scripts. Trade-offs: nothing to host, fewer features. "
    "Practices: pinned actions, least privilege.\n"
)
OPTION_B = (
    "   - Option B — a web framework. Trade-offs: more features, a host to run. "
    "Practices: pinned actions, security headers, a host-boundary test.\n"
)
GOOD_STACK = f"""# ADR-0002: stack options

- Status: Proposed
- Date: 2026-10-24
- Deciders: maintainers
- Related: ADR-0001
- Requirements: REQ-001

## Context

A reading list that runs on a laptop.

## Decision

1. **Options**
{OPTION_A}{OPTION_B}2. **Practices**
   - pinned actions: check (step: the workflow lint of the adopting build)
   - least privilege: check (step: the permissions check of the adopting build)
   - security headers: check (step: a header test of the adopting build)
   - a host-boundary test: check (step: the boundary test of the adopting build)
3. **Chosen**: none yet

## Consequences

The architect accepts one option; the ADR then locks it.

## Residual

None.
"""


def stack_root(root, text=GOOD_STACK, name="0002-stack-options.md"):
    (root / "docs" / "adr" / name).write_text(text, encoding="utf-8")
    return root


def test_ac4_stack_ids_reads_the_next_adr_number_from_the_ref(started):
    """REQ-036 AC4: SPEC-0029 rule 5 (the number is read from the ref, never guessed)."""
    proc = engines(started, "stack-ids", "--ref", "main")
    assert json.loads(proc.stdout) == {
        "adr": "0002",
        "slug": "stack-options",
        "branch": "stack/options",
    }


def test_ac4_stack_write_makes_a_proposed_skeleton_that_is_not_drafted_yet(started):
    """REQ-036 AC4: SPEC-0029 rule 5 (written through the template; nothing chosen)."""
    proc = engines(started, "stack-write", "--ref", "main", "--date", "2026-10-24")
    assert proc.returncode == 0, proc.stdout
    text = (started / "docs" / "adr" / "0002-stack-options.md").read_text(encoding="utf-8")
    assert "- Status: Proposed" in text and "- Date: 2026-10-24" in text
    assert "**Chosen**: none yet" in text and "TODO(architect)" in text
    check = engines(started, "stack-check")
    assert check.returncode == 1 and "rule 5" in check.stdout and "not drafted" in check.stdout
    again = engines(started, "stack-write", "--ref", "main")
    assert again.returncode == 1 and "rule 5" in again.stdout


def test_ac4_two_or_three_options_with_practices_told_apart_pass(started):
    """REQ-036 AC4: SPEC-0029 rule 5 (checked practices and recorded judgement)."""
    stack_root(started)
    assert engines(started, "stack-check").stdout == "ok engines-stack\n"
    judged = GOOD_STACK.replace(
        "   - a host-boundary test: check (step: the boundary test of the adopting build)\n",
        "   - a host-boundary test: judgement\n",
    )
    stack_root(started, judged)
    assert engines(started, "stack-check").returncode == 0
    third = GOOD_STACK.replace(
        "2. **Practices**",
        "   - Option C — a hosted service. Trade-offs: no servers, lock-in. "
        "Practices: pinned actions.\n"
        "2. **Practices**",
    )
    stack_root(started, third)
    assert engines(started, "stack-check").returncode == 0


def test_ac4_no_stack_adr_is_nothing_to_check(started):
    """REQ-036 AC4: SPEC-0029 rule 5 (the check is silent where /agk:stack was not run)."""
    assert engines(started, "stack-check").stdout == "ok engines-stack (no stack ADR)\n"


@pytest.mark.parametrize(
    ("change", "needle"),
    [
        (lambda t: t.replace(OPTION_B, ""), "two or three"),
        (
            lambda t: t.replace(
                "2. **Practices**",
                "".join(
                    f"   - Option {x} — s. Trade-offs: t. Practices: pinned actions.\n"
                    for x in "CD"
                )
                + "2. **Practices**",
            ),
            "two or three",
        ),
        (lambda t: t.replace(" Practices: pinned actions, least privilege.", ""), "Practices"),
        (lambda t: t.replace("Trade-offs: nothing to host, fewer features. ", ""), "Trade-offs"),
        (lambda t: t.replace("security headers, ", "tls pinning, "), "not in the Practices item"),
        (
            lambda t: t.replace(
                "least privilege: check (step: the permissions check of the adopting build)",
                "least privilege: maybe",
            ),
            "neither check nor judgement",
        ),
        (
            lambda t: t.replace("check (step: the workflow lint of the adopting build)", "check"),
            "step",
        ),
        (lambda t: t.replace("3. **Chosen**: none yet", "3. **Chosen**: Option A"), "Proposed"),
        (lambda t: t.replace("- Status: Proposed", "- Status: Accepted"), "Chosen"),
        (
            lambda t: t.replace("- Status: Proposed", "- Status: Accepted").replace(
                "none yet", "Option C"
            ),
            "Chosen",
        ),
        (
            lambda t: t.replace("- Status: Proposed", "- Status: Accepted").replace(
                "none yet", "Option A and Option B"
            ),
            "Chosen",
        ),
        (lambda t: t.replace("1. **Options**", "1. **Choices**"), "Options"),
        (lambda t: t + "\nTODO(architect) later\n", "not drafted"),
    ],
)
def test_ac4_a_stack_adr_that_breaks_the_shape_fails_naming_the_rule(started, change, needle):
    """REQ-036 AC4: SPEC-0029 rule 5 (options, trade-offs, practices, the lock)."""
    stack_root(started, change(GOOD_STACK))
    proc = engines(started, "stack-check")
    assert proc.returncode == 1 and "rule 5" in proc.stdout and needle in proc.stdout, proc.stdout


def test_ac4_an_accepted_stack_adr_locks_exactly_one_option(started):
    """REQ-036 AC4: SPEC-0029 rule 5 (the architect accepts one; the ADR locks it)."""
    accepted = GOOD_STACK.replace("- Status: Proposed", "- Status: Accepted").replace(
        "none yet", "Option B"
    )
    stack_root(started, accepted)
    assert engines(started, "stack-check").returncode == 0


def accepted(chosen):
    return GOOD_STACK.replace("- Status: Proposed", "- Status: Accepted").replace(
        "3. **Chosen**: none yet", f"3. **Chosen**: {chosen}"
    )


@pytest.mark.parametrize(
    "chosen",
    [
        "Option A — nothing to host suits a laptop app.",
        "Option B — the owner wants a web page.",
        "Option B",
    ],
)
def test_ac4_chosen_with_a_one_line_reason_and_accepted_together_pass(started, chosen):
    """REQ-036 AC4: brief 274 answer 1 (one ordinary commit sets Chosen and Status together)."""
    stack_root(started, accepted(chosen))
    proc = engines(started, "stack-check")
    # Brief 267 answer 2: an accepted stack with no local-profile decision adds one info line.
    info = "info engines: local profile: not decided\n"
    # Brief 450 (ADR-0241): and one [testing] line before it; this ADR has no test selection.
    testing = "info engines: [testing] not compared: the stack ADR has no test selection practice\n"
    assert (proc.returncode, proc.stdout) == (0, "ok engines-stack\n" + testing + info), proc.stdout


@pytest.mark.parametrize(
    "chosen",
    [
        "Option A —",
        "Option A and B — both.",
        "Option C — a hosted service.",
        "Option A — first line.\n   and a second line.",
    ],
)
def test_ac4_an_accepted_lock_that_is_not_one_option_and_one_line_fails(started, chosen):
    """REQ-036 AC4: brief 274 answer 1 (one option, at most a one-line reason)."""
    stack_root(started, accepted(chosen))
    proc = engines(started, "stack-check")
    assert proc.returncode == 1 and "rule 5" in proc.stdout and "Chosen" in proc.stdout
    assert "hosted" not in proc.stdout and "second" not in proc.stdout


def test_ac4_chosen_while_proposed_is_still_refused_and_names_the_plain_step(started):
    """REQ-036 AC4: brief 274 answer 4 (Chosen while Proposed is refused; the message says how)."""
    stack_root(started, GOOD_STACK.replace("none yet", "Option A — nothing to host."))
    proc = engines(started, "stack-check")
    assert proc.returncode == 1 and "rule 5" in proc.stdout and "Proposed" in proc.stdout
    assert "Status: Accepted in the same commit" in proc.stdout
    assert "nothing to host" not in proc.stdout


# --- the skill and the guide -------------------------------------------------------------------


def test_ac4_the_skill_names_the_engine_the_template_and_the_check():
    """REQ-036 AC4: SPEC-0029 rules 3 and 5 (an engine drafts; the architect accepts one)."""
    text = (KIT_ROOT / "skills" / "stack" / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: stack\n") and "disable-model-invocation: true" in text
    assert "[engines]" in text and "`stack`" in text and "never decides" in text
    assert "engines.py" in text and "stack-check" in text and "stack-write" in text
    assert "protected" in text and "template" in text and "Accepted" in text
    for verb in ("git push", "git commit", "gh pr", "gh issue"):
        assert verb not in text


def test_ac4_the_skill_ends_with_the_plain_accepting_step_its_prompt_and_body():
    """REQ-036 AC4: brief 274 answer 2 (the last step names the one ordinary commit)."""
    text = (KIT_ROOT / "skills" / "stack" / "SKILL.md").read_text(encoding="utf-8")
    last = text[text.index("\n4. ") :]
    for needle in (
        "ordinary commit",
        "`Status: Accepted`",
        "`Chosen: Option <X> — <one-line reason>`",
        "not a `Final:`",
        "Verdict: cleared",
        "The prompt for the accepting change",
        "The body of its pull request",
        "Summary:",
        "Advances:",
        "Build-state row:",
    ):
        assert needle in last, needle


def test_ac4_the_guide_lists_the_command_and_the_two_kinds_of_practice():
    """REQ-036 AC4: SPEC-0029 rule 5 (checked practices and recorded judgement)."""
    guide = (KIT_ROOT / "docs" / "guides" / "reference.md").read_text(encoding="utf-8")
    assert "| `/agk:stack` |" in guide
    for text in ("two or three stacks", "`check`", "`judgement`", "locks it"):
        assert text in guide, text


def test_ac4_an_unknown_command_is_still_a_usage_error(started):
    """REQ-036 AC4: SPEC-0029 rule 5 (no command falls through to another one)."""
    proc = engines(started, "stack-nothing")
    assert (
        proc.returncode == 2 and proc.stdout == "" and proc.stderr.startswith("usage: engines.py")
    )
