"""One supervisor pass per machine starts the conductor and steward jobs, once per event, within the
stop rules (brief #1387, SPEC-0064 build (b), rules 2, 6, 12 and 14; ADR-0585; REQ-071).

`conductor.py watchdog --pass` is the supervisor: one pass under the machine's `lock.py` lock
`autopilot`; a pass whose cheap reads show nothing changed since its last full read starts no model
and reads neither the plan nor the sweep (at most 10 counted GitHub calls on the 650-brief fixture);
a waiting question with no open steward starts one steward job with `AGK_STEWARD_START=conductor`,
which relays nothing; the stop rules start nothing and are said once. Saved GitHub answers, a `gh`
double, a stub adapter and the scripts of the pass replaced in this process: invented names
(`cb-example-1`, example.com), no network, no model.
"""

from __future__ import annotations

import json
import os
import subprocess  # nosec B404 - fixed argument lists, no shell
import sys
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_github_read_budget import World
from test_session import REPO, SHA, clean_env, comment
from test_session_plan_reads import Double

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts" / "agk"
sys.path.insert(0, str(SCRIPTS))

import autopilot  # noqa: E402
import conductor  # noqa: E402
import lock  # noqa: E402
import steward_owner  # noqa: E402

ROOT = SCRIPTS.parents[1]
TAKEN = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)
STEWARD_LINE = (
    "STEWARD: #7 Q-7-1 waited one pass unanswered; run: python3 scripts/agk/launch.py role "
    "--role steward --session steward-11"
)
ADAPTER = """import json, os, sys
with open(sys.argv[1], "a", encoding="utf-8") as log:
    keys = ("AGK_SESSION", "AGK_ROLE", "AGK_JOB_KIND", "AGK_STEWARD_START")
    log.write(json.dumps({**{k: os.environ.get(k) for k in keys}, "prompt": sys.stdin.read()}))
    log.write("\\n")
"""


def queued(number: int = 7) -> dict:
    """One queued pull request as `queued_items` reads it: a re-review after a verdict."""
    said = [comment(1, "boss", f"Verdict: fix list {SHA}\n\n1. a finding")]
    return {"number": number, "title": "An example (brief #9)", "author": "cb-example-1",
            "paths": ["docs/guides/example.md"], "comments": said}  # fmt: skip


@pytest.fixture
def local(repo, tmp_path, monkeypatch):
    """A project in local mode with an adapter double and the reads of a pass recorded."""
    import common

    double = tmp_path / "adapter.py"
    double.write_text(ADAPTER, encoding="utf-8")
    log = tmp_path / "adapter.log"
    text = (
        'default_branch = "main"\n[flow]\nplan_issue = 61\nauto_start = true\n'
        f"launch_adapter = {json.dumps(f'{sys.executable} {double} {log}')}\n"
    )
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.commit(
        {"agk.toml": text, "config/reviewers.yaml": "version: 1\nverdict_authors: [boss]\n"}
    )
    repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
    temp = tmp_path / "temp"
    temp.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp))  # the lock and the health file
    monkeypatch.setattr(common, "available_memory", lambda: None)
    facts = {
        "fingerprint": "fingerprint aaa", "plan": "Start 0: nothing ready.", "sweep": "x",
        "queue": [queued()], "issues": [], "comments": [], "pulls": [{"number": 7}],
        "rate": (5000.0, 0.0), "reads": [],
    }  # fmt: skip

    def lease(root, mode, name, takeover=True):
        print(f"lease: taken by {name}")
        return 0

    def pages(endpoint):
        facts["reads"].append(endpoint)
        return facts["issues"] if "/issues?" in endpoint else facts["pulls"]

    monkeypatch.setattr(conductor, "lease", lease)
    monkeypatch.setattr(conductor, "plan_comments", lambda repo, issue: [])
    monkeypatch.setattr(conductor, "lease_holder", lambda c, a, now: ("conductor-local", TAKEN))
    monkeypatch.setattr(conductor.session, "repo_name", lambda root: REPO)
    monkeypatch.setattr(conductor.session, "pages", pages)
    monkeypatch.setattr(conductor.session, "changed_comments", lambda r, s: facts["comments"])
    monkeypatch.setattr(conductor.session, "rate_state", lambda: facts["rate"])
    monkeypatch.setattr(
        conductor.session, "review_queue", lambda root, m: print(facts["fingerprint"]) or 0
    )
    monkeypatch.setattr(conductor.session_plan, "plan", lambda root, *a: print(facts["plan"]) or 0)
    monkeypatch.setattr(conductor, "sweep", lambda root: print(facts["sweep"]) or 0)
    monkeypatch.setattr(conductor, "queued_items", lambda root, repo: facts["queue"])
    monkeypatch.setattr(conductor, "builder_pass", lambda root, repo, adapter: None)
    monkeypatch.setattr(autopilot, "claude_processes", lambda: [])
    return {"repo": repo, "log": log, "facts": facts, "temp": temp}


def passed(local, capsys) -> tuple[int, str]:
    """One scheduled pass, past the first lease window of the last job."""
    state = conductor.pass_state_file(local["repo"].root)
    if state.exists():
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


# --- rule 2: one supervisor pass, one job per event ------------------------------------------


def test_req071_an_event_starts_one_job_and_a_quiet_pass_reads_no_plan_or_sweep(
    local, capsys, monkeypatch
):
    """REQ-071 AC1: one supervisor starts every job, once per event (rule 2; brief #1387
    answer 1: a pass with nothing changed starts no model; an event starts its job within one
    pass)."""
    code, out = passed(local, capsys)
    assert code == 0 and "watchdog: job started conductor-local" in out and len(jobs(local)) == 1

    def refused(*_a, **_k):
        raise AssertionError("a quiet pass reads neither the plan nor the sweep")

    monkeypatch.setattr(conductor.session_plan, "plan", refused)
    monkeypatch.setattr(conductor, "sweep", refused)
    code, out = passed(local, capsys)
    assert code == 0 and "watchdog: nothing changed; no job started" in out
    assert len(jobs(local)) == 1
    monkeypatch.undo()


def test_req071_a_new_verdict_starts_exactly_one_job_and_a_second_pass_none(local, capsys):
    """REQ-071 AC1: a new verdict on a builder head starts exactly one job, a second pass none
    (rule 2; brief #1387 answer 1)."""
    passed(local, capsys)
    facts = local["facts"]
    facts["comments"] = [comment(5, "boss", f"Verdict: cleared {SHA}")]
    facts["issues"] = [{"number": 7, "updated_at": "2026-11-16T10:05:00Z"}]
    facts["fingerprint"] = "fingerprint bbb"
    code, out = passed(local, capsys)
    assert code == 0 and "the queue changed" in out and len(jobs(local)) == 2
    facts["comments"], facts["issues"] = [], []
    code, out = passed(local, capsys)
    assert "nothing changed" in out and len(jobs(local)) == 2


def test_req071_the_lease_markers_own_edits_are_no_event(local, capsys):
    """REQ-071 AC1: the job's renewal of the lease is not an event (brief #1387 answer 1)."""
    passed(local, capsys)
    lease = "Conductor: active 2026-11-16T10:20:00Z conductor-local since 2026-11-16T10:00:00Z"
    local["facts"]["comments"] = [comment(9, "boss", lease)]
    local["facts"]["issues"] = [{"number": 61, "updated_at": "2026-11-16T10:10:00Z"}]
    code, out = passed(local, capsys)
    assert "nothing changed" in out and len(jobs(local)) == 1


def test_req071_two_passes_never_overlap_under_the_lock_autopilot(local, capsys, monkeypatch):
    """REQ-071 AC1: rule 2 (one pass, never a loop, under the machine's lock `autopilot`)."""
    monkeypatch.setattr(conductor, "AUTOPILOT_WAIT", 0)
    held = lock.lock_folder(local["repo"].root, conductor.AUTOPILOT_LOCK)
    owner = {"session": "cb-example-1", "pid": os.getpid(), "host": lock.socket.gethostname(),
             "started": conductor.stamp_of(datetime.now(UTC)),
             "token": uuid.uuid4().hex}  # fmt: skip
    assert lock.try_take(held, owner)
    try:
        code, out = passed(local, capsys)
    finally:
        lock.clear_if_same(held, owner["token"])
    assert code == 0 and "another pass holds the lock autopilot; nothing started" in out
    assert jobs(local) == []
    code, out = passed(local, capsys)  # the lock is released after a pass
    assert "job started" in out and not held.exists()


def test_req071_a_quiet_pass_on_the_650_brief_fixture_costs_at_most_ten_calls(repo, tmp_path):
    """REQ-071 AC1: on the 650-brief fixture one pass makes at most 10 counted GitHub calls
    when nothing changed (rule 17; brief #1387 answer 1)."""
    double = Double(tmp_path)
    world = World()
    world.serve(double)
    double.serve(f"repos/{REPO}/issues/61/comments", [])
    text = (
        'default_branch = "main"\n[flow]\nplan_issue = 61\nauto_start = true\n'
        'launch_adapter = "cb-example-adapter"\n'
    )
    repo.git("remote", "add", "origin", f"https://github.com/{REPO}.git")
    repo.commit(
        {"agk.toml": text, "config/reviewers.yaml": "version: 1\nverdict_authors: [boss]\n"}
    )
    repo.git("update-ref", "refs/remotes/origin/main", "HEAD")
    now = datetime.now(UTC)
    state = conductor.pass_state_file(repo.root)
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({
        "job_at": conductor.stamp_of(now - timedelta(hours=1)),
        "seen_at": conductor.stamp_of(now),
        "pulls": conductor.pulls_digest([world.pull(p) for p in world.pulls]),
    }))  # fmt: skip
    env = clean_env()
    env.update(PATH=f"{double.bin}{os.pathsep}{os.environ['PATH']}", GH_STUB_DIR=str(double.dir),
               AGK_READ_CACHE=str(double.cache), TMPDIR=str(tmp_path))  # fmt: skip
    double.forget()
    done = subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, str(SCRIPTS / "conductor.py"), "watchdog", "--pass"],
        cwd=repo.root, capture_output=True, text=True, env=env, timeout=300,
    )  # fmt: skip
    assert done.returncode == 0, done.stdout + done.stderr
    assert "watchdog: nothing changed; no job started" in done.stdout
    counted = len(double.counted())
    assert counted <= 10, f"a quiet pass: budget 10, counted {counted}"


def test_req071_each_pass_appends_one_health_line_to_the_temp_folder(local, capsys):
    """REQ-071 AC7: rule 10 (one line per pass in the temp folder, none in the checkout)."""
    passed(local, capsys)
    passed(local, capsys)
    lines = (local["temp"] / autopilot.HEALTH_FILE).read_text().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["started"] == {"conductor": 1}
    assert json.loads(lines[1])["started"] == {}
    assert not list(local["repo"].root.glob("*.jsonl"))


# --- rule 6: the steward job ----------------------------------------------------------------


def test_req071_a_waiting_question_starts_one_steward_job_that_relays_nothing(local, capsys):
    """REQ-071 AC4: a waiting question with no steward record starts one steward job with
    `AGK_STEWARD_START=conductor`; a second pass starts none (rule 6; brief #1387 answer 2)."""
    local["facts"]["sweep"] = f"x\n{STEWARD_LINE}"
    code, out = passed(local, capsys)
    assert code == 0 and "watchdog: steward job started steward-11" in out
    stewards = [j for j in jobs(local) if j["AGK_ROLE"] == "steward"]
    assert len(stewards) == 1
    assert stewards[0]["AGK_STEWARD_START"] == "conductor"
    assert stewards[0]["AGK_JOB_KIND"] == "steward" and stewards[0]["AGK_SESSION"] == "steward-11"
    assert "relay nothing" in stewards[0]["prompt"] and "approve nothing" in stewards[0]["prompt"]
    local["facts"]["comments"] = [comment(12, "cb-example-1", "Report: abc done")]
    code, out = passed(local, capsys)
    assert len([j for j in jobs(local) if j["AGK_ROLE"] == "steward"]) == 1


def test_req071_an_open_steward_means_no_steward_start(local, capsys, monkeypatch):
    """REQ-071 AC4: an open steward (a person's own) means no start (rule 6)."""
    monkeypatch.setattr(autopilot, "claude_processes", lambda: [(40, 1, "claude --agent steward")])
    local["facts"]["sweep"] = f"x\n{STEWARD_LINE}"
    code, out = passed(local, capsys)
    assert "watchdog: steward open; no steward job started" in out
    assert [j for j in jobs(local) if j["AGK_ROLE"] == "steward"] == []


def test_req071_a_supervisor_started_steward_posts_no_relay(tmp_path, monkeypatch, capsys):
    """REQ-071 AC4: the steward job answers from evidence only and relays nothing (rule 6;
    SPEC-0063 rule 4 and its third question as ruled)."""
    said = tmp_path / "said.txt"
    said.write_text("Friday.\n")
    posted: list = []
    monkeypatch.setenv("AGK_STEWARD_START", "conductor")
    monkeypatch.setattr(steward_owner, "post", lambda *a: posted.append(a))
    code = steward_owner.main(["relay", "--qid", "Q-7-1", "--on", "7", "--answer", "Friday",
                               "--said", str(said), "--at", "2026-11-16T10:00:00Z"])  # fmt: skip
    assert code == 2 and posted == []
    assert "relays nothing" in capsys.readouterr().out


# --- rule 12: the stop rules ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("facts", "why"),
    [
        ({"queue": []}, "no brief is ready and nothing waits on AGK"),
        ({"queue": [], "sweep": "NEEDS-YOU: #7 owner answer"},
         "every remaining item waits on the owner"),
        ({"rate": (50.0, 0.0)}, "the GitHub limit is low"),
    ],
)  # fmt: skip
def test_req071_each_stop_rule_starts_nothing_and_is_said_once(local, capsys, facts, why):
    """REQ-071 AC7: rule 12 (each stop rule starts nothing, says so once and is shown in
    `agk status`; brief #1387 answer 3)."""
    local["facts"].update(facts)
    code, out = passed(local, capsys)
    assert code == 0 and f"watchdog: quiet: {why}" in out and jobs(local) == []
    local["facts"]["fingerprint"] = "fingerprint ccc"  # a change, the stop rule still holds
    local["facts"]["comments"] = [comment(13, "cb-example-1", "Report: abc done")]
    code, out = passed(local, capsys)
    assert "quiet:" not in out and jobs(local) == []
    lines, _ = autopilot.github_lines(local["repo"].root)
    assert f"quiet: supervisor: {why}" in lines


def test_req071_a_paused_project_starts_nothing(local, capsys):
    """REQ-071 AC7: rule 12 (paused, session rule 33)."""
    root = local["repo"].root
    (root / "agk.toml").write_text("paused = true\n" + (root / "agk.toml").read_text())
    local["repo"].git("commit", "-qam", "pause")
    local["repo"].git("update-ref", "refs/remotes/origin/main", "HEAD")
    code, out = passed(local, capsys)
    assert "agk paused; nothing started" in out and jobs(local) == []


def test_req071_free_memory_below_one_builder_starts_nothing(local, capsys, monkeypatch):
    """REQ-071 AC7: rule 12 (free memory below one builder)."""
    import common

    monkeypatch.setattr(common, "available_memory", lambda: 1)
    monkeypatch.setattr(conductor, "builder_memory", lambda root: 8)
    code, out = passed(local, capsys)
    assert "free memory is below one builder (setting: builder_memory_gb)" in out
    assert jobs(local) == []


def test_req071_the_owners_rest_hours_stop_no_review_job(local, capsys):
    """REQ-071 AC7: rule 12 and Q-S0064-3 (build and review jobs run in the rest hours; the
    conductor and steward jobs of this build are no owner-only step)."""
    root = local["repo"].root
    (root / "agk.toml").write_text(
        (root / "agk.toml").read_text() + 'owner_rest_hours = "00:00-23:59"\n'
    )
    local["repo"].git("commit", "-qam", "rest")
    local["repo"].git("update-ref", "refs/remotes/origin/main", "HEAD")
    code, out = passed(local, capsys)
    assert code == 0 and "job started" in out and len(jobs(local)) == 1


# --- rule 14 and the role files ---------------------------------------------------------------


def test_req071_the_steward_start_of_the_conductor_is_the_supervisors(tmp_path, monkeypatch):
    """REQ-071 AC1: rule 14 (SPEC-0059 rule 2's steward start of the conductor becomes the
    supervisor's: `ready --start` with `auto_start` on starts nothing itself)."""
    calls: list = []
    monkeypatch.setattr(steward_owner.launch, "role_main", lambda *a, **k: calls.append(a) or 0)
    monkeypatch.setattr(steward_owner.launch, "launch_settings", lambda root: (True, "adapter"))
    monkeypatch.setattr(steward_owner, "not_ready", lambda root, plan, trace: [])
    opts = type("Opts", (), {"plan": tmp_path / "p", "trace": tmp_path / "t",
                             "session": "conductor-1", "start": True})()  # fmt: skip
    for name in ("p", "t"):
        (tmp_path / name).write_text("")
    code, lines = steward_owner.ready(tmp_path, opts)
    assert code == 0 and calls == []
    assert lines == ["ready: the supervisor starts the conductor at its next pass "
                     "(python3 scripts/agk/conductor.py watchdog --pass)"]  # fmt: skip


def test_req071_the_role_files_name_the_supervisor_and_drop_the_loop():
    """REQ-071 AC1 and AC4: brief #1387 answer 2 (the conductor's role drops `/loop`; the
    steward's start is the supervisor's) and ADR-0585."""
    text = " ".join((ROOT / ".claude" / "agents" / "conductor.md").read_text().split())
    assert "/loop" not in text and "ADR-0585" in text
    assert "the supervisor starts the steward job" in text
    steward = " ".join((ROOT / ".claude" / "agents" / "steward.md").read_text().split())
    assert "AGK_STEWARD_START=conductor" in steward and "relay nothing" in steward
