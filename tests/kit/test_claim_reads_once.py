"""A claim reads each GitHub listing once and only the recent pull requests (brief #1435, ADR-0601).

REQ-050. `claim` reads the pull requests as the plan does (`recent_pulls`: the open ones and the
closed ones of the larger of `claim_hours` and the plan's 14 days), never `pulls?state=all`; it
sets the in-run memo, so that the open-brief listing and each comment page are read once; it ends
with the plan's `reads:` line on standard error; and a primary rate-limit wait names its end in
local time. Its verdicts do not change. A `gh` stub serves recorded lists; no network."""

from __future__ import annotations

import re
from datetime import timedelta

import pytest
from test_session import ISSUES, REPO, Stub, claim_posts, comment, iso, issue, listing, posts
from test_session import session as run
from test_session_claim_overlap import alarm, red_fix_scene
from test_session_flow import DAY, PULLS, brief, flow, pr
from test_session_plan import changed, free

FILE = "scripts/agk/example.py"
READS = re.compile(r"reads: \d+ calls \(\d+ from cache\), \d+(\.\d+)? s(, writes: \d+)?")
LISTING = f"{ISSUES}?state=open&labels="


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    return repo


def claim(proj, stub, number: int = 6):
    return run(proj, stub, "claim", "--session", "s-me", "--brief", str(number))


def second(tmp_path) -> Stub:
    (tmp_path / "other").mkdir()
    return Stub(tmp_path / "other")


def endpoints(stub: Stub) -> list[str]:
    return [c[1] for c in stub.calls() if c[0] == "GET"]


def closed(number: int, brief_no: int, ago: timedelta) -> dict:
    """A pull request merged and last updated `ago` before now."""
    at = iso(-ago)
    return {**pr(number, brief_no, "closed"), "merged_at": at, "updated_at": at, "closed_at": at}


OLD = [closed(n, 3, timedelta(days=20 + n)) for n in range(30, 34)]  # closed before the window


def two_briefs(stub: Stub, pulls: list) -> None:
    listing(stub, [issue(5, brief("a/x.py")), issue(6, brief(FILE))])
    stub.serve(PULLS, pulls)
    changed(stub, 20, ("modified", "a/x.py"))
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: s-other {DAY}")])
    free(stub, 6)


# --- answers 1 and 2: recent pull requests only, each listing read once --------------------------


def test_a_claim_never_reads_every_pull_request_and_reads_each_listing_once(proj, stub):
    """REQ-050: brief #1435 answers 1 and 2."""
    two_briefs(stub, [pr(20, 5), *OLD])
    out = claim(proj, stub)
    assert out.returncode == 0 and out.stdout.strip() == "claimed #6", out.stdout + out.stderr
    got = endpoints(stub)
    assert not [e for e in got if "state=all" in e], got
    assert len([e for e in got if e.startswith(f"{PULLS}?state=open")]) == 1, got
    assert len([e for e in got if e.startswith(f"{PULLS}?state=closed")]) == 1, got
    assert len([e for e in got if e.startswith(LISTING)]) == 1, got
    again = [e for e in got if got.count(e) > 1]
    assert set(again) == {f"{ISSUES}/6/comments?per_page=100&page=1"}, got  # the take read back


def test_old_closed_pull_requests_change_no_verdict(proj, stub, tmp_path):
    """REQ-050: brief #1435 answer 7; the same verdict with and without the pull requests closed
    before the window."""
    two_briefs(stub, [pr(20, 5), *OLD])
    with_old = claim(proj, stub)
    other = second(tmp_path)
    two_briefs(other, [pr(20, 5)])
    without = claim(proj, other)
    assert (with_old.returncode, with_old.stdout) == (without.returncode, without.stdout)
    assert len(claim_posts(stub)) == len(claim_posts(other)) == 1


# --- answer 7: the edge cases ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ago", "said"),
    [(timedelta(hours=2), "skip #6: lost the take to s-other"), (timedelta(days=20), "claimed #6")],
)
def test_a_take_whose_pull_request_closed_inside_or_before_the_window(proj, stub, ago, said):
    """REQ-050: brief #1435 answer 7; an old take of another session whose pull request merged
    two hours ago still holds; one whose pull request merged twenty days ago does not."""
    two_briefs(stub, [closed(21, 6, ago), *OLD])
    old = comment(2, "x", f"taken: s-other {DAY}", iso(-timedelta(hours=30)))
    stub.serve(f"{ISSUES}/6/comments", [old])
    out = claim(proj, stub)
    assert out.stdout.strip() == said, out.stdout + out.stderr
    assert not [e for e in endpoints(stub) if "state=all" in e]


def test_a_stale_take_older_than_claim_hours_is_taken_over(proj, stub):
    """REQ-050: brief #1435 answer 7; a take older than `claim_hours` with no pull request."""
    two_briefs(stub, [*OLD])
    stub.serve(
        f"{ISSUES}/6/comments",
        [comment(2, "x", "taken: s-gone 2026-01-01", iso(-timedelta(days=3)))],
    )
    out = claim(proj, stub)
    assert out.returncode == 0 and out.stdout.strip() == "claimed #6", out.stdout + out.stderr
    assert claim_posts(stub)[0][2][1].splitlines()[0].endswith(" retakes")


def test_while_main_is_red_the_open_brief_listing_is_read_once(proj, stub):
    """REQ-050: brief #1435 answer 7; the alarm and its fix brief, one listing read."""
    red_fix_scene(stub)
    out = claim(proj, stub)
    assert out.returncode == 0 and out.stdout.strip() == "claimed #6", out.stdout + out.stderr
    got = endpoints(stub)
    assert len([e for e in got if e.startswith(LISTING)]) == 1, got
    assert len([e for e in got if e.startswith(f"{ISSUES}/9/comments")]) == 1, got
    assert alarm()["number"] == 9


@pytest.mark.parametrize("mode", ["full", "off"])
def test_full_reads_and_no_cache_give_the_same_verdicts(proj, stub, tmp_path, monkeypatch, mode):
    """REQ-050: brief #1435 answer 7; `github_reads = "full"` and `AGK_READ_CACHE=off`."""
    two_briefs(stub, [pr(20, 5), *OLD])
    plain = claim(proj, stub)
    if mode == "full":
        flow(proj, 'github_reads = "full"')
    else:
        monkeypatch.setenv("AGK_READ_CACHE", "off")
    other = second(tmp_path)
    two_briefs(other, [pr(20, 5), *OLD])
    again = claim(proj, other)
    assert (plain.returncode, plain.stdout) == (again.returncode, again.stdout), again.stderr
    assert not [e for e in endpoints(other) if "state=all" in e]


def test_personal_mode_reads_the_sidecars_briefs_the_same_way(proj, stub, tmp_path):
    """REQ-050: brief #1435 answer 7; a sidecar's settings change no read of a claim."""
    two_briefs(stub, [pr(20, 5), *OLD])
    team = claim(proj, stub)
    proj.write("agk.toml", '[personal]\nforge = "files"\n')
    other = second(tmp_path)
    two_briefs(other, [pr(20, 5), *OLD])
    personal = claim(proj, other)
    assert (team.returncode, team.stdout) == (personal.returncode, personal.stdout)
    assert endpoints(stub) == endpoints(other)


def test_a_read_that_fails_still_stops_the_claim(proj, stub):
    """REQ-050: brief #1435 answer 7; an unreadable pull request listing posts nothing."""
    two_briefs(stub, [])
    stub.serve(PULLS, "FAIL")
    out = claim(proj, stub)
    assert out.returncode != 0 and posts(stub) == []
    assert READS.fullmatch((out.stderr.strip().splitlines() or [""])[-1]), out.stdout


# --- answer 4: the reads line ---------------------------------------------------------------


def test_a_claim_ends_with_the_reads_line_of_the_plan(proj, stub):
    """REQ-050: brief #1435 answer 4."""
    two_briefs(stub, [pr(20, 5)])
    out = claim(proj, stub)
    assert out.returncode == 0, out.stdout + out.stderr
    last = out.stderr.strip().splitlines()[-1]
    assert READS.fullmatch(last), out.stderr
    assert "reads:" not in out.stdout


def test_a_take_posted_in_the_run_is_read_again_and_not_from_the_memo(proj, stub):
    """REQ-050: brief #1435 answer 2; the memo forgets the comments of a brief the run posted on,
    so that the take it posted is the one it reads back."""
    two_briefs(stub, [pr(20, 5)])
    stub.serve(f"{ISSUES}/6/comments", [], nth=1)
    mine = comment(3, "me", f"taken: s-me {DAY}")
    stub.serve(f"{ISSUES}/6/comments", [comment(2, "x", f"taken: s-rival {DAY}"), mine], nth=2)
    out = claim(proj, stub)
    assert out.stdout.strip() == "skip #6: lost the take to s-rival", out.stdout + out.stderr
