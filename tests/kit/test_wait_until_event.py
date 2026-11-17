"""A waiting session costs no model turns (brief #1310, ADR-0554; REQ-050).

`session.py watch --pr N --until-event` and `watch --assign ID --until-event` return only on an
event, every event line of one read printed, or after `[flow] wake_minutes` with `renew: no event`,
renewing a slot's lease every 240 s themselves; `session.py summary` posts the one working summary
and edits it in place; `resume --pr N` prints it with the diff since its head; `conductor.py
watchdog --pass` starts a conductor job only when the queue, the plan or the sweep says so. GitHub
and the clock are replaced in this process, or served by the `gh` stub of `test_session`; invented
names, no network.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_session import REPO, SHA, Stub, comment, iso, pull, session

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import conductor  # noqa: E402
import session as session_script  # noqa: E402

WAKE = 110 * 60
LIMIT = 2 * 3600  # the runtime's longest background command (verify)
OTHER = "f" * 40
TAKEN = datetime(2026, 11, 15, 10, 0, tzinfo=UTC)


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


class Quiet:
    """No `Tell:` line ever: the conductor issue is not part of these tests."""

    changed = False

    def __init__(self, *args) -> None:
        pass

    def start(self):
        return None

    def poll(self):
        return None


def series(items: list):
    """A function that gives the next item on each call and repeats the last one."""
    left = list(items)

    def give(*args, **kwargs):
        return left.pop(0) if len(left) > 1 else left[0]

    return give


def pr_world(monkeypatch, clock, pulls: list, threads: list, slot: bool = False, settings=None):
    """`watch --pr 7` in this process: the pull request and its comments come from the lists."""
    renewals: list[float] = []

    def lease(root, mode, name, *rest):
        renewals.append(clock.spent)
        return 0

    pr_of, comments_of = series(pulls), series(threads)
    monkeypatch.setattr(session_script, "time", clock)
    monkeypatch.setattr(session_script, "repo_name", lambda root: REPO)
    monkeypatch.setattr(session_script, "owner_wait_settings", lambda root: None)
    monkeypatch.setattr(session_script, "verdict_authors", lambda root: ["boss"])
    monkeypatch.setattr(session_script, "spec_approvers", lambda root: ["owner"])
    monkeypatch.setattr(
        session_script,
        "flow_int",
        lambda root, key, default, rule: (settings or {}).get(key, default),
    )
    monkeypatch.setattr(session_script, "gh", lambda endpoint, *a, method="GET": pr_of())
    monkeypatch.setattr(session_script, "pages", lambda path: comments_of())
    monkeypatch.setattr(session_script, "Told", Quiet)
    monkeypatch.setattr(session_script, "is_slot", lambda root, me: slot)
    monkeypatch.setattr(session_script, "slot_run", lambda root, me: "run" if slot else "")
    monkeypatch.setattr(session_script, "slot_lease", lease)
    return renewals


def until(**extra: str) -> dict:
    return {"--pr": "7", "--interval": "60", "--until-event": "1", **extra}


# --- (a) and (c): a quiet hour costs no return before wake_minutes ---------------------------


def test_1310a_a_quiet_wait_returns_only_at_wake_minutes(monkeypatch, capsys):
    """REQ-050: brief #1310 tests (a) and (c)."""
    clock = Clock()
    pr_world(monkeypatch, clock, [pull()], [[]])
    code = session_script.watch("root", until())
    assert code == 0
    assert capsys.readouterr().out.strip() == "renew: no event"
    assert WAKE <= clock.spent < LIMIT


def test_1310a_a_slots_wait_renews_its_lease_every_240_seconds(monkeypatch, capsys):
    """REQ-050: brief #1310 test (a): the renewal moves into the script."""
    clock = Clock()
    renewals = pr_world(monkeypatch, clock, [pull()], [[]], slot=True)
    session_script.watch("root", until(**{"--session": "s1"}))
    assert capsys.readouterr().out.strip() == "renew: no event"
    gaps = [b - a for a, b in zip(renewals, renewals[1:], strict=False)]
    assert renewals[0] <= 5 and len(renewals) >= WAKE // 240 - 1
    assert max(gaps) <= 240 + 120  # a poll in flight may finish first


def test_1310c_wake_minutes_is_read_from_the_flow_table(monkeypatch, capsys):
    """REQ-050: brief #1310 test (c): `[flow] wake_minutes` sets the bound."""
    clock = Clock()
    pr_world(monkeypatch, clock, [pull()], [[]], settings={"wake_minutes": 5})
    assert session_script.watch("root", until()) == 0
    assert capsys.readouterr().out.strip() == "renew: no event"
    assert 300 <= clock.spent < 400


def test_1310c_a_shorter_timeout_still_says_timeout(monkeypatch, capsys):
    """REQ-050: brief #1310 answer 1: a smaller `--timeout` keeps its own line and exit."""
    clock = Clock()
    pr_world(monkeypatch, clock, [pull()], [[]])
    assert session_script.watch("root", until(**{"--timeout": "120"})) == 3
    assert capsys.readouterr().out.strip() == "timeout"


def test_1310c_a_lease_that_cannot_be_renewed_ends_with_the_unreadable_exit(monkeypatch, capsys):
    """REQ-050: brief #1310 answer 5 (GitHub unreadable: the existing exit, never silence)."""
    clock = Clock()
    pr_world(monkeypatch, clock, [pull()], [[]], slot=True)

    def broken(*args):
        raise session_script.CheckError("the slot's lease cannot be read")

    monkeypatch.setattr(session_script, "slot_lease", broken)
    code = session_script.watch("root", until(**{"--session": "s1"}))
    assert code == session_script.EXIT_UNREADABLE
    assert "the slot's lease cannot be read" in capsys.readouterr().out


def test_1310c_without_the_flag_the_wait_is_unchanged(monkeypatch, capsys):
    """REQ-050: brief #1310 test (g): no flag, no wake bound and no renewal."""
    clock = Clock()
    renewals = pr_world(monkeypatch, clock, [pull()], [[]], slot=True)
    args = {"--pr": "7", "--interval": "60", "--timeout": "9000", "--session": "s1"}
    assert session_script.watch("root", args) == 3
    assert capsys.readouterr().out.strip() == "timeout" and renewals == []


# --- (b): each event kind returns once with its line -------------------------------------------

ASKED = comment(10, "builder", "Question: Q-7-1 which reading?")
EVENTS = [
    (
        [comment(11, "boss", f"Verdict: cleared {SHA}")],
        pull(),
        f"verdict cleared {SHA} (comment 11)",
    ),
    ([comment(11, "boss", "Correction: the brief means the narrower one")], pull(), "correction"),
    ([comment(11, "owner", "Maintainer answer: Q-7-1 the narrower one")], pull(), "answer Q-7-1"),
    ([], pull(merged=iso()), "merged #7"),
    ([], pull(state="closed"), "closed #7"),
    ([], pull(mergeable="dirty"), "conflict #7"),
    ([], pull(labels=("agk:fix",)), "label agk:fix"),
]


@pytest.mark.parametrize(("said", "after", "line"), EVENTS)
def test_1310b_each_event_ends_the_wait_once_with_its_line(monkeypatch, capsys, said, after, line):
    """REQ-050: brief #1310 test (b)."""
    clock = Clock()
    pr_world(monkeypatch, clock, [pull(), after], [[ASKED], [ASKED], [ASKED, *said]])
    assert session_script.watch("root", until()) == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1 and out[0].startswith(line)
    assert clock.spent < WAKE


def test_1310b_two_events_in_one_read_are_both_printed(monkeypatch, capsys):
    """REQ-050: brief #1310 answer 5 (two events in one return are all printed)."""
    clock = Clock()
    both = [
        ASKED,
        comment(11, "boss", f"Verdict: fix list {SHA}"),
        comment(12, "owner", "Answer: Q-7-1 the narrower one"),
    ]
    pr_world(monkeypatch, clock, [pull()], [[ASKED], [ASKED], both])
    assert session_script.watch("root", until()) == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out[0] == f"verdict fix list {SHA} (comment 11)"
    assert out[1].startswith("answer Q-7-1") and len(out) == 2


def test_1310b_a_verdict_on_another_head_is_no_event(monkeypatch, capsys):
    """REQ-050: brief #1310 answer 1 (only a real event)."""
    clock = Clock()
    stale = [ASKED, comment(11, "boss", f"Verdict: cleared {OTHER}")]
    pr_world(monkeypatch, clock, [pull()], [[ASKED], [ASKED], stale])
    assert session_script.watch("root", until()) == 0
    assert capsys.readouterr().out.strip() == "renew: no event"


# --- watch --assign --until-event ----------------------------------------------------------------


def assign_world(monkeypatch, clock, slot: bool = True):
    calls: list[str] = []

    def lease(root, mode, name, *rest):
        calls.append(mode)
        return 0

    monkeypatch.setattr(session_script, "time", clock)
    monkeypatch.setattr(session_script, "repo_name", lambda root: REPO)
    monkeypatch.setattr(session_script, "conductor_issue", lambda repo: 204)
    monkeypatch.setattr(session_script, "pages", lambda path: [])
    monkeypatch.setattr(session_script, "verdict_authors", lambda root: ["boss"])
    monkeypatch.setattr(session_script, "is_slot", lambda root, me: slot)
    monkeypatch.setattr(session_script, "slot_lease", lease)
    monkeypatch.setattr(session_script, "slot_run", lambda root, name: "run" if slot else "")
    monkeypatch.setattr(session_script, "flow_int", lambda root, key, default, rule: default)
    return calls


def test_1310a_a_slots_assign_wait_lifts_the_300_second_bound(monkeypatch, capsys):
    """REQ-050: brief #1310 answer 1 (`watch --assign` renews the lease itself)."""
    clock = Clock()
    calls = assign_world(monkeypatch, clock)
    code = session_script.watch_assign("root", "s1", {"--interval": "60", "--until-event": "1"})
    assert code == 0 and capsys.readouterr().out.strip().splitlines()[-1] == "renew: no event"
    assert WAKE <= clock.spent < LIMIT
    assert calls.count("--renew") >= WAKE // 240 - 1


def test_1310g_a_slots_assign_wait_without_the_flag_keeps_its_bound(monkeypatch, capsys):
    """REQ-050: brief #1310 test (g) (ADR-0368's bound stays without the flag)."""
    clock = Clock()
    assign_world(monkeypatch, clock)
    assert session_script.watch_assign("root", "s1", {"--interval": "60"}) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "no event"
    assert clock.spent <= 300


# --- the command line -------------------------------------------------------------------------


@pytest.fixture
def stub(tmp_path):
    return Stub(tmp_path)


@pytest.fixture
def proj(repo, stub):
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.write("config/reviewers.yaml", "version: 1\nverdict_authors: [boss, second]\n")
    return repo


@pytest.mark.parametrize(
    "args",
    [
        ("watch", "--merged", "7", "--until-event"),
        ("watch", "--pr", "7", "--until-event", "--until-event"),
        ("summary", "--pr", "7"),
        ("summary", "--file", "x.md"),
    ],
)
def test_1310_the_usage_is_checked(proj, stub, args):
    """REQ-050: brief #1310: `--until-event` with `--pr` or `--assign` only; two summary options."""
    out = session(proj, stub, *args)
    assert out.returncode == 2 and "usage:" in out.stdout
    assert stub.calls() == []


# --- (d): the summary is created once and edited in place ---------------------------------------

PR = f"repos/{REPO}/pulls/7"
COMMENTS = f"repos/{REPO}/issues/7/comments"
FIXED = (  # brief #1389 (ADR-0586): the fixed sections every summary carries
    "Alternatives rejected: none.\nRisks: none.\nHow to run the tests: pytest.\n"
    "Where it is stuck: nowhere.\n"
)


def writes(stub) -> list[list]:
    return [c for c in stub.calls() if c[0] != "GET"]


def test_1310d_the_summary_is_posted_once_then_edited_in_place(proj, stub, tmp_path):
    """REQ-050: brief #1310 test (d)."""
    text = tmp_path / "summary.md"
    text.write_text("Built: the wait.\nDecisions and why: none.\n" + FIXED, encoding="utf-8")
    stub.serve(PR, pull())
    stub.serve(COMMENTS, [ASKED])
    out = session(proj, stub, "summary", "--pr", "7", "--file", str(text))
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.strip() == f"summary: posted at {SHA[:7]}"
    posted = writes(stub)
    assert len(posted) == 1 and posted[0][:2] == ["POST", COMMENTS]
    sent = f"body=Summary: {SHA}\n\nBuilt: the wait.\nDecisions and why: none."
    assert any(arg.startswith(sent) for arg in posted[0][2])
    (tmp_path / "again").mkdir()
    again = Stub(tmp_path / "again")
    mine = comment(20, "builder", f"Summary: {OTHER}\n\nBuilt: an older text.")
    again.serve(PR, pull())
    again.serve(COMMENTS, [ASKED, mine])
    again.serve(f"repos/{REPO}/issues/comments/20", {"id": 20}, method="PATCH")
    out = session(proj, again, "summary", "--pr", "7", "--file", str(text))
    assert out.returncode == 0, out.stdout + out.stderr
    assert out.stdout.strip() == f"summary: edited comment 20 at {SHA[:7]}"
    edited = writes(again)
    assert len(edited) == 1 and edited[0][:2] == ["PATCH", f"repos/{REPO}/issues/comments/20"]


def test_1310d_a_summary_of_another_author_is_not_edited(proj, stub, tmp_path):
    """REQ-050: brief #1310 answer 2 (the builder's own summary only)."""
    text = tmp_path / "summary.md"
    text.write_text("Built: the wait.\nDecisions and why: none.\n" + FIXED, encoding="utf-8")
    stub.serve(PR, pull())
    stub.serve(COMMENTS, [comment(20, "stranger", f"Summary: {OTHER}\n\nnot mine")])
    out = session(proj, stub, "summary", "--pr", "7", "--file", str(text))
    assert out.returncode == 0 and [c[0] for c in writes(stub)] == ["POST"]


def test_1310d_a_summary_longer_than_the_setting_is_refused(proj, stub, tmp_path):
    """REQ-050: brief #1310 answer 5 (refused naming the setting; nothing posted)."""
    text = tmp_path / "summary.md"
    lines = [f"line {n}" for n in range(21)] + ["Decisions and why: none."]
    text.write_text("\n".join(lines) + "\n" + FIXED, encoding="utf-8")
    stub.serve(PR, pull())
    stub.serve(COMMENTS, [])
    out = session(proj, stub, "summary", "--pr", "7", "--file", str(text))
    assert out.returncode == 1
    assert "summary_lines" in out.stdout and "26" not in out.stdout
    assert writes(stub) == []
    proj.write("agk.toml", "[flow]\nsummary_lines = 30\n")
    out = session(proj, stub, "summary", "--pr", "7", "--file", str(text))
    assert out.returncode == 0, out.stdout + out.stderr


# --- (e): resume gives the summary, the newest verdict and the diff since its head ----------------


def resumed(proj, stub, comments: list):
    body = {**pull(), "title": "build 7", "draft": False, "body": "Advances: REQ-050\n"}
    body["head"] = {"sha": SHA, "ref": "claude/brief-7"}
    stub.serve(PR, body)
    stub.serve(COMMENTS, comments)
    return session(proj, stub, "resume", "--pr", "7")


def test_1310e_resume_prints_the_summary_the_verdict_and_the_diff_since_its_head(proj, stub):
    """REQ-050: brief #1310 test (e)."""
    found = [
        comment(20, "builder", f"Summary: {OTHER}\n\nBuilt: the wait.\nOpen: none."),
        comment(21, "boss", f"Verdict: fix list {SHA}\n\n1. rename the line."),
    ]
    out = resumed(proj, stub, found)
    assert out.returncode == 0, out.stdout + out.stderr
    text = out.stdout
    assert f"summary (comment 20) at {OTHER}:" in text
    assert "  Built: the wait." in text and "  Open: none." in text
    assert f"verdict: fix list {SHA} (comment 21) names the head" in text
    assert f"git diff {OTHER}..{SHA}" in text
    assert writes(stub) == []


def test_1310e_resume_without_a_summary_names_the_newest_report(proj, stub):
    """REQ-050: brief #1310 answer 5 (an older pull request: the newest Report and the diff)."""
    found = [
        comment(18, "builder", f"Report: {OTHER[:7]} ready for review"),
        comment(19, "builder", f"Report: {OTHER[:9]} fix list applied"),
    ]
    out = resumed(proj, stub, found)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "summary: none" in out.stdout
    assert f"report: Report: {OTHER[:9]} fix list applied (comment 19)" in out.stdout
    assert f"git diff {OTHER[:9]}..{SHA}" in out.stdout


# --- (f): the scripted conductor pass starts a job only when there is work ----------------------

ADAPTER = """import json, os, sys
with open(sys.argv[1], "a", encoding="utf-8") as log:
    keys = ("AGK_SESSION", "AGK_ROLE", "CLAUDE_CODE_ENABLE_AWAY_SUMMARY")
    log.write(json.dumps({**{k: os.environ.get(k) for k in keys}, "prompt": sys.stdin.read()}))
    log.write("\\n")
sys.exit(int(os.environ.get("ADAPTER_EXIT", "0")))
"""


@pytest.fixture
def local(repo, tmp_path, monkeypatch):
    """A project in local mode with an adapter double; the scripts of the pass are replaced."""
    import common

    double = tmp_path / "adapter.py"
    double.write_text(ADAPTER, encoding="utf-8")
    log = tmp_path / "adapter.log"
    toml = (
        'default_branch = "main"\n[flow]\nplan_issue = 61\nauto_start = true\n'
        f"launch_adapter = {json.dumps(f'{sys.executable} {double} {log}')}\n"
    )
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.commit({"agk.toml": toml, "config/reviewers.yaml": "version: 1\nverdict_authors: [b]\n"})
    repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
    monkeypatch.delenv("ADAPTER_EXIT", raising=False)
    monkeypatch.setattr(common, "available_memory", lambda: None)
    facts = {"fingerprint": "fingerprint aaa", "plan": "Start 0: nothing ready.", "sweep": "x 5m"}
    facts["holder"] = ("conductor-local", TAKEN)  # the lease as the script's own take left it
    leases: list[str] = []

    def lease(root, mode, name, takeover=True):
        leases.append(f"{mode} {name} {takeover}")
        print(f"lease: taken by {name}")
        return 0

    monkeypatch.setattr(conductor, "lease", lease)
    monkeypatch.setattr(conductor.launch, "conductor_refusal", lambda root: None)  # brief #1449
    monkeypatch.setattr(conductor, "plan_comments", lambda repo, issue: [])
    monkeypatch.setattr(conductor, "lease_holder", lambda comments, authors, now: facts["holder"])
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(
        conductor.session, "review_queue", lambda root, m: print(facts["fingerprint"]) or 0
    )
    monkeypatch.setattr(conductor.session_plan, "plan", lambda root, *a: print(facts["plan"]) or 0)
    monkeypatch.setattr(conductor, "sweep", lambda root: print(facts["sweep"]) or 0)
    # Brief #1387 (ADR-0585): the supervisor's change reads, stop rules and health line are
    # tested in test_autopilot_supervisor.py; here they read nothing and stop nothing.
    monkeypatch.setattr(conductor, "change_reads", lambda root, repo, state, now: (False, None))
    monkeypatch.setattr(conductor, "stop_reason", lambda root, repo, *a: (None, None))
    monkeypatch.setattr(conductor, "record_health", lambda started, now: None)
    return {"repo": repo, "log": log, "facts": facts, "leases": leases}


def passed(local, capsys, later: bool = True) -> tuple[int, str]:
    """One scheduled pass; `later` puts it past the first lease window of the last job."""
    state = conductor.pass_state_file(local["repo"].root)
    if later and state.exists():
        kept = json.loads(state.read_text())
        if kept.get("job_at"):
            start = datetime.strptime(kept["job_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
            kept["job_at"] = conductor.stamp_of(start - timedelta(minutes=11))
            state.write_text(json.dumps(kept))
    code = conductor.main(["watchdog", "--pass"], root=local["repo"].root)
    return code, capsys.readouterr().out


def jobs(local) -> list[dict]:
    log = local["log"]
    return [json.loads(x) for x in log.read_text().splitlines()] if log.exists() else []


def test_1310f_an_unchanged_fingerprint_starts_no_job_and_a_change_one(local, capsys):
    """REQ-050: brief #1310 test (f)."""
    code, out = passed(local, capsys)
    assert code == 0 and "watchdog: job started conductor-local" in out
    assert len(jobs(local)) == 1
    code, out = passed(local, capsys)
    assert code == 0 and "watchdog: nothing changed; no job started" in out
    local["facts"]["sweep"] = "x 9m"  # an age alone is no change
    code, out = passed(local, capsys)
    assert "nothing changed" in out and len(jobs(local)) == 1
    local["facts"]["fingerprint"] = "fingerprint bbb"
    code, out = passed(local, capsys)
    assert code == 0 and "the queue changed" in out and len(jobs(local)) == 2
    assert local["leases"] == ["--take conductor-local False"] * 4


def test_1310f_the_job_does_one_pass_with_recaps_off(local, capsys):
    """REQ-050: brief #1310 answers 3 and 4."""
    passed(local, capsys)
    job = jobs(local)[0]
    assert job["AGK_SESSION"] == "conductor-local" and job["AGK_ROLE"] == "conductor"
    assert job["CLAUDE_CODE_ENABLE_AWAY_SUMMARY"] == "0"
    assert "Do one pass" in job["prompt"] and "do not release it" in job["prompt"]


@pytest.mark.parametrize(
    ("key", "value", "why"),
    [
        ("plan", "Start 1: b1 takes #9.", "the plan starts a brief"),
        ("sweep", "HANDOVER #7 3m", "a sweep line changed"),
    ],
)
def test_1310f_a_start_or_a_new_sweep_line_starts_a_job(local, capsys, key, value, why):
    """REQ-050: brief #1310 answer 3."""
    passed(local, capsys)
    local["facts"][key] = value
    code, out = passed(local, capsys)
    assert code == 0 and why in out and len(jobs(local)) == 2


def test_1310f_a_failed_job_is_tried_again_on_the_next_pass(local, capsys, monkeypatch):
    """REQ-050: brief #1310 answer 5 (the state is kept only after a job started)."""
    monkeypatch.setenv("ADAPTER_EXIT", "3")
    code, _ = passed(local, capsys)
    assert code == 1
    monkeypatch.delenv("ADAPTER_EXIT")
    code, out = passed(local, capsys)
    assert code == 0 and "job started" in out and len(jobs(local)) == 2


def test_1310f_a_day_without_a_job_starts_one_for_the_report(local, capsys):
    """REQ-050: brief #1310 answer 5 (one job a day on an unchanged fingerprint)."""
    passed(local, capsys)
    state = conductor.pass_state_file(local["repo"].root)
    kept = json.loads(state.read_text())
    kept["job_at"] = "2026-01-01T00:00:00Z"
    state.write_text(json.dumps(kept))
    code, out = passed(local, capsys)
    assert code == 0 and "no job ran for 24 hours" in out and len(jobs(local)) == 2


def test_1310f_another_holder_of_the_lease_starts_nothing(local, capsys, monkeypatch):
    """REQ-050: brief #1310 answer 3 (an interactive conductor with /loop is unchanged)."""

    def held(root, mode, name, takeover=True):
        print("lease: held by c1 until 2026-11-15T10:00:00Z")
        return conductor.merge_cleared.EXIT_HELD

    monkeypatch.setattr(conductor, "lease", held)
    code, out = passed(local, capsys)
    assert code == 0 and "held by c1" in out and "nothing started" in out
    assert jobs(local) == []


def test_1310f_no_second_job_starts_while_the_last_one_runs(local, capsys):
    """REQ-050: fix list 6889113783 item 2: one job at a time, with a live job."""
    passed(local, capsys)
    local["facts"]["fingerprint"] = "fingerprint bbb"  # the job's own verdicts change the queue
    code, out = passed(local, capsys, later=False)  # within the job's first lease window
    assert code == 0 and "watchdog: job conductor-local still running; nothing started" in out
    local["facts"]["holder"] = ("conductor-local", TAKEN + timedelta(minutes=7))  # it renewed
    code, out = passed(local, capsys)
    assert code == 0 and "still running; nothing started" in out
    assert len(jobs(local)) == 1 and len(local["leases"]) == 1  # the script took nothing more
    local["facts"]["holder"] = None  # the job ended and its lease lapsed
    code, out = passed(local, capsys)
    assert code == 0 and "job started" in out and len(jobs(local)) == 2


def test_1310f_the_job_is_told_to_renew_first(local, capsys):
    """REQ-050: fix list 6889113783 item 2 (the renewal is what marks the job live)."""
    passed(local, capsys)
    assert "renew it first" in jobs(local)[0]["prompt"]


def test_1310f_install_with_pass_prints_a_ten_minute_line(local, capsys, monkeypatch):
    """REQ-050: brief #1310 answer 3."""
    monkeypatch.setattr(conductor.sys, "platform", "linux")
    assert conductor.main(["watchdog", "--install", "--pass"], root=local["repo"].root) == 0
    line = capsys.readouterr().out.strip()
    assert line.startswith("*/10 * * * * ") and line.endswith("conductor.py watchdog --pass")
    assert jobs(local) == []
