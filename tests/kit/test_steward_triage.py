"""Tests of scripts/agk/steward_evidence.py: triage, filing and skills first (SPEC-0059 rules 6, 7,
9, 12 and 19; brief #1321, ADR-0558; REQ-066).

Rule 6's outbound data guard is build (e) and is not tested here. Invented data only (example.com),
no network, no model.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

import steward_evidence as ev  # noqa: E402

BRIEF = """Sentence: "Add a report export for example.com projects."

Answers:
1. The export writes one file.

Contexts: kit (not applicable: project only); github (the same); local (the same); personal (the \
same); stacks (not applicable: no stack change).
Modes: github the same; local the same; personal printed for the developer
Advances: new
Priority: {priority}
Measured: before: `make export` fails (1 failed); after: 1 passed.
Size: S
Touches: src/export.py
"""
OWNER = 'Owner said (2026-11-15T10:00Z): "file the export brief"'


@pytest.fixture
def project(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "neutrality.txt").write_text("widgetcorp\n", encoding="utf-8")
    (tmp_path / "agk.toml").write_text('default_branch = "main"\n', encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "requirements.md").write_text("# Requirements\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "export.py").write_text("", encoding="utf-8")
    return tmp_path


def finding(triage="project brief", priority=0, text=None, **more) -> dict:
    return {
        "id": "F-1",
        "triage": triage,
        "why": "the export is missing",
        "text": BRIEF.format(priority=priority) if text is None else text,
        **more,
    }


def test_req066_each_finding_gets_exactly_one_triage_and_one_entry(project):
    """REQ-066: rule 6, one of the kit, a project brief or an owner question, with `Triage:`."""
    for choice in ev.TRIAGES:
        found = ev.triage(finding(choice, text=BRIEF.format(priority=0) + OWNER), project)
        assert found["entry"] == f"Triage: F-1 {choice}: the export is missing"
    refused = ev.triage(finding("both"), project)
    assert refused["action"] == "refused" and "one triage" in refused["lines"][0]
    assert ev.triage(finding("owner question"), project)["action"] == "ask"


def test_req066_a_project_brief_at_or_below_auto_file_is_filed(project):
    """REQ-066: rules 6 and 12, `auto_file` 0 by default files a `Priority: 0` brief."""
    assert ev.triage(finding(), project)["action"] == "file"


def test_req066_a_brief_above_auto_file_needs_the_owners_word(project):
    """REQ-066: rules 6 and 12, refused naming the setting, never the value."""
    found = ev.triage(finding(priority=2), project)
    assert found["action"] == "refused" and "steward.auto_file" in found["lines"][0]
    assert ev.triage(finding(text=BRIEF.format(priority=2) + OWNER), project)["action"] == "file"
    (project / "agk.toml").write_text("[steward]\nauto_file = 2\n", encoding="utf-8")
    assert ev.triage(finding(priority=2), project)["action"] == "file"
    (project / "agk.toml").write_text("[steward]\nauto_file = false\n", encoding="utf-8")
    assert ev.triage(finding(priority=0), project)["action"] == "refused"


def test_req066_a_brief_that_fails_check_brief_is_never_filed(project):
    """REQ-066: rule 6, no `MALFORMED:` line follows a filing."""
    found = ev.triage(finding(text=BRIEF.format(priority=0).replace("Size: S\n", "")), project)
    assert found["action"] == "refused" and "check_brief" in found["lines"][0]


def test_req066_a_neutrality_token_refuses_naming_the_list_not_the_value(project):
    """REQ-066: rule 6, check_neutrality's list on the text, fail closed."""
    text = BRIEF.format(priority=0).replace("example.com", "WidgetCorp")
    found = ev.triage(finding(text=text), project)
    assert found["action"] == "refused" and "config/neutrality.txt" in found["lines"][0]
    assert "widgetcorp" not in " ".join(found["lines"]).lower()
    (project / "config" / "neutrality.txt").unlink()
    assert ev.triage(finding(), project)["action"] == "refused"


def test_req066_a_brief_or_correction_carries_its_modes_line(project):
    """REQ-066: rule 7, `Modes: github <effect>; local <effect>; personal <effect>`."""
    text = BRIEF.format(priority=0).replace("Modes: github", "Mode: github")
    found = ev.triage(finding(text=text), project)
    assert found["action"] == "refused" and "Modes:" in found["lines"][0]
    correction = "Correction: the export names one file.\nModes: github a; local b; personal c\n"
    assert ev.triage(finding("kit correction", text=correction + OWNER), ROOT)["action"] == "file"


def test_req066_a_cause_is_reproduced_on_the_default_branch_before_it_is_filed(project):
    """REQ-066: rule 7."""
    found = ev.triage(finding(cause=True), project)
    assert found["action"] == "refused" and "reproduced" in found["lines"][0]
    done = finding(cause=True, reproduced="make export: 1 failed")
    assert ev.triage(done, project)["action"] == "file"


def test_req066_nothing_goes_to_the_kit_from_a_customer_project_before_build_e(project):
    """REQ-066: rule 17 (e), a kit brief from a customer project is a draft for the owner."""
    found = ev.triage(finding("kit brief"), project)
    assert found["action"] == "draft" and "draft" in found["lines"][0]
    assert ev.triage(finding("kit brief"), ROOT)["action"] == "file"


# --- rule 19: skills first ----------------------------------------------------------------------


def test_req066_each_step_uses_the_skill_of_the_agent_files_table():
    """REQ-066: rule 19, the table is read from the agent file, never a second copy."""
    table = ev.skills(ROOT)
    assert table["plan"] == "`plan-intake`, then `scope-lock`"
    assert table["a brief for a build"] == "`brief`"
    for stage in ev.STAGES[:-1]:
        assert any(stage in step for step in table), stage
    assert ev.skill_line(ROOT, "scope") == "skill: `scope-review`"


def test_req066_a_step_with_no_skill_produces_one_kit_brief(capsys):
    """REQ-066: rule 19, the step is done once by hand and a kit brief for the skill is filed."""
    line = ev.skill_line(ROOT, "translate the release notes")
    assert line.startswith("no skill: ") and "kit brief" in line
    assert ev.main(["skill", "--step", "translate the release notes"]) == 3
    assert capsys.readouterr().out.count("kit brief") == 1


def test_req066_the_agent_file_names_the_evidence_commands():
    """REQ-066: rule 19 and rule 2, the agent file calls the script and names no hand flow."""
    text = (ROOT / ".claude" / "agents" / "steward.md").read_text(encoding="utf-8")
    for command in ("stage", "settle", "answer", "triage", "skill"):
        assert f"steward_evidence.py {command}" in text
