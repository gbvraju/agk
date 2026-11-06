"""The heavy lock is never taken from a live holder; a heartbeat, not age, decides staleness (brief
#607, ADR-0295).

REQ-047. A lock whose holder (`lock.py` or its command) still runs on this machine is never
cleared, whatever its age, also after a sleep gap; a lock from another host, or whose liveness
cannot be read, is stale only when its heartbeat (`beat` in `owner.json`) is older than
`lock_stale_minutes`. The holder writes the heartbeat about once a minute; `status` prints the
holder, its age and the heartbeat's age, and every cleared lock says why. The queue runner's own
slot behaves the same. The clock is injected and the process check is a fake set of live process
ids, so no test waits on a timer. Every test points `lock_dir` at its own folder; no network;
invented data (example.com).
"""

from __future__ import annotations

import json
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import heavy_queue
import lock
import pytest

PY = sys.executable
NOW = datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC)
LIVE = 424242  # a fake process id that the fake process check says runs
GONE = 434343  # a fake process id that the fake process check says ended
ELSEWHERE = "builder-two.example.com"


def stamp(when: datetime) -> str:
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture(autouse=True)
def fake_pids(monkeypatch):
    """Only LIVE runs on this machine."""
    monkeypatch.setattr(lock, "pid_alive", lambda pid, *a, **k: pid == LIVE)


def plant(
    folder: Path,
    *,
    pid: int,
    host: str | None = None,
    started: datetime,
    beat: datetime | None = None,
    child: int | None = None,
    name: str = "agk-lock-heavy",
) -> Path:
    """A lock left by another run: its owner file as `lock.py` writes it."""
    held = folder / name
    held.mkdir(parents=True)
    owner = {
        "session": "builder-old",
        "pid": pid,
        "host": host or socket.gethostname(),
        "started": stamp(started),
        "token": uuid.uuid4().hex,  # another run's own random token
    }
    if beat is not None:
        owner["beat"] = stamp(beat)
    if child is not None:
        owner["child"] = child
    (held / "owner.json").write_text(json.dumps(owner), encoding="utf-8")
    return held


def reason(held: Path, limit: int = 120, now: datetime = NOW) -> str | None:
    return lock.stale_reason(lock.read_owner(held), held, limit, now=now)


def clear(held: Path, now: datetime = NOW, limit: int = 120) -> bool:
    return lock.clear_stale([held], "heavy", limit, "", None, now=now)


# --- answer 1: a live holder on this host is never cleared by age -------------------------------


def test_a_live_holder_older_than_the_limit_is_not_cleared(tmp_path, capsys):
    """REQ-047: brief #607 answers 1 and 5 (an injected clock and a fake pid)."""
    held = plant(tmp_path, pid=LIVE, started=NOW - timedelta(hours=9), beat=NOW)
    assert reason(held) is None
    assert clear(held) is False
    assert held.exists()
    assert "cleared" not in capsys.readouterr().out


def test_a_live_holder_with_no_heartbeat_at_all_is_not_cleared(tmp_path):
    """REQ-047: brief #607 answer 1 (an owner file of an older kit, with no `beat`)."""
    held = plant(tmp_path, pid=LIVE, started=NOW - timedelta(hours=9))
    assert reason(held) is None


def test_a_live_command_of_a_killed_holder_still_holds_whatever_its_age(tmp_path):
    """REQ-047: brief #607 answer 1 (the holder is `lock.py` or its command)."""
    held = plant(tmp_path, pid=GONE, child=LIVE, started=NOW - timedelta(hours=9))
    assert reason(held) is None


# --- answer 1: a dead holder is cleared, saying why ---------------------------------------------


def test_a_dead_holder_is_cleared_saying_its_process_no_longer_runs(tmp_path, capsys):
    """REQ-047: brief #607 answers 1, 4 and 5."""
    held = plant(tmp_path, pid=GONE, started=NOW - timedelta(minutes=3), beat=NOW)
    assert reason(held) == "its process no longer runs"
    assert clear(held) is True
    assert not held.exists()
    out = capsys.readouterr().out
    assert "lock heavy: cleared a stale lock of builder-old (its process no longer runs)" in out


# --- answer 2: another host, a heartbeat decides ------------------------------------------------


def test_a_remote_holder_with_a_fresh_heartbeat_is_kept_however_old_the_lock(tmp_path):
    """REQ-047: brief #607 answers 2 and 5 (a remote holder with a fresh heartbeat)."""
    held = plant(
        tmp_path,
        pid=GONE,
        host=ELSEWHERE,
        started=NOW - timedelta(hours=7),
        beat=NOW - timedelta(minutes=1),
    )
    assert reason(held) is None
    assert clear(held) is False
    assert held.exists()


def test_a_remote_holder_with_a_stale_heartbeat_is_cleared_saying_so(tmp_path, capsys):
    """REQ-047: brief #607 answers 2, 4 and 5 (a remote holder with a stale heartbeat)."""
    held = plant(
        tmp_path,
        pid=LIVE,  # a process id on another host says nothing about this machine
        host=ELSEWHERE,
        started=NOW - timedelta(minutes=150),
        beat=NOW - timedelta(minutes=121),
    )
    want = (
        f"its heartbeat from host {ELSEWHERE} is older than 120 min, setting: lock_stale_minutes"
    )
    assert reason(held) == want
    assert clear(held) is True
    assert not held.exists()
    assert f"lock heavy: cleared a stale lock of builder-old ({want})" in capsys.readouterr().out


def test_the_heartbeat_limit_is_lock_stale_minutes(tmp_path):
    """REQ-047: brief #607 answer 2 (the limit is the setting, and only the heartbeat counts)."""
    held = plant(
        tmp_path,
        pid=GONE,
        host=ELSEWHERE,
        started=NOW - timedelta(minutes=500),
        beat=NOW - timedelta(minutes=200),
    )
    assert reason(held, limit=300) is None
    assert reason(held, limit=120) is not None


def test_a_remote_lock_of_an_older_kit_without_a_heartbeat_is_judged_by_its_start(tmp_path):
    """REQ-047: brief #607 answer 2 (no `beat`: the start time is its last sign of life)."""
    young = plant(tmp_path / "a", pid=GONE, host=ELSEWHERE, started=NOW - timedelta(minutes=30))
    old = plant(tmp_path / "b", pid=GONE, host=ELSEWHERE, started=NOW - timedelta(minutes=121))
    assert reason(young) is None
    assert "heartbeat" in (reason(old) or "")


def test_a_holder_here_whose_liveness_cannot_be_read_is_judged_by_its_heartbeat(tmp_path):
    """REQ-047: brief #607 answer 1 (age matters only where liveness cannot be read)."""
    folder = tmp_path / "a"
    fresh = plant(folder, pid=0, started=NOW - timedelta(hours=5), beat=NOW)
    assert reason(fresh) is None
    stale = plant(tmp_path / "b", pid=0, started=NOW - timedelta(hours=5), beat=NOW - timedelta(hours=3))
    assert "heartbeat" in (reason(stale) or "")


# --- answer 3: a sleep gap with the process alive is kept ---------------------------------------


def test_a_sleep_gap_with_the_process_alive_is_kept_and_the_heartbeat_resumes(tmp_path):
    """REQ-047: brief #607 answers 3 and 5 (a 62-minute run and a 6-hour sleep, as in #606)."""
    started = NOW - timedelta(hours=7, minutes=2)
    held = plant(tmp_path, pid=LIVE, started=started, beat=started + timedelta(minutes=62))
    assert reason(held) is None  # the heartbeat stopped six hours ago; the process still runs
    token = lock.read_owner(held)["token"]
    lock.beat(held, token, NOW)  # the holder wakes: its next heartbeat
    assert lock.read_owner(held)["beat"] == stamp(NOW)
    assert lock.read_owner(held)["started"] == stamp(started)


# --- answer 2: the holder writes the heartbeat --------------------------------------------------


def test_beat_writes_only_the_lock_of_its_own_token(tmp_path):
    """REQ-047: brief #607 answer 2 (a lock taken again by another run is never written)."""
    held = plant(tmp_path, pid=LIVE, started=NOW, beat=NOW)
    before = (held / "owner.json").read_text(encoding="utf-8")
    lock.beat(held, uuid.uuid4().hex, NOW + timedelta(minutes=5))
    assert (held / "owner.json").read_text(encoding="utf-8") == before


def test_the_heartbeat_beats_once_a_wait_until_it_is_stopped(tmp_path):
    """REQ-047: brief #607 answer 2 (about once a minute; the wait is injected, no timer)."""
    held = plant(tmp_path, pid=LIVE, started=NOW, beat=NOW)
    token = lock.read_owner(held)["token"]
    times = iter([NOW + timedelta(minutes=k) for k in range(1, 10)])
    waits: list[float] = []
    answers = iter([False, False, True])  # two waits run out, then the run ends

    def wait(seconds: float) -> bool:
        waits.append(seconds)
        return next(answers)

    lock.heartbeat_loop(held, token, lambda: next(times), wait)
    assert waits == [lock.HEARTBEAT] * 3 and lock.HEARTBEAT == 60
    assert lock.read_owner(held)["beat"] == stamp(NOW + timedelta(minutes=2))


def test_a_new_lock_carries_its_first_heartbeat(repo, tmp_path):
    """REQ-047: brief #607 answer 2 (`lock.py run` writes `beat` when it takes the lock)."""
    folder = tmp_path / "locks"
    repo.commit({"agk.toml": f"lock_dir = '{folder.as_posix()}'\n"}, "base")
    owner = folder / "agk-lock-heavy" / "owner.json"
    probe = (
        "import json,sys; d=json.load(open(sys.argv[1], encoding='utf-8'));"
        "print('BEAT', d['beat'][-1], d['beat'] >= d['started'])"
    )
    proc = repo.run("lock.py", "run", "--name", "heavy", "--", PY, "-c", probe, str(owner))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "BEAT Z True" in proc.stdout


# --- answer 4: status prints the holder, its age and the heartbeat's age ------------------------


def test_describe_prints_the_holder_its_age_and_the_heartbeats_age(tmp_path):
    """REQ-047: brief #607 answer 4."""
    held = plant(
        tmp_path, pid=LIVE, started=NOW - timedelta(minutes=95), beat=NOW - timedelta(minutes=2)
    )
    line = lock.describe(lock.read_owner(held), now=NOW)
    assert line.startswith("held by builder-old (pid 424242, host ")
    assert line.endswith("for 95 min; heartbeat 2 min ago")
    assert lock.describe(None, now=NOW) == "held by an unknown owner"


def test_describe_says_when_there_is_no_heartbeat(tmp_path):
    """REQ-047: brief #607 answer 4 (an owner file of an older kit)."""
    held = plant(tmp_path, pid=LIVE, started=NOW - timedelta(minutes=5))
    assert lock.describe(lock.read_owner(held), now=NOW).endswith("for 5 min; no heartbeat")


def test_status_prints_the_heartbeats_age(repo, tmp_path):
    """REQ-047: brief #607 answer 4 (`status` through the command)."""
    folder = tmp_path / "locks"
    repo.commit({"agk.toml": f"lock_dir = '{folder.as_posix()}'\n"}, "base")
    now = datetime.now(UTC)
    plant(
        folder,
        pid=GONE,
        host=ELSEWHERE,
        started=now - timedelta(minutes=30),
        beat=now - timedelta(minutes=3, seconds=10),
    )
    out = repo.run("lock.py", "status", "--name", "heavy").stdout
    assert out.startswith("lock heavy: held by builder-old")
    assert "for 30 min; heartbeat 3 min ago" in out and "stale" not in out


# --- answer 5: the queue runner's own lock behaves the same -------------------------------------


def test_the_runners_slot_is_kept_while_its_runner_lives_whatever_its_age(tmp_path):
    """REQ-047: brief #607 answer 5 (the slot a runner's job holds, as `execute` writes it)."""
    held = plant(tmp_path, pid=LIVE, child=GONE, started=NOW - timedelta(hours=8))
    assert lock.clear_stale([held], "heavy", 120, "", None, now=NOW) is False
    gone = plant(tmp_path / "b", pid=GONE, child=GONE, started=NOW - timedelta(minutes=1))
    assert lock.clear_stale([gone], "heavy", 120, "", None, now=NOW) is True


def test_the_runner_writes_a_heartbeat_into_its_jobs_slot(repo, tmp_path):
    """REQ-047: brief #607 answer 5 (the runner's slot carries `beat` from the runner's clock)."""
    folder = tmp_path.parent / f"{tmp_path.name}-locks"
    text = f"lock_dir = '{folder.as_posix()}'\n[locks]\nqueue = true\n"
    repo.commit({"agk.toml": text}, "settings")
    seen = folder / "seen.json"
    probe = (
        "import shutil,sys; shutil.copy(sys.argv[1], sys.argv[2])"
    )
    command = [PY, "-c", probe, str(folder / "agk-lock-heavy" / "owner.json"), str(seen)]
    head = repo.git("rev-parse", "HEAD").strip()
    job = heavy_queue.new_job(
        session="b1", repository=str(repo.root), branch="main", head=head, command=command,
        folder=".", kind="other", brief=None, priority=heavy_queue.UNKNOWN, submitted=NOW,
    )  # fmt: skip
    heavy_queue.submit(folder / ".agk-lock-heavy.queue", "heavy", job)
    now = [NOW]

    def sleep(seconds: float) -> None:
        now[0] += timedelta(seconds=seconds)

    assert lock.runner(repo.root, "heavy", clock=lambda: now[0], sleep=sleep) == 0
    owner = json.loads(seen.read_text(encoding="utf-8"))
    assert owner["beat"] == owner["started"]
    assert owner["host"] == socket.gethostname()


def test_a_real_live_process_older_than_the_limit_is_not_cleared(tmp_path, monkeypatch):
    """REQ-047: brief #607 answer 1 with the real process check (a sleeping child process)."""
    monkeypatch.undo()
    child = subprocess.Popen([PY, "-c", "import sys; sys.stdin.read()"], stdin=subprocess.PIPE)  # nosec B603 - fixed argument list, no shell
    try:
        held = plant(tmp_path, pid=child.pid, started=NOW - timedelta(hours=9))
        assert reason(held) is None
    finally:
        child.stdin.close()
        child.wait(timeout=10)
    assert reason(held) == "its process no longer runs"
