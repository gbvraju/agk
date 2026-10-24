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
            # a line of one pull request ends with its link; a grouped line (SPEC-0016) holds one
            # link for each number
            assert " — " + base in line or (line.startswith("- PRs ") and "](" + base in line), line


def test_the_drift_line_without_an_open_issue_is_the_one_line_without_a_link(capsys):
    """Rule 10: At risk prints the facts' drift counts and links the open drift issue, if any."""
    _, out, _ = render(REPORT / "quiet" / "facts.json", capsys=capsys)
    assert section(out, "## At risk") == ["nothing this week"]  # a total of 0 with no open issue
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
        "kit version: unknown\n"
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
        ' declared "Behaviour: unchanged": 2; estimate: none declared this week — '
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


# --- E2: the proof reason in the Proven line, and the file link of a spec or an ADR -------------


def proven_lines(doc, tmp_path, capsys) -> str:
    return "\n".join(section(render_doc(doc, tmp_path, capsys=capsys), "## Proven"))


def with_last_change(doc: dict, proof: str, reason) -> dict:
    """REQ-002 in the `kinds` facts has its last change at PR 6; give that PR a proof and reason."""
    for p in doc["pull_requests"]:
        if p["number"] == 6:
            p["proof"], p["proof_reason"] = proof, reason
    return doc


@pytest.mark.parametrize(
    ("reason", "words"),
    [
        ("red-on-head", "the tests fail on the change itself"),
        ("green-on-base", "the new tests already pass without the change"),
        ("timeout", "the test run took too long"),
        ("no-project-tests", "no test command is configured"),
        ("no-test-files", "the change adds no test file"),
    ],
)
def test_the_proven_line_prints_the_reason_next_to_not_proven(reason, words, tmp_path, capsys):
    """REQ-018 AC2: rule 9 as amended (an environment fault reads differently from a real gap)."""
    doc = with_last_change(kinds(), "not-proven", reason)
    lines = proven_lines(doc, tmp_path, capsys)
    needle = f"(PR #{6}) was not shown to need its test (not-proven: {reason}, {words})"
    assert needle in lines


def test_an_unknown_proof_prints_its_reason_too(tmp_path, capsys):
    """REQ-018 AC2: the same, for an outcome of unknown."""
    doc = with_last_change(kinds(), "unknown", "timeout")
    assert "has an unknown proof (unknown: timeout, the test run took too long)" in proven_lines(
        doc, tmp_path, capsys
    )


@pytest.mark.parametrize("reason", ["unknown", "a-reason-the-renderer-has-no-words-for"])
def test_a_reason_that_is_unknown_or_has_no_words_is_printed_as_it_is(reason, tmp_path, capsys):
    """REQ-018 AC2: rule 12 (unknown stays unknown; a reason without words is not hidden)."""
    lines = proven_lines(with_last_change(kinds(), "not-proven", reason), tmp_path, capsys)
    if reason == "unknown":
        assert "(not-proven: reason unknown)" in lines
    else:
        assert f"(not-proven: {reason})" in lines


def test_a_document_without_proof_reason_still_renders(tmp_path, capsys):
    """REQ-018 AC2: schema 1 is unchanged; a document made before the field existed has none."""
    doc = kinds()
    for p in doc["pull_requests"]:
        p.pop("proof_reason", None)
    assert "(not-proven: reason unknown)" in proven_lines(doc, tmp_path, capsys)


def test_a_draft_spec_and_a_proposed_adr_link_their_files_when_the_facts_carry_a_path(
    tmp_path, capsys
):
    """Residual of SPEC-0011 (due 2026-11-30): the inbox links the file, not the directory."""
    out = render_doc(kinds(), tmp_path, "--inbox", capsys=capsys)
    commit = kinds()["commit"]
    base = f"https://github.com/demo-org/demo-repo/blob/{commit}/"
    assert group(out, "Draft specs")[0].endswith(f" — {base}docs/specs/0002-draft.md")
    assert group(out, "Proposed ADRs")[0].endswith(f" — {base}docs/adr/0002-proposed.md")


def test_without_a_path_the_inbox_links_the_directory_as_before(tmp_path, capsys):
    """REQ-017 AC1: a document without `path` (made before the field existed) still renders."""
    doc = kinds()
    for item in (*doc["specs"], *doc["adrs"]):
        item.pop("path", None)
    out = render_doc(doc, tmp_path, "--inbox", capsys=capsys)
    assert group(out, "Draft specs")[0].endswith("/tree/" + doc["commit"] + "/docs/specs")
    assert group(out, "Proposed ADRs")[0].endswith("/tree/" + doc["commit"] + "/docs/adr")


def test_a_residual_marked_closed_is_in_neither_the_inbox_nor_at_risk(tmp_path, capsys):
    """REQ-017 AC1: a delivered bullet (state closed in the facts) is not overdue."""
    doc = kinds()
    for r in doc["residuals"]:
        r["state"] = "closed"
    out = render_doc(doc, tmp_path, capsys=capsys)
    assert "Overdue" not in out and "Residual overdue" not in out


# --- At risk: a pull request merged before its head was cleared (SPEC-0011 rule 10 (v)) ---------


def merged_pr(doc: dict, number: int, verdicts, head: str | None = "aaaaaaa" + "b" * 33) -> dict:
    row = next(p for p in doc["pull_requests"] if p["number"] == number)
    row.update(
        {"state": "merged", "merged_at": "2026-10-08T10:00:00Z", "verdicts": verdicts, "head": head}
    )
    return row


def risk_lines(doc: dict, tmp_path, capsys) -> list[str]:
    return [
        ln
        for ln in section(render_doc(doc, tmp_path, capsys=capsys), "## At risk")
        if "was merged" in ln
    ]


def cleared(sha: str | None, at: str = "2026-10-08T09:00:00Z") -> dict:
    return {"at": at, "kind": "cleared", "sha": sha}


def test_the_last_cleared_verdict_naming_the_merged_head_is_no_risk(tmp_path, capsys):
    """REQ-020 AC2: SPEC-0011 rule 10 (v) (a short sha, upper case, or the whole head)."""
    for sha in ("aaaaaaa", "AAAAAAA", "aaaaaaa" + "b" * 33):
        doc = kinds()
        merged_pr(doc, 5, [cleared(sha)])
        assert not [ln for ln in risk_lines(doc, tmp_path, capsys) if "#5 " in ln], sha


def lone(doc: dict) -> dict:
    """The facts without #8, the one pull request of `kinds` merged before it was cleared."""
    doc["pull_requests"] = [p for p in doc["pull_requests"] if p["number"] != 8]
    return doc


def test_a_cleared_verdict_for_an_earlier_commit_is_reported(tmp_path, capsys):
    """REQ-020 AC2: rule 10 (v) (the last cleared verdict decides, not an earlier one)."""
    doc = lone(kinds())
    merged_pr(doc, 5, [cleared("aaaaaaa"), cleared("ccccccc", "2026-10-08T09:30:00Z")])
    lines = [ln for ln in risk_lines(doc, tmp_path, capsys) if "#5 " in ln]
    assert len(lines) == 1
    assert lines[0].startswith(f"- {PR}5 was merged before its last commit was cleared — ")
    assert lines[0].endswith("/pull/5")
    doc = lone(kinds())
    merged_pr(doc, 5, [cleared("ccccccc"), cleared("aaaaaaa", "2026-10-08T09:30:00Z")])
    assert not [ln for ln in risk_lines(doc, tmp_path, capsys) if "#5 " in ln]


def test_verdicts_that_never_cleared_the_head_are_reported(tmp_path, capsys):
    """REQ-020 AC2: rule 10 (v) (only fix verdicts, or a cleared verdict with no sha)."""
    for verdicts in ([{"at": "2026-10-08T09:00:00Z", "kind": "fix", "sha": None}], [cleared(None)]):
        doc = lone(kinds())
        merged_pr(doc, 5, verdicts)
        lines = [ln for ln in risk_lines(doc, tmp_path, capsys) if "#5 " in ln]
        assert len(lines) == 1 and "before its last commit was cleared" in lines[0]


def test_a_pull_request_merged_with_no_verdict_is_reported(tmp_path, capsys):
    """REQ-020 AC2: rule 10 (v)."""
    doc = lone(kinds())
    merged_pr(doc, 5, [])
    lines = [ln for ln in risk_lines(doc, tmp_path, capsys) if "#5 " in ln]
    assert len(lines) == 1 and lines[0].startswith(f"- {PR}5 was merged with no verdict — ")


def test_only_pull_requests_merged_in_the_week_are_checked(tmp_path, capsys):
    """REQ-020 AC2: rule 10 (v) (an open, a closed and an earlier merge are not)."""
    doc = kinds()
    for number in (5, 6, 7, 8):
        merged_pr(doc, number, [cleared("ccccccc")])
    next(p for p in doc["pull_requests"] if p["number"] == 5).update({"state": "closed"})
    next(p for p in doc["pull_requests"] if p["number"] == 6).update({"state": "open"})
    next(p for p in doc["pull_requests"] if p["number"] == 7)["merged_at"] = "2026-09-01T10:00:00Z"
    lines = risk_lines(doc, tmp_path, capsys)
    assert [ln.split(" ")[2] for ln in lines] == ["#8"]


def test_unreadable_verdicts_or_head_are_not_reported_as_a_miss(tmp_path, capsys):
    """REQ-020 AC2: rule 10 (v) (unknown is not a miss; nothing is invented)."""
    for verdicts, head in (("unknown", "a" * 40), ([], "unknown"), ([], None), ([cleared("a")], 5)):
        doc = kinds()
        merged_pr(doc, 5, verdicts, head)
        assert not [ln for ln in risk_lines(doc, tmp_path, capsys) if "#5 " in ln], (verdicts, head)


def test_the_merged_before_cleared_lines_come_after_the_drift_line_in_pull_request_order(
    tmp_path, capsys
):
    """REQ-020 AC2: rule 10 (v) is the fifth item, after (iv) the drift counts."""
    doc = kinds()
    merged_pr(doc, 6, [])
    merged_pr(doc, 5, [])
    lines = section(render_doc(doc, tmp_path, capsys=capsys), "## At risk")
    drift = next(i for i, ln in enumerate(lines) if "drift audit:" in ln)
    late = [i for i, ln in enumerate(lines) if "merged" in ln]
    # #5 and #6 above are one line (SPEC-0016), then #8 whose clearance names another commit
    assert late == [drift + 1, drift + 2]
    assert lines[late[0]].startswith("- PRs [#5](") and "[#6](" in lines[late[0]]
    assert lines[late[1]].startswith(f"- {PR}8 was merged before")


def footer_of(text: str) -> list[str]:
    lines = text.splitlines()
    return lines[lines.index("---") :]


def test_ac1_the_footer_names_the_kit_version_directly_after_the_facts_line(tmp_path, capsys):
    """REQ-021 AC1: SPEC-0014 rule 4."""
    doc = kinds()
    doc["kit_version"] = "1.2.3"
    footer = footer_of(render_doc(doc, tmp_path, capsys=capsys))
    assert footer[1] == f"facts: {doc['commit']}"
    assert footer[2] == "kit version: 1.2.3"
    assert "http" not in footer[2], "the line has no link: its evidence is the facts commit"


def test_ac1_the_kit_version_line_comes_before_the_dirty_notice(tmp_path, capsys):
    """REQ-021 AC1: SPEC-0014 rule 4 (directly after `facts:`, whatever follows)."""
    doc = json.loads((REPORT / "dirty-unknown" / "facts.json").read_text(encoding="utf-8"))
    doc["kit_version"] = "1.2.3"
    footer = footer_of(render_doc(doc, tmp_path, capsys=capsys))
    assert footer[1].startswith("facts: ") and footer[2] == "kit version: 1.2.3"
    assert footer[3].startswith("the working tree was modified")


@pytest.mark.parametrize("value", ["absent", "unknown", 3, None, ["1.2.3"], ""])
def test_ac2_a_missing_or_unusable_kit_version_prints_unknown(tmp_path, capsys, value):
    """REQ-021 AC2: SPEC-0014 rule 4 (a document made before this rule; never a guess)."""
    doc = kinds()
    doc.pop("kit_version", None)
    if value != "absent":
        doc["kit_version"] = value
    footer = footer_of(render_doc(doc, tmp_path, capsys=capsys))
    assert footer[2] == "kit version: unknown"


def test_ac2_the_inbox_output_has_no_footer_and_does_not_change(tmp_path, capsys):
    """REQ-021 AC2: SPEC-0014 rule 5."""
    doc = kinds()
    plain = render_doc(doc, tmp_path, "--inbox", "--today", "2026-10-17", capsys=capsys)
    doc["kit_version"] = "1.2.3"
    versioned = render_doc(doc, tmp_path, "--inbox", "--today", "2026-10-17", capsys=capsys)
    assert plain == versioned and "kit version" not in plain


# --- a busy week: REQ-022 (SPEC-0015) ------------------------------------------------------------

BUSY = REPORT / "busy" / "facts.json"
WEEK41_LINK = "https://github.com/demo-org/demo-repo/pulls?q=is%3Apr+is%3Amerged+merged%3A2026-10-05..2026-10-11"


def busy_doc() -> dict:
    return json.loads(BUSY.read_text(encoding="utf-8"))


def merged_in_week41(doc: dict) -> list[dict]:
    return [
        p
        for p in doc["pull_requests"]
        if p["state"] == "merged" and "2026-10-05" <= p["merged_at"][:10] <= "2026-10-11"
    ]


def keep_merged(doc: dict, count: int) -> dict:
    """The doc with exactly `count` pull requests merged in week 41 (the highest numbers go)."""
    doc = copy.deepcopy(doc)
    drop = {p["number"] for p in sorted(merged_in_week41(doc), key=lambda p: -p["number"])[count:]}
    doc["pull_requests"] = [p for p in doc["pull_requests"] if p["number"] not in drop]
    assert len(merged_in_week41(doc)) == count
    return doc


def test_ac1_the_threshold_is_one_named_constant():
    """REQ-022 AC1: SPEC-0015 rule 1 (ten, not a setting)."""
    import product_report

    assert product_report.BUSY_WEEK == 10
    assert len(merged_in_week41(busy_doc())) == 12


def test_ac1_delivered_keeps_the_requirements_and_shows_one_line_with_the_link(tmp_path, capsys):
    """REQ-022 AC1: SPEC-0015 rule 3."""
    out = render_doc(busy_doc(), tmp_path, capsys=capsys)
    delivered = section(out, "## Delivered")
    requirements = [ln for ln in delivered if ln.startswith("- REQ-")]
    done = [r["id"] for r in busy_doc()["requirements"] if r["status"] == "done"]
    assert [ln.split()[1] for ln in requirements] == sorted(done)
    assert not [ln for ln in delivered if PR in ln], "no line for a single pull request"
    assert delivered[-1] == f"- 12 pull requests were merged this week \u2014 {WEEK41_LINK}"
    assert len(delivered) == len(requirements) + 1


def test_ac2_cost_is_the_totals_line_alone_ending_with_the_week_link(tmp_path, capsys):
    """REQ-022 AC2: SPEC-0015 rule 4."""
    doc = busy_doc()
    out = render_doc(doc, tmp_path, capsys=capsys)
    cost = section(out, "## Cost")
    merged = merged_in_week41(doc)
    hours = sum(
        (_parse(p["merged_at"]) - _parse(p["created_at"])).total_seconds() / 3600 for p in merged
    )
    fixes = sum(1 for p in merged for v in p["verdicts"] if v["kind"] == "fix")
    declared = sum(1 for p in merged if p["behaviour"] == "unchanged")
    text = (
        f"- This week: 12 pull requests merged; hours in total: {hours:.1f}; "
        f'fix verdicts in total: {fixes}; declared "Behaviour: unchanged": {declared}; '
        "estimate: none declared this week"
    )
    assert cost == [f"{text} \u2014 {WEEK41_LINK}"]
    assert "hours from opening to merge" not in out


def _parse(stamp: str):
    from datetime import datetime

    return datetime.fromisoformat(stamp.replace("Z", "+00:00"))


@pytest.mark.parametrize(
    ("week", "shift", "dates"),
    [("2026-W41", 0, "2026-10-05..2026-10-11"), ("2026-W42", 7, "2026-10-12..2026-10-18")],
)
def test_ac3_the_link_is_built_from_the_repo_and_the_weeks_utc_dates(
    tmp_path, capsys, week, shift, dates
):
    """REQ-022 AC3: SPEC-0015 rule 5 (the dates of the opening line; nothing but the facts)."""
    from datetime import timedelta

    doc = busy_doc()
    for p in doc["pull_requests"]:
        for key in ("created_at", "merged_at", "closed_at"):
            if p[key]:
                shifted = _parse(p[key]) + timedelta(days=shift)
                p[key] = shifted.strftime("%Y-%m-%dT%H:%M:%SZ")
    out = render_doc(doc, tmp_path, "--week", week, capsys=capsys)
    link = f"https://github.com/demo-org/demo-repo/pulls?q=is%3Apr+is%3Amerged+merged%3A{dates}"
    opening = out.splitlines()[1]
    assert f"Monday {dates[:10]} to Sunday {dates[12:]}" in opening
    assert section(out, "## Delivered")[-1].endswith(f"\u2014 {link}")
    assert section(out, "## Cost")[-1].endswith(f"\u2014 {link}")


@pytest.mark.parametrize("count", [1, 4, 9, 10])
def test_ac4_ten_or_fewer_pull_requests_keep_one_line_each(tmp_path, capsys, count):
    """REQ-022 AC4: SPEC-0015 rule 2 (a quiet week is unchanged, at the boundary and below)."""
    out = render_doc(keep_merged(busy_doc(), count), tmp_path, capsys=capsys)
    delivered, cost = section(out, "## Delivered"), section(out, "## Cost")
    assert len([ln for ln in delivered if "was merged on" in ln]) == count
    assert len([ln for ln in cost if "hours from opening to merge" in ln]) == count
    assert not [ln for ln in delivered if "were merged this week" in ln]
    assert WEEK41_LINK not in out


def test_ac4_eleven_pull_requests_are_a_busy_week(tmp_path, capsys):
    """REQ-022 AC4: SPEC-0015 rules 1 and 2 (more than ten collapses; ten does not)."""
    out = render_doc(keep_merged(busy_doc(), 11), tmp_path, capsys=capsys)
    assert section(out, "## Delivered")[-1].startswith("- 11 pull requests were merged this week")
    assert len(section(out, "## Cost")) == 1


def test_ac5_needs_you_at_risk_proven_and_the_footer_are_not_changed(tmp_path, capsys, monkeypatch):
    """REQ-022 AC5: SPEC-0015 rule 6 (every pull request they named is still named)."""
    import product_report

    doc = busy_doc()
    short = render_doc(doc, tmp_path, capsys=capsys)
    monkeypatch.setattr(product_report, "BUSY_WEEK", 10**6)
    long = render_doc(doc, tmp_path, capsys=capsys)
    assert short != long
    for heading in ("## Proven", "## Needs you", "## At risk"):
        assert section(short, heading) == section(long, heading), heading
    assert (
        short.splitlines()[short.splitlines().index("---") :]
        == (long.splitlines()[long.splitlines().index("---") :])
    )
    at_risk = "\n".join(section(short, "## At risk"))
    assert "[#26](" in at_risk and "(2 times)" in at_risk  # SPEC-0016: named, in a grouped line
    assert f"{PR}27 was merged with no verdict" in at_risk


def test_ac5_the_inbox_output_of_a_busy_week_is_not_changed(tmp_path, capsys, monkeypatch):
    """REQ-022 AC5: SPEC-0015 rule 6."""
    import product_report

    doc = busy_doc()
    short = render_doc(doc, tmp_path, "--inbox", capsys=capsys)
    monkeypatch.setattr(product_report, "BUSY_WEEK", 10**6)
    assert short == render_doc(doc, tmp_path, "--inbox", capsys=capsys)


def test_ac4_unknown_pull_requests_are_not_a_count(tmp_path, capsys):
    """REQ-022 AC4: SPEC-0015 rule 8 (today's unknown line, no collapse)."""
    doc = busy_doc()
    doc["pull_requests"] = "unknown"
    out = render_doc(doc, tmp_path, capsys=capsys)
    assert "were merged this week" not in out
    assert "unknown: pull requests could not be read" in "\n".join(section(out, "## Delivered"))
    assert "unknown: pull requests could not be read" in "\n".join(section(out, "## Cost"))
