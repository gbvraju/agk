"""Kit-only tests of the conductor catch log and its operating lessons (brief #604, ADR-0294).

Every conductor incident is a row of `docs/runs/conductor-catches-N.md` with the strongest guard
that prevents it: a check, else a test, else a rule line of `.claude/agents/conductor.md`, or a
pending brief. The tests read files only: no network, so a `pending #n` is read for its form.
"""

from __future__ import annotations

import re

from conftest import KIT_ROOT

RUNS = KIT_ROOT / "docs" / "runs"
LOGS = sorted(RUNS.glob("conductor-catches-*.md"))
ARCHITECT_LOGS = sorted(RUNS.glob("architect-catches-*.md"))
CONDUCTOR = KIT_ROOT / ".claude" / "agents" / "conductor.md"
COLUMNS = ["#", "Date", "Kind", "What happened", "Cost", "Cause", "Guard"]
GUARD = re.compile(
    r"^(?:(check|test|rule) `([^`]+)`|pending #(\d+)|pending \(to be filed\))"
    r"(?: \([^()]*(?:\([^()]*\)[^()]*)*\))?$"
)
COST = re.compile(r"^(?:\d+(?:\.\d+)? (?:h|min|merges?)\b|\(unknown\))")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}\b")


def kinds(path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    paragraph = text.split("Kinds (fixed list):", 1)[1].split("\n\n", 1)[0]
    if "(a fact" in paragraph:
        paragraph = paragraph.split("(a fact", 1)[0]
    return re.findall(r"`([a-z-]+)`", paragraph)


def table(path) -> tuple[list[str], list[list[str]]]:
    text = path.read_text(encoding="utf-8").split("## The catches", 1)[1]
    lines = [ln for ln in text.splitlines() if ln.startswith("|")]
    cells = [[c.strip() for c in ln.strip().strip("|").split(" | ")] for ln in lines]
    return cells[0], [row for row in cells[2:]]


def rows() -> list[dict[str, str]]:
    found = []
    for path in LOGS:
        header, body = table(path)
        found += [dict(zip(header, row, strict=True), log=path.name) for row in body]
    return found


def guards(row: dict[str, str]) -> list[re.Match]:
    return [GUARD.match(part.strip()) for part in row["Guard"].split("; ")]


def lessons() -> str:
    text = CONDUCTOR.read_text(encoding="utf-8")
    assert "## Operating lessons" in text
    return text.split("## Operating lessons", 1)[1].split("\n## ", 1)[0]


def test_the_catch_log_exists_and_parses_with_the_columns_of_the_brief():
    assert LOGS and LOGS[0].name == "conductor-catches-1.md"
    for path in LOGS:
        header, body = table(path)
        assert header == COLUMNS, path.name
        assert body, path.name
        for row in body:
            assert len(row) == len(COLUMNS), (path.name, row[0])
    numbers = [int(r["#"]) for r in rows()]
    assert numbers == list(range(1, len(numbers) + 1))


def test_the_first_log_holds_the_seeded_incidents_and_the_rows_of_2026_11_06():
    _, body = table(LOGS[0])
    assert len(body) == 23  # 12 seeded, 2 of the fix list (brief #604), 8 of #695, 1 of #770
    by_number = {r["#"]: r for r in rows()}
    for number in ("15", "16"):  # the pre-merge tests of brief #667 guard both
        assert by_number[number]["Guard"].startswith("check `scripts/agk/merge_cleared.py`")
        assert [g.group(1) for g in guards(by_number[number])] == ["check", "test"]
    assert by_number["13"]["Kind"] == "watch"
    assert [g.group(1) for g in guards(by_number["13"])] == ["check", "rule"]  # brief #643
    assert by_number["3"]["Guard"].startswith("check `scripts/agk/conductor.py`")  # build (b)
    assert by_number["14"]["Kind"] == "kit-gap"
    assert by_number["14"]["Guard"].startswith("pending (to be filed)")


def test_the_rows_of_brief_695_carry_their_kinds_and_guards():
    by_number = {r["#"]: r for r in rows()}
    expected = {
        "15": ("parallel-merge", "check `scripts/agk/merge_cleared.py`"),  # brief #667
        "16": ("parallel-merge", "check `scripts/agk/merge_cleared.py`"),  # brief #667
        "17": ("watch", "check `scripts/agk/conductor.py`"),
        "18": ("false-red", "check `scripts/agk/conductor.py`"),  # brief #700, rerun
        "19": ("false-red", "check `scripts/agk/conductor.py`"),  # brief #700, rerun
        "20": ("kit-gap", "check `scripts/agk/prepush.py`"),
        "21": ("history", "pending (to be filed)"),
        "22": ("unread-result", "check `scripts/agk/conductor.py`"),  # brief #643 build (b)
    }
    for number, (kind, guard) in expected.items():
        row = by_number[number]
        assert row["Date"].startswith("2026-11-06"), number
        assert row["Kind"] == kind, number
        assert row["Guard"].startswith(guard), number


def test_each_row_has_a_date_a_kind_a_cost_a_cause_and_a_guard_of_the_four_forms():
    assert LOGS
    for path in LOGS:
        allowed = kinds(path)
        assert allowed, path.name
        _, body = table(path)
        for cells in body:
            row = dict(zip(COLUMNS, cells, strict=True))
            where = (path.name, row["#"])
            assert DATE.match(row["Date"]), where
            assert row["Kind"] in allowed, where
            assert COST.match(row["Cost"]), where
            assert row["Cause"] and row["What happened"], where
            assert all(guards(row)), where


def test_the_kinds_are_not_the_kinds_the_review_checklist_reads():
    """Brief #604 item 3: the checklist reads the architect kinds; no conductor kind is one."""
    assert ARCHITECT_LOGS and LOGS
    architect = set(kinds(ARCHITECT_LOGS[-1]))
    for path in LOGS:
        assert not set(kinds(path)) & architect, path.name


def test_every_check_or_test_guard_path_exists():
    paths = [g.group(2) for r in rows() for g in guards(r) if g.group(1) in ("check", "test")]
    assert paths
    for row in rows():
        for found in guards(row):
            if found.group(1) in ("check", "test"):
                assert (KIT_ROOT / found.group(2)).exists(), (row["#"], found.group(2))


def test_every_rule_guard_is_a_line_of_conductor_md_that_cites_its_row():
    text = lessons()
    rule_rows = []
    for row in rows():
        for found in guards(row):
            if found.group(1) == "rule":
                assert found.group(2) == ".claude/agents/conductor.md", row["#"]
                rule_rows.append(row["#"])
    assert rule_rows
    for number in rule_rows:
        assert re.search(rf"(?m)^- .*\(row {number}\)", text), number


def test_every_lesson_line_cites_a_rule_row_of_the_log():
    text = lessons()
    rule_rows = {r["#"] for r in rows() for g in guards(r) if g.group(1) == "rule"}
    cited = re.findall(r"(?m)^- .*\(row (\d+)\)", text)
    assert cited and set(cited) <= rule_rows


def test_a_pending_guard_names_an_issue_number():
    pending = [g for r in rows() for g in guards(r) if g.group(0).startswith("pending")]
    assert pending
    for found in pending:
        assert found.group(3) is None or int(found.group(3)) > 0, found.group(0)
    assert any(g.group(3) for g in pending)


def test_the_section_states_the_logging_rule_the_order_of_guards_and_the_monthly_revisit():
    text = lessons()
    assert "before the conductor reports it" in text
    assert "a check before a test before a rule line" in text
    assert "monthly" in text
    assert "conductor-catches-" in text


def test_the_guard_form_and_the_cost_form_refuse_a_bad_cell():
    assert GUARD.match("check `scripts/agk/x.py` (in force)")
    assert GUARD.match("pending #601")
    assert GUARD.match("pending (to be filed)")
    assert not GUARD.match("pending 601")
    assert not GUARD.match("pending (later)")
    assert not GUARD.match("guess `x`")
    assert not GUARD.match("rule conductor.md")
    assert COST.match("25 min") and COST.match("(unknown): overnight")
    assert not COST.match("a lot")


def test_the_lesson_of_row_3_names_the_merge_queue():
    """Brief #643 build (b), ADR-0329: the rule line of row 3 names the kit command."""
    assert re.search(r"(?m)^- .*`conductor\.py merge-queue`.*\(row 3\)", lessons())
