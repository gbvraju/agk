"""The heavy-run queue's job files, `submit` and `status` (brief #529, ADR-0264, SPEC-0040 (a)).

REQ-047. With `[locks] queue = true` in agk.toml, `lock.py submit --name heavy --session S
[--kind K] [--brief N] -- <cmd...>` writes one job file for the committed head into
`.agk-lock-heavy.queue/` beside the lock, prints `queued <ticket> position <n> of <m> (head
<sha12>)` at once and never waits on the lock; `lock.py status` adds the order in force, the
running and waiting jobs with an estimated start from past results, and `queue empty`. With no
`[locks]` table, or `queue = false`, nothing changes, no queue folder is made, and `submit` and
`runner` exit 2 naming the setting. The runner is build (b): `runner` exits 2 with `not built yet`.

Every test points `lock_dir` at its own folder, reads saved brief responses from a fake `gh` on
PATH and makes no network call; data is invented (example.com).
"""

from __future__ import annotations

import json
import os
import re
import socket
import sys
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import heavy_queue
import lock
import pytest

PY = sys.executable
STAMP = "%Y-%m-%dT%H:%M:%SZ"
QUEUED = re.compile(
    r"queued (heavy-\d{6}-[0-9a-f]{4}) position (\d+) of (\d+) \(head ([0-9a-f]{12})\)"
)
COMMAND = ["python3", "-c", "print('suite')"]


def stamp(when: datetime) -> str:
    return when.strftime(STAMP)


def settings(repo, folder: Path, locks: str | None = "queue = true\n", extra: str = "") -> None:
    text = f"lock_dir = '{folder.as_posix()}'\n{extra}"
    if locks is not None:
        text += f"[locks]\n{locks}"
    repo.commit({"agk.toml": text}, "settings")


@pytest.fixture
def where(repo, tmp_path) -> Path:
    folder = tmp_path / "locks"
    settings(repo, folder)
    return folder


def queue_of(folder: Path) -> Path:
    return folder / ".agk-lock-heavy.queue"


def job_files(folder: Path) -> list[Path]:
    box = queue_of(folder) / "jobs"
    return sorted(box.glob("*.json")) if box.is_dir() else []


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fake_gh(tmp_path: Path, bodies: dict[int, str]) -> Path:
    """A `gh` on PATH that answers `repos/<o>/<r>/issues/<n>` from saved bodies, else fails."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    saved = tmp_path / "briefs.json"
    saved.write_text(json.dumps({str(k): v for k, v in bodies.items()}), encoding="utf-8")
    script = bin_dir / "gh"
    script.write_text(
        f"#!{PY}\n"
        "import json, sys\n"
        f"data = json.load(open({str(saved)!r}, encoding='utf-8'))\n"
        "path = next((a for a in sys.argv[1:] if a.startswith('repos/')), '')\n"
        "number = path.rsplit('/', 1)[-1]\n"
        "if '/issues/' not in path or number not in data:\n"
        "    sys.stderr.write('HTTP 404: Not Found\\n'); sys.exit(1)\n"
        "print(json.dumps({'number': int(number), 'body': data[number]}))\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return bin_dir


def submit(repo, *args: str, bin_dir: Path | None = None, command=None):
    env = {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"} if bin_dir else {}
    return repo.run(
        "lock.py", "submit", "--name", "heavy", "--session", "b1", *args, "--",
        *(command or COMMAND), **env,
    )


def queued(proc) -> re.Match:
    match = QUEUED.search(proc.stdout)
    assert proc.returncode == 0 and match, proc.stdout + proc.stderr
    return match


def head(repo) -> str:
    return repo.git("rev-parse", "HEAD").strip()


# --- rule 1: off by default ---------------------------------------------------------------------


@pytest.mark.parametrize("locks", [None, "queue = false\n"])
def test_with_the_queue_off_status_and_run_print_what_they_print_today(repo, tmp_path, locks):
    """REQ-047 AC1: SPEC-0040 rule 1; no queue folder is made."""
    folder = tmp_path / "locks"
    settings(repo, folder, locks)
    status = repo.run("lock.py", "status", "--name", "heavy")
    assert (status.returncode, status.stdout, status.stderr) == (0, "lock heavy: free\n", "")
    run = repo.run("lock.py", "run", "--name", "heavy", "--", PY, "-c", "print('hi')")
    assert (run.returncode, run.stdout) == (0, "hi\n")
    assert not queue_of(folder).exists()


@pytest.mark.parametrize("locks", [None, "queue = false\n"])
@pytest.mark.parametrize("action", ["submit", "runner"])
def test_with_the_queue_off_submit_and_runner_exit_2_naming_the_setting(
    repo, tmp_path, locks, action
):
    """REQ-047 AC1: SPEC-0040 rule 1; the setting is named, never a value."""
    folder = tmp_path / "locks"
    settings(repo, folder, locks)
    if action == "submit":
        proc = submit(repo)
    else:
        proc = repo.run("lock.py", "runner", "--name", "heavy")
    assert proc.returncode == 2
    assert "setting: [locks] queue" in proc.stderr
    assert "false" not in proc.stderr
    assert not queue_of(folder).exists()


@pytest.mark.parametrize(
    "locks, key",
    [
        ('queue = "yes"\n', "queue"),
        ("queue = true\nqueue_autostart = 1\n", "queue_autostart"),
        ("queue = true\nqueue_idle_minutes = 0\n", "queue_idle_minutes"),
        ("queue = true\nqueue_idle_minutes = true\n", "queue_idle_minutes"),
        ('queue = true\nqueue_order = "lifo"\n', "queue_order"),
        ("queue = true\nqueue_max_wait = -5\n", "queue_max_wait"),
        ("queue = true\nqueue_max_wait = 2.5\n", "queue_max_wait"),
        ("queue = true\nqueue_colour = 1\n", "queue_colour"),
    ],
)
def test_an_invalid_locks_value_is_refused_naming_the_setting(repo, tmp_path, locks, key):
    """REQ-047 AC1: SPEC-0040 rule 1 (any other value of a `[locks]` key is refused)."""
    settings(repo, tmp_path / "locks", locks)
    for args in (["status", "--name", "heavy"], ["run", "--name", "heavy", "--", PY, "-V"]):
        proc = repo.run("lock.py", *args)
        assert proc.returncode == 2, proc.stdout
        assert f"(setting: [locks] {key})" in proc.stderr
        for value in ('"yes"', "lifo", "-5", "2.5"):
            assert value not in proc.stderr


def test_a_locks_value_that_is_not_a_table_is_refused(repo, tmp_path):
    """REQ-047 AC1: SPEC-0040 rule 1."""
    repo.commit({"agk.toml": f"lock_dir = '{(tmp_path / 'l').as_posix()}'\nlocks = 3\n"})
    proc = repo.run("lock.py", "status", "--name", "heavy")
    assert proc.returncode == 2 and "(setting: [locks])" in proc.stderr


def test_the_defaults_of_the_locks_table():
    """REQ-047 AC1: SPEC-0040 rules 1 and 8 (fifo, 120 minutes, 10 idle minutes, both off)."""
    import common

    assert common.QUEUE_DEFAULTS == {
        "queue": False,
        "queue_autostart": False,
        "queue_idle_minutes": 10,
        "queue_order": "fifo",
        "queue_max_wait": 120,
    }


# --- rules 2 and 3: the queue folder and submit -------------------------------------------------


def test_submit_writes_one_job_with_every_field_and_returns_at_once(repo, where):
    """REQ-047 AC2: SPEC-0040 rules 2 and 3."""
    before = datetime.now(UTC).replace(microsecond=0)
    proc = submit(repo, "--kind", "prepush")
    match = queued(proc)
    ticket = match.group(1)
    assert match.group(2, 3) == ("1", "1") and match.group(4) == head(repo)[:12]
    assert "no runner; start one with lock.py runner --name heavy" in proc.stdout
    files = job_files(where)
    assert [p.name for p in files] == [f"{ticket}.json"]
    job = read(files[0])
    assert set(job) == {
        "schema", "ticket", "seq", "session", "repository", "branch", "head", "command",
        "folder", "kind", "brief", "priority", "submitted",
    }
    assert job["schema"] == 1 and job["ticket"] == ticket and job["seq"] == 1
    assert job["session"] == "b1" and job["branch"] == "main" and job["head"] == head(repo)
    assert Path(job["repository"]).resolve() == repo.root.resolve()
    assert job["command"] == COMMAND and job["folder"] == "." and job["kind"] == "prepush"
    assert job["brief"] is None and job["priority"] == "unknown"
    submitted = datetime.strptime(job["submitted"], STAMP).replace(tzinfo=UTC)
    assert before <= submitted <= datetime.now(UTC)
    assert (queue_of(where) / "seq").read_text(encoding="utf-8").strip() == "2"
    assert not list(queue_of(where).rglob("*.new"))  # written whole, then moved into place


def test_the_kind_is_other_by_default_and_must_be_one_of_three(repo, where):
    """REQ-047 AC2: SPEC-0040 rule 3."""
    queued(submit(repo))
    assert read(job_files(where)[0])["kind"] == "other"
    proc = submit(repo, "--kind", "e2e", command=["python3", "-V"])
    assert proc.returncode == 2 and len(job_files(where)) == 1


def test_submit_never_waits_on_a_held_lock(repo, where):
    """REQ-047 AC2: SPEC-0040 rule 3 (it returns before a held lock is released)."""
    held = where / "agk-lock-heavy"
    held.mkdir(parents=True)
    owner = {
        "session": "builder-other", "pid": os.getpid(), "host": socket.gethostname(),
        "started": stamp(datetime.now(UTC)), "token": "t" * 8,
    }
    (held / "owner.json").write_text(json.dumps(owner), encoding="utf-8")
    queued(submit(repo))
    assert held.is_dir() and (held / "owner.json").is_file()


def test_a_dirty_tracked_tree_writes_no_job_and_exits_2(repo, where):
    """REQ-047 AC2: SPEC-0040 rule 3 (an unrecorded change would be hidden)."""
    repo.write("agk.toml", (repo.root / "agk.toml").read_text(encoding="utf-8") + "# changed\n")
    proc = submit(repo)
    assert proc.returncode == 2 and "uncommitted" in proc.stderr
    assert job_files(where) == []


def test_an_untracked_file_does_not_block_a_submission(repo, where):
    """REQ-047 AC2: SPEC-0040 rule 3 (only changes to tracked files are refused)."""
    repo.write("notes.txt", "scratch\n")
    queued(submit(repo))


def test_submit_has_no_option_that_sets_the_priority(repo, where):
    """REQ-047 AC2: SPEC-0040 rule 3 (a builder cannot type its job ahead)."""
    proc = submit(repo, "--priority", "0")
    assert proc.returncode == 2 and job_files(where) == []


def test_submit_needs_a_session_and_a_command(repo, where):
    """REQ-047 AC2: SPEC-0040 rule 3."""
    no_session = repo.run("lock.py", "submit", "--name", "heavy", "--", *COMMAND)
    no_command = repo.run("lock.py", "submit", "--name", "heavy", "--session", "b1")
    assert no_session.returncode == 2 and no_command.returncode == 2
    assert job_files(where) == []


def test_two_racing_submissions_get_two_sequence_numbers(repo, where):
    """REQ-047 AC2: SPEC-0040 rule 2 (every change is made under the lock's mutex)."""
    held = where / "agk-lock-heavy"
    now = datetime.now(UTC)
    tickets: list[str] = []

    def one(n: int) -> None:
        job = heavy_queue.new_job(
            session=f"b{n}", repository=str(repo.root), branch=f"claude/brief-{n}",
            head=f"{n:040x}", command=COMMAND, folder=".", kind="other", brief=None,
            priority="unknown", submitted=now,
        )
        tickets.append(lock.enqueue(held, "heavy", job, "fifo", 120, now)[0])

    threads = [threading.Thread(target=one, args=(n,)) for n in range(1, 9)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    seqs = sorted(read(p)["seq"] for p in job_files(where))
    assert seqs == list(range(1, 9)) and len(set(tickets)) == 8


@pytest.mark.parametrize(
    "body, want",
    [
        ("Why: x\nPriority: 1\nSize: S\n", 1),
        ("Priority: 0\nMeasured: make test\n", 0),
        ("Why: x\nSize: S\n", "unknown"),
        ("Priority: 5\n", "unknown"),
        ("Priority: 1\nPriority: 2\n", "unknown"),
    ],
)
def test_the_priority_is_read_once_from_the_briefs_priority_line(repo, where, tmp_path, body, want):
    """REQ-047 AC2: SPEC-0040 rule 3; a line that cannot be read is `unknown`, never 0."""
    repo.git("remote", "add", "origin", "https://github.com/example/demo.git")
    bin_dir = fake_gh(tmp_path, {7: body})
    queued(submit(repo, "--brief", "7", bin_dir=bin_dir))
    job = read(job_files(where)[0])
    assert job["brief"] == 7 and job["priority"] == want


def test_an_unreadable_brief_gives_unknown_never_0(repo, where, tmp_path):
    """REQ-047 AC2: SPEC-0040 rule 3 (the GET fails)."""
    repo.git("remote", "add", "origin", "https://github.com/example/demo.git")
    bin_dir = fake_gh(tmp_path, {})
    queued(submit(repo, "--brief", "8", bin_dir=bin_dir))
    job = read(job_files(where)[0])
    assert job["brief"] == 8 and job["priority"] == "unknown"


def test_a_brief_that_is_not_a_number_is_refused(repo, where):
    """REQ-047 AC2: SPEC-0040 rule 3."""
    assert submit(repo, "--brief", "seven").returncode == 2
    assert job_files(where) == []


def test_the_runner_is_not_built_yet_and_says_so(repo, where):
    """REQ-047 AC1: brief #529 answer 2 (a call is never silent)."""
    proc = repo.run("lock.py", "runner", "--name", "heavy")
    assert proc.returncode == 2 and "not built yet" in proc.stderr
    assert not (queue_of(where) / "runner.json").exists()


# --- rule 5: dedupe and replace in place --------------------------------------------------------


def test_a_duplicate_submission_prints_the_first_ticket_and_adds_nothing(repo, where):
    """REQ-047 AC4: SPEC-0040 rule 5."""
    first = queued(submit(repo)).group(1)
    second = queued(submit(repo)).group(1)
    assert first == second and len(job_files(where)) == 1


def test_another_command_is_another_job(repo, where):
    """REQ-047 AC4: SPEC-0040 rule 5 (the command list is compared exactly)."""
    queued(submit(repo))
    match = queued(submit(repo, command=["python3", "-c", "print('suite') "]))
    assert match.group(2, 3) == ("2", "2") and len(job_files(where)) == 2


def test_a_later_head_replaces_the_waiting_job_in_its_position(repo, where):
    """REQ-047 AC4: SPEC-0040 rule 5 (it keeps its sequence number and its waiting time)."""
    repo.branch("claude/brief-1")
    old = queued(submit(repo)).group(1)
    other = queued(submit(repo, command=["python3", "-V"])).group(1)
    old_job = read(queue_of(where) / "jobs" / f"{old}.json")
    repo.commit({"a.txt": "more\n"}, "next step")
    match = queued(submit(repo))
    new = match.group(1)
    assert new != old and match.group(2, 3) == ("1", "2")
    jobs = {read(p)["ticket"]: read(p) for p in job_files(where)}
    assert set(jobs) == {new, other}
    assert jobs[new]["seq"] == old_job["seq"] and jobs[new]["submitted"] == old_job["submitted"]
    assert jobs[new]["head"] == head(repo) != old_job["head"]
    result = read(queue_of(where) / "results" / f"{old}.json")
    assert result["outcome"] == f"replaced by {new}" and result["head"] == old_job["head"]
    assert result["schema"] == 1 and result["ticket"] == old
    shown = repo.run("lock.py", "status", "--name", "heavy", "--ticket", old)
    assert shown.stdout.startswith(f"result {old} replaced by {new} head {old_job['head'][:12]}")


def test_a_replacing_job_reads_its_brief_again(repo, where, tmp_path):
    """REQ-047 AC4: SPEC-0040 rule 5 (its priority is read again from its brief)."""
    repo.git("remote", "add", "origin", "https://github.com/example/demo.git")
    queued(submit(repo, "--brief", "7", bin_dir=fake_gh(tmp_path, {7: "Priority: 3\n"})))
    repo.commit({"a.txt": "more\n"}, "next step")
    (tmp_path / "briefs.json").write_text(json.dumps({"7": "Priority: 1\n"}), encoding="utf-8")
    queued(submit(repo, "--brief", "7", bin_dir=tmp_path / "bin"))
    [job] = [read(p) for p in job_files(where)]
    assert job["priority"] == 1 and job["head"] == head(repo)


def test_a_detached_head_job_is_never_replaced(repo, where):
    """REQ-047 AC4: SPEC-0040 rule 5."""
    repo.git("checkout", "-q", "--detach")
    queued(submit(repo))
    repo.commit({"a.txt": "more\n"}, "next step")
    queued(submit(repo))
    jobs = [read(p) for p in job_files(where)]
    assert [j["branch"] for j in jobs] == ["detached", "detached"] and len(jobs) == 2


def test_a_running_job_is_never_replaced_and_still_dedupes(repo, where):
    """REQ-047 AC4: SPEC-0040 rule 5 (a running job: one the runner marked `started`)."""
    first = queued(submit(repo)).group(1)
    path = queue_of(where) / "jobs" / f"{first}.json"
    job = read(path)
    job["started"] = stamp(datetime.now(UTC))
    path.write_text(json.dumps(job), encoding="utf-8")
    again = submit(repo)
    assert again.returncode == 0 and f"queued {first} running" in again.stdout
    repo.commit({"a.txt": "more\n"}, "next step")
    later = queued(submit(repo))
    assert later.group(1) != first and later.group(2, 3) == ("1", "1")
    assert len(job_files(where)) == 2 and "started" in read(path)


def test_a_finished_job_is_never_reused(repo, where):
    """REQ-047 AC4: SPEC-0040 rule 5 (a new submission after a result runs again)."""
    first = queued(submit(repo)).group(1)
    box = queue_of(where)
    (box / "results").mkdir()
    (box / "jobs" / f"{first}.json").rename(box / "results" / f"{first}.json")
    second = queued(submit(repo))
    assert second.group(1) != first and read(job_files(where)[0])["seq"] == 2


# --- rule 5: the order in force -----------------------------------------------------------------


NOW = datetime(2026, 11, 4, 12, 0, 0, tzinfo=UTC)


def job(seq: int, priority, minutes_ago: float = 0.0, **extra) -> dict:
    return {
        "schema": 1, "ticket": f"heavy-{seq:06d}-abcd", "seq": seq, "session": f"b{seq}",
        "head": f"{seq:040x}", "kind": "prepush", "priority": priority,
        "submitted": stamp(NOW - timedelta(minutes=minutes_ago)), **extra,
    }


def seqs(jobs: list[dict]) -> list[int]:
    return [j["seq"] for j in jobs]


def test_fifo_is_the_sequence_number_only(repo):
    """REQ-047 AC3: SPEC-0040 rule 5 (priorities 3, 0 and 2 keep submission order)."""
    jobs = [job(3, 2), job(1, 3), job(2, 0)]
    assert seqs(heavy_queue.waiting_order(jobs, "fifo", 120, NOW)) == [1, 2, 3]
    plain = [job(3, "unknown"), job(1, "unknown"), job(2, "unknown")]
    assert seqs(heavy_queue.waiting_order(plain, "fifo", 120, NOW)) == [1, 2, 3]


def test_priority_order_is_0_first_and_unknown_last(repo):
    """REQ-047 AC3: SPEC-0040 rule 5 (3, 2, 0, unknown run 0, 2, 3, unknown)."""
    jobs = [job(1, 3), job(2, 2), job(3, 0), job(4, "unknown"), job(5, 2)]
    assert seqs(heavy_queue.waiting_order(jobs, "priority", 120, NOW)) == [3, 2, 5, 1, 4]


def test_an_unreadable_priority_goes_after_every_priority_3(repo):
    """REQ-047 AC3: SPEC-0040 rule 5 (never counted as 0)."""
    jobs = [job(1, None), job(2, 3), job(3, "high"), job(4, 3)]
    assert seqs(heavy_queue.waiting_order(jobs, "priority", 120, NOW)) == [2, 4, 1, 3]


def test_an_overdue_job_goes_first_and_overdue_jobs_go_by_sequence(repo):
    """REQ-047 AC3: SPEC-0040 rule 5 with `queue_max_wait = 1` and a fake clock."""
    jobs = [job(1, 3, minutes_ago=5), job(2, 2, minutes_ago=3), job(3, 0, minutes_ago=0.5)]
    assert seqs(heavy_queue.waiting_order(jobs, "priority", 1, NOW)) == [1, 2, 3]
    assert seqs(heavy_queue.waiting_order(jobs, "priority", 10, NOW)) == [3, 2, 1]


def test_running_jobs_are_not_in_the_waiting_order(repo):
    """REQ-047 AC3: SPEC-0040 rule 5 (the order changes only which waiting job starts next)."""
    jobs = [job(1, 3, started=stamp(NOW)), job(2, 0)]
    for order in ("fifo", "priority"):
        assert seqs(heavy_queue.waiting_order(jobs, order, 120, NOW)) == [2]


# --- rule 7: status and the estimate ------------------------------------------------------------


def result(ticket: str, seconds: int, ended_minutes_ago: float, kind: str = "prepush") -> dict:
    return {
        "schema": 1, "ticket": ticket, "head": "e" * 40, "kind": kind, "outcome": "passed",
        "exit_code": 0, "run_seconds": seconds,
        "ended": stamp(datetime.now(UTC) - timedelta(minutes=ended_minutes_ago)),
    }


def plant_queue(folder: Path, jobs: list[dict], results: list[dict]) -> Path:
    box = queue_of(folder)
    for sub in ("jobs", "results"):
        (box / sub).mkdir(parents=True, exist_ok=True)
    for j in jobs:
        (box / "jobs" / f"{j['ticket']}.json").write_text(json.dumps(j), encoding="utf-8")
    for r in results:
        (box / "results" / f"{r['ticket']}.json").write_text(json.dumps(r), encoding="utf-8")
    (box / "seq").write_text(f"{len(jobs) + len(results) + 1}\n", encoding="utf-8")
    return box


def live_job(seq: int, priority, waited_seconds: int, **extra) -> dict:
    when = datetime.now(UTC) - timedelta(seconds=waited_seconds)
    return {**job(seq, priority), "submitted": stamp(when), **extra}


def snapshot(box: Path) -> dict[str, bytes]:
    return {str(p.relative_to(box)): p.read_bytes() for p in sorted(box.rglob("*")) if p.is_file()}


def five_results() -> list[dict]:
    return [result(f"heavy-00000{n}-beef", 60 * n, 100 - n) for n in range(1, 6)]


def three_jobs() -> list[dict]:
    started = stamp(datetime.now(UTC) - timedelta(seconds=60))
    return [
        live_job(6, 3, 600, started=started),
        live_job(7, 3, 210),
        live_job(8, 0, 150),
    ]


def test_status_shows_the_fifo_queue_with_estimates_and_changes_no_file(repo, where):
    """REQ-047 AC6: SPEC-0040 rule 7 (median 180 s; the running job has 120 s left)."""
    box = plant_queue(where, three_jobs(), five_results())
    before = snapshot(box)
    proc = repo.run("lock.py", "status", "--name", "heavy")
    assert proc.returncode == 0, proc.stderr
    sha = lambda n: f"{n:040x}"[:12]  # noqa: E731
    assert proc.stdout.splitlines() == [
        "lock heavy: free",
        "order: fifo",
        f"running heavy-000006-abcd b6 head {sha(6)} for 1 min",
        f"1. heavy-000007-abcd b7 head {sha(7)} waiting 3 min, start in about 2 min",
        f"2. heavy-000008-abcd b8 head {sha(8)} waiting 2 min, start in about 5 min",
    ]
    assert snapshot(box) == before


def test_status_shows_the_priority_order_with_priorities_and_overdue(repo, tmp_path):
    """REQ-047 AC6: SPEC-0040 rule 7 under `"priority"`; positions are in the order in force."""
    folder = tmp_path / "locks"
    settings(repo, folder, 'queue = true\nqueue_order = "priority"\nqueue_max_wait = 3\n')
    jobs = three_jobs() + [live_job(9, 2, 30)]
    plant_queue(folder, jobs, five_results())
    proc = repo.run("lock.py", "status", "--name", "heavy")
    sha = lambda n: f"{n:040x}"[:12]  # noqa: E731
    assert proc.stdout.splitlines()[1:] == [
        "order: priority, max wait 3 min",
        f"running heavy-000006-abcd b6 head {sha(6)} for 1 min",
        f"1. heavy-000007-abcd b7 head {sha(7)} priority 3 waiting 3 min overdue,"
        " start in about 2 min",
        f"2. heavy-000008-abcd b8 head {sha(8)} priority 0 waiting 2 min, start in about 5 min",
        f"3. heavy-000009-abcd b9 head {sha(9)} priority 2 waiting 0 min, start in about 8 min",
    ]


def test_with_two_past_results_the_start_is_unknown(repo, where):
    """REQ-047 AC6: SPEC-0040 rule 7 (fewer than three results of a kind ahead)."""
    plant_queue(where, three_jobs()[1:], five_results()[:2])
    lines = repo.run("lock.py", "status", "--name", "heavy").stdout.splitlines()
    assert lines[2].endswith("waiting 3 min, start in about 0 min")
    assert lines[3].endswith("waiting 2 min, start unknown")


def test_an_empty_queue_says_so_and_makes_no_folder(repo, where):
    """REQ-047 AC6: SPEC-0040 rule 7."""
    proc = repo.run("lock.py", "status", "--name", "heavy")
    assert proc.stdout.splitlines() == ["lock heavy: free", "order: fifo", "queue empty"]
    assert not queue_of(where).exists()


def test_status_of_one_ticket(repo, where):
    """REQ-047 AC6: SPEC-0040 rule 7 (`status --ticket T`: its line, its result or unknown)."""
    box = plant_queue(where, three_jobs(), five_results())
    (box / "results" / "heavy-000005-beef.out").write_text("ok\n", encoding="utf-8")

    def shown(ticket: str):
        return repo.run("lock.py", "status", "--name", "heavy", "--ticket", ticket)

    waiting = shown("heavy-000008-abcd")
    assert (waiting.returncode, waiting.stdout) == (
        0, f"2. heavy-000008-abcd b8 head {f'{8:040x}'[:12]} waiting 2 min, start in about 5 min\n"
    )
    running = shown("heavy-000006-abcd")
    assert running.stdout.startswith("running heavy-000006-abcd b6 head ")
    done = shown("heavy-000005-beef")
    out = box / "results" / "heavy-000005-beef.out"
    assert done.stdout == f"result heavy-000005-beef passed head {'e' * 12} in 300s, output {out}\n"
    missing = shown("heavy-000099-abcd")
    assert (missing.returncode, missing.stdout) == (1, "unknown ticket\n")


def test_status_of_a_ticket_with_the_queue_off_is_refused(repo, tmp_path):
    """REQ-047 AC1: SPEC-0040 rule 1."""
    settings(repo, tmp_path / "locks", None)
    proc = repo.run("lock.py", "status", "--name", "heavy", "--ticket", "heavy-000001-abcd")
    assert proc.returncode == 2 and "setting: [locks] queue" in proc.stderr


def test_the_estimate_is_divided_by_the_slots_and_rounded_up(repo):
    """REQ-047 AC6: SPEC-0040 rule 7 (summed, divided by the slots, rounded up to a minute)."""
    past = [result(f"heavy-00000{n}-beef", s, 10 - n) for n, s in enumerate((100, 200, 300), 1)]
    ahead = [job(1, 2), job(2, 2), job(3, 2)]
    now = datetime.now(UTC)
    assert heavy_queue.estimate(ahead, past, 1, now) == 10  # 600 s
    assert heavy_queue.estimate(ahead, past, 2, now) == 5
    assert heavy_queue.estimate(ahead[:1], past, 4, now) == 1  # 50 s rounds up
    assert heavy_queue.estimate([], past, 1, now) == 0
    other = [{**job(4, 2), "kind": "proof"}]
    assert heavy_queue.estimate(other, past, 1, now) is None


def test_the_estimate_uses_the_last_ten_results_of_the_kind(repo):
    """REQ-047 AC6: SPEC-0040 rule 7 (the median of the last ten finished results)."""
    old = [result(f"heavy-0000{n:02d}-beef", 9000, 500 - n) for n in range(1, 6)]
    recent = [result(f"heavy-0001{n:02d}-beef", 60, 50 - n) for n in range(1, 11)]
    replaced = [{"schema": 1, "ticket": "heavy-000200-beef", "outcome": "replaced by x"}]
    assert heavy_queue.estimate([job(1, 2)], old + recent + replaced, 1, datetime.now(UTC)) == 1
