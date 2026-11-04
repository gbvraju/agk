"""The heavy-run queue's runner (brief #552, ADR-0274, SPEC-0040 build (b), rules 4 to 6, 8, 14).

REQ-047. `lock.py runner --name heavy` takes the waiting jobs one at a time in the order of build
(a), never pre-empting a running one, runs each under the lock in a detached worktree of its head,
writes its result (with its `kind`) and cleans up. The runner is called in-process with an
injectable clock and sleep, so no test waits on a timer; the fake commands are small Python
programs. Every test points `lock_dir` at its own folder; no network; invented data.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import heavy_queue
import lock
import pytest

PY = sys.executable
SCRIPTS = str(Path(lock.__file__).resolve().parent)
NOW = datetime.now(UTC).replace(microsecond=0)
# A fake job: logs its label and the `which.txt` of the tree it runs in, and prints its label.
LOG = "import sys; open(sys.argv[2], 'a').write(sys.argv[1] + ' ' + open('which.txt').read())\n"
LOG += "print('out', sys.argv[1])\n"


class Clock:
    """The runner's clock; its sleep moves the time on and waits for nothing."""

    def __init__(self, now: datetime = NOW) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


@pytest.fixture
def where(repo, tmp_path) -> Path:
    return configure(repo, tmp_path)


def configure(repo, tmp_path: Path, locks: str = "", extra: str = "") -> Path:
    folder = tmp_path.parent / f"{tmp_path.name}-locks"
    text = f"lock_dir = '{folder.as_posix()}'\n{extra}[locks]\nqueue = true\n{locks}"
    repo.commit({"agk.toml": text, "which.txt": "one\n"}, "settings")
    return folder


def queue_of(folder: Path) -> Path:
    return folder / ".agk-lock-heavy.queue"


def head(repo) -> str:
    return repo.git("rev-parse", "HEAD").strip()


def job_of(repo, where, label: str, priority=heavy_queue.UNKNOWN, at=None, **kw) -> dict:
    """A job as `submit` writes it; its command logs `label` unless another is given."""
    command = kw.get("command") or [PY, "-c", LOG, label, str(where / "log.txt")]
    return heavy_queue.new_job(
        session=kw.get("session", "b1"), repository=str(repo.root), branch="main",
        head=kw.get("sha") or head(repo), command=command, folder=".",
        kind=kw.get("kind", "other"), brief=None, priority=priority, submitted=at or NOW,
    )  # fmt: skip


def add(repo, where, label: str, **kw) -> dict:
    return heavy_queue.submit(queue_of(where), "heavy", job_of(repo, where, label, **kw))[0]


def work(repo, clock: Clock | None = None) -> int:
    clock = clock or Clock()
    return lock.runner(repo.root, "heavy", clock=clock, sleep=clock.sleep)


def results(where) -> dict[str, dict]:
    return {r["ticket"]: r for r in heavy_queue.results(queue_of(where))}


def log(where) -> list[str]:
    return (where / "log.txt").read_text(encoding="utf-8").split()[::2]


# --- rules 4 and 6: one at a time, in order, on the exact head ----------------------------------


def test_jobs_run_in_submission_order_each_on_its_own_head_with_a_full_result(repo, where):
    """REQ-047 AC3: SPEC-0040 rules 4 and 6; the result carries `kind` (Q-529-2)."""
    first = add(repo, where, "a", kind="prepush")
    repo.commit({"which.txt": "two\n"}, "two")
    record = ["--record", str(where / "rec.json")]
    second = add(repo, where, "b", command=[PY, "-c", LOG, "b", str(where / "log.txt"), *record])
    repo.commit({"which.txt": "three\n"}, "builder moves on")
    assert work(repo) == 0
    assert (where / "log.txt").read_text(encoding="utf-8") == "a one\nb two\n"
    done = results(where)
    for job, kind in ((first, "prepush"), (second, "other")):
        r = done[job["ticket"]]
        out = (queue_of(where) / "results" / f"{job['ticket']}.out").read_bytes()
        assert (r["outcome"], r["exit"], r["head"], r["kind"]) == ("passed", 0, job["head"], kind)
        assert r["output_sha256"] == hashlib.sha256(out).hexdigest()
        assert r["output_bytes"] == len(out) and b"out" in out
        assert {"queued_seconds", "run_seconds", "started", "ended"} <= r.keys()
    assert done[first["ticket"]]["record"] is None
    assert done[second["ticket"]]["record"] == str(where / "rec.json")
    assert list((queue_of(where) / "jobs").glob("*.json")) == []
    assert repo.git("worktree", "list").count("\n") == 1  # every job's worktree is removed
    assert (repo.root / "which.txt").read_text(encoding="utf-8") == "three\n"


def test_a_job_gets_the_session_token_and_name_of_its_slot(repo, where):
    """REQ-047 AC3: SPEC-0040 rule 4 (as `lock.py run`, ADR-0254)."""
    code = "import os; print(os.environ['AGK_LOCK_SESSION'], os.environ['AGK_LOCK_NAME'],"
    code += " len(os.environ['AGK_LOCK_TOKEN']))"
    job = add(repo, where, "x", command=[PY, "-c", code], session="b7")
    assert work(repo) == 0
    out = (queue_of(where) / "results" / f"{job['ticket']}.out").read_text(encoding="utf-8")
    assert out.split() == ["b7", "heavy", "32"]


@pytest.mark.parametrize(
    "order, priorities, ran",
    [
        ("fifo", [3, 0, 2], ["p0", "p1", "p2"]),
        ("", [3, 0, 2], ["p0", "p1", "p2"]),
        ("priority", [3, 2, 0, "unknown"], ["p2", "p1", "p0", "p3"]),
        ("priority", [1, 1], ["p0", "p1"]),
    ],
)
def test_the_runner_takes_jobs_in_the_order_in_force(repo, tmp_path, order, priorities, ran):
    """REQ-047 AC3: SPEC-0040 rules 4 and 5; fifo ignores priorities."""
    where = configure(repo, tmp_path, f'queue_order = "{order}"\n' if order else "")
    for n, p in enumerate(priorities):
        add(repo, where, f"p{n}", priority=p)
    assert work(repo) == 0
    assert log(where) == ran


def test_an_overdue_job_runs_before_a_newer_job_of_a_higher_priority(repo, tmp_path):
    """REQ-047 AC3: SPEC-0040 rule 5 (Q-S0040-18), with a fake clock."""
    where = configure(repo, tmp_path, 'queue_order = "priority"\nqueue_max_wait = 1\n')
    add(repo, where, "late", priority=3, at=NOW - timedelta(minutes=5))
    add(repo, where, "later", priority=2, at=NOW - timedelta(minutes=3))
    add(repo, where, "urgent", priority=0)
    assert work(repo) == 0
    assert log(where) == ["late", "later", "urgent"]


@pytest.mark.parametrize("order", ["fifo", "priority"])
def test_a_running_job_is_never_pre_empted_by_a_job_of_priority_0(repo, tmp_path, order):
    """REQ-047 AC3: SPEC-0040 rules 4 and 5; the urgent job is submitted while the other runs."""
    where = configure(repo, tmp_path, f'queue_order = "{order}"\n')
    urgent = job_of(repo, where, "urgent", priority=0, session="b2")
    inserts = (
        "import sys, json; sys.path.insert(0, sys.argv[1]); import heavy_queue, lock\n"
        "from pathlib import Path; held = Path(sys.argv[2])\n"
        "with lock.mutex(held): heavy_queue.submit(heavy_queue.queue_folder(held), 'heavy',"
        " json.loads(sys.argv[3]))\n"
        "open(sys.argv[4], 'a').write('slow x\\n')\n"
    )
    held, logged = str(where / "agk-lock-heavy"), str(where / "log.txt")
    command = [PY, "-c", inserts, SCRIPTS, held, json.dumps(urgent), logged]
    slow = add(repo, where, "slow", priority=3, command=command)
    assert work(repo) == 0
    assert log(where) == ["slow", "urgent"]
    assert results(where)[slow["ticket"]]["outcome"] == "passed"


def test_with_two_slots_two_jobs_run_at_once_and_none_overtakes(repo, tmp_path):
    """REQ-047 AC3: SPEC-0040 rule 4 (Q-S0040-15)."""
    where = configure(repo, tmp_path, extra="lock_slots = 2\n")
    busy = where / "busy"
    code = (
        "import sys, os, time; from pathlib import Path; box = Path(sys.argv[2]);"
        " box.mkdir(exist_ok=True); me = box / sys.argv[1]; me.touch();"
        " open(sys.argv[3], 'a').write(sys.argv[1] + ' ' + str(len(list(box.iterdir()))) + '\\n');"
        " time.sleep(0.3); me.unlink()"
    )
    for label in ("j1", "j2", "j3"):
        add(repo, where, label, command=[PY, "-c", code, label, str(busy), str(where / "log.txt")])
    assert work(repo) == 0
    lines = (where / "log.txt").read_text(encoding="utf-8").split("\n")[:-1]
    ran = [x.split()[0] for x in lines]  # j1 and j2 start together, in either order
    assert sorted(ran[:2]) == ["j1", "j2"] and ran[2] == "j3"
    assert max(int(x.split()[1]) for x in lines) <= 2
    started = [r["started"] for r in sorted(results(where).values(), key=lambda r: r["ticket"])]
    assert started == sorted(started)


# --- rule 14: cleanup; nothing that did not pass is passed --------------------------------------


def dead_pid() -> int:
    proc = subprocess.Popen([PY, "-c", "pass"])  # nosec B603 - fixed argument list, no shell
    proc.wait()
    return proc.pid


def mark_running(where, job: dict, **runner) -> None:
    path = queue_of(where) / "jobs" / f"{job['ticket']}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(started=heavy_queue.stamp(runner.pop("started", NOW)), runner=runner)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_jobs_that_cannot_pass_get_a_failed_result_naming_why(repo, where):
    """REQ-047 AC5: SPEC-0040 rules 6 and 14; never `passed`."""
    host = socket.gethostname()
    orphan = add(repo, where, "orphan")
    mark_running(where, orphan, pid=dead_pid(), host=host)
    elsewhere = add(repo, where, "elsewhere", session="b3")
    old = NOW - timedelta(minutes=200)
    mark_running(where, elsewhere, pid=1, host="other.example.com", started=old)
    exits = add(repo, where, "exit", command=[PY, "-c", "raise SystemExit(3)"])
    missing = add(repo, where, "missing", command=["agk-no-such-command-anywhere"])
    gone = add(repo, where, "gone", sha="0" * 40)
    (queue_of(where) / "jobs" / "heavy-000099-abcd.json").write_text("{not json", encoding="utf-8")
    want = {
        orphan["ticket"]: "failed (its runner no longer runs)",
        elsewhere["ticket"]: "failed (older than 120 min, setting: lock_stale_minutes)",
        exits["ticket"]: "failed (exit 3)",
        missing["ticket"]: "failed (the command cannot be started)",
        gone["ticket"]: "failed (head not found)",
        "heavy-000099-abcd": "failed (unreadable job)",
    }
    if os.name != "nt":
        kill = "import os, signal; os.kill(os.getpid(), signal.SIGKILL)"
        killed = add(repo, where, "killed", command=[PY, "-c", kill])
        want[killed["ticket"]] = "failed (killed by signal 9)"
    assert work(repo) == 0
    assert {t: r["outcome"] for t, r in results(where).items()} == want
    assert list((queue_of(where) / "jobs").glob("*.json")) == []


def test_old_results_are_removed_when_a_runner_starts(repo, where):
    """REQ-047 AC5: SPEC-0040 rule 14 (Q-S0040-9: seven days)."""
    box = queue_of(where) / "results"
    box.mkdir(parents=True)
    for name, days in (("heavy-000001-aaaa", 8), ("heavy-000002-bbbb", 6)):
        for suffix in (".json", ".out"):
            path = box / f"{name}{suffix}"
            path.write_text(json.dumps({"ticket": name}), encoding="utf-8")
            old = (NOW - timedelta(days=days)).timestamp()
            os.utime(path, (old, old))
    assert work(repo) == 0
    kept = ["heavy-000002-bbbb.json", "heavy-000002-bbbb.out"]
    assert sorted(p.name for p in box.iterdir()) == kept


# --- rule 8: one runner, idle stop, autostart ---------------------------------------------------


def test_a_runner_replaces_a_dead_runners_file_and_stops_when_idle(repo, where, capsys):
    """REQ-047 AC5: SPEC-0040 rules 8 and 14 (Q-S0040-3: 10 minutes by default)."""
    pid = dead_pid()
    dead = {"pid": pid, "host": socket.gethostname()}
    heavy_queue.write_whole(queue_of(where) / "runner.json", json.dumps(dead))
    clock = Clock()
    assert work(repo, clock) == 0
    out = capsys.readouterr().out
    assert f"replaced the runner file of pid {pid}, which no longer runs" in out
    assert "runner idle for 10 min; stopped" in out and clock.now - NOW >= timedelta(minutes=10)
    assert not (queue_of(where) / "runner.json").exists()


def test_a_second_runner_exits_0_naming_the_live_one(repo, where):
    """REQ-047 AC5: SPEC-0040 rule 4; the live runner's file is left as it is."""
    me = {"pid": os.getpid(), "host": socket.gethostname(), "read": heavy_queue.stamp(NOW)}
    heavy_queue.write_whole(queue_of(where) / "runner.json", json.dumps(me))
    proc = repo.run("lock.py", "runner", "--name", "heavy")
    assert proc.returncode == 0
    assert proc.stdout == f"runner already running (pid {os.getpid()}, host {me['host']})\n"
    assert json.loads((queue_of(where) / "runner.json").read_text(encoding="utf-8")) == me


@pytest.mark.parametrize("autostart", ["", "queue_autostart = true\n"])
def test_submit_starts_a_runner_only_with_autostart(repo, tmp_path, monkeypatch, capsys, autostart):
    """REQ-047 AC5: SPEC-0040 rule 8 (Q-S0040-1, Q-529-1)."""
    configure(repo, tmp_path, autostart)
    started: list[str] = []
    monkeypatch.setattr(lock, "start_runner", lambda root, name: started.append(name) or 4242)
    monkeypatch.chdir(repo.root)
    assert lock.main(["submit", "--name", "heavy", "--session", "b1", "--", PY, "-c", "1"]) == 0
    out = capsys.readouterr().out
    if autostart:
        assert started == ["heavy"] and "runner started (pid 4242)" in out
    else:
        assert started == [] and "no runner; start one with lock.py runner --name heavy" in out


def test_an_autostarted_runner_is_detached_and_started_without_a_shell(repo, where, monkeypatch):
    """REQ-047 AC5: SPEC-0040 rule 8; never inside the builder's own process group."""
    seen: dict = {}

    class Fake:
        pid = 4242

        def __init__(self, args, **kw):
            seen.update(kw, args=args)

    assert lock.start_runner(repo.root, "heavy", popen=Fake) == 4242
    assert seen["args"][-3:] == ["runner", "--name", "heavy"] and "shell" not in seen
    if os.name == "nt":
        assert seen["creationflags"] & subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        assert seen["start_new_session"] is True
    assert seen["stdin"] == subprocess.DEVNULL
