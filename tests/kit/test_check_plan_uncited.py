"""Tests of the plan check and the source documents no requirement cites (brief #1217, ADR-0516;
REQ-050).

Rule 10 (amendment 175 item 1): once `docs/plan/` exists, every file under `docs/sources/` has at
least one location that a requirement's `Source:` line cites (and that resolves), or is listed by
its own path under `Out of scope` in `docs/plan/scope.md` with a reason; otherwise one line
`FAIL plan: <file> is a source no requirement cites (list it out of scope or cite it)`, naming
the file and never its text. Rule 9 (item 2): `--trace` prints one line per source file,
`<file>: <a> of <b> headings or rows cited`, and the coverage line stays as it was.
Invented files only (example.com), in `tmp_path`; no network.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "check_plan.py"

SOW = (
    "Source: Example statement of work\nKind: sow\nVersion: 1\nDate: 2026-10-01\n\n"
    "# Orders\n\n"  # line 6
    "The portal at example.com lists orders.\n"  # line 8
)
NOTES = (
    "Source: Example context notes\nKind: other\nVersion: 1\nDate: 2026-10-02\n\n"
    "# Background\n\n"  # line 6
    "The shop at example.com sells tea.\n\n"  # line 8
    "# Decisions\n\n"  # line 10
    "| Id | Decision |\n"  # line 12
    "| --- | --- |\n"  # line 13
    "| D1 | Orders are listed by date |\n"  # line 14
    "| D2 | Invoices are sent by mail |\n"  # line 15
    "\n"
    "```\n# not a heading\n```\n"
)
SECRET_TEXT = "sells tea"  # a source's text; never printed
HANDOFF = (
    "Source: Example handoff\nKind: other\nVersion: 1\nDate: 2026-10-03\n\nOne line of text.\n"
)
SCOPE = "# Scope\n\n## In scope\n\n- Orders are listed (`docs/sources/sow.md:8`)\n"
REQS = (
    "# Proposed requirements\n\n"
    "### orders-list Orders are listed\n\n"
    "- Status: planned\n"
    "- Source: docs/sources/sow.md:8\n"
)
MILESTONES = "# Milestones\n\n### M1 Orders\n\nExit: all 1 requirements have a brief.\n"
BRIEF = "Advances: orders-list\nTouches: app/orders.py\nPriority: 1\nSize: S\nMilestone: M1\n"
FAIL_NOTES = (
    "FAIL plan: docs/sources/notes.md is a source no requirement cites "
    "(list it out of scope or cite it)"
)


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def plan(root: Path, *, scope: str = SCOPE, reqs: str = REQS) -> Path:
    """The invented project: a cited statement of work, uncited context notes and a plan."""
    write(root, "docs/sources/sow.md", SOW)
    write(root, "docs/sources/notes.md", NOTES)
    write(root, "docs/plan/scope.md", scope)
    write(root, "docs/plan/requirements-proposed.md", reqs)
    write(root, "docs/plan/milestones.md", MILESTONES)
    write(root, "docs/plan/briefs/M1/orders-page.md", BRIEF)
    return root


def check(root: Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return proc.returncode, proc.stdout + proc.stderr


def fails(out: str) -> list[str]:
    return [line for line in out.splitlines() if line.startswith("FAIL plan: ")]


def test_ac3_a_source_no_requirement_cites_fails_naming_the_file(tmp_path):
    """REQ-050 AC3: amendment 175 item 1, an uncited source fails with one line, never its text;
    the coverage line stays and still counts the in-scope lines only."""
    code, out = check(plan(tmp_path))
    assert code == 1, out
    assert fails(out) == [FAIL_NOTES]
    assert SECRET_TEXT not in out
    assert out.splitlines()[-1].startswith(
        "plan: 1 of 1 in-scope source lines have a requirement, "
    )


def test_ac3_each_uncited_source_fails_once(tmp_path):
    """REQ-050 AC3: item 1, one line per uncited document, at any depth under docs/sources/."""
    plan(tmp_path)
    write(tmp_path, "docs/sources/adr/handoff.txt", HANDOFF)
    code, out = check(tmp_path)
    assert code == 1, out
    assert fails(out) == [
        "FAIL plan: docs/sources/adr/handoff.txt is a source no requirement cites "
        "(list it out of scope or cite it)",
        FAIL_NOTES,
    ]


def test_ac3_a_source_listed_out_of_scope_with_a_reason_passes(tmp_path):
    """REQ-050 AC3: item 1, the file's own path under Out of scope with a reason passes."""
    scope = SCOPE + "\n## Out of scope\n\n- Context only, no work (`docs/sources/notes.md`)\n"
    code, out = check(plan(tmp_path, scope=scope))
    assert code == 0, out
    assert fails(out) == []


def test_ac3_an_out_of_scope_line_without_a_reason_does_not_pass(tmp_path):
    """REQ-050 AC3: item 1, a line that holds only the path gives no reason, so it still fails."""
    scope = SCOPE + "\n## Out of scope\n\n- `docs/sources/notes.md`\n"
    code, out = check(plan(tmp_path, scope=scope))
    assert code == 1, out
    assert fails(out) == [FAIL_NOTES]


def test_ac3_a_location_out_of_scope_does_not_cover_the_whole_file(tmp_path):
    """REQ-050 AC3: item 1, an Out of scope location of one line is not the file listed, and a
    path under In scope is not Out of scope."""
    scope = (
        SCOPE.replace(
            "(`docs/sources/sow.md:8`)", "(`docs/sources/sow.md:8`, `docs/sources/notes.md`)"
        )
        + "\n## Out of scope\n\n- Tea is not sold here (`docs/sources/notes.md:8`)\n"
    )
    code, out = check(plan(tmp_path, scope=scope))
    assert code == 1, out
    assert FAIL_NOTES in fails(out)


def test_ac3_one_citation_passes_and_the_trace_shows_the_count(tmp_path):
    """REQ-050 AC3: items 1 and 2, one resolving citation passes; the trace prints one line per
    source with its headings and table rows (fenced lines aside) cited."""
    reqs = (
        REQS
        + "\n### dated Orders by date\n\n- Status: planned\n- Source: docs/sources/notes.md:14\n"
    )
    code, out = check(plan(tmp_path, reqs=reqs), "--trace")
    assert code == 0, out
    assert fails(out) == []
    lines = out.splitlines()
    assert "docs/sources/notes.md: 1 of 4 headings or rows cited" in lines
    assert "docs/sources/sow.md: 0 of 1 headings or rows cited" in lines
    assert lines[-1].startswith("ok plan: 1 of 1 in-scope source lines have a requirement, ")


def test_ac3_a_heading_cited_by_name_or_by_line_counts_once(tmp_path):
    """REQ-050 AC3: item 2, `#<heading>` and `:<line>` of the same heading are one cited heading."""
    reqs = REQS + (
        "\n### background Background\n\n- Status: planned\n"
        "- Source: docs/sources/notes.md#Background\n- Source: docs/sources/notes.md:6\n"
    )
    code, out = check(plan(tmp_path, reqs=reqs), "--trace")
    assert code == 0, out
    assert "docs/sources/notes.md: 1 of 4 headings or rows cited" in out.splitlines()


def test_ac3_a_citation_that_does_not_resolve_does_not_count(tmp_path):
    """REQ-050 AC3: item 1, a location past the file's end cites nothing."""
    reqs = REQS.replace(
        "- Source: docs/sources/sow.md:8\n",
        "- Source: docs/sources/sow.md:8\n- Source: docs/sources/notes.md:999\n",
    )
    code, out = check(plan(tmp_path, reqs=reqs))
    assert code == 1, out
    assert fails(out) == [FAIL_NOTES]


def test_ac3_a_project_with_no_plan_is_not_checked(tmp_path):
    """REQ-050 AC3: rule 10, with no docs/plan/ an uncited source prints `ok plan (no plan)`."""
    write(tmp_path, "docs/sources/notes.md", NOTES)
    assert check(tmp_path) == (0, "ok plan (no plan)\n")
