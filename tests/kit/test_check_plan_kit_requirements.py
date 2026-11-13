"""Tests of the plan check and the kit's own requirements (brief #1183, ADR-0502; REQ-050).

`init.py` installs `docs/requirements.md` with the kit's REQ-001 to REQ-003, which the file reserves
(REQ-001 to REQ-099) for the kit and which carry no `Source:` line. Rule 10's `Source:` test and the
counts of rule 11 leave out a requirement of that range with no `Source:` line; one that carries a
`Source:` line is still checked, and a project requirement (REQ-101) is checked as before.
Invented files only (example.com), in `tmp_path`; no network.
"""

from __future__ import annotations

from pathlib import Path

import check_plan

SOW = (
    "Source: Example statement of work\nKind: sow\nVersion: 1\nDate: 2026-10-01\n\n"
    "# Orders\n\n"
    "The portal at example.com lists orders.\n"  # line 8
)
SCOPE = "# Scope\n\n## In scope\n\n- Orders are listed `docs/sources/sow.md:8`\n"
KIT = (
    "# Requirements\n\n"
    "REQ-001 to REQ-099 are reserved for the kit.\n\n"
    "### REQ-001 — Protected paths change only with an ADR in the same PR\n\n"
    "- Acceptance: AC1 check fails without ADR\n- Status: done\n\n"
    "### REQ-002 — Agents never merge or bypass checks\n\n"
    "- Acceptance: AC1 branch rules documented\n- Status: in-progress\n\n"
    "### REQ-003 — Every requirement is traceable to tests\n\n"
    "- Acceptance: AC1 matrix generated\n- Status: done\n"
)
REQ_101 = (
    "\n### REQ-101 — Orders are listed\n\n"
    "- Acceptance: AC1 the orders page at example.com lists orders\n"
    "- Status: planned\n- Source: {source}\n"
)
MILESTONES = "# Milestones\n\n### M1 Orders\n\nExit: all 1 briefs merged.\nTarget: 2026-12-18\n"
BRIEF = "Advances: REQ-101\nTouches: app/list.py\nPriority: 1\nSize: S\nMilestone: M1\n"


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def project(root: Path, source: str = "docs/sources/sow.md:8", extra: str = "") -> Path:
    """An invented project: the kit's three requirements, REQ-101 and a plan."""
    write(root, "docs/sources/sow.md", SOW)
    write(root, "docs/plan/scope.md", SCOPE)
    write(root, "docs/plan/milestones.md", MILESTONES)
    write(root, "docs/plan/briefs/M1/m1-list.md", BRIEF)
    write(root, "docs/requirements.md", KIT + REQ_101.format(source=source) + extra)
    return root


def check(root: Path, capsys, *args: str) -> tuple[int, list[str]]:
    code = check_plan.main(["--root", str(root), *args])
    return code, capsys.readouterr().out.splitlines()


def failures(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith("FAIL ")]


def test_kit_requirements_without_source_pass_rule_10(tmp_path: Path, capsys) -> None:
    # REQ-050: (a) the kit's REQ-001 to REQ-003 have no Source: line and are not failed.
    code, lines = check(project(tmp_path), capsys)
    assert failures(lines) == []
    assert code == 0
    assert lines[-1].startswith("ok plan: 1 of 1 in-scope source lines have a requirement")


def test_kit_requirements_are_left_out_of_the_counts(tmp_path: Path, capsys) -> None:
    # REQ-050: the requirement counts of rule 11 count REQ-101 alone.
    root = project(tmp_path)
    code, lines = check(root, capsys, "--facts", str(facts(root)))
    assert code == 0
    assert "1 of 1 requirements have a brief" in lines[-1]
    assert "of 1 requirements have a test" in lines[-1]


def test_trace_prints_no_row_for_kit_requirements(tmp_path: Path, capsys) -> None:
    # REQ-050: the trace names REQ-101 and none of the kit's requirements.
    _, lines = check(project(tmp_path), capsys, "--trace")
    text = "\n".join(lines)
    assert "REQ-101" in text
    for kit in ("REQ-001", "REQ-002", "REQ-003"):
        assert kit not in text


def test_project_requirement_without_resolving_source_fails(tmp_path: Path, capsys) -> None:
    # REQ-050: (b) REQ-101 whose Source: line does not resolve still fails rule 10.
    code, lines = check(project(tmp_path, source="docs/sources/missing.md:3"), capsys)
    assert code == 1
    assert "FAIL plan: rule 10: docs/requirements.md: REQ-101: no Source: line resolves" in lines
    assert not any("REQ-00" in line for line in failures(lines))


def test_kit_requirement_with_unresolving_source_still_fails(tmp_path: Path, capsys) -> None:
    # REQ-050: (c) a REQ-005 that carries a Source: line is checked like any other.
    extra = (
        "\n### REQ-005 — Reviewer groups own path classes\n\n"
        "- Status: planned\n- Source: docs/sources/missing.md:3\n"
    )
    code, lines = check(project(tmp_path, extra=extra), capsys)
    assert code == 1
    assert failures(lines) == [
        "FAIL plan: rule 10: docs/requirements.md: REQ-005: no Source: line resolves"
    ]


def test_project_requirement_without_source_line_fails(tmp_path: Path, capsys) -> None:
    # REQ-050: REQ-101 with no Source: line at all is not left out: the range is the kit's only.
    root = project(tmp_path)
    text = (root / "docs/requirements.md").read_text(encoding="utf-8")
    write(root, "docs/requirements.md", text.replace("- Source: docs/sources/sow.md:8\n", ""))
    code, lines = check(root, capsys)
    assert code == 1
    assert "FAIL plan: rule 10: docs/requirements.md: REQ-101: no Source: line resolves" in lines


def facts(root: Path) -> Path:
    path = root.parent / "facts.json"
    path.write_text('{"pull_requests": []}\n', encoding="utf-8")
    return path
