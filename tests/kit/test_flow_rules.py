"""The session rules and the conductor role for parallel builders (SPEC-0034 rules 7b, 7c and 11).

The rules file requires `push-check` before every push, lists the shared-mechanical files, lets a
session resolve only a mechanical conflict and otherwise stop with one comment, and gives the two
shapes of what a session puts on its pull request; the conductor role reads and answers them.
Text only. No network. REQ-041 AC7.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def rules() -> str:
    return (ROOT / "config" / "session-rules.md").read_text(encoding="utf-8")


def conductor() -> str:
    return (ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")


def test_ac7_the_rules_are_numbered_without_a_gap():
    """REQ-041 AC7"""
    numbers = [int(line.split(".")[0]) for line in rules().splitlines() if line[:1].isdigit()]
    assert numbers == list(range(1, len(numbers) + 1)) and len(numbers) >= 15


def test_ac7_the_rules_require_push_check_before_every_push_and_a_merge_not_a_rebase():
    """REQ-041 AC7: rule 7b."""
    text = rules()
    for phrase in (
        "python3 scripts/agk/session.py push-check",
        "before every push",
        "merges the default branch first",
        "never rebases or force-pushes",
    ):
        assert phrase in text, phrase


def test_ac7_the_rules_list_the_shared_mechanical_files_and_the_release_file():
    """REQ-041 AC7: rule 7a and the residual (the maintainers own the list)."""
    text = rules()
    for phrase in (
        "shared-mechanical",
        "marked `merge=union` in `.gitattributes`",
        "`changelog.d/`",
        "`kit/hashes.json` is a release file that a build never edits",
    ):
        assert phrase in text, phrase


def test_ac7_a_session_resolves_only_a_mechanical_conflict_and_otherwise_stops_with_one_comment():
    """REQ-041 AC7: rule 7c."""
    text = rules()
    for phrase in (
        "resolves only a mechanical conflict",
        "an appended line in a shared-mechanical file",
        "a file that a kit script regenerates",
        "a number moved by `intake.py renumber`",
        "a session rule number moved to the next free one",
        "`conflict needs a person: <files>`",
        "and pushes nothing",
    ):
        assert phrase in text, phrase


def test_ac7_the_rules_give_the_shapes_of_question_and_report_and_the_answer():
    """REQ-041 AC7: rule 11."""
    text = rules()
    for phrase in (
        "`Question: Q-<id> <text>`",
        "`Report: <head> <what changed and the CI>`",
        "on its pull request",
        "answers only by a `Verdict:` comment that names the head",
        "restarts `watch` after every push and every event",
        "no person carries messages",
    ):
        assert phrase in text, phrase


def test_ac7_the_rules_name_no_project_and_no_launcher():
    """REQ-041 AC7: generic text."""
    lowered = rules().lower()
    assert "gbvraju" not in lowered and "launcher" not in lowered
    assert not re.search(r"#\d{2,}", rules()), "a rule names an issue or pull request number"


def test_ac7_the_conductor_reads_question_and_report_comments_and_answers_each_by_a_verdict():
    """REQ-041 AC7: rule 11 (the role file)."""
    text = conductor()
    for phrase in (
        "read the `Question:` and `Report:` comments there",
        "answer each by a verdict",
        "puts its questions and reports on its pull request",
    ):
        assert phrase in text, phrase
    assert "never merge" in text and "edit no file" in text  # the limits are as before


def test_ac4_the_rules_say_where_each_comment_lives_and_that_a_builder_never_ends_silently():
    """REQ-041 AC4: the hand-off design (rule 17)."""
    text = rules()
    for phrase in (
        "Each comment lives in one place",
        "On the pull request: `Report:`, `Question:` and `Verdict:`",
        "On the brief: `taken: <id> <date> [build (<x>)]` and `released: <id> [build (<x>)]`",
        "labelled `agk-conductor`: `Request:` and `Assign:`",
        "A builder never ends silently",
        "a `Report:`, a `released:` or a `Request:`",
    ):
        assert phrase in text, phrase


def test_ac5_the_rules_give_the_hand_off_of_a_finished_builder():
    """REQ-041 AC5: rule 18."""
    text = rules()
    for phrase in (
        "session.py claim --session ID --brief N --build X",
        "refuses a build that a live take holds",
        "session.py after --session ID",
        '`assign = "next"`',
        '`assign = "conductor"`',
        "`Request: <id> finished #<brief>` or `Request: <id> new`",
        "session.py watch --assign ID",
        "by a listed verdict author",
        "`Assign: <id> none` and `assign-timeout` end the session",
        "starts nothing on its own",
    ):
        assert phrase in text, phrase


def test_ac5_the_conductor_answers_each_request_with_one_assign_line():
    """REQ-041 AC5: the role file."""
    text = " ".join(conductor().split())
    for phrase in (
        "labelled `agk-conductor`",
        "read each `Request:` comment there",
        "`Assign: <session> #<brief> build (<x>)`",
        "`Assign: <session> none`",
    ):
        assert phrase in text, phrase
