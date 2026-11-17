# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""`autopilot.py status`: what the jobs of this machine do, and the week's health figures.

    python3 autopilot.py status [--week] [--root DIR]
    python3 autopilot.py on|off|budget on|budget off [--today]|retry N [--root DIR]
    python3 autopilot.py jobs [--claim] | next [--brief N] [--root DIR]

Brief #1391, SPEC-0064 build (f), rule 13 (ADR-0589); `agk next` is `next`. `pick` is the
supervisor's choice of jobs over GitHub-shaped records of any forge, so every mode starts the same
jobs: a `review` job while a pull request's newest `Report:` is newer than every `Verdict:`,
`Correction:` or answer, a `fix` job where build (c)'s `conductor.job_gate` sees its event (a
clearing verdict is none), and a `build` job per brief the plan starts (personal mode: per open
brief whose `Depends-on` issues are closed). An item with a `Started:` or `taken:` newer than its
event and `conductor.START_HOURS` is held by that job's machine until the take lapses. `jobs
[--claim]` prints the jobs from GitHub, gated by `job_allowed`; with `--claim`,
`conductor.claim_job` (the supervisor's one write) posts one `Started:` claim per build or fix job
first, so this script still holds no write of its own. CI mode's launcher task is the supervisor
and fires one cloud session per `job:` line. `next [--brief N]` runs one job in the foreground
through the adapter, waits for its exit file and ends; it posts nothing, and in personal mode
reads the sidecar's files forge (`forge.FilesForge`), never `gh`.

Brief #1390, SPEC-0064 build (d), rules 7, 8 and 11 (ADR-0587); `agk autopilot` is its short form.
`on` installs the one scheduler entry (a crontab line tagged `# agk-autopilot`, or the Windows task
`agk-autopilot`), every `[autopilot] interval_minutes` (5), a `git fetch` then `conductor.py
watchdog --pass`; `off` removes it and keeps every other line. `on` runs the machine checks (the
entry runs while nobody is signed in, sleep off, free memory for one builder, `gh` signed in, the
adapter set and runnable), each `ok:` or `warn:` naming the setting, only reads and never changes
a power setting `(verify: per OS)`; both print, never write, the protected `agk.toml` change of
`mode`. `mode_allows` and `job_allowed` are what the supervisor asks before a start: `off` starts
nothing, `assist` a build or fix job only on the owner's yes, `on` all, no table today's settings;
a reached `daily_budget` (tokens of the UTC day, as `metrics.py --cost --day`; `unknown` when it
cannot be read, which stops new build and fix jobs too) stops new build and fix jobs, never review,
steward or conductor jobs. `budget off [--today]` relaxes it and `budget on` ends that, and `retry
N` lifts a hold of rule 9, each kept in `<git dir>/agk/autopilot.json`, never a tracked file.
`status` begins with the mode and the budget line.

Brief #1386, SPEC-0064 build (a), rules 3, 5 and 10 (ADR-0584); `agk status` is its short form.
`status` reads the job records (`<parent of the checkout>/agk-<session>/.agk-session-pid`, with the
`kind=`, `item=` and `head=` that `launch.py` hands the adapters) and lists each running job: its
kind, item, head, since when and its last event (the newest of the record and the log file
`.agk-session.log`). A `claude` process outside every recorded job's process tree is reported as
`unrecorded: process <pid> (not adopted)`, except a person's own steward (`--agent steward`); it
is never adopted as a job. Then it reads the plan and the sweep, the GitHub reads of one
`watchdog --pass` (at most those calls), and prints the queue (the plan's `Start` line), what waits
on the owner (the sweep's `NEEDS-YOU:` lines), the held jobs (those of them that say `held (`) and
one `quiet:` line with the reason no job would start. It posts nothing and writes nothing. After the
jobs, `refusals today: <n> (<reason> <k>, ...)` counts the hook refusals of the UTC day from the
refusal log (brief #1410, ADR-0593), or says `none`.

`append_health` is the pass's one line per pass (build (b) calls it) in `agk-autopilot.jsonl` of
the user's temp folder, never the checkout: jobs started by kind, ended, failed, held, pull
requests merged and the seconds from each event to its job's start, with the time; numbers, kinds
and times only, refused otherwise. `status --week` prints the last seven days of that file and the
tokens per merged pull request from `metrics.py --cost`'s local records; a figure it cannot read
is `unknown`, never 0. No network call of its own (verify: the process table is `ps -A -o
pid=,ppid=,args=`; on Windows `Get-CimInstance Win32_Process` with its command lines, brief #1409).
"""

from __future__ import annotations

import configparser
import json
import os
import re
import shlex
import shutil
import subprocess  # nosec B404 - fixed argument lists, no shell
import sys
import tempfile
import time
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import conductor
import guard_logs
import launch
import metrics
import session
import session_plan
from common import CheckError, personal_table, utf8_output

import config

HEALTH_FILE = "agk-autopilot.jsonl"
COUNTS = ("ended", "failed", "held", "merged")
USAGE = (
    "usage: autopilot.py status [--week] | on | off | budget on | budget off [--today] | retry N"
    " | jobs [--claim] | next [--brief N] [--root DIR]"
)


def stamp(when: datetime) -> str:
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def claude_processes(run=subprocess.run, platform: str | None = None):
    """(pid, parent pid, command line) of every process, or None when it cannot be read
    (`launch.command_lines`: `ps` on POSIX, `Get-CimInstance Win32_Process` on Windows)."""
    return launch.command_lines(run, platform)


is_claude = launch.is_claude


def unrecorded(table: list[tuple[int, int, str]], roots: set[int]) -> list[int]:
    """The `claude` processes outside every recorded tree, but a person's own steward."""
    steward = {pid for pid, _, args in table if "--agent steward" in args}
    return [pid for pid in launch.outside_trees(table, roots) if pid not in steward]


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


def status(root: Path, now: datetime | None = None) -> int:
    jobs, roots = job_lines(root)
    print(f"jobs: {len(jobs) or 'none'}")
    for line in jobs:
        print(line)
    print(guard_logs.today_line(root, now or datetime.now(UTC)))  # brief #1410, ADR-0593
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


# --- the setting, the budget and the command (rules 7, 8 and 11; brief #1390, ADR-0587) -------

PLATFORM = sys.platform
ENTRY_TAG = "# agk-autopilot"  # marks the one crontab line `on` writes and `off` removes
TASK_NAME = "agk-autopilot"  # the one Windows Task Scheduler entry
STATE_FILE = "autopilot.json"  # beside the lease mark, in the git directory: never tracked
RUN_LINE = "python3 scripts/agk/conductor.py watchdog --pass"
NO_CRONTAB = re.compile(r"^no crontab for ", re.MULTILINE)  # the one failed read that is empty
WINDOWS_RUN_LINE = "python scripts\\agk\\conductor.py watchdog --pass"
PROC_VERSION = Path("/proc/version")  # names Microsoft inside WSL, as `doctor.inside_wsl` reads it
WSL_CONF = Path("/etc/wsl.conf")  # `[interop] enabled = false` turns Windows interop off
WSL_TASK = "agk-autopilot (WSL)"  # the one Windows task of a WSL checkout (brief #1448, ADR-0606)
OWNER_JOBS = ("review", "steward", "conductor")  # rule 8: never stopped by the budget


def run_command(argv: list[str], given: str | None = None) -> tuple[int, str]:
    """Run one fixed command of this machine: (exit code, its output, or its error output when
    it fails); 127 when it cannot run."""
    try:
        done = subprocess.run(  # nosec B603 - fixed argument lists, no shell
            argv, input=given, capture_output=True, text=True, encoding="utf-8", check=False
        )  # fmt: skip
    except OSError:
        return 127, ""
    return done.returncode, done.stdout if done.returncode == 0 else done.stderr


def mode_allows(mode: str | None, kind: str, owner_yes: bool = False) -> bool:
    """Rule 7: `off` starts nothing, `assist` a builder only on the owner's yes, `on` all; with no
    `[autopilot]` table (None) today's settings decide, as before this build."""
    if mode == "off":
        return False
    if mode == "assist":
        return kind in OWNER_JOBS or owner_yes
    return True


def state_path(root: Path) -> Path | None:
    mark = conductor.lease_mark(root)
    return None if mark is None else mark.parent / STATE_FILE


def load_state(root: Path) -> dict:
    found = state_path(root)
    try:
        data = json.loads(found.read_text(encoding="utf-8")) if found else {}
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def keep_state(root: Path, data: dict) -> None:
    found = state_path(root)
    if found is None:
        raise CheckError("the git directory cannot be read (setting: autopilot state)")
    found.parent.mkdir(parents=True, exist_ok=True)
    found.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")


def day_spend(root: Path, day) -> int | None:
    """The day's tokens as `metrics.py --cost --day` counts them, or None when unknown."""
    try:
        home = metrics.records_home(None)
        replies, _, _, lost = metrics.read_replies(
            home, metrics.clone_folders(root), metrics.start_of(day)
        )
    except (CheckError, OSError):
        return None
    figures = metrics.day_figures(day, replies, {})
    return None if lost or not figures["rows"] else metrics.total_of(figures["total"]["tokens"])


def relaxed(root: Path, now: datetime) -> str | None:
    """`today` or `until set again` while `budget off` holds, else None."""
    off = load_state(root).get("budget_off")
    if off is True:
        return "until set again"
    return f"for {now.date()}" if off == str(now.date()) else None


def budget_line(root: Path, now: datetime) -> str:
    limit = config.autopilot_settings(root)["daily_budget"]
    spend = day_spend(root, now.date())
    shown = "unknown" if spend is None else f"{spend} tokens"
    head = "budget: off" if limit is None else f"budget: {limit} tokens"
    if limit is not None and (why := relaxed(root, now)):
        head += f" (relaxed {why})"
    return f"{head}; spend {now.date()}: {shown}"


def job_allowed(root: Path, kind: str, now: datetime, owner_yes: bool = False) -> tuple[bool, str]:
    """Whether the setting and the budget let a job of KIND start now, and why not."""
    settings = config.autopilot_settings(root)
    if not mode_allows(settings["mode"], kind, owner_yes):
        return False, f"mode {settings['mode']} (setting: autopilot.mode)"
    limit = settings["daily_budget"]
    if kind in OWNER_JOBS or limit is None or relaxed(root, now):
        return True, ""
    spend = day_spend(root, now.date())
    if spend is None:
        return False, "budget set and the spend is unknown (setting: autopilot.daily_budget)"
    if spend >= limit:
        return False, "budget reached (setting: autopilot.daily_budget)"
    return True, ""


def budget_note(root: Path, now: datetime) -> bool:
    """True the first time a UTC day asks, so the owner is told once a day."""
    data = load_state(root)
    if data.get("told") == str(now.date()):
        return False
    keep_state(root, data | {"told": str(now.date())})
    return True


def retries(root: Path) -> dict:
    return load_state(root).get("retry") or {}


def mode_change(mode: str | None, wanted: str) -> list[str]:
    if mode == wanted:
        return []
    return [
        "agk.toml: this change is yours, as a pull request with its ADR (agk.toml is a protected "
        "path); the command edits no tracked file:",
        f'  [autopilot]\n  mode = "{wanted}"',
    ]


def entry_line(root: Path, interval: int) -> str:
    folder = shlex.quote(str(Path(root).resolve()))
    return f"*/{interval} * * * * cd {folder} && git fetch -q origin && {RUN_LINE} {ENTRY_TAG}"


def run_shown(argv: list[str]) -> int:
    """Run one fixed command on the person's own terminal: what Windows asks there (the task's
    stored sign-in) goes to Windows, never through this script; 127 when it cannot run."""
    try:
        return subprocess.run(argv, check=False).returncode  # nosec B603 - fixed list, no shell
    except OSError:
        return 127


def inside_wsl() -> bool:
    if PLATFORM != "linux":
        return False
    try:
        return "microsoft" in PROC_VERSION.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return False


def interop_on() -> bool:
    found = configparser.ConfigParser(strict=False, interpolation=None)
    try:
        found.read_string(WSL_CONF.read_text(encoding="utf-8", errors="replace"))
    except (OSError, configparser.Error):
        return True  # no readable file: WSL's default, interop on
    value = found.get("interop", "enabled", fallback="true").strip().lower()
    return value not in ("false", "0", "no", "off")


def set_wsl_task(root: Path, interval: int | None) -> int:
    """Brief #1448 (ADR-0606): inside WSL the one entry is the Windows task WSL_TASK, registered
    through interop to run whether or not the person is signed in; Windows asks for the stored
    sign-in (`/RP *`) and a declined one leaves a signed-in-only task `(verify: on Windows)`."""
    if not interop_on():
        print(
            "autopilot: Windows interop is off in this distro; nothing written "
            "(setting: [interop] enabled in /etc/wsl.conf)"
        )
        return 1
    if interval is None:
        return run_command(["schtasks.exe", "/Delete", "/TN", WSL_TASK, "/F"])[0]
    distro = os.environ.get("WSL_DISTRO_NAME", "").strip()
    code, user = run_command(["whoami.exe"])
    if not distro or code != 0 or not user.strip():
        print("autopilot: the distro or the Windows account cannot be read; nothing written "
              "(setting: WSL_DISTRO_NAME)")  # fmt: skip
        return 1
    inner = f'"git fetch -q origin && {RUN_LINE}"'
    run = f"wsl.exe -d {distro} --cd {Path(root).resolve()} -- bash -lc {inner}"
    argv = ["schtasks.exe", "/Create", "/SC", "MINUTE", "/MO", str(interval), "/TN", WSL_TASK]
    argv += ["/TR", run, "/F"]
    signed_out = [*argv, "/RU", user.strip(), "/RP", "*"]
    print(f"autopilot: {shlex.join(signed_out)}")
    if run_shown(signed_out) == 0:
        print("ok: the task runs whether or not you are signed in")
        return 0
    code, _ = run_command(argv)
    if code == 0:
        print("warn: runs only while you are signed in (setting: the task's sign-in option)")
    return code


def set_entry(root: Path, interval: int | None) -> int:
    """Install (INTERVAL) or remove (None) the one scheduler entry of this checkout."""
    if inside_wsl():
        return set_wsl_task(root, interval)
    if PLATFORM == "win32":
        if interval is None:
            code, _ = run_command(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
            return code
        folder = str(Path(root).resolve())
        command = f'cmd /c cd /d "{folder}" && git fetch -q origin && {WINDOWS_RUN_LINE}'
        argv = ["schtasks", "/Create", "/SC", "MINUTE", "/MO", str(interval), "/TN", TASK_NAME]
        code, _ = run_command([*argv, "/TR", command, "/F"])
        return code
    code, text = run_command(["crontab", "-l"])
    if code != 0 and not NO_CRONTAB.search(text):  # a failed read never empties the crontab
        print("autopilot: the crontab cannot be read; nothing written (setting: crontab)")
        return 1
    kept = [x for x in (text if code == 0 else "").splitlines() if not x.endswith(ENTRY_TAG)]
    if interval is not None:
        kept.append(entry_line(root, interval))
    code, _ = run_command(["crontab", "-"], "".join(f"{x}\n" for x in kept))
    return code


def machine_checks(root: Path) -> list[str]:
    """Rule 11: `ok:` or `warn:` lines naming the setting; reads only, changes no power setting."""
    out = []
    if PLATFORM == "win32":
        out.append(
            "warn: the task runs only while you are signed in unless it is set to run whether "
            "you are signed in or not (setting: Task Scheduler run whether signed in) (verify)"
        )
        out.append("warn: sleep cannot be read here (setting: power sleep) (verify: per OS)")
    else:
        if not inside_wsl():  # inside WSL `set_wsl_task` printed the task's sign-in line
            out.append("ok: the cron entry runs while nobody is signed in")
        code, text = 127, ""
        if PLATFORM == "linux":  # a read: `is-enabled` changes nothing
            code, text = run_command(["systemctl", "is-enabled", "sleep.target"])
        if code in (0, 1) and text.strip() == "masked":
            out.append("ok: sleep is off")
        else:
            out.append(
                "warn: sleep is on or unknown; turn it off or set a wake timer while autopilot "
                "is on (setting: power sleep) (verify: per OS)"
            )
    line, allowed = conductor.memory_line(root)
    if allowed:
        out.append(f"ok: {line.removeprefix('watchdog: ')}")
    else:
        out.append("warn: free memory is below one builder (setting: capacity.builder_memory_gb)")
    code, _ = run_command(["gh", "auth", "status"])
    signed = "ok: gh is signed in"
    out.append(signed if code == 0 else "warn: gh is not signed in (setting: gh auth login)")
    adapter = launch.launch_settings(root)[1]
    first = shlex.split(adapter)[0] if adapter and adapter.strip() else None
    if first and (shutil.which(first) or Path(first).is_file()):
        out.append("ok: the adapter is set and runs")
    else:
        out.append("warn: the adapter is unset or does not run (setting: flow.launch_adapter)")
    return out


def autopilot_on(root: Path, turn_on: bool) -> int:
    settings = config.autopilot_settings(root)
    code = set_entry(root, settings["interval_minutes"] if turn_on else None)
    what = "installed" if turn_on else "removed"
    print(f"autopilot: scheduler entry {what}" if code == 0 else f"autopilot: entry not {what}")
    if turn_on:
        print("\n".join(machine_checks(root)))
    print("\n".join(mode_change(settings["mode"], "on" if turn_on else "off")))
    return 0 if code == 0 else 1


def budget_command(root: Path, words: list[str], now: datetime) -> int:
    data = load_state(root)
    if words == ["on"]:
        data.pop("budget_off", None)
    elif words in (["off"], ["off", "--today"]):
        data["budget_off"] = str(now.date()) if words[1:] else True
    else:
        print(USAGE, file=sys.stderr)
        return 2
    keep_state(root, data)
    print(budget_line(root, now))
    return 0


def mode_lines(root: Path, now: datetime) -> list[str]:
    mode = config.autopilot_settings(root)["mode"]
    if mode is None:
        head = "autopilot: no [autopilot] table; today's settings decide (setting: autopilot.mode)"
    elif mode == "off":
        head = f"autopilot: mode off; nothing starts by itself; run: {RUN_LINE}"
    else:
        head = f"autopilot: mode {mode}"
    return [head, budget_line(root, now)]


# --- every mode runs the same jobs (brief #1391, SPEC-0064 build (f), rule 13, ADR-0589) ----------

CLEARED = "Verdict: cleared"  # waits for its merge: no builder job (Q-1391-1)
HELD_BY = ("Started: ", "taken: ")  # a claim on an item: its job runs on some machine (rule 13)
DEPENDS = re.compile(r"^Depends-on: #(\d+)\s*$", re.M)
NEXT_POLL = 5  # seconds between two reads of the foreground job's exit file
NEXT_POLLS = 6 * 3600 // NEXT_POLL  # six hours, LIFETIME's outer bound
SLEEP = time.sleep
PERSONAL_NOTE = (
    "Personal mode (SPEC-0041): post nothing to GitHub and push nothing; the files forge of this "
    "sidecar keeps every result (session rule 37).\n"
)


def holder(said: list, since: datetime | None, now: datetime) -> str | None:
    """The session of the newest `Started:` or `taken:` newer than SINCE and than
    `conductor.START_HOURS` ago: the job another machine may be running (Q-S0064-4)."""
    edge = now - timedelta(hours=conductor.START_HOURS)
    edge = max(edge, since) if since else edge
    found = [c for c in session.in_order(said) if session.first_line(c).startswith(HELD_BY)
             and session.moment(c.get("created_at")) > edge]  # fmt: skip
    return (session.first_line(found[-1]).split() + ["?"])[1] if found else None


def pick(pulls: list, issues: list, comments: dict, now: datetime, ready: dict | None = None):
    """(the jobs, the held ones) by the supervisor's rules, from GitHub-shaped records of any
    forge: one `review` job while a non-draft pull request's newest `Report:` is newer than every
    `Verdict:`, `Correction:` or answer; a `fix` job where `conductor.job_gate` (build (c)) sees
    its event, a clearing verdict being none; a `build` job per open brief that no open pull
    request names, of READY (the plan's starts) or, with none, whose `Depends-on` issues are
    closed. A job whose item carries a newer claim is held, never started twice (rule 13)."""
    jobs: list[dict] = []
    held: list[dict] = []
    named, review = set(), None

    def add(kind: str, item: int, name: str, since: datetime | None) -> None:
        job = {"kind": kind, "item": item, "session": name}
        if by := holder(comments.get(item) or [], since, now):
            held.append(job | {"by": by})
        else:
            jobs.append(job)

    for pull in sorted(pulls, key=lambda p: p["number"]):
        n, said, brief = (
            pull["number"],
            comments.get(pull["number"]) or [],
            session.brief_number(pull),
        )
        named.add(brief)
        report = conductor.newest(said, ("Report:",))
        verdict = conductor.newest(said, conductor.OWED)
        if not pull.get("draft") and report and (verdict is None or report > verdict):
            review = review or n
        own = conductor.newest(said, conductor.ALIVE) or session.moment(pull.get("created_at"))
        owing = [c for c in said if not session.first_line(c).startswith(CLEARED)]
        facts = {"own": own, "owed": conductor.newest(owing, conductor.OWED),
                 "labels": session.labels_of(pull)}  # fmt: skip
        if brief is not None and conductor.job_gate(None, facts, now) is None:
            add("fix", n, f"cb{brief}", conductor.newest(owing, conductor.OWED))
    if review is not None:
        jobs.insert(0, {"kind": "review", "item": review, "session": "conductor"})
    open_ = {i["number"] for i in issues}
    for issue in sorted(issues, key=lambda i: i["number"]):
        n = issue["number"]
        if n in named or session.LABEL not in session.labels_of(issue):
            continue
        waits = any(int(d) in open_ for d in DEPENDS.findall(str(issue.get("body") or "")))
        if (n not in ready) if ready is not None else waits:
            continue
        add("build", n, f"cb{n}{(ready or {}).get(n) or ''}", None)
    return jobs, held


def github_records(root: Path, repo: str) -> tuple[list, list, dict, dict]:
    """The open pull requests, briefs and their comments from GitHub, and the plan's starts
    (brief -> build letter); only the briefs the plan starts are read further."""
    plan = session_plan.build(root)
    ready = {r["brief"]: r.get("build") for r in [*plan.get("start", []), *plan.get("assign", [])]}
    pulls = session.pages(f"repos/{repo}/pulls?state=open")
    issues = session.pages(f"repos/{repo}/issues?state=open&labels={session.LABEL}")
    if pulls is None or issues is None:
        raise CheckError("the open pull requests and briefs cannot be read")
    briefs = [i for i in issues if "pull_request" not in i]
    comments = {}
    for n in [p["number"] for p in pulls] + [
        n for n in ready if n in {i["number"] for i in briefs}
    ]:
        if (said := session.pages(f"repos/{repo}/issues/{n}/comments")) is None:
            raise CheckError(f"#{n} cannot be read")
        comments[n] = said
    return pulls, briefs, comments, ready


def forge_records(root: Path) -> tuple[list, list, dict, None]:
    """The same records from a sidecar's files forge (personal mode): no `gh`, no network."""
    import forge

    files = forge.FilesForge(root)
    pulls = files.get("pulls-open", "pulls?state=open")
    issues = files.get(f"issues-{session.LABEL}", "issues?state=open")
    said = {x["number"]: files.get(f"comments-{x['number']}", "") or [] for x in pulls + issues}
    return pulls, issues, said, None


def jobs_command(root: Path, claiming: bool, now: datetime) -> int:
    """`jobs [--claim]`: the pass's jobs from GitHub, one line each (CI mode's launcher reads
    them and fires one cloud session per `job:` line); a review job waits for a held lease."""
    repo = session.repo_name(root)
    pulls, briefs, comments, ready = github_records(root, repo)
    jobs, held = pick(pulls, briefs, comments, now, ready)
    issue = conductor.plan_issue(root)
    lease = None if issue is None else conductor.lease_holder(
        conductor.plan_comments(repo, issue), conductor.verdict_authors(root), now)  # fmt: skip
    for job in jobs:
        if job["kind"] == "review" and lease:
            held.append(job | {"by": lease[0]})
            continue
        allowed, why = job_allowed(root, job["kind"], now)
        line = f"{job['kind']} #{job['item']} {job['session']}"
        if not allowed:
            print(f"not started: {line} ({why})")
        elif (
            claiming and job["kind"] != "review" and not conductor.claim_job(repo, job, stamp(now))
        ):
            print(f"not started: {line} (the claim cannot be posted)")
        else:
            print(f"job: {line}")
    for job in held:
        print(f"held: {job['kind']} #{job['item']} by {job['by']} (until its take lapses)")
    print("jobs: none" if not jobs and not held else "jobs: end")
    return 0


def next_command(root: Path, brief: int | None, now: datetime) -> int:
    """`next [--brief N]`: one job in the foreground, by the rules of `pick`, then end; it posts
    nothing (personal mode: the files forge keeps the results). `--brief N` is the owner's own yes
    to a build job (Q-S0064-8)."""
    personal = personal_table(root) is not None
    repo = root.name if personal else session.repo_name(root)
    pulls, briefs, comments, ready = (forge_records(root) if personal
                                      else github_records(root, repo))  # fmt: skip
    jobs, held = pick(pulls, briefs, comments, now, ready)
    if brief is not None:
        jobs = [{"kind": "build", "item": brief, "session": f"cb{brief}"}]
        held = [h for h in held if h["item"] == brief]
    job = next((j for j in jobs if job_allowed(root, j["kind"], now, brief is not None)[0]), None)
    if job is None or (brief is not None and held):
        why = f"held by {held[0]['by']}" if held else "no job is due"
        print(f"next: nothing started ({why})")
        return 0
    adapter = launch.launch_settings(root)[1]
    if not adapter or not adapter.strip():
        print("next: nothing started (setting: flow.launch_adapter)")
        return 2
    name, item = job["session"], job["item"]
    print(f"next: {job['kind']} #{item} {name}")
    if job["kind"] == "review":
        args = ["role", "--role", "conductor", "--session", "conductor-next", "--adapter", adapter]
        name, code = "conductor-next", launch.role_main(args, root=root)
    else:
        number = session.brief_number(next((p for p in pulls if p["number"] == item), {})) or item
        prompt = (launch.prompt_for(name, number) if job["kind"] == "build" else
                  launch.resume_for(name, number, None, item, None) + launch.FIX_JOB)  # fmt: skip
        prompt += PERSONAL_NOTE if personal else ""
        code = launch.start_with(adapter, [(name, number, None)], [prompt], None, root,
                                 [(job["kind"], item)])  # fmt: skip
    if code:
        return 1
    worktree = launch.worktree_of(root, name)
    for _ in range(NEXT_POLLS):  # the foreground: wait for the job's own exit file
        record = launch.read_record(worktree)
        if record is not None and launch.exited(worktree, record):
            break
        SLEEP(NEXT_POLL)
    ended = launch.fields_of(worktree / launch.EXIT_FILE).get("exit_code", "unknown")
    print(f"next: {name} ended (exit {ended})")
    return 0 if ended == "0" else 1


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    now = now or datetime.now(UTC)
    root = Path.cwd()
    if "--root" in args:
        at = args.index("--root")
        if at + 1 >= len(args):
            print(USAGE, file=sys.stderr)
            return 2
        root = Path(args[at + 1])
        del args[at : at + 2]
    if args in (["on"], ["off"]):
        return autopilot_on(root, args == ["on"])
    if args[:1] == ["budget"]:
        return budget_command(root, args[1:], now)
    if len(args) == 2 and args[0] == "retry" and args[1].isdigit():
        data = load_state(root)
        keep_state(root, data | {"retry": (data.get("retry") or {}) | {args[1]: stamp(now)}})
        print(f"autopilot: #{args[1]} may be retried")
        return 0
    if args in (["jobs"], ["jobs", "--claim"]):
        return jobs_command(root, args == ["jobs", "--claim"], now)
    if args[:1] == ["next"] and (args[1:] == [] or (args[1:2] == ["--brief"] and len(args) == 3
                                                    and args[2].isdigit())):  # fmt: skip
        return next_command(root, int(args[2]) if args[1:] else None, now)
    if args not in (["status"], ["status", "--week"]):
        print(USAGE, file=sys.stderr)
        return 2
    if args == ["status", "--week"]:
        return week(root, now)
    print("\n".join(mode_lines(root, now)))
    return status(root)


if __name__ == "__main__":
    sys.exit(main())
