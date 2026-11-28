"""Kit tests: the weekly `parts:` lines (SPEC-0076 build (i), rules 9 and 12; brief #2076,
ADR-0866; REQ-083 AC6, AC7 and AC8).

On saved trees with stub records (invented parts, example.com) `parts.report_lines` names, in
record order, each part whose recorded last release is over `[parts] max_age_months` calendar
months before `--today`, each part recorded deprecated or archived, the rows whose health is not
read, then one summary whose flagged count is always `unknown (no advisory scan)`, never 0; at most
10 detail lines. A refused setting, no record, no work type or an unreadable record is one line and
never a failure. `metrics.report` and `personal.report` both show the lines after the packs lines,
their results unchanged. No network, no model.
"""

from __future__ import annotations

import datetime
import inspect
import shutil
import socket
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT_ROOT / "scripts" / "agk"))

import metrics  # noqa: E402
import personal  # noqa: E402
from gates import parts  # noqa: E402

TODAY = datetime.date(2026, 12, 7)
HEAD = (
    "| Need | Part | Version | Kind | Why | Alternatives considered | Licence | Health (date) "
    "| For the business |\n|---|---|---|---|---|---|---|---|---|\n"
)
WORK = '[delivery]\nwork_type = "web-app"\n'
SUMMARY = "parts: {n} recorded; old {a}; deprecated {b}; flagged unknown (no advisory scan)"


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the parts lines opened a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def health(status: str = "maintained", last: str = "2026-11-02", read: str = "2026-11-20") -> str:
    return (
        f"{status}; advisories none; last release {last}; 900 weekly downloads; "
        f"scorecard: not published (read {read}, https://example.com/registry)"
    )


def row(part: str, cell: str, need: str = "web-api") -> str:
    cells = (need, part, "1.0.0", "runtime", "REQ-001", "none", "MIT", cell, "Serves example.com.")
    return "| " + " | ".join(cells) + " |\n"


def tree(tmp: Path, sections: dict[str, str] | None, toml: str = WORK) -> Path:
    (tmp / "docs").mkdir(parents=True, exist_ok=True)
    books = tmp / "config" / "playbooks"
    shutil.copytree(KIT_ROOT / "config" / "playbooks", books, dirs_exist_ok=True)
    (tmp / "agk.toml").write_text('default_branch = "main"\n' + toml, encoding="utf-8")
    if sections is not None:
        body = "".join(f"## {name}\n\n{HEAD}{rows}\n" for name, rows in sections.items())
        text = f"# Parts\n\n{body}Questions for the person:\n\nConfirmed by: none yet\n"
        (tmp / "docs" / "parts.md").write_text(text, encoding="utf-8")
    return tmp


def measured(tmp: Path, toml: str = WORK) -> Path:
    """The brief's measured tree: one part released 400 days before today, one deprecated."""
    rows = row("example-old", health(last="2025-11-02")) + row(
        "example-gone", health(status="deprecated"), "time"
    )
    return tree(tmp, {"node": rows}, toml)


# --- answer 1: the section ------------------------------------------------------------------------


def test_ac7_an_old_and_a_deprecated_part_are_named_with_the_summary(tmp_path):
    """REQ-083 AC7: SPEC-0076 rule 12 (old and deprecated, in record order, then the summary)."""
    assert parts.report_lines(measured(tmp_path), TODAY) == [
        "parts: old example-old (node) released 2025-11-02, older than [parts] max_age_months",
        "parts: deprecated example-gone (node) recorded deprecated (read 2026-11-20)",
        SUMMARY.format(n=2, a=1, b=1),
    ]


def test_ac7_an_archived_old_part_gets_both_lines(tmp_path):
    """REQ-083 AC7: SPEC-0076 rule 12 (archived counts as deprecated; old as well)."""
    root = tree(tmp_path, {"python": row("example-arch", health("archived", "2020-01-02"))})
    assert parts.report_lines(root, TODAY) == [
        "parts: old example-arch (python) released 2020-01-02, older than [parts] max_age_months",
        "parts: deprecated example-arch (python) recorded archived (read 2026-11-20)",
        SUMMARY.format(n=1, a=1, b=1),
    ]


def test_ac7_a_fresh_record_prints_the_summary_alone(tmp_path):
    """REQ-083 AC7: SPEC-0076 rule 12 (nothing old, deprecated or unread)."""
    rows = row("example-new", health()) + row("stdlib", "none (stdlib)", "time")
    assert parts.report_lines(tree(tmp_path, {"node": rows}), TODAY) == [
        SUMMARY.format(n=2, a=0, b=0)
    ]


def test_ac7_unread_rows_are_counted_and_a_bad_date_is_never_old(tmp_path):
    """REQ-083 AC7: SPEC-0076 rule 12 (`not read`, a date out of form; a future date not old)."""
    rows = (
        row("example-a", "not read (harvested)")
        + row("example-b", health(last="2026-13-40"), "b")
        + row("example-c", health(last="2027-01-01"), "c")
        + row("example-d", "inferred from the stack record", "d")
    )
    assert parts.report_lines(tree(tmp_path, {"node": rows}), TODAY) == [
        "parts: health not read 2 rows",
        SUMMARY.format(n=4, a=0, b=0),
    ]


def test_ac7_two_runtimes_each_row_names_its_runtime(tmp_path):
    """REQ-083 AC7: SPEC-0076 rule 12 (each section's runtime)."""
    old = health(last="2024-01-01")
    root = tree(tmp_path, {"node": row("example-n", old), "python": row("example-p", old)})
    found = parts.report_lines(root, TODAY)
    assert found[0].startswith("parts: old example-n (node) ")
    assert found[1].startswith("parts: old example-p (python) ")


def test_ac7_at_most_ten_detail_lines_then_and_more(tmp_path):
    """REQ-083 AC7: SPEC-0076 rule 12 (the cap)."""
    rows = "".join(row(f"example-{i}", health(last="2020-01-02"), f"n{i}") for i in range(12))
    found = parts.report_lines(tree(tmp_path, {"node": rows}), TODAY)
    assert len(found) == 12 and found[10] == "parts: and 2 more"
    assert found[-1] == SUMMARY.format(n=12, a=12, b=0)


def test_ac7_the_flagged_count_is_never_zero_while_no_scan_runs(tmp_path):
    """REQ-083 AC7: SPEC-0076 rule 12, Q-PI-3 (no advisory scan: unknown, never 0)."""
    for found in (parts.report_lines(measured(tmp_path), TODAY),):
        assert found[-1].endswith("flagged unknown (no advisory scan)")
        assert not any("flagged 0" in ln for ln in found)
    source = inspect.getsource(parts.report_lines)
    assert "sbom" not in source and "urlopen" not in source


# --- answer 5: settings ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("months", "old"), [(None, 0), (1, 1), (60, 0)], ids=["default", "one", "sixty"]
)
def test_ac6_max_age_months_sets_what_is_old(tmp_path, months, old):
    """REQ-083 AC6: SPEC-0076 rule 9 (`max_age_months`: 12 by default, 1 and 60)."""
    toml = WORK + (f"\n[parts]\nmax_age_months = {months}\n" if months else "")
    rows = row("example-x", health(last="2026-10-28"))  # 40 days before TODAY
    found = parts.report_lines(tree(tmp_path, {"node": rows}, toml), TODAY)
    assert found[-1] == SUMMARY.format(n=1, a=old, b=0)


@pytest.mark.parametrize(
    ("table", "key"),
    [
        ("max_age_months = 0", "max_age_months"),
        ('max_age_months = "12"', "max_age_months"),
        ('advisories = "high"', "advisories"),
        ('record = "always"', "record"),
        ("colour = 1", "colour"),
    ],
)
def test_ac6_a_refused_setting_is_one_unknown_line(tmp_path, table, key):
    """REQ-083 AC6: SPEC-0076 rule 9 (a refusal names the setting, never the value)."""
    root = measured(tmp_path, WORK + f"\n[parts]\n{table}\n")
    assert parts.report_lines(root, TODAY) == [f"parts: unknown (setting: parts.{key})"]


@pytest.mark.parametrize("value", ["critical-high", "critical", "any"])
def test_ac6_advisories_changes_nothing_while_no_scan_runs(tmp_path, value):
    """REQ-083 AC6: SPEC-0076 rule 9 (`advisories`: the level a later scan reads)."""
    root = measured(tmp_path, WORK + f'\n[parts]\nadvisories = "{value}"\n')
    assert parts.report_lines(root, TODAY) == parts.report_lines(measured(tmp_path), TODAY)


@pytest.mark.parametrize("record", ["required", "optional"])
def test_ac6_record_required_or_optional_gives_the_same_lines(tmp_path, record):
    """REQ-083 AC6: SPEC-0076 rule 9 (`record`: the section never fails)."""
    root = measured(tmp_path, WORK + f'\n[parts]\nrecord = "{record}"\n')
    assert parts.report_lines(root, TODAY)[-1] == SUMMARY.format(n=2, a=1, b=1)


def test_ac7_no_record_no_work_type_and_an_unreadable_record(tmp_path):
    """REQ-083 AC7: SPEC-0076 rule 12 (each one line, never a failure)."""
    (tmp_path / "a").mkdir()
    assert parts.report_lines(tree(tmp_path / "a", None), TODAY) == [
        "parts: not run (no parts record)"
    ]
    (tmp_path / "b").mkdir()
    assert parts.report_lines(measured(tmp_path / "b", toml=""), TODAY) == [
        "parts: not run (no stack chosen)"
    ]
    (tmp_path / "c").mkdir()
    root = tree(tmp_path / "c", None)
    (root / "docs" / "parts.md").write_text("# Parts\n\nno table here\n", encoding="utf-8")
    assert parts.report_lines(root, TODAY) == ["parts: unknown (path class: docs/parts.md)"]


def test_ac8_the_age_is_counted_from_today_never_the_clock(tmp_path):
    """REQ-083 AC8: SPEC-0076 rule 12 (`--today`)."""
    root = measured(tmp_path)
    assert parts.report_lines(root, datetime.date(2025, 12, 1))[-1] == SUMMARY.format(
        n=2, a=0, b=1
    )


# --- answer 2: where it shows ---------------------------------------------------------------------


def test_ac8_the_weekly_metrics_report_shows_the_lines_after_packs(tmp_path):
    """REQ-083 AC8: SPEC-0076 rule 12 (`metrics.report`, its result unchanged)."""
    root = measured(tmp_path)

    class Src:
        def get(self, name, path, older=None):
            return []

    body, incomplete = metrics.report(metrics.Context(Src(), root, []), TODAY, [])
    lines = body.splitlines()
    packs_at = max(i for i, ln in enumerate(lines) if "packs:" in ln)
    parts_at = [i for i, ln in enumerate(lines) if "parts:" in ln]
    signals_at = min(i for i, ln in enumerate(lines) if "signals:" in ln)
    assert parts_at and packs_at < parts_at[0] and parts_at[-1] < signals_at
    assert any(SUMMARY.format(n=2, a=1, b=1) in ln for ln in lines)
    assert incomplete is False


def test_ac8_the_sidecar_report_shows_the_lines_before_its_caution(tmp_path, monkeypatch):
    """REQ-083 AC8: SPEC-0076 rule 12 (`personal.py report`: the sidecar's record, nothing
    posted)."""
    side = measured(tmp_path)
    monkeypatch.setattr(personal, "read_events", lambda sidecar: ([], 0))
    monkeypatch.setattr(personal, "ungated", lambda clone, sidecar: [])
    lines = personal.report(tmp_path, side, "2026-W49", today=TODAY).splitlines()
    assert lines[-1] == personal.CAUTION
    assert lines[-2] == SUMMARY.format(n=2, a=1, b=1)
    assert lines[-5].startswith("packs: ") or lines[-5].startswith("warn packs: ")


def test_ac8_both_reports_call_the_one_reader():
    """REQ-083 AC8: answer 8 (one reader for both reports)."""
    assert "parts.report_lines(" in inspect.getsource(metrics)
    assert "parts.report_lines(" in inspect.getsource(personal.report)


def test_ac8_the_guide_names_both_update_bots_and_the_kit_writes_neither():
    """REQ-083 AC8: SPEC-0076 rule 12, Q-S0076-5 (Renovate and Dependabot named, no file)."""
    guide = (KIT_ROOT / "docs" / "guides" / "reference.md").read_text(encoding="utf-8")
    assert "Renovate" in guide and "Dependabot" in guide
    assert not (KIT_ROOT / ".github" / "renovate.json").exists()
    assert not (KIT_ROOT / ".github" / "dependabot.yml").exists()
