"""`autopilot.py status`: what the jobs of this machine do, and the week's health figures.

    python3 autopilot.py status [--week] [--root DIR]

Brief #1386, SPEC-0064 build (a), rules 3, 5 and 10 (ADR-0584); `agk status` is its short form.
`status` reads the job records (`<parent of the checkout>/agk-<session>/.agk-session-pid`, with the
`kind=`, `item=` and `head=` that `launch.py` hands the adapters) and lists each running job: its
kind, item, head, since when and its last event (the newest of the record and the log file
`.agk-session.log`). A `claude` process outside every recorded job's process tree is reported as
`unrecorded: process <pid> (not adopted)`, except a person's own steward (`--agent steward`); it
is never adopted as a job. Then it reads the plan and the sweep, the GitHub reads of one
`watchdog --pass` (at most those calls), and prints the queue (the plan's `Start` line), what waits
on the owner (the sweep's `NEEDS-YOU:` lines), the held jobs (those of them that say `held (`) and
one `quiet:` line with the reason no job would start. It posts nothing and writes nothing.

`append_health` is the pass's one line per pass (build (b) calls it) in `agk-autopilot.jsonl` of
the user's temp folder, never the checkout: jobs started by kind, ended, failed, held, pull
requests merged and the seconds from each event to its job's start, with the time; numbers, kinds
and times only, refused otherwise. `status --week` prints the last seven days of that file and the
tokens per merged pull request from `metrics.py --cost`'s local records; a figure it cannot read
is `unknown`, never 0. No network call of its own (verify: the process table is `ps -A -o
pid=,ppid=,args=`; on Windows it is not read and the line says `unknown`).
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists, no shell
import sys
import tempfile
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import conductor
import launch
import metrics
import session
import session_plan
from common import CheckError, utf8_output

HEALTH_FILE = "agk-autopilot.jsonl"
COUNTS = ("ended", "failed", "held", "merged")
USAGE = "usage: autopilot.py status [--week] [--root DIR]"


def stamp(when: datetime) -> str:
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def claude_processes() -> list[tuple[int, int, str]] | None:
    """(pid, parent pid, command line) of every process, or None when it cannot be read."""
    if sys.platform == "win32":
        return None
    try:
        done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["ps", "-A", "-o", "pid=,ppid=,args="],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )  # fmt: skip
    except OSError:
        return None
    if done.returncode:
        return None
    table = []
    for line in done.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            table.append((int(parts[0]), int(parts[1]), parts[2] if len(parts) > 2 else ""))
    return table


def is_claude(args: str) -> bool:
    return any(Path(w).name in ("claude", "claude.exe") for w in args.split()[:2])


def unrecorded(table: list[tuple[int, int, str]], roots: set[int]) -> list[int]:
    """The `claude` processes outside every recorded tree, but a person's own steward."""
    parent = {pid: ppid for pid, ppid, _ in table}

    def recorded(pid: int) -> bool:
        seen: set[int] = set()
        while pid not in seen and pid > 1:
            if pid in roots:
                return True
            seen.add(pid)
            pid = parent.get(pid, 0)
        return False

    return [
        pid
        for pid, _, args in table
        if is_claude(args) and "--agent steward" not in args and not recorded(pid)
    ]


def job_lines(root: Path) -> tuple[list[str], set[int]]:
    """One line per running job of this machine, and the process ids of their records."""
    lines, roots = [], set()
    for worktree, rec in conductor.local_records(root):
        if launch.exited(worktree, rec) or not launch.process_alive(rec["pid"]):
            continue
        roots.add(rec["pid"])
        events = [("start", worktree / launch.RECORD_FILE), ("log", worktree / ".agk-session.log")]
        times = [(p.stat().st_mtime, what) for what, p in events if p.exists()]
        at, what = max(times) if times else (None, "unknown")
        last = f"{what} {stamp(datetime.fromtimestamp(at, UTC))}" if at else "unknown"
        lines.append(
            f"job {rec['session']} {rec.get('kind', 'unknown')} {rec.get('item', 'unknown')} "
            f"head {rec.get('head', 'unknown')} since {rec['started_utc']} last {last}"
        )
    return lines, roots


def paused(root: Path) -> bool:
    try:
        return tomllib.loads((root / "agk.toml").read_text(encoding="utf-8")).get("paused") is True
    except (OSError, ValueError):
        return False


def github_lines(root: Path) -> tuple[list[str], bool]:
    """The queue, owner, held and quiet lines from the plan and the sweep (one pass's reads)."""
    out, ok, quiet = [], True, None
    try:
        code, planned = session.quietly(session_plan.plan, root, False, False, False)
    except CheckError:
        code, planned = 2, ""
    starts = [x for x in planned.splitlines() if x.startswith(("Start ", "Assign "))]
    if code not in (0, 1) or not starts:
        out.append("queue: unknown (the plan cannot be read)")
        ok = False
    else:
        out.append(f"queue: {starts[0]}")
        if starts[0].startswith("Start 0:"):
            quiet = starts[0].removeprefix("Start 0:").strip().rstrip(".")
    try:
        code, swept = session.quietly(conductor.sweep, root)
    except CheckError:
        code, swept = 2, ""
    if code:
        out.append("owner: unknown (the sweep cannot be read)")
        ok = False
    else:
        needs = [x.strip() for x in swept.splitlines() if x.strip().startswith("NEEDS-YOU:")]
        owner = [x for x in needs if " held (" not in x]
        held = [x for x in needs if " held (" in x]
        out += [f"owner: {x}" for x in owner] or ["owner: none"]
        out += [f"held: {x}" for x in held] or ["held: none"]
    if paused(root):
        quiet = "paused (setting: paused)"
    if quiet:
        out.append(f"quiet: {quiet}")
    if kept := conductor.pass_state(root).get("quiet"):  # the supervisor's stop rule (ADR-0585)
        out.append(f"quiet: supervisor: {kept}")
    return out, ok


def status(root: Path) -> int:
    jobs, roots = job_lines(root)
    print(f"jobs: {len(jobs) or 'none'}")
    for line in jobs:
        print(line)
    table = claude_processes()
    if table is None:
        print("unrecorded: unknown (the process table cannot be read)")
    for pid in unrecorded(table or [], roots):
        print(f"unrecorded: process {pid} (not adopted)")
    lines, ok = github_lines(root)
    print("\n".join(lines))
    return 0 if ok else 1


# --- the health file (rule 10) ----------------------------------------------------------------


def health_path() -> Path:
    return Path(tempfile.gettempdir()) / HEALTH_FILE


def whole(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def append_health(figures: dict, now: datetime) -> None:
    """Append one pass's line; CheckError for anything but numbers, the job kinds and the time."""
    if not set(figures) <= {"started", "waits", *COUNTS}:
        raise CheckError("the health line takes numbers only (field: a name it does not know)")
    started = figures.get("started") or {}
    if not isinstance(started, dict) or not set(started) <= set(launch.JOB_KINDS):
        raise CheckError("the health line takes only the job kinds of rule 3 (field started)")
    waits = figures.get("waits") or []
    if not (
        all(whole(v) for v in started.values())
        and all(whole(figures.get(k, 0)) for k in COUNTS)
        and isinstance(waits, list)
        and all(whole(v) for v in waits)
    ):
        raise CheckError("the health line takes numbers only")
    line = {"at": stamp(now), "started": started, "waits": waits}
    line |= {k: figures.get(k, 0) for k in COUNTS}
    with health_path().open("a", encoding="utf-8") as out:
        out.write(json.dumps(line, sort_keys=True) + "\n")


def week_lines(since: datetime, now: datetime) -> list[dict]:
    try:
        text = health_path().read_text(encoding="utf-8")
    except OSError:
        return []
    found = []
    for raw in text.splitlines():
        try:
            line = json.loads(raw)
            at = datetime.strptime(line["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        except (ValueError, KeyError, TypeError):
            continue
        if since <= at <= now:
            found.append(line)
    return found


def week_tokens(root: Path, since: datetime) -> int | None:
    """The tokens of this clone's local session records since SINCE, or None when unknown."""
    try:
        home = metrics.records_home(None)
        replies, _, _, _ = metrics.read_replies(home, metrics.clone_folders(root), since)
    except (CheckError, OSError):
        return None
    totals = [metrics.total_of(r["tokens"]) for r in replies if r["when"] and r["when"] >= since]
    known = [n for n in totals if n is not None]
    return sum(known) if known and len(known) == len(totals) else None


def minutes(seconds: float) -> str:
    return f"{seconds / 60:.1f}".removesuffix(".0")


def week(root: Path, now: datetime) -> int:
    since = now - timedelta(days=7)
    lines = week_lines(since, now)
    kinds: dict[str, int] = {}
    sums = dict.fromkeys(COUNTS, 0)
    waits: list[int] = []
    for line in lines:
        for kind, n in (line.get("started") or {}).items():
            kinds[kind] = kinds.get(kind, 0) + n
        for k in COUNTS:
            sums[k] += line.get(k, 0)
        waits += line.get("waits") or []
    started = sum(kinds.values())
    by_kind = ", ".join(f"{k} {kinds[k]}" for k in sorted(kinds))
    print(f"week {since.date()} to {now.date()} (UTC; this machine's health file, numbers only)")
    print(
        f"jobs: started {started}" + (f" ({by_kind})" if by_kind else "")
        + f", ended {sums['ended']}, failed {sums['failed']}, held {sums['held']}"
    )  # fmt: skip
    if waits:
        mid, top = minutes(median(waits)), minutes(max(waits))
        print(f"event to start: median {mid} min, longest {top} min")
    else:
        print("event to start: unknown")
    tokens = week_tokens(root, since)
    if tokens is None or not sums["merged"]:
        print("tokens per merged pull request: unknown")
    else:
        merged = sums["merged"]
        print(f"tokens per merged pull request: {tokens // merged} ({merged} merged)")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path.cwd()
    if "--root" in args:
        at = args.index("--root")
        if at + 1 >= len(args):
            print(USAGE, file=sys.stderr)
            return 2
        root = Path(args[at + 1])
        del args[at : at + 2]
    if args not in (["status"], ["status", "--week"]):
        print(USAGE, file=sys.stderr)
        return 2
    if args == ["status", "--week"]:
        return week(root, datetime.now(UTC))
    return status(root)


if __name__ == "__main__":
    sys.exit(main())
