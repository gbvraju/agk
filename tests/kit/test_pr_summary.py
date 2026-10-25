"""The `Summary:` line of every pull request body (SPEC-0036 rules 1 and 6; REQ-043 AC1 and AC7).

`check_pr_body.py` fails a body that is not a draft without one line `Summary: <sentence>` of 1 to
120 characters, naming the rule and never the text. The conductor's role file and the session rules
say the same. Files and stdin only. No network.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "agk" / "check_pr_body.py"
BODY = "Advances: REQ-001\nBuild-state row: 2026-10-25 REQ-001 planned, a change\n"
SENTENCE = "Reviews can no longer approve a spec on a person's behalf."


def check(body: str, *extra: str):
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *extra, "-"],
        input=body,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_ac1_a_body_with_one_plain_sentence_passes():
    """REQ-043 AC1"""
    out = check(BODY + f"Summary: {SENTENCE}\n")
    assert out.returncode == 0 and "ok pr-body" in out.stdout


@pytest.mark.parametrize("extra", [BODY + "Brief: #7\n", BODY])
def test_ac1_a_body_without_a_summary_fails_with_or_without_a_brief_line(extra):
    """REQ-043 AC1: rule 1 as ruled, every pull request body that is not a draft."""
    out = check(extra)
    assert out.returncode == 1 and "SPEC-0036 rule 1" in out.stdout and "Summary:" in out.stdout


@pytest.mark.parametrize("line", ["Summary:", "Summary:    ", "Summary:\t"])
def test_ac1_an_empty_summary_fails_and_the_message_names_the_rule_only(line):
    """REQ-043 AC1"""
    out = check(BODY + line + "\n")
    assert out.returncode == 1 and "SPEC-0036 rule 1" in out.stdout


def test_ac1_the_length_is_one_to_120_characters():
    """REQ-043 AC1"""
    assert check(BODY + "Summary: " + "a" * 120 + "\n").returncode == 0
    assert check(BODY + "Summary: a\n").returncode == 0
    long = "b" * 121
    out = check(BODY + f"Summary: {long}\n")
    assert out.returncode == 1 and "SPEC-0036 rule 1" in out.stdout and long not in out.stdout


def test_ac1_the_message_never_carries_the_summary_text():
    """REQ-043 AC1"""
    text = "x" * 121 + " secret words"
    out = check(BODY + f"Summary: {text}\n")
    assert out.returncode == 1 and "secret" not in out.stdout and "xxxx" not in out.stdout


def test_ac1_two_summary_lines_fail_because_the_summary_is_one_line():
    """REQ-043 AC1"""
    out = check(BODY + f"Summary: {SENTENCE}\nSummary: another sentence\n")
    assert out.returncode == 1 and "SPEC-0036 rule 1" in out.stdout


def test_ac1_an_indented_or_quoted_summary_is_not_the_line():
    """REQ-043 AC1"""
    assert check(BODY + f"  Summary: {SENTENCE}\n").returncode == 1
    assert check(BODY + f"> Summary: {SENTENCE}\n").returncode == 1


def test_ac1_a_draft_is_skipped_until_it_is_ready_for_review():
    """REQ-043 AC1"""
    out = check(BODY, "--draft", "true")
    assert out.returncode == 0 and "skipped" in out.stdout
    assert check(BODY, "--draft", "false").returncode == 1


def test_ac1_the_other_checks_still_report_beside_the_summary():
    """REQ-043 AC1"""
    out = check("Summary: " + SENTENCE + "\n")
    assert out.returncode == 1 and "Advances" in out.stdout and "Build-state" in out.stdout


# --- the role file and the session rules (rule 6) -------------------------------------------------


def words(rel: str) -> str:
    return " ".join((ROOT / rel).read_text(encoding="utf-8").split())


def test_ac7_the_conductor_gives_no_clearing_verdict_without_a_plain_summary():
    """REQ-043 AC7: rule 6."""
    text = words(".claude/agents/conductor.md")
    for phrase in (
        "a clearing verdict is not given while the `Summary:` line of the pull request is missing",
        "written for developers",
        "what the change does for a person",
    ):
        assert phrase in text, phrase


def test_ac1_the_session_rules_say_every_body_carries_a_summary_line():
    """REQ-043 AC1: the session rules."""
    text = words("config/session-rules.md")
    for phrase in (
        "Every pull request body that is not a draft has one line `Summary: <one plain sentence>`",
        "1 to 120 characters",
        "what the change does for a person, not how",
    ):
        assert phrase in text, phrase
