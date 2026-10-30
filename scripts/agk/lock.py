"""The heavy-step lock: one heavy run at a time on a machine (brief #337, ADR-0191).

    python3 scripts/agk/lock.py run --name NAME [--session ID] [--timeout S] -- COMMAND [ARG...]
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

from common import config_source

USAGE = (
    "usage: lock.py run --name NAME [--session ID] [--timeout S] -- COMMAND [ARG...]\n"
    "       lock.py status --name NAME"
)
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
STALE_MINUTES = 120
POLL = 0.5  # seconds between two tries
ANNOUNCE = 60  # seconds between two waiting lines
STILL_ACTIVE = 259  # GetExitCodeProcess: the process has not ended
QUERY = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
MUTEX_STALE = 10.0  # seconds: a mutex this old was left by a process that died holding it


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
    options: dict = {"action": args[0], "name": None, "session": None, "timeout": None}
    rest = args[1:]
    command: list[str] | None = None
    if "--" in rest:
        cut = rest.index("--")
        rest, command = rest[:cut], rest[cut + 1 :]
    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg in ("--name", "--session", "--timeout") and i + 1 < len(rest):
            options[arg[2:]] = rest[i + 1]
            i += 2
        else:
            raise Usage(USAGE)
    if not options["name"] or not NAME.fullmatch(options["name"]):
        raise Usage(USAGE)
    if options["action"] == "status":
        if command is not None or options["session"] or options["timeout"]:
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
        return "its process no longer runs"
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
    mutex older than MUTEX_STALE seconds was left by a process that died inside it."""
    held.parent.mkdir(parents=True, exist_ok=True)
    gate = held.parent / f".{held.name}.mutex"
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


def take(held: Path, name: str, owner: dict, limit: int, timeout: float | None) -> bool:
    began = time.monotonic()
    announced: float | None = None
    while True:
        if try_take(held, owner):
            if announced is not None:
                print(f"lock {name}: taken", flush=True)
            return True
        current = read_owner(held)
        reason = stale_reason(current, held, limit)
        if reason is not None:
            who = (current or {}).get("session") or "an unknown session"
            if clear_if_same(held, (current or {}).get("token")):
                print(f"lock {name}: cleared a stale lock of {who} ({reason})", flush=True)
            continue
        now = time.monotonic()
        if timeout is not None and now - began >= timeout:
            print(f"lock {name}: not taken after {timeout:g} s; {describe(current)}", flush=True)
            return False
        if announced is None or now - announced >= ANNOUNCE:
            print(f"lock {name}: waiting; {describe(current)}", flush=True)
            announced = now
        time.sleep(POLL)


def on_signal(signum, _frame) -> None:
    raise Stopped(128 + signum)


def run_held(command: list[str], held: Path, token: str) -> int:
    try:
        child = subprocess.Popen(command)  # nosec B603 - the person's own argument list, no shell
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
    except Usage as exc:
        print(exc, file=sys.stderr)
        return 2
    name = options["name"]
    if options["action"] == "status":
        if not held.exists():
            print(f"lock {name}: free")
            return 0
        current = read_owner(held)
        reason = stale_reason(current, held, limit)
        line = f"lock {name}: {describe(current)}"
        print(line + (f"; stale ({reason})" if reason else ""))
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
    try:
        if not take(held, name, owner, limit, options["timeout"]):
            return 3
        return run_held(options["command"], held, token)
    except KeyboardInterrupt:
        return 130
    except Stopped as exc:
        return exc.code
    except OSError:
        print(f"lock {name}: the lock folder cannot be written (setting: lock_dir)", flush=True)
        return 3
    finally:
        clear_if_same(held, token)


if __name__ == "__main__":
    sys.exit(main())
