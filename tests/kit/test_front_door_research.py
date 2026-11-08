"""Tests of `front_door.py` build (d): the research record and the design (SPEC-0048 6, 7).

REQ-055 AC3 (rule 6): a research record has at least two options, the criteria table with its
seven criteria, a dated source line for every option and a recommendation marked `(proposal)`; a
record cited by a design is stale when any source was accessed more than 180 days before the date
given, so 179 and 180 days pass and 181 fails. REQ-055 AC4 (rule 7): the architecture file is a
text diagram with one `Research:` line naming the record of its slug, and a stale record fails it.
Every refusal names the rule and the file, never a value (rule 15). Fixtures in `tmp_path` only:
invented data (`example.com`), no network (a socket stub raises).
"""

from __future__ import annotations

import datetime
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "agk" / "front_door.py"
sys.path.insert(0, str(SCRIPT.parent))

TODAY = "2026-11-08"
SLUG = "orders-are-lost"
OPTION_A = "Hosted queue Alpha"
OPTION_B = "Hosted queue Beta"
URL_A = "https://alpha.example.com/docs"
URL_B = "https://beta.example.com/docs"
CRITERIA = [
    "capability fit",
    "cost",
    "licence",
    "data handling and residency",
    "maturity",
    "integration effort",
    "lock-in",
]
PLANTED = "10.1.2.3"  # an invented private address the data guard finds (kind IP)


def days_before(days: int) -> str:
    return (datetime.date.fromisoformat(TODAY) - datetime.timedelta(days=days)).isoformat()


def record_text(
    accessed: str = "2026-10-01",
    criteria=CRITERIA,
    options=((OPTION_A, URL_A), (OPTION_B, URL_B)),
    recommendation=f"{OPTION_A}, for its lower integration effort (proposal).",
) -> str:
    lines = ["# Research: Orders are lost", ""]
    for name, url in options:
        lines += [f"## Option: {name}", "", f"- Source: {url} (accessed {accessed})", ""]
    names = [name for name, _ in options]
    lines += [
        "## Criteria",
        "",
        "| Criterion | " + " | ".join(names) + " |",
        "| --- | " + " | ".join("---" for _ in names) + " |",
    ]
    lines += [f"| {c} | " + " | ".join("invented" for _ in names) + " |" for c in criteria]
    lines += ["", "## Recommendation", "", recommendation, ""]
    return "\n".join(lines)


def design_text(research: str = f"Research: docs/research/{SLUG}.md", diagram: bool = True) -> str:
    lines = ["# Architecture: Orders are lost", "", research, ""]
    if diagram:
        lines += ["```text", "browser -> shop api -> queue -> worker -> orders store", "```", ""]
    return "\n".join(lines)


def write(tmp_path: Path, rel: str, text: str) -> Path:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def record(tmp_path: Path, text: str | None = None, slug: str = SLUG) -> Path:
    return write(tmp_path, f"docs/research/{slug}.md", record_text() if text is None else text)


def design(tmp_path: Path, text: str | None = None, slug: str = SLUG) -> Path:
    rel = f"docs/design/architecture/{slug}.md"
    # No discovery document gives `Screens:`, so rule 8 reads `open` as `yes`: a prototype version.
    (tmp_path / "docs" / "design" / "prototype" / "v1").mkdir(parents=True, exist_ok=True)
    return write(tmp_path, rel, design_text() if text is None else text)


def run(tmp_path: Path, *args: str, date: str | None = TODAY):
    extra = ["--date", date] if date is not None else []
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPT), *args, *extra, "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )


def no_value(out: str) -> bool:
    return all(v not in out for v in (OPTION_A, OPTION_B, URL_A, URL_B, PLANTED, "invented"))


# --- rule 6: the research record -----------------------------------------------------------------


def test_ac3_a_record_with_its_form_passes(tmp_path):
    """REQ-055 AC3: SPEC-0048 rule 6 (two options, seven criteria, dated sources, a proposal)."""
    record(tmp_path)
    proc = run(tmp_path, "check-research")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok front-door: check-research (1 records)" in proc.stdout


@pytest.mark.parametrize(
    "text,expected",
    [
        (record_text(options=((OPTION_A, URL_A),)), "at least two options"),
        (record_text(criteria=CRITERIA[:-1]), "`lock-in`"),
        (record_text(criteria=[c for c in CRITERIA if c != "cost"]), "`cost`"),
        (record_text().replace(" (accessed 2026-10-01)", "", 1), "without an access date"),
        (record_text(accessed="2026-02-30"), "without an access date"),
        (record_text().replace(f"- Source: {URL_B}", "- See also:"), "option 2 has no source"),
        (record_text(recommendation=f"{OPTION_A}."), "(proposal)"),
        (record_text().split("## Recommendation")[0], "`## Recommendation`"),
        (record_text().replace("## Criteria", "## Notes"), "`## Criteria`"),
        ("Research about queues.\n", "`# Research: <title>`"),
    ],
    ids=[
        "one-option",
        "no-lock-in",
        "no-cost",
        "source-without-date",
        "impossible-date",
        "option-without-source",
        "not-a-proposal",
        "no-recommendation",
        "no-criteria-table",
        "no-title",
    ],
)
def test_ac3_each_record_without_its_form_fails_naming_the_rule_and_the_file(
    tmp_path, text, expected
):
    """REQ-055 AC3: SPEC-0048 rules 6 and 15 (the rule and the file, never a value)."""
    record(tmp_path, text)
    proc = run(tmp_path, "check-research")
    assert proc.returncode == 1, proc.stdout
    assert f"rule 6: docs/research/{SLUG}.md" in proc.stdout and expected in proc.stdout
    assert no_value(proc.stdout)


@pytest.mark.parametrize("days,ok", [(179, True), (180, True), (181, False)])
def test_ac3_a_cited_record_is_stale_after_180_days(tmp_path, days, ok):
    """REQ-055 AC3: SPEC-0048 rule 6 (freshness: more than 180 days before `--date` is stale)."""
    record(tmp_path, record_text(accessed=days_before(days)))
    design(tmp_path)
    research = run(tmp_path, "check-research")
    built = run(tmp_path, "check-design")
    assert (research.returncode == 0) is ok, research.stdout
    assert (built.returncode == 0) is ok, built.stdout
    if not ok:
        assert f"rule 6: docs/research/{SLUG}.md" in research.stdout
        assert "180 days" in research.stdout
        assert f"rule 7: docs/design/architecture/{SLUG}.md" in built.stdout
        assert "stale" in built.stdout and "rule 6" in built.stdout
        assert no_value(research.stdout + built.stdout)


def test_ac3_one_old_source_among_fresh_ones_makes_a_cited_record_stale(tmp_path):
    """REQ-055 AC3: SPEC-0048 rule 6 (any source line older than 180 days)."""
    text = record_text().replace("(accessed 2026-10-01)", f"(accessed {days_before(181)})", 1)
    record(tmp_path, text)
    design(tmp_path)
    proc = run(tmp_path, "check-research")
    assert proc.returncode == 1 and "180 days" in proc.stdout


def test_ac3_an_uncited_old_record_passes_its_form_and_is_noted(tmp_path):
    """REQ-055 AC3: SPEC-0048 rule 6 (stale only when a design cites it; re-verified by a PR)."""
    record(tmp_path, record_text(accessed=days_before(400)))
    proc = run(tmp_path, "check-research")
    assert proc.returncode == 0, proc.stdout
    assert f"note front-door: rule 6: docs/research/{SLUG}.md" in proc.stdout
    assert "no design cites it" in proc.stdout


def test_ac3_a_re_read_source_makes_the_record_fresh_again(tmp_path):
    """REQ-055 AC3: SPEC-0048 rule 6 (changed access dates make the record fresh)."""
    path = record(tmp_path, record_text(accessed=days_before(200)))
    design(tmp_path)
    assert run(tmp_path, "check-design").returncode == 1
    path.write_text(record_text(accessed=days_before(3)), encoding="utf-8")
    assert run(tmp_path, "check-design").returncode == 0


def test_ac7_the_record_is_scanned_by_the_guard(tmp_path):
    """REQ-055 AC7: SPEC-0048 rule 14 (the check of rule 6 scans with `guard.scan_text`)."""
    record(tmp_path, record_text() + f"\nOur router is {PLANTED}.\n")
    proc = run(tmp_path, "check-research")
    assert proc.returncode == 1 and "rule 14" in proc.stdout and "IP" in proc.stdout
    assert no_value(proc.stdout)


def test_ac3_named_files_are_checked_and_no_record_passes(tmp_path):
    """REQ-055 AC3: SPEC-0048 rule 6 (every `docs/research/*.md` by default)."""
    proc = run(tmp_path, "check-research")
    assert proc.returncode == 0 and "no research record" in proc.stdout
    record(tmp_path, "broken\n", slug="other")
    good = record(tmp_path)
    assert run(tmp_path, "check-research", str(good)).returncode == 0
    assert run(tmp_path, "check-research").returncode == 1


# --- rule 7: the design --------------------------------------------------------------------------


def test_ac4_a_design_with_its_diagram_and_research_line_passes(tmp_path):
    """REQ-055 AC4: SPEC-0048 rule 7 (a text diagram and one `Research:` line)."""
    record(tmp_path)
    design(tmp_path)
    proc = run(tmp_path, "check-design")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ok front-door: check-design (1 designs)" in proc.stdout


def test_ac4_a_mermaid_diagram_passes(tmp_path):
    """REQ-055 AC4: SPEC-0048 rule 7 (Mermaid or plain text)."""
    record(tmp_path)
    text = design_text(diagram=False) + "```mermaid\nflowchart LR\n  shop --> queue\n```\n"
    design(tmp_path, text)
    assert run(tmp_path, "check-design").returncode == 0


@pytest.mark.parametrize(
    "text,expected",
    [
        (design_text(research=""), "one `Research:` line"),
        (design_text() + f"\nResearch: docs/research/{SLUG}.md\n", "one `Research:` line"),
        (design_text(research="Research: docs/research/other.md"), "of its own slug"),
        (design_text(diagram=False), "text diagram"),
        (design_text() + "\n![parts](parts.png)\n", "image"),
        (design_text() + '\n<img src="parts.svg">\n', "image"),
    ],
    ids=["no-line", "two-lines", "other-slug", "no-diagram", "markdown-image", "html-image"],
)
def test_ac4_each_design_without_its_form_fails_naming_the_rule_and_the_file(
    tmp_path, text, expected
):
    """REQ-055 AC4: SPEC-0048 rules 7 and 15 (the rule and the file, never a value)."""
    record(tmp_path)
    design(tmp_path, text)
    proc = run(tmp_path, "check-design")
    assert proc.returncode == 1, proc.stdout
    assert f"rule 7: docs/design/architecture/{SLUG}.md" in proc.stdout
    assert expected in proc.stdout and no_value(proc.stdout)


def test_ac4_a_design_whose_record_is_missing_or_broken_fails(tmp_path):
    """REQ-055 AC4: SPEC-0048 rule 7 (the design's record must exist and pass rule 6)."""
    design(tmp_path)
    proc = run(tmp_path, "check-design")
    assert proc.returncode == 1 and "does not exist" in proc.stdout
    record(tmp_path, record_text(recommendation="Alpha."))
    proc = run(tmp_path, "check-design")
    assert proc.returncode == 1 and "rule 6" in proc.stdout and "(proposal)" in proc.stdout


def test_ac4_no_design_passes_and_says_so(tmp_path):
    """REQ-055 AC4: SPEC-0048 rule 7 (a project with no design passes)."""
    proc = run(tmp_path, "check-design")
    assert proc.returncode == 0 and "no design" in proc.stdout


# --- rules 6, 15 and 16: usage and no network ----------------------------------------------------


@pytest.mark.parametrize("cmd", ["check-research", "check-design"])
@pytest.mark.parametrize("date", [None, "08-11-2026", "2026-13-01"])
def test_ac3_the_date_is_required_and_read_from_the_argument(tmp_path, cmd, date):
    """REQ-055 AC3: SPEC-0048 rule 6 (`--date` from `date -u`; a check never reads a clock)."""
    proc = run(tmp_path, cmd, date=date)
    assert proc.returncode == 2 and "usage" in proc.stderr


def test_ac3_no_url_is_fetched(tmp_path, monkeypatch, capsys):
    """REQ-055 AC3: SPEC-0048 rule 16 (files only: a socket stub raises)."""
    import front_door

    def refuse(*_a, **_k):
        raise AssertionError("a check opened a socket")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    record(tmp_path)
    design(tmp_path)
    root = ["--date", TODAY, "--root", str(tmp_path)]
    assert front_door.main(["check-research", *root]) == 0
    assert front_door.main(["check-design", *root]) == 0
    assert "ok front-door" in capsys.readouterr().out
