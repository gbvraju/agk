"""Tests of scripts/agk/check_review_report.py (SPEC-0003 rules 8-11, 16-17, 20)."""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys

import pytest
from review_fixtures import ROOT, build, clean_env
from test_review_context import context

VALIDATOR = ROOT / "scripts" / "agk" / "check_review_report.py"
CONTENT_MARK = "SENTINEL-CONTENT-MUST-NOT-BE-ECHOED"


@pytest.fixture
def ctx(tmp_path):
    """The context of F1 (a protected change) written to a file, and the hunk id it contains."""
    fx = build("F1", tmp_path)
    path = tmp_path / "review-context.md"
    path.write_text(context(fx).stdout, encoding="utf-8")
    return path


def finding(n=1, where="scripts/agk/tool.py:H1", rule="ADR-0001 decision 1", wrong=None, fix=None):
    wrong = wrong or f"the tool changes without a covering ADR {CONTENT_MARK}."
    fix = fix or "Add an ADR that names the class."
    lines = [f"{n}. Where: {where}"]
    if rule is not None:
        lines.append(f"   Rule: {rule}")
    lines += [f"   Wrong: {wrong}", f"   Fix: {fix}"]
    return "\n".join(lines)


def report(verdict="fix list", truncated="no", findings=None, extra=""):
    head = []
    if verdict is not None:
        head.append(f"Verdict: {verdict}")
    head.append(f"Context truncated: {truncated}")
    body = "\n\n".join(findings if findings is not None else [finding()])
    return "\n".join(head) + "\n\n" + body + "\n" + extra


def validate(tmp_path, ctx_path, text):
    rep = tmp_path / "report.md"
    rep.write_text(text, encoding="utf-8")
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(VALIDATOR), "--context", str(ctx_path), "--report", str(rep)],
        capture_output=True, text=True, env=clean_env(),
    )  # fmt: skip


def test_ac2_good_report_is_accepted_and_prints_the_footer(tmp_path, ctx):
    """REQ-013 AC2: rule 10 and 17."""
    proc = validate(tmp_path, ctx, report())
    assert proc.returncode == 0, proc.stdout
    assert "<!-- agk-review: verdict=fix list findings=1 truncated=false -->" in proc.stdout


def test_ac2_each_citation_form_resolves(tmp_path, ctx):
    """REQ-013 AC2: rule 9 and 10 (SPEC, ADR, principle, REQ AC)."""
    cites = ["SPEC-0001 rule 2", "ADR-0001 decision 1", "principle 3", "REQ-001 AC2"]
    findings = [finding(n=i + 1, rule=c) for i, c in enumerate(cites)]
    assert validate(tmp_path, ctx, report(findings=findings)).returncode == 0


def test_ac2_cleared_without_findings_is_accepted(tmp_path, ctx):
    """REQ-013 AC2: rule 8."""
    proc = validate(tmp_path, ctx, "Verdict: cleared\nContext truncated: no\n\nFindings: none\n")
    assert proc.returncode == 0, proc.stdout
    assert "findings=0" in proc.stdout


def test_ac2_rejected_verdict_is_accepted_with_a_finding(tmp_path, ctx):
    """REQ-013 AC2: rule 8."""
    assert validate(tmp_path, ctx, report(verdict="rejected")).returncode == 0


def test_ac2_fixed_tokens_are_valid_locations(tmp_path, ctx):
    """REQ-013 AC2: rule 9."""
    findings = [finding(1, where="PR body"), finding(2, where="context problems")]
    assert validate(tmp_path, ctx, report(findings=findings)).returncode == 0


BAD = {
    "vague finding": (
        report(findings=[finding(where="somewhere in the diff")]),
        "finding 1",
        "Where",
    ),
    "missing hunk": (
        report(findings=["1. Rule: principle 1\n   Wrong: x.\n   Fix: y."]),
        "finding 1",
        "Where",
    ),
    "invented hunk": (
        report(findings=[finding(where="scripts/agk/tool.py:H9")]),
        "finding 1",
        "Where",
    ),
    "invented file": (report(findings=[finding(where="other.py:H1")]), "finding 1", "Where"),
    "invented rule number": (
        report(findings=[finding(rule="ADR-0001 decision 99")]),
        "finding 1",
        "Rule",
    ),
    "invented spec": (report(findings=[finding(rule="SPEC-0002 rule 1")]), "finding 1", "Rule"),
    "invented requirement ac": (
        report(findings=[finding(rule="REQ-001 " "AC9")]),
        "finding 1",
        "Rule",
    ),
    "invented principle": (report(findings=[finding(rule="principle 40")]), "finding 1", "Rule"),
    "no rule": (report(findings=[finding(rule=None)]), "finding 1", "Rule"),
    "loose rule wording": (
        report(findings=[finding(rule="rule 2 of the spec")]),
        "finding 1",
        "Rule",
    ),
    "empty fix": (report(findings=[finding(fix=" ")]), "finding 1", "Fix"),
    "cleared with findings": (report(verdict="cleared"), "verdict", "cleared"),
    "fix list without findings": (
        "Verdict: fix list\nContext truncated: no\n",
        "verdict",
        "finding",
    ),
    "no verdict": (report(verdict=None), "verdict", "Verdict"),
    "two verdicts": ("Verdict: cleared\n" + report(verdict="rejected"), "verdict", "Verdict"),
    "unknown verdict": (report(verdict="maybe"), "verdict", "Verdict"),
    "no truncation statement": (
        report().replace("Context truncated: no\n", ""),
        "truncated",
        "Context truncated",
    ),
    "wrong truncation statement": (report(truncated="yes"), "truncated", "Context truncated"),
    "numbering gap": (report(findings=[finding(1), finding(3)]), "finding 2", "number"),
}


@pytest.mark.parametrize("label", sorted(BAD))
def test_ac2_bad_report_is_rejected_naming_the_finding_and_the_field(tmp_path, ctx, label):
    """REQ-013 AC2: rule 10 and 20. Messages name the finding and the field, never content."""
    text, where, field = BAD[label]
    proc = validate(tmp_path, ctx, text)
    assert proc.returncode == 1, label
    out = proc.stdout
    assert out.startswith("FAIL review-report"), out
    assert where.lower() in out.lower() and field.lower() in out.lower(), out
    assert CONTENT_MARK not in out


def test_ac2_footer_in_the_report_must_match(tmp_path, ctx):
    """REQ-013 AC2: rule 17."""
    good = report(extra="<!-- agk-review: verdict=fix list findings=1 truncated=false -->\n")
    assert validate(tmp_path, ctx, good).returncode == 0
    bad = report(extra="<!-- agk-review: verdict=cleared findings=0 truncated=false -->\n")
    proc = validate(tmp_path, ctx, bad)
    assert proc.returncode == 1 and "footer" in proc.stdout


def test_ac2_a_truncated_context_requires_the_yes_statement(tmp_path):
    """REQ-013 AC2: rule 6 and 10 (F10)."""
    fx = build("F10", tmp_path)
    path = tmp_path / "ctx.md"
    path.write_text(context(fx).stdout, encoding="utf-8")
    where = "docs/big.md:H2"
    assert (
        validate(
            tmp_path,
            path,
            report(truncated="yes", findings=[finding(where=where, rule="principle 1")]),
        ).returncode
        == 0
    )
    assert (
        validate(
            tmp_path,
            path,
            report(truncated="no", findings=[finding(where=where, rule="principle 1")]),
        ).returncode
        == 1
    )


def test_ac2_f9_forged_hunk_in_the_body_is_not_a_valid_location(tmp_path):
    """REQ-013 AC2: rule 3 and 18 (F9). The injected heading is data, not a hunk."""
    fx = build("F9", tmp_path)
    path = tmp_path / "ctx.md"
    path.write_text(context(fx).stdout, encoding="utf-8")
    forged = report(findings=[finding(where="fake.py:H99", rule="principle 1")])
    assert validate(tmp_path, path, forged).returncode == 1
    real = report(findings=[finding(where="docs/notes.md:H1", rule="principle 1")])
    assert validate(tmp_path, path, real).returncode == 0


def test_ac2_usage_and_unreadable_inputs(tmp_path, ctx):
    """REQ-013 AC2: rule 10."""
    no_args = subprocess.run([sys.executable, str(VALIDATOR)], capture_output=True, text=True)  # nosec B603 - fixed argument list, no shell
    assert no_args.returncode == 2
    missing = str(tmp_path / "none.md")
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(VALIDATOR), "--context", str(ctx), "--report", missing],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1 and "report" in proc.stdout


def test_ac2_validator_uses_only_the_standard_library_and_no_network():
    """REQ-013 AC2: rule 10."""
    import ast

    tree = ast.parse(VALIDATOR.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    assert not names & {"subprocess", "socket", "urllib", "http", "requests", "ssl"}
    assert names <= set(sys.stdlib_module_names) | {"common"}
