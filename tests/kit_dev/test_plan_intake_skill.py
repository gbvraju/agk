"""Kit-only tests of `/agk:plan-intake` (SPEC-0043 rules 3, 4 and 6; REQ-050 AC2).

`skills/` is not vendored into a project, so these tests live in `tests/kit_dev/`. The skill writes
one proposals file outside `docs/` and nothing else, runs the guard first and `validate` last.
"""

from __future__ import annotations

import json

from conftest import KIT_ROOT

SKILL = KIT_ROOT / "skills" / "plan-intake" / "SKILL.md"
MANIFEST = KIT_ROOT / "kit" / "manifest.json"


def flat() -> str:
    return " ".join(SKILL.read_text(encoding="utf-8").split())


def test_ac2_the_skill_names_the_proposals_schema():
    """REQ-050 AC2: rule 4, the proposals file, `schema` 1, and every key of each item."""
    text = flat()
    assert text.startswith("--- name: plan-intake description: ")
    assert "disable-model-invocation: true" in text
    for key in (
        '"schema": 1',
        "scope",
        "in",
        "out",
        "assumptions",
        "constraints",
        "open_questions",
        "milestones",
        "exit",
        "acceptance",
        "target",
        "requirements",
        "criteria",
        "areas",
        "briefs",
        "size",
        "expected",
        "advances",
        "touches",
        "depends_on",
        "conflicts",
        "settled",
        "sources",
    ):
        assert f'"{key}"' in text or key in text, key


def test_ac2_the_skill_writes_the_proposals_only_and_nothing_else():
    """REQ-050 AC2: rule 4, a path the person names outside docs/, never committed."""
    text = flat()
    for phrase in (
        "at a path the person names outside `docs/`",
        "never committed",
        "It never writes a requirement, a spec, a brief or a GitHub object.",
        'plan_intake.py" validate --proposals',
        "until it prints `ok proposals`",
    ):
        assert phrase in text, phrase
    for verb in ("gh api", "gh issue", "git commit", "git push", "new_spec.py"):
        assert verb not in text, verb


def test_ac1_the_skill_runs_the_guard_before_reading_a_source():
    """REQ-050 AC1: rule 3, `states` passes the guard before any source is read."""
    text = flat()
    assert text.index('plan_intake.py" states') < text.index("Read the sources")
    assert "data guard not installed" in text and "exit 2" in text


def test_ac2_the_skill_invents_nothing_and_shows_the_conflicts():
    """REQ-050 AC2: rule 6 and amendment 163 item 5."""
    text = flat()
    for phrase in (
        "(verify)",
        "never a value made up",
        "Settled: <location>",
        "the person settles",
        "each line `states` prints is one `scope.open_questions` item",
    ):
        assert phrase in text, phrase


def test_ac2_the_script_is_installed_and_the_skill_is_not():
    """REQ-050 AC2: `plan_intake.py` is `verbatim`; the plugin carries the skill."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert "scripts/agk/plan_intake.py" in manifest["verbatim"]
    assert not [p for p in manifest["verbatim"] if p.startswith("skills/")]


def test_ac2_the_skill_writes_personas_and_stories_and_invents_no_user():
    """REQ-050 AC2: rules 4 and 6 with amendment 164 item 2 (ADR-0462), build (p)."""
    text = flat()
    for phrase in (
        '"personas": [{"key": "P1", "name": "", "goals": [""], "sources": []}]',
        '"persona": "P1", "story": "As <name>, I want <capability>, so that <outcome>"',
        "persona keys run `P1`, `P2`, ... in order",
        "starts `As <that persona's name>, I want ` and goes on `, so that <outcome>`",
        "is never a persona you make up",
        "is a `scope.open_questions` item whose text ends `(verify)`",
    ):
        assert phrase in text, phrase
