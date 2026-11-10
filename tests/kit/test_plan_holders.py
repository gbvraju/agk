"""`session.py plan` ranks the open pull requests by the briefs they hold (amendment 141 item 4).

REQ-057 AC10. `Holds <k>:` lines, highest first, and a `Stall:` line for a holder of two or more
idle over `[flow] stall_minutes`; the plan posts nothing, the conductor posts the stall. A `gh` stub
serves saved JSON; invented briefs only; no network."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from test_conductor_guard import project, run_hook  # noqa: F401 - the fixture
from test_session import ISSUES, REPO, Stub, comment, iso, issue, listing, posts
from test_session_flow import DAY, PULLS, brief, flow, pr
from test_session_plan import changed, data, free, labelled, plan

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    repo.write("config/protected-paths.txt", "config/\nscripts/agk/\n")
    return repo


def idle(item: dict, minutes: int) -> dict:
    return {**item, "updated_at": iso(-timedelta(minutes=minutes, seconds=10))}


def scene(stub: Stub, pulls: list[dict], files: dict[int, str], briefs: dict[int, str]) -> None:
    """Open pull requests, the one file each changes, and free briefs with their `Touches:`."""
    stub.serve(PULLS, pulls)
    for number, path in files.items():
        changed(stub, number, ("modified", path))
    listing(stub, [issue(n, brief(t)) for n, t in briefs.items()])
    free(stub, *briefs)


def holds(out: str) -> list[str]:
    return [x for x in out.splitlines() if x.startswith(("Holds ", "Stall:"))]


def test_ac10_the_holders_are_ranked_highest_first(proj, stub):
    """REQ-057 AC10: item 4, the exact line, `k` first, in the words and the data."""
    scene(
        stub,
        [idle(pr(20, 90), 5), idle(pr(30, 91), 7)],
        {20: "a.py", 30: "b.py"},
        {5: "a.py", 6: "b.py", 7: "b.py"},
    )
    assert holds(plan(proj, stub).stdout) == [
        "Holds 2: #30 (open, idle 7 min) for #6, #7",
        "Holds 1: #20 (open, idle 5 min) for #5",
    ]
    assert data(proj, stub)["holders"][0] == {
        "pr": 30,
        "state": "open",
        "idle": 7,
        "head": pr(30)["head"]["sha"],
        "briefs": [6, 7],
    }


def test_ac10_a_tie_goes_to_the_lowest_pull_request(proj, stub):
    """REQ-057 AC10: item 4, then the lowest number."""
    scene(
        stub, [idle(pr(30, 91), 1), idle(pr(20, 90), 1)], {20: "a.py", 30: "b.py"},
        {5: "a.py", 6: "b.py"},
    )  # fmt: skip
    assert [h["pr"] for h in data(proj, stub)["holders"]] == [20, 30]


def test_ac10_a_brief_held_by_two_pull_requests_counts_under_each(proj, stub):
    """REQ-057 AC10: `Q-772-6`, merging one does not free it."""
    scene(
        stub, [idle(pr(20, 90), 1), idle(pr(30, 91), 1)], {20: "a.py", 30: "b.py"},
        {5: "a.py, b.py"},
    )  # fmt: skip
    assert [(h["pr"], h["briefs"]) for h in data(proj, stub)["holders"]] == [(20, [5]), (30, [5])]


@pytest.mark.parametrize(
    ("item", "state"),
    [
        (labelled(20, 90, "agk:blocked", "other"), "blocked"),
        ({**pr(20, 90), "draft": True, "labels": [{"name": "agk:review"}]}, "review"),
        ({**pr(20, 90), "draft": True}, "draft"),
        (pr(20, 90), "open"),
    ],
)
def test_ac10_the_state_is_the_label_or_draft_or_open(proj, stub, item, state):
    """REQ-057 AC10: item 4, the `agk:` label without its prefix, or `draft`, or `open`."""
    scene(stub, [idle(item, 3)], {20: "a.py"}, {5: "a.py"})
    assert data(proj, stub)["holders"][0]["state"] == state


def test_ac10_a_pull_request_does_not_hold_its_own_brief(proj, stub):
    """REQ-057 AC10: item 4, as `running_conflict` skips it."""
    scene(stub, [idle(pr(20, 5), 3)], {20: "a.py"}, {5: "a.py"})
    assert data(proj, stub)["holders"] == []


def test_ac10_nothing_held_prints_no_line(proj, stub):
    """REQ-057 AC10: item 4, a pull request that holds nothing is not ranked."""
    scene(stub, [idle(pr(20, 90), 300)], {20: "a.py"}, {5: "b.py"})
    assert holds(plan(proj, stub).stdout) == []


def test_ac10_a_taken_brief_is_not_a_holder(proj, stub):
    """REQ-057 AC10: ADR-0358's residual: only pull requests are ranked."""
    listing(stub, [issue(4, brief("a.py")), issue(5, brief("a.py"))])
    stub.serve(f"{ISSUES}/4/comments", [comment(1, "x", f"taken: s-other {DAY}")])
    free(stub, 5)
    got = data(proj, stub)
    assert got["waits"] == [{"brief": 5, "waits_for": 4, "why": "both touch a.py"}]
    assert got["holders"] == []


def stalled(proj, stub, minutes: int, *briefs: int) -> list[str]:
    scene(stub, [idle(pr(20, 90), minutes)], {20: "a.py"}, {b: "a.py" for b in briefs})
    return holds(plan(proj, stub).stdout)


def test_ac10_a_holder_of_two_idle_over_the_limit_is_a_stall(proj, stub):
    """REQ-057 AC10: item 4, `Q-772-7`, the default is 30 minutes and the plan posts nothing."""
    assert stalled(proj, stub, 31, 5, 6)[1:] == ["Stall: #20 holds 2, idle 31 min"]
    assert data(proj, stub)["holders"][0]["stall"] == "Stall: #20 holds 2, idle 31 min"
    assert posts(stub) == []


def test_ac10_no_stall_at_the_limit_or_for_one_brief(proj, stub):
    """REQ-057 AC10: item 4, over the limit, and `k` of 2 or more."""
    assert len(stalled(proj, stub, 30, 5, 6)) == 1
    assert len(stalled(proj, stub, 300, 5)) == 1
    assert "stall" not in data(proj, stub)["holders"][0]


def test_ac10_stall_minutes_is_a_setting(proj, stub):
    """REQ-057 AC10: item 4, the key of the `[flow]` table."""
    flow(proj, "stall_minutes = 5")
    assert stalled(proj, stub, 6, 5, 6)[1:] == ["Stall: #20 holds 2, idle 6 min"]


@pytest.mark.parametrize("value", ["0", '"zq-value"', "true"])
def test_ac10_a_wrong_stall_minutes_is_refused_naming_the_setting(proj, stub, value):
    """REQ-057 AC10: item 11, a wrong value is refused by its name, never its value."""
    flow(proj, f"stall_minutes = {value}")
    listing(stub, [])
    out = plan(proj, stub)
    assert out.returncode != 0 and "stall_minutes" in out.stdout + out.stderr
    assert "zq-value" not in out.stdout + out.stderr


def test_ac10_prose_makes_no_holder(proj, stub):
    """REQ-057 AC9 and AC10: items 3 and 4, a shared prose file holds nothing to rank."""
    scene(stub, [idle(pr(20, 90), 3)], {20: "docs/guides/a.md"}, {5: "docs/guides/a.md"})
    assert data(proj, stub)["holders"] == []


def test_ac10_the_guard_lets_the_conductor_post_the_stall(project):  # noqa: F811
    """REQ-057 AC10: `Q-772-8`, the one comment POST takes a `Stall:` body."""
    line = "gh api --method POST repos/o/r/issues/7/comments -f 'body=Stall: holds 2, idle 31 min'"
    out = run_hook({"tool_name": "Bash", "tool_input": {"command": line}}, project)
    assert out.returncode == 0 and out.stdout.strip() == ""


def test_ac10_the_conductor_works_in_the_order_of_the_holders():
    """REQ-057 AC10: item 4, the work list reads `holders` and posts each `stall` once."""
    text = (ROOT / ".claude/agents/conductor.md").read_text(encoding="utf-8")
    assert "`holders`" in text and "`stall`" in text and "plan issue" in text


# --- one red head gets one fix (brief #962) -----------------------------------------------------

RED = "The default branch is red"  # session.RED_TITLE
ROUTER = {"login": "github-actions[bot]"}  # session.ROUTER_LOGIN
SLOTS = '[flow]\nbuilder_start = "assign"\nbuilder_slots = 2\n'


def alarm(number: int = 953) -> dict:
    """The router's red-branch alarm (`route.write_red`), invented."""
    body = "Sentence: the default branch is red at an example head.\nAdvances: none\nPriority: 0\n"
    return {**issue(number, body), "title": RED, "user": ROUTER}


def fixing(number: int, line: str) -> dict:
    """An open brief whose body carries LINE, which may name the alarm."""
    return {**issue(number, brief("src/fix.py") + line + "\n"), "user": {"login": "boss"}}


def red_scene(stub: Stub, briefs: list[dict], pulls: list[dict], said: list[dict] = ()) -> None:
    stub.serve(PULLS, pulls)
    listing(stub, [alarm(), *briefs])
    free(stub, *(b["number"] for b in briefs))
    stub.serve(f"{ISSUES}/953/comments", list(said))


def pull(number: int, body: str, state: str = "open") -> dict:
    return {**pr(number, None, state), "body": body}


def assigned(found: dict) -> list[int]:
    return [row["brief"] for row in found.get("assign", [])]


def test_962_a_red_alarm_with_an_open_fix_brief_is_not_assigned(proj, stub):
    """REQ-039 REQ-041: brief #962 answers 1 and 3 (a), the case of 10 Nov (#953, #955)."""
    proj.write("agk.toml", SLOTS)
    red_scene(stub, [fixing(955, "Red: #953")], [])
    found = data(proj, stub)
    assert 953 not in assigned(found)
    assert {"brief": 953, "fixed_by": 955, "why": "is fixed by #955"} in found["waits"]
    out = plan(proj, stub).stdout
    assert "#953 is fixed by #955." in out and "s1 #953" not in out and "s2 #953" not in out
    assert posts(stub) == []


def test_962_a_red_alarm_alone_is_still_assigned(proj, stub):
    """REQ-039 REQ-041: brief #962 answers 2 and 3 (b), SPEC-0032 rule 9 kept."""
    proj.write("agk.toml", SLOTS)
    red_scene(stub, [], [])
    found = data(proj, stub)
    assert assigned(found) == [953]
    assert not any(w.get("brief") == 953 for w in found["waits"])


def test_962_an_open_fix_pull_request_that_names_it_stops_the_assignment(proj, stub):
    """REQ-039 REQ-041: brief #962 answers 1 and 3 (c)."""
    proj.write("agk.toml", SLOTS)
    red_scene(stub, [], [pull(956, "Fixes #953\nAdvances: REQ-039\n")])
    found = data(proj, stub)
    assert assigned(found) == []
    assert {"brief": 953, "fixed_by": 956, "why": "is fixed by #956"} in found["waits"]


@pytest.mark.parametrize(
    "line",
    ["Fixes #953", "Closes #953", "closes: #953", "Red: #953", "Plan: #953",
     "This is the fix brief for issue #953."],
)  # fmt: skip
def test_962_each_naming_line_names_the_alarm(proj, stub, line):
    """REQ-039 REQ-041: brief #962 answer 1, the lines that name `#<red>`."""
    proj.write("agk.toml", SLOTS)
    red_scene(stub, [fixing(955, line)], [])
    assert assigned(data(proj, stub)) == []


@pytest.mark.parametrize(
    "line", ["Fixes #9531", "Brief: #953", "Sentence: see #953", "Red: #95"]
)
def test_962_a_line_that_does_not_name_the_alarm_leaves_it_assigned(proj, stub, line):
    """REQ-039 REQ-041: brief #962 answer 2, only the named lines and the whole number count."""
    proj.write("agk.toml", SLOTS)
    red_scene(stub, [fixing(955, line)], [pull(956, line + "\n")])
    assert 953 in assigned(data(proj, stub))


def test_962_a_closed_pull_request_fixes_nothing(proj, stub):
    """REQ-039 REQ-041: brief #962 answer 1, an open pull request only."""
    proj.write("agk.toml", SLOTS)
    red_scene(stub, [], [pull(956, "Fixes #953\n", state="closed")])
    assert assigned(data(proj, stub)) == [953]


def test_962_a_listed_author_naming_an_open_brief_on_the_alarm_stops_it(proj, stub):
    """REQ-039 REQ-041: brief #962 answer 1, `fix brief filed: #n` by a listed author."""
    proj.write("agk.toml", SLOTS)
    red_scene(stub, [fixing(955, "")], [], [comment(1, "boss", "Fix brief filed: #955.")])
    found = data(proj, stub)
    assert assigned(found) == []
    assert {"brief": 953, "fixed_by": 955, "why": "is fixed by #955"} in found["waits"]


@pytest.mark.parametrize(
    ("login", "named"), [("someone", 955), ("boss", 957)]
)  # fmt: skip
def test_962_an_unlisted_author_or_a_brief_not_open_does_not_stop_it(proj, stub, login, named):
    """REQ-039 REQ-041: brief #962 answer 1, a listed author and an open brief only."""
    proj.write("agk.toml", SLOTS)
    said = [comment(1, login, f"fix brief filed: #{named}")]
    red_scene(stub, [fixing(955, "")], [], said)
    assert assigned(data(proj, stub)) == [953]
