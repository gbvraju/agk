"""Kit-only tests of discovery before design (SPEC-0023 rules 6 and 7; REQ-030 AC5 and AC6).

`/agk:start` asks about six topics before the charter; `playbook.py check-start` refuses a start
whose charter lacks the Discovery item, a topic, an answer, or the Slice bullet of a topic answered
`not known yet`. A charter written before this change is not checked again. No model, no network.
"""

from __future__ import annotations

import re

import pytest
from conftest import KIT_ROOT
from test_playbook import GOOD_CHARTER, GOOD_VISION, check_start, failed, good_start
from test_playbook import started as playbook_started  # noqa: F401  (wrapped below)

SKILL = KIT_ROOT / "skills" / "start" / "SKILL.md"
TOPICS = ("users", "existing", "runs", "data", "scale", "compliance")
ANSWERS = {
    "users": "readers, who pay nothing",
    "existing": "one public repository",
    "runs": "a laptop, not portable",
    "data": "saved items, kept for a year",
    "scale": "one reader",
    "compliance": "none",
}
TAIL = "2. **Non-goals**"


@pytest.fixture
def started(request):
    return request.getfixturevalue("playbook_started")


def charter_with(answers=None, slice_lines=None, topics=TOPICS, gap=""):
    """GOOD_CHARTER with Discovery (and Slice) items as numbered items 1 and 2 of the Decision."""
    answers = {**ANSWERS, **(answers or {})}
    discovery = "".join(f"   - {t}: {answers[t]}\n" for t in topics)
    items = f"1. **Discovery**\n{discovery}"
    if slice_lines is not None:
        items += "2. **Slice**\n" + "".join(f"   - {ln}\n" for ln in slice_lines)
    text = re.sub(r"4\. \*\*Discovery\*\*\n(?:   - .*\n)+", "", GOOD_CHARTER)
    text = text.replace("1. **Milestones**", "3. **Milestones**")
    text = text.replace("2. **Non-goals**", "4. **Non-goals**")
    text = text.replace("3. **Done means**", "5. **Done means**")
    return text.replace("## Decision\n\n", f"## Decision\n\n{items}") + gap


def test_ac5_a_start_with_all_six_topics_answered_passes(started):
    """REQ-030 AC5: rules 6 and 7 (the six topics in order, no Slice item needed)."""
    good_start(started, charter=charter_with())
    assert check_start(started).stdout == "ok playbook-start\n"


def test_ac5_a_charter_without_the_discovery_item_fails(started):
    """REQ-030 AC5: rule 7 (the old charter shape is refused on a start)."""
    good_start(started, charter=charter_with().replace("**Discovery**", "**Findings**"))
    failed(started, "Discovery")


@pytest.mark.parametrize("topic", TOPICS)
def test_ac5_a_missing_topic_fails_and_the_message_names_it(started, topic):
    """REQ-030 AC5: rule 7 (one of the six topics is missing)."""
    good_start(started, charter=charter_with(topics=[t for t in TOPICS if t != topic]))
    out = failed(started, "rule 6")
    assert topic in out


@pytest.mark.parametrize("topic", TOPICS)
def test_ac5_a_topic_without_an_answer_fails(started, topic):
    """REQ-030 AC5: rule 7 (the bullet has no answer)."""
    good_start(started, charter=charter_with(answers={topic: ""}))
    out = failed(started, "no answer")
    assert topic in out


def test_ac5_the_topics_must_come_in_the_order_of_rule_6(started):
    """REQ-030 AC5: rule 6 (users, existing, runs, data, scale, compliance)."""
    good_start(started, charter=charter_with(topics=("existing", "users", *TOPICS[2:])))
    failed(started, "order")


def test_ac5_not_known_yet_without_its_slice_line_fails(started):
    """REQ-030 AC5: rule 7 (the Slice bullet of a topic answered not known yet)."""
    good_start(started, charter=charter_with(answers={"scale": "not known yet"}))
    out = failed(started, "Slice")
    assert "scale" in out
    good_start(
        started,
        charter=charter_with(
            answers={"scale": "not known yet"}, slice_lines=["users: nobody can sign in"]
        ),
    )
    failed(started, "Slice")


def test_ac5_not_known_yet_with_its_slice_line_passes(started):
    """REQ-030 AC5: rule 7 (an allowed answer, with what breaks if it is wrong)."""
    good_start(
        started,
        charter=charter_with(
            answers={"scale": "Not known yet", "data": "not known yet"},
            slice_lines=["scale: the list is slow past a thousand items", "data: nothing is kept"],
        ),
    )
    assert check_start(started).stdout == "ok playbook-start\n"


def test_ac5_a_slice_bullet_for_a_known_topic_is_allowed(started):
    """REQ-030 AC5: rule 6 and Q-K4-226 (another topic may have a Slice bullet too)."""
    good_start(started, charter=charter_with(slice_lines=["compliance: audit fails later"]))
    assert check_start(started).stdout == "ok playbook-start\n"


@pytest.mark.parametrize("line", ["colour: it is ugly", "scale:", "scale:   "])
def test_ac5_a_slice_bullet_must_name_a_topic_and_say_a_sentence(started, line):
    """REQ-030 AC5: rule 6 (`- <topic>: <one sentence>`)."""
    good_start(started, charter=charter_with(slice_lines=[line]))
    failed(started, "Slice")


def test_ac6_an_old_charter_in_the_base_is_not_checked_again(started):
    """REQ-030 AC6: rule 7 (only the charter of the start is checked)."""
    from conftest import git

    old = started / "docs" / "adr" / "0002-project-charter.md"
    git(started, "switch", "-q", "main")
    old.write_text(charter_with().replace("**Discovery**", "**Findings**"), encoding="utf-8")
    git(started, "add", "-A")
    git(started, "commit", "-q", "-m", "an older charter, no Discovery")
    git(started, "switch", "-q", "-c", "start/second")
    (started / "constitution" / "vision.md").write_text(GOOD_VISION, encoding="utf-8")
    new = charter_with().replace("ADR-0002", "ADR-0003")
    (started / "docs" / "adr" / "0003-project-charter.md").write_text(new, encoding="utf-8")
    assert check_start(started).stdout == "ok playbook-start\n"


def test_ac6_no_other_script_reads_the_discovery_item():
    """REQ-030 AC6: rule 7 (`check-start` is the only check; nothing in governance reads it)."""
    hits = [
        p.name
        for p in sorted((KIT_ROOT / "scripts" / "agk").glob("*.py"))
        if "Discovery" in p.read_text(encoding="utf-8")
    ]
    assert hits == ["playbook.py"]


def test_ac5_messages_name_the_rule_and_the_topic_never_the_answer(started):
    """Principle 6: a refusal names the topic, never the answer text."""
    secret = "zebra-quartz-answer"
    good_start(started, charter=charter_with(answers={"users": secret}, topics=TOPICS[1:]))
    out = failed(started, "rule 6")
    assert secret not in out


def test_ac5_the_skill_asks_six_topics_in_order_at_most_three_questions_a_round():
    """REQ-030 AC5: rule 6 (only about open topics; Discovery and Slice items; not known yet)."""
    body = SKILL.read_text(encoding="utf-8")
    flat = " ".join(body.split())
    positions = [flat.index(f"`{t}`") for t in TOPICS]
    assert positions == sorted(positions)
    assert "at most three questions" in flat
    assert "leaves open" in flat
    for word in ("**Discovery**", "**Slice**", "not known yet"):
        assert word in body
    assert re.search(r"before the charter", flat)


def test_ac5_the_skill_still_writes_exactly_two_files_and_edits_no_principles():
    """REQ-030 AC5: SPEC-0013 rule 4 unchanged (discovery is a conversation, not a file)."""
    body = SKILL.read_text(encoding="utf-8")
    assert "Write exactly two files" in body and "constitution/principles.md" in body
    assert "disable-model-invocation: true" in body
