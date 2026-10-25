"""session.py next, ids, demand and push-check by capacity, overlap, numbers and claims (SPEC-0034).

Rules 1, 3, 4, 5, 6 and 7b; REQ-041 AC1, AC3, AC4, AC5, AC6 and AC7. A `gh` stub serves saved JSON
copies of the GitHub responses and a real git repository serves the default branch; no network."""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
from datetime import UTC, datetime, timedelta

import pytest
from test_session import FREE, ISSUES, REPO, SHA, Stub, comment, iso, issue, listing, posts, session

PULLS = f"repos/{REPO}/pulls"
DAY = datetime.now(UTC).strftime("%Y-%m-%d")


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    return repo


def brief(touches: str = "docs/**", priority: int | None = None, advances: str = "REQ-001") -> str:
    body = FREE.replace("Advances: REQ-001", f"Advances: {advances}")
    body = body.replace("Touches: docs/**", f"Touches: {touches}")
    return body + (f"Priority: {priority}\n" if priority else "")


def pr(number: int, brief_no: int | None = None, state: str = "open") -> dict:
    body = "Advances: REQ-001\n" + (f"Brief: #{brief_no}\n" if brief_no else "")
    return {
        "number": number, "state": state, "body": body, "title": "t", "labels": [],
        "user": {"login": "b"}, "created_at": iso(), "head": {"sha": SHA},
    }  # fmt: skip


def files(stub: Stub, number: int, *names: str) -> None:
    stub.serve(f"{PULLS}/{number}/files", [{"filename": n, "status": "added"} for n in names])


def reads(stub: Stub, number: int, before: list, after: list | None = None) -> None:
    """The comments of a brief before the take and, once the take is posted, after it."""
    stub.serve(f"{ISSUES}/{number}/comments", before, nth=1)
    mine = comment(90, "me", f"taken: s-me {DAY}")
    stub.serve(f"{ISSUES}/{number}/comments", [*before, mine] if after is None else after, nth=2)


def flow(proj, text: str) -> None:
    proj.write("agk.toml", f"[flow]\n{text}\n")


def nxt(proj, stub, who: str = "s-me"):
    return session(proj, stub, "next", "--session", who)


def base(proj, adrs: int = 3, specs: int = 0, reqs: tuple[str, ...] = ("REQ-001",)) -> None:
    """The default branch: requirements, ADRs and specs as files, and its ref origin/main."""
    out = {"docs/requirements.md": "".join(f"### {r} t\n\n- Status: planned\n\n" for r in reqs)}
    out |= {f"docs/adr/{n:04d}-a.md": "x\n" for n in range(1, adrs + 1)}
    out |= {f"docs/specs/{n:04d}-a.md": "x\n" for n in range(1, specs + 1)}
    proj.commit(out)
    proj.git("update-ref", "refs/remotes/origin/main", "HEAD")


# --- rule 1: the capacity (REQ-041 AC1) ------------------------------------------------------


def test_rule1_a_full_pool_prints_full_exits_1_and_posts_nothing(proj, stub):
    """REQ-041 AC1: only open pull requests with a Brief line count."""
    listing(stub, [issue(5, brief())])
    others = [pr(20), pr(21, 9, state="closed")]
    stub.serve(PULLS, [pr(10, 1), pr(11, 2), pr(12, 3), *others])
    out = nxt(proj, stub)
    assert (out.returncode, out.stdout) == (1, "full 3/3\n") and posts(stub) == []


def test_rule1_two_open_leave_room_and_the_table_sets_the_maximum(proj, stub):
    """REQ-041 AC1"""
    listing(stub, [issue(5, brief())])
    stub.serve(PULLS, [pr(10, 1), pr(11, 2)])
    files(stub, 10, "z/a")
    files(stub, 11, "z/b")
    reads(stub, 5, [])
    out = nxt(proj, stub)
    assert out.returncode == 0 and out.stdout.startswith("brief #5")
    flow(proj, "max_builders = 2")
    out = nxt(proj, stub)
    assert (out.returncode, out.stdout) == (1, "full 2/2\n")


@pytest.mark.parametrize(
    ("text", "setting"),
    [
        ("max_builders = 0", "max_builders"),
        ('max_builders = "7777"', "max_builders"),
        ("max_builders = true", "max_builders"),
        ("max_builders = 2.5", "max_builders"),
        ("claim_hours = 0", "claim_hours"),
        ('claim_hours = "8888"', "claim_hours"),
    ],
)
def test_rule1_an_invalid_value_is_refused_naming_the_setting_and_not_the_value(
    proj, stub, text, setting
):
    """REQ-041 AC1"""
    flow(proj, text)
    listing(stub, [issue(5, brief())])
    out = nxt(proj, stub)
    assert out.returncode == 2 and out.stdout.startswith("FAIL session: rule ")
    assert setting in out.stdout and "7777" not in out.stdout + out.stderr
    assert "8888" not in out.stdout + out.stderr and posts(stub) == []


def test_rule1_unreadable_pull_requests_stop_next_and_demand(proj, stub):
    """REQ-041 AC1"""
    listing(stub, [issue(5, brief())])
    stub.serve(PULLS, "FAIL")
    for args in (("next", "--session", "s-me"), ("demand",)):
        out = session(proj, stub, *args)
        assert out.returncode == 2 and out.stdout.startswith("FAIL session: rule 1")
    assert posts(stub) == []


# --- rule 3: the overlap and the order (REQ-041 AC3) -----------------------------------------


def test_rule3_an_overlapping_brief_is_skipped_with_its_reason_and_the_next_is_taken(proj, stub):
    """REQ-041 AC3"""
    listing(stub, [issue(5, brief("scripts/**")), issue(6, brief("docs/**, tests/kit/*.py"))])
    stub.serve(PULLS, [pr(20, 1), pr(21, 2)])
    files(stub, 20, "scripts/agk/session.py")
    files(stub, 21, "src/other.py")
    stub.serve(f"{ISSUES}/5/comments", [])
    reads(stub, 6, [])
    out = nxt(proj, stub)
    assert "skip #5: overlaps open pull request #20" in out.stdout.splitlines()
    assert out.stdout.splitlines()[-1].startswith("Sentence") or "brief #6" in out.stdout
    assert [p[1] for p in posts(stub)] == [f"{ISSUES}/6/comments"]


def test_rule3_a_shared_mechanical_path_never_counts_as_an_overlap(proj, stub):
    """REQ-041 AC3: changelog.d/ and the merge=union files of .gitattributes."""
    proj.write(".gitattributes", "docs/runs/decisions-log.md merge=union\n")
    listing(stub, [issue(5, brief("changelog.d/**, docs/runs/decisions-log.md"))])
    stub.serve(PULLS, [pr(20, 1)])
    files(stub, 20, "changelog.d/x.md", "docs/runs/decisions-log.md")
    reads(stub, 5, [])
    out = nxt(proj, stub)
    assert out.returncode == 0 and out.stdout.startswith("brief #5")


def test_rule3_a_taken_brief_without_a_pull_request_overlaps_by_its_touches(proj, stub):
    """REQ-041 AC3"""
    listing(stub, [issue(5, brief("src/**")), issue(6, brief("src/a.py")), issue(7, brief("lib/"))])
    stub.serve(PULLS, [])
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: s-other {DAY}")])
    stub.serve(f"{ISSUES}/6/comments", [])
    reads(stub, 7, [])
    out = nxt(proj, stub)
    assert "skip #5: taken by s-other" in out.stdout.splitlines()
    assert "skip #6: overlaps the taken brief #5" in out.stdout.splitlines()
    assert "brief #7" in out.stdout.splitlines()


def test_rule3_the_order_is_priority_then_the_oldest_issue_and_a_default_of_2(proj, stub):
    """REQ-041 AC3"""
    bodies = [(5, None), (6, 3), (7, 1), (8, 1), (9, 2)]
    listing(stub, [issue(n, brief(f"d{n}/", p)) for n, p in bodies])
    stub.serve(PULLS, [])
    for n, _ in bodies:
        stub.serve(f"{ISSUES}/{n}/comments", [], nth=1)
    reads(stub, 7, [])
    out = nxt(proj, stub)
    assert out.returncode == 0 and "brief #7" in out.stdout.splitlines()


# --- rule 4: the numbers (REQ-041 AC4) -------------------------------------------------------


def test_rule4_ids_count_the_default_branch_open_pull_requests_and_reservations(proj, stub):
    """REQ-041 AC4"""
    base(proj, adrs=3, specs=1)
    listing(stub, [issue(5, brief())])
    stub.serve(PULLS, [pr(20, 1), pr(21)])
    stub.serve(
        f"{PULLS}/20/files",
        [
            {"filename": "docs/adr/0006-x.md", "status": "added"},
            {"filename": "docs/adr/0002-a.md", "status": "modified"},
            {"filename": "docs/requirements.md", "status": "modified", "patch": "+### REQ-004 t"},
        ],
    )
    reserved = comment(1, "x", f"taken: s-other {DAY} reserves ADR-0009, SPEC-0007")
    stub.serve(f"{ISSUES}/5/comments", [reserved])
    out = session(proj, stub, "ids")
    assert out.returncode == 0, out.stdout
    assert json.loads(out.stdout) == {"req": "REQ-005", "spec": "0008", "adr": "0010"}
    assert out.stdout.count("\n") == 1 and posts(stub) == []


@pytest.mark.parametrize(
    ("advances", "reserves"),
    [("new", "REQ-002, SPEC-0001, ADR-0004"), ("REQ-001", "ADR-0004")],
)
def test_rule4_next_reserves_the_numbers_its_advances_implies_in_the_one_take(
    proj, stub, advances, reserves
):
    """REQ-041 AC4: Advances: new needs a requirement, a spec and an ADR; a build an ADR."""
    base(proj)
    stub.serve(PULLS, [])
    listing(stub, [issue(5, brief(advances=advances))])
    reads(stub, 5, [])
    assert nxt(proj, stub).returncode == 0
    assert posts(stub)[-1][2][1] == f"body=taken: s-me {DAY} reserves {reserves}"


# --- rule 5: the claims (REQ-041 AC5) --------------------------------------------------------


def test_rule5_an_expired_take_is_retaken_and_the_new_comment_says_retakes(proj, stub):
    """REQ-041 AC5: claim_hours is 4 by default."""
    base(proj)
    old = comment(1, "x", f"taken: s-other {DAY}", iso(-timedelta(hours=5)))
    listing(stub, [issue(5, brief())])
    stub.serve(PULLS, [])
    reads(stub, 5, [old])
    out = nxt(proj, stub)
    assert out.returncode == 0 and out.stdout.startswith("brief #5")
    assert posts(stub)[0][2][1] == f"body=taken: s-me {DAY} retakes reserves ADR-0004"


def test_rule5_a_young_take_and_a_take_with_a_builder_pull_request_stay_live(proj, stub):
    """REQ-041 AC5"""
    young = comment(1, "x", f"taken: s-other {DAY}", iso(-timedelta(hours=3)))
    old = comment(2, "y", f"taken: s-third {DAY}", iso(-timedelta(hours=30)))
    listing(stub, [issue(5, brief("a/")), issue(6, brief("b/"))])
    stub.serve(PULLS, [pr(20, 6)])
    files(stub, 20, "b/x")
    stub.serve(f"{ISSUES}/5/comments", [young])
    stub.serve(f"{ISSUES}/6/comments", [old])
    out = nxt(proj, stub)
    assert "skip #5: taken by s-other" in out.stdout and "skip #6: taken by s-third" in out.stdout
    assert out.returncode == 1 and posts(stub) == []


def test_rule5_claim_hours_sets_the_expiry(proj, stub):
    """REQ-041 AC5"""
    flow(proj, "claim_hours = 1")
    old = comment(1, "x", f"taken: s-other {DAY}", iso(-timedelta(hours=2)))
    listing(stub, [issue(5, brief())])
    stub.serve(PULLS, [])
    reads(stub, 5, [old])
    assert nxt(proj, stub).returncode == 0 and len(posts(stub)) == 1


def test_rule5_a_released_brief_is_free_at_once_and_is_not_a_retake(proj, stub):
    """REQ-041 AC5"""
    base(proj)
    taken = comment(1, "x", f"taken: s-other {DAY}")
    released = comment(2, "x", "released: s-other")
    listing(stub, [issue(5, brief())])
    stub.serve(PULLS, [])
    reads(stub, 5, [taken, released])
    out = nxt(proj, stub)
    assert out.returncode == 0 and out.stdout.startswith("brief #5")
    assert posts(stub)[0][2][1] == f"body=taken: s-me {DAY} reserves ADR-0004"


# --- rule 6: the demand (REQ-041 AC6) --------------------------------------------------------


@pytest.mark.parametrize(
    ("prs", "ready", "figures"),
    [
        ([pr(10, 1), pr(11, 2), pr(12, 3)], 2, {"ready": 2, "open": 3, "max": 3, "start": 0}),
        ([pr(10, 1)], 5, {"ready": 5, "open": 1, "max": 3, "start": 2}),
        ([], 1, {"ready": 1, "open": 0, "max": 3, "start": 1}),
        ([], 0, {"ready": 0, "open": 0, "max": 3, "start": 0}),
    ],
)
def test_rule6_demand_prints_the_figures_and_posts_nothing(proj, stub, prs, ready, figures):
    """REQ-041 AC6: start = min(ready, max - open), 0 when negative."""
    listing(stub, [issue(n, brief(f"d{n}/")) for n in range(30, 30 + ready)])
    stub.serve(PULLS, prs)
    for p in prs:
        files(stub, p["number"], "z/z")
    for n in range(30, 30 + ready):
        stub.serve(f"{ISSUES}/{n}/comments", [])
    out = session(proj, stub, "demand")
    assert out.returncode == 0 and json.loads(out.stdout) == figures
    assert out.stdout.count("\n") == 1 and posts(stub) == []


def test_rule6_demand_does_not_count_a_taken_or_an_overlapping_brief(proj, stub):
    """REQ-041 AC6"""
    listing(stub, [issue(5, brief("a/")), issue(6, brief("a/b")), issue(7, brief("c/"))])
    stub.serve(PULLS, [])
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "x", f"taken: s-other {DAY}")])
    for n in (6, 7):
        stub.serve(f"{ISSUES}/{n}/comments", [])
    out = session(proj, stub, "demand")
    assert json.loads(out.stdout) == {"ready": 1, "open": 0, "max": 3, "start": 1}


# --- rule 7b: push-check (REQ-041 AC7) -------------------------------------------------------


def origin(repo, tmp_path) -> None:
    bare = tmp_path.with_name(tmp_path.name + "-origin.git")  # outside the work tree
    subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "init", "-q", "--bare", str(bare)], check=True
    )
    repo.git("remote", "add", "origin", str(bare))
    repo.commit({"a.txt": "1\n", "b.txt": "1\n"})
    repo.git("push", "-q", "origin", "main")
    repo.git("checkout", "-q", "-b", "feature")
    repo.commit({"a.txt": "2\n"})
    repo.git("checkout", "-q", "main")


def test_rule7b_push_check_is_silent_and_exits_0_when_the_head_merges_cleanly(repo, stub, tmp_path):
    """REQ-041 AC7"""
    origin(repo, tmp_path)
    repo.commit({"b.txt": "2\n"})
    repo.git("push", "-q", "origin", "main")
    repo.git("checkout", "-q", "feature")
    out = session(repo, stub, "push-check")
    assert (out.returncode, out.stdout, out.stderr) == (0, "", "")


def test_rule7b_push_check_names_the_conflicting_files_and_exits_1(repo, stub, tmp_path):
    """REQ-041 AC7"""
    origin(repo, tmp_path)
    repo.commit({"a.txt": "3\n"})
    repo.git("push", "-q", "origin", "main")
    repo.git("checkout", "-q", "feature")
    before = repo.git("rev-parse", "HEAD")
    out = session(repo, stub, "push-check")
    assert out.returncode == 1 and out.stdout.strip() == "conflict: a.txt"
    assert repo.git("rev-parse", "HEAD") == before and repo.git("status", "--short") == ""


def test_rule7b_the_new_commands_take_no_option(proj, stub):
    """REQ-041 AC7"""
    for cmd in ("ids", "demand", "push-check"):
        assert session(proj, stub, cmd, "--session", "x").returncode == 2
