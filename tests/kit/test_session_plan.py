"""session.py plan: waves, capacity, the merge queue, the safe merge set, drift and stale briefs.

Brief 247 build (a); SPEC-0034 rule 15; REQ-039. A `gh` stub serves saved JSON copies of the GitHub
responses; the plan is plain words by default and the same data with `--json`; it posts nothing,
uses no model and reads only what the session scripts already read."""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - the tests stub it, nothing is run
from datetime import datetime, timedelta

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
    assert "#6 waits for #5 (both touch scripts/agk/x.py)." in lines  # the file, not the folder


def test_the_priority_and_then_the_number_decide_who_waits(proj, stub):
    listing(stub, [issue(5, brief("a/")), issue(6, brief("a/b", priority=1))])
    free(stub, 5, 6)
    lines = plan(proj, stub).stdout.splitlines()
    assert lines[0] == "Start 1: builder-a takes #6."
    assert "#5 waits for #6 (both touch a/b)." in lines


def changed(stub: Stub, number: int, *entries: tuple[str, str]) -> None:
    """The files of a pull request as (status, filename) pairs."""
    stub.serve(
        f"{PULLS}/{number}/files",
        [{"filename": name, "status": status} for status, name in entries],
    )


def test_a_brief_that_overlaps_running_work_waits_for_it(proj, stub):
    listing(stub, [issue(5, brief("scripts/**")), issue(6, brief("docs/**"))])
    stub.serve(PULLS, [labelled(20, 1, "agk:review")])
    changed(stub, 20, ("modified", "scripts/agk/session.py"))
    free(stub, 5, 6)
    lines = plan(proj, stub).stdout.splitlines()
    assert lines[0] == "Start 1: builder-a takes #6."
    assert "#5 waits for pull request #20 (it changes scripts/agk/session.py)." in lines


def test_a_file_a_pull_request_adds_blocks_only_on_an_exact_path(proj, stub):
    """Every build adds an ADR, a fragment and tests: an added file is no reason to wait."""
    listing(stub, [issue(5, brief("docs/adr/**")), issue(6, brief("docs/guides/new.md"))])
    stub.serve(PULLS, [labelled(20, 1, "agk:review")])
    changed(stub, 20, ("added", "docs/adr/0153-x.md"), ("added", "docs/guides/new.md"))
    free(stub, 5, 6)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [5]  # the added ADR does not block #5
    assert got["waits"] == [
        {"brief": 6, "pull_request": 20, "why": "it adds docs/guides/new.md"}
    ]  # an exact path does


def test_a_modified_renamed_or_removed_file_matched_by_a_glob_blocks(proj, stub):
    listing(stub, [issue(5, brief("a/**")), issue(6, brief("b/**")), issue(7, brief("c/**"))])
    stub.serve(PULLS, [labelled(20, 1, "agk:review")])
    changed(stub, 20, ("modified", "a/x.py"), ("removed", "b/y.py"), ("renamed", "c/z.py"))
    free(stub, 5, 6, 7)
    got = data(proj, stub)
    assert got["start"] == [] and [w["brief"] for w in got["waits"]] == [5, 6, 7]
    assert got["waits"][0]["why"] == "it changes a/x.py"


def test_a_renamed_file_blocks_by_its_old_name_too(proj, stub):
    listing(stub, [issue(5, brief("old/**"))])
    stub.serve(PULLS, [labelled(20, 1, "agk:review")])
    stub.serve(
        f"{PULLS}/20/files",
        [{"filename": "new/x.py", "previous_filename": "old/x.py", "status": "renamed"}],
    )
    free(stub, 5)
    assert [w["brief"] for w in data(proj, stub)["waits"]] == [5]


# --- the names of running sessions --------------------------------------------------------------


def test_a_session_with_an_open_builder_pull_request_is_not_offered_as_a_name(proj, stub):
    """Its take is older than the claim hours; the open pull request keeps it live."""
    listing(stub, [issue(9, brief("zz/")), issue(5, brief("a/")), issue(6, brief("b/"))])
    old = iso(-timedelta(hours=30))
    stub.serve(f"{ISSUES}/9/comments", [comment(1, "x", f"taken: builder-a {DAY}", old)])
    stub.serve(PULLS, [labelled(20, 9, "agk:review")])
    changed(stub, 20, ("modified", "zz/y.py"))
    free(stub, 5, 6)
    got = data(proj, stub)
    assert [s["session"] for s in got["start"]] == ["builder-b", "builder-c"]


def test_a_take_with_the_attribution_footer_is_read_as_a_take(proj, stub):
    """The server adds `---` and a `Generated by` line to a comment; the take is still a take."""
    footer = "\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_"
    listing(stub, [issue(5, brief("a/")), issue(6, brief("b/"))])
    stub.serve(
        f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-a {DAY} build (a){footer}")]
    )
    free(stub, 6)
    got = data(proj, stub)
    assert got["capacity"]["running"] == 1 and got["skipped"][0]["brief"] == 5
    assert [s["session"] for s in got["start"]] == ["builder-b"]


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
    # #5 waits for pull request #21 (it modifies a file the brief names), so #21 goes first
    listing(stub, [issue(5, brief("w/**")), issue(70, brief("q/", priority=3))])
    free(stub, 5, 70)
    waiting = [
        labelled(20, 70, "agk:ready", at=iso(-timedelta(days=4))),
        labelled(21, 71, "agk:ready", at=iso(-timedelta(days=1))),
    ]
    stub.serve(PULLS, waiting)
    changed(stub, 20, ("modified", "a.py"))
    changed(stub, 21, ("modified", "w/x.py"))
    for p in waiting:
        stub.serve(f"repos/{REPO}/compare/main...{p['head']['sha']}", {"behind_by": 0})
    got = data(proj, stub)
    assert got["waits"] == [{"brief": 5, "pull_request": 21, "why": "it changes w/x.py"}]
    assert got["merge_set"]["together"] == [21, 20]


def test_without_a_brief_unblocked_the_priority_of_the_brief_then_the_age_decide(proj, stub):
    listing(stub, [issue(70, brief("q/", priority=1)), issue(71, brief("r/", priority=3))])
    free(stub, 70, 71)
    waiting = [
        labelled(20, 71, "agk:ready", at=iso(-timedelta(days=4))),
        labelled(21, 70, "agk:ready", at=iso(-timedelta(days=1))),
        labelled(22, 99, "agk:ready", at=iso(-timedelta(days=6))),
    ]
    stub.serve(PULLS, waiting)
    for p in waiting:
        changed(stub, p["number"], ("modified", f"z/{p['number']}.py"))
        stub.serve(f"repos/{REPO}/compare/main...{p['head']['sha']}", {"behind_by": 0})
    # priority 1 (#21), then 2 for the brief that is not open (#22), then 3 (#20)
    assert data(proj, stub)["merge_set"]["together"] == [21, 22, 20]


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
        "start", "waits", "skipped", "capacity", "merge", "merge_set", "behind", "conflicts",
        "stale_claims",
    }  # fmt: skip
    assert got["waits"] == [{"brief": 6, "waits_for": 5, "why": "both touch a/b"}]
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


# --- the builds of a brief (brief 251) ----------------------------------------------------------

BUILDS = "Builds: (a) the first part; (b) the second part\n"
MERGED_ALL = "every build is merged; the conductor closes it"


def built(number: int, brief_no: int, build: str) -> dict:
    """A merged pull request that names `build (<x>)` for the brief."""
    title = f"feat: a part, brief #{brief_no} build ({build})"
    return {**merged(number, brief_no, timedelta(hours=2)), "title": title}


def parts(touches: str = "a/", line: str = BUILDS) -> str:
    return brief(touches) + line


def test_the_next_free_build_is_named_in_the_plan_and_the_words(proj, stub):
    listing(stub, [issue(5, parts())])
    free(stub, 5)
    got = data(proj, stub)
    assert got["start"] == [{"session": "builder-a", "brief": 5, "title": "t5", "build": "a"}]
    assert plan(proj, stub).stdout.splitlines()[0] == "Start 1: builder-a takes #5 build (a)."


def test_a_merged_build_is_skipped_and_the_next_one_is_named(proj, stub):
    listing(stub, [issue(5, parts())])
    stub.serve(PULLS, [built(100, 5, "a")])
    free(stub, 5)
    assert [s["build"] for s in data(proj, stub)["start"]] == ["b"]


def test_a_build_of_another_brief_does_not_count_as_merged(proj, stub):
    listing(stub, [issue(5, parts())])
    stub.serve(PULLS, [built(100, 9, "a")])  # build (a) of brief #9
    free(stub, 5)
    assert [s["build"] for s in data(proj, stub)["start"]] == ["a"]


def test_an_open_pull_request_that_names_a_build_keeps_it_from_being_named_again(proj, stub):
    listing(stub, [issue(5, parts())])
    still_open = {**built(101, 5, "a"), "state": "open", "merged_at": None}
    stub.serve(PULLS, [still_open])
    files(stub, 101, "zz/x.py")
    free(stub, 5)
    got = data(proj, stub)
    assert got["start"] == []
    assert got["waits"] == [
        {"brief": 5, "build": "b", "waits_for_build": "a", "why": "build (b) waits for build (a)"}
    ]


def test_a_build_waits_for_the_one_before_it_while_that_is_taken(proj, stub):
    listing(stub, [issue(5, parts())])
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-z {DAY} build (a)")])
    got = data(proj, stub)
    assert got["start"] == []
    assert got["waits"] == [
        {"brief": 5, "build": "b", "waits_for_build": "a", "why": "build (b) waits for build (a)"}
    ]
    out = plan(proj, stub).stdout.splitlines()
    assert "#5 build (b) waits for build (a)." in out


def test_a_build_marked_independent_does_not_wait(proj, stub):
    line = "Builds: (a) the first part; (b) independent: the second part\n"
    listing(stub, [issue(5, parts(line=line))])
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-z {DAY} build (a)")])
    got = data(proj, stub)
    assert [(s["brief"], s["build"]) for s in got["start"]] == [(5, "b")]
    assert got["waits"] == []


def test_a_take_of_the_whole_brief_leaves_no_build_to_name(proj, stub):
    listing(stub, [issue(5, parts())])
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-z {DAY}")])
    got = data(proj, stub)
    assert got["start"] == [] and got["skipped"][0]["brief"] == 5


def test_a_brief_whose_builds_are_all_merged_starts_nothing_and_says_so(proj, stub):
    listing(stub, [issue(5, parts())])
    stub.serve(PULLS, [built(100, 5, "a"), built(101, 5, "b")])
    free(stub, 5)
    got = data(proj, stub)
    assert got["start"] == [] and {"brief": 5, "why": MERGED_ALL} in got["skipped"]


def test_a_brief_without_a_builds_line_is_planned_as_before(proj, stub):
    listing(stub, [issue(5, brief("a/"))])
    free(stub, 5)
    (entry,) = data(proj, stub)["start"]
    assert "build" not in entry
    assert plan(proj, stub).stdout.splitlines()[0] == "Start 1: builder-a takes #5."


# --- a take whose session has moved on (the verdict on 39b7f9a) -------------------------------


def ends(stamp: str, hours: int = 4) -> str:
    """The `HH:MM UTC` at which a take posted at `stamp` stops being live."""
    when = datetime.fromisoformat(stamp.replace("Z", "+00:00")) + timedelta(hours=hours)
    return when.strftime("%H:%M UTC")


def test_a_session_that_moved_on_frees_its_finished_brief_for_the_next_build(proj, stub):
    listing(stub, [issue(5, parts("a/")), issue(6, brief("b/"))])
    old, recent = iso(-timedelta(hours=3)), iso(-timedelta(hours=1))
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-z {DAY}", old)])
    stub.serve(f"{ISSUES}/6/comments", [comment(2, "x", f"taken: builder-z {DAY}", recent)])
    stub.serve(PULLS, [built(100, 5, "a")])
    got = data(proj, stub)
    assert [(s["brief"], s["build"]) for s in got["start"]] == [(5, "b")]
    assert got["capacity"]["running"] == 1  # only the take on #6 is running work


def test_a_session_that_has_not_moved_on_still_holds_the_brief_and_the_hour_is_named(proj, stub):
    listing(stub, [issue(5, parts("a/"))])
    when = iso(-timedelta(hours=1))
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-z {DAY}", when)])
    stub.serve(PULLS, [built(100, 5, "a")])
    got = data(proj, stub)
    assert got["start"] == []
    held = f"build (b) is held for builder-z until {ends(when)}"
    assert got["waits"] == [{"brief": 5, "build": "b", "held_by": "builder-z", "why": held}]
    assert f"#5 {held}." in plan(proj, stub).stdout.splitlines()


def test_a_take_of_the_session_on_another_brief_older_than_this_one_does_not_free_it(proj, stub):
    listing(stub, [issue(5, parts("a/")), issue(6, brief("b/"))])
    older, newer = iso(-timedelta(hours=3)), iso(-timedelta(hours=1))
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-z {DAY}", newer)])
    stub.serve(f"{ISSUES}/6/comments", [comment(2, "x", f"taken: builder-z {DAY}", older)])
    stub.serve(PULLS, [built(100, 5, "a")])
    got = data(proj, stub)
    assert got["start"] == [] and got["waits"][0]["held_by"] == "builder-z"


def test_a_taken_brief_says_until_when_and_while_a_pull_request_is_open(proj, stub):
    listing(stub, [issue(5, brief("a/")), issue(6, brief("b/"))])
    when = iso(-timedelta(hours=1))
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-z {DAY}", when)])
    stub.serve(f"{ISSUES}/6/comments", [comment(2, "x", f"taken: builder-y {DAY}", when)])
    stub.serve(PULLS, [labelled(20, 6, "agk:review")])
    changed(stub, 20, ("modified", "zz/y.py"))
    why = {s["brief"]: s["why"] for s in data(proj, stub)["skipped"]}
    assert why[5] == f"taken by builder-z until {ends(when)}"
    assert why[6] == "taken by builder-y while its pull request is open"
    assert f"#5 (taken by builder-z until {ends(when)})" in plan(proj, stub).stdout


# --- the build a pull request delivers is read from its title (the verdict on 6ef8389) ------------


def test_a_sentence_in_a_body_that_says_a_build_is_not_done_does_not_mark_it_done(proj, stub):
    """#248's body says "Build (b) of the brief is not in this pull request."."""
    listing(stub, [issue(5, parts())])
    shipped = {
        **merged(100, 5, timedelta(hours=2)),
        "title": "feat(k5): retired requirements, brief #5 build (a) (SPEC-0004 rule 24, ADR-0151)",
        "body": "Brief: #5\n\nBuild (b) of the brief is not in this pull request.\n",
    }
    stub.serve(PULLS, [shipped])
    free(stub, 5)
    got = data(proj, stub)
    assert [(s["brief"], s["build"]) for s in got["start"]] == [(5, "b")]


def test_a_build_named_only_in_the_body_of_a_pull_request_is_not_taken_as_delivered(proj, stub):
    listing(stub, [issue(5, parts())])
    loose = {
        **merged(100, 5, timedelta(hours=2)),
        "title": "feat(k5): something else, brief #5",
        "body": "Brief: #5\nThis is build (a) of it.\n",
    }
    stub.serve(PULLS, [loose])
    free(stub, 5)
    assert [s["build"] for s in data(proj, stub)["start"]] == ["a"]


def test_the_title_of_another_brief_with_the_same_build_does_not_count(proj, stub):
    listing(stub, [issue(5, parts())])
    stub.serve(PULLS, [built(100, 50, "a")])  # "brief #50 build (a)" is not brief #5
    free(stub, 5)
    assert [s["build"] for s in data(proj, stub)["start"]] == ["a"]


# --- a brief never disappears from the plan without a word ---------------------------------------


def test_a_moved_on_brief_whose_builds_are_all_merged_is_listed_with_its_reason(proj, stub):
    listing(stub, [issue(5, parts("a/")), issue(6, brief("b/"))])
    old, recent = iso(-timedelta(hours=3)), iso(-timedelta(hours=1))
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-z {DAY}", old)])
    stub.serve(f"{ISSUES}/6/comments", [comment(2, "x", f"taken: builder-z {DAY}", recent)])
    stub.serve(PULLS, [built(100, 5, "a"), built(101, 5, "b")])
    got = data(proj, stub)
    assert {"brief": 5, "why": MERGED_ALL} in got["skipped"]
    assert f"#5 ({MERGED_ALL})" in plan(proj, stub).stdout


def test_a_brief_the_plan_does_not_start_for_want_of_a_slot_is_listed(proj, stub):
    listing(stub, [issue(n, brief(f"d{n}/")) for n in (5, 6, 7)])
    free(stub, 5, 6, 7)
    flow(proj, "max_builders = 2")
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [5, 6]
    assert {"brief": 7, "why": "no free slot"} in got["skipped"]


def test_a_brief_whose_builds_are_all_taken_or_in_progress_is_listed(proj, stub):
    listing(stub, [issue(5, parts("a/", "Builds: (a) the only part\n"))])
    still_open = {**built(101, 5, "a"), "state": "open", "merged_at": None}
    stub.serve(PULLS, [still_open])
    files(stub, 101, "zz/x.py")
    free(stub, 5)
    got = data(proj, stub)
    assert got["start"] == []
    named = {x["brief"] for x in got["skipped"]} | {x["brief"] for x in got["waits"]}
    assert 5 in named


def test_every_open_brief_is_in_start_waits_or_skipped(proj, stub):
    listing(stub, [issue(n, brief(f"d{n}/")) for n in (5, 6, 7, 8)] + [issue(9, parts("e/"))])
    stub.serve(f"{ISSUES}/8/comments", [comment(1, "x", f"taken: builder-y {DAY}")])
    free(stub, 5, 6, 7, 9)
    flow(proj, "max_builders = 2")
    got = data(proj, stub)
    seen = {x["brief"] for x in got["start"] + got["waits"] + got["skipped"]}
    assert seen == {5, 6, 7, 8, 9}


# --- the running sessions (brief 402, the verdict on 7dfdcd8, Q-402-1) ---------------------------


def test_a_plan_with_one_take_and_one_open_pull_request_lists_both_as_running(proj, stub):
    """REQ-040: brief #402 answer 1 (`running`: the live takes and the open builder pull
    requests, each with its session, its brief and, where known, its pull request and author)."""
    listing(stub, [issue(9, brief("zz/")), issue(5, brief("a/")), issue(6, brief("b/"))])
    old = iso(-timedelta(hours=30))
    stub.serve(f"{ISSUES}/9/comments", [comment(1, "b", f"taken: builder-a {DAY}", old)])
    stub.serve(f"{ISSUES}/5/comments", [comment(2, "x", f"taken: builder-b {DAY} build (a)")])
    stub.serve(PULLS, [labelled(20, 9, "agk:review")])
    changed(stub, 20, ("modified", "zz/y.py"))
    free(stub, 6)
    got = data(proj, stub)
    assert got["running"] == [
        {"session": "builder-a", "brief": 9, "pull_request": 20, "author": "b"},
        {"session": "builder-b", "brief": 5, "build": "a", "author": "x"},
    ]
    assert got["capacity"]["running"] == 2  # the count stays as it was
    read_only(stub)


def test_no_running_work_is_an_empty_running_list(proj, stub):
    """REQ-040: brief #402 answer 1 (no running session: an empty list, never a missing one)."""
    listing(stub, [issue(5, brief("a/"))])
    free(stub, 5)
    assert data(proj, stub)["running"] == []


def test_an_open_pull_request_without_a_live_take_is_not_listed(proj, stub):
    """REQ-040: brief #402 answer 1 (a resume prompt needs the session's name; a pull request
    whose brief has no live take names none, so it is left out rather than guessed)."""
    listing(stub, [issue(9, brief("zz/"))])
    free(stub, 9)
    stub.serve(PULLS, [labelled(20, 9, "agk:review")])
    changed(stub, 20, ("modified", "zz/y.py"))
    assert data(proj, stub)["running"] == []


# --- the machine's memory (brief 409) -----------------------------------------------------------

GIB = 1024**3


def planned(proj, stub, monkeypatch, capsys, memory: int | None, *extra: str):
    """The plan, run in this process with the machine's available memory read as MEMORY bytes
    (None: unreadable), so that a test never depends on the memory of the machine that runs it."""
    import common
    import session

    monkeypatch.chdir(proj.root)
    monkeypatch.setenv("PATH", f"{stub.bin}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GH_STUB_DIR", str(stub.dir))
    for name in ("GITHUB_BASE_REF", "AGK_BASE", "CI"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(common, "available_memory", lambda: memory)
    code = session.main(["plan", *extra])
    return code, capsys.readouterr().out


def four_ready(stub) -> None:
    listing(stub, [issue(n, brief(f"d{n}/")) for n in (5, 6, 7, 8)])
    free(stub, 5, 6, 7, 8)


def test_without_builder_memory_gb_the_plan_is_unchanged_and_names_its_limit(
    proj, stub, monkeypatch, capsys
):
    """REQ-041: brief #409 answers 1 and 3 (unset: today's figure, the limit is named)."""
    four_ready(stub)
    flow(proj, "max_builders = 3")
    code, out = planned(proj, stub, monkeypatch, capsys, 1 * GIB, "--json")
    got = json.loads(out)
    assert code == 0 and len(got["start"]) == 3
    assert got["capacity"]["slots"] == 3 and got["capacity"]["limit"] == "max_builders"
    assert "memory" not in got["capacity"] and "builder_memory_gb" not in got["capacity"]
    code, words = planned(proj, stub, monkeypatch, capsys, 1 * GIB)
    assert code == 0 and "memory" not in words
    read_only(stub)


def test_a_memory_limit_below_max_builders_caps_the_start_and_is_named(
    proj, stub, monkeypatch, capsys
):
    """REQ-041: brief #409 answers 1 and 3 (the lower of today's figure and memory / setting)."""
    four_ready(stub)
    flow(proj, "max_builders = 4\nreviews_in_flight = 9\nbuilder_memory_gb = 4")
    code, out = planned(proj, stub, monkeypatch, capsys, 11 * GIB, "--json")
    got = json.loads(out)
    assert code == 0 and [s["brief"] for s in got["start"]] == [5, 6]  # 11 // 4 = 2
    cap = got["capacity"]
    assert cap["slots"] == 2 and cap["limit"] == "memory"
    assert cap["builder_memory_gb"] == 4
    assert cap["memory"] == {"available_bytes": 11 * GIB, "builders": 2}
    assert {"brief": 7, "why": "no free slot"} in got["skipped"]
    code, words = planned(proj, stub, monkeypatch, capsys, 11 * GIB)
    lines = words.splitlines()
    assert lines[0] == "Start 2: builder-a takes #5, builder-b takes #6."
    assert (
        "Capacity: 2 (limit: memory; 11 GB available, builder_memory_gb is 4, room for 2)." in lines
    )


def test_a_memory_limit_above_max_builders_leaves_max_builders_the_limit(
    proj, stub, monkeypatch, capsys
):
    """REQ-041: brief #409 answers 1 and 3 (memory enough: today's figure stands)."""
    four_ready(stub)
    flow(proj, "max_builders = 2\nbuilder_memory_gb = 2")
    code, out = planned(proj, stub, monkeypatch, capsys, 64 * GIB, "--json")
    cap = json.loads(out)["capacity"]
    assert code == 0 and cap["slots"] == 2 and cap["limit"] == "max_builders"
    assert cap["memory"] == {"available_bytes": 64 * GIB, "builders": 32}
    code, words = planned(proj, stub, monkeypatch, capsys, 64 * GIB)
    assert (
        "Capacity: 2 (limit: max_builders; 64 GB available, builder_memory_gb is 2, room for 32)."
        in words.splitlines()
    )


def test_the_reviews_limit_is_named_when_it_is_the_lowest(proj, stub, monkeypatch, capsys):
    """REQ-041: brief #409 answer 3 (`reviews` when the conductor's backlog is the lowest)."""
    four_ready(stub)
    stub.serve(PULLS, [labelled(10, 1, "agk:review")])
    files(stub, 10, "z/10")
    flow(proj, "max_builders = 6\nreviews_in_flight = 2\nbuilder_memory_gb = 1")
    code, out = planned(proj, stub, monkeypatch, capsys, 8 * GIB, "--json")
    cap = json.loads(out)["capacity"]
    assert code == 0 and cap["slots"] == 1 and cap["limit"] == "reviews"


def test_memory_never_counts_below_one_builder(proj, stub, monkeypatch, capsys):
    """REQ-041: brief #409 answer 1 (rounded down, never below 1 while no builder runs)."""
    four_ready(stub)
    flow(proj, "max_builders = 3\nbuilder_memory_gb = 8")
    code, out = planned(proj, stub, monkeypatch, capsys, 3 * GIB, "--json")
    got = json.loads(out)
    assert code == 0 and len(got["start"]) == 1
    assert got["capacity"]["memory"] == {"available_bytes": 3 * GIB, "builders": 1}
    assert got["capacity"]["limit"] == "memory"


def test_an_unreadable_memory_says_unknown_and_uses_todays_figure(proj, stub, monkeypatch, capsys):
    """REQ-041: brief #409 answer 2 (`memory: unknown`, today's figure)."""
    four_ready(stub)
    flow(proj, "max_builders = 3\nbuilder_memory_gb = 4")
    code, out = planned(proj, stub, monkeypatch, capsys, None, "--json")
    cap = json.loads(out)["capacity"]
    assert code == 0 and cap["slots"] == 3 and cap["limit"] == "max_builders"
    assert cap["memory"] == "unknown" and cap["builder_memory_gb"] == 4
    code, words = planned(proj, stub, monkeypatch, capsys, None)
    assert "Capacity: 3 (limit: max_builders; memory: unknown)." in words.splitlines()


@pytest.mark.parametrize("value", ["0", "-2", "2.5", '"4"', "true"])
def test_a_builder_memory_gb_that_is_not_a_whole_number_is_refused_naming_the_setting(
    proj, stub, monkeypatch, capsys, value
):
    """REQ-041: brief #409 answer 4 (refused, naming the setting, never the value)."""
    four_ready(stub)
    flow(proj, f"builder_memory_gb = {value}")
    code, out = planned(proj, stub, monkeypatch, capsys, 8 * GIB)
    assert code == 2 and "builder_memory_gb" in out
    assert value not in out.replace("builder_memory_gb", "")


# --- reading the available memory (brief 409 answer 2) ------------------------------------------

MEMINFO = "MemTotal:       16314560 kB\nMemFree:          812344 kB\nMemAvailable:    9437184 kB\n"


def test_linux_reads_memavailable_of_proc_meminfo():
    """REQ-041: brief #409 answer 2 (Linux: `/proc/meminfo`, MemAvailable, in bytes)."""
    import common

    assert common.meminfo_available(MEMINFO) == 9437184 * 1024
    assert common.meminfo_available("MemTotal: 1 kB\n") is None
    assert common.meminfo_available("MemAvailable: lots kB\n") is None


def test_macos_reads_the_free_pages_of_sysctl():
    """REQ-041: brief #409 answer 2 (macOS: `sysctl -n hw.pagesize vm.page_free_count`)."""
    import common

    assert common.sysctl_available("16384\n262144\n") == 16384 * 262144
    assert common.sysctl_available("16384\n") is None
    assert common.sysctl_available("x\ny\n") is None


def test_the_reading_follows_the_platform_and_any_failure_is_unknown(monkeypatch, tmp_path):
    """REQ-041: brief #409 answer 2 (no new dependency; unreadable is None, never an error)."""
    import common

    seen: list = []

    def fake_run(args, **kwargs):
        seen.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="4096\n1000\n", stderr="")

    monkeypatch.setattr(common.subprocess, "run", fake_run)
    monkeypatch.setattr(common.sys, "platform", "darwin")
    assert common.available_memory() == 4096 * 1000
    assert seen == [["sysctl", "-n", "hw.pagesize", "vm.page_free_count"]]

    def broken(args, **kwargs):
        raise OSError("no sysctl")

    monkeypatch.setattr(common.subprocess, "run", broken)
    assert common.available_memory() is None
    monkeypatch.setattr(common.sys, "platform", "linux")
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(MEMINFO, encoding="utf-8")
    monkeypatch.setattr(common, "MEMINFO", meminfo)
    assert common.available_memory() == 9437184 * 1024
    monkeypatch.setattr(common, "MEMINFO", tmp_path / "missing")
    assert common.available_memory() is None
    monkeypatch.setattr(common.sys, "platform", "sunos5")
    assert common.available_memory() is None
    monkeypatch.setattr(common.sys, "platform", "win32")
    monkeypatch.setattr(common, "windows_available", lambda: 5 * 1024**3)
    assert common.available_memory() == 5 * 1024**3

    def no_ctypes():
        raise AttributeError("windll")

    monkeypatch.setattr(common, "windows_available", no_ctypes)
    assert common.available_memory() is None


def test_with_builders_running_memory_for_none_more_starts_none(proj, stub, monkeypatch, capsys):
    """REQ-041: brief #409 answer 1, the verdict on 43ada36 (the floor of 1 holds only while no
    builder runs; with builders running, memory for none more is 0 and memory is the limit)."""
    listing(stub, [issue(n, brief(f"d{n}/")) for n in (5, 6, 7, 8)])
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-a {DAY}")])
    stub.serve(f"{ISSUES}/6/comments", [comment(2, "y", f"taken: builder-b {DAY}")])
    free(stub, 7, 8)
    flow(proj, "max_builders = 4\nreviews_in_flight = 9\nbuilder_memory_gb = 6")
    code, out = planned(proj, stub, monkeypatch, capsys, 2 * GIB, "--json")
    got = json.loads(out)
    assert code == 0 and got["start"] == [] and got["capacity"]["running"] == 2
    cap = got["capacity"]
    assert cap["slots"] == 0 and cap["limit"] == "memory"
    assert cap["memory"] == {"available_bytes": 2 * GIB, "builders": 0}
    code, words = planned(proj, stub, monkeypatch, capsys, 2 * GIB)
    lines = words.splitlines()
    assert lines[0] == (
        "Start 0: the machine's memory has room for no more builders "
        "(2 GB available, builder_memory_gb is 6)."
    )
    assert (
        "Capacity: 0 (limit: memory; 2 GB available, builder_memory_gb is 6, room for 0)." in lines
    )
