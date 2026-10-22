"""Kit-only tests of the review agent, the protocol and the checklist (SPEC-0023 rules 1 to 5)."""

from __future__ import annotations

import json
import re

import pytest
from conftest import KIT_ROOT, manifest

AGENTS = KIT_ROOT / ".claude" / "agents"
DECIDER = AGENTS / "architect.md"
REVIEW = AGENTS / "architect-review.md"
TEMPLATE = KIT_ROOT / "kit" / "templates" / "playbook" / "verdict.md"
CHECKLIST = KIT_ROOT / "config" / "review-checklist.md"
CATCHES = sorted((KIT_ROOT / "docs" / "runs").glob("architect-catches-*.md"))
PROTOCOL = re.compile(r"<!-- protocol -->\n(.*?)<!-- /protocol -->", re.S)
STEPS = [
    ("Fetch the head", ["verdict's first line names that sha", "another sha is void"]),
    ("Read the diff", ["`Read:`"]),
    ("Walk the spec's rules", ["`holds`", "`does not hold (where)`", "`not testable here`"]),
    ("Run what can be run", ["`(verify)`"]),
    ("Say what the tests do not prove", ["what a passing test would still allow"]),
    ("The fixed lens", ["security", "honesty", "portability", "size", "duplication"]),
    ("Kit or project?", ["`project:`", "`kit:`"]),
    ("The verdict form", ["`Verdict: cleared <sha>`", "`Verdict: fix list <sha>`", "`Final:`"]),
    ("Own the misses", ["decisions log"]),
]
SHAPE = ["Read:", "Rules:", "Not proven:", "Lens:", "Gaps:", "Checklist:"]


def head(path) -> str:
    return path.read_text(encoding="utf-8").split("---\n", 2)[1]


def protocol(path) -> str:
    found = PROTOCOL.search(path.read_text(encoding="utf-8"))
    assert found, path.name
    return found.group(1)


def test_ac1_the_review_agent_has_exactly_the_read_tools_and_the_review_guard():
    """REQ-030 AC1: rules 1 and 2 (no Edit, no Write; the hook runs in review mode)."""
    front = head(REVIEW)
    assert re.search(r"(?m)^name: architect-review$", front)
    assert re.search(r"(?m)^tools: Read, Grep, Glob, Bash$", front)
    assert "PreToolUse:" in front and "architect_guard.py --review" in front
    assert re.search(r"matcher: \"Edit\|Write\|MultiEdit\|NotebookEdit\|Bash\"", front)


def test_ac1_the_review_agent_forbids_editing_building_merging_and_a_commit():
    """REQ-030 AC1: rule 2 (the prohibitions of the file; the verdict is a comment)."""
    body = REVIEW.read_text(encoding="utf-8")
    for needle in (
        "Never edit a file of the project",
        "never build",
        "never merge, enable auto-merge",
        "never review in the session that built the change",
        "The builder's report is not evidence",
        "a comment, never a commit",
        "Never execute the pull request's code",
    ):
        assert needle in body, needle


def test_ac2_both_files_carry_the_same_nine_steps_in_order():
    """REQ-030 AC2: rules 1 and 3 (word for word; each step in order with its key words)."""
    assert protocol(DECIDER) == protocol(REVIEW)
    text = protocol(REVIEW)
    numbered = re.findall(r"(?m)^(\d)\. ", text)
    assert numbered == [str(n) for n in range(1, 10)]
    position = 0
    for title, words in STEPS:
        at = text.index(title, position)
        position = at
        step = text[at : text.find("\n\n", at) if "\n\n" in text[at:] else None]
        for word in words:
            assert word in step or word in text[at : at + 700], (title, word)


def test_ac2_the_lens_is_in_the_fixed_order():
    """REQ-030 AC2: rule 3 step 6."""
    lens = protocol(REVIEW).split("The fixed lens", 1)[1].split("Kit or project?", 1)[0]
    order = [lens.index(w) for w in ("security", "honesty", "portability", "size", "duplication")]
    assert order == sorted(order)


def test_ac2_the_deciding_architect_still_writes_only_under_docs_and_the_vision():
    """REQ-030 AC2: rule 1 (tools, hook and prohibitions unchanged)."""
    front = head(DECIDER)
    assert re.search(r"(?m)^name: architect$", front)
    assert re.search(r"(?m)^tools: Read, Grep, Glob, Edit, Write, Bash$", front)
    assert "architect_guard.py" in front and "--review" not in front
    assert "Write a file outside `docs/` and `constitution/vision.md`" in DECIDER.read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("path", [DECIDER, REVIEW, TEMPLATE])
def test_ac3_the_files_name_the_lines_of_a_verdict(path):
    """REQ-030 AC3: rule 4 (first line, Read, Rules, Not proven, Lens, Gaps, Checklist)."""
    text = path.read_text(encoding="utf-8")
    positions = [text.index(line) for line in SHAPE]
    assert positions == sorted(positions), path.name
    assert "Verdict: cleared" in text and "five" in text.lower()


def test_ac3_the_template_first_line_still_matches_the_verdict_rule():
    """REQ-030 AC3: rule 4 (SPEC-0007 rule 4 is unchanged)."""
    import sys

    sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))
    import metrics

    first = TEMPLATE.read_text(encoding="utf-8").splitlines()[0].replace("{{sha}}", "abc1234")
    assert metrics.VERDICT.fullmatch(first)


def kinds_of_the_catch_log() -> list[str]:
    text = CATCHES[-1].read_text(encoding="utf-8")
    paragraph = text.split("Kinds (fixed list):", 1)[1].split("(a fact", 1)[0]
    return re.findall(r"`([a-z-]+)`", paragraph)


def questions() -> list[str]:
    return re.findall(r"(?m)^\d+\. (.*)$", CHECKLIST.read_text(encoding="utf-8"))


def test_ac4_the_checklist_has_one_question_per_kind_of_the_catch_log_and_at_most_fifteen():
    """REQ-030 AC4: rule 5 (grown from evidence only)."""
    kinds = kinds_of_the_catch_log()
    assert len(kinds) >= 12 and CATCHES
    found = questions()
    assert 1 <= len(found) <= 15
    named = [re.match(r"`([a-z-]+)`", q) for q in found]
    assert all(named), "every question names its kind first"
    assert [m.group(1) for m in named] == kinds


def test_ac4_the_checklist_states_its_change_rule_and_is_installed_verbatim():
    """REQ-030 AC4: rule 5 (a decision record that cites a row of a catch log)."""
    text = CHECKLIST.read_text(encoding="utf-8")
    assert "cites a row of a catch log" in text and "from opinion" in text
    assert "with evidence or `n/a`" in text
    assert "config/review-checklist.md" in manifest()["verbatim"]


def test_ac4_the_new_files_are_installed_verbatim_and_named_in_the_hashes():
    """REQ-030 AC1 and AC4: rule 1 (both files are in the manifest and the hashes)."""
    listed = manifest()["verbatim"]
    assert ".claude/agents/architect-review.md" in listed
    hashes = json.loads((KIT_ROOT / "kit" / "hashes.json").read_text(encoding="utf-8"))
    assert ".claude/agents/architect-review.md" in json.dumps(hashes)


@pytest.mark.parametrize("path", [REVIEW, CHECKLIST, TEMPLATE])
def test_ac2_the_files_name_no_project_and_no_plugin_variable(path):
    """REQ-030 AC2: SPEC-0005 rule 2 and the genericity of SPEC-0023."""
    text = path.read_text(encoding="utf-8")
    assert "CLAUDE_PLUGIN" not in text and "/agk:" not in text
    for word in ("cloudflare", "slack", "dashboard"):
        assert word not in text.lower(), word
