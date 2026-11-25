"""Tests of the discovery record's three grill sections (SPEC-0073 rules 4, 6 and 7; REQ-080 AC2
and AC4; brief #1938, ADR-0803).

`front_door.py discovery-write` appends `## Assumptions`, `## Risks` and `## Readiness` after `##
Open points` only when the answers file has a non-empty `grill` list; `check-discovery` checks the
three sections only when one is present, through `quality_problems`, never through
`document_problems`; `status` prints the readiness line and, while `[quality] grill_hold` is true,
the critical ids that hold the design. Fixtures in `tmp_path` only: invented data (`example.com`),
no network, no model.
"""

from __future__ import annotations

import shutil
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest
from test_front_door_entry import SCRIPT, WORDS, answers, issue, run

GRILL = SCRIPT.parent / "grill.py"
DEFAULT = SCRIPT.parents[2] / "config" / "playbooks" / "default.toml"
REL = "docs/discovery/orders-are-lost.md"
ACCEPTED = "accepted recommendation (in session 2026-11-25, 2026-11-25T10:00:00Z)"
RISK_ACCEPTED = "Risk accepted: riskiest (2026-11-25T11:00:00Z)"
ROWS = [
    {
        "id": "problem",
        "claim": "Orders vanish at checkout.",
        "status": "stated",
        "accepted": ACCEPTED,
    },
    {
        "id": "who-hurts",
        "claim": "Small shops on example.com.",
        "status": "assumption",
        "test": "Ask five shops.",
        "source": "https://example.com/survey",
    },
    {"id": "non-goals", "claim": "No refunds.", "status": "stated"},
    {"id": "riskiest", "claim": "", "status": "open"},
]
RISKS = [
    {
        "id": "pre-mortem",
        "risk": "Payments fail at the busiest hour",
        "sign": "timeouts over one in a hundred",
        "owner": "the shop owner",
    }
]


def project(root: Path, agk: str = "") -> Path:
    folder = root / "config" / "playbooks"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DEFAULT, folder / "default.toml")
    if agk:
        (root / "agk.toml").write_text(agk, encoding="utf-8")
    return root


def grilled(root: Path, rows=None, risks=None) -> Path:
    """The answers file of `test_front_door_entry.answers` with a `grill` and a `risks` list."""
    extra = {"grill": ROWS if rows is None else rows, "risks": RISKS if risks is None else risks}
    return answers(root, extra=extra)


def write(root: Path, answers_file: Path) -> subprocess.CompletedProcess[str]:
    body = f"Problem: {WORDS}\n\nMore notes."
    return run(
        root, "discovery-write", "--issue", str(issue(root, body)), "--answers", str(answers_file)
    )


def ready_line(root: Path, answers_file: Path) -> str:
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(GRILL), "ready", "--answers", str(answers_file), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip()


def document(root: Path, rows=None, risks=None) -> Path:
    project(root)
    proc = write(root, grilled(root, rows, risks))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return root / REL


def tail(text: str) -> str:
    return text[text.index("## Open points") :]


def test_ac4_the_writer_appends_the_three_sections_from_the_grill_and_risks(tmp_path):
    """REQ-080 AC4: SPEC-0073 rule 7 (the sections' form, the composed order, D-<n> for an open
    critical item, the readiness line `grill.py ready` prints)."""
    doc = document(tmp_path)
    line = ready_line(tmp_path, tmp_path / "answers.json")
    assert line.startswith("critical 4/5; risk accepted: none; questions 4/"), line
    assert tail(doc.read_text(encoding="utf-8")) == "\n".join(
        [
            "## Open points",
            "",
            "- D-1: `brand` is open",
            "- D-2: `riskiest` is open",
            '- D-3: "Refunds may need their own flow." (given: in session 2026-11-06)',
            "",
            "## Assumptions",
            "",
            '- A-1: problem: "Orders vanish at checkout." (stated)',
            f"  {ACCEPTED}",
            '- A-2: who-hurts: "Small shops on example.com." (assumption)',
            "  Test: Ask five shops.",
            "  Source: https://example.com/survey",
            '- A-3: non-goals: "No refunds." (stated)',
            "- A-4: riskiest: (open)",
            "",
            "## Risks",
            "",
            "- R-1: Payments fail at the busiest hour; first sign: timeouts over one in a hundred;"
            " owner: the shop owner",
            "",
            "## Readiness",
            "",
            line,
            "",
        ]
    )
    proc = run(tmp_path, "check-discovery")
    assert proc.returncode == 0, proc.stdout


def test_ac4_an_accepted_risk_is_shown_under_its_item_and_needs_no_open_point(tmp_path):
    """REQ-080 AC4: SPEC-0073 rule 6 (`Risk accepted: <id> (<UTC time>)`); rows in any order
    are written in the composed order, the last status row of an id counting."""
    rows = [
        {"id": "riskiest", "risk": RISK_ACCEPTED},
        *ROWS[::-1],
        {
            "id": "non-goals",
            "claim": "No refunds, no gift cards.",
            "status": "stated",
            "revised": True,
        },
    ]
    text = document(tmp_path, rows=rows, risks=[]).read_text(encoding="utf-8")
    assert "`riskiest` is open" not in text
    assert f"- A-4: riskiest: (open)\n  {RISK_ACCEPTED}\n" in text
    assert '- A-3: non-goals: "No refunds, no gift cards." (stated)\n' in text
    assert "## Risks\n\n- none\n" in text
    assert "critical 5/5; risk accepted: riskiest;" in text
    assert run(tmp_path, "check-discovery").returncode == 0


@pytest.mark.parametrize("extra", [{}, {"grill": []}, {"risks": RISKS}])
def test_ac2_an_answers_file_without_a_grill_list_writes_the_document_as_before(tmp_path, extra):
    """REQ-080 AC2: SPEC-0073 rule 4 (no `grill` list: today's bytes, no new section)."""
    before = tmp_path / "before"
    after = tmp_path / "after"
    for root, more in ((before, {}), (after, extra)):
        root.mkdir()
        project(root)
        assert write(root, answers(root, extra=more)).returncode == 0
    text = (after / REL).read_text(encoding="utf-8")
    assert text == (before / REL).read_text(encoding="utf-8")
    assert text.endswith("(given: in session 2026-11-06)\n")
    assert "## Assumptions" not in text and "## Readiness" not in text
    assert run(after, "check-discovery").returncode == 0


@pytest.mark.parametrize(
    "rows,risks",
    [
        ([{"id": "zz-unknown", "claim": "x", "status": "stated"}], []),
        (ROWS, [{"id": "pre-mortem", "risk": "", "sign": "s", "owner": "o"}]),
        (ROWS, [{"id": "pre-mortem", "risk": "two\nlines", "sign": "s", "owner": "o"}]),
        (ROWS, "not a list"),
    ],
    ids=["unknown-id", "empty-risk", "two-line-risk", "risks-not-a-list"],
)
def test_ac4_the_writer_refuses_a_grill_row_or_risk_out_of_form(tmp_path, rows, risks):
    """REQ-080 AC4: SPEC-0073 rule 7 (refused naming the rule and the file, nothing written)."""
    project(tmp_path)
    proc = write(tmp_path, grilled(tmp_path, rows, risks))
    assert proc.returncode == 1, proc.stdout
    assert "rule 7" in proc.stdout and "answers.json" in proc.stdout
    assert not (tmp_path / REL).exists()


def mutate(doc: Path, old: str, new: str) -> None:
    text = doc.read_text(encoding="utf-8")
    assert old in text, old
    doc.write_text(text.replace(old, new, 1), encoding="utf-8")


LINE = "\n- R-1: Payments fail at the busiest hour; first sign: timeouts over one in a hundred;"


@pytest.mark.parametrize(
    "old,new,expected",
    [
        ("\n## Risks\n" + LINE, "\n" + LINE, "the `## Risks` section is missing"),
        ("- A-2: who-hurts", "- A-3: who-hurts", "`## Assumptions` section's numbers"),
        ("- A-2: who-hurts", "- A-2: zz-unknown", "names an id that is not a grill item"),
        ("  Test: Ask five shops.\n", "", "an assumption with no `Test:`"),
        ("- D-2: `riskiest` is open\n- D-3", "- D-2", "an open critical item with no D-<n>"),
        ("- A-4: riskiest: (open)", "- A-4 riskiest open", "`## Assumptions` section has a line"),
        (LINE, "\n- R-1: Payments fail;", "`## Risks` section has a line not of rule 7's form"),
        (
            LINE,
            LINE.replace("R-1", "R-2"),
            "`## Risks` section's numbers",
        ),
        ("critical 4/5;", "critical 4/6;", "critical total is not the composed playbook's"),
        ("critical 4/5;", "critical 6/5;", "critical total is not the composed playbook's"),
        ("risk accepted: none;", "risk accepted: stop;", "an accepted risk with no A-<n> or R-<n>"),
        (
            "critical 4/5;",
            "nearly ready;",
            "`## Readiness` section is not one line of rule 7's form",
        ),
    ],
    ids=[
        "a-section-missing",
        "a-numbers",
        "unknown-id",
        "assumption-no-test",
        "open-critical-no-point",
        "a-line-form",
        "r-line-form",
        "r-numbers",
        "total-wrong",
        "settled-over-total",
        "risk-id-unbacked",
        "readiness-form",
    ],
)
def test_ac4_each_malformed_section_fails_check_discovery_naming_the_section(
    tmp_path, old, new, expected
):
    """REQ-080 AC4: SPEC-0073 rule 7 (each failure names the rule, the section and the file,
    never a value)."""
    doc = document(tmp_path)
    mutate(doc, old, new)
    proc = run(tmp_path, "check-discovery")
    assert proc.returncode == 1, proc.stdout
    assert f"rule 7: {REL}:" in proc.stdout and expected in proc.stdout, proc.stdout
    for value in ("Orders vanish", "Small shops", "Ask five shops", "Payments fail"):
        assert value not in proc.stdout


def test_ac2_document_problems_never_reads_the_three_sections(tmp_path):
    """REQ-080 AC2: SPEC-0073 rule 4 (`document_problems`, which `phase_of` and
    `check_acceptance.py` read, passes a document with the sections, even malformed ones, and
    gives the same result with them cut off)."""
    import front_door

    doc = document(tmp_path)
    mutate(doc, "  Test: Ask five shops.\n", "")
    text = doc.read_text(encoding="utf-8")
    cut = text[: text.index("## Assumptions")]
    assert front_door.document_problems(REL, text) == front_door.document_problems(REL, cut) == []
    assert front_door.quality_problems(REL, cut, tmp_path) == []
    assert front_door.quality_problems(REL, text, tmp_path) != []


def test_ac2_a_document_written_before_this_change_passes_and_its_phase_is_unchanged(tmp_path):
    """REQ-080 AC2: SPEC-0073 rule 4 and rule 14 (records written before this lands)."""
    project(tmp_path)
    assert write(tmp_path, answers(tmp_path)).returncode == 0
    assert run(tmp_path, "check-discovery").returncode == 0
    proc = run(tmp_path, "status", "--date", "2026-11-25")
    assert (
        proc.stdout
        == "orders-are-lost: phase 3 research; waits for docs/research/orders-are-lost.md\n"
    )


def test_ac4_status_prints_readiness_and_the_held_ids(tmp_path):
    """REQ-080 AC4: SPEC-0073 rule 6 (readiness in `front_door.py status`; the ids that hold the
    design while `grill_hold` is true)."""
    document(tmp_path)
    line = ready_line(tmp_path, tmp_path / "answers.json")
    proc = run(tmp_path, "status", "--date", "2026-11-25")
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.splitlines() == [
        "orders-are-lost: phase 3 research; waits for docs/research/orders-are-lost.md",
        f"  readiness: {line}",
        "  held at the design: riskiest",
    ]


def test_ac4_with_grill_hold_false_status_shows_readiness_and_holds_nothing(tmp_path):
    """REQ-080 AC4 and AC7: SPEC-0073 rules 6 and 11 (`grill_hold = false`)."""
    document(tmp_path)
    (tmp_path / "agk.toml").write_text("[quality]\ngrill_hold = false\n", encoding="utf-8")
    lines = run(tmp_path, "status", "--date", "2026-11-25").stdout.splitlines()
    assert len(lines) == 2 and lines[1].startswith("  readiness: critical 4/5;")


def test_ac4_an_accepted_risk_holds_nothing_in_status(tmp_path):
    """REQ-080 AC4: SPEC-0073 rule 6 (an accepted risk settles its critical item)."""
    document(tmp_path, rows=[*ROWS, {"id": "riskiest", "risk": RISK_ACCEPTED}])
    lines = run(tmp_path, "status", "--date", "2026-11-25").stdout.splitlines()
    assert len(lines) == 2 and "critical 5/5; risk accepted: riskiest;" in lines[1]
