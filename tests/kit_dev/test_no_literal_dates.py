"""Kit-only test: no installed file holds a literal date (brief #185, ADR-0112).

A literal `YYYY-MM-DD` date in a role file, a guide or a script of the kit fails a test on the
day it names, when a test rewrites the day it runs (`test_init.py`). The installed files, outside
the templates that the installer stamps with `{{date}}`, hold none. No network, no model.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import KIT_ROOT, manifest

DATE = re.compile(r"(?<![\w-])\d{4}-\d{2}-\d{2}(?![\w-])")


def literal_dates(root: Path, rels: list[str]) -> list[str]:
    """`path:line` of every literal date in the text files RELS of ROOT (`{{date}}` is not one)."""
    found = []
    for rel in rels:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        found += [f"{rel}:{n}" for n, line in enumerate(text.splitlines(), 1) if DATE.search(line)]
    return found


def installed_files() -> list[str]:
    """The kit files the installer writes: the verbatim ones and the sources of the templates."""
    return sorted(set(manifest()["verbatim"]) | set(manifest()["templates"].values()))


def test_the_scan_finds_a_literal_date_and_not_a_placeholder_or_a_week(tmp_path):
    """ADR-0112: the scan itself (a date, but not `{{date}}`, `YYYY-MM-DD`, a week or a version)."""
    (tmp_path / "a.md").write_text("read on 2026-10-25\n", encoding="utf-8")
    (tmp_path / "b.md").write_text(
        "on {{date}}, as YYYY-MM-DD, week 2026-W41, v1.2.3-4\n", encoding="utf-8"
    )
    assert literal_dates(tmp_path, ["a.md", "b.md", "missing.md"]) == ["a.md:1"]


def test_no_installed_file_holds_a_literal_date():
    """ADR-0112 (brief #185 answer 3): a role file or a guide cannot age into a failure again."""
    assert literal_dates(KIT_ROOT, installed_files()) == []


def test_the_conductor_role_keeps_its_documentation_address():
    """ADR-0112 (brief #185 answer 1): the date goes, the address stays."""
    text = (KIT_ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    assert "code.claude.com/docs/en/sub-agents" in text
