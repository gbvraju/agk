"""The heavy-step lock: N heavy runs at a time on a machine (brief #337, ADR-0191; brief #426,
ADR-0231).

    python3 scripts/agk/lock.py run --name NAME [--session ID] [--priority P] [--timeout S]
        -- COMMAND [ARG...]
    python3 scripts/agk/lock.py status --name NAME

`run` takes the lock NAME, runs COMMAND without a shell, and releases the lock when the command
ends, also when it fails or is interrupted; its exit code is the command's (127 when it cannot be
started, 130 on an interrupt, 143 on a termination, 128 + n when the command is killed by signal
n). The lock is a folder `agk-lock-NAME` made in one atomic rename, holding `owner.json` (session,
process id, host, start time, a token, and the command's process id once it starts), under the
user's temp folder or `lock_dir` of agk.toml. Taking, clearing and releasing are serialised by a
short mutex beside it (`.agk-lock-NAME.mutex`, made with mkdir), so a lock is removed only after it
is checked under the mutex. While another run holds it, `run` waits and
prints one line at once and then one a minute, naming the holder and its age; `--timeout S` gives
up after S seconds (exit 3). A lock whose process no longer runs on this machine is cleared with a
line saying so; it counts as held while either `lock.py` or its command still runs. `status` prints
the holder, or `free`, and changes nothing.

Brief #607 (ADR-0295, changing the age rule of ADR-0191 and ADR-0231): a lock whose holder still
runs on this machine is never cleared, whatever its age, also after the machine slept. The holder
writes a heartbeat, `beat` in `owner.json`, when it takes the lock and then about once a minute
while it runs. A lock of another host, or one whose process ids cannot be read, is stale only when
its heartbeat (its start, for an owner file without one) is older than `lock_stale_minutes`
(agk.toml, 120 by default), and the line that clears it names the host. `status` and the waiting
lines print the holder, its age and the heartbeat's age. The queue runner's slots follow the same
rules and carry the same heartbeat.

Brief #426 (ADR-0231): `lock_slots` (agk.toml, 1 by default) lets that many runs hold the lock at
once; slot 1 is the folder `agk-lock-NAME` as before, slot k is `agk-lock-NAME.k`, and `status`
prints one line per slot when there are several. All slots share the one mutex. A run that cannot
take a slot at once writes a ticket (`.agk-lock-NAME.tickets/`, with its `--priority`, 0 to 3, 2 by
default) under the mutex; a free slot goes to the lowest priority, then to the oldest ticket, and
the ticket of a process that no longer runs on this machine is dropped with a line saying so. When
the lock of a run whose process no longer runs is cleared, `lock_cleanup` (agk.toml, empty by
default) runs once through `sh -c` with `AGK_LOCK_SESSION` and `AGK_LOCK_PID` of that run; its
output is shown, and a failure is reported and never blocks. The locked command gets
`AGK_LOCK_SESSION`, so a project can label what it starts by session.

Brief #505 (ADR-0254): the locked command also gets `AGK_LOCK_TOKEN`, the token of the slot taken,
and `AGK_LOCK_NAME`, and every process below it inherits them, so `prepush.py` inside a wrapper
finds its caller's slot. The token is a random value with no secret meaning, and it is never
printed.

Brief #529 (ADR-0264, SPEC-0040 build (a)): with `queue = true` in the `[locks]` table of agk.toml,

    python3 scripts/agk/lock.py submit --name NAME --session S [--kind K] [--brief N] -- COMMAND...
    python3 scripts/agk/lock.py status --name NAME [--ticket T]

`submit` writes one job for the committed head into the queue beside the lock (`heavy_queue.py`),
under the lock's mutex and never taking a slot, prints `queued <ticket> position <n> of <m> (head
<sha12>)` and returns at once; a work tree with uncommitted changes to tracked files writes nothing
(exit 2). The job's priority is the `Priority:` line of brief N, read once with one REST GET;
anything unreadable is `unknown`, never 0. A brief that an open brief or open pull request names in
a `Depends-on:` line is raised one level, never to 0, with a `raised` note (amendment 117,
ADR-0274). `status` adds the order in force, the running and
waiting jobs with an estimated start, or `queue empty`. With the setting off, `submit`, `runner`
and `status --ticket` exit 2 naming the setting, and everything else is as before.

Brief #552 (ADR-0274, SPEC-0040 build (b)): `runner --name NAME` claims `runner.json` (a live
runner makes it exit 0 naming it), removes results older than seven days, and then, each pass
under the mutex, fails the jobs that can no longer pass and starts the next waiting jobs in the
order in force while a slot is free. Each job takes a slot with `take` at the default priority,
runs without a shell in a detached worktree of its head outside every repository, and gets its
result beside its ticket; a running job is never stopped by the order. The runner stops after
`queue_idle_minutes` with an empty queue. With `queue_autostart = true`, `submit` starts a
detached runner when none lives.

Brief #566 (SPEC-0040 build (c), rules 9 and 10): `prepush.py --record FILE --queue` and
`proof.py --queue` submit themselves through `queue_self` as one job of kind `prepush` or `proof`,
with `--brief` from the body's `Brief: #n` line and the session from `AGK_SESSION`. `status
--ticket T --head SHA` (the full sha) prints the result line and exits 0 only for a passed result
of exactly that head; `stale (result for <sha12>, asked <sha12>)` or `failed: <result line>` and 1;
`waiting: <line>` or the `running` line and 3 while there is no result; `unknown ticket` and 1.

Standard library only; no network but the one brief GET of `submit --brief`. POSIX and Windows:
a process is looked up with signal 0 on POSIX and with OpenProcess on Windows, where `os.kill`
would end it.
"""

from __future__ import annotations

import ctypes
import json
import os
import re
import shutil
import signal
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import heavy_queue
from common import (
    CheckError,
    config_source,
    lock_cleanup,
    lock_slots,
    long_temp_dir,
    queue_settings,
)

USAGE = (
    "usage: lock.py run --name NAME [--session ID] [--priority P] [--timeout S]"
    " -- COMMAND [ARG...]\n"
    "       lock.py status --name NAME [--ticket T [--head SHA]]\n"
    "       lock.py submit --name NAME --session ID [--kind prepush|proof|other] [--brief N]"
    " -- COMMAND [ARG...]\n"
    "       lock.py runner --name NAME\n"
    "--priority P is 0 to 3 (2 by default); the lowest goes first"
)
QUEUE_OFF = "the heavy-run queue is off (setting: [locks] queue)"
PRIORITY_LINE = re.compile(r"Priority: ([0-3])")
DEPENDS = re.compile(r"Depends-on: #(\d+)")
BRIEF_LINE = re.compile(r"Brief: #([1-9][0-9]*)")
FULL_SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
STALE_MINUTES = 120
HEARTBEAT = 60  # seconds between two heartbeats of a holder (brief #607)
POLL = 0.5  # seconds between two tries
ANNOUNCE = 60  # seconds between two waiting lines
STILL_ACTIVE = 259  # GetExitCodeProcess: the process has not ended
QUERY = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
MUTEX_STALE = 10.0  # seconds: a mutex this old was left by a process that died holding it
PRIORITY = 2  # the default priority, as for briefs; 0 goes first
PRIORITIES = range(0, 4)
DEAD = "its process no longer runs"
STOP_WAIT = 15  # seconds a stopped runner waits for each job to write its result
CLEANUP_TIMEOUT = 300  # seconds a cleanup may take before it is ended and reported (Q-426-3)


class Usage(Exception):
    """A usage error or a refused setting (exit 2)."""


class Stopped(Exception):
    """A termination signal arrived while the lock is held."""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


def parse_args(args: list[str]) -> dict:
    if not args or args[0] not in ("run", "status", "submit", "runner"):
        raise Usage(USAGE)
    options: dict = {
        "action": args[0],
        "name": None,
        "session": None,
        "timeout": None,
        "priority": None,
        "ticket": None,
        "kind": None,
        "brief": None,
        "head": None,
    }
    rest = args[1:]
    command: list[str] | None = None
    if "--" in rest:
        cut = rest.index("--")
        rest, command = rest[:cut], rest[cut + 1 :]
    i = 0
    while i < len(rest):
        arg = rest[i]
        allowed = {
            "run": ("--name", "--session", "--timeout", "--priority"),
            "status": ("--name", "--ticket", "--head"),
            "submit": ("--name", "--session", "--kind", "--brief"),
            "runner": ("--name",),
        }[options["action"]]
        if arg in allowed and i + 1 < len(rest) and options[arg[2:]] is None:
            options[arg[2:]] = rest[i + 1]
            i += 2
        else:
            raise Usage(USAGE)
    if not options["name"] or not NAME.fullmatch(options["name"]):
        raise Usage(USAGE)
    if options["action"] in ("status", "runner"):
        head = options["head"]
        if command is not None or (head and not (options["ticket"] and FULL_SHA.fullmatch(head))):
            raise Usage(USAGE)  # `--head` is the full sha of the head asked for (rule 10)
        return options
    if options["action"] == "submit":
        return submit_options(options, command)
    if not command:
        raise Usage(USAGE)
    if options["timeout"] is not None:
        try:
            options["timeout"] = float(options["timeout"])
        except ValueError:
            raise Usage(USAGE) from None
        if options["timeout"] < 0:
            raise Usage(USAGE)
    priority = options["priority"]
    if priority is None:
        options["priority"] = PRIORITY
    elif not re.fullmatch(r"[0-9]", priority) or int(priority) not in PRIORITIES:
        raise Usage(USAGE)
    else:
        options["priority"] = int(priority)
    options["command"] = command
    return options


def submit_options(options: dict, command: list[str] | None) -> dict:
    """`submit`: a session and a command are needed; the kind is one of three, `other` by
    default; the brief is a positive whole number. No option sets the priority (rule 3)."""
    if not command or not options["session"]:
        raise Usage(USAGE)
    options["kind"] = options["kind"] or "other"
    if options["kind"] not in heavy_queue.KINDS:
        raise Usage(USAGE)
    brief = options["brief"]
    if brief is not None:
        if not re.fullmatch(r"[1-9][0-9]*", brief):
            raise Usage(USAGE)
        options["brief"] = int(brief)
    options["command"] = command
    return options


def git(cwd: Path | None, *args: str) -> tuple[int, str]:
    """One git call without a shell: (its exit code, its output); 127 when git cannot start."""
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return 127, ""
    return proc.returncode, proc.stdout


def repo_root() -> Path:
    """The work tree's top folder, or the current folder outside one."""
    code, out = git(None, "rev-parse", "--show-toplevel")
    return Path(out.strip()) if code == 0 else Path.cwd()


def settings(root: Path) -> dict:
    try:
        source = config_source(root)
    except (OSError, ValueError):
        raise Usage("agk.toml cannot be read (path class: agk.toml)") from None
    return source


def lock_folder(root: Path, name: str) -> Path:
    folder = settings(root).get("lock_dir") or ""
    if not isinstance(folder, str):
        raise Usage("lock_dir must be a folder path (setting: lock_dir)")
    base = Path(folder).expanduser() if folder else Path(tempfile.gettempdir())
    return base / f"agk-lock-{name}"


def slots_setting(root: Path) -> int:
    settings(root)  # an unreadable agk.toml is refused first, naming the file
    try:
        return lock_slots(root)
    except CheckError as exc:
        raise Usage(str(exc)) from None


def cleanup_setting(root: Path) -> str:
    settings(root)
    try:
        return lock_cleanup(root)
    except CheckError as exc:
        raise Usage(str(exc)) from None


def slot_folders(held: Path, slots: int) -> list[Path]:
    """Slot 1 is the lock folder itself, as with one slot; slot k is `<lock>.k` (a name cannot
    hold a dot, so no other lock's folder is ever a slot)."""
    return [held] + [held.with_name(f"{held.name}.{k}") for k in range(2, slots + 1)]


def base_name(held: Path) -> str:
    return held.name.split(".")[0]


def ticket_box(held: Path) -> Path:
    return held.parent / f".{base_name(held)}.tickets"


def stale_minutes(root: Path) -> int:
    value = settings(root).get("lock_stale_minutes", STALE_MINUTES)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise Usage(
            "lock_stale_minutes must be a positive whole number (setting: lock_stale_minutes)"
        )
    return value


def pid_alive(pid: int, windows: bool = os.name == "nt", kernel=None) -> bool:
    """Whether process `pid` runs on this machine. Windows: OpenProcess and GetExitCodeProcess,
    because `os.kill` there ends the process; POSIX: signal 0, which only looks."""
    if pid <= 0:
        return False
    if windows:
        k = kernel if kernel is not None else ctypes.WinDLL("kernel32")
        handle = k.OpenProcess(QUERY, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not k.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            k.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # it runs, under another user
    except OSError:
        return False
    return True


def read_owner(held: Path) -> dict | None:
    try:
        data = json.loads((held / "owner.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def minutes_since(owner: dict, key: str, now: datetime | None = None) -> float | None:
    """Minutes since the owner file's time `key` (`started` or `beat`), or None when unreadable."""
    try:
        then = datetime.strptime(str(owner[key]), "%Y-%m-%dT%H:%M:%SZ")
    except (KeyError, ValueError):
        return None
    now = now or datetime.now(UTC)
    return (now - then.replace(tzinfo=UTC)).total_seconds() / 60


def age_minutes(owner: dict, now: datetime | None = None) -> float | None:
    return minutes_since(owner, "started", now)


def beat_minutes(owner: dict, now: datetime | None = None) -> float | None:
    """Minutes since the holder's last heartbeat; an owner file without one (an older kit) has
    its start as its last sign of life."""
    if "beat" in owner:
        return minutes_since(owner, "beat", now)
    return age_minutes(owner, now)


def stale_reason(
    owner: dict | None, held: Path, limit: int, now: datetime | None = None
) -> str | None:
    """Why a lock may be cleared, or None while its owner may still hold it (brief #607): a holder
    of this machine whose process ids can be read is judged by them alone, never by age; any
    other holder by the age of its heartbeat."""
    if owner is None:
        # Taken in one rename with its owner file, so a folder without one is a leftover; it is
        # cleared only once it is older than the limit, by the folder's own time.
        try:
            stamp = now.timestamp() if now is not None else time.time()
            minutes = (stamp - held.stat().st_mtime) / 60
        except OSError:
            return None
        return f"it has no owner file and is older than {limit} min" if minutes > limit else None
    host = owner.get("host")
    if host == socket.gethostname() and holder_pids(owner):
        return None if holder_alive(owner) else DEAD
    minutes = beat_minutes(owner, now)
    if minutes is None or minutes > limit:
        return (
            f"its heartbeat from host {host or 'unknown'} is older than {limit} min,"
            " setting: lock_stale_minutes"
        )
    return None


def holder_pids(owner: dict) -> list[int]:
    """The process ids of the holder (`lock.py`) and of its command, as far as they can be read."""
    pids = [owner.get("pid"), owner.get("child")]
    return [p for p in pids if isinstance(p, int) and not isinstance(p, bool) and p > 0]


def holder_alive(owner: dict) -> bool:
    """The lock is held while `lock.py` or the command it started still runs: a holder killed
    with SIGKILL leaves its command running, and that command still holds the machine."""
    return any(pid_alive(p) for p in holder_pids(owner))


@contextmanager
def mutex(held: Path):
    """A short mutex beside the lock (`.<lock>.mutex`, made with mkdir) that serialises taking,
    clearing and releasing, so a lock is only removed after it is checked under the mutex. A
    mutex older than MUTEX_STALE seconds was left by a process that died inside it. Every slot of
    a lock, and its tickets, share the mutex of slot 1."""
    held.parent.mkdir(parents=True, exist_ok=True)
    gate = held.parent / f".{base_name(held)}.mutex"
    while True:
        try:
            os.mkdir(gate)
            break
        except FileExistsError:
            try:
                age = time.time() - gate.stat().st_mtime
            except OSError:
                continue  # released meanwhile
            if age > MUTEX_STALE:
                try:
                    os.rmdir(gate)
                except OSError:
                    pass
                continue
            time.sleep(0.02)
    try:
        yield
    finally:
        try:
            os.rmdir(gate)
        except OSError:
            pass


def describe(owner: dict | None, now: datetime | None = None) -> str:
    """The holder, its age and the heartbeat's age (brief #607 answer 4)."""
    if owner is None:
        return "held by an unknown owner"
    minutes = age_minutes(owner, now)
    age = f"for {int(minutes)} min" if minutes is not None else "since an unknown time"
    beat = minutes_since(owner, "beat", now) if "beat" in owner else None
    pulse = f"heartbeat {max(0, int(beat))} min ago" if beat is not None else "no heartbeat"
    child = f", command pid {owner['child']}" if owner.get("child") else ""
    return (
        f"held by {owner.get('session') or 'an unknown session'} "
        f"(pid {owner.get('pid')}{child}, host {owner.get('host')}) {age}; {pulse}"
    )


def try_take(held: Path, owner: dict) -> bool:
    """One try under the mutex: the folder with its owner file is renamed into place, so a lock
    folder never exists without its owner file; it fails while the lock folder exists."""
    with mutex(held):
        return place(held, owner)


def place(held: Path, owner: dict) -> bool:
    """The take itself, for a caller that holds the mutex."""
    if held.exists():
        return False
    staging = Path(tempfile.mkdtemp(prefix=f".{held.name}.", dir=held.parent))
    try:
        (staging / "owner.json").write_text(json.dumps(owner), encoding="utf-8")
        os.rename(staging, held)
        return True
    except OSError:
        return False
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def ticket_of(owner: dict, priority: int) -> dict:
    return {
        "session": owner.get("session") or "",
        "pid": owner.get("pid"),
        "host": owner.get("host"),
        "priority": priority,
        "created": time.time_ns(),
        "token": owner["token"],
    }


def turn_key(ticket: dict) -> tuple[int, int, str]:
    """A free slot goes to the lowest priority, then to the oldest ticket."""
    return (ticket["priority"], ticket["created"], ticket["token"])


def valid_ticket(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    numbers = (data.get("priority"), data.get("created"), data.get("pid"))
    return all(isinstance(n, int) and not isinstance(n, bool) for n in numbers) and isinstance(
        data.get("token"), str
    )


def ticket_file(box: Path, ticket: dict) -> Path:
    return box / f"{ticket['created']:020d}-{ticket['token']}.json"


def write_ticket(box: Path, ticket: dict) -> None:
    """Written whole under a name the readers skip, then moved into place."""
    path = ticket_file(box, ticket)
    if path.exists():
        return
    box.mkdir(parents=True, exist_ok=True)
    staged = box / f"{path.name}.new"
    staged.write_text(json.dumps(ticket), encoding="utf-8")
    os.replace(staged, path)


def drop_ticket(box: Path, ticket: dict) -> None:
    """Remove this run's ticket, and the ticket folder once it is empty; under the mutex."""
    try:
        ticket_file(box, ticket).unlink()
    except OSError:
        pass
    try:
        box.rmdir()
    except OSError:
        pass  # other runs still wait, or it was never made


def waiting_others(box: Path, mine: dict) -> tuple[list[dict], list[str]]:
    """The live tickets of other runs, and the sessions whose dead tickets were dropped. A ticket
    that cannot be read is a leftover (tickets are moved into place whole) and is dropped too."""
    others: list[dict] = []
    dropped: list[str] = []
    if not box.is_dir():
        return others, dropped
    here = socket.gethostname()
    for path in sorted(box.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        if not valid_ticket(data):
            path.unlink(missing_ok=True)
            continue
        if data["token"] == mine["token"]:
            continue
        if data.get("host") == here and not pid_alive(data["pid"]):
            path.unlink(missing_ok=True)
            dropped.append(data.get("session") or "an unknown session")
            continue
        others.append(data)
    return others, dropped


def try_turn(
    folders: list[Path], box: Path, owner: dict, mine: dict
) -> tuple[Path | None, int, list[str]]:
    """One try under the mutex: (the slot taken or None, how many waiting runs go first, the
    sessions whose dead tickets were dropped). A run takes a free slot only when fewer runs go
    before it than there are free slots; otherwise it leaves its ticket and waits."""
    with mutex(folders[0]):
        others, dropped = waiting_others(box, mine)
        ahead = sum(1 for t in others if turn_key(t) < turn_key(mine))
        free = [f for f in folders if not f.exists()]
        if ahead < len(free):
            for folder in free:
                if place(folder, owner):
                    drop_ticket(box, mine)
                    return folder, ahead, dropped
        write_ticket(box, mine)
        return None, ahead, dropped


def clear_if_same(held: Path, token: str | None) -> bool:
    """Remove the lock only when, under the mutex, it is still the one whose token is `token`
    (None: a folder without an owner file). A lock taken again since it was judged is kept."""
    with mutex(held):
        if not held.exists() or (read_owner(held) or {}).get("token") != token:
            return False
        shutil.rmtree(held, ignore_errors=True)
        return not held.exists()


def update_owner(held: Path, token: str, **fields) -> None:
    """Set `fields` in this run's owner file, under the mutex; a lock taken again by another run
    (another token) is never written."""
    with mutex(held):
        owner = read_owner(held)
        if (owner or {}).get("token") != token:
            return
        owner.update(fields)
        staged = held / "owner.json.new"
        staged.write_text(json.dumps(owner), encoding="utf-8")
        os.replace(staged, held / "owner.json")


def record_child(held: Path, token: str, child: int) -> None:
    """Add the command's process id to this run's owner file, under the mutex."""
    update_owner(held, token, child=child)


def beat(held: Path, token: str, now: datetime) -> None:
    """One heartbeat: `beat` in this run's owner file is `now` (brief #607 answer 2)."""
    update_owner(held, token, beat=now.strftime("%Y-%m-%dT%H:%M:%SZ"))


def heartbeat_loop(held: Path, token: str, clock, wait) -> None:
    """Beat after each `wait(HEARTBEAT)` that runs out, until `wait` says the run ended. A machine
    that slept resumes here when it wakes; a failed write is tried again at the next beat."""
    while not wait(HEARTBEAT):
        try:
            beat(held, token, clock())
        except OSError:
            pass


@contextmanager
def heartbeat(held: Path, token: str, clock=None):
    """Keep this run's heartbeat going in a daemon thread while the block runs."""
    clock = clock or (lambda: datetime.now(UTC))
    done = threading.Event()
    thread = threading.Thread(
        target=heartbeat_loop, args=(held, token, clock, done.wait), daemon=True
    )
    thread.start()
    try:
        yield
    finally:
        done.set()
        thread.join(timeout=5)


def take(
    held: Path,
    name: str,
    owner: dict,
    limit: int,
    timeout: float | None,
    slots: int = 1,
    priority: int = PRIORITY,
    cleanup: str = "",
    root: Path | None = None,
) -> Path | None:
    """Wait for a slot in turn and take it; the slot's folder, or None after `timeout`. Called as
    `prepush.py` calls it (merged in #422), it is the one-slot lock of before, with a ticket at the
    default priority and no cleanup."""
    folders = slot_folders(held, slots)
    box = ticket_box(held)
    mine = ticket_of(owner, priority)
    began = time.monotonic()
    announced: float | None = None
    taken: Path | None = None
    try:
        while True:
            taken, ahead, dropped = try_turn(folders, box, owner, mine)
            for who in dropped:
                print(f"lock {name}: dropped the ticket of {who} ({DEAD})", flush=True)
            if taken is not None:
                if announced is not None:
                    print(f"lock {name}: taken", flush=True)
                return taken
            if clear_stale(folders, name, limit, cleanup, root):
                continue
            now = time.monotonic()
            state = waiting_state(folders, ahead)
            if timeout is not None and now - began >= timeout:
                print(f"lock {name}: not taken after {timeout:g} s; {state}", flush=True)
                return None
            if announced is None or now - announced >= ANNOUNCE:
                print(f"lock {name}: waiting; {state}", flush=True)
                announced = now
            time.sleep(POLL)
    finally:
        if taken is None:
            with mutex(held):
                drop_ticket(box, mine)


def clear_stale(
    folders: list[Path],
    name: str,
    limit: int,
    cleanup: str,
    root: Path | None,
    now: datetime | None = None,
) -> bool:
    """Clear each stale slot, each once (a lock taken again since it was judged is kept), and run
    the cleanup after each dead run cleared here. Whether any slot was cleared."""
    cleared = False
    for folder in folders:
        if not folder.exists():
            continue
        current = read_owner(folder)
        reason = stale_reason(current, folder, limit, now)
        if reason is None:
            continue
        who = (current or {}).get("session") or "an unknown session"
        if clear_if_same(folder, (current or {}).get("token")):
            print(f"lock {name}: cleared a stale lock of {who} ({reason})", flush=True)
            after_clear(name, current, reason, cleanup, root)
            cleared = True
    return cleared


def waiting_state(folders: list[Path], ahead: int) -> str:
    """The holders (one slot: `held by ...` as before; several: `slot k held by ...`), and how
    many waiting runs go first."""
    parts: list[str] = []
    for k, folder in enumerate(folders, start=1):
        if not folder.exists():
            continue
        line = describe(read_owner(folder))
        parts.append(line if len(folders) == 1 else f"slot {k} {line}")
    if ahead:
        parts.append(f"{ahead} waiting run{'s go' if ahead > 1 else ' goes'} first")
    return "; ".join(parts) or "a slot is being freed"


def after_clear(
    name: str, owner: dict | None, reason: str, cleanup: str, root: Path | None
) -> None:
    """Run `lock_cleanup` once for a dead run whose lock was just cleared here. It is not run for
    a lock that names no session (the cleanup could not be aimed), nor for one cleared by age,
    whose run may still go on (Q-426-2)."""
    if not cleanup:
        return
    session = (owner or {}).get("session") or ""
    if not session:
        print(f"lock {name}: cleanup not run (the lock names no session, setting: lock_cleanup)")
        return
    if reason != DEAD:
        print(f"lock {name}: cleanup not run (the run may still go on, setting: lock_cleanup)")
        return
    pid = owner.get("pid") if owner else None
    print(f"lock {name}: cleanup of {session} (setting: lock_cleanup)", flush=True)
    code = run_cleanup(cleanup, root or Path.cwd(), session, pid if isinstance(pid, int) else None)
    if code == 0:
        print(f"lock {name}: cleanup of {session} done (setting: lock_cleanup)", flush=True)
    elif code is None:
        print(
            f"lock {name}: the cleanup of {session} did not end within {CLEANUP_TIMEOUT} s and was"
            " stopped (setting: lock_cleanup)",
            flush=True,
        )
    elif code == 127:
        print(
            f"lock {name}: the cleanup of {session} cannot be started (setting: lock_cleanup)",
            flush=True,
        )
    else:
        print(
            f"lock {name}: the cleanup of {session} failed (exit {code}, setting: lock_cleanup)",
            flush=True,
        )


def run_cleanup(command: str, root: Path, session: str, pid: int | None) -> int | None:
    """The cleanup through `sh -c`, its output shown as it comes; its exit code (127 when it cannot
    be started, 128 + n when killed by signal n), or None when it did not end in time."""
    env = {**os.environ, "AGK_LOCK_SESSION": session, "AGK_LOCK_PID": str(pid or "")}
    group = os.name != "nt"
    try:
        proc = subprocess.Popen(  # nosec B603 B607 - the project's own cleanup command line
            ["sh", "-c", command],
            cwd=root,
            env=env,
            stdin=subprocess.DEVNULL,
            start_new_session=group,
        )
    except OSError:
        return 127
    try:
        code = proc.wait(timeout=CLEANUP_TIMEOUT)
    except subprocess.TimeoutExpired:
        if group:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
        proc.kill()
        proc.wait()
        return None
    return 128 - code if code < 0 else code


def queue_setting(root: Path) -> dict:
    settings(root)
    try:
        return queue_settings(root)
    except CheckError as exc:
        raise Usage(str(exc)) from None


def brief_priority(root: Path, number: int | None) -> int | str:
    """The single `Priority:` line (0 to 3) of brief `number`, read once with one REST GET the
    way `session.py` reads a brief; no brief, a failed read, no line, several lines or a value
    outside 0 to 3 is `unknown`, never 0 (SPEC-0040 rule 3)."""
    if number is None:
        return heavy_queue.UNKNOWN
    try:
        import session  # only here: the one read of GitHub that `submit --brief` makes

        data = session.gh(f"repos/{session.repo_name(root)}/issues/{number}")
    except (CheckError, OSError, ValueError):
        return heavy_queue.UNKNOWN
    body = data.get("body") if isinstance(data, dict) else None
    if not isinstance(body, str):
        return heavy_queue.UNKNOWN
    lines = [x.strip() for x in body.splitlines() if x.startswith("Priority:")]
    match = PRIORITY_LINE.fullmatch(lines[0]) if len(lines) == 1 else None
    return int(match.group(1)) if match else heavy_queue.UNKNOWN


def unblocks(root: Path, number: int) -> list[int]:
    """The open briefs (label `agk-brief`) and open pull requests, other than brief `number`
    itself, with a `Depends-on: #<number>` line, read once at submission (amendment 117 to
    SPEC-0040 rule 5, ADR-0274). A failed read is no item, so it never raises a priority."""
    try:
        import session  # only here, like `brief_priority`

        items = session.pages(f"repos/{session.repo_name(root)}/issues?state=open")
    except (CheckError, OSError, ValueError):
        return []
    found: list[int] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get("number"), int):
            continue
        labels = {x.get("name") for x in item.get("labels") or [] if isinstance(x, dict)}
        body = item.get("body") if isinstance(item.get("body"), str) else ""
        named = {int(m.group(1)) for x in body.splitlines() if (m := DEPENDS.fullmatch(x.strip()))}
        kind_ok = "pull_request" in item or "agk-brief" in labels
        if kind_ok and item["number"] != number and number in named:
            found.append(item["number"])
    return sorted(found)


def raised(priority: int | str, blocked: list[int]) -> tuple[int | str, str | None]:
    """One level up for a job whose brief unblocks others: 3 to 2, 2 to 1, never to 0, which stays
    the red-default-branch brief's (Q-552-3); `unknown` and 0 and 1 stay as read (Q-552-4)."""
    if not blocked or not isinstance(priority, int) or priority < 2:
        return priority, None
    return priority - 1, "raised: unblocks " + ", ".join(f"#{n}" for n in blocked)


def enqueue(
    held: Path, name: str, job: dict, order: str, max_wait: int, now: datetime
) -> tuple[str, str, tuple[int, int] | None, bool]:
    """Add the job under the lock's mutex: (its ticket, how, its position among the waiting,
    whether a live runner will see it). The runner check shares the mutex with the runner's own
    decision to stop (`idle_stop`), so a job is never left waiting with no runner."""
    folder = heavy_queue.queue_folder(held)
    with mutex(held):
        placed, how = heavy_queue.submit(folder, name, job)
        place = heavy_queue.position(folder, placed["ticket"], order, max_wait, now)
        alive = heavy_queue.runner_alive(folder, pid_alive, socket.gethostname())
        return placed["ticket"], how, place, alive


def submit_job(root: Path, held: Path, options: dict, queue: dict) -> int:
    """`lock.py submit` (SPEC-0040 rule 3): one job for the committed head, at once."""
    name = options["name"]
    code, top = git(None, "rev-parse", "--show-toplevel")
    if code != 0:
        raise Usage(f"lock {name}: submit runs inside a git work tree")
    top_folder = Path(top.strip())
    code, dirty = git(top_folder, "status", "--porcelain", "--untracked-files=no")
    if code != 0 or dirty.strip():
        raise Usage(
            f"lock {name}: the work tree has uncommitted changes to tracked files; commit them"
            " first, because a job runs on the committed head (nothing queued)"
        )
    code, sha = git(top_folder, "rev-parse", "HEAD")
    if code != 0:
        raise Usage(f"lock {name}: the work tree has no commit (nothing queued)")
    code, branch = git(top_folder, "symbolic-ref", "--short", "-q", "HEAD")
    try:
        here = Path.cwd().resolve().relative_to(top_folder.resolve()).as_posix()
    except ValueError:
        here = "."
    now = datetime.now(UTC)
    job = heavy_queue.new_job(
        session=options["session"],
        repository=str(top_folder),
        branch=branch.strip() if code == 0 and branch.strip() else "detached",
        head=sha.strip(),
        command=options["command"],
        folder=here or ".",
        kind=options["kind"],
        brief=options["brief"],
        priority=brief_priority(root, options["brief"]),
        submitted=now,
    )
    if options["brief"] is not None and isinstance(job["priority"], int):
        blocked = unblocks(root, options["brief"])
        job["priority"], note = raised(job["priority"], blocked)
        if note:
            job["raised"] = note
        if blocked:
            job["unblocks"] = blocked  # first within its priority (the ruling on Q-552-3)
    ticket, how, place, alive = enqueue(
        held, name, job, queue["queue_order"], queue["queue_max_wait"], now
    )
    where = "running" if place is None else f"position {place[0]} of {place[1]}"
    print(f"queued {ticket} {where} (head {job['head'][:12]})", flush=True)
    if alive:
        return 0
    if queue["queue_autostart"]:
        print(f"runner started (pid {start_runner(root, name)})", flush=True)
    else:
        print(f"no runner; start one with lock.py runner --name {name}", flush=True)
    return 0


def ticket_for_head(
    folder: Path, queue: dict, slots: int, ticket: str, head: str
) -> tuple[list[str], int]:
    """`status --ticket T --head H` (SPEC-0040 rule 10): the result line and 0 only for a passed
    result of exactly head H; `stale` or `failed` and 1; `waiting` or `running` and 3."""
    for result in heavy_queue.results(folder):
        if result.get("ticket") != ticket:
            continue
        if result.get("head") != head:
            asked = f"result for {heavy_queue.short(result.get('head'))}, asked {head[:12]}"
            return [f"stale ({asked})"], 1
        line = heavy_queue.result_line(folder, result)
        return ([line], 0) if result.get("outcome") == "passed" else ([f"failed: {line}"], 1)
    lines, code = heavy_queue.status_lines(folder, queue, slots, datetime.now(UTC), ticket)
    if code != 0:
        return lines, 1  # `unknown ticket`: no evidence
    return [lines[0] if lines[0].startswith("running ") else f"waiting: {lines[0]}"], 3


def brief_of(body: str | None) -> int | None:
    """The number of the one `Brief: #n` line of a body file, or None (SPEC-0040 rule 3)."""
    try:
        text = Path(body).read_text(encoding="utf-8") if body and body != "-" else ""
    except (OSError, UnicodeDecodeError):
        return None
    found = [m.group(1) for x in text.splitlines() if (m := BRIEF_LINE.fullmatch(x.strip()))]
    return int(found[0]) if len(found) == 1 else None


def queue_self(tool: str, kind: str, script: Path, args: list[str], body: str | None) -> int:
    """`prepush.py --queue` and `proof.py --queue` (SPEC-0040 rule 9): submit `script` with `args`
    (the same command without `--queue`, its file paths already absolute, rule 6) as one heavy job
    of `kind`, with `--brief` from the body's `Brief: #n` line, and return at once."""
    try:
        enabled = queue_setting(repo_root())["queue"]
    except Usage as exc:
        print(exc, file=sys.stderr)
        return 2
    if not enabled:
        print(f"{tool} --queue: {QUEUE_OFF}", file=sys.stderr)
        return 2
    session = os.environ.get("AGK_SESSION") or ""
    if not session:
        print(f"{tool} --queue: a job names its session (setting: AGK_SESSION)", file=sys.stderr)
        return 2
    try:
        inside = script.resolve().is_relative_to(repo_root().resolve())
        path = os.path.relpath(script.resolve(), Path.cwd().resolve()) if inside else None
    except ValueError:  # another drive on Windows
        path = None
    brief = brief_of(body)
    return main(
        ["submit", "--name", "heavy", "--session", session, "--kind", kind]
        + (["--brief", str(brief)] if brief else [])
        + ["--", sys.executable, path or str(script), *args]
    )


def start_runner(root: Path, name: str, popen=subprocess.Popen) -> int:
    """`queue_autostart` (rule 8, Q-529-1): `lock.py runner` without a shell, detached from the
    builder's process group, its output appended to `runner.log` in the queue folder."""
    folder = heavy_queue.queue_folder(lock_folder(root, name))
    folder.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
        detach: dict = {"creationflags": flags}
    else:
        detach = {"start_new_session": True}
    with open(folder / "runner.log", "ab") as log:
        proc = popen(  # nosec B603 - fixed argument list from sys.executable, no shell
            [sys.executable, str(Path(__file__).resolve()), "runner", "--name", name],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            **detach,
        )
    return proc.pid


def drop_tree(job: dict) -> None:
    """Remove a job's worktree and its temporary folder, also when they were never made."""
    tree = job.get("worktree")
    if not isinstance(tree, str):
        return
    repository = Path(str(job.get("repository") or "."))
    if repository.is_dir():
        git(repository, "worktree", "remove", "--force", tree)
        git(repository, "worktree", "prune")
    shutil.rmtree(Path(tree).parent, ignore_errors=True)


def execute(root: Path, held: Path, name: str, job: dict, setup: dict, children: dict):
    """One job (rules 4 and 6): (outcome, exit code, the time its command began)."""
    repository = Path(str(job.get("repository")))
    if not repository.is_dir() or git(repository, "cat-file", "-e", f"{job['head']}^{{commit}}")[0]:
        return "failed (head not found)", None, None
    tree = Path(job["worktree"])
    if git(repository, "worktree", "add", "--detach", "-q", str(tree), job["head"])[0]:
        return "failed (the worktree cannot be made)", None, None
    clock = setup["clock"]
    token = uuid.uuid4().hex
    owner: dict = {
        "session": str(job.get("session") or ""),
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started": heavy_queue.stamp(clock()),
        "token": token,
    }
    owner["beat"] = owner["started"]
    slot = take(
        held, name, owner, setup["limit"], None, setup["slots"], PRIORITY, setup["cleanup"], root
    )
    if slot is None:
        return "failed (no slot was taken)", None, None
    env = {
        **os.environ,
        "AGK_LOCK_SESSION": owner["session"],
        "AGK_LOCK_TOKEN": token,
        "AGK_LOCK_NAME": name,
    }
    out = setup["folder"] / "results" / f"{job['ticket']}.out"
    out.parent.mkdir(parents=True, exist_ok=True)
    began = clock()
    try:
        with open(out, "wb") as sink:
            try:
                child = subprocess.Popen(  # nosec B603 - the job's own argument list, no shell
                    job["command"],
                    cwd=tree / str(job.get("folder") or "."),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=sink,
                    stderr=subprocess.STDOUT,
                )
            except OSError:
                return "failed (the command cannot be started)", 127, began
            children[job["ticket"]] = child
            record_child(slot, token, child.pid)
            with heartbeat(slot, token, clock):
                code = child.wait()
    finally:
        children.pop(job["ticket"], None)
        clear_if_same(slot, token)
    if code < 0:
        return f"failed (killed by signal {-code})", 128 - code, began
    return ("passed" if code == 0 else f"failed (exit {code})"), code, began


def work_job(root: Path, held: Path, name: str, job: dict, setup: dict, children: dict, wake):
    """Run one job in its own thread, then write its result under the mutex and wake the runner."""
    outcome, code, began = "failed (the job cannot be run)", None, None
    try:
        outcome, code, began = execute(root, held, name, job, setup, children)
    except OSError:
        pass
    finally:
        try:
            drop_tree(job)
            with mutex(held):
                outcome = settle(setup["folder"], job, outcome, setup["clock"](), code, began)
            print(f"runner {name}: {job['ticket']} {outcome}", flush=True)
        finally:
            wake.set()


def settle(folder: Path, job: dict, outcome: str, now: datetime, code, began) -> str:
    """Write the job's result; when that fails, write `failed (the result cannot be written)`
    where possible and release the job either way, so no job stays started under a live runner
    (rule 14). Under the mutex; returns the outcome written, or tried."""
    try:
        heavy_queue.finish(folder, job, outcome, now, code, began)
        return outcome
    except Exception:  # any failure here must not leave the job started
        outcome = "failed (the result cannot be written)"
    try:
        heavy_queue.finish(folder, job, outcome, now, code, began)
    except Exception:  # the job is still released below
        (folder / "jobs" / f"{job['ticket']}.json").unlink(missing_ok=True)
    return outcome


def dispatch(folder: Path, held: Path, name: str, setup: dict, me: dict, active: dict) -> list:
    """One pass under the mutex: fail what can no longer pass (rule 14), then mark started the
    next waiting jobs in the order in force while a slot is free (rules 4 and 5)."""
    clock, queue = setup["clock"], setup["queue"]
    host = me["host"]
    with mutex(held):
        for job, reason in heavy_queue.sweep(
            folder, clock(), pid_alive, host, setup["limit"], set(active)
        ):
            drop_tree(job)
            heavy_queue.finish(folder, job, f"failed ({reason})", clock())
            print(f"runner {name}: {job['ticket']} failed ({reason})", flush=True)
        order = heavy_queue.waiting_order(
            heavy_queue.jobs(folder), queue["queue_order"], queue["queue_max_wait"], clock()
        )
        started = []
        for job in order[: max(0, setup["slots"] - len(active))]:
            place = Path(tempfile.mkdtemp(prefix="agk-job-", dir=long_temp_dir()))
            job = {
                **job,
                "started": heavy_queue.stamp(clock()),
                "worktree": str(place / "tree"),
                "runner": {"pid": me["pid"], "host": host},
            }
            heavy_queue.write_whole(folder / "jobs" / f"{job['ticket']}.json", json.dumps(job))
            started.append(job)
        me["read"] = heavy_queue.stamp(clock())
        heavy_queue.write_whole(folder / "runner.json", json.dumps(me))
        return started


def runner(root: Path, name: str, clock=None, sleep=time.sleep) -> int:
    """`lock.py runner` (SPEC-0040 rules 4, 8 and 14); the clock and sleep are for its tests."""
    clock = clock or (lambda: datetime.now(UTC))
    held = lock_folder(root, name)
    folder = heavy_queue.queue_folder(held)
    setup = {
        "clock": clock,
        "folder": folder,
        "limit": stale_minutes(root),
        "slots": slots_setting(root),
        "cleanup": cleanup_setting(root),
        "queue": queue_setting(root),
    }
    host = socket.gethostname()
    me = {"pid": os.getpid(), "host": host, "started": heavy_queue.stamp(clock())}
    with mutex(held):
        mine, line = heavy_queue.claim(folder, me, pid_alive, host, setup["limit"], clock())
    if line:
        print(line, flush=True)
    if not mine:
        return 0
    heavy_queue.prune(folder, clock())
    active: dict[str, threading.Thread] = {}
    children: dict[str, subprocess.Popen] = {}
    wake = threading.Event()
    idle = setup["queue"]["queue_idle_minutes"]
    since = None
    code = 0
    try:
        while True:
            for ticket in [t for t, th in active.items() if not th.is_alive()]:
                active.pop(ticket).join()
            for job in dispatch(folder, held, name, setup, me, active):
                thread = threading.Thread(
                    target=work_job,
                    args=(root, held, name, job, setup, children, wake),
                    daemon=True,
                )
                active[job["ticket"]] = thread
                thread.start()
            if active:
                wake.wait(POLL)
                wake.clear()
                since = None
                continue
            now = clock()
            if heavy_queue.jobs(folder):
                since = None
            elif since is None:
                since = now
            elif (now - since).total_seconds() >= idle * 60:
                if idle_stop(folder, held, me):
                    print(f"runner idle for {idle} min; stopped", flush=True)
                    return 0
                since = None
            sleep(POLL)
    except KeyboardInterrupt:
        code = 130
    except Stopped as exc:
        code = exc.code
    finally:
        for child in list(children.values()):
            stop(child)
        for thread in active.values():
            thread.join(timeout=STOP_WAIT)  # a job still waiting for a slot fails at the next sweep
        with mutex(held):
            if (heavy_queue.read_json(folder / "runner.json") or {}).get("pid") == me["pid"]:
                (folder / "runner.json").unlink(missing_ok=True)
    return code


def idle_stop(folder: Path, held: Path, me: dict) -> bool:
    """Rule 8: stop only when, under the mutex, no job is queued; `runner.json` is removed in the
    same mutex section, so a `submit` either sees this runner gone or is seen by it (`enqueue`)."""
    with mutex(held):
        if heavy_queue.jobs(folder):
            return False
        if (heavy_queue.read_json(folder / "runner.json") or {}).get("pid") == me["pid"]:
            (folder / "runner.json").unlink(missing_ok=True)
        return True


def on_signal(signum, _frame) -> None:
    raise Stopped(128 + signum)


def run_held(command: list[str], held: Path, token: str, session: str = "", name: str = "") -> int:
    # The slot's token and name travel down to every process the command starts, so prepush
    # inside a wrapper finds its caller's slot (brief #505, ADR-0254). The token is never printed.
    env = {
        **os.environ,
        "AGK_LOCK_SESSION": session,
        "AGK_LOCK_TOKEN": token,
        "AGK_LOCK_NAME": name,
    }
    try:
        child = subprocess.Popen(command, env=env)  # nosec B603 - the person's own argument list
    except OSError:
        print("lock: the command cannot be started (it is not found or not runnable)", flush=True)
        return 127
    try:
        record_child(held, token, child.pid)
        with heartbeat(held, token):
            code = child.wait()
        return 128 - code if code < 0 else code  # killed by signal n: 128 + n, as a shell says
    except KeyboardInterrupt:
        stop(child)
        return 130
    except Stopped as exc:
        stop(child)
        return exc.code


def stop(child: subprocess.Popen) -> None:
    if child.poll() is None:
        child.terminate()
    try:
        child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()


def main(argv: list[str] | None = None) -> int:
    try:
        options = parse_args(list(sys.argv[1:] if argv is None else argv))
        root = repo_root()
        held = lock_folder(root, options["name"])
        limit = stale_minutes(root)
        slots = slots_setting(root)
        cleanup = cleanup_setting(root) if options["action"] == "run" else ""
        queue = queue_setting(root)
        action = options["action"]
        if not queue["queue"] and (action in ("submit", "runner") or options["ticket"]):
            raise Usage(f"lock.py {action}: {QUEUE_OFF}")
        if action == "runner":
            for signum in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGHUP", None)):
                if signum is not None:
                    signal.signal(signum, on_signal)
            return runner(root, options["name"])
        if action == "submit":
            return submit_job(root, held, options, queue)
    except Usage as exc:
        print(exc, file=sys.stderr)
        return 2
    except OSError:
        print(f"lock {options['name']}: the queue cannot be written (setting: lock_dir)")
        return 3
    name = options["name"]
    if options["head"]:
        lines, code = ticket_for_head(
            heavy_queue.queue_folder(held), queue, slots, options["ticket"], options["head"]
        )
        print("\n".join(lines))
        return code
    if options["ticket"]:
        lines, code = heavy_queue.status_lines(
            heavy_queue.queue_folder(held), queue, slots, datetime.now(UTC), options["ticket"]
        )
        print("\n".join(lines))
        return code
    if options["action"] == "status":
        for k, folder in enumerate(slot_folders(held, slots), start=1):
            label = f"lock {name}" if slots == 1 else f"lock {name} slot {k}"
            if not folder.exists():
                print(f"{label}: free")
                continue
            current = read_owner(folder)
            reason = stale_reason(current, folder, limit)
            print(f"{label}: {describe(current)}" + (f"; stale ({reason})" if reason else ""))
        if queue["queue"]:
            lines, _ = heavy_queue.status_lines(
                heavy_queue.queue_folder(held), queue, slots, datetime.now(UTC)
            )
            print("\n".join(lines))
        return 0
    token = uuid.uuid4().hex
    owner = {
        "session": options["session"] or os.environ.get("AGK_SESSION") or "",
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token": token,
    }
    owner["beat"] = owner["started"]
    for signum in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGHUP", None)):
        if signum is not None:
            signal.signal(signum, on_signal)
    taken: Path | None = None
    try:
        taken = take(
            held,
            name,
            owner,
            limit,
            options["timeout"],
            slots=slots,
            priority=options["priority"],
            cleanup=cleanup,
            root=root,
        )
        if taken is None:
            return 3
        return run_held(options["command"], taken, token, owner["session"], name)
    except KeyboardInterrupt:
        return 130
    except Stopped as exc:
        return exc.code
    except OSError:
        print(f"lock {name}: the lock folder cannot be written (setting: lock_dir)", flush=True)
        return 3
    finally:
        for folder in slot_folders(held, slots):  # this run's own slot, found by its token
            clear_if_same(folder, token)


if __name__ == "__main__":
    sys.exit(main())
