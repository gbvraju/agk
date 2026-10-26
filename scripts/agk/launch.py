"""`launch.py prompts`: the prompts of a confirmed plan, and the adapter that starts the sessions.

    python3 launch.py prompts --plan FILE|- [--adapter COMMAND]

Brief 247 build (b); SPEC-0034 rule 16. `FILE` is the plan that `session.py plan --json` printed
(`-` reads standard input). The script prints one ready-to-paste prompt for each session to start,
separated by a line of dashes. With `--adapter COMMAND` it calls that command once for each session
instead, with the prompt on its standard input and the session and the brief in the environment
(`AGK_SESSION` and `AGK_BRIEF`); the command is split into words and run without a shell. It
starts nothing on its own: the person confirms the plan first (the skill asks), it creates no
recurring task, holds no credential and makes no network call. What an adapter prints is its own
and is never echoed. The title of a brief is data written in an issue and is never put in a
prompt: the session reads the brief itself.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess  # nosec B404 - fixed argument lists, no shell
import sys
from pathlib import Path

from common import CheckError

NAME = "launch"
USAGE = "usage: launch.py prompts --plan FILE|- [--adapter COMMAND]"
SEPARATOR = "-" * 72
SESSION_ID = re.compile(r"[A-Za-z0-9._-]+")

PROMPT = """\
You are session {session}, a builder of this repository. You work through pull requests only.
Read CLAUDE.md and config/session-rules.md first and follow them in full.
Your work is brief #{brief}: take it with
    python3 scripts/agk/session.py claim --session {session} --brief {brief}
If that prints a skip, stop and say why. Otherwise read the brief on GitHub (its issue), build it
from a fresh origin/<default branch> on its own branch, and open one pull request. When your work
is done, run
    python3 scripts/agk/session.py after --session {session}
and do what it says. Report on your pull request; ask on it; never merge.
"""


def read_plan(source: str) -> dict:
    try:
        text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
        plan = json.loads(text)
    except (OSError, UnicodeDecodeError, ValueError):
        raise CheckError("the plan cannot be read as JSON (option --plan)") from None
    if not isinstance(plan, dict) or not isinstance(plan.get("start"), list):
        raise CheckError("the plan has no list `start` (field start)")
    return plan


def sessions(plan: dict) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for item in plan["start"]:
        name = item.get("session") if isinstance(item, dict) else None
        number = item.get("brief") if isinstance(item, dict) else None
        if not isinstance(name, str) or not SESSION_ID.fullmatch(name):
            raise CheckError("a session to start has no valid name (field session)")
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise CheckError("a session to start has no valid brief number (field brief)")
        found.append((name, number))
    return found


def prompt_for(session: str, brief: int) -> str:
    return PROMPT.format(session=session, brief=brief)


def start_with(adapter: str, found: list[tuple[str, int]]) -> int:
    """Call the adapter once for each session; stop at the first one that fails."""
    words = shlex.split(adapter)
    if not words:
        raise CheckError("the adapter is empty (option --adapter)")
    for session, brief in found:
        env = {**os.environ, "AGK_SESSION": session, "AGK_BRIEF": str(brief)}
        try:
            done = subprocess.run(  # nosec B603 - the person's own command, split, no shell
                words, input=prompt_for(session, brief), text=True, env=env, capture_output=True
            )
        except OSError:
            print(f"FAIL {NAME}: the adapter cannot be run for {session}", file=sys.stderr)
            return 1
        if done.returncode != 0:
            print(f"FAIL {NAME}: the adapter failed for {session}", file=sys.stderr)
            return 1
        print(f"started {session} #{brief}")
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
        found = sessions(read_plan(opts["--plan"]))
        if not found:
            print("no session to start")
            return 0
        if "--adapter" in opts:
            return start_with(opts["--adapter"], found)
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}", file=sys.stderr)
        return 2
    print((SEPARATOR + "\n").join(prompt_for(s, b) for s, b in found), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
