"""The heavy-run queue: its folder, job and result files, order and estimate (SPEC-0040 rules 2, 3,
5 and 7; brief #529, ADR-0264).

The queue of a lock NAME is the folder `.agk-lock-NAME.queue/` beside the lock, outside every
repository: `jobs/` (one JSON file per waiting or running job), `results/` (one JSON result, and
the runner's output file, per finished job), `seq` (the next sequence number) and `runner.json`
(the live runner). `lock.py` changes it only under the lock's mutex, and every file is written
whole under a `.new` name and moved into place, so a reader never sees half a file and needs no
mutex. A job is running once the runner (build (b)) has written its `started` time into it.

The order (rule 5): under `fifo` the sequence number only; under `priority` the job's priority (0
first, `unknown` last), then the sequence number, with every job waiting longer than
`queue_max_wait` minutes first, by sequence number. The estimate (rule 7) comes from past results
only. After a result line, `timing_lines` adds one separate line with the timing total of the
result's prepush record (SPEC-0044 rule 3, brief #560). Standard library only; no network, no
process started.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import uuid
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = 1
KINDS = ("prepush", "proof", "other")
UNKNOWN = "unknown"
STAMP = "%Y-%m-%dT%H:%M:%SZ"
LAST = 10  # the last ten finished results of a kind
FEWEST = 3  # with fewer results of a kind ahead, the start is unknown


def queue_folder(held: Path) -> Path:
    """`.agk-lock-NAME.queue/` beside the lock folder `agk-lock-NAME` (slot 1)."""
    return held.parent / f".{held.name.split('.')[0]}.queue"


def stamp(when: datetime) -> str:
    return when.astimezone(UTC).strftime(STAMP)


def moment(text: object) -> datetime | None:
    try:
        return datetime.strptime(str(text), STAMP).replace(tzinfo=UTC)
    except ValueError:
        return None


def write_whole(path: Path, text: str) -> None:
    """Written whole under a name the readers skip, then moved into place."""
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(f"{path.name}.new")
    staged.write_text(text, encoding="utf-8")
    os.replace(staged, path)


def read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def read_all(box: Path) -> list[dict]:
    if not box.is_dir():
        return []
    found = (read_json(p) for p in sorted(box.glob("*.json")))
    return [d for d in found if d is not None and isinstance(d.get("ticket"), str)]


def jobs(folder: Path) -> list[dict]:
    return [j for j in read_all(folder / "jobs") if isinstance(j.get("seq"), int)]


def results(folder: Path) -> list[dict]:
    return read_all(folder / "results")


def running(job: dict) -> bool:
    return moment(job.get("started")) is not None


def new_job(
    *,
    session: str,
    repository: str,
    branch: str,
    head: str,
    command: list[str],
    folder: str,
    kind: str,
    brief: int | None,
    priority: int | str,
    submitted: datetime,
) -> dict:
    """A job without its ticket and sequence number, which `submit` gives it under the mutex."""
    return {
        "schema": SCHEMA,
        "ticket": "",
        "seq": 0,
        "session": session,
        "repository": repository,
        "branch": branch,
        "head": head,
        "command": list(command),
        "folder": folder,
        "kind": kind,
        "brief": brief,
        "priority": priority,
        "submitted": stamp(submitted),
    }


def rank(priority: object) -> int:
    """0 to 3 as written; anything else (`unknown`, unreadable) ranks after 3, never as 0."""
    if isinstance(priority, int) and not isinstance(priority, bool) and 0 <= priority <= 3:
        return priority
    return 4


def waited_minutes(job: dict, now: datetime) -> float:
    submitted = moment(job.get("submitted"))
    return 0.0 if submitted is None else max(0.0, (now - submitted).total_seconds() / 60)


def overdue(job: dict, max_wait: int, now: datetime) -> bool:
    return waited_minutes(job, now) > max_wait


def waiting_order(all_jobs: list[dict], order: str, max_wait: int, now: datetime) -> list[dict]:
    """The waiting jobs in the order in force; a running job is never in it."""
    waiting = [j for j in all_jobs if not running(j)]
    if order != "priority":
        return sorted(waiting, key=lambda j: j["seq"])

    def key(j: dict) -> tuple[int, int, int]:
        if overdue(j, max_wait, now):
            return (0, 0, j["seq"])
        return (1, rank(j.get("priority")), j["seq"])

    return sorted(waiting, key=key)


def next_seq(folder: Path) -> int:
    """The next sequence number, counted on in `seq`; under the mutex."""
    try:
        seq = int((folder / "seq").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        seq = 1 + max((j["seq"] for j in jobs(folder)), default=0)
    write_whole(folder / "seq", f"{seq + 1}\n")
    return seq


def make_ticket(name: str, seq: int) -> str:
    """`NAME-<six digits>-<four hex>`; the random part has no secret meaning."""
    return f"{name}-{seq:06d}-{uuid.uuid4().hex[:4]}"


def same_run(a: dict, b: dict) -> bool:
    """Rule 5: the same repository, head, command and folder, compared exactly."""
    return all(a.get(k) == b.get(k) for k in ("repository", "head", "command", "folder"))


def same_pull(a: dict, b: dict) -> bool:
    """Rule 5: the same repository, branch, session and command, never a detached head (a
    replace also needs a different head, which `submit` checks)."""
    if a.get("branch") == "detached" or b.get("branch") == "detached":
        return False
    return all(a.get(k) == b.get(k) for k in ("repository", "branch", "session", "command"))


def submit(folder: Path, name: str, job: dict) -> tuple[dict, str]:
    """Add `job` under the mutex: (the job in the queue, `new`, `duplicate` or `replaced <old>`).
    A duplicate of a waiting or running job adds nothing; a later head of a waiting job of the
    same pull request takes its sequence number and submitted time, and the replaced ticket gets
    the result `replaced by <ticket>`."""
    present = jobs(folder)
    for other in present:
        if same_run(other, job):
            return other, "duplicate"
    for other in sorted(present, key=lambda j: j["seq"]):
        if running(other) or not same_pull(other, job) or other.get("head") == job.get("head"):
            continue
        placed = {**job, "seq": other["seq"], "submitted": other["submitted"]}
        placed["ticket"] = make_ticket(name, other["seq"])
        write_whole(folder / "jobs" / f"{placed['ticket']}.json", json.dumps(placed, indent=1))
        replaced = {
            "schema": SCHEMA,
            "ticket": other["ticket"],
            "head": other.get("head"),
            "kind": other.get("kind"),
            "outcome": f"replaced by {placed['ticket']}",
            "ended": stamp(datetime.now(UTC)),
        }
        write_whole(folder / "results" / f"{other['ticket']}.json", json.dumps(replaced, indent=1))
        (folder / "jobs" / f"{other['ticket']}.json").unlink(missing_ok=True)
        return placed, f"replaced {other['ticket']}"
    seq = next_seq(folder)
    placed = {**job, "seq": seq, "ticket": make_ticket(name, seq)}
    write_whole(folder / "jobs" / f"{placed['ticket']}.json", json.dumps(placed, indent=1))
    return placed, "new"


def position(folder: Path, ticket: str, order: str, max_wait: int, now: datetime):
    """(n, m): the job's place among the m waiting jobs in the order in force, or None."""
    waiting = waiting_order(jobs(folder), order, max_wait, now)
    for n, j in enumerate(waiting, start=1):
        if j["ticket"] == ticket:
            return n, len(waiting)
    return None


def median_run(kind: object, past: list[dict]) -> float | None:
    """The median `run_seconds` of the last ten finished results of `kind`, or None with fewer
    than three."""
    timed = [
        r
        for r in past
        if r.get("kind") == kind
        and isinstance(r.get("run_seconds"), (int, float))
        and not isinstance(r.get("run_seconds"), bool)
    ]
    timed.sort(key=lambda r: (str(r.get("ended") or ""), r["ticket"]))
    last = [float(r["run_seconds"]) for r in timed[-LAST:]]
    return statistics.median(last) if len(last) >= FEWEST else None


def estimate(ahead: list[dict], past: list[dict], slots: int, now: datetime) -> int | None:
    """Minutes until a job starts: for each job ahead, the median of its kind, less the time a
    running one has run (never below 0), summed, divided by the slots and rounded up; None when a
    kind ahead has fewer than three past results."""
    total = 0.0
    for job in ahead:
        seconds = median_run(job.get("kind"), past)
        if seconds is None:
            return None
        started = moment(job.get("started"))
        if started is not None:
            seconds = max(0.0, seconds - (now - started).total_seconds())
        total += seconds
    return math.ceil(total / max(1, slots) / 60)


def short(sha: object) -> str:
    return str(sha or "?")[:12]


def running_line(job: dict, now: datetime) -> str:
    started = moment(job.get("started")) or now
    minutes = int(max(0.0, (now - started).total_seconds()) // 60)
    who = job.get("session") or "?"
    return f"running {job['ticket']} {who} head {short(job.get('head'))} for {minutes} min"


def waiting_line(
    n: int, job: dict, ahead: list[dict], past: list[dict], settings: dict, slots: int, now
) -> str:
    by_priority = settings["queue_order"] == "priority"
    line = f"{n}. {job['ticket']} {job.get('session') or '?'} head {short(job.get('head'))}"
    if by_priority:
        line += f" priority {job.get('priority') if rank(job.get('priority')) < 4 else UNKNOWN}"
    line += f" waiting {int(waited_minutes(job, now))} min"
    if by_priority and overdue(job, settings["queue_max_wait"], now):
        line += " overdue"
    minutes = estimate(ahead, past, slots, now)
    return line + (", start unknown" if minutes is None else f", start in about {minutes} min")


def result_line(folder: Path, result: dict) -> str:
    outcome = result.get("outcome") or "?"
    line = f"result {result['ticket']} {outcome} head {short(result.get('head'))}"
    seconds = result.get("run_seconds")
    if isinstance(seconds, (int, float)) and not isinstance(seconds, bool):
        line += f" in {int(seconds)}s"
    out = folder / "results" / f"{result['ticket']}.out"
    return line + (f", output {out}" if out.is_file() else "")


def timing_lines(result: dict) -> list[str]:
    """One separate line `  timing <total> s (<source>)` when the result's prepush record (its
    `record` path, SPEC-0040 rule 4) holds a timing total, else none (SPEC-0044 rule 3). The sum
    of the totals of the tests step's runs; the result line and the estimate are unchanged."""
    path = result.get("record")
    record = read_json(Path(path)) if isinstance(path, str) and path else None
    total, sources = 0.0, []
    for step in (record or {}).get("steps") or []:
        if not isinstance(step, dict) or step.get("name") != "tests":
            continue
        for run in step.get("runs") or []:
            timing = run.get("timing") if isinstance(run, dict) else None
            seconds = timing.get("total_seconds") if isinstance(timing, dict) else None
            if isinstance(seconds, (int, float)) and not isinstance(seconds, bool):
                total += seconds
                sources.append(str(timing.get("source")))
    if not sources:
        return []
    return [f"  timing {total:.1f} s ({', '.join(dict.fromkeys(sources))})"]


def status_lines(
    folder: Path, settings: dict, slots: int, now: datetime, ticket: str | None = None
) -> tuple[list[str], int]:
    """The queue's lines of `lock.py status` (rule 7), or the one ticket's line; reads only."""
    present = jobs(folder)
    past = results(folder)
    active = sorted((j for j in present if running(j)), key=lambda j: j["seq"])
    waiting = waiting_order(present, settings["queue_order"], settings["queue_max_wait"], now)
    lines: list[str] = []
    for j in active:
        lines.append(running_line(j, now))
        if j["ticket"] == ticket:
            return [lines[-1]], 0
    for n, j in enumerate(waiting, start=1):
        lines.append(waiting_line(n, j, active + waiting[: n - 1], past, settings, slots, now))
        if j["ticket"] == ticket:
            return [lines[-1]], 0
    if ticket is not None:
        for r in past:
            if r["ticket"] == ticket:
                return [result_line(folder, r), *timing_lines(r)], 0
        return ["unknown ticket"], 1
    if settings["queue_order"] == "priority":
        head = f"order: priority, max wait {settings['queue_max_wait']} min"
    else:
        head = "order: fifo"
    return [head, *(lines or ["queue empty"])], 0


def runner_alive(folder: Path, alive, host: str) -> bool:
    """Whether `runner.json` names a process that runs on this machine."""
    data = read_json(folder / "runner.json")
    if data is None:
        return False
    pid = data.get("pid")
    if data.get("host") != host or not isinstance(pid, int) or isinstance(pid, bool):
        return False
    return bool(alive(pid))
