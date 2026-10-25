"""Kit-only test of the guide section "Running the loop" (SPEC-0030 rule 9; REQ-037 AC8)."""

from __future__ import annotations

import re

from conftest import KIT_ROOT

GUIDE = KIT_ROOT / "docs" / "guides" / "getting-started.md"


def section() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    found = re.search(r"(?ms)^## Running the loop\n(.*?)(?=^## |\Z)", text)
    assert found, "the guide has no section 'Running the loop'"
    return found.group(1)


def test_ac8_the_section_tells_how_to_start_each_role_and_where_to_merge_from():
    """REQ-037 AC8"""
    body = section()
    for phrase in (
        "python3 scripts/agk/session.py next --session",
        "claude --agent conductor",
        "python3 scripts/agk/session.py watch --pr",
        "Ready to merge",
        "check_brief.py",
        "agk-brief",
        "config/session-rules.md",
        "workspace trust dialog",
        "as a background task",
        "wakes the session",
        "never detached with `&`",
        "`label <name>`",
        "Approve: <head> SPEC-<n>",
        "spec_approvers",
        "python3 scripts/agk/session.py queue --role",
    ):
        assert phrase in body, phrase


def test_ac8_the_section_shows_the_shape_of_a_brief_with_one_example_that_passes(tmp_path):
    """REQ-037 AC8 (the example is checked by the script it names)"""
    import subprocess
    import sys

    body = section()
    example = re.search(r"(?ms)^```text\n(Sentence:.*?)^```", body)
    assert example, "the section has no example brief in a text block"
    path = tmp_path / "brief.md"
    path.write_text(example.group(1), encoding="utf-8")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "check_brief.py"), str(path)],
        capture_output=True,
        text=True,
    )
    assert (proc.returncode, proc.stdout) == (0, "ok brief\n")


def test_ac8_the_section_names_no_project_and_no_person():
    """REQ-037 AC8: generic text"""
    body = section().lower()
    assert "gbvraju" not in body and "agk-brief" in body


def test_ac7_the_section_states_what_happens_when_the_credits_run_out():
    """REQ-040 AC7 (rule 7 of SPEC-0033: the guide's statements)"""
    body = section()
    for phrase in (
        "Every session stops",
        "keeps running",
        "needs no model",
        "second budget",
        "Actions minutes on private repositories",
        "session.py resume",
        "since the previous `Report:` of the same pull request and not a running total",
        "subtracts the total it reported last",
    ):
        assert phrase in body, phrase
