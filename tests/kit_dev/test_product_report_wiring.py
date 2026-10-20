"""Kit-only tests of the product report wiring: manifest, version, templates, layout, notice."""

from __future__ import annotations

import subprocess
import sys

from conftest import (
    KIT_ROOT,
    assert_lean,
    clean_env,
    kit_fixture_files,
    make_repo,
    manifest,
    run_init,
)

INSTALLED = {
    ".github/workflows/product-report.yml",
    "scripts/agk/product_report.py",
    "tests/kit/test_product_report.py",
    "tests/kit/test_product_report_workflow.py",
}


def test_ac1_the_report_files_and_fixtures_are_installed_by_init_and_adopt():
    """REQ-018 AC1: SPEC-0011 rule 17 (verbatim files; nothing extra to opt into)."""
    assert_lean(INSTALLED)
    fixtures = kit_fixture_files("tests/kit/fixtures/report")
    assert len(fixtures) > 30 and not fixtures & set(manifest()["verbatim"])


def test_ac1_kit_version_is_at_least_0_16_0():
    """REQ-018 AC1: the workflow item bumps the minor version."""
    version = tuple(int(part) for part in manifest()["kit_version"].split("."))
    assert version >= (0, 16, 0)


def test_ac1_both_agk_toml_templates_carry_inbox_hours_48():
    """REQ-017 AC1: SPEC-0011 rule 22 (the key is new in agk.toml)."""
    for name in ("agk.toml", "agk.adopt.toml"):
        text = (KIT_ROOT / "kit" / "templates" / name).read_text(encoding="utf-8")
        assert "\ninbox_hours = 48\n" in text, name


def test_ac1_init_prints_a_notice_that_names_three_workflows():
    """REQ-018 AC1: SPEC-0011 rule 17."""
    text = (KIT_ROOT / "scripts" / "agk" / "init.py").read_text(encoding="utf-8")
    assert "drift-audit.yml, metrics.yml and product-report.yml" in text


def test_ac1_installed_repository_gets_the_workflow_and_renders_a_report(installed):
    """REQ-018 AC1: the installed script runs in an installed repository, from a facts file."""
    assert (installed / ".github" / "workflows" / "product-report.yml").is_file()
    facts = subprocess.run(
        [sys.executable, "scripts/agk/facts.py", "--today", "2026-10-14", "--repo", "o/r"],
        cwd=installed,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert facts.returncode == 0, facts.stdout + facts.stderr
    (installed / "facts.json").write_text(facts.stdout, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "scripts/agk/product_report.py", "--facts", "facts.json"],
        cwd=installed,
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines()[0] == "<!-- agk-product-report: 2026-W41 -->"


def test_ac1_run_init_notice_names_the_three_workflows(target):
    """REQ-018 AC1: the notice printed by init."""
    proc = run_init(target)
    assert "drift-audit.yml, metrics.yml and product-report.yml" in proc.stdout.replace("\n", " ")


def test_ac1_init_and_adopt_warn_that_the_issue_writing_workflows_need_issues_enabled(
    target, tmp_path
):
    """REQ-002 AC1: SPEC-0006 amendment (the install prints the warning; it reads no setting)."""
    flat = run_init(target).stdout.replace("\n", " ")
    assert "warning: those workflows need Issues enabled on the repository" in flat
    assert "`agk doctor` checks the setting (issues-disabled)" in flat
    existing = make_repo(tmp_path / "existing", branch="main")
    out = subprocess.run(
        [sys.executable, str(KIT_ROOT / "scripts" / "agk" / "adopt.py"), str(existing)],
        capture_output=True,
        text=True,
        env=clean_env(),
    )
    assert out.returncode == 0, out.stdout + out.stderr
    assert "warning: those workflows need Issues enabled on the repository" in out.stdout.replace(
        "\n", " "
    )
