"""session.py plan: overlap by files, not folders, and claims whose session is gone.

Brief #330, ADR-0189; REQ-041. A brief waits only when it would change the same file as running
work (answer 1), a claim whose session has posted nothing for `claim_stale_hours` and has no open
pull request no longer blocks its brief and is listed (answer 2), and every wait names the exact
file (answer 3). The tests were written first (answer 4)."""

from __future__ import annotations

from datetime import timedelta

from test_session import ISSUES, comment, iso, issue, listing
from test_session_flow import DAY, PULLS, brief, flow, merged
from test_session_plan import changed, data, free, labelled, plan, proj, stub  # noqa: F401

# --- answer 1: overlap is judged by files ---------------------------------------------------------


def test_two_briefs_under_one_folder_with_different_files_start_together(proj, stub):
    """The wave of 30 Oct 2026: seven briefs each named one guide of `docs/guides/`."""
    listing(
        stub,
        [
            issue(5, brief("docs/guides/a.md, scripts/a.py")),
            issue(6, brief("docs/guides/b.md, scripts/b.py")),
            issue(7, brief("docs/guides/c.md")),
        ],
    )
    free(stub, 5, 6, 7)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [5, 6, 7] and got["waits"] == []


def test_a_folder_entry_does_not_hold_a_brief_that_names_a_file_under_it(proj, stub):
    """A taken brief whose `Touches:` is `docs/guides/` holds no brief that names one guide."""
    listing(stub, [issue(4, brief("docs/guides/")), issue(5, brief("docs/guides/a.md"))])
    stub.serve(f"{ISSUES}/4/comments", [comment(1, "x", f"taken: builder-x {DAY}")])
    free(stub, 5)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [5] and got["waits"] == []


def test_the_same_file_waits_and_the_plan_names_that_file(proj, stub):
    listing(
        stub,
        [
            issue(5, brief("docs/guides/a.md, scripts/a.py")),
            issue(6, brief("docs/guides/, docs/guides/a.md")),
        ],
    )
    free(stub, 5, 6)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [5]
    assert got["waits"] == [{"brief": 6, "waits_for": 5, "why": "both touch docs/guides/a.md"}]
    assert "#6 waits for #5 (both touch docs/guides/a.md)." in plan(proj, stub).stdout.splitlines()


def test_a_file_glob_overlaps_the_file_it_matches_and_names_it(proj, stub):
    listing(stub, [issue(5, brief("scripts/agk/session.py")), issue(6, brief("scripts/agk/*.py"))])
    free(stub, 5, 6)
    got = data(proj, stub)
    assert got["waits"] == [
        {"brief": 6, "waits_for": 5, "why": "both touch scripts/agk/session.py"}
    ]


def test_two_folder_entries_still_overlap_as_before(proj, stub):
    listing(stub, [issue(5, brief("docs/guides/")), issue(6, brief("docs/guides/"))])
    free(stub, 5, 6)
    assert data(proj, stub)["waits"] == [
        {"brief": 6, "waits_for": 5, "why": "both touch docs/guides/"}
    ]


def test_shared_mechanical_files_still_never_overlap(proj, stub):
    listing(stub, [issue(5, brief("changelog.d/*.md, a.py")), issue(6, brief("changelog.d/x.md"))])
    free(stub, 5, 6)
    assert [s["brief"] for s in data(proj, stub)["start"]] == [5, 6]


def test_a_changed_file_overlaps_a_folder_entry_only_when_the_brief_names_that_file(proj, stub):
    listing(
        stub,
        [
            issue(5, brief("docs/guides/")),
            issue(6, brief("docs/guides/, docs/guides/x.md")),
            issue(7, brief("docs/guides/y.md")),
        ],
    )
    stub.serve(PULLS, [labelled(20, 1, "agk:review")])
    changed(stub, 20, ("modified", "docs/guides/x.md"))
    free(stub, 5, 6, 7)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [5, 7]
    assert got["waits"] == [{"brief": 6, "pull_request": 20, "why": "it changes docs/guides/x.md"}]
    words = plan(proj, stub).stdout.splitlines()
    assert "#6 waits for pull request #20 (it changes docs/guides/x.md)." in words


# --- answer 2: a claim whose session is gone ------------------------------------------------------

THREE = "Builds: (a) the first part; (b) independent: the second; (c) independent: the third\n"


def built(number: int, brief_no: int, name: str, ago: timedelta, state: str = "closed") -> dict:
    found = {**merged(number, brief_no, ago), "title": f"feat: x (brief #{brief_no} build {name})"}
    if state == "open":
        found.update(state="open", merged_at=None)
    return found


def test_a_stale_claim_no_longer_blocks_its_brief_and_is_listed(proj, stub):
    """#263 on 30 Oct 2026: builder-f took build (c) days before, merged it and ended; an open
    pull request of builder-y for build (b) kept that take live, and the plan said "taken by
    builder-f"."""
    listing(stub, [issue(5, brief("a/x.py") + THREE)])
    old, recent = iso(-timedelta(hours=80)), iso(-timedelta(hours=1))
    stub.serve(
        f"{ISSUES}/5/comments",
        [
            comment(1, "x", f"taken: builder-f {DAY} build (c)", old),
            comment(2, "x", f"taken: builder-y {DAY} build (b)", recent),
        ],
    )
    stub.serve(
        PULLS,
        [
            built(20, 5, "(c)", timedelta(hours=79)),
            built(21, 5, "b", timedelta(0), state="open"),
        ],
    )
    changed(stub, 21, ("modified", "z/b.py"))
    got = data(proj, stub)
    assert [(s["brief"], s.get("build")) for s in got["start"]] == [(5, "a")]
    (claim,) = got["stale_claims"]
    assert {"brief": 5, "session": "builder-f", "build": "c"}.items() <= claim.items()
    assert claim["why"] == "stale claim by builder-f, 3 days"
    assert all("builder-f" not in s["why"] for s in got["skipped"])
    assert "Stale: #5 (stale claim by builder-f, 3 days)." in plan(proj, stub).stdout.splitlines()


def test_a_stale_claim_on_a_brief_without_builds_frees_it(proj, stub):
    """With `claim_hours` longer than `claim_stale_hours` a take with no pull request is still
    live; once its session has posted nothing for `claim_stale_hours`, it is stale."""
    flow(proj, "claim_hours = 72")
    listing(stub, [issue(5, brief("a/x.py")), issue(6, brief("b/x.py"))])
    stub.serve(
        f"{ISSUES}/5/comments",
        [comment(1, "x", f"taken: builder-f {DAY}", iso(-timedelta(hours=30)))],
    )
    free(stub, 6)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [5, 6] and got["capacity"]["running"] == 0
    assert got["stale_claims"][0]["why"] == "stale claim by builder-f, 30 hours"


def test_a_fresh_claim_with_no_pull_request_still_blocks_and_is_not_stale(proj, stub):
    listing(stub, [issue(5, brief("a/x.py")), issue(6, brief("b/x.py"))])
    stub.serve(
        f"{ISSUES}/5/comments",
        [comment(1, "x", f"taken: builder-f {DAY}", iso(-timedelta(hours=1)))],
    )
    free(stub, 6)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [6] and got["stale_claims"] == []
    assert got["capacity"]["running"] == 1
    assert any(s["brief"] == 5 and "taken by builder-f" in s["why"] for s in got["skipped"])


def test_claim_stale_hours_sets_the_age_and_an_invalid_value_names_the_setting(proj, stub):
    flow(proj, "claim_hours = 72\nclaim_stale_hours = 40")
    listing(stub, [issue(5, brief("a/x.py"))])
    stub.serve(
        f"{ISSUES}/5/comments",
        [comment(1, "x", f"taken: builder-f {DAY}", iso(-timedelta(hours=30)))],
    )
    got = data(proj, stub)
    assert got["start"] == [] and got["stale_claims"] == []
    flow(proj, "claim_stale_hours = 0")
    out = plan(proj, stub)
    assert out.returncode == 2 and "claim_stale_hours" in out.stdout


def test_a_session_with_an_open_pull_request_is_never_stale(proj, stub):
    """builder-f's own open pull request for build (c) keeps its old take live and fresh."""
    listing(stub, [issue(5, brief("a/x.py") + THREE)])
    old = iso(-timedelta(hours=80))
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: builder-f {DAY} build (c)", old)])
    stub.serve(PULLS, [{**built(20, 5, "(c)", timedelta(0), state="open"), "created_at": old}])
    changed(stub, 20, ("modified", "z/c.py"))
    got = data(proj, stub)
    assert got["stale_claims"] == []


def test_a_later_post_of_the_session_keeps_its_claim_fresh(proj, stub):
    """A `taken:` or `released:` of the session on any brief is a post."""
    flow(proj, "claim_hours = 72")
    listing(stub, [issue(5, brief("a/x.py")), issue(6, brief("b/x.py"))])
    stub.serve(
        f"{ISSUES}/5/comments",
        [comment(1, "x", f"taken: builder-f {DAY}", iso(-timedelta(hours=30)))],
    )
    stub.serve(
        f"{ISSUES}/6/comments",
        [
            comment(2, "x", f"taken: builder-f {DAY}", iso(-timedelta(hours=3))),
            comment(3, "x", "released: builder-f", iso(-timedelta(hours=2))),
        ],
    )
    got = data(proj, stub)
    assert got["stale_claims"] == [] and [s["brief"] for s in got["start"]] == [6]
