"""Kit-only tests of `/agk:confirm` and the guide line of solo mode (brief 277, ADR-0179; REQ-039).

`skills/` is not vendored into a project, so these tests live in `tests/kit_dev/`."""

from __future__ import annotations

from conftest import KIT_ROOT

SKILL = KIT_ROOT / "skills" / "confirm" / "SKILL.md"
GUIDE = KIT_ROOT / "docs" / "guides" / "getting-started.md"
REFERENCE = KIT_ROOT / "docs" / "guides" / "reference.md"


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
        "This command writes no file and posts nothing.",
    ):
        assert phrase in text, phrase
    assert "--method POST" not in text and "-X POST" not in text


def test_the_guide_says_the_person_posts_it_and_re_runs_governance():
    """REQ-039: brief #277 (the verdict on f58803a, item 3: the one guide line)."""
    text = flat(GUIDE)
    assert "/agk:confirm" in text and "a session never does, session rule 29" in text
    assert "re-run the governance check or push" in text
    assert "| `/agk:confirm` |" in REFERENCE.read_text(encoding="utf-8")
