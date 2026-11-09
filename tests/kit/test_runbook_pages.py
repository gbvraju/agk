"""Tests of the three shipped runbook pages (SPEC-0056 build (b), rules 2, 3 and 7 to 11; REQ-063).

The pages exist, `check_runbooks.py` passes on them, they and the local-mode guide are verbatim
files of the kit, and no page holds a literal value. The check reads a page and runs nothing; no
test here runs a command a page names.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = KIT_ROOT / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import guard  # noqa: E402

PAGES = (
    "docs/runbooks/actions-blocked.md",
    "docs/runbooks/leaked-secret.md",
    "docs/runbooks/red-default-branch.md",
)
GUIDE = "docs/guides/local-mode.md"
LEAK_LINK = "](../runbooks/leaked-secret.md)"
CREDENTIAL_NAME = re.compile(r"\b[A-Z][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY)\b|secrets\.")


def text_of(rel: str) -> str:
    return (KIT_ROOT / rel).read_text(encoding="utf-8")


def section(page: str, name: str) -> list[str]:
    """The lines of one `## ` section of a page, without its heading."""
    lines = text_of(page).splitlines()
    start = lines.index(f"## {name}") + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start:end]


@pytest.mark.parametrize("page", PAGES)
def test_ac1_the_page_exists(page: str) -> None:
    """REQ-063 AC1: rule 2, one page each at its known path."""
    assert (KIT_ROOT / page).is_file(), page


def test_ac2_the_check_passes_on_the_shipped_pages() -> None:
    """REQ-063 AC2 and AC3: rules 4 to 7 hold on the three pages; the check runs nothing."""
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-I", str(SCRIPTS / "check_runbooks.py"), "--root", str(KIT_ROOT)],
        capture_output=True,
        text=True,
    )
    assert (proc.returncode, proc.stdout) == (0, "ok runbooks\n"), proc.stdout + proc.stderr


@pytest.mark.parametrize("rel", [*PAGES, GUIDE])
def test_ac1_the_file_is_a_verbatim_entry_of_the_kit(rel: str) -> None:
    """REQ-063 AC1: rule 3, `init`, `adopt` and an upgrade place what the manifest lists."""
    manifest = json.loads(text_of("kit/manifest.json"))
    assert rel in manifest["verbatim"], rel
    assert manifest["verbatim"] == sorted(manifest["verbatim"])


@pytest.mark.parametrize("page", PAGES)
def test_ac4_a_page_holds_no_literal_value(page: str) -> None:
    """REQ-063 AC4: rule 7, nothing the guard finds and no credential named."""
    text = text_of(page)
    assert [(f.line, f.kind) for f in guard.scan_text(text)] == [], page
    assert CREDENTIAL_NAME.findall(text) == [], page


def test_ac4_revoking_at_the_provider_is_the_first_step() -> None:
    """REQ-063 AC4: rule 10, before anything in the repository."""
    first = next(ln for ln in section(PAGES[1], "Steps") if ln.startswith("1. "))
    assert "Revoke" in first and "provider" in first, first


def test_ac4_the_leak_page_tells_a_person_never_to_paste_and_never_to_rewrite() -> None:
    """REQ-063 AC4: rules 7 and 10, and the limit of a later green scan."""
    flat = " ".join(text_of(PAGES[1]).split())
    assert "never paste the value" in flat.lower()
    assert "Rewrite no history" in flat and "ignore list" in flat
    assert "says nothing about the old commit" in flat


def test_ac6_the_leak_record_has_the_form_of_rule_11() -> None:
    """REQ-063 AC6: rule 11, the title, the label and the two lines the report reads."""
    text = " ".join(text_of(PAGES[1]).split())
    for part in (
        "`A leaked secret was revoked`",
        "`agk-secret-leak`",
        "`Detected: <UTC time>`",
        "`Revoked: <UTC time>`",
    ):
        assert part in text, part


@pytest.mark.parametrize("guide", ["docs/guides/reference.md", "docs/guides/security.md"])
def test_ac5_each_guide_gains_one_link(guide: str) -> None:
    """REQ-063 AC5: rule 13, a person finds the page from the guide; one link, no more."""
    assert text_of(guide).count(LEAK_LINK) == 1, guide
