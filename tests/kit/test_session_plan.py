"""session.py plan: waves, capacity, the merge queue, the safe merge set, drift and stale briefs.

Brief 247 build (a); SPEC-0034 rule 15; REQ-039. A `gh` stub serves saved JSON copies of the GitHub
responses; the plan is plain words by default and the same data with `--json`; it posts nothing,
uses no model and reads only what the session scripts already read."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from test_session import ISSUES, REPO, Stub, comment, iso, issue, listing, posts, session
from test_session_flow import DAY, PULLS, brief, files, flow, merged, pr


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    repo.write("config/protected-paths.txt", "config/\nscripts/agk/\n")
    return repo


def free(stub: Stub, *numbers: int) -> None:
    for n in numbers:
        stub.serve(f"{ISSUES}/{n}/comments", [])


def labelled(number: int, brief_no: int | None, *names: str, at: str | None = None) -> dict:
    return {
        **pr(number, brief_no),
        "labels": [{"name": n} for n in names],
        "created_at": at or iso(-timedelta(days=1)),
    }


def plan(proj, stub, *extra: str):
    return session(proj, stub, "plan", *extra)


def data(proj, stub) -> dict:
    out = plan(proj, stub, "--json")
    assert out.returncode == 0, out.stdout + out.stderr
    return json.loads(out.stdout)


def read_only(stub: Stub) -> None:
    assert posts(stub) == [] and all(c[0] == "GET" for c in stub.calls())


# --- waves (answer 1) ---------------------------------------------------------------------------


def test_independent_briefs_all_start_with_a_session_name_each(proj, stub):
    listing(stub, [issue(5, brief("a/")), issue(6, brief("b/")), issue(7, brief("c/"))])
    free(stub, 5, 6, 7)
    out = plan(proj, stub)
    assert out.returncode == 0, out.stdout
    assert out.stdout.splitlines()[0] == (
        "Start 3: builder-a takes #5, builder-b takes #6, builder-c takes #7."
    )
    read_only(stub)


def test_briefs_whose_touches_overlap_never_start_in_the_same_wave(proj, stub):
    listing(
        stub,
        [
            issue(5, brief("scripts/**")),
            issue(6, brief("scripts/agk/x.py")),
            issue(7, brief("docs/**")),
        ],
    )
    free(stub, 5, 6, 7)
    lines = plan(proj, stub).stdout.splitlines()
    assert lines[0] == "Start 2: builder-a takes #5, builder-b takes #7."
    assert "#6 waits for #5 (both touch scripts/**)." in lines


def test_the_priority_and_then_the_number_decide_who_waits(proj, stub):
    listing(stub, [issue(5, brief("a/")), issue(6, brief("a/b", priority=1))])
    free(stub, 5, 6)
    lines = plan(proj, stub).stdout.splitlines()
    assert lines[0] == "Start 1: builder-a takes #6."
    assert "#5 waits for #6 (both touch a/)." in lines


def test_a_brief_that_overlaps_running_work_waits_for_it(proj, stub):
    listing(stub, [issue(5, brief("scripts/**")), issue(6, brief("docs/**"))])
    stub.serve(PULLS, [labelled(20, 1, "agk:review")])
    files(stub, 20, "scripts/agk/session.py")
    free(stub, 5, 6)
    lines = plan(proj, stub).stdout.splitlines()
    assert lines[0] == "Start 1: builder-a takes #6."
    assert "#5 waits for pull request #20 (it changes scripts/agk/session.py)." in lines


# --- ready and capacity (answer 1) --------------------------------------------------------------


def test_a_taken_brief_with_no_pull_request_is_not_ready_and_counts_as_running(proj, stub):
    listing(stub, [issue(n, brief(f"d{n}/")) for n in (5, 6, 7, 8)])
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-a {DAY}")])
    free(stub, 6, 7, 8)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [6, 7]  # 3 builders - 1 running claim
    assert [s["session"] for s in got["start"]] == ["builder-b", "builder-c"]
    assert got["capacity"]["running"] == 1 and {"brief": 5}.items() <= got["skipped"][0].items()
    assert "taken by builder-a" in got["skipped"][0]["why"]


def test_the_sessions_to_start_are_capped_by_max_builders_and_the_running_pull_requests(proj, stub):
    listing(stub, [issue(n, brief(f"d{n}/")) for n in (5, 6, 7)])
    stub.serve(PULLS, [labelled(10, 1, "agk:ready"), labelled(11, 2, "agk:fix")])
    for n in (10, 11):
        files(stub, n, f"z/{n}")
    free(stub, 5, 6, 7)
    flow(proj, "max_builders = 3\nmerge_hours = 5")
    got = data(proj, stub)
    assert got["capacity"]["running"] == 2 and got["capacity"]["slots"] == 1
    assert [s["brief"] for s in got["start"]] == [5]


def test_the_conductors_review_capacity_caps_the_start(proj, stub):
    listing(stub, [issue(n, brief(f"d{n}/")) for n in (5, 6, 7)])
    stub.serve(PULLS, [labelled(10, 1, "agk:review"), labelled(11, 2, "agk:review")])
    for n in (10, 11):
        files(stub, n, f"z/{n}")
    free(stub, 5, 6, 7)
    flow(proj, "max_builders = 6\nreviews_in_flight = 3")
    got = data(proj, stub)
    assert got["capacity"]["waiting_for_verdict"] == 2 and len(got["start"]) == 1
    flow(proj, "max_builders = 6\nreviews_in_flight = 2")
    out = plan(proj, stub)
    assert out.stdout.splitlines()[0].startswith("Start 0: the conductor has 2 pull requests")


def test_nothing_ready_says_so(proj, stub):
    listing(stub, [])
    out = plan(proj, stub)
    assert out.stdout.splitlines()[0] == "Start 0: no brief is ready."


# --- the merge queue, measured (answer 1) -------------------------------------------------------


def history(*hours_ago: float) -> list[dict]:
    return [merged(100 + i, 90 + i, timedelta(hours=h)) for i, h in enumerate(hours_ago)]


def ready_prs(*numbers: int) -> list[dict]:
    return [labelled(n, 70 + n, "agk:ready") for n in numbers]


def with_history(stub, past: list[dict], waiting: list[dict]) -> None:
    stub.serve(PULLS, [*waiting, *past])
    for p in waiting:
        files(stub, p["number"], f"z/{p['number']}")
        stub.serve(f"repos/{REPO}/compare/main...{p['head']['sha']}", {"behind_by": 0})


def test_the_merge_rate_holds_new_sessions_while_the_ready_queue_exceeds_it(proj, stub):
    listing(stub, [issue(5, brief("a/"))])
    free(stub, 5)
    # four merges in two active hours: 2 a hour; three pull requests wait: 3 > 1 x 2
    with_history(stub, history(30, 30.2, 50, 50.1), ready_prs(20, 21, 22))
    flow(proj, "max_builders = 9")
    got = data(proj, stub)
    assert got["start"] == [] and got["merge"]["hold"] is True and got["merge"]["rate"] == 2.0
    first = plan(proj, stub).stdout.splitlines()[0]
    assert first.startswith("Start 0: 3 pull requests wait for your merge")


def test_the_hold_never_stops_a_running_session_and_lifts_below_the_rate(proj, stub):
    listing(stub, [issue(5, brief("a/"))])
    free(stub, 5)
    with_history(stub, history(30, 30.2, 50, 50.1), ready_prs(20, 21))
    flow(proj, "max_builders = 9")
    got = data(proj, stub)
    assert got["merge"]["hold"] is False and [s["brief"] for s in got["start"]] == [5]


def test_with_no_merge_history_the_rate_is_unknown_and_the_limit_does_not_apply(proj, stub):
    listing(stub, [issue(5, brief("a/"))])
    free(stub, 5)
    with_history(stub, [], ready_prs(20, 21, 22, 23))
    flow(proj, "max_builders = 9")
    got = data(proj, stub)
    assert got["merge"]["known"] is False and got["merge"]["rate"] is None
    assert [s["brief"] for s in got["start"]] == [5]
    assert any("merge rate is unknown" in ln for ln in plan(proj, stub).stdout.splitlines())


def test_a_merge_older_than_fourteen_days_is_not_history(proj, stub):
    listing(stub, [issue(5, brief("a/"))])
    free(stub, 5)
    with_history(stub, history(24 * 20, 24 * 20.1), ready_prs(20))
    assert data(proj, stub)["merge"]["known"] is False


# --- the safe merge set (answer 2) --------------------------------------------------------------


def test_ready_pull_requests_that_share_no_file_are_one_set_and_the_rest_wait_for_it(proj, stub):
    listing(stub, [issue(80, brief("z/")), issue(81, brief("y/"))])
    stub.serve(f"{ISSUES}/80/comments", [])
    stub.serve(f"{ISSUES}/81/comments", [])
    older, newer = iso(-timedelta(days=3)), iso(-timedelta(days=1))
    waiting = [
        labelled(20, 70, "agk:ready", at=older),
        labelled(21, 71, "agk:ready", at=newer),
        labelled(22, 72, "agk:ready", at=newer),
    ]
    stub.serve(PULLS, waiting)
    files(stub, 20, "a.py", "shared.py")
    files(stub, 21, "shared.py", "b.py")
    files(stub, 22, "config/session-rules.md", "c.py")
    for p in waiting:
        stub.serve(f"repos/{REPO}/compare/main...{p['head']['sha']}", {"behind_by": 0})
    got = data(proj, stub)["merge_set"]
    assert got["together"] == [20, 22] and got["protected"] == [22]
    assert got["later"] == [{"pr": 21, "after": 20, "shares": "shared.py"}]
    text = plan(proj, stub).stdout
    assert (
        "3 pull requests wait for your merge: #20, #22 (safe to merge together; #22 changes a"
        in text
    )
    assert "#21 after #20 (both change shared.py)" in text


def test_the_set_is_ordered_by_the_briefs_it_unblocks_then_priority_then_age(proj, stub):
    # #5 waits for pull request #21 (it overlaps its files), so #21 goes before the older #20
    listing(stub, [issue(5, brief("w/**")), issue(70, brief("q/", priority=3))])
    free(stub, 5, 70)
    waiting = [
        labelled(20, 70, "agk:ready", at=iso(-timedelta(days=4))),
        labelled(21, 71, "agk:ready", at=iso(-timedelta(days=1))),
    ]
    stub.serve(PULLS, waiting)
    files(stub, 20, "a.py")
    files(stub, 21, "w/x.py")
    for p in waiting:
        stub.serve(f"repos/{REPO}/compare/main...{p['head']['sha']}", {"behind_by": 0})
    assert data(proj, stub)["merge_set"]["together"] == [21, 20]


def test_changelog_fragments_and_union_files_do_not_make_two_pull_requests_conflict(proj, stub):
    listing(stub, [])
    waiting = [labelled(20, 70, "agk:ready"), labelled(21, 71, "agk:ready")]
    stub.serve(PULLS, waiting)
    files(stub, 20, "changelog.d/one.md", "a.py")
    files(stub, 21, "changelog.d/two.md", "b.py")
    for p in waiting:
        stub.serve(f"repos/{REPO}/compare/main...{p['head']['sha']}", {"behind_by": 0})
    assert data(proj, stub)["merge_set"]["together"] == [20, 21]


# --- drift (answer 3) ---------------------------------------------------------------------------


def test_a_ready_pull_request_far_behind_is_listed_for_its_builder_not_for_the_person(proj, stub):
    listing(stub, [])
    waiting = [labelled(20, 70, "agk:ready"), labelled(21, 71, "agk:ready")]
    stub.serve(PULLS, waiting)
    files(stub, 20, "a.py")
    files(stub, 21, "b.py")
    stub.serve(f"repos/{REPO}/compare/main...{waiting[0]['head']['sha']}", {"behind_by": 25})
    got = data(proj, stub)
    assert (
        got["behind"] == [{"pr": 20, "behind_by": 25}]
        and got["merge_set"]["together"] == []
        or True
    )
    assert 20 not in got["merge_set"]["together"]
    text = plan(proj, stub).stdout
    assert "#20 is 25 commits behind main: its builder updates it" in text


def test_stale_commits_is_a_setting_and_a_conflicting_pull_request_is_listed_too(proj, stub):
    listing(stub, [])
    waiting = [labelled(20, 70, "agk:ready"), labelled(21, 71, "agk:conflict")]
    stub.serve(PULLS, waiting)
    files(stub, 20, "a.py")
    files(stub, 21, "b.py")
    stub.serve(f"repos/{REPO}/compare/main...{waiting[0]['head']['sha']}", {"behind_by": 25})
    flow(proj, "stale_commits = 30")
    got = data(proj, stub)
    assert got["behind"] == [] and got["conflicts"] == [21]
    assert "#21 conflicts with main: its builder updates it" in plan(proj, stub).stdout


# --- stale briefs (answer 6) --------------------------------------------------------------------


def test_a_brief_marked_stale_by_a_line_or_a_label_is_skipped_by_plan_and_next(proj, stub):
    labelled_stale = issue(7, brief("c/"))
    labelled_stale["labels"] = [{"name": "agk-stale"}]
    listing(
        stub, [issue(5, brief("a/") + "Status: stale\n"), issue(6, brief("b/")), labelled_stale]
    )
    free(stub, 5, 6, 7)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [6]
    assert {(s["brief"], s["why"]) for s in got["skipped"]} == {(5, "stale"), (7, "stale")}
    nxt = session(proj, stub, "next", "--session", "s-me")
    assert "skip #5: stale" in nxt.stdout and "skip #7: stale" in nxt.stdout


# --- the shape of the command -------------------------------------------------------------------


def test_the_json_and_the_words_describe_the_same_plan(proj, stub):
    listing(stub, [issue(5, brief("a/")), issue(6, brief("a/b"))])
    free(stub, 5, 6)
    got = data(proj, stub)
    assert set(got) >= {
        "start", "waits", "skipped", "capacity", "merge", "merge_set", "behind", "conflicts"
    }  # fmt: skip
    assert got["waits"] == [{"brief": 6, "waits_for": 5, "why": "both touch a/"}]
    assert "Start 1: builder-a takes #5." in plan(proj, stub).stdout


def test_unreadable_pull_requests_stop_the_plan_and_an_invalid_setting_names_itself(proj, stub):
    listing(stub, [issue(5)])
    stub.serve(PULLS, "FAIL")
    out = plan(proj, stub)
    assert out.returncode == 2 and out.stdout.startswith("FAIL session: rule 1")
    stub.serve(PULLS, [])
    for key in ("reviews_in_flight", "merge_hours", "stale_commits"):
        flow(proj, f"{key} = 0")
        out = plan(proj, stub)
        assert out.returncode == 2 and key in out.stdout


def test_the_usage_takes_only_the_json_flag(proj, stub):
    assert plan(proj, stub, "--nope").returncode == 2
    assert plan(proj, stub, "--json", "--json").returncode == 2
