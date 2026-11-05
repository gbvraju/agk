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
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import common
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
        ("", [3, 0, 2], ["p1", "p2", "p0"]),
        ("priority", [3, 2, 0, "unknown"], ["p2", "p1", "p0", "p3"]),
        ("priority", [1, 1], ["p0", "p1"]),
    ],
)
def test_the_runner_takes_jobs_in_the_order_in_force(repo, tmp_path, order, priorities, ran):
    """REQ-047 AC3: SPEC-0040 rules 4 and 5; fifo ignores priorities; unset is priority (117)."""
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


# --- amendment 117 to rule 5: priority by default, and a job that unblocks others goes first ----


def fake_gh(tmp_path: Path, briefs: dict[int, str], open_items: list[dict] | None) -> Path:
    """A `gh` on PATH: `repos/<o>/<r>/issues/<n>` from saved bodies, and the open issues and pull
    requests from `open_items` (a failed read when None); anything else fails."""
    bin_dir = tmp_path.parent / f"{tmp_path.name}-bin"
    bin_dir.mkdir(exist_ok=True)
    saved = bin_dir / "saved.json"
    saved.write_text(json.dumps({"briefs": briefs, "open": open_items}), encoding="utf-8")
    (bin_dir / "gh").write_text(
        f"#!{PY}\n"
        "import json, sys\n"
        f"data = json.load(open({str(saved)!r}, encoding='utf-8'))\n"
        "path = next((a for a in sys.argv[1:] if a.startswith('repos/')), '')\n"
        "tail = path.split('/issues', 1)[-1]\n"
        "if tail.startswith('?state=open') and data['open'] is not None:\n"
        "    print(json.dumps(data['open'] if 'page=1' in tail.split('&') else [])); sys.exit(0)\n"
        "number = tail.lstrip('/')\n"
        "if number in data['briefs']:\n"
        "    print(json.dumps({'number': int(number), 'body': data['briefs'][number]}))\n"
        "    sys.exit(0)\n"
        "sys.stderr.write('HTTP 404: Not Found\\n'); sys.exit(1)\n",
        encoding="utf-8",
    )
    (bin_dir / "gh").chmod(0o755)
    return bin_dir


def brief(number: int, body: str) -> dict:
    return {"number": number, "body": body, "labels": [{"name": "agk-brief"}]}


def pull(number: int, body: str) -> dict:
    return {"number": number, "body": body, "labels": [], "pull_request": {"url": "x"}}


BLOCKS_TWO = [
    brief(20, "Why: x\nDepends-on: #7\nPriority: 2\n"),
    pull(21, "Brief: #22\nDepends-on: #7\n"),
    brief(23, "Depends-on: #70\n"),  # names another number: not a dependence on #7
    {"number": 24, "body": "Depends-on: #7\n", "labels": []},  # neither a brief nor a pull request
]


def submit_brief(repo, where, bin_dir: Path, number: int, label: str) -> dict:
    """`lock.py submit --brief N` for a fake job that logs `label`; returns the job file."""
    repo.commit({f"{label}.txt": label}, label)
    proc = repo.run(
        "lock.py", "submit", "--name", "heavy", "--session", label, "--brief", str(number), "--",
        PY, "-c", LOG, label, str(where / "log.txt"),
        PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
    )  # fmt: skip
    assert proc.returncode == 0 and "queued heavy-" in proc.stdout, proc.stdout + proc.stderr
    box = queue_of(where) / "jobs"
    return max((json.loads(p.read_text(encoding="utf-8")) for p in box.glob("*.json")),
               key=lambda j: j["seq"])  # fmt: skip


def test_priority_is_the_default_order():
    """REQ-047 AC3: amendment 117 item 1 to SPEC-0040 rule 5; `fifo` stays available."""
    import common

    assert common.QUEUE_DEFAULTS["queue_order"] == "priority"
    assert common.QUEUE_ORDERS == ("fifo", "priority")


def test_a_job_whose_brief_blocks_two_open_items_runs_before_an_older_job_of_its_priority(
    repo, tmp_path
):
    """REQ-047 AC3: amendment 117 item 2; `queue_order` unset is `priority`."""
    where = configure(repo, tmp_path)
    repo.git("remote", "add", "origin", "https://github.com/example/demo.git")
    bin_dir = fake_gh(tmp_path, {"7": "Priority: 2\n", "8": "Priority: 2\n"}, BLOCKS_TWO)
    older = submit_brief(repo, where, bin_dir, 8, "older")
    unblocker = submit_brief(repo, where, bin_dir, 7, "unblocker")
    assert (older["priority"], "raised" not in older) == (2, True)
    assert unblocker["priority"] == 1 and unblocker["raised"] == "raised: unblocks #20, #21"
    assert work(repo) == 0
    assert log(where) == ["unblocker", "older"]


def test_the_red_branch_brief_stays_at_0_and_first(repo, tmp_path):
    """REQ-047 AC3: amendment 117 item 2; a raise never takes a job to 0 (Q-552-3)."""
    where = configure(repo, tmp_path)
    repo.git("remote", "add", "origin", "https://github.com/example/demo.git")
    blocks = [brief(30, "Depends-on: #7\n"), brief(31, "Depends-on: #9\n")]
    bin_dir = fake_gh(tmp_path, {"7": "Priority: 1\n", "9": "Priority: 0\n"}, blocks)
    one = submit_brief(repo, where, bin_dir, 7, "one")
    red = submit_brief(repo, where, bin_dir, 9, "red")
    assert (one["priority"], red["priority"]) == (1, 0)
    assert work(repo) == 0
    assert log(where) == ["red", "one"]


def test_with_fifo_an_unblocker_takes_its_turn(repo, tmp_path):
    """REQ-047 AC3: amendment 117 items 1 and 3; the raise is recorded, the order is unchanged."""
    where = configure(repo, tmp_path, 'queue_order = "fifo"\n')
    repo.git("remote", "add", "origin", "https://github.com/example/demo.git")
    bin_dir = fake_gh(tmp_path, {"7": "Priority: 2\n", "8": "Priority: 2\n"}, BLOCKS_TWO)
    submit_brief(repo, where, bin_dir, 8, "older")
    assert submit_brief(repo, where, bin_dir, 7, "unblocker")["priority"] == 1
    assert work(repo) == 0
    assert log(where) == ["older", "unblocker"]


@pytest.mark.parametrize("written, open_items", [("Priority: 2\n", None), ("Why: x\n", BLOCKS_TWO)])
def test_a_failed_read_or_an_unknown_priority_raises_nothing(repo, tmp_path, written, open_items):
    """REQ-047 AC3: amendment 117 item 2; a read failure leaves the priority as read."""
    where = configure(repo, tmp_path)
    repo.git("remote", "add", "origin", "https://github.com/example/demo.git")
    job = submit_brief(repo, where, fake_gh(tmp_path, {"7": written}, open_items), 7, "job")
    assert job["priority"] == (2 if open_items is None else "unknown") and "raised" not in job


# --- the fix list of 2026-11-05 on #555 ----------------------------------------------------------


def test_a_job_submitted_as_the_runner_goes_idle_is_never_left_without_a_runner(
    repo, where, monkeypatch
):
    """REQ-047 AC5: SPEC-0040 rule 8; the stop decision and the submit's runner check share the
    mutex. The submit is forced in at the runner's last read of an empty queue before it stops."""
    clock = Clock()
    gate = where / ".agk-lock-heavy.mutex"
    real_jobs, real_dispatch = heavy_queue.jobs, lock.dispatch
    state: dict = {"dispatching": False, "alive": None}
    threads: list[threading.Thread] = []
    late = job_of(repo, where, "late")

    def submit() -> None:
        held = where / "agk-lock-heavy"
        state["alive"] = lock.enqueue(held, "heavy", late, "priority", 60, NOW)[3]

    def dispatch(*args, **kw):
        state["dispatching"] = True
        try:
            return real_dispatch(*args, **kw)
        finally:
            state["dispatching"] = False

    def jobs(folder):
        found = real_jobs(folder)
        idle = clock.now - NOW >= timedelta(minutes=10)
        if idle and not found and not state["dispatching"] and not threads:
            threads.append(threading.Thread(target=submit))
            threads[0].start()
            if not gate.exists():  # the runner reads outside the mutex: the submit goes first
                threads[0].join()
        return found

    monkeypatch.setattr(lock, "dispatch", dispatch)
    monkeypatch.setattr(heavy_queue, "jobs", jobs)
    assert work(repo, clock) == 0
    assert threads, "the interleaving was never forced"
    threads[0].join()
    assert not (queue_of(where) / "runner.json").exists()
    assert [j["session"] for j in real_jobs(queue_of(where))] == [late["session"]]  # it waits
    assert state["alive"] is False  # so the submit starts a runner for the waiting job


def test_a_job_worktree_is_made_under_the_long_temp_folder_on_windows(
    repo, where, monkeypatch, tmp_path
):
    """REQ-047 AC3: SPEC-0040 rule 4 on a fake Windows; the 8.3 short name never reaches a job
    (brief #508, ADR-0257)."""
    short = r"C:\Users\EXAMPL~1.USR\AppData\Local\Temp"
    long = tmp_path / "long temp"
    long.mkdir()
    monkeypatch.setattr(common, "on_windows", lambda: True)
    monkeypatch.setattr(common, "long_path_name", lambda path: str(long) if path == short else None)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: short)
    job = add(repo, where, "w", command=[PY, "-c", "import os; print(os.getcwd())"])
    assert work(repo) == 0
    assert results(where)[job["ticket"]]["outcome"] == "passed"
    out = (queue_of(where) / "results" / f"{job['ticket']}.out").read_text(encoding="utf-8")
    assert Path(out.strip()).resolve().is_relative_to(long.resolve())
    assert list(long.iterdir()) == []  # the job's temporary folder is removed


class Ending(Clock):
    """A clock whose sleep interrupts the runner after 30 min, so a runner that never stops ends."""

    def sleep(self, seconds: float) -> None:
        super().sleep(seconds)
        if self.now - NOW > timedelta(minutes=30):
            raise KeyboardInterrupt


@pytest.mark.parametrize("fails", [1, 99])
def test_a_result_that_cannot_be_written_never_leaves_the_job_started(
    repo, where, monkeypatch, fails
):
    """REQ-047 AC5: SPEC-0040 rules 4 and 14; the runner fails the job where it can, releases it
    and goes on to the next one and to its idle stop."""
    real, calls = heavy_queue.finish, []

    def finish(folder, job, outcome, *args, **kw):
        calls.append(outcome)
        if len(calls) <= fails:
            raise OSError("the result cannot be written")
        return real(folder, job, outcome, *args, **kw)

    monkeypatch.setattr(heavy_queue, "finish", finish)
    first, second = add(repo, where, "a"), add(repo, where, "b")
    clock = Ending()
    assert lock.runner(repo.root, "heavy", clock=clock, sleep=clock.sleep) == 0
    assert log(where) == ["a", "b"]
    assert list((queue_of(where) / "jobs").glob("*.json")) == []
    done = {t: r["outcome"] for t, r in results(where).items()}
    if fails == 1:
        assert done == {
            first["ticket"]: "failed (the result cannot be written)",
            second["ticket"]: "passed",
        }
    else:
        assert done == {}


def test_an_unblocker_already_at_1_is_not_raised_but_goes_first_within_1(repo, tmp_path):
    """REQ-047 AC3: amendment 117 item 2 and the ruling on Q-552-3: 0 stays the red-default-branch
    brief's; within one priority an unblocker goes before other jobs, then by sequence number."""
    where = configure(repo, tmp_path)
    repo.git("remote", "add", "origin", "https://github.com/example/demo.git")
    blocks = [brief(30, "Depends-on: #7\n"), pull(31, "Depends-on: #6\n")]
    briefs = {
        "6": "Priority: 2\n",
        "7": "Priority: 1\n",
        "8": "Priority: 1\n",
        "9": "Priority: 0\n",
    }
    bin_dir = fake_gh(tmp_path, briefs, blocks)
    older = submit_brief(repo, where, bin_dir, 8, "older")
    one = submit_brief(repo, where, bin_dir, 7, "one")
    two = submit_brief(repo, where, bin_dir, 6, "two")
    red = submit_brief(repo, where, bin_dir, 9, "red")
    assert (one["priority"], one["unblocks"], "raised" not in one) == (1, [30], True)
    assert (two["priority"], two["unblocks"], two["raised"]) == (1, [31], "raised: unblocks #31")
    assert (older["priority"], "unblocks" not in older, red["priority"]) == (1, True, 0)
    assert work(repo) == 0
    assert log(where) == ["red", "one", "two", "older"]
