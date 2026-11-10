"""The compaction-recovery reads (brief #941 answers 1 and 4, ADR-0403; REQ-052).

After compaction or a new session, `CLAUDE.md` sends a session to the decision files that a
`grep -l` finds for its item under `docs/runs/decisions/`, never to the frozen
`docs/runs/decisions-log.md` as a step to re-read. Invented texts only; no network.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = ROOT / "CLAUDE.md"
LOG = "docs/runs/decisions-log.md"
FOLDER = "docs/runs/decisions/"


def recovery(text: str) -> str:
    """The `## Compaction recovery` section, flattened to one line; empty when it is missing."""
    m = re.search(r"(?ms)^## Compaction recovery\n(.*?)(?=^## |\Z)", text)
    return " ".join(m.group(1).split()) if m else ""


def problems(text: str) -> list[str]:
    """What is wrong with a CLAUDE.md's recovery step; an empty list when it reads lean."""
    section = recovery(text)
    if not section:
        return ["no Compaction recovery section"]
    found = []
    step = section.split(";")[0]
    if LOG in step:
        found.append("the frozen log is a re-read step")
    if FOLDER not in step or "grep" not in step:
        found.append("the step does not name the grep of the decisions folder")
    return found


OLD = (
    "# T\n\n## Compaction recovery\n\nAfter compaction or a new session, re-read CLAUDE.md, "
    f"the current brief, `{LOG}` and the\nopen PR body before acting. A new decisions-log row "
    f"is one file under `{FOLDER}`; the old log is frozen.\n"
)
LEAN = (
    "# T\n\n## Compaction recovery\n\nAfter compaction or a new session, re-read CLAUDE.md, "
    f"the brief, the open PR body and the `{FOLDER}` files that `grep -l` finds\nfor the "
    f"brief's number, spec, Q ids and paths; the old `{LOG}` is frozen.\n"
)


def test_req052_the_old_step_that_rereads_the_frozen_log_is_refused():
    """REQ-052: brief #941 answer 4 (fails while the log is a re-read step)."""
    assert "the frozen log is a re-read step" in problems(OLD)
    assert "the step does not name the grep of the decisions folder" in problems(OLD)


def test_req052_a_step_that_greps_the_folder_and_names_the_log_frozen_passes():
    """REQ-052: brief #941 answer 1 (the log may be named, as frozen, after the step)."""
    assert problems(LEAN) == []


def test_req052_a_missing_section_or_a_folder_without_grep_is_refused():
    """REQ-052: brief #941 answer 4 (negative cases: no section; the folder read whole)."""
    assert problems("# T\n\nNothing here.\n") == ["no Compaction recovery section"]
    whole = LEAN.replace(" that `grep -l` finds", "")
    assert problems(whole) == ["the step does not name the grep of the decisions folder"]


def test_req052_claude_md_reads_only_the_decisions_its_item_names():
    """REQ-052: brief #941 answers 1 and 4 (the installed CLAUDE.md itself)."""
    assert problems(CLAUDE.read_text(encoding="utf-8")) == []
