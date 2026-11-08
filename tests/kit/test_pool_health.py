"""The pool's health and the shorter leases (brief #776 build (b) and its 09:36Z addition; REQ-041).

The health issues `No live conductor` and `Builder pool down` from the router's event job, the
10-minute leases and the 5-minute bound of the two watches. Saved comments through a `gh` stub on
`PATH` that tells one issues query from another; invented names, no network.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import conductor  # noqa: E402
import session as session_script  # noqa: E402

REPO = "acme/widgets"
ISSUES = f"repos/{REPO}/issues"
PLAN = f"{ISSUES}/61/comments"
ASSIGNMENTS = f"{ISSUES}/204/comments"
BRIEFS = f"{ISSUES}?state=open&labels=agk-brief"
HEALTH = f"{ISSUES}?state=open&labels=agk-health"
PULLS = f"repos/{REPO}/pulls"
ON = '[flow]\nbuilder_start = "assign"\nbuilder_slots = 3\nplan_issue = 61\n'
BRIEF = {"number": 9, "title": "A brief", "labels": [{"name": "agk-brief"}]}

STUB = '''#!/usr/bin/env python3
"""A gh stub: GET answers come from fixtures.json by the endpoint without its paging; every call is
logged; a write answers {}."""
import json, os, re, sys
args = sys.argv[2:]
method, endpoint, rest, skip = "GET", None, [], False
for i, a in enumerate(args):
    if skip:
        skip = False
    elif a in ("--method", "-X"):
        method, skip = args[i + 1], True
    elif a == "-f":
        rest.append(args[i + 1]); skip = True
    elif a == "-H":
        skip = True
    elif not a.startswith("-") and endpoint is None:
        endpoint = a
root = os.environ["GH_STUB_DIR"]
with open(os.path.join(root, "calls.log"), "a") as log:
    log.write(json.dumps([method, endpoint, rest]) + "\\n")
if method != "GET":
    print("{}")
    sys.exit(0)
fixtures = json.load(open(os.path.join(root, "fixtures.json")))
key = re.sub(r"[?&]per_page=\\d+(&page=\\d+)?$", "", endpoint)
value = fixtures.get(key, fixtures.get(key.split("?")[0]))
if value is None or value == "FAIL":
    sys.exit(1)
print(json.dumps(value))
'''


def stamp(minutes: float) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def said(cid: int, login: str, body: str) -> dict:
    return {"id": cid, "user": {"login": login}, "body": body, "created_at": stamp(1)}


def live(cid: int = 1, who: str = "c1", minutes: float = 1, login: str = "boss") -> dict:
    return said(cid, login, f"Conductor: active {stamp(minutes)} {who}")


def slot(name: str, cid: int, minutes: float = 1, state: str = "active") -> dict:
    return said(cid, "boss", f"Slot: {state} {stamp(minutes)} {name} run{cid}")


class Stub:
    def __init__(self, tmp: Path) -> None:
        self.dir = tmp / "stub"
        self.dir.mkdir()
        self.bin = tmp / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(STUB, encoding="utf-8")
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        self.fixtures: dict = {
            f"repos/{REPO}/labels": [],
            f"{ISSUES}?state=open&labels=agk-conductor": [{"number": 204, "title": "Assignments"}],
            BRIEFS: [BRIEF],
            HEALTH: [],
            PULLS: [],
            PLAN: [live()],
            ASSIGNMENTS: [slot("s1", 2), slot("s2", 3), slot("s3", 4)],
        }

    def calls(self) -> list[list]:
        log = self.dir / "calls.log"
        return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []

    def writes(self) -> list[list]:
        return [c for c in self.calls() if c[0] != "GET"]


@pytest.fixture
def stub(tmp_path: Path) -> Stub:
    return Stub(tmp_path)


@pytest.fixture
def proj(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "config").mkdir(parents=True)
    (root / "config" / "reviewers.yaml").write_text(
        "version: 1\nverdict_authors: [boss]\nspec_approvers: [owner]\n", encoding="utf-8"
    )
    (root / "agk.toml").write_text(ON, encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)  # nosec B603 B607
    return root


def router(proj: Path, stub: Stub, tmp: Path, *args: str):
    """The router woken by a comment on an issue that is no pull request (a `Request:` line)."""
    (stub.dir / "fixtures.json").write_text(json.dumps(stub.fixtures), encoding="utf-8")
    event = tmp / "event.json"
    event.write_text(json.dumps({"issue": {"number": 204}}), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "AGK_BASE", "CI")}
    env.update(
        PATH=f"{stub.bin}{os.pathsep}{os.environ['PATH']}",
        GH_STUB_DIR=str(stub.dir),
        GITHUB_EVENT_NAME="issue_comment",
        GITHUB_EVENT_PATH=str(event),
        GITHUB_REPOSITORY=REPO,
        AGK_PIPELINE_FILE=str(tmp / "pipeline.json"),
    )
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "route.py"), *args],
        cwd=proj,
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def opened(stub: Stub) -> list[str]:
    return [
        next(f[6:] for f in c[2] if f.startswith("title="))
        for c in stub.writes()
        if c[0] == "POST" and c[1] == ISSUES
    ]


# --- the health issue (answer 5) ---------------------------------------------------------------


def test_a_dead_conductor_with_work_waiting_opens_the_issue(proj, stub, tmp_path):
    """REQ-041: no valid lease, an open brief: one issue, with its label."""
    stub.fixtures[PLAN] = []
    out = router(proj, stub, tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr
    assert opened(stub) == ["No live conductor"]
    made = next(c for c in stub.writes() if c[1] == ISSUES)
    assert "labels[]=agk-health" in made[2]
    assert any(c[0] == "POST" and c[1].endswith("/labels") for c in stub.writes())


def test_an_open_ready_pull_request_is_work_for_the_conductor(proj, stub, tmp_path):
    """REQ-041"""
    stub.fixtures[PLAN] = []
    stub.fixtures[BRIEFS] = []
    stub.fixtures[PULLS] = [{"number": 7, "draft": False}]
    router(proj, stub, tmp_path)
    assert opened(stub) == ["No live conductor"]


def test_an_expired_or_released_or_strangers_marker_is_no_live_conductor(proj, stub, tmp_path):
    """REQ-041: 11 minutes old, released or by an unlisted account: each is no valid lease."""
    for marker in (
        live(minutes=11),
        said(1, "boss", f"Conductor: released {stamp(1)} c1"),
        live(login="stranger"),
    ):
        stub.fixtures[PLAN] = [marker]
        (stub.dir / "calls.log").unlink(missing_ok=True)
        router(proj, stub, tmp_path)
        assert opened(stub) == ["No live conductor"], marker


def test_more_than_a_third_of_the_slots_dead_opens_the_pool_issue(proj, stub, tmp_path):
    """REQ-041: of 3 slots, 2 have no valid lease (2 > 3 / 3)."""
    stub.fixtures[ASSIGNMENTS] = [slot("s1", 2), slot("s2", 3, minutes=11)]
    router(proj, stub, tmp_path)
    assert opened(stub) == ["Builder pool down"]
    made = next(c for c in stub.writes() if c[1] == ISSUES)
    body = next(f for f in made[2] if f.startswith("body="))
    assert "s2" in body and "s3" in body and "s1," not in body


def test_a_third_of_the_slots_dead_opens_nothing(proj, stub, tmp_path):
    """REQ-041: 1 of 3 is not more than a third."""
    stub.fixtures[ASSIGNMENTS] = [slot("s1", 2), slot("s2", 3)]
    router(proj, stub, tmp_path)
    assert stub.writes() == []


def test_no_work_waiting_opens_nothing(proj, stub, tmp_path):
    """REQ-041: a draft is not work for the conductor, and nothing is open for the slots."""
    stub.fixtures[PLAN] = []
    stub.fixtures[ASSIGNMENTS] = []
    stub.fixtures[BRIEFS] = []
    stub.fixtures[PULLS] = [{"number": 7, "draft": True}]
    router(proj, stub, tmp_path)
    assert stub.writes() == []


def test_the_open_issue_is_updated_only_when_its_text_changes(proj, stub, tmp_path):
    """REQ-041: one issue per kind; the same state writes nothing."""
    stub.fixtures[ASSIGNMENTS] = [slot("s1", 2)]
    router(proj, stub, tmp_path)
    made = next(c for c in stub.writes() if c[1] == ISSUES)
    body = next(f[5:] for f in made[2] if f.startswith("body="))
    (stub.dir / "calls.log").unlink()
    stub.fixtures[HEALTH] = [{"number": 88, "title": "Builder pool down", "body": body}]
    router(proj, stub, tmp_path)
    assert stub.writes() == []
    stub.fixtures[HEALTH] = [{"number": 88, "title": "Builder pool down", "body": "older"}]
    router(proj, stub, tmp_path)
    assert [c[:2] for c in stub.writes()] == [["PATCH", f"{ISSUES}/88"]]


def test_the_issue_closes_when_the_leases_are_back(proj, stub, tmp_path):
    """REQ-041"""
    stub.fixtures[HEALTH] = [
        {"number": 88, "title": "Builder pool down", "body": "x"},
        {"number": 89, "title": "No live conductor", "body": "y"},
    ]
    router(proj, stub, tmp_path)
    closed = [c for c in stub.writes() if c[0] == "PATCH"]
    assert sorted(c[1] for c in closed) == [f"{ISSUES}/88", f"{ISSUES}/89"]
    assert all("state=closed" in c[2] for c in closed)


def test_a_lease_still_missing_keeps_the_issue_when_the_work_is_gone(proj, stub, tmp_path):
    """REQ-041: it closes when the leases are back, not when the work runs out."""
    stub.fixtures[PLAN] = []
    stub.fixtures[BRIEFS] = []
    stub.fixtures[HEALTH] = [{"number": 89, "title": "No live conductor", "body": "y"}]
    router(proj, stub, tmp_path)
    assert stub.writes() == []


def test_without_a_plan_issue_the_conductor_is_not_reported(proj, stub, tmp_path):
    """REQ-041: the lease is off, so nothing says it is dead."""
    (proj / "agk.toml").write_text(ON.replace("plan_issue = 61\n", ""), encoding="utf-8")
    stub.fixtures[PLAN] = []
    router(proj, stub, tmp_path)
    assert stub.writes() == []


def test_builder_start_start_reads_and_writes_nothing(proj, stub, tmp_path):
    """REQ-041: answer 7, `builder_start = "start"` unchanged."""
    (proj / "agk.toml").write_text("[flow]\nplan_issue = 61\n", encoding="utf-8")
    stub.fixtures[PLAN] = []
    out = router(proj, stub, tmp_path)
    assert out.returncode == 0
    assert stub.writes() == []
    assert not [c for c in stub.calls() if c[1].startswith(PLAN)]


def test_an_unreadable_lease_opens_nothing_and_fails_no_routing(proj, stub, tmp_path):
    """REQ-041: unknown is never dead, and the labels are the job's first duty."""
    stub.fixtures[PLAN] = "FAIL"
    out = router(proj, stub, tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "health:" in out.stdout and stub.writes() == []


def test_the_health_form_runs_it_for_a_person_and_dry_run_writes_nothing(proj, stub, tmp_path):
    """REQ-041: local mode has no workflow; `--health` is the same check."""
    stub.fixtures[PLAN] = []
    out = router(proj, stub, tmp_path, "--health", "--dry-run")
    assert out.returncode == 0, out.stdout + out.stderr
    assert "No live conductor" in out.stdout and stub.writes() == []
    assert router(proj, stub, tmp_path, "--health").returncode == 0
    assert opened(stub) == ["No live conductor"]


def test_a_paused_kit_reads_nothing(proj, stub, tmp_path):
    """REQ-041: session rule 33."""
    (proj / "agk.toml").write_text("paused = true\n" + ON, encoding="utf-8")
    stub.fixtures[PLAN] = []
    router(proj, stub, tmp_path)
    assert stub.calls() == []


# --- the bound of the two watches (the 09:36Z addition) ----------------------------------------


class Clock:
    """Stands in for the `time` module: `sleep` moves it, and a read costs a second."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.start = self.now

    def monotonic(self) -> float:
        self.now += 1
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    @property
    def spent(self) -> float:
        return self.now - self.start


def test_conductor_watch_with_no_event_returns_within_five_minutes(monkeypatch, capsys):
    """REQ-041"""
    clock = Clock()
    monkeypatch.setattr(conductor, "time", clock)
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(conductor.session, "flow_int", lambda *a: 60)
    monkeypatch.setattr(conductor, "new_lines", lambda repo, since: [])
    monkeypatch.setattr(conductor, "renew_lease", lambda root: 0)
    assert conductor.watch("root", datetime.now(UTC), False) == 0
    assert capsys.readouterr().out.strip() == "nothing new"
    assert clock.spent <= 300


def test_conductor_watch_is_bounded_while_github_cannot_be_read(monkeypatch, capsys):
    """REQ-041: a read that keeps failing does not lose the bound."""
    clock = Clock()

    def broken(repo, since):
        raise conductor.CheckError("the open briefs cannot be read")

    monkeypatch.setattr(conductor, "time", clock)
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(conductor.session, "flow_int", lambda *a: 60)
    monkeypatch.setattr(conductor, "new_lines", broken)
    monkeypatch.setattr(conductor, "renew_lease", lambda root: 0)
    assert conductor.watch("root", datetime.now(UTC), False) == 0
    assert clock.spent <= 300


def test_conductor_watch_renews_at_each_pass_in_time(monkeypatch, capsys):
    """REQ-041: renewed at once and again before the bound, so 10 minutes never run out."""
    clock = Clock()
    renewals: list[float] = []

    def renew(root):
        renewals.append(clock.spent)
        return 0

    monkeypatch.setattr(conductor, "time", clock)
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(conductor.session, "flow_int", lambda *a: 60)
    monkeypatch.setattr(conductor, "new_lines", lambda repo, since: [])
    monkeypatch.setattr(conductor, "renew_lease", renew)
    conductor.watch("root", datetime.now(UTC), False)
    assert len(renewals) >= 2 and renewals[0] <= 2 and renewals[1] <= 300


def slot_watch(monkeypatch, clock, found=lambda: [], mark: str = "mine"):
    """`watch_assign` of a slot in this process, with GitHub and the clock replaced."""
    calls: list[str] = []

    def lease(root, mode, name):
        calls.append(mode)
        return 0

    monkeypatch.setattr(session_script, "time", clock)
    monkeypatch.setattr(session_script, "repo_name", lambda root: REPO)
    monkeypatch.setattr(session_script, "conductor_issue", lambda repo: 204)
    monkeypatch.setattr(session_script, "pages", lambda path: found())
    monkeypatch.setattr(session_script, "verdict_authors", lambda root: ["boss"])
    monkeypatch.setattr(session_script, "builder_start", lambda root: "assign")
    monkeypatch.setattr(session_script, "builder_slots", lambda root: 3)
    monkeypatch.setattr(session_script, "slot_lease", lease)
    monkeypatch.setattr(session_script, "slot_run", lambda root, name: mark)
    monkeypatch.setattr(session_script, "local_head", lambda root: "local head x")
    monkeypatch.setattr(session_script, "flow_int", lambda root, key, default, rule: default)
    return calls


def test_a_slots_assign_watch_with_no_event_returns_within_five_minutes(monkeypatch, capsys):
    """REQ-041"""
    clock = Clock()
    calls = slot_watch(monkeypatch, clock)
    code = session_script.watch_assign("root", "s1", {"--interval": "60"})
    assert code == 0 and capsys.readouterr().out.strip().splitlines()[-1] == "no event"
    assert clock.spent <= 300
    assert calls.count("--renew") >= 2


def test_a_slots_assign_watch_never_waits_longer_than_the_bound(monkeypatch, capsys):
    """REQ-041: a larger `--timeout` does not lift it."""
    clock = Clock()
    slot_watch(monkeypatch, clock)
    session_script.watch_assign("root", "s1", {"--interval": "60", "--timeout": "99999"})
    assert clock.spent <= 300


def test_a_session_that_is_no_slot_keeps_its_long_wait(monkeypatch, capsys):
    """REQ-041: `builder_start = "start"` unchanged: `assign-timeout` at its own limit."""
    clock = Clock()
    calls = slot_watch(monkeypatch, clock)
    monkeypatch.setattr(session_script, "builder_start", lambda root: "start")
    code = session_script.watch_assign("root", "b1", {"--interval": "60", "--timeout": "900"})
    assert code == 0 and capsys.readouterr().out.strip().splitlines()[-1] == "assign-timeout"
    assert clock.spent >= 900 and calls == []


def test_a_lost_slot_ends_the_watch(monkeypatch, capsys):
    """REQ-041: another run holds the slot: exit 3, at once."""
    clock = Clock()
    slot_watch(monkeypatch, clock)
    monkeypatch.setattr(session_script, "slot_lease", lambda root, mode, name: 3)
    assert session_script.watch_assign("root", "s1", {"--interval": "60"}) == 3


def test_an_unreadable_end_releases_the_slot(monkeypatch, capsys):
    """REQ-041: every exit path releases; the fifth failed read ends the wait."""
    clock = Clock()
    calls = slot_watch(monkeypatch, clock, found=lambda: None)
    code = session_script.watch_assign("root", "s1", {"--interval": "1"})
    assert code == session_script.EXIT_UNREADABLE and calls[-1] == "--release"
