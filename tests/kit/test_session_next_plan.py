"""session.py next and claim judge overlap and claims by the plan's rules (brief #345, ADR-0195).

REQ-041. `next` uses the functions of `session.py plan` (`clash`, `file_conflict`, `covering`,
`entries_of` and the stale-claim reading) instead of its own, and prints the plan's reason when it
skips a brief (answer 1); nothing else in `next` changes (answer 2). `claim` reads takes the plan's
way too (the field note of 2026-10-30). For the cases of #330's tests, `next` and `plan` give the
same answer (answer 3); the tests were written first."""

from __future__ import annotations

from datetime import timedelta

import pytest
from test_session import ISSUES, REPO, Stub, comment, iso, issue, listing, posts, session
from test_session_flow import DAY, PULLS, brief, flow, merged
from test_session_plan import changed, data, free, labelled

THREE = "Builds: (a) the first part; (b) independent: the second; (c) independent: the third\n"


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    repo.write("config/protected-paths.txt", "config/\nscripts/agk/\n")
    return repo


def nxt(proj, stub):
    return session(proj, stub, "next", "--session", "s-me")


def skips(out) -> dict[int, str]:
    found = {}
    for line in out.stdout.splitlines():
        if line.startswith("skip #"):
            number, _, why = line[6:].partition(": ")
            found[int(number)] = why
    return found


def taken(out) -> int | None:
    for line in out.stdout.splitlines():
        if line.startswith("brief #"):
            return int(line[7:])
    return None


def plan_waits(got: dict) -> dict[int, str]:
    """The plan's reason for each brief that waits, in the words `next` prints."""
    out = {}
    for w in got["waits"]:
        target = f"#{w['waits_for']}" if "waits_for" in w else f"pull request #{w['pull_request']}"
        out[w["brief"]] = f"waits for {target} ({w['why']})"
    return out


# --- the cases of #330's tests: next and plan agree -----------------------------------------------


def test_two_briefs_under_one_folder_with_different_files_do_not_block_each_other(proj, stub):
    """A taken brief names `docs/guides/` and a file under it; another names a different file
    there: neither the plan nor `next` makes it wait (the old `next` compared folder prefixes)."""
    listing(
        stub,
        [issue(4, brief("docs/guides/, docs/guides/b.md")), issue(5, brief("docs/guides/a.md"))],
    )
    stub.serve(f"{ISSUES}/4/comments", [comment(1, "x", f"taken: builder-x {DAY}")])
    free(stub, 5)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [5] and got["waits"] == []
    out = nxt(proj, stub)
    assert out.returncode == 0 and taken(out) == 5 and 5 not in skips(out)


def test_a_folder_only_brief_waits_for_a_brief_that_names_a_file_under_it(proj, stub):
    listing(stub, [issue(4, brief("docs/guides/")), issue(5, brief("docs/guides/a.md"))])
    stub.serve(f"{ISSUES}/4/comments", [comment(1, "x", f"taken: builder-x {DAY}")])
    free(stub, 5)
    got = data(proj, stub)
    out = nxt(proj, stub)
    assert skips(out)[5] == plan_waits(got)[5] == "waits for #4 (both touch docs/guides/a.md)"
    assert out.returncode == 1 and posts(stub) == []


def test_a_folder_only_brief_against_a_pull_request_changing_a_file_under_it(proj, stub):
    """`tests/kit/` waits for a pull request that modifies a file under it and the reason names
    that file; a brief that names other files under the folder does not wait (the old `next`
    skipped both with `overlaps open pull request #20`)."""
    listing(
        stub,
        [
            issue(5, brief("tests/kit/")),
            issue(6, brief("tests/kit/, tests/kit/test_y.py")),
        ],
    )
    stub.serve(PULLS, [labelled(20, 1, "agk:review")])
    changed(stub, 20, ("modified", "tests/kit/test_x.py"))
    free(stub, 5, 6)
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [6]
    out = nxt(proj, stub)
    why = "waits for pull request #20 (it changes tests/kit/test_x.py)"
    assert skips(out)[5] == plan_waits(got)[5] == why
    assert out.returncode == 0 and taken(out) == 6
    assert [p[1] for p in posts(stub)] == [f"{ISSUES}/6/comments"]


def test_a_stale_claim_no_longer_blocks_next(proj, stub):
    """A take whose session has posted nothing for `claim_stale_hours` and has no open pull
    request holds nothing: the plan starts the brief and `next` takes it, saying `retakes`."""
    flow(proj, "claim_hours = 72")
    listing(stub, [issue(5, brief("a/x.py"))])
    old = comment(1, "x", f"taken: builder-f {DAY}", iso(-timedelta(hours=30)))
    stub.serve(f"{ISSUES}/5/comments", [old])
    got = data(proj, stub)
    assert [s["brief"] for s in got["start"]] == [5]
    assert got["stale_claims"][0]["why"] == "stale claim by builder-f, 30 hours"
    out = nxt(proj, stub)
    assert out.returncode == 0 and taken(out) == 5, out.stdout + out.stderr
    assert posts(stub)[0][2][1].startswith(f"body=taken: s-me {DAY} retakes")


def test_a_stale_claim_no_longer_makes_another_brief_wait(proj, stub):
    """A stale claim is not running work: a brief that touches the same file is not held back."""
    flow(proj, "claim_hours = 72")
    listing(stub, [issue(5, brief("a/x.py", priority=3)), issue(6, brief("a/x.py"))])
    old = comment(1, "x", f"taken: builder-f {DAY}", iso(-timedelta(hours=30)))
    stub.serve(f"{ISSUES}/5/comments", [old])
    free(stub, 6)
    got = data(proj, stub)
    assert 6 not in plan_waits(got)
    out = nxt(proj, stub)
    assert out.returncode == 0 and taken(out) == 6 and 6 not in skips(out)


def test_a_fresh_claim_with_no_pull_request_still_blocks_with_the_plans_reason(proj, stub):
    listing(stub, [issue(5, brief("a/x.py")), issue(6, brief("a/x.py"))])
    young = comment(1, "x", f"taken: builder-f {DAY}", iso(-timedelta(hours=1)))
    stub.serve(f"{ISSUES}/5/comments", [young])
    free(stub, 6)
    got = data(proj, stub)
    planned = {s["brief"]: s["why"] for s in got["skipped"]}
    out = nxt(proj, stub)
    assert planned[5].startswith("taken by builder-f until ") and skips(out)[5] == planned[5]
    assert skips(out)[6] == plan_waits(got)[6] == "waits for #5 (both touch a/x.py)"
    assert out.returncode == 1 and posts(stub) == []


def test_next_still_keeps_its_order_and_its_capacity(proj, stub):
    """Answer 2: the priority, then the number; `full` before anything is read or posted."""
    listing(stub, [issue(5, brief("a/", priority=3)), issue(6, brief("b/", priority=1))])
    free(stub, 5, 6)
    out = nxt(proj, stub)
    assert taken(out) == 6
    flow(proj, "max_builders = 1")
    stub.serve(PULLS, [labelled(20, 1)])
    out = nxt(proj, stub)
    assert out.stdout.strip() == "full 1/1" and out.returncode == 1


# --- claim reads takes the plan's way (the field note of 2026-10-30) ------------------------------

BRIEF = f"{ISSUES}/5/comments"


def built(number: int, name: str, ago: timedelta) -> dict:
    return {**merged(number, 5, ago), "title": f"feat: x (brief #5 build {name})"}


def claim(proj, stub, build: str = "c"):
    return session(proj, stub, "claim", "--session", "s-me", "--brief", "5", "--build", build)


def test_claim_takes_a_build_whose_old_take_is_stale(proj, stub):
    """#263 on 30 Oct 2026: builder-f's take of build (c), four days old with no pull request,
    was live again only because build (a) had just merged; it no longer refuses the claim."""
    listing(stub, [issue(5, brief("a/x.py") + THREE)])
    old = comment(1, "x", f"taken: builder-f {DAY} build (c)", iso(-timedelta(hours=96)))
    stub.serve(BRIEF, [old])
    stub.serve(PULLS, [built(20, "(a)", timedelta(hours=1))])
    got = data(proj, stub)
    assert [c["session"] for c in got["stale_claims"]] == ["builder-f"]
    out = claim(proj, stub)
    assert out.returncode == 0 and out.stdout.strip() == "claimed #5 build (c)", out.stdout
    assert posts(stub) == [["POST", BRIEF, ["-f", f"body=taken: s-me {DAY} build (c) retakes"]]]


def test_claim_still_refuses_a_build_that_a_fresh_take_holds(proj, stub):
    listing(stub, [issue(5, brief("a/x.py") + THREE)])
    young = comment(1, "x", f"taken: builder-f {DAY} build (c)", iso(-timedelta(hours=2)))
    stub.serve(BRIEF, [young])
    stub.serve(PULLS, [built(20, "(a)", timedelta(hours=1))])
    out = claim(proj, stub)
    assert out.returncode == 1 and out.stdout.strip() == "skip #5: taken by builder-f"
    assert posts(stub) == []


def test_claim_keeps_the_old_reading_when_the_open_briefs_cannot_be_read(proj, stub):
    """With the briefs unread nobody is judged stale: the old take still refuses the claim."""
    stub.serve(ISSUES, "FAIL")
    old = comment(1, "x", f"taken: builder-f {DAY} build (c)", iso(-timedelta(hours=96)))
    stub.serve(BRIEF, [old])
    stub.serve(PULLS, [built(20, "(a)", timedelta(hours=1))])
    out = claim(proj, stub)
    assert out.returncode == 1 and "taken by builder-f" in out.stdout and posts(stub) == []
