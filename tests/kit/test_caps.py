"""The cap table, the tokens and hours a build used, and the sweep's OVER lines (SPEC-0049
rules 2, 3 and 5 to 7, brief #714, build (b), ADR-0324).

REQ-056 AC1: `config.caps_settings` reads the optional `[caps]` table and refuses a malformed one
naming `caps.<key>`, never the value. REQ-056 AC3: `caps.py` reads the cap of a builder pull
request from its brief's `Size:` line, the tokens used (never 0 for a missing figure) and the hours
the builder held the turn; `conductor.py sweep` prints one `OVER` line per cap passed and an
`UNKNOWN` line for a build with no token figure, with GET calls only and no file written.
Fixtures in `tmp_path`, saved responses through a `gh` stub, invented data, no network. The tests
were written first (answer 4).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import caps
import pytest
import test_conductor_commands as tcc
from test_conductor_commands import ago, pr, run, serve_pr, sweep
from test_session import REPO, SHA, comment

import config

FULL = (
    "[caps]\n"
    "S = { tokens = 1000, hours = 2 }\n"
    "M = { tokens = 5000, hours = 4 }\n"
    "L = { tokens = 9000, hours = 8 }\n"
)
ODD = 987654321  # a value that a refusal must never print
NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
TABLE = {
    "S": {"tokens": 1, "hours": 1},
    "M": {"tokens": 2, "hours": 2},
    "L": {"tokens": 3, "hours": 3},
}
stub = tcc.stub  # the fixtures of the sweep tests, shared
proj = tcc.proj


def root_with(tmp_path, text: str):
    (tmp_path / "agk.toml").write_text(text, encoding="utf-8")
    return tmp_path


def at(hours: float) -> str:
    """An ISO time `hours` after 00:00 UTC of the fixed day."""
    moment = datetime(2026, 11, 7, tzinfo=UTC) + timedelta(hours=hours)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def brief_body(size: str | None = "M") -> str:
    lines = ['Sentence: "A widget shows its price."', "", "Answers:", "1. The price."]
    if size:
        lines.append(f"Size: {size}")
    return "\n".join([*lines, "Advances: REQ-001", "Touches: src/**", ""])


# --- rule 2: the [caps] table -----------------------------------------------------------------


def test_no_caps_table_gives_no_cap(tmp_path):
    """REQ-056 AC1: rule 2, without the table no build has a cap (Q-S0049-1)."""
    assert config.caps_settings(root_with(tmp_path, "[flow]\n")) is None


def test_a_full_caps_table_is_read(tmp_path):
    """REQ-056 AC1: rule 2, the three sizes with their two whole numbers."""
    assert config.caps_settings(root_with(tmp_path, FULL)) == {
        "S": {"tokens": 1000, "hours": 2},
        "M": {"tokens": 5000, "hours": 4},
        "L": {"tokens": 9000, "hours": 8},
    }


@pytest.mark.parametrize(
    ("text", "setting"),
    [
        (FULL.replace("M = { tokens = 5000, hours = 4 }\n", ""), "caps.M"),
        (FULL.replace("M = { tokens = 5000, hours = 4 }", "M = { tokens = 5000 }"), "caps.M"),
        (FULL + f"X = {{ tokens = {ODD}, hours = 1 }}\n", "caps.X"),
        (FULL.replace("hours = 4", "hours = 4, extra = 1"), "caps.M"),
        (FULL.replace("tokens = 5000", f'tokens = "{ODD}"'), "caps.M"),
        (FULL.replace("tokens = 1000", "tokens = 0"), "caps.S"),
        (FULL.replace("tokens = 1000", f"tokens = -{ODD}"), "caps.S"),
        (FULL.replace("hours = 2", "hours = 1.5"), "caps.S"),
        (FULL.replace("hours = 2", "hours = true"), "caps.S"),
        (FULL.replace("tokens = 1000", f"tokens = {ODD}"), "caps.M"),
        (FULL.replace("hours = 8", "hours = 3"), "caps.L"),
        ("caps = 1\n", "caps"),
        ("[caps]\nM = 5\nS = { tokens = 1, hours = 1 }\nL = { tokens = 1, hours = 1 }\n", "caps.M"),
    ],
)
def test_a_malformed_caps_table_is_refused_naming_the_setting(tmp_path, text, setting):
    """REQ-056 AC1: rule 2, a missing size or key, an unknown key, a string, 0, a negative, a
    fraction, a bool and a size above a larger one are refused naming caps.<key>, never a value."""
    with pytest.raises(config.CapsSettingError) as raised:
        config.caps_settings(root_with(tmp_path, text))
    message = str(raised.value)
    assert message.endswith(f"(setting: {setting})")
    assert str(ODD) not in message


# --- rule 3: which cap a build has --------------------------------------------------------------


def test_the_cap_is_the_size_of_the_brief():
    """REQ-056 AC3: rule 3, the brief's Size: line chooses the cap."""
    assert caps.cap_of(TABLE, brief_body("S")) == ("S", {"tokens": 1, "hours": 1})
    assert caps.cap_of(TABLE, brief_body("M")) == ("M", {"tokens": 2, "hours": 2})


@pytest.mark.parametrize(
    "body", [brief_body(None), brief_body("M") + "Size: S\n", "Size: XL", None]
)
def test_a_brief_whose_size_cannot_be_read_gets_the_l_cap(body):
    """REQ-056 AC3: rule 3, a missing, repeated or unreadable Size gives L, `size unknown`."""
    assert caps.cap_of(TABLE, body) == (None, {"tokens": 3, "hours": 3})


# --- rule 5: the tokens used --------------------------------------------------------------------


def test_the_tokens_are_the_sum_of_the_reports():
    """REQ-056 AC3: rule 5, the sum of `metrics.usage_of` over the author's reports."""
    comments = [
        comment(1, "builder", f"Report: {SHA[:7]} ready for review\n\nUsage: 1200 tokens"),
        comment(2, "builder", "Report: abc1234 fix list applied; Usage: 1200 tokens"),
        comment(3, "builder", "Report: abc1234 merge of main; Usage: 300 tokens"),
        comment(4, "other", "Report: abc1234 merge of main; Usage: 9999 tokens"),
    ]
    assert caps.tokens_used(comments, "builder") == 1500


def test_a_progress_figure_edited_after_the_newest_report_is_added():
    """REQ-056 AC3: rule 5, the progress line's figure counts when edited after the newest
    Report:, and not when the newest Report: came after it."""
    report = comment(1, "builder", "Report: abc1234 merge of main; Usage: 300 tokens", at(2))
    line = "Progress: abc1234 done 2/4; next: 3; Usage: 700 tokens"
    progress = comment(2, "builder", line, at(1))
    progress["updated_at"] = at(3)
    assert caps.tokens_used([report, progress], "builder") == 1000
    progress["updated_at"] = at(1.5)
    assert caps.tokens_used([report, progress], "builder") == 300
    assert caps.tokens_used([progress], "builder") == 700


@pytest.mark.parametrize(
    "bodies",
    [
        [],
        ["Report: abc1234 ready for review; Usage: not shown"],
        ["Progress: abc1234 done 1/4; next: 2; Usage: not shown", "Report: abc1234 merge of main"],
    ],
)
def test_no_figure_is_unknown_never_zero(bodies):
    """REQ-056 AC3: rule 5, no figure at all is `unknown`, never 0."""
    comments = [comment(i, "builder", b, at(i)) for i, b in enumerate(bodies, 1)]
    assert caps.tokens_used(comments, "builder") == "unknown"
    assert caps.tokens_used(None, "builder") == "unknown"


# --- rule 6: the hours used ---------------------------------------------------------------------


def hours(brief: list, pull: list, now: datetime = NOW, created: str = at(1)):
    return caps.hours_used(brief, pull, "builder", {"boss"}, created, now)


def test_hours_run_from_the_take_to_the_first_ready_report():
    """REQ-056 AC3: rule 6, the turn from `taken:` to the first `ready for review` report;
    the wait for a verdict after it is not counted."""
    brief = [comment(1, "builder", "taken: b9 2026-11-07", at(0))]
    pull = [comment(2, "builder", "Report: abc1234 ready for review; Usage: 10 tokens", at(3.25))]
    assert hours(brief, pull) == Decimal("3.3")


def test_hours_count_each_fix_list_to_the_next_report_and_the_open_turn():
    """REQ-056 AC3: rule 6, from each fix list or correction by a listed verdict author to the
    author's next Report:, and the last open interval to the time of the sweep."""
    brief = [comment(1, "builder", "taken: b9 2026-11-07", at(0))]
    pull = [
        comment(2, "builder", "Report: abc1234 ready for review", at(2)),
        comment(3, "boss", "Verdict: fix list abc1234\n\n1. A finding.", at(5)),
        comment(4, "builder", "Report: def5678 fix list applied", at(6)),
        comment(5, "boss", "Correction: the finding stands.", at(10)),
    ]
    assert hours(brief, pull) == Decimal("5.0")  # 2 + 1 + (12 - 10)


def test_a_question_waits_on_the_conductor_and_is_not_counted():
    """REQ-056 AC3: rule 6, from the author's Question: to the next comment by a listed verdict
    author is the conductor's time."""
    brief = [comment(1, "builder", "taken: b9 2026-11-07", at(0))]
    pull = [
        comment(2, "builder", "Question: Q-9-1 which file?", at(1)),
        comment(3, "boss", "Answer: the first one.", at(4)),
        comment(4, "builder", "Report: abc1234 ready for review", at(5)),
    ]
    assert hours(brief, pull) == Decimal("2.0")


def test_a_verdict_wait_and_another_account_do_not_count():
    """REQ-056 AC3: rule 6, a fix list by an account not listed opens no interval."""
    brief = [comment(1, "builder", "taken: b9 2026-11-07", at(0))]
    pull = [
        comment(2, "builder", "Report: abc1234 ready for review", at(1)),
        comment(3, "stranger", "Verdict: fix list abc1234", at(2)),
    ]
    assert hours(brief, pull) == Decimal("1.0")


def test_hours_start_at_the_newest_take_before_the_pull_request():
    """REQ-056 AC3: rules 3 and 6, a later build's take is the newest one by the author at or
    before the pull request was opened."""
    brief = [
        comment(1, "builder", "taken: b9 2026-11-06", at(-20)),
        comment(2, "builder", "taken: b9 2026-11-07 build (c)", at(0)),
        comment(3, "builder", "taken: b9 2026-11-07 build (d)", at(9)),
    ]
    pull = [comment(4, "builder", "Report: abc1234 ready for review", at(1.5))]
    assert hours(brief, pull) == Decimal("1.5")


def test_no_readable_take_gives_unknown_hours():
    """REQ-056 AC3: rule 6, Q-S0049-7, an unreadable take gives `unknown`, never over."""
    pull = [comment(4, "builder", "Report: abc1234 ready for review", at(1.5))]
    assert hours([], pull) == "unknown"
    assert hours(None, pull) == "unknown"
    assert hours([comment(1, "other", "taken: b9 2026-11-07", at(0))], pull) == "unknown"
    assert hours([comment(1, "builder", "taken: b9 2026-11-07", at(0))], None) == "unknown"


# --- rule 7: the sweep's OVER and UNKNOWN lines -------------------------------------------------


def open_build(stub, body: str, pull_comments: list, brief: list, size: str | None = "M"):
    item = pr(7, body=body)
    serve_pr(stub, item, pull_comments)
    stub.serve(f"repos/{REPO}/issues/9", {"number": 9, "body": brief_body(size)})
    stub.serve(f"repos/{REPO}/issues/9/comments", brief)


def take_hours_ago(h: float) -> dict:
    return comment(1, "builder", "taken: b9 2026-11-07", ago(int(h * 60)))


def test_sweep_without_caps_prints_no_over_line_and_reads_no_brief(proj, stub):
    """REQ-056 AC1: rule 2, a project with no table sees the sweep it saw before."""
    open_build(stub, "Brief: #9\n", [], [take_hours_ago(9)])
    lines = sweep(proj, stub)
    assert not [x for x in lines if x.startswith(("OVER", "UNKNOWN"))]
    assert not [c for c in stub.calls() if c[1].endswith("issues/9")]


def test_sweep_marks_a_build_past_its_token_cap(proj, stub):
    """REQ-056 AC3: rule 7, one OVER line with the unit and the pull request, after the pull
    request lines and before the default branch line."""
    proj.write("agk.toml", FULL)
    report = comment(2, "builder", "Report: abc1234 ready for review; Usage: 6200 tokens", ago(10))
    open_build(stub, "Brief: #9\n", [report], [take_hours_ago(2)])
    lines = sweep(proj, stub)
    assert lines[1] == "OVER #9 6200/5000 tokens #7"
    assert lines[2].startswith("main: ")
    assert not [x for x in lines if "hours" in x]


def test_sweep_marks_a_build_past_its_hours_cap(proj, stub):
    """REQ-056 AC3: rule 7, the hours cap, with the hours given to one decimal."""
    proj.write("agk.toml", FULL)
    line = "Progress: abc1234 done 1/4; next: 2; Usage: 10 tokens"
    progress = comment(2, "builder", line, ago(5))
    open_build(stub, "Brief: #9\n", [progress], [take_hours_ago(5)])
    lines = sweep(proj, stub)
    assert lines[1] == "OVER #9 5.0/4 hours #7"
    assert not [x for x in lines if x.startswith("UNKNOWN")]


def test_sweep_a_build_under_its_caps_has_no_line(proj, stub):
    """REQ-056 AC3: rule 7, a build within both caps is not marked."""
    proj.write("agk.toml", FULL)
    report = comment(2, "builder", "Report: abc1234 ready for review; Usage: 4000 tokens", ago(10))
    open_build(stub, "Brief: #9\n", [report], [take_hours_ago(2)])
    assert not [x for x in sweep(proj, stub) if x.startswith(("OVER", "UNKNOWN"))]


def test_sweep_a_build_with_no_token_figure_prints_unknown_and_no_over(proj, stub):
    """REQ-056 AC3: rules 5 and 7, no figure is UNKNOWN, never 0 and never OVER."""
    proj.write("agk.toml", FULL)
    report = comment(2, "builder", "Report: abc1234 ready for review; Usage: not shown", ago(10))
    open_build(stub, "Brief: #9\n", [report], [take_hours_ago(2)])
    lines = sweep(proj, stub)
    assert lines[1] == "UNKNOWN #9 tokens #7"
    assert not [x for x in lines if x.startswith("OVER")]


def test_sweep_a_brief_with_no_size_is_read_at_the_l_cap(proj, stub):
    """REQ-056 AC3: rule 3, Q-S0049-4, the L cap and `size unknown` on the line."""
    proj.write("agk.toml", FULL)
    report = comment(2, "builder", "Report: abc1234 ready for review; Usage: 9500 tokens", ago(10))
    open_build(stub, "Brief: #9\n", [report], [take_hours_ago(2)], size=None)
    assert sweep(proj, stub)[1] == "OVER #9 9500/9000 tokens #7 size unknown"


def test_sweep_an_unreadable_brief_is_read_at_the_l_cap_with_unknown_hours(proj, stub):
    """REQ-056 AC3: rules 3 and 6, an unreadable brief gives the L cap and no hours line."""
    proj.write("agk.toml", FULL)
    report = comment(2, "builder", "Report: abc1234 ready for review; Usage: 6200 tokens", ago(10))
    serve_pr(stub, pr(7), [report])
    stub.serve(f"repos/{REPO}/issues/9", "FAIL")
    stub.serve(f"repos/{REPO}/issues/9/comments", "FAIL")
    lines = sweep(proj, stub)
    assert not [x for x in lines if x.startswith("OVER")]


def test_sweep_a_pull_request_with_no_brief_line_is_never_capped(proj, stub):
    """REQ-056 AC3: rule 15, only a builder pull request with `Brief: #n` has a cap."""
    proj.write("agk.toml", FULL)
    report = comment(2, "builder", "Report: abc1234 ready for review; Usage: 99999 tokens", ago(10))
    open_build(stub, "A person's change.\n", [report], [take_hours_ago(9)])
    assert not [x for x in sweep(proj, stub) if x.startswith(("OVER", "UNKNOWN"))]


def files(root) -> list:
    """Every file of the project, with its text, the stub's own folders and git left out."""
    skip = {".git", "stub", "bin"}
    found = [p for p in root.rglob("*") if not skip & set(p.relative_to(root).parts)]
    found = [p for p in found if p.is_file()]
    return sorted((str(p.relative_to(root)), p.read_bytes()) for p in found)


def test_sweep_with_caps_makes_get_calls_only_and_writes_no_file(proj, stub):
    """REQ-056 AC3: rule 7, Q-S0049-8, GET only (checked by `sweep`) and no file written."""
    proj.write("agk.toml", FULL)
    report = comment(2, "builder", "Report: abc1234 ready for review; Usage: 6200 tokens", ago(10))
    open_build(stub, "Brief: #9\n", [report], [take_hours_ago(9)])
    before = files(proj.root)
    lines = sweep(proj, stub)
    assert files(proj.root) == before
    assert lines[1:3] == ["OVER #9 6200/5000 tokens #7", "OVER #9 8.8/4 hours #7"]


def test_sweep_a_malformed_caps_table_is_refused_naming_the_setting(proj, stub):
    """REQ-056 AC1: rule 2, the sweep stops on a malformed table, naming the setting."""
    proj.write("agk.toml", FULL.replace("hours = 2", f"hours = {ODD}"))
    open_build(stub, "Brief: #9\n", [], [take_hours_ago(2)])
    out = run(proj, stub, "sweep")
    assert out.returncode != 0
    assert "setting: caps.M" in out.stdout + out.stderr
    assert str(ODD) not in out.stdout + out.stderr
