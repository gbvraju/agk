"""Kit-only tests of `/agk:confirm` and the guide line of solo mode (brief 277, ADR-0179; REQ-039).

Brief #1692 (ADR-0705, ADR-0661 build (c); REQ-069): the skill, the steward's role file and the
voice guide name the natural path, one question and a yes that the steward posts with
`steward_owner.py approve`, and the words of each setting it depends on.

`skills/` is not vendored into a project, so these tests live in `tests/kit_dev/`."""

from __future__ import annotations

from conftest import KIT_ROOT

SKILL = KIT_ROOT / "skills" / "confirm" / "SKILL.md"
GUIDE = KIT_ROOT / "docs" / "guides" / "getting-started.md"
REFERENCE = KIT_ROOT / "docs" / "guides" / "reference.md"
STEWARD = KIT_ROOT / ".claude" / "agents" / "steward.md"
VOICE = KIT_ROOT / "docs" / "guides" / "steward-voice.md"
# brief #1692 answer 5: the words of each setting, in every file that names the natural path
SETTINGS = ('review_mode = "solo"', "agent_apps", "personal mode")


def flat(path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_the_skill_prints_the_confirmation_and_never_posts_it():
    """REQ-039: brief #277 (the verdict on f58803a, condition 1)."""
    text = flat(SKILL)
    assert "disable-model-invocation: true" in text
    for phrase in (
        "the person posts it, never the session",
        "session rule 29",
        "Confirmed: <the full head ID>",
        "Verdict: <kind> <the same full head ID>",
        "Shown:",
        "confirmed by <the person's login> in a session at",
        "from the browser or the GitHub app",
        "The print path writes no file and posts nothing.",
    ):
        assert phrase in text, phrase
    assert "--method POST" not in text and "-X POST" not in text


def test_the_guide_says_the_person_posts_it_and_re_runs_governance():
    """REQ-039: brief #277 (the verdict on f58803a, item 3: the one guide line)."""
    text = flat(GUIDE)
    assert "/agk:confirm" in text and "you post it yourself" in text
    # brief #1692 (fix list on 9ceea87 item 1): the steward's natural path, then the print path
    assert "on your plain yes in the chat, posts that comment" in text
    assert "the steward alone, session rule 29" in text and "(no other session posts it)" in text
    assert "a session never does" not in text
    assert "re-run the governance check or push" in text
    assert "| `/agk:confirm` |" in REFERENCE.read_text(encoding="utf-8")


def section(path, heading: str) -> str:
    """The flattened body of the `## HEADING` section of PATH."""
    body = path.read_text(encoding="utf-8").split(f"\n## {heading}\n", 1)[1]
    return " ".join(body.split("\n## ", 1)[0].split())


def test_req069_the_skill_opens_with_the_natural_path():
    """REQ-069: brief #1692 answer 2: the natural path comes first; printing is the fallback."""
    text = SKILL.read_text(encoding="utf-8")
    assert text.split("\n## ", 2)[1].startswith("The natural path\n")
    path = section(SKILL, "The natural path")
    for words in (
        "steward_owner.py ask --target",
        "steward_owner.py approve",
        "paste",
        "prefers to post it",
        *SETTINGS,
    ):
        assert words in path, words
    assert "Never posts it" not in text


def test_req069_the_steward_names_the_one_approval_path():
    """REQ-069: brief #1692 answer 1: the role file's owner paragraph and its Never aside."""
    text = flat(STEWARD)
    for words in ("ask --target", "approve", "paste", *SETTINGS):
        assert words in text, words
    aside = (
        "(in solo mode, the `Approve:` and `Confirmed:` lines that `steward_owner.py approve`"
        " writes on a recorded yes aside, session rule 29)"
    )
    assert aside in text


def test_req069_the_voice_guide_shows_the_question_and_the_reply_after_a_yes():
    """REQ-069: brief #1692 answer 3: two examples, the one question and the reply after a yes."""
    body = section(VOICE, "One question, one yes")
    for words in ("steward_owner.py ask --target", "steward_owner.py approve", "https://"):
        assert words in body, words
    for words in SETTINGS:
        assert words in body, words
    assert body.count("Example") >= 2
    assert "Posted" in body and "paste this one line" in body
