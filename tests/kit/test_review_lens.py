"""Review asks whether a change rebuilds what exists (brief #2065, ADR-0857; REQ-037).

Answer 6: the lens's last entry in the four protocol copies names a rebuild of the project's code,
a part or a kit feature, the copies stay identical, checklist item 10 names it, and no file of the
rule budget grows. Files only; no network.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import rules  # noqa: E402

AGENTS = ("architect.md", "architect-review.md", "shadow.md", "conductor.md")
PROTOCOL = re.compile(r"<!-- protocol -->\n(.*?)<!-- /protocol -->", re.S)
LENS = (
    "duplication (logic copied from a kit file, or rebuilt where the project's code, a part or a"
    " kit feature already does it)"
)


def protocol(name: str) -> str:
    found = PROTOCOL.search((ROOT / ".claude" / "agents" / name).read_text(encoding="utf-8"))
    assert found, name
    return found.group(1)


def test_req037_the_four_protocol_copies_are_identical_and_name_a_rebuild():
    """REQ-037: answer 6 (the lens)."""
    copies = {name: protocol(name) for name in AGENTS}
    assert len(set(copies.values())) == 1
    lens = next(x for x in copies["architect.md"].splitlines() if "**The fixed lens**" in x)
    assert lens.endswith(LENS + ".")
    assert "a part or a kit feature" in lens


def test_req037_checklist_item_10_asks_for_a_rebuild():
    """REQ-037: answer 6 (item 10, `kit-defect`, widened; no new question)."""
    text = (ROOT / "config" / "review-checklist.md").read_text(encoding="utf-8")
    item = next(x for x in text.splitlines() if x.startswith("10. "))
    assert item.startswith("10. `kit-defect`:")
    assert "rebuild what the project's code, a part or a kit feature already does" in item
    assert len(re.findall(r"(?m)^\d+\. `", text)) == 12


def test_req037_the_catch_log_row_is_a_kit_defect():
    """REQ-037: answer 6 (SPEC-0023 rule 5: the row the widened item cites)."""
    text = (ROOT / "docs" / "runs" / "architect-catches-3.md").read_text(encoding="utf-8")
    assert re.search(r"(?m)^\| 1 \| 2026-10-22 \| project PR #27 \| `kit-defect` \|", text)


def test_req037_no_rule_budget_grows():
    """REQ-037: answer 6 (`rules.py budget --check`)."""
    assert rules.budget_problems(ROOT) == []
