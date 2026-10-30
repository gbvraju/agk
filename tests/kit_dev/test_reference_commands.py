"""The reference guide lists the kit's commands (brief #341; REQ-020).

`docs/guides/reference.md` has one section for each of the minutes report, the test plan and the
core audit: the command with its options, one plain sentence, and a link to the guide section (or,
with no guide, the ADR) that explains it (answer 1). Every installed kit script is named in the
reference, unless the kit itself runs it (a target of `agk.mk` or an installed workflow) or another
installed script imports it, so a future command cannot be missed (answer 3). Files only; no
network, no model.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from conftest import KIT_ROOT

REFERENCE = KIT_ROOT / "docs" / "guides" / "reference.md"
GUIDES = KIT_ROOT / "docs" / "guides"
# Installed scripts that are a command of their own but not yet in the reference: none may be
# added here without a brief (Q-341-2).
NOT_YET_LISTED = {"check_brief.py"}

COMMANDS = {
    "minutes.py": {
        "options": ("--json", "--repo OWNER/REPO", "--today YYYY-MM-DD", "--api-dir DIR"),
        "link": "project-ci.md#how-many-minutes-are-left",
    },
    "test_plan.py": {
        "options": ("--base REF", "--head REF", "--json", "ROOT"),
        "link": "existing-codebase.md#step-4-tell-the-proof-check-how-to-run-your-tests",
    },
    "core_audit.py": {
        "options": (
            "--since YYYY-MM-DD",
            "--json",
            "--write",
            "--today YYYY-MM-DD",
            "--repo OWNER/REPO",
            "--api-dir DIR",
            "--authors LOGIN,LOGIN",
        ),
        "link": "../adr/0188-the-kit-reports-which-of-its-checks-and-rules-ever-fired-req-011-"
        "brief-328.md",
    },
}


def reference() -> str:
    return REFERENCE.read_text(encoding="utf-8")


def sections() -> dict[str, str]:
    """The body of each `## ` section of the reference, by its heading."""
    found: dict[str, str] = {}
    for part in reference().split("\n## ")[1:]:
        heading, _, body = part.partition("\n")
        found[heading.strip()] = body
    return found


def section_of(script: str) -> str:
    """The one section whose indented command line runs SCRIPT."""
    command = re.compile(rf"^    python3 scripts/agk/{re.escape(script)}(?: |$)", re.M)
    owners = [body for body in sections().values() if command.search(body)]
    assert len(owners) == 1, (script, len(owners))
    return owners[0]


def anchors(text: str) -> set[str]:
    """GitHub's anchors of the headings of a markdown text."""
    found = set()
    for line in text.splitlines():
        if line.startswith("#"):
            title = line.lstrip("#").strip().lower()
            title = re.sub(r"[^\w\- ]", "", title)
            found.add(title.replace(" ", "-"))
    return found


# --- one section per command (answer 1) ---------------------------------------------------------


@pytest.mark.parametrize("script", sorted(COMMANDS))
def test_each_command_has_a_section_with_its_options(script):
    body = section_of(script)
    line = next(
        ln for ln in body.splitlines() if ln.startswith(f"    python3 scripts/agk/{script}")
    )
    for option in COMMANDS[script]["options"]:
        assert option in line, (script, option)


@pytest.mark.parametrize("script", sorted(COMMANDS))
def test_each_section_links_to_where_the_command_is_explained(script):
    link = COMMANDS[script]["link"]
    body = section_of(script)
    assert f"]({link})" in body, script
    path, _, anchor = link.partition("#")
    target = (GUIDES / path).resolve()
    assert target.is_file(), link
    if anchor:
        assert anchor in anchors(target.read_text(encoding="utf-8")), link


@pytest.mark.parametrize("script", sorted(COMMANDS))
def test_each_section_says_in_one_sentence_what_the_command_does(script):
    prose = [ln for ln in section_of(script).splitlines() if ln and not ln.startswith("    ")]
    assert prose, script
    first = " ".join(prose).split(". ")[0]
    assert 20 <= len(first) <= 300, (script, first)


# --- no installed script is missed (answer 3) ---------------------------------------------------


def installed_scripts() -> list[str]:
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    return sorted(
        Path(rel).name
        for rel in manifest["verbatim"]
        if rel.startswith("scripts/agk/") and rel.endswith(".py")
    )


def run_by_the_kit() -> str:
    """The text of `agk.mk` and of the installed workflows, which name the scripts the kit runs."""
    manifest = json.loads((KIT_ROOT / "kit" / "manifest.json").read_text(encoding="utf-8"))
    names = ["agk.mk"] + [
        rel for rel in manifest["verbatim"] if rel.startswith(".github/workflows/")
    ]
    return "\n".join((KIT_ROOT / rel).read_text(encoding="utf-8") for rel in names)


def imported(script: str, installed: list[str]) -> bool:
    module = script.removesuffix(".py")
    pattern = re.compile(rf"^\s*(?:from {module} import|import {module}\b)", re.M)
    return any(
        pattern.search((KIT_ROOT / "scripts" / "agk" / other).read_text(encoding="utf-8"))
        for other in installed
        if other != script
    )


def test_every_installed_script_is_named_in_the_reference():
    installed = installed_scripts()
    text, kit = reference(), run_by_the_kit()
    missing = [
        script
        for script in installed
        if script not in text
        and script not in kit
        and not imported(script, installed)
        and script not in NOT_YET_LISTED
    ]
    assert missing == [], missing


def test_the_exceptions_are_still_installed_and_still_missing():
    """An exception that is named now, or no longer installed, is removed from the list."""
    installed = installed_scripts()
    for script in NOT_YET_LISTED:
        assert script in installed and script not in reference(), script


def test_the_three_commands_are_found_by_the_check():
    """The check reads the reference: minutes is installed and named there only by this brief."""
    assert "minutes.py" in installed_scripts()
    assert "minutes.py" not in run_by_the_kit()
    assert not imported("minutes.py", installed_scripts())
