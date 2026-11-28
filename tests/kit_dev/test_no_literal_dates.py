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


PACK_DATE = re.compile(r'^as_of = "\d{4}-\d{2}-\d{2}"$')


def pack_date(found: str) -> bool:
    """ADR-0804: a domain pack's `as_of` line is the pack's data (SPEC-0074 rule 2); its age is a
    `warn domains:` line and never a failure (rule 14), so it cannot age into one."""
    rel, number = found.rsplit(":", 1)
    if not rel.startswith("config/domains/"):
        return False
    line = (KIT_ROOT / rel).read_text(encoding="utf-8").splitlines()[int(number) - 1]
    return bool(PACK_DATE.match(line))


PARTS_DATE = re.compile(
    r'^(source = "https?://\S+ \(accessed \d{4}-\d{2}-\d{2}\)"|reviewed = "\d{4}-\d{2}-\d{2}")$'
)


def parts_date(found: str, root: Path = KIT_ROOT) -> bool:
    """ADR-0861: a stack catalogue's whole `source` line (with its access date) and `reviewed` line are
    the maintainers' data (SPEC-0076 rule 5); no check compares them with the day it runs (`Q-PB-5`),
    so they cannot age into a failure. `needs.toml` holds no dated row and gets no exemption."""
    rel, number = found.rsplit(":", 1)
    folder, _, name = rel.rpartition("/")
    if folder != "config/parts" or not name.endswith(".toml") or name == "needs.toml":
        return False
    line = (root / rel).read_text(encoding="utf-8").splitlines()[int(number) - 1]
    return bool(PARTS_DATE.match(line))


def test_no_installed_file_holds_a_literal_date():
    """ADR-0112 (brief #185 answer 3): a role file or a guide cannot age into a failure again."""
    found = literal_dates(KIT_ROOT, installed_files())
    assert [f for f in found if not pack_date(f) and not parts_date(f)] == []


def test_a_pack_date_is_only_an_as_of_line(tmp_path):
    """ADR-0804: only a pack's whole `as_of` line is the pack's data; any other date still fails."""
    assert pack_date("config/domains/payments.toml:12")
    assert not pack_date("config/domains/payments.toml:1")
    assert not pack_date("config/playbooks/default.toml:1")


def test_the_conductor_role_keeps_its_documentation_address():
    """ADR-0112 (brief #185 answer 1): the date goes, the address stays."""
    text = (KIT_ROOT / ".claude" / "agents" / "conductor.md").read_text(encoding="utf-8")
    assert "code.claude.com/docs/en/sub-agents" in text


def test_a_parts_date_is_only_a_source_or_reviewed_line_of_a_stack_catalogue(tmp_path):
    """ADR-0861 (brief #2082): a stack catalogue's whole `source` (with its access date) and `reviewed`
    lines are the maintainers' data (SPEC-0076 rule 5); any other date there, or elsewhere, still fails."""
    rows = tmp_path / "config" / "parts"
    rows.mkdir(parents=True)
    (rows / "node.toml").write_text(
        'format = 1\n'
        'source = "https://example.com/a (accessed 2026-11-28)"\n'
        'reviewed = "2026-11-28"\n'
        'when = "after 2026-11-28"\n'
        'reviewed = "2026-11-28" # note\n',
        encoding="utf-8",
    )
    (rows / "needs.toml").write_text('reviewed = "2026-11-28"\n', encoding="utf-8")
    (tmp_path / "config" / "other.toml").write_text('reviewed = "2026-11-28"\n', encoding="utf-8")
    assert parts_date("config/parts/node.toml:2", tmp_path)
    assert parts_date("config/parts/node.toml:3", tmp_path)
    assert not parts_date("config/parts/node.toml:4", tmp_path)
    assert not parts_date("config/parts/node.toml:5", tmp_path)
    assert not parts_date("config/parts/needs.toml:1", tmp_path)
    assert not parts_date("config/other.toml:1", tmp_path)


def test_the_shipped_stack_catalogue_dates_are_all_parts_dates():
    """ADR-0861: every date the shipped node catalogue holds sits on a source or reviewed line."""
    found = [f for f in literal_dates(KIT_ROOT, installed_files()) if f.startswith("config/parts/")]
    assert found
    assert [f for f in found if not parts_date(f)] == []
