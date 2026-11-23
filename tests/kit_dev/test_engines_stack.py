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

# Brief #1591 (ADR-0671): a Proposed option gives the four effects; one is recommended with a Why.
EFFECTS = (
    "Cost: low; Build speed: quick; Security: one sign-in; Uptime: a short pause on a restart. "
)
OPTION_A = (
    "   - Option A — plain scripts (recommended). Trade-offs: nothing to host, fewer features. "
    f"{EFFECTS}Why: a laptop is all it needs. "
    "Parts: a 1.0 MIT. Practices: pinned actions, least privilege.\n"
)
OPTION_B = (
    f"   - Option B — a web framework. Trade-offs: more features, a host to run. {EFFECTS}"
    "Parts: a 1.0 MIT. Practices: pinned actions, security headers, a host-boundary test.\n"
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


# Brief #1785 answer 3: a Proposed record with no one profile per option cannot be accepted, and
# `stack-check` says so for each option, as notes after `ok engines-stack`.
NO_PROFILE = "rule 5: the test selection practice names no one profile for option"
NO_PROFILE_NOTES = "".join(f"note: option {x} cannot be accepted: {NO_PROFILE} {x}\n" for x in "AB")


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
    assert engines(started, "stack-check").stdout == "ok engines-stack\n" + NO_PROFILE_NOTES
    judged = GOOD_STACK.replace(
        "   - a host-boundary test: check (step: the boundary test of the adopting build)\n",
        "   - a host-boundary test: judgement\n",
    )
    stack_root(started, judged)
    assert engines(started, "stack-check").returncode == 0
    third = GOOD_STACK.replace(
        "2. **Practices**",
        f"   - Option C — a hosted service. Trade-offs: no servers, lock-in. {EFFECTS}"
        "Parts: a 1.0 MIT. Practices: pinned actions.\n"
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
                    f"   - Option {x} — s. Trade-offs: t. "
                    "Parts: a 1.0 MIT. Practices: pinned actions.\n"
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


# --- brief #1778 (ADR-0744; REQ-079): an option naming no runtime the kit checks is noted ------

NOTE_B = (
    "note: option B names no runtime the kit checks (python, node); "
    "its pins and standards pack will not run"
)


def declared(root, work_type=True):
    import shutil  # noqa: PLC0415 - only these tests copy the playbooks

    shutil.copytree(KIT_ROOT / "config" / "playbooks", root / "config" / "playbooks")
    toml = 'default_branch = "main"\n' + (
        '[delivery]\nwork_type = "web-app"\n' if work_type else ""
    )
    (root / "agk.toml").write_text(toml, encoding="utf-8")
    text = GOOD_STACK.replace(
        "Parts: a 1.0 MIT. Practices: pinned actions, least",
        "Parts: Node 22.11.0 MIT, a 1.0 MIT. Practices: pinned actions, least",
    )
    return stack_root(root, text)


def test_req079_an_option_with_no_known_runtime_prints_a_note_not_a_failure(started):
    """REQ-079: brief #1778 answer 2 (option A names `Node`, read as `node`; B names none)."""
    proc = engines(declared(started), "stack-check")
    assert proc.returncode == 0, proc.stdout
    assert NOTE_B in proc.stdout.splitlines()
    assert "option A names no runtime" not in proc.stdout


def test_req079_no_work_type_prints_no_runtime_note(started):
    """REQ-079: brief #1778 answer 3 (without `[delivery] work_type` nothing changes)."""
    proc = engines(declared(started, work_type=False), "stack-check")
    assert proc.returncode == 0 and "names no runtime" not in proc.stdout


# --- brief #1785 (ADR-0748; REQ-061): one licence reader, said at the choice, the accept's refusals

OFF_LIST = (
    "note: option A part 1 licence is not on the allowed list (setting: config/licences.toml); "
    "choosing it needs a project ADR that widens the list (principle 11)"
)
NO_ID = "FAIL engines: rule 5: option A part 1 has no licence id"


def with_part(root, licence, selection=""):
    text = GOOD_STACK.replace(
        "Parts: a 1.0 MIT. Practices: pinned actions, least",
        f"Parts: SQLite 3.47.1 {licence} (verify). Practices: pinned actions, least",
    )
    if selection:
        text = text.replace("2. **Practices**\n", f"2. **Practices**\n   - {selection}\n")
    return stack_root(root, text)


def test_req061_a_part_off_the_list_passes_and_is_said_off_the_list(started):
    """REQ-061: brief #1785 answers 1 and 2 (a note, never a failure); brief #1811 answer 7
    moves it from `blessing`, now on the default list, to `BUSL-1.1`, still off it."""
    proc = engines(with_part(started, "BUSL-1.1"), "stack-check")
    assert proc.returncode == 0, proc.stdout
    lines = proc.stdout.splitlines()
    assert lines[0] == "ok engines-stack" and OFF_LIST in lines
    assert "BUSL" not in proc.stdout  # principle 8: the note names no id


@pytest.mark.parametrize("licence", ["blessing", "Zlib", "BSL-1.0", "0BSD", "Unlicense"])
def test_req061_an_added_permissive_id_prints_no_note(started, licence):
    """REQ-061: brief #1811 answer 4 (no project list: the wider default, no off-list note)."""
    assert not (started / "config" / "licences.toml").exists()
    proc = engines(with_part(started, licence), "stack-check")
    assert proc.returncode == 0 and "not on the allowed list" not in proc.stdout, proc.stdout


@pytest.mark.parametrize(
    "licence",
    [
        "curl",
        "GPL-2.0-or-later WITH Classpath-exception-2.0",
        "(MIT OR Apache-2.0)",
        "MIT+",
        "DocumentRef-a:LicenseRef-b",
        "bzip2-1.0.6",
    ],
)
def test_req061_real_spdx_forms_pass_the_form(started, licence):
    """REQ-061: brief #1785 answers 1 and 6 (the SPDX grammar, any case)."""
    proc = engines(with_part(started, licence), "stack-check")
    assert proc.returncode == 0 and "FAIL" not in proc.stdout, proc.stdout


@pytest.mark.parametrize("licence", ["see LICENSE", "(MIT OR Apache-2.0", "MIT OR", ""])
def test_req061_a_text_that_is_no_expression_still_fails(started, licence):
    """REQ-061: brief #1785 answer 6 (no id, unbalanced parentheses, a dangling operator)."""
    proc = engines(with_part(started, licence), "stack-check")
    assert proc.returncode == 1 and NO_ID in proc.stdout.splitlines(), proc.stdout


def test_req061_a_project_list_holding_the_id_prints_no_note(started):
    """REQ-061: brief #1785 answer 5 (the project's list, compared case-folded)."""
    (started / "config").mkdir(exist_ok=True)
    (started / "config" / "licences.toml").write_text('allowed = ["MIT", "busl-1.1"]\n', "utf-8")
    proc = engines(with_part(started, "BUSL-1.1"), "stack-check")
    assert proc.returncode == 0 and "not on the allowed list" not in proc.stdout, proc.stdout


def test_req061_a_list_not_of_its_form_is_said_once(started):
    """REQ-061: brief #1785 answer 5 (one note naming the setting, no per-part note)."""
    (started / "config").mkdir(exist_ok=True)
    (started / "config" / "licences.toml").write_text('allowed = "MIT"\n', "utf-8")
    proc = engines(with_part(started, "blessing"), "stack-check")
    form = "note: the allowed list is not of its form (setting: config/licences.toml)"
    assert proc.returncode == 0 and proc.stdout.splitlines().count(form) == 1, proc.stdout
    assert "not on the allowed list" not in proc.stdout


TWO = "test selection: judgement (Option A: profile fast profile thorough; Option B: profile fast)"
ONE = "test selection: judgement (Option A: profile fast; Option B: profile fast)"


def accept_root(root, text_root):
    git = ["git", "-C", str(root)]
    subprocess.run([*git, "add", "-A"], check=True, capture_output=True)
    subprocess.run([*git, "commit", "-q", "-m", "record"], check=True, capture_output=True)
    subprocess.run([*git, "switch", "-q", "-c", "stack/accept"], check=True, capture_output=True)
    return text_root


@pytest.mark.parametrize(
    ("selection", "toml", "refusal"),
    [
        (TWO, None, "rule 5: the test selection practice names no one profile for option A"),
        (ONE, "x = [\n", "rule 5: agk.toml cannot be read (setting: testing)"),
    ],
)
def test_req061_the_check_names_the_refusal_the_accept_gives(started, selection, toml, refusal):
    """REQ-061: brief #1785 answer 3 (the check says it first; the accept refuses with it)."""
    root = with_part(started, "MIT", selection)
    if toml is not None:
        (root / "agk.toml").write_text(toml, encoding="utf-8")
    check = engines(root, "stack-check")
    assert check.returncode == 0, check.stdout
    assert f"note: option A cannot be accepted: {refusal}" in check.stdout.splitlines()
    if toml is None:  # option B names one profile; an unreadable agk.toml refuses both
        assert "option B cannot be accepted" not in check.stdout
    if toml is not None:  # an unreadable agk.toml stops the accept earlier, at its branch check
        return
    accept = engines(accept_root(root, root), "stack-accept", "--option", "A", "--reason", "r")
    assert accept.returncode == 1 and refusal in accept.stdout + accept.stderr, accept.stdout


def test_req061_a_chosen_line_the_accept_cannot_rewrite_is_named_first(started):
    """REQ-061: brief #1785 answer 3 (a hand-written `Chosen` on its own line)."""
    root = with_part(started, "MIT", ONE)
    path = root / "docs" / "adr" / "0002-stack-options.md"
    text = path.read_text("utf-8").replace("3. **Chosen**: none yet", "3. **Chosen**:\n   none yet")
    path.write_text(text, encoding="utf-8")
    refusal = "rule 5: the accepted stack ADR would fail stack-check"
    check = engines(root, "stack-check")
    assert check.returncode == 0, check.stdout
    assert f"note: option A cannot be accepted: {refusal}" in check.stdout.splitlines()
    accept = engines(accept_root(root, root), "stack-accept", "--option", "A", "--reason", "r")
    assert accept.returncode == 1 and refusal in accept.stdout + accept.stderr


# The accept's refusals that do not depend on the record: its arguments, the branch and the tree,
# and a record the check itself fails. Every other refusal must come through `accept_problems`.
NOT_RECORD = (
    "the option to accept is A, B or C",
    "the reason is one line",
    "the work tree is not clean",
    "there is not exactly one stack ADR",
    "is not a Proposed record that passes stack-check",
    "is not an option of the stack ADR",
)


def refusal_texts(tree, name):
    import ast  # noqa: PLC0415 - only this test reads the source

    func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    out = []
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "CheckError":
            parts = [c.value for c in ast.walk(node) if isinstance(c, ast.Constant)]
            out.append("".join(p for p in parts if isinstance(p, str)))
    return func, out


def test_req061_every_record_refusal_of_the_accept_is_named_by_the_check():
    """REQ-061: brief #1785 answer 3 (a new refusal cannot be added to the accept alone)."""
    import ast  # noqa: PLC0415 - only this test reads the source

    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    checker, _ = refusal_texts(tree, "accept_problems")
    source = ast.unparse(checker)
    calls = {getattr(n.func, "id", "") for n in ast.walk(checker) if isinstance(n, ast.Call)}
    assert "testing_copy" in calls  # each refusal of testing_copy reaches the check
    _, texts = refusal_texts(tree, "cmd_stack_accept")
    assert texts
    for text in texts:
        assert any(n in text for n in NOT_RECORD) or text in source, text
    notes, _ = refusal_texts(tree, "accept_notes")
    assert "accept_problems" in ast.unparse(notes)
    stack_check, _ = refusal_texts(tree, "cmd_stack_check")
    assert "accept_notes" in ast.unparse(stack_check)


def test_req061_a_project_list_of_the_old_six_still_notes_blessing(started):
    """REQ-061: brief #1811 answer 2 (a project's own list decides the note, unchanged)."""
    (started / "config").mkdir(exist_ok=True)
    six = '"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "PSF-2.0"'
    (started / "config" / "licences.toml").write_text(f"allowed = [{six}]\n", "utf-8")
    proc = engines(with_part(started, "blessing"), "stack-check")
    assert proc.returncode == 0 and OFF_LIST in proc.stdout.splitlines(), proc.stdout
