"""Kit-only tests of the texts of the flow-mode release model (SPEC-0028 rules 1, 7 and 8).

The changelog and its template, the sessions' rules of `CLAUDE.md` and the principles, the guide
section and the workflow step of the release check. No network, no model.
"""

from __future__ import annotations

import re

from conftest import KIT_ROOT

CLAUDE = KIT_ROOT / "CLAUDE.md"
PRINCIPLES = KIT_ROOT / "constitution" / "principles.md"
REFERENCE = KIT_ROOT / "docs" / "guides" / "reference.md"
WORKFLOW = KIT_ROOT / ".github" / "workflows" / "governance.yml"


def flat(path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_ac1_the_changelog_and_its_template_have_the_shape_of_rule_1():
    """REQ-035 AC1: rule 1 (heading, Unreleased, then one heading per release, newest first)."""
    for path in (KIT_ROOT / "CHANGELOG.md", KIT_ROOT / "kit" / "templates" / "changelog.md"):
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines[0] == "# Changelog", path
        assert "## Unreleased" in lines, path
        headings = [ln for ln in lines if ln.startswith("## ")]
        assert headings[0] == "## Unreleased", path
        assert all(re.fullmatch(r"## \d+\.\d+\.\d+ \(\d{4}-\d{2}-\d{2}\)", h) for h in headings[1:])
    real = (KIT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert all(re.fullmatch(r"- #\d+ .+", ln) for ln in real.splitlines() if ln.startswith("- "))


def test_ac1_the_changelog_is_not_installed_in_a_project():
    """REQ-035 AC1: rule 1 (a kit file of this repository; the manifest does not list it)."""
    import json

    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    listed = {*manifest["verbatim"], *manifest["templates"], *manifest["templates"].values()}
    assert "CHANGELOG.md" not in listed and "kit/templates/changelog.md" not in listed


def test_ac7_claude_md_and_the_principles_hold_the_rules_of_the_sessions():
    """REQ-035 AC7: rule 7 (several sessions in flow mode, never stacked, Depends-on)."""
    claude = flat(CLAUDE)
    assert "One open PR per session" in claude
    assert "several sessions may have one each" in claude
    assert "never stacked on another's unmerged change" in claude
    assert "`Depends-on: #n`" in claude
    assert "in strict mode" in claude and "a person has one open PR at a time" in claude
    assert "never stacked; one open PR at a time" not in claude
    principles = flat(PRINCIPLES)
    assert "never stacked on another's unmerged change" in principles
    assert "`Depends-on`" in principles and "no stacks" not in principles
    assert "twelve numbered rules" in CLAUDE.read_text(encoding="utf-8")
    assert len(re.findall(r"(?m)^\d+\. ", PRINCIPLES.read_text(encoding="utf-8"))) == 12


def test_ac8_the_guide_section_names_the_line_the_release_and_the_one_command():
    """REQ-035 AC8: rule 8 (in `docs/guides/reference.md`)."""
    text = REFERENCE.read_text(encoding="utf-8")
    assert "## Developing the kit" in text
    section = " ".join(text.split("## Developing the kit", 1)[1].split("\n## ", 1)[0].split())
    assert "`## Unreleased`" in section and "`CHANGELOG.md`" in section
    assert "release pull request" in section and "`scripts/agk/check_release.py`" in section
    assert "`python3 scripts/agk/kit_hashes.py --write`" in section
    assert "strict mode" in section


def test_ac5_the_workflow_runs_the_release_check_only_where_the_kit_suite_is_installed():
    """REQ-035 AC5: rule 5 (a kit-only script; a project has neither the script nor the file)."""
    text = WORKFLOW.read_text(encoding="utf-8")
    block = text.split("      - name: Release check\n", 1)[1].split("\n      - name:", 1)[0]
    assert "hashFiles('kit/agk-kit.mk') != ''" in block
    assert "run: python scripts/agk/check_release.py" in block
    assert "!cancelled()" in block
