"""The builder's side of a cap (SPEC-0049 build (c), rules 4 and 8 to 10; brief #726; ADR-0324).

REQ-056 AC2: session rule 8's progress line ends with the usage, which `resume` reads past and
`metrics.usage_of` never reads as 0. REQ-056 AC4: session rule 32 lets a builder act on a
`Tell: <id> stop: over cap ...` by a listed verdict author, `watch --session` ends on it, and a
pull request whose newest author `Report:` is an `over cap` report is parked: `session.py next`
does not offer it as stalled until a raised `Size:` puts it under the new cap. A `gh` stub on
`PATH`, saved responses, invented data, no network.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from metrics import usage_of
from test_session import ISSUES, PR, PR_COMMENTS, comment, listing, posts, pull, session, watching
from test_session import proj as session_proj  # noqa: F401  (the fixtures of test_session)
from test_session import stub as session_stub  # noqa: F401
from test_session_resume import OLD, PRS, label, nxt, offered, pr_object, serve_list, serve_resume
from test_session_tell import COMMENTS, CONDUCTOR, CONDUCTOR_ISSUE, told

ROOT = Path(__file__).resolve().parents[2]
RULES = (ROOT / "config" / "session-rules.md").read_text(encoding="utf-8")
SCRIPTS = ROOT / "scripts" / "agk"
CAPS = (
    "[caps]\n"
    "S = { tokens = 1000, hours = 2 }\n"
    "M = { tokens = 5000, hours = 4 }\n"
    "L = { tokens = 9000, hours = 8 }\n"
)
BRIEF = f"{ISSUES}/5"


@pytest.fixture
def stub(request):
    return request.getfixturevalue("session_stub")


@pytest.fixture
def proj(request):
    return request.getfixturevalue("session_proj")


def rule(number: int) -> str:
    found = re.search(rf"^{number}\. (.*)$", RULES, re.MULTILINE)
    assert found, number
    return found.group(1)


# --- rule 4: the usage at each milestone (AC2) --------------------------------------------------


def test_ac2_session_rule_8_ends_the_progress_line_with_the_usage():
    """REQ-056 AC2"""
    text = rule(8)
    assert "; Usage: <n> tokens" in text and "; Usage: not shown" in text


@pytest.mark.parametrize("tail", ["; Usage: 1200 tokens", "; Usage: not shown", ""])
def test_ac2_resume_reads_the_next_step_without_the_usage(proj, stub, tail):
    """REQ-056 AC2: the usage ending is not part of the next step."""
    progress = comment(3, "builder", f"Progress: abc1234 done 2/5; next: the report lines{tail}")
    serve_resume(stub, comments=[progress])
    out = session(proj, stub, "resume", "--pr", "7")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "progress: abc1234 done 2/5; next: the report lines\n" in out.stdout
    assert "continue from: the report lines\n" in out.stdout


def test_ac2_a_progress_or_report_without_a_figure_is_not_reported_never_0():
    """REQ-056 AC2: `metrics.usage_of` reads only report figures, as before."""
    saved = [
        comment(1, "builder", "Progress: abc1234 done 1/3; next: x; Usage: 1200 tokens"),
        comment(2, "builder", "Report: abc1234 tests red; Usage: not shown"),
        comment(3, "builder", "Report: abc1234 tests green"),
    ]
    assert usage_of(saved, "builder") == "not-reported"
    figure = comment(4, "builder", "Report: def5678 ready for review; Usage: 1200 tokens")
    assert usage_of([*saved, figure], "builder") == 1200


# --- rules 8 and 9: the stop (AC4) --------------------------------------------------------------


def test_ac4_session_rule_32_lets_a_builder_act_on_the_stop_line():
    """REQ-056 AC4"""
    text = rule(32)
    assert "`Tell: <id> stop: over cap <used>/<cap> <unit>`" in text
    for step in (
        "`checkpoint:`",
        "`session.py push-check`",
        "`prepush.py`",
        "`Report: <head> over cap <used>/<cap> <unit>; Usage: <n> tokens`",
        "`released:`",
        "`watch`",
        "force-pushes",
    ):
        assert step in text, step


def test_ac4_watch_ends_on_a_stop_line_by_a_listed_verdict_author(proj, stub):
    """REQ-056 AC4"""
    stub.serve(CONDUCTOR, [CONDUCTOR_ISSUE])
    stop = told(9, "Tell: s-me stop: over cap 5200/5000 tokens")
    stub.serve(COMMENTS, [], nth=1)
    stub.serve(COMMENTS, [stop])
    watching(stub, [(pull(), [])] * 2)
    args = ("watch", "--pr", "7", "--session", "s-me", "--interval", "0", "--timeout", "5")
    out = session(proj, stub, *args)
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.strip() == "tell stop: over cap 5200/5000 tokens"
    assert stub.calls() and all(call[0] == "GET" for call in stub.calls())


def test_ac4_the_same_stop_line_by_another_account_does_not_count(proj, stub):
    """REQ-056 AC4"""
    stub.serve(CONDUCTOR, [CONDUCTOR_ISSUE])
    stub.serve(COMMENTS, [], nth=1)
    stub.serve(COMMENTS, [told(9, "Tell: s-me stop: over cap 5200/5000 tokens", "stranger")])
    stub.serve(PR, pull())
    stub.serve(PR_COMMENTS, [])
    args = ("watch", "--pr", "7", "--session", "s-me", "--interval", "0", "--timeout", "1")
    out = session(proj, stub, *args)
    assert out.returncode == 3 and out.stdout.strip() == "timeout"


def test_ac4_no_kit_command_closes_a_pull_request_deletes_a_branch_or_releases_on_a_stop():
    """REQ-056 AC4: the work is kept."""
    for path in sorted(SCRIPTS.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "over cap" not in text or "released:" not in text.split("over cap", 1)[1][:400]
        assert not re.search(r"git/refs/heads[^\n]*DELETE|DELETE[^\n]*git/refs/heads", text), path
        assert not re.search(r"push[^\n]*--delete", text), path


# --- rule 10: parked until a person rules (AC4) -------------------------------------------------


def over(cid: int = 8, line: str = "over cap 5200/5000 tokens", who: str = "builder") -> dict:
    return comment(cid, who, f"Report: abc1234 {line}; Usage: 300 tokens", "2026-11-07T10:00:00Z")


def serve_parked(proj, stub, comments, size="M", table=True):
    if table:
        proj.write("agk.toml", CAPS)
    pr = pr_object(7, draft=True, body="Advances: REQ-056\nBrief: #5\n")
    serve_list(stub, [(pr, comments, OLD)])
    stub.serve(BRIEF, {"number": 5, "body": f"Sentence: x\nSize: {size}\n", "labels": label()})
    stub.serve(f"{BRIEF}/comments", [])
    listing(stub, [])


def test_ac4_a_pull_request_parked_by_an_over_cap_report_is_not_offered(proj, stub):
    """REQ-056 AC4"""
    serve_parked(proj, stub, [over()])
    out = nxt(proj, stub)
    assert not offered(out), out.stdout
    assert posts(stub) == []


def test_ac4_a_parked_pull_request_is_not_offered_without_the_take_either(proj, stub):
    """REQ-056 AC4"""
    serve_parked(proj, stub, [over()])
    out = session(proj, stub, "next", "--session", "s-me")
    assert "stalled #7" not in out.stdout and posts(stub) == []


def test_ac4_a_parked_pull_request_stays_parked_without_a_caps_table(proj, stub):
    """REQ-056 AC4: no cap can be read, so no ruling can be seen."""
    serve_parked(proj, stub, [over()], size="L", table=False)
    assert not offered(nxt(proj, stub))


def test_ac4_a_raised_size_that_is_still_under_the_used_figure_keeps_it_parked(proj, stub):
    """REQ-056 AC4"""
    serve_parked(proj, stub, [over(line="over cap 9500/5000 tokens")], size="L")
    assert not offered(nxt(proj, stub))


@pytest.mark.parametrize(
    "line", ["over cap 5200/5000 tokens", "over cap 4.5/4 hours", "over cap 8.0/4 hours"]
)
def test_ac4_a_raised_size_under_which_the_build_is_no_longer_over_offers_it_again(
    proj, stub, line
):
    """REQ-056 AC4"""
    serve_parked(proj, stub, [over(line=line)], size="L")
    out = nxt(proj, stub)
    assert out.stdout.startswith("stalled #7\n"), out.stdout + out.stderr


def test_ac4_a_later_report_by_the_author_ends_the_park(proj, stub):
    """REQ-056 AC4: only the newest author report parks."""
    later = comment(9, "builder", "Report: def5678 fix list applied", "2026-11-07T11:00:00Z")
    serve_parked(proj, stub, [over(), later])
    assert offered(nxt(proj, stub))


def test_ac4_an_over_cap_report_by_another_account_parks_nothing(proj, stub):
    """REQ-056 AC4"""
    serve_parked(proj, stub, [over(who="stranger")])
    assert offered(nxt(proj, stub))


def test_ac4_an_unreadable_brief_keeps_it_parked(proj, stub):
    """REQ-056 AC4"""
    serve_parked(proj, stub, [over()], size="L")
    stub.serve(BRIEF, "FAIL")
    assert not offered(nxt(proj, stub))


def test_ac4_the_parked_check_reads_only(proj, stub):
    """REQ-056 AC4 and rule 16: GET only."""
    serve_parked(proj, stub, [over()])
    nxt(proj, stub)
    assert all(call[0] == "GET" for call in stub.calls())
    assert not any(call[1] == f"{PRS}/7" and call[0] != "GET" for call in stub.calls())
