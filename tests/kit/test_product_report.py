"""Tests of scripts/agk/product_report.py (SPEC-0011 rules 3 to 14). No network, no model, no `gh`.

The goldens are the renderer's output on the facts fixtures: the eleven facts goldens of SPEC-0009
and three report fixtures of their own. `AGK_WRITE_GOLDENS=1` rewrites them; a diff is then read by
a person.
"""

from __future__ import annotations

import ast
import builtins
import copy
import json
import os
import socket
import subprocess  # nosec B404 - fixed argument lists, no shell
import sys
from pathlib import Path

import pytest
from product_report import main

FIXTURES = Path(__file__).parent / "fixtures"
FACTS = FIXTURES / "facts"
REPORT = FIXTURES / "report"
GOLDEN = REPORT / "golden"
SOURCE = Path(__file__).resolve().parents[2] / "scripts" / "agk" / "product_report.py"
PR = "PR " + "#"
MASK = "<pr>"  # goldens hold the mask: installed files carry no pull request number
HEADINGS = ["## Delivered", "## Proven", "## Needs you", "## At risk", "## Cost"]
CASES = sorted(
    [("facts-" + p.name, p / "facts.json") for p in FACTS.iterdir()]
    + [(p.name, p / "facts.json") for p in REPORT.iterdir() if p.name != "golden"]
)
ALLOWED_IMPORTS = {
    "argparse",
    "json",
    "re",
    "sys",
    "datetime",
    "decimal",
    "collections",
    "pathlib",
    "__future__",
}


def render(facts: Path, *extra: str, capsys) -> tuple[int, str, str]:
    code = main(["--facts", str(facts), *extra])
    out = capsys.readouterr()
    return code, out.out, out.err


def pr(number: int) -> str:
    return f'PR #{number} "Change number {number}"'


def kinds() -> dict:
    return json.loads((REPORT / "kinds" / "facts.json").read_text(encoding="utf-8"))


def render_doc(doc: dict, tmp_path: Path, *extra: str, capsys) -> str:
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    code, out, _ = render(path, *extra, capsys=capsys)
    assert code == 0, out
    return out


def group(text: str, title: str) -> list[str]:
    """The bullet lines of the inbox group whose heading starts with `### title`."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith(f"### {title} (")), None)
    if start is None:
        return []
    found = []
    for ln in lines[start + 1 :]:
        if not ln.startswith("- "):
            break
        found.append(ln)
    return found


def section(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    start = lines.index(heading) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), None)
    if end is None:
        end = lines.index("---")
    return [ln for ln in lines[start:end] if ln]


# --- goldens ------------------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "facts"), CASES, ids=[name for name, _ in CASES])
@pytest.mark.parametrize(("mode", "flags"), [("report", []), ("inbox", ["--inbox"])])
def test_golden_outputs(name, facts, mode, flags, capsys):
    """REQ-018 AC2: the report and the inbox are a fixed function of the facts document."""
    code, out, err = render(facts, *flags, capsys=capsys)
    assert (code, err) == (0, "")
    golden = GOLDEN / name / f"{mode}.md"
    if os.environ.get("AGK_WRITE_GOLDENS") == "1":
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(out.replace(PR, MASK), encoding="utf-8")
    assert out == golden.read_text(encoding="utf-8").replace(MASK, PR)


@pytest.mark.parametrize(("name", "facts"), CASES, ids=[name for name, _ in CASES])
def test_same_input_same_output(name, facts, capsys):
    """REQ-018 AC2: nothing but the facts decides the text, so two runs are equal."""
    first = render(facts, capsys=capsys)
    assert first == render(facts, capsys=capsys)


# --- the report ---------------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "facts"), CASES, ids=[name for name, _ in CASES])
def test_five_headings_in_order_then_the_footer(name, facts, capsys):
    """REQ-018 AC2: rule 9 (five sections, in this order, with these headings)."""
    _, out, _ = render(facts, capsys=capsys)
    lines = out.splitlines()
    assert [ln for ln in lines if ln.startswith("## ")] == HEADINGS
    doc = json.loads(facts.read_text(encoding="utf-8"))
    assert f"facts: {doc['commit']}" in lines
    assert lines.index("---") > lines.index("## Cost")


def test_every_line_in_a_section_links_to_evidence(capsys):
    """REQ-018 AC2: rule 10 (every line links to a PR, file, issue or commit)."""
    _, out, _ = render(REPORT / "kinds" / "facts.json", capsys=capsys)
    base = "https://github.com/demo-org/demo-repo/"
    for heading in HEADINGS:
        for line in section(out, heading):
            if line.startswith("###"):
                continue
            assert line.startswith("- "), line
            assert " — " + base in line, line


def test_the_drift_line_without_an_open_issue_is_the_one_line_without_a_link(capsys):
    """Rule 10: At risk prints the facts' drift counts and links the open drift issue, if any."""
    _, out, _ = render(REPORT / "quiet" / "facts.json", capsys=capsys)
    assert section(out, "## At risk") == [
        "- drift audit: 0 findings (D1 0, D2 0, D3 0, D4 0, D5 0, D6 0, D7 0); no open drift issue"
    ]
    _, out, _ = render(REPORT / "kinds" / "facts.json", capsys=capsys)
    line = next(ln for ln in section(out, "## At risk") if ln.startswith("- drift audit"))
    assert line.startswith("- drift audit: 4 findings (D1 0, D2 0, D3 2, D4 1, D5 0, D6 0, D7 1)")
    assert line.endswith("https://github.com/demo-org/demo-repo/issues/4")


def test_a_quiet_week_prints_nothing_this_week(capsys):
    """REQ-018 AC2: rule 10 (an empty section says so)."""
    _, out, _ = render(REPORT / "quiet" / "facts.json", capsys=capsys)
    for heading in ("## Delivered", "## Needs you", "## Cost"):
        assert section(out, heading) == ["nothing this week"]
    _, inbox, _ = render(REPORT / "quiet" / "facts.json", "--inbox", capsys=capsys)
    assert "nothing waits for you" in inbox


def test_unknown_is_printed_as_unknown_never_as_zero(capsys):
    """REQ-018 AC2: rule 10 (a field the facts could not read is shown as unknown)."""
    _, out, _ = render(REPORT / "dirty-unknown" / "facts.json", capsys=capsys)
    assert "- unknown: test markers could not be read — " in out
    assert "### Questions waiting (unknown)" in out
    assert "### Overdue residuals (unknown)" in out
    assert "- drift audit: unknown (D1 0, D2 0, D3 0, D4 0, D5 0, D6 unknown, D7 0)" in out


def test_a_dirty_tree_is_named_in_the_footer(capsys):
    """REQ-018 AC2: rule 11 (a notice when dirty is not false)."""
    _, out, _ = render(REPORT / "dirty-unknown" / "facts.json", capsys=capsys)
    assert "the working tree was modified (dirty: true)" in out.splitlines()
    _, out, _ = render(REPORT / "quiet" / "facts.json", capsys=capsys)
    assert "modified" not in out


def test_the_footer_names_the_commit_and_the_two_issues(capsys):
    """REQ-018 AC2: rule 11 (facts: <commit>, the metrics and drift issues, or none found)."""
    _, out, _ = render(REPORT / "kinds" / "facts.json", capsys=capsys)
    assert out.endswith(
        "facts: c0ffee0000000000000000000000000000000000\n"
        'metrics: #3 "agk metrics 2026-W41"\n'
        'drift audit: #4 "agk drift audit 2026-10-10"\n'
    )


def test_the_week_is_the_iso_week_before_today_and_can_be_given(capsys):
    """REQ-018 AC2: rule 8 (the window is the full ISO week before today unless --week)."""
    facts = REPORT / "quiet" / "facts.json"
    _, out, _ = render(facts, "--today", "2026-10-12", capsys=capsys)
    assert out.splitlines()[0] == "<!-- agk-product-report: 2026-W41 -->"
    _, out, _ = render(facts, "--today", "2026-10-11", capsys=capsys)
    assert out.splitlines()[0] == "<!-- agk-product-report: 2026-W40 -->"
    _, out, _ = render(facts, "--week", "2026-W01", capsys=capsys)
    assert out.splitlines()[0] == "<!-- agk-product-report: 2026-W01 -->"
    assert "Monday 2025-12-29 to Sunday 2026-01-04" in out


def test_only_pull_requests_merged_in_the_week_are_delivered_and_costed(tmp_path, capsys):
    """REQ-018 AC2: rule 9 (Delivered and Cost list the week's merges only)."""
    doc = kinds()
    for p in doc["pull_requests"]:
        if p["number"] == 5:
            p["merged_at"] = "2026-10-12T00:00:00Z"
    out = render_doc(doc, tmp_path, capsys=capsys)
    assert pr(5) not in "\n".join(section(out, "## Delivered"))
    assert pr(5) not in "\n".join(section(out, "## Cost"))


def test_cost_totals_are_computed_from_the_facts(capsys):
    """REQ-018 AC2: rule 9 (hours to merge and fix verdicts, from timestamps and verdicts)."""
    _, out, _ = render(REPORT / "kinds" / "facts.json", capsys=capsys)
    cost = section(out, "## Cost")
    assert f"{pr(6)}: 49.3 hours from opening to merge, 2 fix verdicts" in cost[1]
    assert cost[-1].startswith(
        "- This week: 4 pull requests merged; hours in total: 107.3; fix verdicts in total: 2;"
        ' declared "Behaviour: unchanged": 2 — '
    )


def test_a_cost_figure_that_cannot_be_computed_is_unknown(tmp_path, capsys):
    """REQ-018 AC2: rule 10 (no zero stands in for a missing figure)."""
    doc = kinds()
    for p in doc["pull_requests"]:
        if p["number"] == 7:
            p["verdicts"] = "unknown"
            p["created_at"] = "unknown"
    out = render_doc(doc, tmp_path, capsys=capsys)
    cost = "\n".join(section(out, "## Cost"))
    assert f"{pr(7)}: unknown hours from opening to merge, unknown fix verdicts" in cost
    assert "hours in total: unknown; fix verdicts in total: unknown" in cost


def test_one_day_is_not_written_as_one_days(capsys):
    _, out, _ = render(REPORT / "kinds" / "facts.json", capsys=capsys)
    assert "(1 day):" in out
    assert "1 days" not in out


# --- Proven -------------------------------------------------------------------------------------


def test_proven_gives_one_reason_per_requirement(capsys):
    """REQ-018 AC2: rule 9 (a requirement is proven only when every criterion has a test and its
    last change was proven or declared unchanged)."""
    _, out, _ = render(REPORT / "kinds" / "facts.json", capsys=capsys)
    proven = "\n".join(section(out, "## Proven"))
    assert "is proven (last change PR #" in proven
    assert "is proven (last change PR #" in proven and "skipped (declared unchanged)" in proven
    for reason in (
        "has no test",
        "it lists no acceptance criteria",
        "no merged change was found",
        "was not shown to need its test",
        "has an unknown proof",
        "its acceptance criteria are unknown",
    ):
        assert reason in proven, reason


def test_planned_requirements_are_counted_not_judged(capsys):
    """REQ-018 AC2: rule 9 (a planned requirement is not proven or unproven)."""
    _, out, _ = render(REPORT / "quiet" / "facts.json", capsys=capsys)
    assert section(out, "## Proven")[0].startswith(
        "- 1 requirement is planned and not counted here — "
    )


# --- the inbox: one fixture per item kind -------------------------------------------------------


def test_the_inbox_lists_each_kind_under_its_own_heading_in_order(capsys):
    """REQ-017 AC1: rules 3 and 4 (six kinds, a heading and a count for each)."""
    _, out, _ = render(REPORT / "kinds" / "facts.json", "--inbox", capsys=capsys)
    assert [ln for ln in out.splitlines() if ln.startswith("### ")] == [
        "### Draft specs (1)",
        "### Proposed ADRs (1)",
        "### Questions waiting (2)",
        "### Pull requests without a verdict (2)",
        "### Overdue residuals (2)",
        "### Planned requirements with no spec (1)",
    ]
    assert out.splitlines()[0] == "The inbox as of 2026-10-14."


def test_a_draft_spec_is_waiting_and_an_approved_one_is_not(tmp_path, capsys):
    """REQ-017 AC1: rule 4, kind spec."""
    out = render_doc(kinds(), tmp_path, "--inbox", capsys=capsys)
    assert len(group(out, "Draft specs")) == 1
    assert "SPEC-0002" in group(out, "Draft specs")[0]
    doc = kinds()
    for s in doc["specs"]:
        s["status"] = "Approved"
    assert group(render_doc(doc, tmp_path, "--inbox", capsys=capsys), "Draft specs") == []


def test_a_proposed_adr_is_waiting_and_an_accepted_one_is_not(tmp_path, capsys):
    """REQ-017 AC1: rule 4, kind adr."""
    out = render_doc(kinds(), tmp_path, "--inbox", capsys=capsys)
    assert "Proposed ADR-0002" in group(out, "Proposed ADRs")[0]
    doc = kinds()
    for a in doc["adrs"]:
        a["status"] = "Accepted"
    assert group(render_doc(doc, tmp_path, "--inbox", capsys=capsys), "Proposed ADRs") == []


def test_an_unruled_question_with_an_open_place_is_waiting(tmp_path, capsys):
    """REQ-017 AC1: rule 4, kind question (open where it was asked, and not ruled)."""
    out = render_doc(kinds(), tmp_path, "--inbox", capsys=capsys)
    lines = group(out, "Questions waiting")
    assert [ln.split(" ")[2] for ln in lines] == ["Q-X1-1", "Q-X1-4"]
    doc = kinds()
    for q in doc["questions"]:
        q["ruled"] = True
    assert group(render_doc(doc, tmp_path, "--inbox", capsys=capsys), "Questions waiting") == []


def test_a_pull_request_without_a_verdict_waits_from_inbox_hours(tmp_path, capsys):
    """REQ-017 AC1: rule 5, kind pull-request (open, no verdict, at least inbox_hours old)."""
    out = render_doc(kinds(), tmp_path, "--inbox", capsys=capsys)
    assert [ln.split(" ")[2] for ln in group(out, "Pull requests without a verdict")] == [
        "#9",
        "#11",
    ]
    doc = kinds()
    doc["config"]["inbox_hours"] = 24 * 14
    quiet = render_doc(doc, tmp_path, "--inbox", capsys=capsys)
    assert group(quiet, "Pull requests without a verdict") == []
    doc["config"]["inbox_hours"] = 48
    for p in doc["pull_requests"]:
        if p["number"] == 9:
            p["verdicts"] = [{"kind": "cleared"}]
    shown = group(
        render_doc(doc, tmp_path, "--inbox", capsys=capsys), "Pull requests without a verdict"
    )
    assert [ln.split(" ")[2] for ln in shown] == ["#11"]


@pytest.mark.parametrize("hours", ["unknown", None, True, "48"])
def test_an_inbox_hours_that_is_not_a_number_is_shown_as_unknown(hours, tmp_path, capsys):
    """Rule 6: the inbox stays honest; no guess stands in for the age limit."""
    doc = kinds()
    doc["config"]["inbox_hours"] = hours
    out = render_doc(doc, tmp_path, "--inbox", capsys=capsys)
    assert "### Pull requests without a verdict (unknown)" in out
    assert "(inbox_hours)" in out


def test_an_open_residual_past_its_due_date_is_waiting_on_the_day_after(tmp_path, capsys):
    """REQ-017 AC1: rule 5, kind residual (open and due before today)."""
    out = render_doc(kinds(), tmp_path, "--inbox", capsys=capsys)
    lines = group(out, "Overdue residuals")
    assert lines[0].startswith("- Overdue since 2026-09-01: ")
    assert lines[1].startswith("- Overdue since 2026-10-13: ")
    assert all(len(ln.split(": ", 1)[1].split(" — ")[0]) <= 120 for ln in lines)
    doc = kinds()
    for r in doc["residuals"]:
        if r.get("due") == "2026-10-13":
            r["due"] = "2026-10-14"
    shown = group(render_doc(doc, tmp_path, "--inbox", capsys=capsys), "Overdue residuals")
    assert len(shown) == 1


def test_a_planned_requirement_no_spec_names_is_waiting(tmp_path, capsys):
    """REQ-017 AC1: rule 5, kind requirement."""
    out = render_doc(kinds(), tmp_path, "--inbox", capsys=capsys)
    assert group(out, "Planned requirements with no spec")[0].startswith("- REQ-007 ")
    doc = kinds()
    doc["specs"][0]["requirements"] = [*doc["specs"][0]["requirements"], "REQ-007"]
    shown = group(render_doc(doc, tmp_path, "--inbox", capsys=capsys), "Planned requirements")
    assert shown == []


def test_a_field_the_facts_could_not_read_makes_an_unknown_group(capsys):
    """Rule 6 (an unreadable source is a visible unknown, not an empty group)."""
    _, out, _ = render(REPORT / "dirty-unknown" / "facts.json", "--inbox", capsys=capsys)
    assert "### Questions waiting (unknown)" in out
    assert "### Overdue residuals (unknown)" in out


def test_the_inbox_in_the_report_is_the_inbox_alone(capsys):
    """REQ-017 AC1: the Needs you section is the inbox's groups, line for line."""
    facts = REPORT / "kinds" / "facts.json"
    _, report, _ = render(facts, capsys=capsys)
    _, inbox, _ = render(facts, "--inbox", capsys=capsys)
    for line in inbox.splitlines():
        if line.startswith(("### ", "- ")):
            assert line in report.splitlines()


# --- the issue action ---------------------------------------------------------------------------


def test_print_action_creates_or_updates_the_one_issue_of_the_week(tmp_path, capsys):
    """Rule 12: one issue per ISO week, found by label and exact title, updated in place."""
    doc = kinds()
    doc["issues"] = []
    assert render_doc(doc, tmp_path, "--print-action", capsys=capsys) == "create\n"
    doc["issues"] = [
        {"number": 21, "title": "agk product report 2026-W41", "label": "agk-product-report"},
        {"number": 20, "title": "agk product report 2026-W40", "label": "agk-product-report"},
        {"number": 22, "title": "agk product report 2026-W41", "label": "other"},
    ]
    out = render_doc(doc, tmp_path, "--print-action", capsys=capsys)
    assert out == "update 21\n"


def test_print_action_names_duplicates_and_updates_the_lowest(tmp_path, capsys):
    doc = kinds()
    doc["issues"] = [
        {"number": 31, "title": "agk product report 2026-W41", "label": "agk-product-report"},
        {"number": 30, "title": "agk product report 2026-W41", "label": "agk-product-report"},
    ]
    out = render_doc(doc, tmp_path, "--print-action", capsys=capsys)
    assert out.splitlines() == [
        "update 30",
        "duplicate product report issues: #30,#31; #30 is the one updated",
    ]


def test_print_action_refuses_when_issues_are_unknown(tmp_path, capsys):
    doc = kinds()
    doc["issues"] = "unknown"
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    code, out, _ = render(path, "--print-action", capsys=capsys)
    assert code == 1
    assert out.startswith("FAIL product-report: the field issues is unknown")


# --- refusals and usage -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("edit", "named"),
    [
        (lambda d: d.update(schema=2), "schema"),
        (lambda d: d.update(repo="unknown"), "repo"),
        (lambda d: d.pop("drift"), "drift"),
        (lambda d: d.pop("pull_requests"), "pull_requests"),
    ],
)
def test_a_facts_document_the_renderer_cannot_use_is_refused_by_field(
    edit, named, tmp_path, capsys
):
    """Rule 14: a refusal names the field or the path class, never a value."""
    doc = copy.deepcopy(kinds())
    edit(doc)
    path = tmp_path / "facts.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    code, out, _ = render(path, capsys=capsys)
    assert code == 1
    assert out.startswith("FAIL product-report: ")
    assert f"field: {named}" in out
    assert "demo-org" not in out


def test_a_missing_or_malformed_facts_file_is_refused_by_path_class(tmp_path, capsys):
    code, out, _ = render(tmp_path / "absent.json", capsys=capsys)
    assert (code, out) == (
        1,
        "FAIL product-report: the facts file cannot be read (path class: facts file)\n",
    )
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    code, out, _ = render(bad, capsys=capsys)
    assert (code, out) == (
        1,
        "FAIL product-report: the facts file is not JSON (path class: facts file)\n",
    )
    assert str(tmp_path) not in out


@pytest.mark.parametrize("today", ["14-10-2026", "2026-13-01", "2026-02-30", ""])
def test_a_bad_today_is_refused_by_option(today, capsys):
    code, out, _ = render(REPORT / "quiet" / "facts.json", "--today", today, capsys=capsys)
    assert code == 1
    assert "(option: --today)" in out
    assert today not in out or today == ""


@pytest.mark.parametrize("week", ["2026-41", "2026-W54", "W41"])
def test_a_bad_week_is_refused_by_option(week, capsys):
    code, out, _ = render(REPORT / "quiet" / "facts.json", "--week", week, capsys=capsys)
    assert code == 1
    assert "(option: --week)" in out


@pytest.mark.parametrize(
    "argv",
    [[], ["--facts"], ["--facts", "x", "--bogus"], ["--facts", "x", "--inbox", "--print-action"]],
)
def test_usage_errors_exit_2_with_the_usage_line(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2
    assert capsys.readouterr().err.startswith("usage: product_report.py --facts FILE")


# --- criterion e: the renderer reads nothing but --facts ----------------------------------------


def test_the_renderer_imports_only_the_allowed_modules():
    """REQ-018 AC2: rule 13 (no os, subprocess, urllib, socket or time; no clock)."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= ALLOWED_IMPORTS, sorted(imported - ALLOWED_IMPORTS)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "datetime":
            assert {a.name for a in node.names} == {"date", "timedelta"}


def test_the_renderer_opens_one_file_and_reads_no_clock_or_environment():
    """REQ-018 AC2: rule 13 (exactly one read, of --facts; no open, exec, eval or __import__)."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    called = {
        n.func.attr
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }
    assert not names & {"open", "exec", "eval", "compile", "__import__", "input", "os"}
    assert not called & {"today", "now", "utcnow", "getenv", "popen", "system"}
    assert not attrs & {"environ", "getenv"}
    reads = [
        n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr.startswith("read")
    ]
    assert [r.attr for r in reads] == ["read_text"]
    text = SOURCE.read_text(encoding="utf-8")
    for needle in ("gh ", "git ", "http://", "curl"):
        assert needle not in text.replace("https://github.com/", ""), needle


def test_a_run_touches_no_file_but_the_facts_file_and_opens_no_socket(
    monkeypatch, tmp_path, capsys
):
    """REQ-018 AC2: the same rule, observed: every open and every socket is recorded."""
    facts = REPORT / "kinds" / "facts.json"
    opened: list[str] = []
    real_open, real_path_open = builtins.open, Path.open

    def spy(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    def spy_path(self, *args, **kwargs):
        opened.append(str(self))
        return real_path_open(self, *args, **kwargs)

    def no_socket(*args, **kwargs):
        raise AssertionError("the renderer opened a socket")

    monkeypatch.setattr(builtins, "open", spy)
    monkeypatch.setattr(Path, "open", spy_path)
    monkeypatch.setattr(socket, "socket", no_socket)
    monkeypatch.setattr(socket, "create_connection", no_socket)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "must-not-be-read")
    code, out, _ = render(facts, capsys=capsys)
    assert code == 0
    assert opened == [str(facts)]
    assert "must-not-be-read" not in out


def test_the_report_changes_with_the_facts_and_with_nothing_else(tmp_path, monkeypatch, capsys):
    """REQ-018 AC2: the facts decide every number; the working directory and the clock do not."""
    facts = REPORT / "kinds" / "facts.json"
    _, here, _ = render(facts, capsys=capsys)
    monkeypatch.chdir(tmp_path)
    _, there, _ = render(facts, capsys=capsys)
    assert here == there
    doc = kinds()
    doc["pull_requests"] = [p for p in doc["pull_requests"] if p["number"] != 5]
    changed = render_doc(doc, tmp_path, capsys=capsys)
    assert changed != here
    assert pr(5) not in changed


# --- rule 13 (c) to (e), and the arithmetic of rules 5 and 10 -----------------------------------


def test_a_run_with_an_empty_environment_in_an_empty_directory_matches_the_golden(tmp_path):
    """REQ-018 AC2: rule 13 (c) (no environment, no HOME, no working copy)."""
    facts = REPORT / "kinds" / "facts.json"
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SOURCE), "--facts", str(facts)],
        cwd=tmp_path,
        env={},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == (GOLDEN / "kinds" / "report.md").read_text(encoding="utf-8").replace(
        MASK, PR
    )


def changed_lines(before: str, after: str) -> list[str]:
    old, new = before.splitlines(), after.splitlines()
    assert len(old) == len(new)
    return [b for a, b in zip(old, new, strict=True) if a != b]


def test_changing_one_number_changes_the_one_line_that_depends_on_it(tmp_path, capsys):
    """REQ-018 AC2: rule 13 (d) (no number is constant in the renderer)."""
    base = render(REPORT / "kinds" / "facts.json", capsys=capsys)[1]
    doc = kinds()
    for r in doc["residuals"]:
        if r.get("due") == "2026-10-13":
            r["due"] = "2026-10-11"
    after = render_doc(doc, tmp_path, capsys=capsys)
    lines = changed_lines(base, after)
    assert len(lines) == 2  # the line in Needs you and the line in At risk, and no other
    assert lines[0].startswith("- Overdue since 2026-10-11: ")
    assert lines[1].startswith("- Residual overdue since 2026-10-11 (3 days): ")


def hours(opened: str, closed: str) -> str:
    """A second, independent computation of hours to merge, to the tenth, half up."""
    from datetime import datetime  # noqa: PLC0415 - a test, not the renderer

    fmt = "%Y-%m-%dT%H:%M:%SZ"
    seconds = (datetime.strptime(closed, fmt) - datetime.strptime(opened, fmt)).total_seconds()
    tenths = (
        int(seconds * 10 / 3600 + 0.5)
        if seconds * 10 % 3600 != 1800
        else int(seconds * 10 // 3600) + 1
    )
    return f"{tenths // 10}.{tenths % 10}"


def test_every_cost_figure_equals_an_independent_recomputation(capsys):
    """REQ-018 AC2: rule 13 (e) and the totals of rule 10."""
    facts = REPORT / "kinds" / "facts.json"
    doc = kinds()
    out = render(facts, capsys=capsys)[1]
    cost = section(out, "## Cost")
    merged = [
        p
        for p in sorted(doc["pull_requests"], key=lambda p: p["number"])
        if p["state"] == "merged" and "2026-10-05" <= p["merged_at"][:10] < "2026-10-12"
    ]
    assert len(cost) == len(merged) + 1
    for line, p in zip(cost, merged, strict=False):
        assert f": {hours(p['created_at'], p['merged_at'])} hours from opening to merge, " in line
        fixes = sum(1 for v in p["verdicts"] if v["kind"] == "fix")
        assert f", {fixes} fix verdict" in line
    total = sum(int(hours(p["created_at"], p["merged_at"]).replace(".", "")) for p in merged)
    assert f"hours in total: {total // 10}.{total % 10};" in cost[-1]
    assert f"{len(merged)} pull requests merged" in cost[-1]


def test_hours_use_the_same_rounding_as_the_metrics_issue(tmp_path, capsys):
    """Residual of SPEC-0011: the report and the metrics issue round alike (half up, to 0.1)."""
    from metrics import hours_between as metrics_hours

    pairs = [
        ("2026-10-06T00:00:00Z", "2026-10-06T00:01:30Z"),
        ("2026-10-06T00:00:00Z", "2026-10-06T00:03:00Z"),
        ("2026-10-06T00:00:00Z", "2026-10-06T00:02:15Z"),
        ("2026-10-06T00:00:00Z", "2026-10-08T01:20:00Z"),
    ]
    doc = kinds()
    template = next(p for p in doc["pull_requests"] if p["number"] == 5)
    doc["pull_requests"] = []
    for n, (opened, closed) in enumerate(pairs, start=100):
        row = dict(template, number=n, created_at=opened, merged_at=closed)
        doc["pull_requests"].append(row)
    out = render_doc(doc, tmp_path, capsys=capsys)
    for line, (opened, closed) in zip(section(out, "## Cost"), pairs, strict=False):
        assert f": {metrics_hours(opened, closed)} hours from" in line


@pytest.mark.parametrize(
    ("created", "listed"),
    [("2026-10-14", False), ("2026-10-13", False), ("2026-10-12", True), ("2026-10-11", True)],
)
def test_the_age_arithmetic_counts_whole_calendar_days(created, listed, tmp_path, capsys):
    """REQ-017 AC1: rule 5 (with 48 hours, two days before today is an item, one day is not)."""
    doc = kinds()
    doc["pull_requests"] = [
        dict(
            p,
            created_at=f"{created}T23:59:00Z",
            state="open",
            verdicts=[],
            number=9,
        )
        for p in doc["pull_requests"][:1]
    ]
    out = render_doc(doc, tmp_path, "--inbox", capsys=capsys)
    assert bool(group(out, "Pull requests without a verdict")) is listed
