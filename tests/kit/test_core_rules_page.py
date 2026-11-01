"""config/core-rules.md: the page of core rules a session reads first (brief #388; REQ-039).

The page names the core rules chosen in row 13 of the decision table of plan #278 by their
numbers, with at most one plain sentence each, and holds the numbered list that `CLAUDE.md`
carried before, item for item with its numbers; `CLAUDE.md` points at the page instead of
restating the rules (ADR-0247).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "config" / "core-rules.md"
CLAUDE = ROOT / "CLAUDE.md"
RULES = ROOT / "config" / "session-rules.md"
PRINCIPLES = ROOT / "constitution" / "principles.md"

# Row 13: the safety rules and the working rules of the core, by number.
SAFETY_SESSION_RULES = {2, 14, 15, 22, 29, 30, 33}
SAFETY_CLAUDE_ITEMS = {3, 5, 8}
WORKING_SESSION_RULES = {1, 3, 7, 17, 18, 21, 31}

# The numbered list of CLAUDE.md before brief #388, item for item, whitespace flattened.
OLD_CLAUDE_ITEMS = {
    1: (
        "You implement; you never decide. Decisions are ADRs or requirement statuses "
        "written by the reviewers. Where a brief leaves something open, record it as a "
        "`Q-…` question and choose the most conservative reading."
    ),
    2: (
        "One PR per item, branched from the default branch (`origin/<default branch>`), "
        "never stacked on another's unmerged change; a dependence is declared with "
        "`Depends-on: #n`. One open PR per session: several sessions may have one each "
        "in flow mode (`pr_mode` in `agk.toml`); in strict mode, the default, a person "
        "has one open PR at a time. Push and stop; never poll CI; never merge; never "
        "enable auto-merge. Never post a comment whose first line is `Confirmed:`: in "
        "solo mode you print its text and the person posts it (session rule 29)."
    ),
    3: (
        "Protected paths (`config/protected-paths.txt`) change only with an ADR in the "
        "same PR that names each changed path class."
    ),
    4: "Tests first. Every check ships with tests of the check. You never mark anything done.",
    5: "No secrets anywhere, ever; no network calls in checks; no new ignore entries for scanners.",
    6: "Dates from `date -u`. Refusal messages name the setting or path class, never a value.",
    7: (
        "PR body: `Advances: REQ-…`, `Build-state row:` (you never edit "
        "`docs/build-state.md` in a feature PR), `Decisions taken:`, `Questions:`, "
        "`Verified:` (commands and verbatim counts)."
    ),
    8: (
        "No token listed in config/neutrality.txt appears in tracked files "
        "(check_neutrality.py); refusals name the setting, never the value."
    ),
    9: (
        "Unsure of a Claude Code fact: mark it `(verify)` in the file and in the PR "
        "body; an unconfirmed fact is a question, not a guess."
    ),
    10: (
        "Check the state of a pull request with `gh api repos/{owner}/{repo}/pulls/{n}` "
        "(a GET); the GraphQL form of the command is blocked in cloud sessions."
    ),
}

COMPACTION = (
    "## Compaction recovery\n\nAfter compaction or a new session, re-read CLAUDE.md, "
    "the current brief, `docs/runs/decisions-log.md` and the\nopen PR body before acting.\n"
)

REF = re.compile(r"`?(session rule|principle|CLAUDE\.md item) (\d+)`?")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def flat(text: str) -> str:
    return " ".join(text.split())


def numbered(text: str) -> dict[int, str]:
    """The numbered items of a markdown list: number -> flattened text, continuations joined."""
    items: dict[int, str] = {}
    current = None
    for line in text.splitlines():
        m = re.match(r"^(\d+)\. (.*)$", line)
        if m:
            current = int(m.group(1))
            items[current] = m.group(2)
        elif current is not None and line.startswith("   ") and line.strip():
            items[current] += " " + line.strip()
        else:
            current = None
    return {n: flat(t) for n, t in items.items()}


def section(text: str, title: str) -> str:
    m = re.search(rf"(?ms)^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text)
    assert m, title
    return m.group(1)


def summary_lines(text: str, title: str) -> dict[tuple[str, int], str]:
    """`- <reference>: <summary>` lines of a section: (kind, number) -> summary."""
    out: dict[tuple[str, int], str] = {}
    for line in section(text, title).splitlines():
        if not line.startswith("- "):
            continue
        m = re.match(r"^- `(session rule|CLAUDE\.md item) (\d+)`: (.+)$", line)
        assert m, line
        out[(m.group(1), int(m.group(2)))] = m.group(3)
    return out


def test_req039_the_page_exists_and_fits_one_page():
    """REQ-039: brief #388 answer 4 (at most 60 lines)."""
    lines = read(PAGE).splitlines()
    assert 0 < len(lines) <= 60, len(lines)


def test_req039_the_page_says_the_numbered_rules_win():
    """REQ-039: brief #388 answer 1 (its top says the numbered rules win over the summaries)."""
    top = flat("\n".join(read(PAGE).splitlines()[:8]))
    assert "The numbered rules win over the summaries" in top


def test_req039_the_page_names_exactly_the_core_of_row_13():
    """REQ-039: brief #388 answer 1 (the constitution, the safety and working rules of row 13)."""
    text = read(PAGE)
    assert "principles 1 to 12" in flat(section(text, "The constitution"))
    safety = summary_lines(text, "Safety rules")
    assert set(safety) == {("session rule", n) for n in SAFETY_SESSION_RULES} | {
        ("CLAUDE.md item", n) for n in SAFETY_CLAUDE_ITEMS
    }
    working = summary_lines(text, "Working rules")
    assert set(working) == {("session rule", n) for n in WORKING_SESSION_RULES}


def test_req039_each_summary_is_at_most_one_plain_sentence():
    """REQ-039: brief #388 answer 1 (a plain summary of at most one sentence)."""
    text = read(PAGE)
    for title in ("Safety rules", "Working rules"):
        for ref, summary in summary_lines(text, title).items():
            assert summary.endswith("."), ref
            body = re.sub(r"`[^`]*`", "", summary[:-1])
            assert not re.search(r"[.!?;](\s|$)", body), ref


def test_req039_every_rule_the_page_names_exists():
    """REQ-039: brief #388 answer 4 (every rule the page names exists)."""
    text = read(PAGE)
    rules = numbered(read(RULES))
    principles = numbered(read(PRINCIPLES))
    items = numbered(section(text, "CLAUDE.md items"))
    assert len(principles) == 12
    named = set(REF.findall(text))
    assert named, "the page names no rule"
    for kind, number in named:
        n = int(number)
        if kind == "session rule":
            assert n in rules, f"session rule {n}"
        elif kind == "principle":
            assert n in principles, f"principle {n}"
        else:
            assert n in items, f"CLAUDE.md item {n}"


def test_req039_every_old_claude_md_item_is_on_the_page_with_its_number_and_exact_text():
    """REQ-039: brief #388 answers 2 and 4 (never dropped, never renumbered, exact text)."""
    items = numbered(section(read(PAGE), "CLAUDE.md items"))
    assert set(items) == set(OLD_CLAUDE_ITEMS)
    for n, text in OLD_CLAUDE_ITEMS.items():
        assert items[n] == flat(text), f"CLAUDE.md item {n}"


def test_req039_claude_md_points_at_the_page_and_restates_no_rule():
    """REQ-039: brief #388 answer 2 (a pointer instead of the numbered list)."""
    text = read(CLAUDE)
    assert "`config/core-rules.md`" in text
    assert not numbered(text), "CLAUDE.md still carries a numbered list"
    for n, item in OLD_CLAUDE_ITEMS.items():
        assert flat(item)[:40] not in flat(text), f"CLAUDE.md item {n} is still restated"


def test_req039_claude_md_keeps_its_compaction_recovery_section_and_the_rules_file_pointer():
    """REQ-039: brief #388 answers 2 and 4 (the section is kept; REQ-037 AC1's pointer holds)."""
    text = read(CLAUDE)
    assert text.endswith(COMPACTION)
    assert "config/session-rules.md" in text
    assert "`constitution/principles.md` is authoritative (twelve numbered rules)" in text


def test_req039_the_page_changes_no_rule_text():
    """REQ-039: brief #388 answer 3 (the page cites the files; the rules keep their numbers)."""
    rules = numbered(read(RULES))
    assert sorted(rules) == list(range(1, len(rules) + 1))
    assert "config/session-rules.md" in read(PAGE) and "constitution/principles.md" in read(PAGE)
