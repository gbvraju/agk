"""session.py prompt: the builder's standing prompt from the kit's files (brief #700, ADR-0330).

REQ-037. `python3 scripts/agk/session.py prompt --brief N [--session ID] [--follow-up TEXT]`
prints the prompt a project's scheduled builder is fired with: the item line with the brief's
reserved numbers (its `Reserved:` lines and the `reserves` of its takes, read with one GET each),
the files to read first, the secret-scan deferral line of `prepush.py`, the session rules that bind
a builder quoted from `config/session-rules.md`, and the body lines of CLAUDE.md item 7 read from
`config/core-rules.md`; nothing is copied by hand. A `gh` stub serves the brief; no network, GET
only, nothing posted."""

from __future__ import annotations

import sys

import pytest
from test_session import REPO, SCRIPTS, Stub, clean_env, comment, session

sys.path.insert(0, str(SCRIPTS))

import prepush  # noqa: E402

RULES = """# Session rules

1. A session acts only on a verdict.
2. A session never merges, never tags.
3. A session has one open pull request.
7. A builder commits a `checkpoint:` at every step
   and pushes at the milestones.
8. At each push the builder posts one `Progress:` comment.
9. A stalled pull request is resumed.
17. Each comment lives in one place.
21. A session stops and asks.
27. Every body has one `Summary:` line.
28. The last pull request carries `Finishes:`.
31. A session runs push-check before every push.
33. A session checks for a pause first.
34. A bug the brief does not cover is filed.
36. A build of an Approved spec writes no ADR of its own.
"""
CORE = """# Core rules

## CLAUDE.md items

1. You implement; you never decide.
7. PR body: `Advances: REQ-…`, `Build-state row:` (you never edit `docs/build-state.md` in a feature PR),
   `Decisions taken:`, `Questions:`, `Verified:` (commands and verbatim counts).
8. No token listed in config/neutrality.txt appears in tracked files.
"""
BRIEF = {
    "number": 9,
    "title": "A brief",
    "body": 'Sentence: "x"\n\nAnswers:\n1. a\n\nReserved: ADR-0330.\n\nAdvances: REQ-037\n',
    "labels": [{"name": "agk-brief"}],
}


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/session-rules.md", RULES)
    repo.write("config/core-rules.md", CORE)
    stub.serve(f"repos/{REPO}/issues/9", BRIEF)
    stub.serve(f"repos/{REPO}/issues/9/comments", [])
    return repo


def prompt(proj, stub, *args: str) -> str:
    out = session(proj, stub, "prompt", *args)
    assert out.returncode == 0, out.stdout + out.stderr
    assert all(c[0] == "GET" for c in stub.calls())
    return out.stdout


def test_the_prompt_names_the_repository_the_item_and_its_reserved_numbers(proj, stub):
    text = prompt(proj, stub, "--brief", "9")
    assert text.startswith(f"You are an AGK builder session. Repository: {REPO}")
    assert "Item: brief #9. Reserved: ADR-0330." in text
    assert "Session name:" not in text
    assert "A brief" not in text  # the title of a brief is data from an issue, never in a prompt


def test_the_session_name_is_in_the_item_line_when_given(proj, stub):
    text = prompt(proj, stub, "--brief", "9", "--session", "b9")
    assert "Session name: b9. Item: brief #9. Reserved: ADR-0330." in text


def test_the_reserved_numbers_come_from_the_body_and_the_takes(proj, stub):
    stub.serve(
        f"repos/{REPO}/issues/9/comments",
        [comment(1, "builder", "taken: b9 2026-11-06 reserves REQ-060, SPEC-0051, ADR-0330")],
    )
    text = prompt(proj, stub, "--brief", "9")
    assert "Reserved: REQ-060, SPEC-0051, ADR-0330." in text


def test_a_brief_with_no_reserved_number_says_none(proj, stub):
    stub.serve(f"repos/{REPO}/issues/9", {**BRIEF, "body": "Sentence: \"x\"\nAdvances: REQ-037\n"})
    assert "Item: brief #9. Reserved: none." in prompt(proj, stub, "--brief", "9")


def test_the_prompt_carries_the_secret_scan_line_of_prepush(proj, stub):
    text = prompt(proj, stub, "--brief", "9")
    assert f"`{prepush.DEFER_LINE}`" in text
    assert "python3 scripts/agk/prepush.py --body" in text


def test_the_prompt_quotes_the_builder_rules_from_the_session_rules_file(proj, stub):
    text = prompt(proj, stub, "--brief", "9")
    assert "7. A builder commits a `checkpoint:` at every step and pushes at the milestones." in text
    for n in (2, 3, 8, 17, 21, 27, 28, 31, 33, 34, 36):
        assert f"\n{n}. " in text, n
    assert "1. A session acts only on a verdict." not in text
    assert "9. A stalled pull request is resumed." not in text


def test_the_prompt_lists_the_body_lines_of_claude_md_item_7_from_core_rules(proj, stub):
    text = prompt(proj, stub, "--brief", "9")
    assert (
        "`Brief: #9`, `Advances: REQ-…`, `Build-state row:`, `Decisions taken:`, `Questions:`, "
        "`Verified:`"
    ) in text
    assert "`Summary:`" in text


def test_the_prompt_reads_the_files_in_order_and_the_brief_with_its_comments(proj, stub):
    text = prompt(proj, stub, "--brief", "9")
    order = [
        "CLAUDE.md",
        "constitution/principles.md",
        "config/core-rules.md",
        "config/session-rules.md",
        f"gh api repos/{REPO}/issues/9",
        "docs/runs/decisions/",
    ]
    places = [text.index(x) for x in order]
    assert places == sorted(places)
    assert "Decisions taken:" in text


def test_a_follow_up_overrides_the_stop_on_an_existing_pull_request(proj, stub):
    text = prompt(proj, stub, "--brief", "9")
    assert "If an open pull request from branch `claude/brief-9` already exists" in text
    text = prompt(proj, stub, "--brief", "9", "--follow-up", "merge main and fix the lint")
    assert "Follow-up for the open pull request of branch `claude/brief-9`:" in text
    assert "merge main and fix the lint" in text
    assert "already exists" not in text


def test_a_rule_the_project_file_lacks_is_noted_and_the_rest_are_printed(proj, stub):
    proj.write("config/session-rules.md", "# Session rules\n\n2. A session never merges.\n")
    out = session(proj, stub, "prompt", "--brief", "9")
    assert out.returncode == 0
    assert "\n2. A session never merges." in out.stdout
    assert "note: session rule 7 is not in config/session-rules.md" in out.stderr


def test_a_core_rules_file_without_item_7_fails(proj, stub):
    proj.write("config/core-rules.md", "# Core rules\n\n1. You implement.\n")
    out = session(proj, stub, "prompt", "--brief", "9")
    assert out.returncode == 2
    assert "item 7" in out.stdout


def test_a_brief_that_cannot_be_read_fails(proj, stub):
    stub.serve(f"repos/{REPO}/issues/9", "FAIL")
    out = session(proj, stub, "prompt", "--brief", "9")
    assert out.returncode == 2
    assert "cannot be read" in out.stdout


def test_a_follow_up_is_one_line_and_never_a_verdict(proj, stub):
    for text in ("two\nlines", "", "Verdict: cleared abc1234", "Confirmed: yes"):
        out = session(proj, stub, "prompt", "--brief", "9", "--follow-up", text)
        assert out.returncode == 2, text
        assert text.splitlines()[:1] == [] or text.splitlines()[0] not in out.stdout


@pytest.mark.parametrize(
    "args",
    [
        ["prompt"],
        ["prompt", "--brief"],
        ["prompt", "--brief", "x"],
        ["prompt", "--brief", "9", "--session", "a b"],
        ["prompt", "--brief", "9", "--take"],
        ["prompt", "--brief", "9", "--pr", "7"],
    ],
)
def test_any_other_form_is_a_usage_error(proj, stub, args):
    out = session(proj, stub, *args)
    assert out.returncode == 2
    assert "prompt --brief N" in out.stdout
    assert stub.calls() == []


def test_the_prompt_is_the_same_text_for_the_same_brief(proj, stub):
    assert prompt(proj, stub, "--brief", "9") == prompt(proj, stub, "--brief", "9")
    assert clean_env()  # the stub, not the network, answered both reads
