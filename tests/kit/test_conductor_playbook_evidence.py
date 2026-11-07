"""The verdict's evidence lines per playbook gate (SPEC-0038 rule 9; REQ-045 AC3; brief #666).

With a declared work type, a clearing verdict names, in one `Playbook evidence:` line, each
`evidence` item of the declared playbook with where the conductor read it, or `not applicable:
<reason>`: a `judgement` gate's item names a person's line (`comment <id>`) or a run record
(`docs/runs/<file>`), a `check` gate's item names the governance step (`step <name>`). The
conductor's role file says so in one paragraph and `docs/guides/reference.md` documents the line;
no check reads it (`Q-S0038-10`). A verdict fixture with and without the gate lines, read by the
documented shape only: invented data, no network.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
ROLE = KIT_ROOT / ".claude" / "agents" / "conductor.md"
GUIDE = KIT_ROOT / "docs" / "guides" / "reference.md"
PLAYBOOK = KIT_ROOT / "config" / "playbooks" / "web-app.toml"
SCRIPTS = KIT_ROOT / "scripts" / "agk"
LINE = "Playbook evidence:"
SHA = "4f3e2d1c0b9a8f7e6d5c4b3a29181706f5e4d3c2"

# The documented shape: `Playbook evidence: <item> (<where>); <item> (<where>); ...`, one item per
# `evidence` entry of the playbook, in its order; `<where>` is `step <name>`, `comment <id>`,
# `docs/runs/<file>` or `not applicable: <reason>`.
ITEM = re.compile(r"^(?P<item>[^()]+?) \((?P<where>[^()]+)\)$")
WHERE = re.compile(r"^(step \S+|comment \d+|docs/runs/\S+|not applicable: .+)$")

WITH_LINES = (
    f"Verdict: cleared {SHA}\n\n"
    "Read: all\n"
    "Rules: 1 holds; 2 holds\n"
    "Not proven: AC1 a slow path\n"
    "Lens: security ok; honesty ok; portability ok; size ok; duplication ok\n"
    "Gaps: none\n"
    "Checklist: 1 yes\n"
    "Playbook evidence: the contract test output (step contract-tests); "
    "the mock parity output (step mock-parity); "
    "the e2e smoke run record of the merge batch (docs/runs/e2e-smoke-batch-3.md); "
    "the accessibility review (not applicable: the brief adds no screen)\n\n"
    "No findings.\n"
)
WITH_A_COMMENT = WITH_LINES.replace("(docs/runs/e2e-smoke-batch-3.md)", "(comment 6688900001)")
WITHOUT_LINES = WITH_LINES.replace(
    WITH_LINES[WITH_LINES.index(LINE) : WITH_LINES.index("\n\nNo findings.")],
    "Local evidence: none",
)
MISSING_ONE = WITH_LINES.replace(
    "; the accessibility review (not applicable: the brief adds no screen)", ""
)
NO_WHERE = WITH_LINES.replace(" (step contract-tests)", "")


def flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def evidence_items(body: str) -> list[tuple[str, str]] | None:
    """The `(item, where)` pairs of the one `Playbook evidence:` line, or None without the line.

    A pair whose item or where is not of the documented shape is `(text, "")`.
    """
    lines = [ln for ln in body.splitlines() if ln.startswith(LINE)]
    if not lines:
        return None
    out: list[tuple[str, str]] = []
    for part in lines[0][len(LINE) :].split(";"):
        part = part.strip()
        found = ITEM.match(part)
        if not found or not WHERE.match(found["where"]):
            out.append((part, ""))
        else:
            out.append((found["item"], found["where"]))
    return out


def playbook_evidence() -> list[str]:
    return tomllib.loads(PLAYBOOK.read_text(encoding="utf-8"))["evidence"]


def test_ac3_the_role_file_names_the_playbook_evidence_line_in_one_paragraph():
    """REQ-045 AC3: rule 9, the conductor's role file names the `Playbook evidence:` line."""
    text = ROLE.read_text(encoding="utf-8")
    paragraphs = [p for p in text.split("\n\n") if LINE in p]
    assert len(paragraphs) == 1, "one paragraph names the line"
    flat_paragraph = " ".join(paragraphs[0].split())
    for phrase in (
        "SPEC-0038 rule 9",
        "`Playbook evidence:`",
        "`evidence`",
        "`not applicable: <reason>`",
        "`judgement`",
        "`check`",
        "fix item, never a clearing verdict",
        "`[delivery] work_type`",
    ):
        assert phrase in flat_paragraph, phrase
    assert not re.match(r"^\s*(\d+\.|[-*])\s", paragraphs[0]), "prose, not a rule line"


def test_ac3_the_role_file_says_what_each_gate_kind_names_and_fails_closed_only_when_declared():
    """REQ-045 AC3: brief #666 answer 2."""
    text = flat(ROLE)
    assert "a person's line" in text and "run record" in text and "the governance step" in text
    assert "nothing merges on a missing line" in text
    assert "without a declaration" in text.lower() and "nothing changes" in text


def test_ac3_the_reference_guide_documents_the_line_and_its_forms():
    """REQ-045 AC3: rule 9, the reference guide documents the lines."""
    text = GUIDE.read_text(encoding="utf-8")
    assert "## Playbook evidence" in text
    section = text.split("## Playbook evidence", 1)[1].split("\n## ", 1)[0]
    flat_section = " ".join(section.split())
    for phrase in (
        "`Playbook evidence:`",
        "`step <name>`",
        "`comment <id>`",
        "`docs/runs/<file>`",
        "`not applicable: <reason>`",
        "`judgement`",
        "`check`",
        "`check_pr_body.py`",
        "Q-S0038-10",
        "SPEC-0038 rule 9",
        "ADR-0319",
        "fix item, never a clearing verdict",
    ):
        assert phrase in flat_section, phrase


def test_ac3_the_guides_example_line_has_the_documented_shape():
    """REQ-045 AC3: the example of the guide reads by the same shape as the fixture."""
    section = GUIDE.read_text(encoding="utf-8").split("## Playbook evidence", 1)[1]
    examples = [ln.strip() for ln in section.splitlines() if ln.strip().startswith(LINE)]
    assert len(examples) == 2, "the guide shows the line's template and one example"
    items = evidence_items(examples[1])
    assert items and [item for item, _where in items] == playbook_evidence()
    assert all(where for _item, where in items)


def test_ac3_the_fixture_with_the_gate_lines_names_every_evidence_item_of_the_playbook():
    """REQ-045 AC3: one item per `evidence` entry of the declared playbook, in its order."""
    items = evidence_items(WITH_LINES)
    assert items is not None
    assert [item for item, _where in items] == playbook_evidence()
    assert all(where for _item, where in items)


@pytest.mark.parametrize(
    ("body", "wheres"),
    [
        (
            WITH_LINES,
            [
                "step contract-tests",
                "step mock-parity",
                "docs/runs/e2e-smoke-batch-3.md",
                "not applicable: the brief adds no screen",
            ],
        ),
        (
            WITH_A_COMMENT,
            [
                "step contract-tests",
                "step mock-parity",
                "comment 6688900001",
                "not applicable: the brief adds no screen",
            ],
        ),
    ],
)
def test_ac3_a_check_gate_names_a_step_and_a_judgement_gate_a_record_or_a_persons_line(
    body, wheres
):
    """REQ-045 AC3: brief #666 answer 2, the forms of `<where>`."""
    items = evidence_items(body)
    assert items is not None and [where for _item, where in items] == wheres
    assert body.count(LINE) == 1, "one line"


def test_ac3_the_fixture_without_the_gate_lines_has_no_line_and_is_a_fix_item_on_a_declared_type():
    """REQ-045 AC3: a missing line is a fix item, never a clearing verdict (fail closed)."""
    assert evidence_items(WITHOUT_LINES) is None
    assert WITHOUT_LINES.startswith(f"Verdict: cleared {SHA}"), "the first line is unchanged"
    assert "Local evidence:" in WITHOUT_LINES and LINE not in WITHOUT_LINES


def test_ac3_a_missing_item_or_an_item_without_where_is_not_the_documented_shape():
    """REQ-045 AC3: each evidence item has where it was read or `not applicable: <reason>`."""
    items = evidence_items(MISSING_ONE)
    assert items is not None and [item for item, _where in items] != playbook_evidence()
    items = evidence_items(NO_WHERE)
    assert items is not None and items[0] == ("the contract test output", "")


def test_ac3_no_check_reads_the_line_so_the_conductor_reads_it():
    """REQ-045 AC3: rule 9 and `Q-S0038-10`, `check_pr_body.py`, `proof.py` and CI do not change."""
    for rel in ("check_pr_body.py", "proof.py", "pr_body.py", "route.py", "merge_cleared.py"):
        assert LINE not in (SCRIPTS / rel).read_text(encoding="utf-8"), rel
    for path in (KIT_ROOT / ".github" / "workflows").glob("*.yml"):
        assert LINE not in path.read_text(encoding="utf-8"), path.name


def test_ac3_the_role_file_stays_within_its_rule_budget():
    """REQ-037 AC1 beside AC3: the paragraph is paid for in the same file (brief #666 answer 1)."""
    from rules import counts

    words, rules = counts(ROLE.read_text(encoding="utf-8"))
    budget = (KIT_ROOT / "config" / "rule-budget.txt").read_text(encoding="utf-8")
    role_line = ".claude/agents/conductor.md "
    listed = [ln.split() for ln in budget.splitlines() if ln.startswith(role_line)]
    assert listed and (words, rules) == (int(listed[0][1]), int(listed[0][2]))
    assert words < 4538 and rules <= 37, "the budget only goes down (brief #666)"
