"""Kit-only tests of the reviewer wiring: manifest, requirement, version, installed layout."""

from __future__ import annotations

import subprocess
import sys

from conftest import KIT_ROOT, clean_env, expected_files, git, manifest

GOOD_BODY = "Advances: REQ-001\n\nBuild-state row: 2026-10-15 | a demo change | REQ-001\n"
SECTIONS = [
    "Context problems",
    "PR body",
    "Diff",
    "Requirements",
    "Protected classes touched",
    "Referenced specs and ADRs",
    "Principles",
]


def test_ac3_reviewer_and_scripts_are_installed_by_init_and_adopt():
    """REQ-013 AC3: rule 13."""
    wanted = {
        ".claude/agents/reviewer.md",
        "scripts/agk/review_context.py",
        "scripts/agk/check_review_report.py",
    }
    assert wanted <= set(manifest()["verbatim"])
    assert wanted <= expected_files()


def test_ac3_requirement_013_exists_and_is_planned():
    """REQ-013 AC3: rule 15 (an ADR adds the requirement). Never marked done by an agent."""
    text = (KIT_ROOT / "docs" / "requirements.md").read_text(encoding="utf-8")
    section = text.split("### REQ-013", 1)[1].split("\n### ", 1)[0]
    for ac in ("AC1", "AC2", "AC3", "AC4"):
        assert ac in section
    assert "- Status: planned" in section


def test_ac3_kit_version_is_at_least_0_5_0():
    """REQ-013 AC3: ADR-0011 shipped the reviewer in 0.5.0; later versions keep it."""
    version = tuple(int(part) for part in manifest()["kit_version"].split("."))
    assert version >= (0, 5, 0)


def test_ac3_the_template_requirements_are_not_changed_by_this_requirement():
    """REQ-013 AC3: installed repositories get no REQ-013."""
    template = (KIT_ROOT / "kit" / "templates" / "requirements.md").read_text(encoding="utf-8")
    assert "REQ-013" not in template


def test_ac1_context_runs_in_an_installed_repository(installed):
    """REQ-013 AC1: rule 13. The installed scripts work without the kit checkout."""
    git(installed, "checkout", "-q", "-b", "feature")
    (installed / "notes.txt").write_text("hello\n", encoding="utf-8")
    body = installed / ".." / "body.md"
    body.write_text(GOOD_BODY, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "scripts/agk/review_context.py", "--base", "main", "--body", str(body)],
        cwd=installed, capture_output=True, text=True, env=clean_env(),
    )  # fmt: skip
    assert proc.returncode == 0, proc.stdout + proc.stderr
    context = installed / ".." / "review-context.md"
    context.write_text(proc.stdout, encoding="utf-8")
    report = installed / ".." / "report.md"
    truncated = "yes" if "\nTruncated: yes\n" in proc.stdout else "no"
    report.write_text(
        f"Verdict: cleared\nContext truncated: {truncated}\n\nFindings: none\n", encoding="utf-8"
    )
    validator = [
        "scripts/agk/check_review_report.py",
        "--context",
        str(context),
        "--report",
        str(report),
    ]
    check = subprocess.run(
        [sys.executable, *validator],
        cwd=installed,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert check.returncode == 0, check.stdout
    headings = [line[3:] for line in proc.stdout.splitlines() if line.startswith("## ")]
    assert [h for h in headings if h in SECTIONS] == SECTIONS
