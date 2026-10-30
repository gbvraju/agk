"""`launch.py prompts`: the prompts of a confirmed plan, and the adapter that starts the sessions.

    python3 launch.py prompts --plan FILE|- [--adapter COMMAND]

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
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess  # nosec B404 - fixed argument lists, no shell
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError

NAME = "launch"
USAGE = "usage: launch.py prompts --plan FILE|- [--adapter COMMAND]"
SEPARATOR = "-" * 72
SESSION_ID = re.compile(r"[A-Za-z0-9._-]+")

PROMPT = """\
You are session {session}, a builder of this repository. You work through pull requests only.
Read CLAUDE.md and config/session-rules.md first and follow them in full.
Your work is {work}: take it with
    python3 scripts/agk/session.py claim --session {session} --brief {brief}{flag}
If that prints a skip, stop and say why. Otherwise read the brief on GitHub (its issue), build it
from a fresh origin/<default branch> on its own branch, and open one pull request. Its body names
the brief with `Brief: #{brief}`; the pull request that finishes the brief (its only one, or the one
of its last build) also carries `Finishes: #{brief}`, so the brief closes when it merges. When your
work is done, run
    python3 scripts/agk/session.py after --session {session}
and do what it says. Report on your pull request; ask on it; never merge.
"""


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


def sessions(plan: dict) -> list[tuple[str, int, str | None]]:
    found: list[tuple[str, int, str | None]] = []
    for item in plan["start"]:
        name = item.get("session") if isinstance(item, dict) else None
        number = item.get("brief") if isinstance(item, dict) else None
        if not isinstance(name, str) or not SESSION_ID.fullmatch(name):
            raise CheckError("a session to start has no valid name (field session)")
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise CheckError("a session to start has no valid brief number (field brief)")
        build = item.get("build") if "build" in item else None
        if "build" in item and (not isinstance(build, str) or not SESSION_ID.fullmatch(build)):
            raise CheckError("a session to start has no valid build name (field build)")
        if any(name == other for other, _, _ in found):
            raise CheckError("a session to start is named twice (field session)")
        if any((number, build) == (n, b) for _, n, b in found):
            raise CheckError("a brief to start is named twice (field brief)")
        found.append((name, number, build))
    return found


def prompt_for(session: str, brief: int, build: str | None = None) -> str:
    work = f"build ({build}) of brief #{brief}" if build else f"brief #{brief}"
    flag = f" --build {build}" if build else ""
    return PROMPT.format(session=session, brief=brief, work=work, flag=flag)


def work_text(session: str, brief: int, build: str | None) -> str:
    return f"{session} #{brief}" + (f" build ({build})" if build else "")


def not_started(rest: list[tuple[str, int, str | None]]) -> None:
    """A refused adapter is reported, never retried: name each session it did not start."""
    for session, brief, build in rest:
        print(f"not started: {work_text(session, brief, build)}", file=sys.stderr)


def start_with(adapter: str, found: list[tuple[str, int, str | None]]) -> int:
    """Call the adapter once for each session; stop at the first one that fails."""
    words = shlex.split(adapter)
    if not words:
        raise CheckError("the adapter is empty (option --adapter)")
    for index, (session, brief, build) in enumerate(found):
        env = {**os.environ, "AGK_SESSION": session, "AGK_BRIEF": str(brief)}
        if build:
            env["AGK_BUILD"] = build
        try:
            done = subprocess.run(  # nosec B603 - the person's own command, split, no shell
                words,
                input=prompt_for(session, brief, build),
                text=True,
                encoding="utf-8",
                env=env,
                capture_output=True,
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
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
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
    try:
        plan = read_plan(opts["--plan"])
        found = sessions(plan)
        within_capacity(plan, len(found), required="--adapter" in opts)
        limit = max_builders(Path.cwd())
        if not found:
            print("no session to start")
            return 0
        found, beyond = found[:limit], found[limit:]
        if "--adapter" in opts:
            code = start_with(opts["--adapter"], found)
        else:
            print((SEPARATOR + "\n").join(prompt_for(s, b, x) for s, b, x in found), end="")
            code = 0
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}", file=sys.stderr)
        return 2
    if code == 0:
        for session, brief, build in beyond:
            print(f"not started: {work_text(session, brief, build)} (max_builders is {limit})")
    return code


if __name__ == "__main__":
    sys.exit(main())
