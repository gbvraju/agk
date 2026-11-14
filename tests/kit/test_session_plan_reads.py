"""session.py plan reads only what a pass needs, milestone by milestone, and counts its reads.

Brief #1251 build (a), ADR-0529; REQ-050. The plan judges the open briefs from their listing alone
(stale, parked, shape, a `Depends-on` brief that no open listing holds is closed, with no GET per
dependency), then reads the comments of the briefs that pass, in the milestone order of ADR-0523,
only until the free slots are filled, besides the briefs that carry the take label `agk:taken` or
that an open pull request names. It reads the open pull requests and the closed ones updated in its
window, never every pull request ever (`state=all`). It ends with `reads: <n> calls (<m> from
cache), <s> s`, and `--json` carries the same. A recorded GitHub double and invented data only."""

from __future__ import annotations

import json
import re
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from test_session import ISSUES, REPO, Stub, comment, iso, issue, posts, session
from test_session_flow import DAY, PULLS, brief, merged

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "agk"))

MILESTONES = [
    {"number": 20 + k, "title": f"M{k + 1} demo", "due_on": f"2026-12-{k + 1:02d}T00:00:00Z"}
    for k in range(7)
]
READS = re.compile(r"reads: (\d+) calls \((\d+) from cache\), (\d+(?:\.\d+)?) s")


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    return repo


def at(number: int, body: str, milestone: dict | None, labels: tuple[str, ...] = ()) -> dict:
    found = {**issue(number, body), "milestone": milestone}
    return found | {"labels": [{"name": n} for n in labels]}


def pages_of(stub: Stub, issues: list[dict]) -> None:
    """The open-briefs listing served 100 at a time, as GitHub pages it."""
    chunks = [issues[i : i + 100] for i in range(0, len(issues), 100)]
    if not chunks or len(chunks[-1]) == 100:
        chunks.append([])
    for n, chunk in enumerate(chunks, start=1):
        stub.serve(ISSUES, chunk, nth=n)
    stub.serve(PULLS, [])


def big_plan(count: int = 600) -> list[dict]:
    """`count` briefs spread over seven milestones, latest numbers in the earliest milestone, each
    touching its own folder so that no two overlap."""
    out = []
    for k in range(count):
        number = 1000 + k
        milestone = MILESTONES[6 - (k * 7 // count)]
        out.append(at(number, brief(f"area{number}/**"), milestone))
    return out


def comment_reads(stub: Stub) -> list[str]:
    found = (c[1].split("?")[0] for c in stub.calls())
    return [e for e in found if re.search(r"/issues/\d+/comments$", e)]


def plan(proj, stub, *extra: str):
    out = session(proj, stub, "plan", *extra)
    assert out.returncode == 0, out.stdout + out.stderr
    assert posts(stub) == [] and all(c[0] == "GET" for c in stub.calls())
    return out


# --- answer 1: read in milestone order and stop early ------------------------------------------


def test_six_hundred_briefs_with_two_free_slots_cost_at_most_twenty_calls(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    briefs = big_plan()
    pages_of(stub, briefs)
    earliest = sorted(b["number"] for b in briefs if b["milestone"] is MILESTONES[0])
    for number in earliest[:4]:
        stub.serve(f"{ISSUES}/{number}/comments", [])
    out = plan(proj, stub, "--json")
    data = json.loads(out.stdout)
    assert [s["brief"] for s in data["start"]] == earliest[:2]  # today's full read starts these
    assert len(stub.calls()) <= 20, len(stub.calls())
    assert len(comment_reads(stub)) == 2  # only the briefs it starts, none of the other 598
    assert data["reads"]["calls"] == len(stub.calls())


def test_a_brief_whose_comments_hold_it_makes_the_walk_read_one_more(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 1\n")
    pages_of(stub, [at(5, brief("a/**"), MILESTONES[0]), at(6, brief("b/**"), MILESTONES[0])])
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "boss", f"taken: other {DAY}")])
    stub.serve(f"{ISSUES}/6/comments", [])
    out = plan(proj, stub, "--json")
    data = json.loads(out.stdout)
    assert data["start"] == [] or [s["brief"] for s in data["start"]] == [6]
    assert sorted(comment_reads(stub)) == [f"{ISSUES}/5/comments", f"{ISSUES}/6/comments"]


def test_a_later_milestone_is_read_only_while_slots_are_free(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    pages_of(
        stub,
        [
            at(5, brief("a/**"), MILESTONES[0]),
            at(6, brief("b/**"), MILESTONES[1]),
            at(7, brief("c/**"), MILESTONES[2]),
        ],
    )
    for n in (5, 6, 7):
        stub.serve(f"{ISSUES}/{n}/comments", [])
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert [s["brief"] for s in data["start"]] == [5, 6]
    assert f"{ISSUES}/7/comments" not in comment_reads(stub)


# --- answer 1: a dependency judged from the listing --------------------------------------------


def test_a_closed_dependency_is_judged_without_a_get(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    pages_of(stub, [at(6, brief("a/**") + "Depends-on: #3\n", MILESTONES[0])])
    stub.serve(f"{ISSUES}/6/comments", [])
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert [s["brief"] for s in data["start"]] == [6]
    assert not any(c[1] == f"{ISSUES}/3" for c in stub.calls())


def test_an_open_dependency_in_the_listing_waits_without_a_get(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    pages_of(
        stub,
        [
            at(5, brief("a/**"), MILESTONES[1]),
            at(6, brief("b/**") + "Depends-on: #5\n", MILESTONES[0]),
        ],
    )
    stub.serve(f"{ISSUES}/5/comments", [])
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert [s["brief"] for s in data["start"]] == [5]
    assert {"brief": 6, "why": "depends on #5, which is open"} in data["skipped"]
    assert not any(c[1] == f"{ISSUES}/5" for c in stub.calls())
    assert f"{ISSUES}/6/comments" not in comment_reads(stub)


# --- answer 2: the take label ------------------------------------------------------------------


def test_a_take_shown_by_the_label_holds_its_brief_and_a_slot(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    pages_of(
        stub,
        [
            at(5, brief("a/**"), MILESTONES[0]),
            at(6, brief("b/**"), MILESTONES[0]),
            at(9, brief("c/**"), MILESTONES[6], labels=("agk:taken",)),
        ],
    )
    for n in (5, 6):
        stub.serve(f"{ISSUES}/{n}/comments", [])
    stub.serve(f"{ISSUES}/9/comments", [comment(1, "someone", f"taken: builder-x {DAY}")])
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert [s["brief"] for s in data["start"]] == [5]  # builder-x holds the other slot
    assert data["running"] == [{"session": "builder-x", "brief": 9, "author": "someone"}]
    assert f"{ISSUES}/6/comments" not in comment_reads(stub)


def test_claim_adds_the_take_label(proj, stub):
    """REQ-050"""
    stub.serve(f"{ISSUES}/5", {"number": 5, "state": "open", "body": brief("a/**"), "labels": []})
    stub.serve(ISSUES, [issue(5, brief("a/**"))])
    stub.serve(PULLS, [])
    stub.serve(f"{ISSUES}/5/comments", [], nth=1)
    stub.serve(f"{ISSUES}/5/comments", [comment(9, "me", f"taken: s-me {DAY}")], nth=2)
    out = session(proj, stub, "claim", "--session", "s-me", "--brief", "5")
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.splitlines()[-1] == "claimed #5"
    sent = posts(stub)
    assert sent[0][1] == f"{ISSUES}/5/comments"
    assert sent[-1][1] == f"{ISSUES}/5/labels"
    assert "labels[]=agk:taken" in sent[-1][2]


# --- answer 4: the pull requests ---------------------------------------------------------------


def test_the_plan_reads_open_and_recently_closed_pull_requests_never_all(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    pages_of(stub, [at(5, brief("a/**"), MILESTONES[0])])
    stub.serve(PULLS, [merged(30, 4, timedelta(hours=1)) | {"updated_at": iso()}])
    stub.serve(f"{ISSUES}/5/comments", [])
    plan(proj, stub)
    pulls = [c[1] for c in stub.calls() if c[1].startswith(PULLS + "?")]
    assert pulls and not any("state=all" in p for p in pulls)
    assert any("state=open" in p for p in pulls)
    assert any("state=closed" in p and "sort=updated" in p for p in pulls)


def test_a_build_merged_before_the_window_is_found_on_the_briefs_timeline(proj, stub):
    """REQ-050"""
    proj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    body = brief("a/**") + "Builds: (a) one; (b) two\n"
    pages_of(stub, [at(5, body, MILESTONES[0])])
    old = {**merged(30, 5, timedelta(days=40)), "title": "brief #5 build (a)"}
    stub.serve(f"{ISSUES}/5/comments", [comment(1, "s", "taken: s-old 2026-10-01 build (a)")])
    event = {"number": 30, "title": old["title"], "state": "closed", "body": old["body"]}
    event["pull_request"] = {"merged_at": old["merged_at"]}
    stub.serve(f"{ISSUES}/5/timeline", [{"event": "cross-referenced", "source": {"issue": event}}])
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert [(s["brief"], s.get("build")) for s in data["start"]] == [(5, "b")]


# --- answer 5: the cost is printed -------------------------------------------------------------


def test_the_plan_prints_its_reads_and_the_data_carries_them(proj, stub):
    """REQ-050"""
    stub.serve(ISSUES, [at(5, brief("a/**"), MILESTONES[0])])
    stub.serve(PULLS, [])
    stub.serve(f"{ISSUES}/5/comments", [])
    out = plan(proj, stub)
    found = READS.fullmatch(out.stdout.rstrip().splitlines()[-1])
    assert found and int(found.group(1)) == len(stub.calls()) and found.group(2) == "0"
    data = json.loads(plan(proj, stub, "--json").stdout)
    assert set(data["reads"]) == {"calls", "cached", "seconds"}
    assert data["reads"]["cached"] == 0


def test_the_checklist_reports_the_last_plans_reads(tmp_path):
    """REQ-050"""
    import checklist

    saved = tmp_path / "agk-plan-reads.json"
    saved.write_text(json.dumps({"calls": 12, "cached": 0, "seconds": 1.5}), encoding="utf-8")
    assert checklist.plan_reads(saved) == "plan reads 12 calls (0 from cache), 1.5 s"
    assert checklist.plan_reads(tmp_path / "missing.json") is None


# --- build (b): the cache with conditional requests, the waits and the roll-over ----------------
# Brief #1251 build (b), answers 3, 3b, 3c and 6 (ADR-0548). The double below answers
# as GitHub does: each body carries an ETag, a request whose `If-None-Match` names it gets a 304
# with no body (which GitHub does not count against the rate limit), `since` keeps the items
# created or updated at or after it, and `page`/`per_page` page a list. A fixture `.N.json` serves
# from the Nth call of its endpoint on, until a later one replaces it.

DOUBLE = '''#!/usr/bin/env python3
"""A recorded GitHub double: ETags, 304s, `since` and pages; logs every call and its status."""
import hashlib, json, os, sys
from urllib.parse import parse_qs
args = sys.argv[1:]
root = os.environ["GH_STUB_DIR"]
at = args.index("--method")
method, endpoint, rest = args[at + 1], args[at + 2], args[at + 3:]
path, _, query = endpoint.partition("?")
params = {k: v[-1] for k, v in parse_qs(query).items()}
name = path.replace("/", "__")
count_file = os.path.join(root, "count." + method + "." + name)
n = int(open(count_file).read()) + 1 if os.path.exists(count_file) else 1
open(count_file, "w").write(str(n))
asked = [rest[i + 1] for i, a in enumerate(rest) if a == "-H" and i + 1 < len(rest)]
match = [h.split(":", 1)[1].strip() for h in asked if h.lower().startswith("if-none-match:")]
def log(status):
    with open(os.path.join(root, "calls.log"), "a") as out:
        out.write(json.dumps([method, endpoint, rest, status]) + "\\n")
if method != "GET":
    log(201)
    made = os.path.join(root, name + "." + method + ".json")
    print(open(made).read() if os.path.exists(made) else "{}")
    sys.exit(0)
one = name + "@" + params.get("state", "")
if "state" in params and os.path.exists(os.path.join(root, one + ".GET.json")):
    name = one  # a fixture of one state: `issues?state=all` alone
chosen = None
for k in range(n, 0, -1):
    candidate = os.path.join(root, name + "." + method + "." + str(k) + ".json")
    if os.path.exists(candidate):
        chosen = candidate
        break
plain = os.path.join(root, name + "." + method + ".json")
chosen = chosen or (plain if os.path.exists(plain) else None)
if chosen is None:
    log(404)
    sys.stderr.write("gh: Not Found (HTTP 404)\\n")
    sys.exit(1)
data = json.load(open(chosen))
if isinstance(data, list):
    if "since" in params:
        data = [x for x in data if max(x.get("updated_at") or "", x.get("created_at") or "")
                >= params["since"]]
    size = int(params.get("per_page", 30))
    page = int(params.get("page", 1))
    data = data[(page - 1) * size : page * size]
text = json.dumps(data)
etag = '"' + hashlib.sha1(text.encode()).hexdigest()[:16] + '"'
head = "-i" in rest
if etag in match:
    log(304)
    if head:
        sys.stdout.write("HTTP/2.0 304 Not Modified\\r\\nEtag: " + etag + "\\r\\n\\r\\n")
    sys.stderr.write("gh: HTTP 304\\n")
    sys.exit(1)
log(200)
if head:
    sys.stdout.write("HTTP/2.0 200 OK\\r\\nContent-Type: application/json\\r\\nEtag: " + etag
                     + "\\r\\n\\r\\n")
sys.stdout.write(text)
'''


class Double(Stub):
    """The recorded double; `counted()` are the calls GitHub would count (all but the 304s)."""

    def __init__(self, tmp: Path) -> None:
        super().__init__(tmp)
        (self.bin / "gh").write_text(DOUBLE, encoding="utf-8")
        self.cache = tmp / "cache"

    def counted(self) -> list[list]:
        return [c for c in self.calls() if c[3] != 304]

    def forget(self) -> None:
        """A new pass: the call log starts again, the fixtures and the cache stay."""
        (self.dir / "calls.log").unlink(missing_ok=True)


def run(proj, double: Double, *args: str, timeout: int = 60):
    import os
    import subprocess  # nosec B404 - fixed argument list, no shell

    from test_session import SCRIPTS, clean_env

    env = clean_env()
    env.update(
        PATH=f"{double.bin}{os.pathsep}{os.environ['PATH']}",
        GH_STUB_DIR=str(double.dir),
        AGK_READ_CACHE=str(double.cache),
    )
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "session.py"), *args],
        cwd=proj.root,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


@pytest.fixture
def double(tmp_path):
    return Double(tmp_path)


@pytest.fixture
def dproj(repo, double):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    return repo


def big_double(double: Double, count: int = 600) -> tuple[list[dict], list[int]]:
    briefs = big_plan(count)
    for b in briefs:
        b["updated_at"] = b["created_at"] = "2026-11-01T00:00:00Z"
    double.serve(ISSUES, briefs)
    double.serve(PULLS, [])
    double.serve(f"{ISSUES}/comments", [])
    earliest = sorted(b["number"] for b in briefs if b["milestone"] is MILESTONES[0])
    for number in earliest[:4]:
        double.serve(f"{ISSUES}/{number}/comments", [])
    return briefs, earliest


def dplan(proj, double, *extra: str) -> dict:
    out = run(proj, double, "plan", "--json", *extra)
    assert out.returncode == 0, out.stdout + out.stderr
    assert all(c[0] == "GET" for c in double.calls())
    return json.loads(out.stdout)


def test_a_cold_plan_costs_at_most_twenty_calls_and_a_warm_one_at_most_five(dproj, double):
    """REQ-050"""
    dproj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    _, earliest = big_double(double)
    cold = dplan(dproj, double)
    assert [s["brief"] for s in cold["start"]] == earliest[:2]
    assert len(double.counted()) <= 20, len(double.counted())
    double.forget()
    warm = dplan(dproj, double)
    assert [s["brief"] for s in warm["start"]] == earliest[:2]  # the same starts
    assert len(double.counted()) <= 5, double.counted()
    assert warm["reads"]["cached"] >= 1


def test_a_304_reuses_the_cached_body(dproj, double):
    """REQ-050"""
    dproj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    double.serve(ISSUES, [at(5, brief("a/**"), MILESTONES[0])])
    double.serve(PULLS, [])
    double.serve(f"{ISSUES}/5/comments", [])
    double.serve(f"{ISSUES}/comments", [])
    first = dplan(dproj, double)
    double.forget()
    second = dplan(dproj, double)
    listing = [c for c in double.calls() if c[1].startswith(f"{ISSUES}?state=open")]
    assert listing and all(c[3] == 304 for c in listing)  # the body came from the cache
    assert any(a.startswith("If-None-Match: ") for c in listing for a in c[2])
    assert [s["brief"] for s in second["start"]] == [s["brief"] for s in first["start"]] == [5]


def test_a_take_posted_between_passes_is_read_again(dproj, double):
    """REQ-050: the repository-wide `since` read names the brief whose comments changed, and only
    that brief's comments are asked again."""
    dproj.write("agk.toml", "[flow]\nmax_builders = 1\n")
    double.serve(ISSUES, [at(5, brief("a/**"), MILESTONES[0]), at(6, brief("b/**"), MILESTONES[0])])
    double.serve(PULLS, [])
    double.serve(f"{ISSUES}/comments", [])
    double.serve(f"{ISSUES}/5/comments", [])
    double.serve(f"{ISSUES}/6/comments", [])
    assert [s["brief"] for s in dplan(dproj, double)["start"]] == [5]
    take = comment(40, "someone", f"taken: other {DAY}", "2999-01-01T00:00:00Z")
    take["issue_url"] = f"https://api.github.com/{ISSUES}/5"
    double.serve(f"{ISSUES}/5/comments", [take], nth=2)
    double.serve(f"{ISSUES}/comments", [take])  # the first `since` read is the second pass's
    double.forget()
    again = dplan(dproj, double)
    assert 5 not in [s["brief"] for s in again["start"]]
    asked = [c[1] for c in double.calls() if "/comments?" in c[1] and "/issues/5/" in c[1]]
    assert asked  # brief 5 changed, so its comments were asked again


# --- answer 3b: the waits read only what is new ------------------------------------------------

CONDUCTOR_ISSUE = {
    "number": 204,
    "title": "Conductor: assignments",
    "comments": 1,
    "labels": [{"name": "agk-conductor"}],
}
OLD = comment(10, "boss", "Assign: s-other #3", "2026-11-14T10:00:00Z")
PR = f"repos/{REPO}/pulls/7"


def waiting(double: Double, conductor: list | None = None) -> None:
    from test_session import pull

    double.serve(PR, pull())
    double.serve(f"{ISSUES}/7/comments", [comment(5, "builder", "Report: a1b2c3d ready")])
    double.serve(ISSUES, [CONDUCTOR_ISSUE])
    double.serve(f"{ISSUES}/204/comments", conductor or [OLD])


def test_a_quiet_minute_of_a_waiting_builder_costs_no_counted_call_after_the_first(dproj, double):
    """REQ-050"""
    waiting(double)
    out = run(dproj, double, "watch", "--pr", "7", "--session", "s-me", "--interval", "0",
              "--timeout", "3")
    assert out.returncode == 3 and out.stdout.splitlines() == ["timeout"], out.stdout
    calls = double.calls()
    assert len([c for c in calls if c[1] == PR]) >= 3  # it polled
    seen: set[str] = set()
    for call in calls:
        assert call[3] == 304 or call[1] not in seen, call  # only an endpoint's first read counts
        seen.add(call[1])
    since = [c[1] for c in calls if "since=" in c[1]]
    assert since and all("/issues/7/comments?since=" in e or "/204/comments?since=" in e
                         for e in since)


def test_a_new_tell_is_seen_within_one_poll(dproj, double):
    """REQ-050"""
    waiting(double)
    tell = comment(11, "boss", "Tell: s-me #52 merged, rebase", "2026-11-14T10:05:00Z")
    double.serve(f"{ISSUES}/204/comments", [OLD, tell], nth=4)
    out = run(dproj, double, "watch", "--pr", "7", "--session", "s-me", "--interval", "0",
              "--timeout", "20")
    assert out.returncode == 0 and out.stdout.splitlines() == ["tell #52 merged, rebase"]
    reads = [c for c in double.calls() if c[1].startswith(f"{ISSUES}/204/comments")]
    assert len(reads) == 4 and reads[-1][3] == 200  # the first read that could see it ended it


def test_the_wait_follows_a_rolled_over_conductor_issue(dproj, double):
    """REQ-050: answer 3c, a `Continued in #<n>` by a listed author moves the reads."""
    waiting(double)
    link = comment(12, "boss", "Continued in #300", "2026-11-14T10:06:00Z")
    double.serve(f"{ISSUES}/204/comments", [OLD, link], nth=3)
    tell = comment(13, "boss", "Tell: s-me stop and look", "2026-11-14T10:07:00Z")
    double.serve(f"{ISSUES}/300/comments", [tell])
    out = run(dproj, double, "watch", "--pr", "7", "--session", "s-me", "--interval", "0",
              "--timeout", "20")
    assert out.returncode == 0 and out.stdout.splitlines() == ["tell stop and look"]


def test_the_assign_wait_follows_a_rolled_over_conductor_issue(dproj, double):
    """REQ-050"""
    dproj.write("agk.toml", '[flow]\nassign = "conductor"\n')
    asked = comment(20, "builder", "Request: s-me new", "2026-11-14T10:00:00Z")
    double.serve(ISSUES, [CONDUCTOR_ISSUE])
    double.serve(f"{ISSUES}/204/comments", [asked])
    link = comment(21, "boss", "Continued in #300", "2026-11-14T10:06:00Z")
    double.serve(f"{ISSUES}/204/comments", [asked, link], nth=3)
    double.serve(f"{ISSUES}/300/comments", [comment(22, "boss", "Assign: s-me #77")])
    out = run(dproj, double, "watch", "--assign", "s-me", "--interval", "0", "--timeout", "20")
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.splitlines()[-1] == "assign #77"


def test_the_poll_interval_backs_off_while_nothing_changes_and_resets_on_a_change():
    """REQ-050"""
    import session

    pause = 60.0
    for _ in range(5):
        pause = session.backoff(pause, 60.0, changed=False)
    assert pause == 300.0
    assert session.backoff(pause, 60.0, changed=True) == 60.0
    assert session.backoff(0.0, 0.0, changed=False) == 0.0
    assert session.backoff(600.0, 600.0, changed=False) == 600.0  # never under the base


# --- answer 3c: the conductor issue rolls over -------------------------------------------------


def test_rollover_opens_a_new_issue_links_it_and_closes_the_old(dproj, double):
    """REQ-050"""
    double.serve(ISSUES, [{**CONDUCTOR_ISSUE, "comments": 501}])
    double.serve(f"{ISSUES}/204/comments", [OLD])
    double.serve(ISSUES, {"number": 300}, method="POST")
    out = run(dproj, double, "rollover")
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.splitlines() == ["rolled over #204 to #300"]
    sent = [c for c in double.calls() if c[0] != "GET"]
    assert [c[:2] for c in sent] == [
        ["POST", ISSUES],
        ["POST", f"{ISSUES}/204/comments"],
        ["PATCH", f"{ISSUES}/204"],
    ]
    assert "labels[]=agk-conductor" in sent[0][2] and "title=Conductor: assignments" in sent[0][2]
    assert "body=Continued in #300\n\nWho: AGK" in sent[1][2] and "state=closed" in sent[2][2]


def test_rollover_waits_under_the_limit_and_while_a_request_waits(dproj, double):
    """REQ-050"""
    double.serve(ISSUES, [{**CONDUCTOR_ISSUE, "comments": 500}])
    double.serve(f"{ISSUES}/204/comments", [OLD])
    out = run(dproj, double, "rollover")
    assert out.stdout.splitlines() == ["rollover: #204 has 500 comments, at most 500; no change"]
    double.serve(ISSUES, [{**CONDUCTOR_ISSUE, "comments": 501}])
    double.serve(f"{ISSUES}/204/comments", [OLD, comment(30, "builder", "Request: s-me new")])
    out = run(dproj, double, "rollover")
    assert out.stdout.splitlines() == [
        "rollover: not now, a Request: waits for its Assign: on #204"
    ]
    assert all(c[0] == "GET" for c in double.calls())


# --- answer 6: the conductor re-plans only on a change -----------------------------------------


def test_the_re_plan_reuses_the_last_plan_until_something_changes(dproj, double):
    """REQ-050"""
    dproj.write("agk.toml", "[flow]\nmax_builders = 2\n")
    double.serve(ISSUES, [at(5, brief("a/**"), MILESTONES[0])])
    double.serve(PULLS, [])
    double.serve(f"{ISSUES}/5/comments", [])
    double.serve(f"{ISSUES}/comments", [])
    double.serve(f"{ISSUES}@all", [{"number": 5, "updated_at": "2026-11-14T10:00:00Z"}])
    first = dplan(dproj, double, "--if-changed")
    assert "unchanged" not in first and [s["brief"] for s in first["start"]] == [5]
    double.forget()
    second = dplan(dproj, double, "--if-changed")
    assert second["unchanged"] and second["start"] == first["start"]
    assert double.counted() == []  # one read of the newest change, a 304
    words = run(dproj, double, "plan", "--if-changed").stdout.splitlines()
    assert words[0].startswith("plan: unchanged since ")
    newer = [{"number": 9, "updated_at": "2026-11-14T11:00:00Z"}]
    double.serve(f"{ISSUES}@all", newer, nth=4)
    double.forget()
    third = dplan(dproj, double, "--if-changed")
    assert "unchanged" not in third
    assert any(c[1].startswith(f"{ISSUES}?state=open") for c in double.calls())


# --- the cache folder is this user's own (finding 2 on 729b5a8) --------------------------------


@pytest.mark.skipif(not hasattr(__import__("os"), "getuid"), reason="POSIX owners and modes")
def test_a_cache_folder_of_another_owner_or_open_to_others_is_not_used(tmp_path, monkeypatch):
    """REQ-050"""
    import os

    import session

    own = tmp_path / "own"
    own.mkdir(mode=0o700)
    assert session.private_folder(own)
    opened = tmp_path / "opened"
    opened.mkdir()
    opened.chmod(0o777)
    assert not session.private_folder(opened)
    link = tmp_path / "link"
    link.symlink_to(own, target_is_directory=True)
    assert not session.private_folder(link)
    monkeypatch.setattr(os, "getuid", lambda: own.stat().st_uid + 1)
    assert not session.private_folder(own)  # another user made it first


@pytest.mark.skipif(not hasattr(__import__("os"), "getuid"), reason="POSIX owners and modes")
def test_a_cache_folder_open_to_others_reads_without_the_cache(dproj, double):
    """REQ-050"""
    double.cache.mkdir()
    double.cache.chmod(0o777)
    double.serve(ISSUES, [at(5, brief("a/**"), MILESTONES[0])])
    double.serve(PULLS, [])
    double.serve(f"{ISSUES}/5/comments", [])
    dplan(dproj, double)
    double.forget()
    dplan(dproj, double)
    assert not any(a.startswith("If-None-Match") for c in double.calls() for a in c[2])
    assert list(double.cache.iterdir()) == []


def test_a_new_cache_folder_is_made_private(dproj, double):
    """REQ-050"""
    double.serve(ISSUES, [at(5, brief("a/**"), MILESTONES[0])])
    double.serve(PULLS, [])
    double.serve(f"{ISSUES}/5/comments", [])
    dplan(dproj, double)
    assert double.cache.is_dir() and any(double.cache.iterdir())
    if hasattr(__import__("os"), "getuid"):
        assert double.cache.stat().st_mode & 0o077 == 0
