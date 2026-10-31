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
up after S seconds (exit 3). A lock whose process no longer runs on this machine, or that is older
than `lock_stale_minutes` (agk.toml, 120 by default), is cleared with a line saying so; it counts
as held while either `lock.py` or its command still runs. `status` prints the holder, or `free`,
and changes nothing.

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

Standard library only; no network. POSIX and Windows: a process is looked up with signal 0 on
POSIX and with OpenProcess on Windows, where `os.kill` would end it.
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
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, config_source, lock_cleanup, lock_slots

USAGE = (
    "usage: lock.py run --name NAME [--session ID] [--priority P] [--timeout S]"
    " -- COMMAND [ARG...]\n"
    "       lock.py status --name NAME\n"
    "--priority P is 0 to 3 (2 by default); the lowest goes first"
)
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
STALE_MINUTES = 120
POLL = 0.5  # seconds between two tries
ANNOUNCE = 60  # seconds between two waiting lines
STILL_ACTIVE = 259  # GetExitCodeProcess: the process has not ended
QUERY = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
MUTEX_STALE = 10.0  # seconds: a mutex this old was left by a process that died holding it
PRIORITY = 2  # the default priority, as for briefs; 0 goes first
PRIORITIES = range(0, 4)
DEAD = "its process no longer runs"
CLEANUP_TIMEOUT = 300  # seconds a cleanup may take before it is ended and reported (Q-426-3)


class Usage(Exception):
    """A usage error or a refused setting (exit 2)."""


class Stopped(Exception):
    """A termination signal arrived while the lock is held."""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


def parse_args(args: list[str]) -> dict:
    if not args or args[0] not in ("run", "status"):
        raise Usage(USAGE)
    options: dict = {
        "action": args[0],
        "name": None,
        "session": None,
        "timeout": None,
        "priority": None,
    }
    rest = args[1:]
    command: list[str] | None = None
    if "--" in rest:
        cut = rest.index("--")
        rest, command = rest[:cut], rest[cut + 1 :]
    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg in ("--name", "--session", "--timeout", "--priority") and i + 1 < len(rest):
            options[arg[2:]] = rest[i + 1]
            i += 2
        else:
            raise Usage(USAGE)
    if not options["name"] or not NAME.fullmatch(options["name"]):
        raise Usage(USAGE)
    if options["action"] == "status":
        if command is not None or options["session"] or options["timeout"] or options["priority"]:
            raise Usage(USAGE)
        return options
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


def repo_root() -> Path:
    """The work tree's top folder, or the current folder outside one."""
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return Path.cwd()
    return Path(proc.stdout.strip()) if proc.returncode == 0 else Path.cwd()


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


def age_minutes(owner: dict) -> float | None:
    try:
        started = datetime.strptime(str(owner["started"]), "%Y-%m-%dT%H:%M:%SZ")
    except (KeyError, ValueError):
        return None
    return (datetime.now(UTC) - started.replace(tzinfo=UTC)).total_seconds() / 60


def stale_reason(owner: dict | None, held: Path, limit: int) -> str | None:
    """Why a lock may be cleared, or None while its owner may still hold it."""
    if owner is None:
        # Taken in one rename with its owner file, so a folder without one is a leftover; it is
        # cleared only once it is older than the limit, by the folder's own time.
        try:
            minutes = (time.time() - held.stat().st_mtime) / 60
        except OSError:
            return None
        return f"it has no owner file and is older than {limit} min" if minutes > limit else None
    minutes = age_minutes(owner)
    if owner.get("host") == socket.gethostname() and not holder_alive(owner):
        return DEAD
    if minutes is None or minutes > limit:
        return f"older than {limit} min, setting: lock_stale_minutes"
    return None


def holder_alive(owner: dict) -> bool:
    """The lock is held while `lock.py` or the command it started still runs: a holder killed
    with SIGKILL leaves its command running, and that command still holds the machine."""
    pids = [owner.get("pid"), owner.get("child")]
    return any(pid_alive(int(p)) for p in pids if isinstance(p, int) and p > 0)


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


def describe(owner: dict | None) -> str:
    if owner is None:
        return "held by an unknown owner"
    minutes = age_minutes(owner)
    age = f"for {int(minutes)} min" if minutes is not None else "since an unknown time"
    child = f", command pid {owner['child']}" if owner.get("child") else ""
    return (
        f"held by {owner.get('session') or 'an unknown session'} "
        f"(pid {owner.get('pid')}{child}, host {owner.get('host')}) {age}"
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


def record_child(held: Path, token: str, child: int) -> None:
    """Add the command's process id to this run's owner file, under the mutex."""
    with mutex(held):
        owner = read_owner(held)
        if (owner or {}).get("token") != token:
            return
        owner["child"] = child
        staged = held / "owner.json.new"
        staged.write_text(json.dumps(owner), encoding="utf-8")
        os.replace(staged, held / "owner.json")


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
    folders: list[Path], name: str, limit: int, cleanup: str, root: Path | None
) -> bool:
    """Clear each stale slot, each once (a lock taken again since it was judged is kept), and run
    the cleanup after each dead run cleared here. Whether any slot was cleared."""
    cleared = False
    for folder in folders:
        if not folder.exists():
            continue
        current = read_owner(folder)
        reason = stale_reason(current, folder, limit)
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


def on_signal(signum, _frame) -> None:
    raise Stopped(128 + signum)


def run_held(command: list[str], held: Path, token: str, session: str = "") -> int:
    env = {**os.environ, "AGK_LOCK_SESSION": session}
    try:
        child = subprocess.Popen(command, env=env)  # nosec B603 - the person's own argument list
    except OSError:
        print("lock: the command cannot be started (it is not found or not runnable)", flush=True)
        return 127
    try:
        record_child(held, token, child.pid)
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
    except Usage as exc:
        print(exc, file=sys.stderr)
        return 2
    name = options["name"]
    if options["action"] == "status":
        for k, folder in enumerate(slot_folders(held, slots), start=1):
            label = f"lock {name}" if slots == 1 else f"lock {name} slot {k}"
            if not folder.exists():
                print(f"{label}: free")
                continue
            current = read_owner(folder)
            reason = stale_reason(current, folder, limit)
            print(f"{label}: {describe(current)}" + (f"; stale ({reason})" if reason else ""))
        return 0
    token = uuid.uuid4().hex
    owner = {
        "session": options["session"] or os.environ.get("AGK_SESSION") or "",
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token": token,
    }
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
        return run_held(options["command"], taken, token, owner["session"])
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
