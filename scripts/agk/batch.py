"""The heavy checks run once for a batch of ready pull requests (brief #436, ADR-0235).

    python3 scripts/agk/batch.py PR [PR...] [--command CMD] [--base REF] [--json] [--record FILE]

Fetches each pull request's head with git alone (`git fetch origin refs/pull/<n>/head`), makes a
detached worktree of the base in a new temporary folder, and merges the heads into it in the given
order. A head that does not merge cleanly is left out as `conflict`, one that cannot be fetched as
`not-fetched`, and the rest go on. The base is the one every kit check uses (`--base`, `AGK_BASE`,
then `origin/<default_branch>`).

CMD (default `make -f agk.mk agk-project-test`) is split as a shell splits it and runs without a
shell in the worktree's root, once, under the heavy-step lock (`lock.py`, name `heavy`). When it
passes, each included pull request is `batch-green <sha12>` (its own head). When it fails, CMD runs
on each included head merged alone onto the base, and each is `green` or `red`, with a red run's
output printed; a batch of one is its own run and is not run again. One line per run,
`batch: run <name> ok|FAIL (<s>s)`, then one line per pull request in the given order,
`#<n> <status> <sha12|->`. `--json` prints one object instead (the lock's lines go to stderr).

It only reports: it labels, merges and posts nothing, changes no branch, ref or file of the
checkout, and removes its worktree when it ends, also after a failure. `--record FILE` writes a
record in the schema of brief #374 (`schema: 1`, `kind: "batch"`, one step per run, the pull
requests and their status; no output text, no environment value, no path outside the repository)
and prints `Evidence: batch schema 1, head <sha12>, <n> steps ok, record <sha12 of the file>`.

Exit 0 when every pull request is green, 1 when one is red, `conflict` or `not-fetched`, 2 for a
usage error or a base that does not resolve, 3 when the lock folder cannot be written.
"""

from __future__ import annotations

import contextlib
import json
import shlex
import shutil
import signal
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import lock as heavy_lock
from common import CheckError, git, resolve_base
from prepush import digest, safe_arg, stop_signals, take_lock, versions, write_record

USAGE = "usage: batch.py PR [PR...] [--command CMD] [--base REF] [--json] [--record FILE]"
DEFAULT = "make -f agk.mk agk-project-test"
SCHEMA = 1
REMOTE = "origin"
IDENTITY = ["-c", "user.name=agk-batch", "-c", "user.email=agk-batch@localhost.invalid"]
QUIET = ["-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]
GREEN = ("batch-green", "green")


class Usage(Exception):
    """A usage error (exit 2)."""


def parse_args(args: list[str]) -> dict:
    options: dict = {"pulls": [], "command": DEFAULT, "base": None, "json": False, "record": None}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--command", "--base", "--record"):
            if i + 1 >= len(args) or not args[i + 1].strip():
                raise Usage(USAGE)
            options[arg[2:]] = args[i + 1]
            i += 2
        elif arg == "--json":
            options["json"] = True
            i += 1
        elif arg.isdigit() and int(arg) > 0 and int(arg) not in options["pulls"]:
            options["pulls"].append(int(arg))
            i += 1
        else:
            raise Usage(USAGE)
    if not options["pulls"]:
        raise Usage(USAGE)
    try:
        options["argv"] = shlex.split(options["command"])
    except ValueError:
        raise Usage(USAGE) from None
    if not options["argv"]:
        raise Usage(USAGE)
    return options


def quiet_git(cwd: Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *QUIET, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout + proc.stderr


def fetch(root: Path, number: int) -> str | None:
    """The sha of the pull request's head, fetched from the remote; None when it cannot be."""
    code, _ = quiet_git(root, "fetch", "--no-tags", "--quiet", REMOTE, f"refs/pull/{number}/head")
    if code != 0:
        return None
    code, out = quiet_git(root, "rev-parse", "--verify", "FETCH_HEAD^{commit}")
    return out.strip() if code == 0 else None


def merge(tree: Path, sha: str, number: int) -> bool:
    """Merge one head into the worktree; abort and say False when it does not merge cleanly."""
    code, _ = quiet_git(
        tree, *IDENTITY, "merge", "--no-ff", "--no-edit", "-q", "-m", f"batch: #{number}", sha
    )
    if code != 0:
        quiet_git(tree, "merge", "--abort")
        quiet_git(tree, "reset", "-q", "--hard")
        return False
    return True


def reset(tree: Path, base: str) -> None:
    quiet_git(tree, "checkout", "-q", "--detach", "-f", base)
    quiet_git(tree, "reset", "-q", "--hard", base)
    quiet_git(tree, "clean", "-q", "-ffdx")


def execute(argv: list[str], tree: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(  # nosec B603 - the person's own argument list, no shell
            argv,
            cwd=tree,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
        )
    except OSError:
        return 127, "batch: the command cannot be started (it is not found or not runnable)\n"
    return proc.returncode, proc.stdout + proc.stderr


class Runner:
    """Runs CMD in the worktree and keeps one record step per run."""

    def __init__(self, argv: list[str], tree: Path, root: Path, say) -> None:
        self.argv = argv
        self.tree = tree
        self.root = root
        self.say = say
        self.steps: list[dict] = []

    def run(self, name: str) -> tuple[bool, str]:
        started = time.monotonic()
        code, out = execute(self.argv, self.tree)
        seconds = time.monotonic() - started
        outcome = "ok" if code == 0 else "FAIL"
        self.say(f"batch: run {name} {outcome} ({seconds:.1f}s)")
        self.steps.append(
            {
                "name": name,
                "outcome": outcome,
                "not_run": False,
                "argv": [scrub(a, self.tree, self.root) for a in self.argv],
                "cwd": ".",
                "exit": code,
                "seconds": round(seconds, 3),
                **digest(out.rstrip("\n")),
            }
        )
        return code == 0, out


def scrub(arg: str, tree: Path, root: Path) -> str:
    """An argument as the record holds it: a path inside the worktree is relative to it, any other
    path as `prepush.py` writes it."""
    try:
        if Path(arg).is_absolute():
            return Path(arg).resolve().relative_to(tree.resolve()).as_posix() or "."
    except ValueError:
        pass
    return safe_arg(arg, root)


def check_heads(
    pulls: list[int], heads: dict[int, str | None], status: dict[int, str], base: str, runner
) -> str | None:
    """Merge the heads in order and run CMD once, then per pull request on failure. Returns the
    batch merge commit (None when nothing was merged)."""
    tree = runner.tree
    included: list[int] = []
    for number in pulls:
        sha = heads[number]
        if sha is None:
            status[number] = "not-fetched"
        elif merge(tree, sha, number):
            included.append(number)
        else:
            status[number] = "conflict"
            runner.say(f"batch: #{number} does not merge cleanly; left out")
    if not included:
        runner.say("batch: no pull request merged; nothing to run")
        return None
    merged = git(tree, "rev-parse", "HEAD").strip()
    ok, out = runner.run("batch")
    if ok:
        for number in included:
            status[number] = "batch-green"
        return merged
    if len(included) == 1:
        status[included[0]] = "red"
        runner.say(out.rstrip("\n"))
        return merged
    for number in included:
        reset(tree, base)
        if not merge(tree, heads[number] or "", number):
            status[number] = "conflict"
            runner.say(f"batch: #{number} does not merge cleanly alone; left out")
            continue
        ok, out = runner.run(f"pr-{number}")
        status[number] = "green" if ok else "red"
        if not ok:
            runner.say(out.rstrip("\n"))
    return merged


def main(argv: list[str] | None = None) -> int:
    try:
        options = parse_args(list(sys.argv[1:] if argv is None else argv))
    except Usage as exc:
        print(exc, file=sys.stderr)
        return 2
    code, top = quiet_git(Path.cwd(), "rev-parse", "--show-toplevel")
    if code != 0:
        print("batch: not inside a git work tree (path class: root)")
        return 2
    root = Path(top.strip())
    try:
        base = resolve_base(root, options["base"])
        if base is None:
            raise CheckError("no base ref resolves")
    except CheckError:
        print("batch: the base does not resolve (setting: --base, AGK_BASE, default_branch)")
        return 2
    record_path = Path(options["record"]) if options["record"] else None
    if record_path is not None and not record_path.parent.is_dir():
        print("batch: the record file cannot be written (option: --record)")
        return 2
    as_json = options["json"]
    out = sys.stderr if as_json else sys.stdout

    def say(line: str) -> None:
        if line:
            print(line, file=out, flush=True)

    started = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    tree_clean = git(root, "status", "--porcelain").strip() == ""
    pulls: list[int] = options["pulls"]
    heads = {number: fetch(root, number) for number in pulls}
    status: dict[int, str] = {}
    say(f"batch: base {base[:12]}")
    folder = Path(tempfile.mkdtemp(prefix="agk-batch-"))
    tree = folder / "tree"
    runner = Runner(options["argv"], tree, root, say)
    merged: str | None = None
    taken = None
    previous = {sig: signal.signal(sig, heavy_lock.on_signal) for sig in stop_signals()}
    try:
        code, _ = quiet_git(root, "worktree", "add", "-q", "--detach", str(tree), base)
        if code != 0:
            print("batch: the scratch worktree cannot be made (path class: temporary folder)")
            return 2
        try:
            with contextlib.redirect_stdout(out):
                taken = take_lock(root)
        except heavy_lock.Usage as exc:
            print(exc)
            return 2
        except OSError:
            print("lock heavy: the lock folder cannot be written (setting: lock_dir)")
            return 3
        merged = check_heads(pulls, heads, status, base, runner)
    except heavy_lock.Stopped as exc:
        return exc.code
    finally:
        if taken is not None:
            heavy_lock.clear_if_same(*taken)
        quiet_git(root, "worktree", "remove", "--force", str(tree))
        shutil.rmtree(folder, ignore_errors=True)
        quiet_git(root, "worktree", "prune")
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    rows = [
        {"number": n, "head": heads[n], "status": status.get(n, "not-fetched")} for n in pulls
    ]
    all_green = all(row["status"] in GREEN for row in rows)
    batch_step = next((s for s in runner.steps if s["name"] == "batch"), None)
    if as_json:
        shown = {
            "base": base,
            "batch": {"head": merged, "outcome": batch_step["outcome"] if batch_step else None},
            "pulls": rows,
        }
        print(json.dumps(shown, indent=2, sort_keys=True))
    else:
        for row in rows:
            print(f"#{row['number']} {row['status']} {(row['head'] or '-')[:12]}")
    result = 0 if all_green else 1
    if record_path is None:
        return result
    record = {
        "schema": SCHEMA,
        "kind": "batch",
        "head": merged,
        "base": base,
        "started": started,
        "tree_clean": tree_clean,
        "versions": versions(root),
        "steps": runner.steps,
        "pulls": rows,
        "not_run": [],
        "result": "passed" if all_green else "failed",
    }
    try:
        sha = write_record(record_path, record)
    except OSError:
        print("batch: the record file cannot be written (option: --record)")
        return 2
    ok = sum(1 for step in runner.steps if step["outcome"] == "ok")
    head = (merged or base)[:12]
    print(
        f"Evidence: batch schema {SCHEMA}, head {head}, {ok} steps ok, record {sha[:12]}",
        file=out,
    )
    return result


if __name__ == "__main__":
    sys.exit(main())
