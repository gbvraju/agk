"""`launch.py prompts`: the prompts of a confirmed plan, and the adapter that starts the sessions.

    python3 launch.py prompts --plan FILE|- [--resume] [--adapter COMMAND]

Brief 247 build (b); SPEC-0034 rule 16. `FILE` is the plan that `session.py plan --json` printed
(`-` reads standard input). The script prints one ready-to-paste prompt for each session to start,
separated by a line of dashes. With `--adapter COMMAND` it calls that command once for each session
instead, with the prompt on its standard input and the session and the brief in the environment
(`AGK_SESSION`, `AGK_BRIEF` and, for a brief built in parts, `AGK_BUILD`); the command is split
into words and run without a shell. It starts nothing on its own: the person confirms the plan
first (the skill asks), it creates no recurring task, holds no credential and makes no network
call. What an adapter prints is its own and is never echoed. The title of a brief is data written
in an issue and is never put in a prompt: the session reads the brief itself.

Brief 331 (ADR-0190): a plan whose `start` list is longer than its `capacity.slots`, or that names
one brief (with its build) or one session twice, is refused before anything is printed or started;
a failing adapter is reported once, with a `not started:` line for each session after it, and
never called again. With `--adapter` a plan without a valid `capacity.slots` starts nothing, and
no run starts or prints more than `[flow] max_builders` (3 by default) of the folder it runs in;
each session past it gets a `not started:` line. `launch_settings` reads `auto_start` and
`launch_adapter` of the `[flow]` table of agk.toml, in the checkout or at a commit, the two
settings by which the conductor's review pass starts the planned sessions itself (its guard reads
them through this function, in the checkout and on the default branch).

Brief 402 (ADR-0219): with `--resume` it reads the plan's list `running` instead of `start`, one
entry per session that holds work (a live take or an open builder pull request: `session`,
`brief`, and optionally `build`, `pull_request` and `author`), and prints for each one a prompt of
one line that starts `You are session <id>`, names its brief and pull request, and tells it to run
`session.py queue --role builder --author <login>` and `session.py inbox --session <id>` first
(session rule 11), then carry on from GitHub alone. No running session prints nothing (exit 0).
With `--adapter` the adapter is called once per running session, as for a start; `max_builders`
still caps the run, and `capacity.slots` is not required (the running sessions hold their slots).

Brief 612 (ADR-0298): with `[flow] min_free_memory_mb` set (a whole number of MiB, 1 or more),
`--adapter`, starting or resuming, first reads the machine's free memory with
`common.available_memory` (standard library, no network). Below the floor it starts nothing,
prints `launch: not started: free memory below [flow] min_free_memory_mb` and exits 1; when the
memory cannot be read it prints one note naming the setting and starts as before. Unset, the
memory is not read. Printing the prompts starts nothing, so the floor does not apply there.

Brief 709 (SPEC-0045 rules 5 to 7, ADR-0289): each entry's `kind` (`design`, `build` or `small`,
which `session.py plan --json` writes from the brief; a running entry may also be `mechanical`;
none is `design`, the highest) is mapped by `config.model_settings` to a tier and an effort, which
every prompt names with the tier's model name from `[models.names]` when the project has one, and
the adapter gets as `AGK_KIND`, `AGK_TIER`, `AGK_EFFORT` and `AGK_MODEL`. A `small` or `mechanical`
prompt names the lean reading list instead of today's line. A running entry's `escalated_from`
(the tier it stopped on, never `strongest`) resumes it one tier up, at least at `build`'s effort.

Brief #1322 (SPEC-0059 rule 2, ADR-0559): `role --role steward|conductor --session ID [--adapter
COMMAND]` starts one role session: the steward (the conductor's start when a question waits) or the
conductor (the steward's start when the plan is ready). It prints the role's prompt, or with
`--adapter` calls the adapter once as above, with `AGK_SESSION`, `AGK_ROLE`, `AGK_AGENT`, the
`design` kind, tier and effort, and no `AGK_BRIEF`. A start that the adapter or the memory floor
refuses prints `stuck: <role> <session> not started (<why>)`, never silent (exit 1).

Brief #1355 (ADR-0568): both adapters write `<worktree>/.agk-session-pid` (`session=`, `pid=`,
`started_utc=`, `brief=`) before the session's first turn, beside the exit file. Before each
adapter call a session whose record shows a live process is refused, naming the session and never
a path: `launch: not started: session <name> is still running (one session per name)` (exit 1).
`read_record`, `exited`, `process_alive` and `stop_tree` are the watchdog's reads of that record.

Brief #1386 (SPEC-0064 rule 3, ADR-0584): each adapter call also gets `AGK_JOB_KIND` (`build` for a
start, `fix` for a resume of a pull request, `build` for one without, the role for `role`),
`AGK_ITEM` (`#<brief or pull request>`, empty for a role) and `AGK_HEAD` (empty until a supervisor
knows it), which the adapters add to the record as `kind=`, `item=` and `head=`; `read_record`
reads them, leaving out a field that is absent or not of its form.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import signal
import subprocess  # nosec B404 - fixed argument lists, no shell
import sys
import tomllib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, available_memory, utf8_output

import config

NAME = "launch"
USAGE = "usage: launch.py prompts --plan FILE|- [--resume] [--adapter COMMAND]"
SEPARATOR = "-" * 72
SESSION_ID = re.compile(r"[A-Za-z0-9._-]+")
LOGIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,38}")  # a GitHub login, managed ones too (ADR-0563)

FULL_READING = "Read CLAUDE.md and config/session-rules.md first and follow them in full."
LEAN_READING = (
    "Read only CLAUDE.md, constitution/principles.md, config/core-rules.md, the brief or the "
    "follow-up message and the files they name (a lean session, SPEC-0045 rule 7); still run "
    "`doctor.py --paused` (session rule 33) and `prepush.py` (session rule 31) as they say."
)
KINDS = ("design", "build", "small")  # a brief's kinds (rule 4); `mechanical` is a follow-up's
FOLLOW_UP_KINDS = (*KINDS, "mechanical")
LEAN_KINDS = ("small", "mechanical")
# Recaps off for agent sessions (brief #1310 answer 4, ADR-0554; verify: the runtime's variable)
QUIET = {"CLAUDE_CODE_ENABLE_AWAY_SUMMARY": "0"}
TIERS = config.MODEL_TIERS  # strongest first
EFFORTS = config.MODEL_EFFORTS  # lowest first
KIND_LINE = "Kind: {kind}; tier: {tier}; effort: {effort}{model}. {stop}"
STOP_BELOW = (
    "You run below `strongest`: when the same check fails in two runs in a row, a conflict cannot "
    "be resolved or a change would touch a protected class the brief's `Touches:` does not name, "
    "stop, push nothing more and post `Report: <head> escalate <reason>` (session rule 21)."
)
STOP_TOP = "You never escalate: when blocked, ask with `Question:` (session rule 21)."
Run = tuple[str, str, str, str | None]  # kind, tier, effort, the project's model name or None
DESIGN: Run = (
    "design",
    config.MODEL_DEFAULTS["design"][0],
    config.MODEL_DEFAULTS["design"][1],
    None,
)

PROMPT = """\
You are session {session}, a builder of this repository. You work through pull requests only.
{reading}
Your work is {work}: take it with
    python3 scripts/agk/session.py claim --session {session} --brief {brief}{flag}
If that prints a skip, stop and say why. Otherwise read the brief on GitHub (its issue), build it
from a fresh origin/<default branch> on its own branch, and open one pull request. Its body names
the brief with `Brief: #{brief}`; the pull request that finishes the brief (its only one, or the one
of its last build) also carries `Finishes: #{brief}`, so the brief closes when it merges. When your
work is done, run
    python3 scripts/agk/session.py after --session {session}
and do what it says. Report on your pull request; ask on it; never merge.
{kind_line}
"""


RESUME = (
    "You are session {session}, a builder of this repository, and you resume your work: {work}, "
    "{where}. {reading} Then run "
    "`python3 scripts/agk/session.py queue --role builder{author}; "
    "python3 scripts/agk/session.py inbox --session {session}` (session rule 11) and carry on "
    "from what they and GitHub show: {carry} {kind_line} When your work is done, run "
    "`python3 scripts/agk/session.py after --session {session}` and do what it says. "
    "Report on your pull request; ask on it; never merge.\n"
)
CARRY_PR = (
    "run `python3 scripts/agk/session.py resume --pr {pr}` and continue from its `next:` step on "
    "the same branch and the same pull request (session rule 9); never open a second one."
)
CARRY_TAKE = (
    "the brief is already yours, so do not take it again; read it on GitHub, build it from a "
    "fresh origin/<default branch> on its own branch and open one pull request that names it "
    "with `Brief: #{brief}`."
)


def read_plan(source: str) -> dict:
    try:
        text = (
            sys.stdin.buffer.read().decode("utf-8")
            if source == "-"
            else Path(source).read_text(encoding="utf-8")
        )
        plan = json.loads(text)
    except (OSError, UnicodeDecodeError, ValueError):
        raise CheckError("the plan cannot be read as JSON (option --plan)") from None
    if not isinstance(plan, dict) or not isinstance(plan.get("start"), list):
        raise CheckError("the plan has no list `start` (field start)")
    return plan


BRANCH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")  # a branch name git reads as nothing else
MAX_BUILDERS = 3  # the default of `[flow] max_builders`, as `session.py` reads it


def flow_of(text: str | None) -> dict:
    """The `[flow]` table of an agk.toml text ({} when there is no file or no table)."""
    if text is None:
        return {}
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        raise CheckError("agk.toml cannot be read") from None
    table = data.get("flow", {})
    return table if isinstance(table, dict) else {}


def checkout_text(root: Path) -> str | None:
    try:
        return (Path(root) / "agk.toml").read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError):
        raise CheckError("agk.toml cannot be read") from None


def text_at(root: Path, ref: str) -> str | None:
    """agk.toml as it stands at REF (None when REF has none); a REF git cannot read is refused."""
    found = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if found.returncode != 0:
        raise CheckError("the default branch cannot be read (setting default_branch)")
    shown = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "show", f"{found.stdout.strip()}:agk.toml"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return shown.stdout if shown.returncode == 0 else None


def launch_settings(root: Path, ref: str | None = None) -> tuple[bool, str | None]:
    """(`auto_start`, `launch_adapter`) of the `[flow]` table of agk.toml, in the checkout or, with
    REF, as it stands at that commit: off and none when unset (an empty `launch_adapter` is unset);
    a value of the wrong kind is refused naming the setting, never the value."""
    table = flow_of(checkout_text(root) if ref is None else text_at(root, ref))
    auto = table.get("auto_start", False)
    if not isinstance(auto, bool):
        raise CheckError("auto_start of the flow table must be true or false")
    adapter = table.get("launch_adapter")
    if adapter == "":  # "" is unset, as `unused_code = ""` is off
        adapter = None
    if adapter is not None and (not isinstance(adapter, str) or not adapter.strip()):
        raise CheckError("launch_adapter of the flow table must be a command (a non-empty string)")
    return auto, adapter


def default_branch(root: Path) -> str:
    """`default_branch` of the checkout's agk.toml ("main" when unset), a plain branch name."""
    text = checkout_text(root)
    try:
        name = tomllib.loads(text).get("default_branch", "main") if text is not None else "main"
    except tomllib.TOMLDecodeError:
        raise CheckError("agk.toml cannot be read") from None
    if not isinstance(name, str) or not BRANCH.fullmatch(name) or ".." in name:
        raise CheckError("default_branch must be a branch name (setting default_branch)")
    return name


def max_builders(root: Path) -> int:
    """`[flow] max_builders` of the checkout's agk.toml (3 when unset), a whole number 1 or up."""
    value = flow_of(checkout_text(root)).get("max_builders", MAX_BUILDERS)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CheckError("max_builders of the flow table must be a whole number, 1 or more")
    return value


MIB = 1024**2
MEMORY_SETTING = "[flow] min_free_memory_mb"


def min_free_memory_mb(root: Path) -> int | None:
    """`[flow] min_free_memory_mb` of the checkout's agk.toml (None when unset), a whole number
    1 or up; any other value is refused naming the setting, never the value."""
    value = flow_of(checkout_text(root)).get("min_free_memory_mb")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CheckError("min_free_memory_mb of the flow table must be a whole number, 1 or more")
    return value


def memory_allows(root: Path) -> bool:
    """False, with one line naming the setting, when free memory is below the floor (brief 612);
    True when the floor is unset, met, or the memory cannot be read (then with one note)."""
    floor = min_free_memory_mb(root)
    if floor is None:
        return True
    free = available_memory()
    if free is None:
        print(
            f"launch: note: free memory cannot be read; started without {MEMORY_SETTING}",
            file=sys.stderr,
        )
        return True
    if free < floor * MIB:
        print(f"launch: not started: free memory below {MEMORY_SETTING}", file=sys.stderr)
        return False
    return True


def within_capacity(plan: dict, count: int, required: bool = False) -> None:
    """A plan starts at most `capacity.slots` sessions (brief 331); with an adapter
    (REQUIRED) a plan without a valid `capacity.slots` starts nothing."""
    if "capacity" not in plan and not required:
        return
    capacity = plan.get("capacity")
    slots = capacity.get("slots") if isinstance(capacity, dict) else None
    if isinstance(slots, bool) or not isinstance(slots, int) or slots < 0:
        raise CheckError("the plan's capacity has no valid slots (field capacity)")
    if count > slots:
        raise CheckError("the plan starts more sessions than its slots (field capacity)")


def sessions(plan: dict, what: str = "a session to start") -> list[tuple[str, int, str | None]]:
    found: list[tuple[str, int, str | None]] = []
    for item in plan["start"]:
        name = item.get("session") if isinstance(item, dict) else None
        number = item.get("brief") if isinstance(item, dict) else None
        if not isinstance(name, str) or not SESSION_ID.fullmatch(name):
            raise CheckError(f"{what} has no valid name (field session)")
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise CheckError(f"{what} has no valid brief number (field brief)")
        build = item.get("build") if "build" in item else None
        if "build" in item and (not isinstance(build, str) or not SESSION_ID.fullmatch(build)):
            raise CheckError(f"{what} has no valid build name (field build)")
        if any(name == other for other, _, _ in found):
            raise CheckError(f"{what} is named twice (field session)")
        if any((number, build) == (n, b) for _, n, b in found):
            raise CheckError("a brief to start is named twice (field brief)")
        found.append((name, number, build))
    return found


Running = tuple[str, int, str | None, int | None, str | None]


def running_sessions(plan: dict) -> list[Running]:
    """(session, brief, build, pull request, author) of each entry of the plan's `running` list,
    in its order; no list (or `null`) is no running session."""
    items = plan.get("running")
    if items is None:
        return []
    if not isinstance(items, list):
        raise CheckError("the plan's running sessions are not a list (field running)")
    found: list[Running] = []
    for item in items:
        if not isinstance(item, dict):
            raise CheckError("a running session has no valid name (field session)")
        name, number, build = sessions({"start": [item]}, "a running session")[0]
        pr = item.get("pull_request")
        if "pull_request" in item and (isinstance(pr, bool) or not isinstance(pr, int) or pr < 1):
            raise CheckError("a running session has no valid pull request (field pull_request)")
        author = item.get("author")
        if "author" in item and (not isinstance(author, str) or not LOGIN.fullmatch(author)):
            raise CheckError("a running session has no valid author (field author)")
        if any(name == other[0] for other in found):
            raise CheckError("a running session is named twice (field session)")
        found.append((name, number, build, pr, author))
    return found


def reading_of(run: Run) -> str:
    return LEAN_READING if run[0] in LEAN_KINDS else FULL_READING


def kind_line(run: Run) -> str:
    kind, tier, effort, model = run
    stop = STOP_TOP if tier == TIERS[0] else STOP_BELOW
    shown = f"; model: {model}" if model else ""
    return KIND_LINE.format(kind=kind, tier=tier, effort=effort, model=shown, stop=stop)


def runs_of(items: list, kinds: tuple[str, ...], what: str) -> list[Run]:
    """The kind, tier, effort and model name of each entry (brief 709): no kind is `design`; an
    `escalated_from` (running entries only) is one tier up, never below the kind's own tier, at
    least at `build`'s effort; the table and names come from the checkout's agk.toml."""
    settings = config.model_settings(Path.cwd())
    names = config.model_names(Path.cwd())
    found: list[Run] = []
    for item in items:
        kind = item.get("kind", "design")
        if not isinstance(kind, str) or kind not in kinds:
            raise CheckError(f"{what} has no valid kind (field kind)")
        tier, effort = settings[kind]["tier"], settings[kind]["effort"]
        if "escalated_from" in item:
            was = item["escalated_from"]
            if kinds is KINDS or not isinstance(was, str) or was not in TIERS[1:]:
                raise CheckError(f"{what} has no valid escalation (field escalated_from)")
            tier = TIERS[min(TIERS.index(tier), TIERS.index(was) - 1)]
            effort = EFFORTS[max(EFFORTS.index(effort), EFFORTS.index(settings["build"]["effort"]))]
        found.append((kind, tier, effort, names.get(tier)))
    return found


def resume_for(
    session: str,
    brief: int,
    build: str | None,
    pr: int | None,
    author: str | None,
    run: Run = DESIGN,
):
    """The one-line prompt that resumes a running session from GitHub alone (brief 402)."""
    work = f"build ({build}) of brief #{brief}" if build else f"brief #{brief}"
    where = f"pull request #{pr}" if pr else "no pull request yet"
    carry = CARRY_PR.format(pr=pr) if pr else CARRY_TAKE.format(brief=brief)
    return RESUME.format(
        session=session,
        work=work,
        where=where,
        author=f" --author {author}" if author else "",
        carry=carry,
        reading=reading_of(run),
        kind_line=kind_line(run),
    )


def prompt_for(session: str, brief: int, build: str | None = None, run: Run = DESIGN) -> str:
    work = f"build ({build}) of brief #{brief}" if build else f"brief #{brief}"
    flag = f" --build {build}" if build else ""
    return PROMPT.format(
        session=session,
        brief=brief,
        work=work,
        flag=flag,
        reading=reading_of(run),
        kind_line=kind_line(run),
    )


# --- one session per name (brief #1355, ADR-0568) -----------------------------------------

RECORD_FILE = ".agk-session-pid"  # written by the adapter before the first turn; never tracked
EXIT_FILE = ".agk-session-exit"
JOB_KINDS = ("review", "build", "fix", "steward", "conductor")  # SPEC-0064 rule 3
ITEM = re.compile(r"#[1-9]\d*")
HEAD = re.compile(r"[0-9a-f]{7,40}")
STILL_RUNNING = "launch: not started: session {name} is still running (one session per name)"


def worktree_of(root: Path, session: str) -> Path:
    """The adapters' worktree of a session: `agk-<session>` beside the checkout."""
    return Path(root).resolve().parent / f"agk-{session}"


def utc_of(text: object) -> datetime | None:
    try:
        return datetime.strptime(str(text), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def fields_of(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError):
        return {}
    return dict(x.strip().split("=", 1) for x in lines if "=" in x)


def read_record(worktree: Path) -> dict | None:
    """The process record of a worktree, or None when there is none or it cannot be read."""
    found = fields_of(Path(worktree) / RECORD_FILE)
    pid, brief = found.get("pid", ""), found.get("brief", "")
    name = found.get("session", "")
    if not (pid.isdigit() and SESSION_ID.fullmatch(name) and utc_of(found.get("started_utc"))):
        return None
    record: dict = {
        "session": name,
        "pid": int(pid),
        "started_utc": found["started_utc"],
        "brief": int(brief) if brief.isdigit() else None,
    }
    # Brief #1386: a job field of its form only, so a #1355 record reads as before.
    if found.get("kind") in JOB_KINDS:
        record["kind"] = found["kind"]
    for key, form in (("item", ITEM), ("head", HEAD)):
        if form.fullmatch(found.get(key, "")):
            record[key] = found[key]
    return record


def exited(worktree: Path, record: dict) -> bool:
    """Whether the exit file is not older than the record: the recorded session ended."""
    ended = utc_of(fields_of(Path(worktree) / EXIT_FILE).get("ended_utc"))
    started = utc_of(record.get("started_utc"))
    return ended is not None and started is not None and ended >= started


def process_alive(pid: int) -> bool:
    """Whether a process of that id exists (verify: an id can be reused after its process ends)."""
    if pid < 1:
        return False
    if sys.platform == "win32":
        done = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
            capture_output=True, text=True, encoding="utf-8", check=False,
        )  # fmt: skip
        return f'"{pid}"' in done.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def has_process(worktree: Path) -> bool:
    """The worktree's record names a process that is there and has not written its exit file."""
    record = read_record(worktree)
    return record is not None and not exited(worktree, record) and process_alive(record["pid"])


WINDOWS_TABLE = (
    "Get-CimInstance Win32_Process | ForEach-Object { '{0} {1} {2}' -f $_.ProcessId, "
    "$_.ParentProcessId, [int64](($_.KernelModeTime + $_.UserModeTime) / 10000000) }"
)


def cpu_seconds(text: str) -> int | None:
    """Whole CPU seconds of `[[dd-]hh:]mm:ss[.cc]` (ps) or of a bare count (Windows)."""
    days, _, clock = text.rpartition("-")
    parts = clock.split(":")
    if (days and not days.isdigit()) or len(parts) > 3:
        return None
    try:
        total = 0.0
        for part in parts:
            total = total * 60 + float(part)
    except ValueError:
        return None
    return int(total) + int(days or 0) * 86400


def process_table(run=subprocess.run, platform: str | None = None) -> dict | None:
    """{pid: (parent pid, CPU seconds)} of every process, or None when it cannot be read (verify:
    `ps -o time=` on POSIX, `Get-CimInstance Win32_Process` through PowerShell on Windows)."""
    if (platform or sys.platform) == "win32":
        words = ["powershell", "-NoProfile", "-Command", WINDOWS_TABLE]
    else:
        words = ["ps", "-A", "-o", "pid=,ppid=,time="]
    try:
        done = run(words, capture_output=True, text=True, encoding="utf-8")
    except OSError:
        return None
    if done.returncode != 0:
        return None
    table = {}
    for line in done.stdout.splitlines():
        parts = line.split()
        cpu = cpu_seconds(parts[2]) if len(parts) == 3 else None
        if cpu is not None and parts[0].isdigit() and parts[1].isdigit():
            table[int(parts[0])] = (int(parts[1]), cpu)
    return table


def tree_cpu(pid: int, table: dict) -> dict[int, int]:
    """{pid: CPU seconds} of PID and every process below it in TABLE."""
    found: dict[int, int] = {}
    todo = [pid]
    while todo:
        current = todo.pop()
        if current in table and current not in found:
            found[current] = table[current][1]
            todo += [p for p, (parent, _) in table.items() if parent == current]
    return found


def stop_tree(pid: int, run=subprocess.run, platform: str | None = None) -> None:
    """Stop the process PID and every process below it, and nothing else (ADR-0568 decision 3)."""
    if (platform or sys.platform) == "win32":
        run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True, text=True, encoding="utf-8",
        )  # fmt: skip
        return
    table = run(
        ["ps", "-A", "-o", "pid=,ppid="], capture_output=True, text=True, encoding="utf-8"
    ).stdout
    children: dict[int, list[int]] = {}
    for line in table.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            children.setdefault(int(parts[1]), []).append(int(parts[0]))
    tree, todo = [], [pid]
    while todo:
        tree.append(todo.pop())
        todo += [c for c in children.get(tree[-1], []) if c not in tree]
    for found in tree:
        try:
            os.kill(found, signal.SIGTERM)
        except OSError:
            continue


def work_text(session: str, brief: int, build: str | None) -> str:
    return f"{session} #{brief}" + (f" build ({build})" if build else "")


def not_started(rest: list[tuple[str, int, str | None]]) -> None:
    """A refused adapter is reported, never retried: name each session it did not start."""
    for session, brief, build in rest:
        print(f"not started: {work_text(session, brief, build)}", file=sys.stderr)


def start_with(
    adapter: str,
    found: list[tuple[str, int, str | None]],
    prompts: list[str] | None = None,
    runs: list[Run] | None = None,
    root: Path | None = None,
    jobs: list[tuple[str, int] | None] | None = None,
) -> int:
    """Call the adapter once for each session; stop at the first one that fails; a session whose
    record shows a live process is refused and the others still start (brief #1355). PROMPTS, when
    given, are the prompts of the sessions in order (the resume prompts of brief 402); RUNS are
    their kinds, tiers, efforts and model names (brief 709), `design` when not given; JOBS are their
job kinds and items (brief #1386), `build` of the brief when not given."""
    words = shlex.split(adapter)
    if not words:
        raise CheckError("the adapter is empty (option --adapter)")
    refused = 0
    for index, (session, brief, build) in enumerate(found):
        if has_process(worktree_of(root or Path.cwd(), session)):
            print(STILL_RUNNING.format(name=session), file=sys.stderr)
            refused = 1
            continue
        env = {**os.environ, **QUIET, "AGK_SESSION": session, "AGK_BRIEF": str(brief)}
        if build:
            env["AGK_BUILD"] = build
        job_kind, item = (jobs[index] if jobs else None) or ("build", brief)
        env.update({"AGK_JOB_KIND": job_kind, "AGK_ITEM": f"#{item}", "AGK_HEAD": ""})
        run = runs[index] if runs else DESIGN
        kind, tier, effort, model = run
        env.update({"AGK_KIND": kind, "AGK_TIER": tier, "AGK_EFFORT": effort})
        if model:
            env["AGK_MODEL"] = model
        try:
            done = subprocess.run(  # nosec B603 - the person's own command, split, no shell
                words,
                input=prompts[index] if prompts else prompt_for(session, brief, build, run),
                text=True,
                encoding="utf-8",
                env=env,
                capture_output=True,
                cwd=root,
            )
        except OSError:
            print(f"FAIL {NAME}: the adapter cannot be run for {session}", file=sys.stderr)
            not_started(found[index + 1 :])
            return 1
        if done.returncode != 0:
            print(f"FAIL {NAME}: the adapter failed for {session}", file=sys.stderr)
            not_started(found[index + 1 :])
            return 1
        print(f"started {work_text(session, brief, build)}")
    return refused


ROLES = ("steward", "conductor")
ROLE_PROMPT = (
    "You are session {session}, the {role} of this repository. Start the role with "
    "`claude --agent {role}` (verify: the flag of the runtime used) and follow "
    "`.claude/agents/{role}.md`. Read CLAUDE.md, constitution/principles.md and "
    "config/core-rules.md first. {kind_line}\n"
)


def role_main(args: list[str]) -> int:
    """`role --role steward|conductor --session ID [--adapter COMMAND]` (brief #1322)."""
    opts = dict(zip(args[1::2], args[2::2], strict=False))
    if (
        len(args[1:]) % 2
        or len(opts) != len(args[1::2])
        or not {"--role", "--session"} <= set(opts) <= {"--role", "--session", "--adapter"}
        or opts["--role"] not in ROLES
        or not SESSION_ID.fullmatch(opts["--session"])
    ):
        print("usage: launch.py role --role steward|conductor --session ID [--adapter COMMAND]",
              file=sys.stderr)  # fmt: skip
        return 2
    role, session = opts["--role"], opts["--session"]
    prompt = ROLE_PROMPT.format(session=session, role=role, kind_line=kind_line(DESIGN))
    if "--adapter" not in opts:
        print(prompt, end="")
        return 0
    stuck = f"stuck: {role} {session} not started"
    words = shlex.split(opts["--adapter"])
    if not words:
        print(f"{stuck} (the adapter is empty)")
        return 1
    try:
        allowed = memory_allows(Path.cwd())
    except CheckError:
        allowed = False
    if not allowed:
        print(f"{stuck} (setting: flow.min_free_memory_mb)")
        return 1
    if has_process(worktree_of(Path.cwd(), session)):
        print(f"{stuck} (one session per name)")
        return 1
    env = {k: v for k, v in os.environ.items() if k not in ("AGK_BRIEF", "AGK_BUILD")}
    env.update(QUIET, AGK_SESSION=session, AGK_ROLE=role, AGK_AGENT=role)
    env.update(AGK_JOB_KIND=role, AGK_ITEM="", AGK_HEAD="")
    env.update(AGK_KIND=DESIGN[0], AGK_TIER=DESIGN[1], AGK_EFFORT=DESIGN[2])
    try:
        done = subprocess.run(  # nosec B603 - the person's own command, split, no shell
            words, input=prompt, text=True, encoding="utf-8", env=env, capture_output=True
        )
    except OSError:
        print(f"{stuck} (the adapter cannot be run)")
        return 1
    if done.returncode != 0:
        print(f"{stuck} (the adapter failed)")
        return 1
    print(f"started {role} {session}")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["role"]:
        return role_main(args)
    resume = args.count("--resume") == 1 and args[:1] == ["prompts"]
    if resume:
        args.remove("--resume")
    opts = dict(zip(args[1::2], args[2::2], strict=False))
    if (
        args[:1] != ["prompts"]
        or len(args[1:]) % 2
        or "--plan" not in opts
        or not set(opts) <= {"--plan", "--adapter"}
        or len(opts) != len(args[1::2])
    ):
        print(USAGE, file=sys.stderr)
        return 2
    if resume:
        return resume_main(opts)
    try:
        plan = read_plan(opts["--plan"])
        found = sessions(plan)
        within_capacity(plan, len(found), required="--adapter" in opts)
        limit = max_builders(Path.cwd())
        if not found:
            print("no session to start")
            return 0
        runs = runs_of(plan["start"][:limit], KINDS, "a session to start")
        found, beyond = found[:limit], found[limit:]
        if "--adapter" in opts and not memory_allows(Path.cwd()):
            return 1
        if "--adapter" in opts:
            code = start_with(opts["--adapter"], found, runs=runs)
        else:
            texts = (prompt_for(s, b, x, r) for (s, b, x), r in zip(found, runs, strict=True))
            print((SEPARATOR + "\n").join(texts), end="")
            code = 0
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}", file=sys.stderr)
        return 2
    if code == 0:
        for session, brief, build in beyond:
            print(f"not started: {work_text(session, brief, build)} (max_builders is {limit})")
    return code


def resume_main(opts: dict) -> int:
    """`prompts --resume`: one resume prompt (or one adapter call) per running session."""
    try:
        plan = read_plan(opts["--plan"])
        found = running_sessions(plan)
        limit = max_builders(Path.cwd())
        if not found:
            return 0
        runs = runs_of(plan["running"][:limit], FOLLOW_UP_KINDS, "a running session")
        found, beyond = found[:limit], found[limit:]
        prompts = [resume_for(*item, run) for item, run in zip(found, runs, strict=True)]
        if "--adapter" in opts and not memory_allows(Path.cwd()):
            return 1
        if "--adapter" in opts:
            jobs = [("fix", item[3]) if item[3] else None for item in found]
            code = start_with(opts["--adapter"], [x[:3] for x in found], prompts, runs, jobs=jobs)
        else:
            print((SEPARATOR + "\n").join(prompts), end="")
            code = 0
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}", file=sys.stderr)
        return 2
    if code == 0:
        for session, brief, build, _, _ in beyond:
            print(f"not started: {work_text(session, brief, build)} (max_builders is {limit})")
    return code


if __name__ == "__main__":
    sys.exit(main())
