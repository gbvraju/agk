"""The planning guide and its recorded walk (brief #1079, ADR-0460; SPEC-0043 rule 26).

`docs/guides/planning.md` shows the path from a customer's prototype and documents to an approved
plan in GitHub: the import, the prototype source, `/agk:plan-intake`, `validate`, `render`, the
trace, the person's `Approve: plan` and `publish`, with the honest limits of rule 26.
`docs/guides/reference.md` lists the commands. `docs/runs/plan-walk-<date>.md` records one walk on
an invented project (example.com) that ends with the coverage line. Amendment 163 (with the
owner's ruling on Q-1073-2) is in the texts of SPEC-0043 and SPEC-0037. Docs only: the tests read
files and run nothing. REQ-050.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "guides" / "planning.md"
REFERENCE = ROOT / "docs" / "guides" / "reference.md"
SPECS = ROOT / "docs" / "specs"
HONEST = (
    "Estimates are ranges from this project's own history, not promises;"
    " AGK drafts from the sources and the person owns scope."
)
# The path of the guide, in order (brief #1079 answer 1).
PATH = (
    "/agk:design import",
    "design_import.py source",
    "/agk:plan-intake",
    "plan_intake.py validate",
    "plan_intake.py render",
    "check_plan.py --trace",
    "Approve: plan",
    "plan_intake.py publish",
)
# The commands as the walk runs them, in order.
WALK_STEPS = (
    "design.py\" import",
    "design_import.py source --version i1",
    "check_plan.py",
    "plan_intake.py states",
    "plan_intake.py validate",
    "plan_intake.py render",
    "check_plan.py --trace",
    "Approve: plan",
    "plan_intake.py publish",
)


def spec(number: str) -> Path:
    """The spec file of NUMBER, read when a test runs and not at import: a copied kit without
    `docs/specs/` still collects this file (brief #1128, as #1103)."""
    return next(SPECS.glob(f"{number}-*.md"))


def walks() -> list[Path]:
    return sorted((ROOT / "docs" / "runs").glob("plan-walk-*.md"))


def test_the_guide_names_each_command_of_the_path_in_order():
    """REQ-050"""
    text = GUIDE.read_text(encoding="utf-8")
    places = [text.find(name) for name in PATH]
    missing = [name for name, at in zip(PATH, places, strict=True) if at == -1]
    assert not missing, f"the guide does not name {missing}"
    assert places == sorted(places), "the guide names the path out of order"


def test_the_guide_states_the_honest_limits():
    """REQ-050"""
    text = " ".join(GUIDE.read_text(encoding="utf-8").split())
    assert HONEST in text
    for phrase in (
        "never contacts the customer",
        "never reads a source the person did not provide",
        "no estimate",
        "the person owns scope",
    ):
        assert phrase in text, phrase


def test_the_guide_points_to_its_walk():
    """REQ-050"""
    text = GUIDE.read_text(encoding="utf-8")
    assert any(f"docs/runs/{walk.name}" in text for walk in walks())


def test_the_reference_lists_the_plan_commands():
    """REQ-050"""
    text = REFERENCE.read_text(encoding="utf-8")
    for command in (
        "python3 scripts/agk/design_import.py source --version i<n> --slug <slug>",
        "python3 scripts/agk/plan_intake.py render --proposals FILE",
        "python3 scripts/agk/plan_intake.py publish --comments FILE --head SHA",
        "python3 scripts/agk/check_plan.py [--root DIR] [--trace]",
        "docs/guides/planning.md",
    ):
        assert command in text, command


def test_a_walk_records_each_step_in_order():
    """REQ-050"""
    assert walks(), "no docs/runs/plan-walk-<date>.md"
    text = walks()[-1].read_text(encoding="utf-8")
    assert re.fullmatch(r"plan-walk-\d{4}-\d{2}-\d{2}\.md", walks()[-1].name)
    at = 0
    for command in WALK_STEPS:
        found = text.find(command, at)
        assert found != -1, f"the walk does not record {command} after the step before it"
        at = found
    assert "gh api 'repos/{owner}/{repo}/milestones'" in text
    assert "gh api 'repos/{owner}/{repo}/issues'" in text


def test_the_walk_ends_with_the_coverage_line():
    """REQ-050"""
    lines = [line for line in walks()[-1].read_text(encoding="utf-8").splitlines() if line.strip()]
    while lines and (lines[-1].startswith("```") or re.fullmatch(r"\(exit \d+\)", lines[-1])):
        lines.pop()
    assert lines and lines[-1].startswith("ok plan: "), lines[-1:]


def test_the_walk_uses_invented_data_only():
    """REQ-050"""
    text = walks()[-1].read_text(encoding="utf-8")
    hosts = set(re.findall(r"(?:https?://|@)([A-Za-z0-9.-]+\.[A-Za-z]{2,})", text))
    hosts |= set(re.findall(r"\b([a-z0-9-]+\.(?:com|net|org|io))\b", text))
    assert hosts <= {"example.com"}, hosts


def test_amendment_163_is_in_the_spec_texts():
    """REQ-050"""
    raw = spec("0043").read_text(encoding="utf-8")
    text = " ".join(raw.split())
    assert re.search(r"(?m)^2a\. \*\*", raw)
    assert "design_import.py source --version i<n> --slug <slug>" in text
    # The owner's ruling on Q-1073-2 over the merged text of amendment 163 item 2.
    assert "all text outside `script`, `style` and `template` elements, in document order" in text
    assert "each `## <screen>/<state>` heading is one in-scope source location" in text
    assert "the states that `docs/design/inventory.md` gives that screen as `yes`" in text
    assert "(k) **the prototype source**" in text
    design = " ".join(spec("0037").read_text(encoding="utf-8").split())
    assert "The one exception is the source file that `design_import.py source` writes" in design


# Brief #1110 answer 2 (ADR-0474): the path from a prototype and an OpenSpec file, in order.
OPENSPEC_SECTION = "## From a prototype and an OpenSpec file"
OPENSPEC_PATH = (
    "/agk:design import",
    "design_import.py source",
    "plan_intake.py openspec-import",
    "plan_intake.py openspec --slug",
    "/agk:plan-intake",
    "plan_intake.py validate",
    "plan_intake.py render",
    "check_plan.py --trace",
    "Approve: plan",
    "plan_intake.py publish",
)
CONFIDENTIAL = (
    "A customer's file is processed only where the customer's contract allows it,"
    " and never enters the kit's repository."
)


def openspec_section() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    assert OPENSPEC_SECTION in text.splitlines(), "the guide has no OpenSpec section"
    rest = text.split(OPENSPEC_SECTION + "\n", 1)[1]
    end = rest.find("\n## ")
    return rest if end == -1 else rest[:end]


def test_the_openspec_section_names_each_command_in_order():
    """REQ-050"""
    section = openspec_section()
    places = [section.find(name) for name in OPENSPEC_PATH]
    missing = [name for name, at in zip(OPENSPEC_PATH, places, strict=True) if at == -1]
    assert not missing, f"the OpenSpec section does not name {missing}"
    assert places == sorted(places), "the OpenSpec section names the path out of order"


def test_the_openspec_section_states_the_confidentiality_sentence():
    """REQ-050"""
    assert CONFIDENTIAL in " ".join(openspec_section().split())


def test_the_openspec_section_names_the_scenario_count():
    """REQ-050"""
    section = " ".join(openspec_section().split())
    assert "scenarios have an acceptance line and" in section
    assert "info plan:" in section


def test_the_guide_lists_openspec_among_the_kinds():
    """REQ-050"""
    text = " ".join(GUIDE.read_text(encoding="utf-8").split())
    assert "`charter`, `openspec` or `other`" in text
