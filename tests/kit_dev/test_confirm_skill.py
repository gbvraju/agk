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
    assert "/agk:confirm" in text and "a session never does, session rule 29" in text
    assert "re-run the governance check or push" in text
    assert "| `/agk:confirm` |" in REFERENCE.read_text(encoding="utf-8")


def test_req069_the_skill_opens_with_the_natural_path():
    """REQ-069: brief #1692 answer 2: the natural path is the first section; printing is the fallback."""
    text = SKILL.read_text(encoding="utf-8")
    assert text.split("\n## ", 2)[1].startswith("The natural path\n")
    path = " ".join(text.split("\n## The natural path\n", 1)[1].split("\n## ", 1)[0].split())
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
    assert (
        "(in solo mode, the `Approve:` and `Confirmed:` lines that `steward_owner.py approve` writes"
        " on a recorded yes aside, session rule 29)"
    ) in text


def test_req069_the_voice_guide_shows_the_question_and_the_reply_after_a_yes():
    """REQ-069: brief #1692 answer 3: two examples, the one question and the reply after a yes."""
    text = VOICE.read_text(encoding="utf-8")
    section = " ".join(text.split("\n## One question, one yes\n", 1)[1].split("\n## ", 1)[0].split())
    for words in ("steward_owner.py ask --target", "steward_owner.py approve", "https://", *SETTINGS):
        assert words in section, words
    assert section.count("Example") >= 2
    assert "Posted" in section and "paste this one line" in section
