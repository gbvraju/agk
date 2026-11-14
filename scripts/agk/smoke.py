"""The smoke run after a merge, chosen by what changed (SPEC-0044 rule 8, brief #923, ADR-0270).

    python3 scripts/agk/smoke.py [--base REF] [--head REF] [--run]

It reads the paths changed between `--base` and `--head` from local git; without them, those of
the last merge on the default branch: `--head` is `origin/<default_branch>`, else the local
branch, and `--base` is the head's first parent. It prints one line, `smoke: <choice>: <reason>`:

- `none` when every changed file is documentation (`impact.is_doc`) and none matches `always_full`
  (`Q-S0044-3`): nothing runs;
- `frontend` or `contract`, the kind of `[testing] smoke` whose `code` every changed file outside
  documentation matches: that kind's command runs;
- `full` for anything else: a file of `always_full`, a file in no kind, files of two kinds, or no
  `[testing] smoke` list (the run of today): `project_tests.py`, the project's `project_tests`.

With `--run` it runs the choice under the heavy-step lock (`lock.py run --name heavy`, with the
session of `AGK_SESSION`; not taken again when this run's caller holds it) and exits with its
code. It writes nothing else and makes no network call. It is never a gate: CI's push run and the
release run do not change, and its choice is never the evidence of a gate (`Q-S0044-8`).

Exit: 0 printed (with `--run`, the command's code), 2 a usage error or a refused setting, which
names the setting, never its value.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - fixed argument lists only
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import lock as heavy_lock
from common import CheckError, git, load_config, repo_root, utf8_output
from impact import changed_files, is_doc, matches, smoke_entries, testing_table
from prepush import LOCK, caller_slot

HERE = Path(__file__).resolve().parent
USAGE = "usage: smoke.py [--base REF] [--head REF] [--run]"


class Usage(Exception):
    """A usage error (exit 2)."""


def parse_args(args: list[str]) -> dict:
    options: dict = {"base": None, "head": None, "run": False}
    i = 0
    while i < len(args):
        if args[i] in ("--base", "--head") and i + 1 < len(args) and options[args[i][2:]] is None:
            options[args[i][2:]] = args[i + 1]
            i += 2
        elif args[i] == "--run" and not options["run"]:
            options["run"] = True
            i += 1
        else:
            raise Usage(USAGE)
    return options


def commit(root: Path, ref: str) -> str | None:
    out = git(root, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}", check=False).strip()
    return out or None


def resolve(root: Path, base: str | None, head: str | None) -> tuple[str, str]:
    """The range: the given refs, else the last merge on the default branch."""
    if head is None:
        branch = load_config(root)["default_branch"]
        found = commit(root, f"origin/{branch}") or commit(root, branch)
        if found is None:
            raise CheckError("the default branch does not resolve (setting: default_branch)")
    else:
        found = commit(root, head)
        if found is None:
            raise CheckError("the given ref does not resolve (option: --head)")
    if base is None:
        start = commit(root, f"{found}^1")
        if start is None:
            raise CheckError("the head has no parent to compare with (option: --base)")
    else:
        start = commit(root, base)
        if start is None:
            raise CheckError("the given ref does not resolve (option: --base)")
    return start, found


def choose(root: Path, base: str, head: str) -> tuple[str, str, str | None]:
    """(choice, reason, the kind's command) for the changed paths; rule 8's order."""
    table = testing_table(root)
    entries = smoke_entries(root)
    changed = changed_files(root, base, head)
    for path in changed:
        for glob in table["always_full"] if table else []:
            if matches(path, glob):
                return "full", f"always_full {glob} matches {path}", None
    code = [p for p in changed if not is_doc(p)]
    if not changed:
        return "none", "no file changed", None
    if not code:
        return "none", f"only documentation changed ({len(changed)} files)", None
    if entries is None:
        return "full", "no [testing] smoke list (setting: testing.smoke)", None
    kinds: dict[str, str] = {}
    for path in code:
        found = [e for e in entries if any(matches(path, g) for g in e["code"])]
        if not found:
            return "full", f"{path} is in no smoke kind", None
        kinds.update((e["kind"], e["command"]) for e in found)
    if len(kinds) > 1:
        return "full", f"files of two kinds ({', '.join(kinds)})", None
    kind, command = next(iter(kinds.items()))
    reason = f"every changed file outside documentation matches its code ({len(code)} files)"
    return kind, reason, command


def run(root: Path, argv: list[str]) -> int:
    """ARGV under the heavy-step lock, or directly when this run's caller holds it."""
    env = {k: v for k, v in os.environ.items() if k != "EVENT"}  # project_tests.py: a full run
    held = heavy_lock.lock_folder(root, LOCK)
    if caller_slot(held, heavy_lock.slots_setting(root)) is None:
        session = os.environ.get("AGK_SESSION") or ""
        locked = [sys.executable, str(HERE / "lock.py"), "run", "--name", LOCK]
        argv = [*locked, *(["--session", session] if session else []), "--", *argv]
    else:
        print(f"lock {LOCK}: held by this run's caller (lock.py run); not taken again", flush=True)
    proc = subprocess.run(argv, cwd=root, env=env)  # nosec B603 - the project's own command
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    try:
        options = parse_args(list(sys.argv[1:] if argv is None else argv))
        root = repo_root()
        base, head = resolve(root, options["base"], options["head"])
        choice, reason, command = choose(root, base, head)
    except Usage as exc:
        print(exc)
        return 2
    except CheckError as exc:
        print(f"smoke: {exc}")
        return 2
    print(f"smoke: {choice}: {reason}", flush=True)
    if not options["run"] or choice == "none":
        return 0
    if command is None:
        argv_run = [sys.executable, str(HERE / "project_tests.py")]
    else:
        argv_run = ["sh", "-c", command]
    try:
        return run(root, argv_run)
    except heavy_lock.Usage as exc:
        print(f"smoke: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
