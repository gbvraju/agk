"""Red-then-green: can the tests a pull request adds fail? (SPEC-0010 rules 7 to 15).

Standard library only, and no language: the test command, directories and patterns come from
`agk.toml`. It places the pull request's test files on the base commit (a detached git worktree) and
runs `project_tests` there, expecting it to fail, then runs it on the head (a second detached
worktree), expecting it to pass. ROOT's work tree is never changed: the script adds two worktrees in
a temporary directory outside ROOT and removes them at the end, also on a failure.

Exit: 0 proven or skipped, 1 not-proven, 4 unknown, 2 usage or a refused setting, 3 I/O.
"""

from __future__ import annotations

import fnmatch
import json
import os
import shutil
import signal
import subprocess  # nosec B404 - fixed argument lists, and the project's own test command
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from common import (
    CheckError,
    declares_unchanged,
    git,
    load_config,
    proof_timeout,
    resolve_base,
)

USAGE = "usage: proof.py [--base REF] [--head REF] [--body FILE|-] [--json] [ROOT]"
SHOWN = 40
EXIT = {"proven": 0, "skipped": 0, "not-proven": 1, "unknown": 4}


class Usage(Exception):
    """A usage error or a refused setting (exit 2)."""


class Failure(Exception):
    """An error that is not an outcome (exit 3)."""


@dataclass
class Result:
    outcome: str
    reason: str | None
    base: str
    head: str
    test_files: list[str]

    def line(self) -> str:
        suffix = f" ({self.reason})" if self.reason else ""
        return f"proof: {self.outcome}{suffix}"

    def data(self) -> dict:
        return {
            "outcome": self.outcome,
            "reason": self.reason,
            "base": self.base,
            "head": self.head,
            "test_files": self.test_files,
        }


def parse_args(args: list[str]) -> dict:
    options: dict = {"base": None, "head": "HEAD", "body": None, "json": False, "root": "."}
    positional: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--base", "--head", "--body") and i + 1 < len(args):
            options[arg[2:]] = args[i + 1]
            i += 2
        elif arg == "--json":
            options["json"] = True
            i += 1
        elif arg.startswith("--") or len(positional) == 1:
            raise Usage(USAGE)
        else:
            positional.append(arg)
            i += 1
    if positional:
        options["root"] = positional[0]
    return options


def read_body(source: str | None) -> str:
    if source is None:
        return ""
    try:
        return sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Failure("the pull request body cannot be read (path class: body file)") from exc


def commit_of(root: Path, ref: str) -> str:
    sha = git(root, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}", check=False).strip()
    if not sha:
        raise Failure("a given ref does not resolve (path class: git ref)")
    return sha


def resolve_range(root: Path, base: str | None, head: str) -> tuple[str, str]:
    head_sha = commit_of(root, head)
    if base is not None:
        return commit_of(root, base), head_sha
    start = resolve_base(root)
    if start is None:
        raise Failure("no base ref is available (path class: git ref)")
    merged = git(root, "merge-base", start, head_sha, check=False).strip()
    if not merged:
        raise Failure("no merge base with the base ref (path class: git ref)")
    return merged, head_sha


def changes(root: Path, base: str, head: str) -> dict[str, str]:
    """Path -> status letter between base and head; a rename is a deletion and an addition."""
    tokens = git(root, "diff", "-z", "--name-status", "--no-renames", base, head).split("\0")
    return {tokens[i + 1]: tokens[i][:1] for i in range(0, len(tokens) - 1, 2)}


def is_test_file(path: str, dirs: list[str], patterns: list[str]) -> bool:
    name = path.rsplit("/", 1)[-1]
    inside = any(d.strip("/") in ("", ".") or path.startswith(d.strip("/") + "/") for d in dirs)
    return inside and any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    proc.communicate()


def execute(command: str, cwd: Path, timeout: int) -> tuple[int | None, str]:
    """(exit status or None on a timeout, output). The shell runs in its own process group."""
    proc = subprocess.Popen(  # nosec B603 B607 - the project's own test command, run as the caller
        ["sh", "-c", command],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        start_new_session=True,
    )
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_group(proc)
        return None, ""
    return proc.returncode, out


def show(label: str, out: str) -> None:
    lines = out.splitlines()[-SHOWN:]
    print(f"--- {label} (last {len(lines)} lines)", file=sys.stderr)
    for line in lines:
        print(line, file=sys.stderr)


def place_tests(root: Path, work: Path, files: dict[str, str], head: str) -> None:
    """The base code with the pull request's tests: copy added or modified, remove deleted."""
    for path, status in sorted(files.items()):
        target = work / path
        if status == "D":
            target.unlink(missing_ok=True)
            continue
        proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
            ["git", "show", f"{head}:{path}"], cwd=root, capture_output=True
        )
        if proc.returncode != 0:
            raise Failure("a test file cannot be read from the head (path class: test files)")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(proc.stdout)


def two_runs(root: Path, base: str, head: str, files: dict[str, str], command: str, limit: int):
    """(run 1, run 2): exit statuses, None for a timeout, None for run 2 when it was not made."""
    temp = Path(tempfile.mkdtemp(prefix="agk-proof-"))
    trees = [temp / "base", temp / "head"]
    added: list[Path] = []
    try:
        for tree, ref in zip(trees, (base, head), strict=True):
            try:
                git(root, "worktree", "add", "--detach", "-q", str(tree), ref)
            except CheckError as exc:
                raise Failure("a worktree cannot be added (path class: temporary)") from exc
            added.append(tree)
        place_tests(root, trees[0], files, head)
        status1, out1 = execute(command, trees[0], limit)
        show("run 1: the base with the pull request's tests", out1)
        if status1 is None:
            return None, None
        status2, out2 = execute(command, trees[1], limit)
        show("run 2: the head", out2)
        return status1, status2
    finally:
        for tree in added:
            git(root, "worktree", "remove", "--force", str(tree), check=False)
        git(root, "worktree", "prune", check=False)
        shutil.rmtree(temp, ignore_errors=True)
        if any(p.exists() for p in added):
            raise Failure("a temporary worktree could not be removed (path class: temporary)")


def decide(status1: int | None, status2: int | None) -> tuple[str, str | None]:
    """The outcome in the order of rule 12: timeout, proven, green-on-base, red-on-head."""
    if status1 is None or status2 is None:
        return "unknown", "timeout"
    if status1 != 0 and status2 == 0:
        return "proven", None
    if status1 == 0:
        return "not-proven", "green-on-base"
    return "not-proven", "red-on-head"


def prove(root: Path, base: str, head: str, body: str) -> Result:
    cfg = load_config(root)
    command = str(cfg["project_tests"] or "").strip()
    limit = proof_timeout(root)
    files = {
        p: s
        for p, s in changes(root, base, head).items()
        if is_test_file(p, list(cfg["test_dirs"]), list(cfg["test_patterns"]))
    }
    names = sorted(files)

    def result(outcome: str, reason: str | None = None) -> Result:
        return Result(outcome, reason, base, head, names)

    if not command:
        return result("unknown", "no-project-tests")
    if declares_unchanged(body):
        return result("skipped")
    if not files or all(s == "D" for s in files.values()):
        return result("unknown", "no-test-files")
    status1, status2 = two_runs(root, base, head, files, command, limit)
    outcome, reason = decide(status1, status2)
    return result(outcome, reason)


def main(argv: list[str] | None = None) -> int:
    try:
        options = parse_args(list(sys.argv[1:] if argv is None else argv))
        root = Path(options["root"])
        if git(root, "rev-parse", "--is-inside-work-tree", check=False).strip() != "true":
            raise Failure("ROOT is not a git work tree (path class: root)")
        body = read_body(options["body"])
        base, head = resolve_range(root, options["base"], options["head"])
        result = prove(root, base, head, body)
    except Usage as exc:
        print(exc, file=sys.stderr)
        return 2
    except CheckError as exc:
        print(f"FAIL proof: {exc}")
        return 2
    except Failure as exc:
        print(f"FAIL proof: {exc}")
        return 3
    except OSError:
        print("FAIL proof: an input or output error (path class: temporary)")
        return 3
    print(json.dumps(result.data(), sort_keys=True) if options["json"] else result.line())
    return EXIT[result.outcome]


if __name__ == "__main__":
    sys.exit(main())
