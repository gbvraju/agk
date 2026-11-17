"""Briefs drafted in a batch get free folder names in one pass (brief #1442, ADR-0603; REQ-050).

The `brief` skill names every new `Adds:` folder with `plan_names.py batch` (one brief alone with
`next --base`) and checks the saved brief with `check_brief.py`; the guide names that step;
`plan_intake.py` writes no `Adds:` line yet. Recorded lists only, invented names, no network."""

from __future__ import annotations

import re
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import plan_intake  # noqa: E402
import plan_names as pn  # noqa: E402

SKILL = KIT_ROOT / "skills" / "brief" / "SKILL.md"
GUIDE = KIT_ROOT / "docs" / "guides" / "planning.md"
REFERENCE = KIT_ROOT / "docs" / "guides" / "reference.md"
PLUGIN = 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/agk/'


def brief(number: int, adds: str, parked: bool = False) -> dict:
    labels = [{"name": "agk-brief"}] + ([{"name": "agk-parked"}] if parked else [])
    body = f'Sentence: "x"\nTouches: src/other.py\nAdds: {adds}\n'
    return {"number": number, "body": body, "labels": labels}


def test_a_batch_of_three_with_one_held_renames_that_one_only():
    """REQ-050"""
    h = pn.Holders(briefs=[brief(1, "src/shop-m2-ui/")])
    bases = ["src/shop-m2-api/", "src/shop-m2-ui/", "src/shop-m2-db/"]
    assert pn.batch(bases, h) == ["src/shop-m2-api/", "src/shop-m2-ui-2/", "src/shop-m2-db/"]


def test_two_equal_bases_in_one_batch_get_two_names():
    """REQ-050"""
    assert pn.batch(["src/shop-m3-api/", "src/shop-m3-api/"], pn.Holders()) == [
        "src/shop-m3-api/",
        "src/shop-m3-api-2/",
    ]


def test_a_base_a_parked_brief_holds_is_not_free():
    """REQ-050"""
    h = pn.Holders(briefs=[brief(7, "src/shop-m4-api/", parked=True)])
    assert pn.batch(["src/shop-m4-api/"], h) == ["src/shop-m4-api-2/"]


def skill() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_the_skill_names_the_free_names_step_before_the_check():
    """REQ-050"""
    text = skill()
    for part in ("Adds:", "<feature>-m<milestone>-<part>", "next --base", "check_brief.py"):
        assert part in text
    assert text.index("plan_names.py") < text.index("check_brief.py")


def test_the_skill_command_lines_are_the_ones_the_reference_lists():
    """REQ-050"""
    found = re.findall(r'^python3 "\$\{CLAUDE_PLUGIN_ROOT\}/scripts/agk/plan_names\.py" (.+)$', skill(), re.M)
    lines = [f"plan_names.py {rest}" for rest in found]
    assert any(line.startswith("plan_names.py batch FILE") for line in lines)
    listed = [
        ln.strip().removeprefix("python3 scripts/agk/")
        for ln in REFERENCE.read_text(encoding="utf-8").splitlines()
        if ln.strip().startswith("python3 scripts/agk/plan_names.py")
    ]
    for line in lines:
        words = line.split()
        assert any(ref.split()[: len(words)] == words for ref in listed), line
    assert PLUGIN + "check_brief.py" in skill()


def test_the_guide_names_the_skill_step():
    """REQ-050"""
    text = GUIDE.read_text(encoding="utf-8")
    section = text[text.index("## New paths have one owner") :]
    section = section[: section.index("\n## ", 1)]
    assert "`brief` skill" in section and "plan_names.py batch" in section


def test_an_intake_brief_still_writes_no_adds_line():
    """REQ-050: when `brief_text` gains an `Adds:` line it must take its names from
    `plan_names.batch` for the whole intake (ADR-0603 decision 2); this test then changes with it."""
    data = {"requirements": [{"key": "R1", "title": "Pay", "criteria": ["a card pays"]}]}
    b = {
        "key": "b1",
        "title": "Pay by card",
        "advances": ["R1"],
        "touches": ["src/pay/"],
        "size": "S",
        "expected": "1-3 hours",
        "milestone": "M1",
        "depends_on": [],
        "sources": [],
    }
    text = plan_intake.brief_text(data, b)
    assert "Touches: src/pay/" in text
    assert not any(ln.startswith("Adds:") for ln in text.splitlines())
