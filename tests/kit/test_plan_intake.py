"""Tests of `plan_intake.py`: the guard gate and `validate` (SPEC-0043 rules 3 to 6; REQ-050).

REQ-050 AC1 and AC2.

Every command first needs the data guard installed and scans every source before it reads a line
(rule 3); `validate` refuses a proposals file with an unknown or missing key, an empty or
unresolved location, an unmeasurable exit, a bad size or range, a dangling or cyclic dependence, a
milestone with no brief, a value no source supports, or an item citing both sides of an unsettled
conflict, naming the rule and the key, never the text. Invented sources only (example.com).
"""

from __future__ import annotations

import copy
import json
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import check_plan
import common
import plan_intake
import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "plan_intake.py"
SOW = "docs/sources/sow.md"
PRD = "docs/sources/prd.md"
SOW_TEXT = (
    "Source: Example statement of work\nKind: sow\nVersion: 1.0\nDate: 2026-10-01\n\n"
    "# Scope\n\nThe portal at example.com lists orders.\n\n"  # line 8
    "## Milestones\n\nM1 ships the order list by 2026-12-18.\n\n"  # line 12
    "## Estimates\n\nThe order list is size M, 4-8 hours.\n\n"  # line 16
    "## Payments\n\nPayments are out of scope.\n"  # line 20
)
PRD_TEXT = (
    "Source: Example product requirements\nKind: prd\nVersion: 2\nDate: 2026-10-02\n\n"
    "# Orders\n\nOrders are listed by date.\n\nPayments are in scope.\n"  # lines 8 and 10
)
TITLE = "Order list for example.com"  # an item's text; never printed
GOOD: dict = {
    "schema": 1,
    "scope": {
        "in": [{"key": "S1", "text": TITLE, "sources": [f"{SOW}:8"]}],
        "out": [],
        "assumptions": [],
        "constraints": [],
        "open_questions": [
            {"key": "Q1", "text": "Who signs the list off? (verify)", "sources": [f"{SOW}#Scope"]}
        ],
    },
    "milestones": [
        {
            "id": "M1",
            "title": TITLE,
            "exit": "exit: all 3 list screens pass",
            "acceptance": "The list shows orders",
            "target": "2026-12-18",
            "sources": [f"{SOW}#Milestones"],
        }
    ],
    "requirements": [
        {
            "key": "R1",
            "title": TITLE,
            "criteria": ["Given orders, when the list opens, then they show by date"],
            "milestone": "M1",
            "sources": [f"{PRD}:8"],
        }
    ],
    "areas": [{"name": "Orders", "requirements": ["R1"]}],
    "briefs": [
        {
            "key": "B1",
            "milestone": "M1",
            "title": TITLE,
            "size": "M",
            "expected": "4-8 hours",
            "advances": ["R1"],
            "touches": ["src/orders.py"],
            "depends_on": [],
            "sources": [f"{SOW}#Estimates"],
        }
    ],
    "conflicts": [],
}
CONFLICT = {"locations": [f"{SOW}:20", f"{PRD}:10"], "description": "payments in or out"}


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    write(root, "scripts/agk/guard.py", "# the data guard (a placeholder of the fixture)\n")
    write(root, ".claude/hooks/data_guard.py", "# the read hook (a placeholder of the fixture)\n")
    write(root, SOW, SOW_TEXT)
    write(root, PRD, PRD_TEXT)
    return root


def validate(root: Path, data: object, capsys) -> tuple[int, str]:
    path = root.parent / "proposals.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    code = plan_intake.main(["validate", "--proposals", str(path), "--root", str(root)])
    out = capsys.readouterr()
    return code, out.out + out.err


def refused(root: Path, data: object, capsys, *lines: str) -> str:
    code, out = validate(root, data, capsys)
    assert code == 1, out
    for line in lines:
        assert line in out, out
    assert TITLE not in out and "ok proposals" not in out
    return out


def good() -> dict:
    return copy.deepcopy(GOOD)


# --- rule 3: the data guard first --------------------------------------------------------------


@pytest.mark.parametrize("rel", ["scripts/agk/guard.py", ".claude/hooks/data_guard.py"])
def test_ac1_rule_3_every_command_exits_2_without_the_guard(repo: Path, rel: str, capsys) -> None:
    """REQ-050 AC1: rule 3, the condition is whether the guard is installed, never a setting."""
    (repo / rel).unlink()
    code, out = validate(repo, good(), capsys)
    assert code == 2 and f"data guard not installed: {rel}" in out, out
    assert plan_intake.main(["states", "--root", str(repo)]) == 2
    assert f"data guard not installed: {rel}" in capsys.readouterr().out


def test_ac1_rule_3_a_secret_in_a_source_is_refused_naming_place_never_value(
    repo: Path, capsys
) -> None:
    """REQ-050 AC1: rule 3, `guard.scan_text`; the value is built here, so no file holds one."""
    value = "ghp_" + "a1B2c3D4" * 4 + "a1B2"
    write(repo, PRD, PRD_TEXT.replace("listed by date", f"listed by {value}"))
    out = refused(repo, good(), capsys, f"rule 3: {PRD}: ", "line 8, column ")
    assert value not in out and "ghp_" not in out


def test_ac1_rule_3_every_source_is_scanned_before_any_location_resolves(
    repo: Path, capsys, monkeypatch
) -> None:
    """REQ-050 AC1: rule 3, a recording stub of `scan_text` and of the location parser."""
    import guard

    calls: list[str] = []
    monkeypatch.setattr(guard, "scan_text", lambda text, *a, **k: calls.append("scan") or [])
    real = check_plan.location_problem
    monkeypatch.setattr(
        check_plan, "location_problem", lambda r, loc: calls.append("resolve") or real(r, loc)
    )
    code, out = validate(repo, good(), capsys)
    assert code == 0, out
    assert calls[:2] == ["scan", "scan"] and "scan" not in calls[2:] and "resolve" in calls


def test_ac2_the_script_uses_only_the_kit_and_the_standard_library(repo: Path, capsys) -> None:
    """REQ-050 AC2: no network (a socket guard), and the imports of build (b) and common.py."""
    original = socket.socket
    socket.socket = None  # type: ignore[assignment,misc]
    try:
        code, out = validate(repo, good(), capsys)
    finally:
        socket.socket = original  # type: ignore[misc]
    assert code == 0 and out.strip() == "ok proposals", out
    assert plan_intake.location_problem is check_plan.location_problem
    assert plan_intake.ESTIMATE_LINES is common.ESTIMATE_LINES


# --- rule 4: the proposals as data -------------------------------------------------------------


def test_ac2_rule_4_a_good_proposals_file_passes_by_the_command(repo: Path) -> None:
    """REQ-050 AC2: rules 4 to 6, the command line prints `ok proposals` and exits 0."""
    path = repo.parent / "proposals.json"
    path.write_text(json.dumps(GOOD), encoding="utf-8")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "validate", "--proposals", str(path), "--root", str(repo)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0 and proc.stdout.strip() == "ok proposals", proc.stdout


def test_ac2_rule_4_an_unknown_and_a_missing_key_are_refused(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 4, an unknown key and a missing key, naming the item's key."""
    data = good()
    data["briefs"][0]["owner"] = "someone"
    del data["requirements"][0]["criteria"]
    data["extra"] = []
    refused(
        repo,
        data,
        capsys,
        "rule 4: briefs B1: unknown key owner",
        "rule 4: requirements R1: missing key criteria",
        "rule 4: proposals: unknown key extra",
    )


def test_ac2_rule_4_missing_and_empty_sources_are_refused(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 4, every item of scope, milestones, requirements and briefs has sources."""
    data = good()
    del data["scope"]["in"][0]["sources"]
    data["milestones"][0]["sources"] = []
    refused(
        repo,
        data,
        capsys,
        "rule 4: scope.in S1: missing key sources",
        "rule 4: milestones M1: sources is empty",
    )


def test_ac2_rule_4_the_schema_ids_and_place_of_the_file(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 4, `schema` 1, ids `M1`, `M2`, ..., and the file outside docs/."""
    data = good()
    data["schema"] = 2
    data["milestones"][0]["id"] = "M2"
    refused(repo, data, capsys, "rule 4: proposals: schema is not 1", "rule 4: milestones M2: ")
    path = write(repo, "docs/plan/proposals.json", json.dumps(GOOD))
    assert plan_intake.main(["validate", "--proposals", str(path), "--root", str(repo)]) == 1
    assert "rule 4: the proposals file is outside docs/" in capsys.readouterr().out


def test_ac2_rule_4_a_file_that_is_not_json_is_refused(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 4, the proposals are one JSON object."""
    path = repo.parent / "proposals.json"
    path.write_text("not json", encoding="utf-8")
    assert plan_intake.main(["validate", "--proposals", str(path), "--root", str(repo)]) == 1
    assert "rule 4: the proposals file is not a JSON object" in capsys.readouterr().out


def test_ac2_the_command_line_is_refused_without_its_arguments(capsys) -> None:
    """REQ-050 AC2: `validate` needs `--proposals FILE`."""
    assert plan_intake.main(["validate"]) == 2
    assert plan_intake.main(["render"]) == 2
    assert "usage: plan_intake.py" in capsys.readouterr().err


# --- rule 5: validation ------------------------------------------------------------------------


def test_ac2_rule_5_unresolved_locations_name_the_rule_and_the_key(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 5, a line past the end, a heading not in the file, a file elsewhere."""
    data = good()
    data["scope"]["in"][0]["sources"] = [f"{SOW}:99"]
    data["requirements"][0]["sources"] = [f"{PRD}#Billing"]
    data["scope"]["open_questions"][0]["sources"] = ["README.md:1"]
    refused(
        repo,
        data,
        capsys,
        "rule 5: scope.in S1: a location's line does not exist in its file",
        "rule 5: requirements R1: a location's heading is not a heading of its file",
        "rule 5: scope.open_questions Q1: a location's file is under docs/sources/",
    )


def test_ac2_rule_5_an_unmeasurable_exit_is_refused(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 5, the measurable test of SPEC-0013 rule 5."""
    data = good()
    data["milestones"][0]["exit"] = "exit: the list is done"
    refused(repo, data, capsys, "rule 5: milestones M1: exit is not measurable")


def test_ac2_rule_5_measurable_is_the_playbook_pattern() -> None:
    """REQ-050 AC2: rule 5, `playbook.py` is kit-only, so the pattern is held equal here."""
    import playbook

    assert plan_intake.MEASURABLE.pattern == playbook.MEASURABLE.pattern
    assert plan_intake.MEASURABLE.flags == playbook.MEASURABLE.flags


@pytest.mark.parametrize(
    ("field", "value"), [("expected", "5-2 hours"), ("expected", "4-8"), ("size", "XL")]
)
def test_ac2_rule_5_a_bad_size_or_range_is_refused(
    repo: Path, field: str, value: str, capsys
) -> None:
    """REQ-050 AC2: rule 5, SPEC-0018 rule 2 (`common.ESTIMATE_LINES`)."""
    data = good()
    data["briefs"][0][field] = value
    refused(repo, data, capsys, f"rule 5: briefs B1: {field} is not SPEC-0018's")


def test_ac2_rule_5_dangling_names_are_refused(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 5, a milestone, advances, depends_on or area that names nothing."""
    data = good()
    data["briefs"][0].update(milestone="M9", advances=["R9"], depends_on=["B9"])
    data["requirements"][0]["milestone"] = "M8"
    data["areas"][0]["requirements"] = ["R7"]
    refused(
        repo,
        data,
        capsys,
        "rule 5: briefs B1: milestone names nothing",
        "rule 5: briefs B1: advances names nothing",
        "rule 5: briefs B1: depends_on names nothing",
        "rule 5: requirements R1: milestone names nothing",
        "rule 5: areas Orders: requirements names nothing",
        "rule 5: milestones M1: no brief",
    )


def test_ac2_rule_5_a_depends_on_cycle_is_refused(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 5, a cycle of `depends_on`."""
    data = good()
    second = copy.deepcopy(data["briefs"][0]) | {"key": "B2", "depends_on": ["B1"]}
    data["briefs"][0]["depends_on"] = ["B2"]
    data["briefs"].append(second)
    refused(repo, data, capsys, "rule 5: briefs B1: depends_on makes a cycle")


def test_ac2_rule_5_a_milestone_with_no_brief_is_refused(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 5, a milestone that no brief names."""
    data = good()
    data["milestones"].append(copy.deepcopy(data["milestones"][0]) | {"id": "M2"})
    out = refused(repo, data, capsys, "rule 5: milestones M2: no brief")
    assert "milestones M1: no brief" not in out


def test_ac2_rule_5_a_repeated_key_is_refused(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 4, each key names one item."""
    data = good()
    data["requirements"].append(copy.deepcopy(data["requirements"][0]))
    refused(repo, data, capsys, "rule 4: requirements R1: the key is repeated")


# --- rule 6: nothing invented, conflicts shown -------------------------------------------------


def test_ac2_rule_6_an_unsupported_target_is_printed_as_an_open_question(
    repo: Path, capsys
) -> None:
    """REQ-050 AC2: rule 6, a target date no location holds is an open question, exit 1."""
    data = good()
    data["milestones"][0]["target"] = "2027-01-15"
    refused(repo, data, capsys, "rule 6: open question: milestones M1: target (verify)")
    data["milestones"][0]["target"] = None
    assert validate(repo, data, capsys)[0] == 0


def test_ac2_rule_6_an_unsupported_size_or_range_is_an_open_question(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 6, a size or range that no location of the brief states."""
    data = good()
    data["briefs"][0].update(size="L", expected="10-20 hours")
    refused(
        repo,
        data,
        capsys,
        "rule 6: open question: briefs B1: size (verify)",
        "rule 6: open question: briefs B1: expected (verify)",
    )


def test_ac2_rule_6_an_open_question_carries_the_verify_mark(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 6, a point the sources do not settle is marked `(verify)`."""
    data = good()
    data["scope"]["open_questions"][0]["text"] = "Who signs the list off?"
    refused(repo, data, capsys, "rule 6: scope.open_questions Q1: no (verify) mark")


def test_ac2_rule_6_an_item_citing_both_sides_of_a_conflict_is_refused(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 6, both sides of an unsettled conflict; `settled` lets it pass."""
    data = good()
    data["conflicts"] = [copy.deepcopy(CONFLICT)]
    data["requirements"][0]["sources"] = [f"{PRD}:8", f"{SOW}:20", f"{PRD}:10"]
    refused(repo, data, capsys, "rule 6: requirements R1: cites both sides of conflict 1")
    data["conflicts"][0]["settled"] = f"Settled: {PRD}:10"
    assert validate(repo, data, capsys)[0] == 0
    data["conflicts"][0]["settled"] = f"Settled: {PRD}:8"
    refused(repo, data, capsys, "rule 6: conflicts 1: settled names neither side")


def test_ac2_rule_6_a_conflict_needs_two_locations_that_resolve(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 4, each conflict is two locations and a description."""
    data = good()
    data["conflicts"] = [{"locations": [f"{SOW}:20", f"{PRD}:99"], "description": "payments"}]
    refused(repo, data, capsys, "rule 5: conflicts 1: a location's line does not exist")
    data["conflicts"] = [{"locations": [f"{SOW}:20"], "description": "payments"}]
    refused(repo, data, capsys, "rule 4: conflicts 1: locations is not two locations")


# --- amendment 163 item 5: the states a prototype does not show -------------------------------

DESIGN = (
    "Source: imported prototype i1\nKind: design\nVersion: i1 abc\nDate: 2026-11-12\n\n"
    "## form/default\n\nName\n\n## list/default\n\nOrders\n\n## list/empty\n\nNo orders\n"
)
INVENTORY = (
    "# Inventory\n\n## Screens\n\n"
    "### form\n\n- State default: yes\n- State error: yes\n- State empty: yes\n"
    "- State loading: n/a: the form loads with the page\n\n"
    "### list\n\n- State default: yes\n- State empty: yes\n\n"
    "### settings\n\n- State default: yes\n"
)


def test_ac2_states_lists_the_inventory_states_no_heading_covers(repo: Path, capsys) -> None:
    """REQ-050 AC2: amendment 163 item 5, two open questions for `form`, none for `list`."""
    write(repo, "docs/sources/proto-prototype-i1.md", DESIGN)
    write(repo, "docs/design/inventory.md", INVENTORY)
    assert plan_intake.main(["states", "--root", str(repo)]) == 0
    lines = capsys.readouterr().out.splitlines()
    first = "docs/sources/proto-prototype-i1.md#form/default"
    assert lines == [f"{first} error (verify)", f"{first} empty (verify)"]
    assert plan_intake.location_problem(repo, first) is None


def test_ac2_states_prints_nothing_without_a_design_source(repo: Path, capsys) -> None:
    """REQ-050 AC2: amendment 163 item 5, a heading of another kind of source is not a screen."""
    write(repo, "docs/sources/notes.md", DESIGN.replace("Kind: design", "Kind: other"))
    write(repo, "docs/design/inventory.md", INVENTORY)
    assert plan_intake.main(["states", "--root", str(repo)]) == 0
    assert capsys.readouterr().out.strip() == "ok states (none to ask)"
