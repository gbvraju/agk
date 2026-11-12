"""Tests of `check_plan.py`, the trace and the coverage (SPEC-0043 rules 9 to 11; REQ-050 AC3).

Rule 9: `--trace` prints one row per source location, from the location to its requirement, the
spec rule, the brief, the merged pull request (with `--facts FILE`) and the test, `none` where a
link is missing, and writes nothing. Rule 10: a requirement without a resolving `Source:` line,
an `In scope` location no requirement cites, a `## <screen>/<state>` heading of a `Kind: design`
source no requirement cites (amendment 163 item 4) and a milestone no brief names each fail,
naming the rule and the item, never its text. Rule 11: the coverage line's counts equal a hand
count, and the last three read `not read` without `--facts`. Invented files only (example.com),
in `tmp_path`; no network.
"""

from __future__ import annotations

import json
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import check_plan

PROPOSED = "docs/plan/requirements-proposed.md"
KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "check_plan.py"

SOW = (
    "Source: Example statement of work\nKind: sow\nVersion: 1\nDate: 2026-10-01\n\n"
    "# Orders\n\n"  # line 6
    "The portal at example.com lists orders.\n"  # line 8
    "\n"
    "# Invoices\n\n"  # line 10
    "Each order has an invoice.\n"  # line 12
)
PROTOTYPE = (
    "Source: imported prototype i1\nKind: design\nVersion: i1 abc123\nDate: 2026-11-12\n\n"
    "## orders/default\n\nOrders\n\n"
    "## orders/empty\n\nNo orders yet\n\n"
    "## cart/default\n\nCart\n"
)
TITLE = "Orders are listed"  # a requirement's text; never printed in a failure

SCOPE = (
    "# Scope\n\n"
    "## In scope\n\n"
    "- Orders are listed `docs/sources/sow.md:8`\n"  # scope.md line 5
    "- Invoices `docs/sources/sow.md#Invoices`\n"  # scope.md line 6
    "\n"
    "## Out of scope\n\n"
    "- Payments `docs/sources/sow.md:12`\n"
)
REQS = (
    "# Proposed requirements\n\n"
    f"### orders-list {TITLE}\n\n"
    "- Criteria: Given orders, when the list opens, then each order shows.\n"
    "- Status: planned\n"
    "- Source: docs/sources/sow.md:8\n"
    "- Source: docs/sources/shop-prototype-i1.md#orders/default\n"
    "\n"
    "### invoices Invoices are shown\n\n"
    "- Status: planned\n"
    "- Source: docs/sources/sow.md#Invoices\n"
)
MILESTONES = (
    "# Milestones\n\n"
    "### M1 Orders\n\nExit: all 2 requirements have a brief.\n\n"
    "### M2 Invoices\n\nExit: all 1 requirements have a brief.\n"
)
BRIEF = "Advances: orders-list\nTouches: app/orders.py\nPriority: 1\nSize: S\nMilestone: M1\n"


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def plan(root: Path, *, prototype: bool = True) -> Path:
    """The invented project: one statement of work, a prototype source and a plan."""
    write(root, "docs/sources/sow.md", SOW)
    if prototype:
        write(root, "docs/sources/shop-prototype-i1.md", PROTOTYPE)
    write(root, "docs/plan/scope.md", SCOPE)
    write(root, "docs/plan/requirements-proposed.md", REQS)
    write(root, "docs/plan/milestones.md", MILESTONES)
    write(root, "docs/plan/briefs/M1/orders-page.md", BRIEF)
    write(
        root,
        "docs/plan/briefs/M2/invoice-page.md",
        BRIEF.replace("orders-list", "invoices").replace("M1", "M2"),
    )
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


def last(out: str) -> str:
    return out.splitlines()[-1]


# --- rule 10: the checks of the plan -----------------------------------------------------------


def test_ac3_a_complete_plan_passes_with_the_coverage_line(tmp_path):
    """REQ-050 AC3: rules 10 and 11, every location cited and every milestone named: exit 0."""
    plan(tmp_path, prototype=False)
    code, out = check(tmp_path)
    assert code == 0, out
    assert fails(out) == []
    assert last(out) == (
        "ok plan: 2 of 2 in-scope source lines have a requirement, "
        "requirements have a brief: not read, briefs have a merged pull request: not read, "
        "requirements have a test: not read"
    )


def test_ac3_a_project_with_no_plan_still_passes(tmp_path):
    """REQ-050 AC3: rule 10, no docs/plan/ prints `ok plan (no plan)`, even with --trace."""
    write(tmp_path, "docs/sources/shop-prototype-i1.md", PROTOTYPE)
    assert check(tmp_path) == (0, "ok plan (no plan)\n")
    assert check(tmp_path, "--trace") == (0, "ok plan (no plan)\n")


def test_ac3_a_requirement_without_a_resolving_source_fails(tmp_path):
    """REQ-050 AC3: rule 10, a requirement block with no Source: line that resolves."""
    plan(tmp_path, prototype=False)
    write(
        tmp_path,
        "docs/plan/requirements-proposed.md",
        REQS.replace("- Source: docs/sources/sow.md#Invoices", "- Source: docs/sources/sow.md:999")
        + "\n### refunds Refunds\n\n- Status: planned\n",
    )
    code, out = check(tmp_path)
    assert code == 1, out
    assert fails(out) == [
        f"FAIL plan: rule 10: {PROPOSED}: invoices: no Source: line resolves",
        f"FAIL plan: rule 10: {PROPOSED}: refunds: no Source: line resolves",
        "FAIL plan: rule 10: docs/plan/scope.md:6: no requirement cites "
        "docs/sources/sow.md#Invoices",
    ]
    assert TITLE not in out


def test_ac3_one_resolving_source_is_enough(tmp_path):
    """REQ-050 AC3: rule 10 fails only a block with no resolving Source: line."""
    plan(tmp_path, prototype=False)
    write(
        tmp_path,
        "docs/plan/requirements-proposed.md",
        REQS.replace(
            "- Status: planned\n- Source: docs/sources/sow.md#",
            "- Status: planned\n- Source: docs/x.md:1\n- Source: docs/sources/sow.md#",
        ),
    )
    code, out = check(tmp_path)
    assert code == 0, out


def test_ac3_a_requirement_of_the_requirements_file_needs_a_source(tmp_path):
    """REQ-050 AC3: rule 10 reads docs/requirements.md's blocks too, by their REQ id."""
    plan(tmp_path, prototype=False)
    write(
        tmp_path,
        "docs/requirements.md",
        "# Requirements\n\n### REQ-001 Orders\n\n- Status: planned\n"
        "- Source: docs/sources/sow.md:8\n\n"
        "### REQ-002 Search\n\n- Status: planned\n",
    )
    code, out = check(tmp_path)
    assert code == 1, out
    assert fails(out) == [
        "FAIL plan: rule 10: docs/requirements.md: REQ-002: no Source: line resolves"
    ]


def test_ac3_an_uncited_in_scope_line_fails_and_out_of_scope_is_not_read(tmp_path):
    """REQ-050 AC3: rule 10, an In scope location no requirement cites; Out of scope is not read."""
    plan(tmp_path, prototype=False)
    write(
        tmp_path,
        "docs/plan/scope.md",
        SCOPE.replace("- Invoices", "- Refunds `docs/sources/sow.md:12`\n- Invoices"),
    )
    code, out = check(tmp_path)
    assert code == 1, out
    assert fails(out) == [
        "FAIL plan: rule 10: docs/plan/scope.md:6: no requirement cites docs/sources/sow.md:12"
    ]
    assert "Refunds" not in out
    assert last(out).startswith("plan: 2 of 3 in-scope source lines have a requirement, ")


def test_ac3_an_in_scope_line_with_no_location_fails(tmp_path):
    """REQ-050 AC3: rules 7 and 10, an In scope line ends with its locations."""
    plan(tmp_path, prototype=False)
    write(tmp_path, "docs/plan/scope.md", SCOPE.replace("- Invoices", "- Refunds\n- Invoices"))
    code, out = check(tmp_path)
    assert code == 1, out
    assert fails(out) == [
        "FAIL plan: rule 10: docs/plan/scope.md:6: an In scope line names no location"
    ]
    assert last(out).startswith("plan: 2 of 3 in-scope source lines have a requirement, ")


def test_ac3_a_milestone_no_brief_names_fails(tmp_path):
    """REQ-050 AC3: rule 10, a milestone of milestones.md that no brief file names."""
    plan(tmp_path, prototype=False)
    write(
        tmp_path,
        "docs/plan/milestones.md",
        MILESTONES + "\n### M3 Refunds\n\nExit: all 0 briefs.\n",
    )
    code, out = check(tmp_path)
    assert code == 1, out
    assert fails(out) == [
        "FAIL plan: rule 10: docs/plan/milestones.md: M3: no brief names this milestone"
    ]
    assert "Refunds" not in out


# --- amendment 163 item 4: the prototype's screens and states -----------------------------------


def test_ac3_a_prototype_source_with_three_screens_and_two_cited_prints_2_of_3(tmp_path):
    """REQ-050 AC3: rule 11 (amendment 163 item 4), each `## <screen>/<state>` heading of a
    `Kind: design` source is one in-scope location; two requirements cite two of three."""
    write(tmp_path, "docs/sources/shop-prototype-i1.md", PROTOTYPE)
    write(
        tmp_path,
        "docs/plan/requirements-proposed.md",
        "### orders-list Orders\n\n- Source: docs/sources/shop-prototype-i1.md#orders/default\n\n"
        "### cart Cart\n\n- Source: docs/sources/shop-prototype-i1.md#cart/default\n",
    )
    code, out = check(tmp_path)
    assert code == 1, out
    assert fails(out) == [
        "FAIL plan: rule 10: docs/sources/shop-prototype-i1.md#orders/empty: "
        "no requirement cites this screen and state"
    ]
    assert last(out).startswith("plan: 2 of 3 in-scope source lines have a requirement, ")


def test_ac3_the_same_headings_in_another_kind_are_not_counted(tmp_path):
    """REQ-050 AC3: rule 11, only a `Kind: design` source's screen headings count."""
    write(tmp_path, "docs/sources/notes.md", PROTOTYPE.replace("Kind: design", "Kind: other"))
    (tmp_path / "docs" / "plan").mkdir(parents=True)
    code, out = check(tmp_path)
    assert code == 0, out
    assert last(out).startswith("ok plan: 0 of 0 in-scope source lines have a requirement, ")


def test_ac3_a_design_heading_without_a_slash_is_not_a_screen(tmp_path):
    """REQ-050 AC3: rule 11, only a level-two `<screen>/<state>` heading outside a fence."""
    text = (
        PROTOTYPE.replace("## cart/default", "## Notes")
        + "\n```\n## search/default\n```\n### list/empty\n"
    )
    write(tmp_path, "docs/sources/shop-prototype-i1.md", text)
    write(
        tmp_path,
        "docs/plan/requirements-proposed.md",
        "### orders Orders\n\n- Source: docs/sources/shop-prototype-i1.md#orders/default\n"
        "- Source: docs/sources/shop-prototype-i1.md#orders/empty\n",
    )
    code, out = check(tmp_path)
    assert code == 0, out
    assert last(out).startswith("ok plan: 2 of 2 in-scope source lines have a requirement, ")


def test_ac3_a_screen_listed_in_scope_too_is_counted_once(tmp_path):
    """REQ-050 AC3: rule 11, a screen heading also listed under In scope is one location."""
    plan(tmp_path)
    write(
        tmp_path,
        "docs/plan/scope.md",
        SCOPE.replace(
            "- Invoices",
            "- Orders screen `docs/sources/shop-prototype-i1.md#orders/default`\n- Invoices",
        ),
    )
    code, out = check(tmp_path)
    assert last(out).startswith("plan: 3 of 5 in-scope source lines have a requirement, "), out


# --- rule 11: the coverage counts with the facts ------------------------------------------------


def facts(root: Path) -> Path:
    data = {
        "schema": 1,
        "pull_requests": [
            {"number": 31, "state": "merged", "brief": 21},
            {"number": 32, "state": "closed", "brief": 22},
            {"number": 33, "state": "open", "brief": 22},
        ],
    }
    return write(root, "out/facts.json", json.dumps(data))


def numbers(root: Path) -> Path:
    return write(root, "out/numbers.json", json.dumps({"orders-page": 21, "invoice-page": 22}))


def test_ac3_the_counts_with_facts_equal_a_hand_count(tmp_path):
    """REQ-050 AC3: rule 11, a hand count: 3 of 5 locations (two sow lines, three screens), 2 of 2
    requirements with a brief, 1 of 2 briefs merged (#31 for #21), 0 of 2 with a test (keys)."""
    plan(tmp_path)
    code, out = check(
        tmp_path, "--facts", str(facts(tmp_path)), "--numbers", str(numbers(tmp_path))
    )
    assert code == 1, out
    assert last(out) == (
        "plan: 3 of 5 in-scope source lines have a requirement, "
        "2 of 2 requirements have a brief, 1 of 2 briefs have a merged pull request, "
        "0 of 2 requirements have a test"
    )


def test_ac3_a_requirement_with_a_test_marker_counts(tmp_path):
    """REQ-050 AC3: rule 11, the test count reads the REQ markers of the tests."""
    plan(tmp_path, prototype=False)
    write(
        tmp_path, "docs/requirements.md", "### REQ-007 Orders\n\n- Source: docs/sources/sow.md:8\n"
    )
    write(tmp_path, "tests/test_orders.py", '"""REQ-007 AC1: orders."""\n')
    write(tmp_path, "docs/plan/briefs/M1/orders-page.md", BRIEF.replace("orders-list", "REQ-007"))
    code, out = check(tmp_path, "--facts", str(facts(tmp_path)))
    assert code == 0, out
    assert last(out) == (
        "ok plan: 2 of 2 in-scope source lines have a requirement, "
        "2 of 3 requirements have a brief, 0 of 2 briefs have a merged pull request, "
        "1 of 3 requirements have a test"
    )


def test_ac3_unknown_pull_requests_in_the_facts_read_not_read(tmp_path):
    """REQ-050 AC3: rule 11, facts whose pull requests are `unknown` give no merged count."""
    plan(tmp_path, prototype=False)
    path = write(tmp_path, "out/facts.json", json.dumps({"schema": 1, "pull_requests": "unknown"}))
    code, out = check(tmp_path, "--facts", str(path))
    assert code == 0, out
    assert ", briefs have a merged pull request: not read, " in last(out)


def test_ac3_an_unreadable_facts_file_is_a_usage_error(tmp_path):
    """REQ-050 AC3: rule 11, a facts file that is not JSON exits 2 naming --facts only."""
    plan(tmp_path, prototype=False)
    path = write(tmp_path, "out/facts.json", "not json at all")
    code, out = check(tmp_path, "--facts", str(path))
    assert code == 2, out
    assert "--facts" in out
    assert "not json at all" not in out


# --- rule 9: the trace -------------------------------------------------------------------------


def trace_rows(out: str) -> dict[str, list[str]]:
    rows = [line for line in out.splitlines() if line.startswith("| docs/")]
    return {
        cells[0]: cells[1:]
        for cells in ([c.strip() for c in row.strip("|").split("|")] for row in rows)
    }


def test_ac3_the_trace_prints_one_row_per_source_location(tmp_path):
    """REQ-050 AC3: rule 9, one row per location, `none` where a link is missing."""
    plan(tmp_path)
    code, out = check(
        tmp_path, "--trace", "--facts", str(facts(tmp_path)), "--numbers", str(numbers(tmp_path))
    )
    head = "| Location | Requirement | Persona | Spec rule | Brief | Pull request | Test |"
    assert head in out  # the persona column of amendment 164 item 2 (ADR-0462)
    rows = trace_rows(out)
    assert list(rows) == [
        "docs/sources/sow.md:8",
        "docs/sources/sow.md#Invoices",
        "docs/sources/shop-prototype-i1.md#orders/default",
        "docs/sources/shop-prototype-i1.md#orders/empty",
        "docs/sources/shop-prototype-i1.md#cart/default",
    ]
    assert rows["docs/sources/sow.md:8"] == [
        "orders-list",
        "none",
        "none",
        "orders-page",
        "#31",
        "none",
    ]
    assert rows["docs/sources/sow.md#Invoices"] == [
        "invoices",
        "none",
        "none",
        "invoice-page",
        "none",
        "none",
    ]
    assert rows["docs/sources/shop-prototype-i1.md#orders/empty"] == ["none"] * 6
    assert code == 1, out  # the checks still run after the trace


def test_ac3_the_trace_names_the_spec_rule_and_the_test(tmp_path):
    """REQ-050 AC3: rule 9, the spec naming the requirement, its citing rule, the test."""
    plan(tmp_path, prototype=False)
    write(
        tmp_path, "docs/requirements.md", "### REQ-007 Orders\n\n- Source: docs/sources/sow.md:8\n"
    )
    write(
        tmp_path,
        "docs/specs/0001-orders.md",
        "# SPEC-0001: Orders\n\n- Status: Approved\n- Requirements: REQ-007\n\n## Rules\n\n"
        "1. **List.** The list shows each order (REQ-007).\n2. **Other.** Nothing else.\n",
    )
    write(tmp_path, "tests/test_orders.py", '"""REQ-007 AC1: orders."""\n')
    write(tmp_path, "docs/plan/briefs/M1/orders-page.md", BRIEF.replace("orders-list", "REQ-007"))
    code, out = check(tmp_path, "--trace")
    assert code == 0, out
    row = trace_rows(out)["docs/sources/sow.md:8"]
    assert row == [
        "orders-list, REQ-007",
        "none",
        "SPEC-0001 rule 1",
        "orders-page",
        "not read",
        "tests/test_orders.py",
    ]


def test_ac3_the_trace_writes_nothing_and_opens_no_network(tmp_path, monkeypatch, capsys):
    """REQ-050 AC3: rule 9, the trace is printed and never written (principle 5); no network."""
    plan(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}

    def refuse(*args, **kwargs):
        raise AssertionError("the check opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    assert check_plan.main(["--root", str(tmp_path), "--trace"]) == 1
    assert "| Location |" in capsys.readouterr().out
    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before
    assert not (tmp_path / "docs" / "plan" / "trace.md").exists()


def test_ac3_the_trace_reuses_the_marker_reading_of_traceability():
    """REQ-050 AC3: rule 9, the REQ-to-test reading is common.py's, the one traceability.py uses."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert "markers_for" in source
    assert "MARKER_RUN" not in source and "REQ_ID.findall" not in source


def test_ac3_an_unknown_option_is_a_usage_error(tmp_path):
    """REQ-050 AC3: the options are --root, --trace, --facts and --numbers."""
    code, out = check(tmp_path, "--trace", "--wide")
    assert code == 2
    assert "usage: check_plan.py" in out
