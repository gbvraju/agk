"""Tests of `plan_intake.py render` (SPEC-0043 rule 7 with amendment 163 item 5; REQ-050).

REQ-050 AC2.

`render` runs `validate` first and refuses a file it fails; it prints every conflict under
`Conflicts for the person`, then the open questions under `Open questions for the person`, and
writes, as new files only and refusing to overwrite, exactly the scope, the milestones, the
proposed requirements, one Draft spec per area (`new_spec.make_spec`, imported) and one brief per
brief; `docs/requirements.md` stays byte for byte. Invented sources only (example.com), no network.
"""

from __future__ import annotations

import copy
import json
import re
import socket
from pathlib import Path

import check_brief
import check_plan
import new_spec
import plan_intake
import pytest
from test_plan_intake import CONFLICT, GOOD, PRD, PRD_TEXT, SOW, SOW_TEXT, TITLE, write

KIT_ROOT = Path(__file__).resolve().parents[2]
REQUIREMENTS = "# Requirements\n\n### REQ-101 — Example orders\n\n- Status: planned\n"
REQUIREMENTS += f"- Source: `{PRD}:8`\n"
LISTED = [
    "docs/plan/briefs/M1/B1.md",
    "docs/plan/briefs/M1/B2.md",
    "docs/plan/milestones.md",
    "docs/plan/requirements-proposed.md",
    "docs/plan/scope.md",
    "docs/specs/0001-orders.md",
]


@pytest.fixture(autouse=True)
def no_network(monkeypatch) -> None:
    def refuse(*args, **kwargs):
        raise AssertionError("render opens no socket")

    monkeypatch.setattr(socket, "socket", refuse)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    write(root, "scripts/agk/guard.py", "# the data guard (a placeholder of the fixture)\n")
    write(root, ".claude/hooks/data_guard.py", "# the read hook (a placeholder of the fixture)\n")
    write(root, SOW, SOW_TEXT)
    write(root, PRD, PRD_TEXT)
    write(root, "docs/requirements.md", REQUIREMENTS)
    write(root, "docs/specs/TEMPLATE.md", (KIT_ROOT / "docs/specs/TEMPLATE.md").read_text("utf-8"))
    return root


def proposals() -> dict:
    data = copy.deepcopy(GOOD)
    second = copy.deepcopy(data["briefs"][0]) | {"key": "B2", "depends_on": ["B1"]}
    data["briefs"].append(second)
    data["requirements"][0]["sources"].append(f"{SOW}:8")
    data["conflicts"] = [CONFLICT | {"settled": f"Settled: {SOW}:20"}]
    return data


def render(root: Path, data: object, capsys) -> tuple[int, str]:
    path = root.parent / "proposals.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    code = plan_intake.main(["render", "--proposals", str(path), "--root", str(root)])
    out = capsys.readouterr()
    return code, out.out + out.err


def tree(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_ac2_rule_7_render_writes_exactly_the_listed_files(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 7, the five kinds of file and nothing else."""
    before = tree(repo)
    code, out = render(repo, proposals(), capsys)
    assert code == 0, out
    after = tree(repo)
    assert sorted(set(after) - set(before)) == LISTED
    assert all(after[rel] == before[rel] for rel in before)
    for rel in LISTED:
        assert f"created {rel}" in out, out


def test_ac2_rule_7_the_files_hold_the_lines_of_the_rule(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 7, every line ending with its locations, Status: planned, Draft spec."""
    assert render(repo, proposals(), capsys)[0] == 0
    scope = (repo / "docs/plan/scope.md").read_text(encoding="utf-8")
    for heading in ("In scope", "Out of scope", "Assumptions", "Constraints", "Open questions"):
        assert f"\n## {heading}\n" in scope
    assert f"- {TITLE} (`{SOW}:8`)" in scope
    milestones = (repo / "docs/plan/milestones.md").read_text(encoding="utf-8")
    assert f"### M1 {TITLE}\n" in milestones
    for line in ("Exit: exit: all 3", "Acceptance: The list", "Target: 2026-12-18"):
        assert f"\n{line}" in milestones
    assert f"\nSource: `{SOW}#Milestones`\n" in milestones
    proposed = (repo / "docs/plan/requirements-proposed.md").read_text(encoding="utf-8")
    assert f"### R1 {TITLE}\n" in proposed
    assert "\nStatus: planned\n" in proposed and f"\nSource: `{PRD}:8`\n" in proposed
    spec = (repo / "docs/specs/0001-orders.md").read_text(encoding="utf-8")
    assert spec.startswith("# SPEC-0001: Orders\n") and "- Status: Draft" in spec
    assert "R1" in spec
    brief = (repo / "docs/plan/briefs/M1/B2.md").read_text(encoding="utf-8")
    for line in ("Advances: R1", "Touches: src/orders.py", "Size: M", "Expected: 4-8 hours"):
        assert f"\n{line}\n" in brief
    assert "\nMilestone: M1\n" in brief and f"\nSource: `{SOW}#Estimates`\n" in brief
    assert "\nDepends-on: B1\n" in brief


def test_ac2_rule_7_a_null_target_renders_as_an_open_question(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 7 with amendment 163 item 6, no target is the person's `(verify)`."""
    data = proposals()
    data["milestones"][0]["target"] = None
    assert render(repo, data, capsys)[0] == 0
    milestones = (repo / "docs/plan/milestones.md").read_text(encoding="utf-8")
    assert "\nTarget: (verify)\n" in milestones


def test_ac2_rule_7_a_second_render_refuses_and_changes_nothing(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 7, after render the files are the person's."""
    assert render(repo, proposals(), capsys)[0] == 0
    (repo / "docs/plan/scope.md").write_text("the person's edit\n", encoding="utf-8")
    before = tree(repo)
    code, out = render(repo, proposals(), capsys)
    assert code == 1 and "rule 7: docs/plan/scope.md already exists; nothing was written" in out
    assert tree(repo) == before


@pytest.mark.parametrize("rel", ["docs/plan/briefs/M1/B2.md", "docs/plan/requirements-proposed.md"])
def test_ac2_rule_7_any_existing_target_refuses_before_a_file_is_written(
    repo: Path, rel: str, capsys
) -> None:
    """REQ-050 AC2: rule 7, all or nothing: one existing file refuses the whole render."""
    write(repo, rel, "already here\n")
    before = tree(repo)
    code, out = render(repo, proposals(), capsys)
    assert code == 1 and f"rule 7: {rel} already exists; nothing was written" in out, out
    assert tree(repo) == before and "created " not in out


def test_ac2_rule_7_requirements_md_stays_byte_identical(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 7, `docs/requirements.md` is protected and never edited."""
    before = (repo / "docs/requirements.md").read_bytes()
    assert render(repo, proposals(), capsys)[0] == 0
    assert (repo / "docs/requirements.md").read_bytes() == before


def test_ac2_rule_7_every_rendered_brief_passes_check_brief(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 7, the shape of SPEC-0034 rule 2 and SPEC-0030 rule 4 as rendered; the
    keys of `Advances:` and `Depends-on:` are the only lines the person or `publish` replaces."""
    assert render(repo, proposals(), capsys)[0] == 0
    paths = sorted((repo / "docs/plan/briefs").rglob("*.md"))
    assert [p.name for p in paths] == ["B1.md", "B2.md"]
    for path in paths:
        body = path.read_text(encoding="utf-8")
        keyed = check_brief.body_problems(body, None, None)
        assert all("Advances" in p or "Depends-on" in p for p in keyed), keyed
        numbered = re.sub(r"(?m)^Advances: .*$", "Advances: REQ-101", body)
        numbered = re.sub(r"(?m)^Depends-on: .*$", "Depends-on: #12", numbered)
        path.write_text(numbered, encoding="utf-8")
        assert check_brief.main([str(path)]) == 0, capsys.readouterr().out
        assert check_brief.main([str(path), "--root", str(repo)]) == 0
    assert "ok brief" in capsys.readouterr().out


def test_ac2_rule_7_the_rendered_plan_passes_check_plan(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 7 feeds rule 10: every requirement cited, every milestone briefed."""
    assert render(repo, proposals(), capsys)[0] == 0
    trace = check_plan.Plan(repo, None, {})
    assert trace.problems() == []


def test_ac2_rule_6_conflicts_print_first_then_the_open_questions(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 6 and amendment 163 item 5, before any file is written."""
    code, out = render(repo, proposals(), capsys)
    assert code == 0, out
    conflicts = out.index("Conflicts for the person")
    questions = out.index("Open questions for the person")
    assert conflicts < questions < out.index("created ")
    assert f"- {SOW}:20 {PRD}:10: payments in or out (Settled: {SOW}:20)" in out
    assert f"- Who signs the list off? (verify) (`{SOW}#Scope`)" in out


def test_ac2_rule_7_render_refuses_what_validate_refuses(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 7, validate first; nothing is printed as a plan, nothing is written."""
    data = proposals()
    data["briefs"][0]["advances"] = ["R9"]
    before = tree(repo)
    code, out = render(repo, data, capsys)
    assert code == 1 and "rule 5: briefs B1: advances names nothing" in out, out
    assert "Conflicts for the person" not in out and tree(repo) == before


def test_ac2_rule_7_an_unsettled_conflict_is_refused_by_validate(repo: Path, capsys) -> None:
    """REQ-050 AC2: rules 6 and 7, nothing is resolved silently."""
    data = proposals()
    data["conflicts"] = [CONFLICT]
    data["requirements"][0]["sources"] = list(CONFLICT["locations"])
    code, out = render(repo, data, capsys)
    assert code == 1 and "cites both sides of conflict 1" in out, out
    assert not (repo / "docs/plan").exists()


@pytest.mark.parametrize(
    ("field", "value", "line"),
    [
        ("key", "../B1", "rule 7: briefs ../B1: the key is not a file name"),
        ("touches", [], "rule 7: briefs B1: touches is empty"),
        ("advances", [], "rule 7: briefs B1: advances is empty"),
        ("title", "x" * 301, "rule 7: briefs B1: the title is over 300 characters"),
    ],
)
def test_ac2_rule_7_a_brief_that_cannot_be_rendered_is_refused(
    repo: Path, field: str, value: object, line: str, capsys
) -> None:
    """REQ-050 AC2: rule 7, a brief that would fail SPEC-0034 rule 2 or leave its folder."""
    data = proposals()
    data["briefs"] = data["briefs"][:1]
    data["briefs"][0][field] = value
    before = tree(repo)
    code, out = render(repo, data, capsys)
    assert code == 1 and line in out, out
    assert tree(repo) == before


def test_ac2_rule_7_an_area_without_a_file_name_is_refused(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 7, `new_spec.slug` needs a letter or digit; nothing is written."""
    data = proposals()
    data["areas"][0]["name"] = "--"
    before = tree(repo)
    code, out = render(repo, data, capsys)
    assert code == 1 and "rule 7: areas --: the name has no letters or digits" in out, out
    assert tree(repo) == before


def test_ac2_rule_7_the_spec_comes_from_new_spec_make_spec(repo: Path, capsys, monkeypatch) -> None:
    """REQ-050 AC2: rule 7, `make_spec` of `new_spec.py spec`, imported, not copied."""
    calls: list[str] = []
    real = new_spec.make_spec
    monkeypatch.setattr(
        new_spec, "make_spec", lambda root, title, *a: calls.append(title) or real(root, title, *a)
    )
    assert render(repo, proposals(), capsys)[0] == 0
    assert calls == ["Orders"]


def test_ac2_rule_7_render_needs_the_spec_template(repo: Path, capsys) -> None:
    """REQ-050 AC2: rule 7, a missing template refuses before any file is written."""
    (repo / "docs/specs/TEMPLATE.md").unlink()
    before = tree(repo)
    code, out = render(repo, proposals(), capsys)
    assert code == 1 and "rule 7: docs/specs/TEMPLATE.md cannot be read" in out, out
    assert tree(repo) == before


def test_ac2_rule_7_render_needs_the_proposals_option(capsys) -> None:
    """REQ-050 AC2: rule 7, the usage line names the command."""
    assert plan_intake.main(["render"]) == 2
    assert "render --proposals FILE" in capsys.readouterr().err
