"""No command reads GitHub once per open brief: one shared read of what changed, and a call budget.

Brief #1314 builds (a) and (b), ADR-0555; REQ-050. Build (b) switches `stalls.py` and the sweep of
`conductor.py` (its per-brief loops) to the comment store, and holds the rest of the table.
`session.changed_comments` makes the one repository-wide `issues/comments?since=` read;
`conductor.py watch` judges its lines from it, and `session.py claim` answers unchanged briefs
from a comment store beside the read cache. `github_reads` of the `[flow]` table is `"delta"` by
default and `"full"` for the old per-item reads. On a recorded 650-brief fixture
(`fixtures/read_budget_650.json`, invented data) each switched command prints the same output in
both modes, through edits, deletions and new comments, and a warm run holds the budget of counted
calls (all but the 304s). The recorded double of test_session_plan_reads."""

from __future__ import annotations

import copy
import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl

import pytest
from test_session import REPO, SCRIPTS, SHA, clean_env
from test_session_flow import brief
from test_session_plan_reads import Double

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "read_budget_650.json").read_text())
ISSUES = f"repos/{REPO}/issues"
PULLS = f"repos/{REPO}/pulls"
MAIN = "d" * 40
NOW = datetime.now(UTC).replace(microsecond=0)
DAY = NOW.strftime("%Y-%m-%d")
SINCE = (NOW - timedelta(minutes=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
OLD = "2026-10-01T00:00:00Z"
BUDGET = {
    "watch quiet": 3,
    "watch one report": 4,
    "claim": 8,
    "review-queue": 6,
    "plan": 35,
    "stalls": 15,
}


def at(minutes: float) -> str:
    return (NOW - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


class World:
    """The fixture's repository, served to the double; edits, deletions and new comments."""

    def __init__(self, count: int | None = None) -> None:
        data = copy.deepcopy(FIXTURE)
        first, many = data["briefs"]["first"], count or data["briefs"]["count"]
        named = {int(k) for k in data["comments"]} | {p["brief"] for p in data["pulls"]} | {300}
        self.numbers = sorted(set(range(first, first + many)) | named)  # a smaller world keeps them
        self.taken = set(data["taken"])
        self.comments: dict[int, list[dict]] = {n: [] for n in self.numbers}
        for key, found in data["comments"].items():
            self.comments[int(key)] = [self.comment(int(key), c) for c in found]
        self.pulls = data["pulls"]
        for p in self.pulls:
            self.comments[p["number"]] = [self.comment(p["number"], c) for c in p["comments"]]

    @staticmethod
    def comment(number: int, c: dict) -> dict:
        body = c["body"].replace("{day}", DAY).replace("{short}", SHA[:7])
        return {
            "id": c["id"], "user": {"login": c["login"]}, "body": body,
            "created_at": at(c["ago"]), "updated_at": at(c.get("edited", c["ago"])),
            "issue_url": f"https://api.github.com/{ISSUES}/{number}",
        }  # fmt: skip

    def listing(self, n: int) -> dict:
        said = self.comments[n]
        labels = [{"name": "agk-brief"}] + ([{"name": "agk:taken"}] if n in self.taken else [])
        return {
            "number": n, "title": f"brief {n}", "body": brief(f"area{n}/**"), "labels": labels,
            "html_url": f"https://github.com/{REPO}/issues/{n}", "user": {"login": "owner"},
            "comments": len(said), "created_at": OLD,
            "updated_at": max([OLD] + [c["updated_at"] for c in said]),
        }  # fmt: skip

    def pull(self, p: dict) -> dict:
        return {
            "number": p["number"], "state": "open", "draft": False, "merged_at": None,
            "user": {"login": "builder"}, "head": {"sha": SHA, "ref": f"claude/brief-{p['brief']}"},
            "labels": [], "body": f"Advances: REQ-001\nBrief: #{p['brief']}\n",
            "created_at": at(120), "mergeable_state": "clean",
        }  # fmt: skip

    def serve(self, double: Double) -> None:
        double.serve(ISSUES, [self.listing(n) for n in self.numbers])
        double.serve(f"{ISSUES}@closed", [])
        double.serve(PULLS, [self.pull(p) for p in self.pulls])
        every = []
        for n, said in self.comments.items():
            double.serve(f"{ISSUES}/{n}/comments", said)
            every += said
        double.serve(f"{ISSUES}/comments", sorted(every, key=lambda c: c["updated_at"]))
        double.serve(f"repos/{REPO}", {"default_branch": "main"})
        double.serve(f"repos/{REPO}/branches/main", {"commit": {"sha": MAIN}})
        for head in (MAIN, SHA):
            double.serve(f"repos/{REPO}/commits/{head}/check-runs", {"check_runs": []})
            double.serve(f"repos/{REPO}/commits/{head}/status", {"state": "", "statuses": []})
        for p in self.pulls:
            double.serve(f"{PULLS}/{p['number']}/files", [])
        double.serve(f"repos/{REPO}/compare/{SHA}...main", {"ahead_by": 0, "files": []})
        for n in self.taken:  # the sweep's SILENT check of a taken brief (build (b))
            double.serve(f"repos/{REPO}/git/matching-refs/heads/claude/brief-{n}", [])
        for p in self.pulls:  # the router's facts of each pull request
            double.serve(f"{PULLS}/{p['number']}", self.pull(p))
            double.serve(f"{ISSUES}/{p['number']}/events", [])

    def edit(self, n: int, cid: int, body: str, minutes: float = 1) -> None:
        for c in self.comments[n]:
            if c["id"] == cid:
                c["body"], c["updated_at"] = body, at(minutes)

    def delete(self, n: int, cid: int) -> None:
        self.comments[n] = [c for c in self.comments[n] if c["id"] != cid]

    def add(self, n: int, cid: int, login: str, body: str, minutes: float = 1) -> None:
        said = {"id": cid, "login": login, "body": body, "ago": minutes}
        self.comments[n].append(self.comment(n, said))


@pytest.fixture
def double(tmp_path):
    return Double(tmp_path)


@pytest.fixture
def proj(repo, double):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write(
        "config/reviewers.yaml",
        "version: 1\nverdict_authors: [boss]\nspec_approvers: [owner]\n",
    )
    mode(repo, "delta")
    return repo


def mode(proj, reads: str | None) -> None:
    line = "" if reads is None else f'github_reads = "{reads}"\n'
    proj.write("agk.toml", f"[flow]\nconductor_poll_seconds = 1\nmax_builders = 4\n{line}")


def run(proj, double: Double, script: str, *args: str) -> subprocess.CompletedProcess:
    env = clean_env()
    env.update(
        PATH=f"{double.bin}{os.pathsep}{os.environ['PATH']}",
        GH_STUB_DIR=str(double.dir),
        AGK_READ_CACHE=str(double.cache),
    )
    double.forget()
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / script), *args],
        cwd=proj.root,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )


COMMANDS = {
    "watch": ("conductor.py", "watch", "--since", SINCE, "--once"),
    "claim taken": ("session.py", "claim", "--session", "s-me", "--brief", "102"),
    "claim free": ("session.py", "claim", "--session", "s-me", "--brief", "300"),
    "stalls": ("stalls.py",),  # build (b)
    "sweep": ("conductor.py", "sweep"),  # build (b): silent_line, slot_lines
}
SAME_AFTER = {"claim free", "stalls"}  # the edits change nothing these print


def said(out: subprocess.CompletedProcess) -> tuple[int, str]:
    """The exit and the output, with the sweep's ages in minutes masked: a 650-brief run takes
    seconds, so the minute can turn between two runs of one state (build (b))."""
    text = re.sub(r"(SILENT \d+ \S+ )\d+", r"\1<age>", out.stdout)
    return out.returncode, re.sub(r"\b\d+m\b", "<age>", text)


def comment_reads(double: Double) -> list[int]:
    found = [c[1].split("?")[0] for c in double.calls() if c[0] == "GET"]
    pre = f"{ISSUES}/"
    return [int(e[len(pre) : -len("/comments")]) for e in found if e.endswith("/comments")
            and e[len(pre) : -len("/comments")].isdigit()]  # fmt: skip


def brief_reads(double: Double) -> list[int]:
    """The per-issue comment pages asked of briefs, not of the open pull requests."""
    pulls = {p["number"] for p in FIXTURE["pulls"]}
    return [n for n in comment_reads(double) if n not in pulls]


def within(name: str, double: Double) -> None:
    counted = len(double.counted())
    assert counted <= BUDGET[name], f"{name}: budget {BUDGET[name]}, counted {counted}"


# --- answer 6: the same output in both modes -----------------------------------------------


@pytest.mark.parametrize("command", sorted(COMMANDS))
def test_each_switched_command_prints_the_same_in_both_modes(proj, double, command):
    """REQ-050: brief #1314 answers 3, 4 and 6 (edits, deletions and a new comment)."""
    world = World()
    world.serve(double)
    args = COMMANDS[command]
    mode(proj, "full")
    full = said(run(proj, double, *args))
    assert len(set(comment_reads(double))) >= 600  # the old reads: every brief's comments
    mode(proj, None)  # the default is delta
    assert said(run(proj, double, *args)) == full  # cold: the store fills
    assert said(run(proj, double, *args)) == full  # warm
    # The sweep's per-pull-request loops read through the ETag cache (304s), not the store.
    asked = brief_reads(double) if command == "sweep" else comment_reads(double)
    assert len(set(asked)) <= 3, asked
    world.edit(102, 21, f"taken: builder-q {DAY}")  # an edit in place
    world.delete(103, 32)  # a deletion lowers the count
    world.add(2003, 60, "builder", f"Report: {SHA[:7]} ready for review")  # a new comment
    world.serve(double)
    mode(proj, "full")
    after = said(run(proj, double, *args))
    mode(proj, "delta")
    assert said(run(proj, double, *args)) == after
    if command not in SAME_AFTER:
        assert after != full  # the change is seen, not merely the same in both modes


# --- answer 7: the call budget ---------------------------------------------------------------


def test_a_quiet_watch_poll_costs_at_most_three_and_one_new_report_four(proj, double):
    """REQ-050: brief #1314 answer 7 (`conductor.py watch --once`)."""
    world = World()
    world.serve(double)
    args = COMMANDS["watch"]
    first = run(proj, double, *args)
    assert first.returncode == 0, first.stderr
    assert first.stderr.splitlines().count("reads: delta") == 1
    assert run(proj, double, *args).stdout == first.stdout
    within("watch quiet", double)
    world.add(2005, 61, "builder", f"Report: {SHA[:7]} ready for review")
    world.serve(double)
    out = run(proj, double, *args)
    assert f"2005 Report: {SHA[:7]} ready for review" in out.stdout.splitlines()
    within("watch one report", double)
    assert comment_reads(double) == []  # no issue's own pages: the delta alone


@pytest.mark.parametrize("command", ["claim taken", "claim free"])
def test_a_warm_claim_costs_at_most_eight(proj, double, command):
    """REQ-050: brief #1314 answer 7 (`session.py claim`, with and without another take)."""
    World().serve(double)
    run(proj, double, *COMMANDS[command])
    run(proj, double, *COMMANDS[command])
    within("claim", double)
    assert len(comment_reads(double)) <= 3, comment_reads(double)  # requests too, 304s included


def test_a_warm_review_queue_costs_at_most_six(proj, double):
    """REQ-050: brief #1314 answer 7 (shared with #1309)."""
    World().serve(double)
    for _ in range(2):
        out = run(proj, double, "session.py", "review-queue", "--fingerprint")
        assert out.returncode == 0, out.stderr
    within("review-queue", double)


def test_a_warm_plan_costs_at_most_thirty_five(proj, double):
    """REQ-050: brief #1314 answer 7."""
    World().serve(double)
    for _ in range(2):
        out = run(proj, double, "session.py", "plan", "--json")
        assert out.returncode == 0, out.stderr
    within("plan", double)


def test_a_warm_stalls_run_costs_at_most_fifteen(proj, double):
    """REQ-050: brief #1314 answer 7 and build (b) (`stalls.py`)."""
    World().serve(double)
    for _ in range(2):
        out = run(proj, double, "stalls.py")
        assert out.returncode in (0, 3), out.stdout + out.stderr
    within("stalls", double)
    assert len(brief_reads(double)) <= 3, brief_reads(double)  # requests too, 304s included


@pytest.mark.parametrize("args", [("conductor.py", "sweep"), ("session.py", "plan", "--json")])
def test_a_warm_sweep_and_plan_ask_no_page_of_each_brief(proj, double, args):
    """REQ-050: brief #1314 answer 3, build (b) (the sweep's loops; the plan's pass, ADR-0548)."""
    World().serve(double)
    for _ in range(2):
        out = run(proj, double, *args)
        assert out.returncode == 0, out.stdout + out.stderr
    assert len(brief_reads(double)) <= 3, brief_reads(double)


def test_the_router_reads_no_brief_page(proj, double):
    """REQ-050: brief #1314 answer 7 (`route.py --all`; its 18-call budget is test_route_local)."""
    World().serve(double)
    out = run(proj, double, "route.py", "--all")
    assert out.returncode == 0, out.stdout + out.stderr
    assert brief_reads(double) == []


def test_a_broken_budget_names_the_command_the_budget_and_the_count(double):
    """REQ-050: brief #1314 answer 7 (the failure message)."""
    for k in range(5):
        with open(double.dir / "calls.log", "a") as log:
            log.write(json.dumps(["GET", f"{ISSUES}/{k}/comments", [], 200]) + "\n")
    with pytest.raises(AssertionError, match="watch quiet: budget 3, counted 5"):
        within("watch quiet", double)


# --- answer 4: the edge cases ----------------------------------------------------------------


def store_file(double: Double) -> Path:
    return double.cache / f"{REPO.replace('/', '__')}.comments.json"


class Fake:
    """GitHub in process for the store: an endpoint's list, `since` on `updated_at`, pages."""

    def __init__(self) -> None:
        self.data: dict[str, list] = {}
        self.calls: list[str] = []

    def gh(self, endpoint: str, *extra: str, method: str = "GET"):
        self.calls.append(endpoint)
        path, _, query = endpoint.partition("?")
        params = dict(parse_qsl(query))
        found = self.data.get(path)
        if found is None:
            return None
        if "since" in params:
            found = [c for c in found if c["updated_at"] >= params["since"]]
        size, page = int(params.get("per_page", 30)), int(params.get("page", 1))
        return found[(page - 1) * size : page * size]

    def put(self, n: int, said: list[dict]) -> None:
        self.data[f"{ISSUES}/{n}/comments"] = said
        listed = [{"number": n, "comments": len(said)}]
        self.data[ISSUES] = sorted(self.data.get(ISSUES, []) + listed, key=lambda i: i["number"])
        self.data[ISSUES] = list({i["number"]: i for i in self.data[ISSUES]}.values())
        every = [
            c for k, v in self.data.items() if k.endswith("/comments") and k != DELTA for c in v
        ]
        self.data[DELTA] = sorted(every, key=lambda c: c["updated_at"])


DELTA = f"{ISSUES}/comments"
LISTING = f"{ISSUES}?state=open&labels=agk-brief"


def stamped(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def note_of(n: int, cid: int, body: str, when: str) -> dict:
    url = f"https://api.github.com/{ISSUES}/{n}"
    return {"id": cid, "body": body, "created_at": when, "updated_at": when, "issue_url": url}


@pytest.fixture
def fake(tmp_path, monkeypatch):
    import session

    found = Fake()
    monkeypatch.setattr(session, "gh", found.gh)
    monkeypatch.setenv("AGK_READ_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(session, "CACHE", session.ReadCache())
    (tmp_path / "agk.toml").write_text("[flow]\n", encoding="utf-8")
    found.root = tmp_path
    return found


def a_run(fake: Fake, numbers: tuple[int, ...] = (7,)) -> dict[int, list]:
    """One run: the store made current, the listing, each issue's comments, the store saved."""
    import session

    store = session.CommentStore()
    session.STORE = store
    store.begin(fake.root, REPO)
    assert session.pages(LISTING) is not None
    found = {n: session.pages(f"{ISSUES}/{n}/comments") for n in numbers}
    if store.repo is not None:
        store.save(store.file(REPO))
    session.STORE = session.CommentStore()
    return found


def asked(fake: Fake, n: int) -> bool:
    return any(c.startswith(f"{ISSUES}/{n}/comments?") for c in fake.calls)


def test_an_edit_stamped_before_the_store_by_a_skewed_clock_is_still_read(fake):
    """REQ-050: brief #1314 answer 4 (equal or skewed timestamps; an edited comment)."""
    fake.put(7, [note_of(7, 1, "taken: builder-y 2026-11-15", OLD)])
    a_run(fake)
    stamp = json.loads(next((fake.root / "cache").glob("*.comments.json")).read_text())["stamp"]
    fake.put(7, [note_of(7, 1, "taken: builder-q 2026-11-15", stamped(stamp - 60))])
    fake.calls.clear()
    found = a_run(fake)
    assert [c["body"] for c in found[7]] == ["taken: builder-q 2026-11-15"]
    assert not asked(fake, 7)  # answered by the delta and the store


def test_a_comment_in_the_delta_and_the_store_is_never_doubled(fake):
    """REQ-050: brief #1314 answer 4 (a comment stamped in the same second as the store)."""
    when = stamped(time.time())
    fake.put(7, [note_of(7, 1, "taken: builder-y 2026-11-15", when)])
    a_run(fake)
    fake.calls.clear()
    found = a_run(fake)
    assert [c["id"] for c in found[7]] == [1] and not asked(fake, 7)


def test_a_deleted_comment_makes_its_brief_read_once(fake):
    """REQ-050: brief #1314 answer 4 (a deleted comment is not returned by `since`)."""
    fake.put(7, [note_of(7, 1, "taken: builder-y 2026-11-15", OLD), note_of(7, 2, "A note.", OLD)])
    a_run(fake)
    fake.put(7, [note_of(7, 2, "A note.", OLD)])
    fake.calls.clear()
    assert [c["id"] for c in a_run(fake)[7]] == [2] and asked(fake, 7)
    fake.calls.clear()
    assert [c["id"] for c in a_run(fake)[7]] == [2] and not asked(fake, 7)  # then from the store


def test_every_page_of_a_busy_delta_is_merged(fake):
    """REQ-050: brief #1314 answer 4 (more than one page of changes)."""
    numbers = tuple(range(1, 151))
    for n in numbers:
        fake.put(n, [note_of(n, n, f"note {n}", OLD)])
    a_run(fake, numbers)
    stamp = json.loads(next((fake.root / "cache").glob("*.comments.json")).read_text())["stamp"]
    for n in numbers:
        fake.put(n, [note_of(n, n, f"edited {n}", stamped(stamp + n))])
    fake.calls.clear()
    found = a_run(fake, numbers)
    assert any("page=2" in c for c in fake.calls if c.startswith(f"{DELTA}?"))
    assert all(found[n][0]["body"] == f"edited {n}" for n in numbers)
    assert not any(asked(fake, n) for n in numbers)


def test_a_comment_the_run_posts_makes_its_brief_read_from_github(fake):
    """REQ-050: brief #1314 answer 4 (the read after a take never comes from the store)."""
    import session

    fake.put(7, [])
    a_run(fake)
    session.STORE = store = session.CommentStore()
    store.begin(fake.root, REPO)
    session.pages(LISTING)
    store.forget(f"{ISSUES}/7/comments")  # what `gh` does on a POST to it
    fake.calls.clear()
    session.pages(f"{ISSUES}/7/comments")
    session.STORE = session.CommentStore()
    assert asked(fake, 7)


def test_an_unreadable_delta_leaves_the_store_off(fake):
    """REQ-050: brief #1314 answer 4 (never an empty list read as no comments)."""
    fake.put(7, [note_of(7, 1, "taken: builder-y 2026-11-15", OLD)])
    a_run(fake)
    del fake.data[DELTA]
    fake.calls.clear()
    assert len(a_run(fake)[7]) == 1 and asked(fake, 7)


@pytest.mark.parametrize("kept", ["{not json", '{"schema": 0, "stamp": 1, "issues": {}}', "[]"])
def test_a_corrupt_or_old_store_reads_in_full_once(proj, double, kept):
    """REQ-050: brief #1314 answer 4 (first run, a cleared, corrupt or old-schema store)."""
    world = World(count=40)
    world.serve(double)
    args = COMMANDS["claim taken"]
    mode(proj, "full")
    full = said(run(proj, double, *args))
    mode(proj, "delta")
    double.cache.mkdir(mode=0o700, exist_ok=True)
    store_file(double).write_text(kept)
    assert said(run(proj, double, *args)) == full
    assert json.loads(store_file(double).read_text())["schema"] == 1  # written again, whole
    found = [f for f in proj.root.glob("**/*.comments.json") if double.cache not in f.parents]
    assert found == []  # beside the read cache, never in the checkout


def test_an_unreadable_delta_reads_as_before_and_never_as_no_comments(proj, double):
    """REQ-050: brief #1314 answer 4 (GitHub unreadable: the same lines and exits)."""
    world = World(count=40)
    world.serve(double)
    for args in (COMMANDS[k] for k in ("watch", "claim taken", "stalls", "sweep")):
        mode(proj, "full")
        full = said(run(proj, double, *args))
        mode(proj, "delta")
        run(proj, double, *args)  # the store is written
        (double.dir / f"{ISSUES.replace('/', '__')}__comments.GET.json").unlink()
        assert said(run(proj, double, *args)) == full
        assert len(set(comment_reads(double))) >= 40  # read as before, not "no comments"
        world.serve(double)


def test_a_take_posted_by_the_claim_is_read_back_from_github(proj, double):
    """REQ-050: brief #1314 answer 4 (the store never answers the read after a post)."""
    World(count=40).serve(double)
    args = COMMANDS["claim free"]
    run(proj, double, *args)
    out = run(proj, double, *args)
    assert out.returncode == 0 and out.stdout.splitlines()[-1] == "claimed #300", out.stderr
    calls = double.calls()
    posted = [k for k, c in enumerate(calls) if c[0] == "POST" and c[1].endswith("/comments")]
    assert posted, calls
    after = [c[1].split("?")[0] for c in calls[posted[0] :] if c[0] == "GET"]
    assert f"{ISSUES}/300/comments" in after


@pytest.mark.parametrize("value", ['"fast"', '"FULL"', "true"])
def test_another_github_reads_value_is_refused_naming_the_setting(proj, double, value):
    """REQ-050: brief #1314 answer 5 (refusals name the setting, never the value)."""
    World(count=5).serve(double)
    proj.write("agk.toml", f"[flow]\ngithub_reads = {value}\n")
    for args in (COMMANDS["watch"], COMMANDS["claim taken"]):
        out = run(proj, double, *args)
        assert out.returncode != 0
        told = out.stdout + out.stderr
        assert "github_reads of the [flow] table must be delta or full" in told
        assert value.strip('"') not in told.replace("github_reads", "")


def test_full_mode_reads_no_delta_and_keeps_no_store(proj, double):
    """REQ-050: brief #1314 answer 5 (the old reads, by one line)."""
    World(count=20).serve(double)
    mode(proj, "full")
    for args in (COMMANDS["watch"], COMMANDS["claim taken"]):
        run(proj, double, *args)
        assert not any(c[1].startswith(f"{ISSUES}/comments") for c in double.calls())
    assert not store_file(double).exists()
    assert run(proj, double, *COMMANDS["watch"]).stderr.splitlines().count("reads: full") == 1
