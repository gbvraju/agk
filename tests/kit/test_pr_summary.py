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


def test_ac1_the_template_asks_for_a_summary_and_unchanged_it_does_not_pass():
    """REQ-043 AC1: Q-K4-316, the verdict on 5699f52."""
    template = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    assert (
        "\nSummary:\n<!--" in template and "what the change does for a person, not how" in template
    )
    assert template.index("Advances:") < template.index("Summary:") < template.index("Build-state")
    out = check(template)
    assert out.returncode == 1 and "SPEC-0036 rule 1" in out.stdout
    filled = template.replace("\nSummary:\n", f"\nSummary: {SENTENCE}\n")
    assert "SPEC-0036 rule 1" not in check(filled).stdout


# --- the message says what it found (brief 237) --------------------------------------------------

RULE = "FAIL pr-body: SPEC-0036 rule 1: "


def lines_of(out: subprocess.CompletedProcess) -> list[str]:
    return [x for x in out.stdout.splitlines() if "SPEC-0036" in x]


def test_a_missing_summary_says_it_is_missing():
    """Brief 237 answer 1 and 3: no line."""
    out = check(BODY)
    assert lines_of(out) == [RULE + "the 'Summary:' line is missing"]


@pytest.mark.parametrize("count", [2, 3, 5])
def test_a_repeated_summary_says_how_many_lines_there_are(count):
    """Brief 237 answer 1 and 3: more than one, with the count."""
    out = check(BODY + f"Summary: {SENTENCE}\n" * count)
    assert lines_of(out) == [RULE + f"there are {count} 'Summary:' lines; exactly one is required"]


@pytest.mark.parametrize("line", ["Summary:", "Summary:   ", "Summary:\t"])
def test_an_empty_summary_says_it_is_empty(line):
    """Brief 237 answer 1 and 3: an empty one."""
    assert lines_of(check(BODY + line + "\n")) == [RULE + "the 'Summary:' line is empty"]


@pytest.mark.parametrize("length", [121, 156, 400])
def test_a_long_summary_says_how_many_characters_it_has_against_the_limit(length):
    """Brief 237 answer 1 and 3: the text after the label counts, the label does not."""
    out = check(BODY + "Summary: " + "x" * length + "\n")
    assert lines_of(out) == [
        RULE + f"the text after 'Summary:' is {length} characters; at most 120"
    ]


def test_the_limit_counts_the_text_after_the_label_and_not_the_label():
    """Brief 237 answer 1: the limit and what it counts stay as they are."""
    assert check(BODY + "Summary: " + "x" * 120 + "\n").returncode == 0
    assert check(BODY + "Summary:" + "x" * 120 + "\n").returncode == 0
    assert check(BODY + "Summary:   " + "x" * 120 + "   \n").returncode == 0
    assert check(BODY + "Summary: " + "x" * 121 + "\n").returncode == 1


def test_no_message_carries_a_sha_a_file_or_a_word_of_the_body():
    """Brief 237 answer 2: only the rule, the case and a count."""
    secret = "hunter2 a1b2c3d4e5f60718293a4b5c6d7e8f9012345678 docs/adr/0001-x.md " + "y" * 130
    for body in (
        BODY + f"Summary: {secret}\n",
        BODY + f"Summary: {secret}\nSummary: {secret}\n",
        BODY,
        BODY + "Summary:\n",
    ):
        out = check(body).stdout
        assert "hunter2" not in out and "a1b2c3d" not in out and "0001" not in out
        assert "yyy" not in out


def test_two_problems_are_both_reported_and_the_summary_one_names_its_case():
    """Brief 237: the other checks still report beside the summary."""
    out = check("Summary: " + "z" * 130 + "\n")
    assert RULE + "the text after 'Summary:' is 130 characters; at most 120" in out.stdout
    assert "Advances" in out.stdout and "Build-state" in out.stdout
