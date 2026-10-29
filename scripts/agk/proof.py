"""Red-then-green: can the tests a pull request adds fail? (SPEC-0010 rules 7 to 15).

Standard library only, and no language: the test command, directories and patterns come from
`agk.toml`. It places the pull request's test files on the base commit (a detached git worktree)
and runs `project_tests` there, expecting it to fail, then runs it on the head (a second detached
worktree), expecting it to pass. With a `[proof]` table, each test area's own command runs instead,
with only the pull request's test files of that area (brief #305, ADR-0172). ROOT's work tree is
never changed: the script adds two worktrees in a temporary directory outside ROOT and removes them
at the end, also on a failure.

Exit: 0 proven or skipped, 1 not-proven, 4 unknown, 2 usage or a refused setting, 3 I/O.
"""

from __future__ import annotations

import fnmatch
import json
import os
import posixpath
import shlex
import shutil
import signal
import subprocess  # nosec B404 - fixed argument lists, and the project's own test command
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    CheckError,
    declares_unchanged,
    git,
    load_config,
    proof_areas,
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
    elapsed: int | None = None  # whole seconds of the run that timed out
    areas: list[dict] | None = None  # with a `[proof]` table: each area's files, outcome, seconds

    def line(self) -> str:
        if self.areas is not None and self.outcome in ("not-proven", "unknown"):
            named = [
                f"{a['name']}: {reason_text(a['reason'], a['elapsed'])}"
                for a in self.areas
                if a["outcome"] not in (None, "proven")
            ]
            if named:
                return f"proof: {self.outcome} ({'; '.join(named)})"
        reason = reason_text(self.reason, self.elapsed)
        suffix = f" ({reason})" if reason else ""
        return f"proof: {self.outcome}{suffix}"

    def data(self) -> dict:
        out = {
            "outcome": self.outcome,
            "reason": self.reason,
            "base": self.base,
            "head": self.head,
            "test_files": self.test_files,
        }
        if self.areas is not None:
            out["areas"] = [
                {k: a[k] for k in ("name", "files", "outcome", "reason", "seconds")}
                for a in self.areas
            ]
        return out


def reason_text(reason: str | None, elapsed: int | None) -> str | None:
    if reason == "timeout" and elapsed is not None:
        return f"timeout after {elapsed} s, setting: proof_timeout"
    return reason


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
        return (
            sys.stdin.buffer.read().decode("utf-8")
            if source == "-"
            else Path(source).read_text(encoding="utf-8")
        )
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


WINDOWS = os.name == "nt"
# CREATE_NEW_PROCESS_GROUP of the Windows API (the subprocess module names it only on Windows).
NEW_PROCESS_GROUP = 0x00000200
# Seconds to wait for `taskkill`, and for the killed tree to close its output, before going on.
KILL_WAIT = 30


def popen_options(windows: bool) -> dict:
    """The run starts its own process group, so that a timeout can end the whole tree."""
    if windows:
        return {"creationflags": NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def kill_tree(proc, windows: bool = WINDOWS, run=subprocess.run) -> None:
    """End the run and every process it started, then read what is left of its output, bounded.

    POSIX: SIGKILL to the process group. Windows (no `os.killpg`, no SIGKILL): `taskkill /T /F`,
    which ends the process and its descendants; if taskkill fails or is missing, the shell itself.
    """
    if windows:
        try:
            ended = (
                run(  # nosec B603 B607 - fixed argument list, no shell
                    ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                    capture_output=True,
                    check=False,
                    timeout=KILL_WAIT,
                ).returncode
                == 0
            )
        except (OSError, subprocess.SubprocessError):
            ended = False
        if not ended:
            try:
                proc.kill()
            except OSError:
                pass
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    try:
        proc.communicate(timeout=KILL_WAIT)
    except subprocess.TimeoutExpired:
        pass  # a process outside the tree holds the output open; proof does not wait for it


def timeout_note(seconds: int) -> str:
    return (
        f"proof: the test run was ended after {seconds} s, the limit set by `proof_timeout` in "
        "agk.toml; the tests did not fail, they did not finish"
    )


def execute(
    command: str,
    cwd: Path,
    timeout: int,
    windows: bool = WINDOWS,
    popen=subprocess.Popen,
    run=subprocess.run,
) -> tuple[int | None, str, int]:
    """(exit status or None on a timeout, output, whole seconds taken). Its own process group."""
    began = time.monotonic()
    proc = popen(  # nosec B603 B607 - the project's own test command, run as the caller
        ["sh", "-c", command],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        **popen_options(windows),
    )
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(proc, windows, run)
        return None, "", round(time.monotonic() - began)
    return proc.returncode, out, round(time.monotonic() - began)


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


class Trees:
    """Two detached worktrees in a temporary directory outside ROOT: the base with the pull
    request's tests placed, and the head. Removed at the end, also on a failure."""

    def __init__(self, root: Path, base: str, head: str, files: dict[str, str]) -> None:
        self.root, self.base, self.head, self.files = root, base, head, files
        self.temp = Path(tempfile.mkdtemp(prefix="agk-proof-"))
        self.trees = [self.temp / "base", self.temp / "head"]
        self.added: list[Path] = []

    def __enter__(self) -> list[Path]:
        try:
            for tree, ref in zip(self.trees, (self.base, self.head), strict=True):
                try:
                    git(self.root, "worktree", "add", "--detach", "-q", str(tree), ref)
                except CheckError as exc:
                    raise Failure("a worktree cannot be added (path class: temporary)") from exc
                self.added.append(tree)
            place_tests(self.root, self.trees[0], self.files, self.head)
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self.trees

    def __exit__(self, *exc) -> None:
        for tree in self.added:
            git(self.root, "worktree", "remove", "--force", str(tree), check=False)
        git(self.root, "worktree", "prune", check=False)
        shutil.rmtree(self.temp, ignore_errors=True)
        if any(p.exists() for p in self.added):
            raise Failure("a temporary worktree could not be removed (path class: temporary)")


def run_pair(trees: list[Path], command: str, limit: int, label: str = ""):
    """(run 1, run 2, seconds of the timed-out run or None, seconds of both runs)."""
    status1, out1, seconds1 = execute(command, trees[0], limit)
    show(f"run 1{label}: the base with the pull request's tests", out1)
    if status1 is None:
        print(timeout_note(seconds1), file=sys.stderr)
        return None, None, seconds1, seconds1
    status2, out2, seconds2 = execute(command, trees[1], limit)
    show(f"run 2{label}: the head", out2)
    if status2 is None:
        print(timeout_note(seconds2), file=sys.stderr)
        return status1, None, seconds2, seconds1 + seconds2
    return status1, status2, None, seconds1 + seconds2


def two_runs(root: Path, base: str, head: str, files: dict[str, str], command: str, limit: int):
    """(run 1, run 2, seconds): exit statuses, None for a timeout, None for run 2 when it was not
    made; seconds is the time of the run that timed out, else None."""
    with Trees(root, base, head, files) as trees:
        status1, status2, seconds, _ = run_pair(trees, command, limit)
    return status1, status2, seconds


def area_files(area: dict, files: dict[str, str]) -> dict[str, str]:
    return {p: s for p, s in files.items() if is_test_file(p, area["dirs"], area["patterns"])}


def area_command(area: dict, paths: list[str]) -> str:
    """The template with `{files}`: each path relative to the area's cwd, shell-quoted."""
    quoted = " ".join(shlex.quote(posixpath.relpath(p, area["cwd"])) for p in paths)
    return area["command"].replace("{files}", quoted)


# The reason of a whole result, in the order of SPEC-0010 rule 12.
REASON_ORDER = ("timeout", "green-on-base", "red-on-head")


def run_areas(root: Path, base: str, head: str, areas: list[dict], files: dict[str, str], limit):
    """Each area with added or changed tests runs its command, with only those files, on the base
    (all the areas' tests placed) and on the head."""
    placed = {p: files[p] for a in areas for p in a["files"]}
    with Trees(root, base, head, placed) as trees:
        for area in areas:
            paths = [p for p in area["files"] if files[p] != "D"]
            if not paths:
                continue
            status1, status2, elapsed, seconds = run_pair(
                trees, area_command(area, paths), limit, f" ({area['name']})"
            )
            area["outcome"], area["reason"] = decide(status1, status2)
            area["seconds"], area["elapsed"] = seconds, elapsed


def combine(areas: list[dict]) -> tuple[str, str | None, int | None]:
    """Proven only when every area that ran is proven; else unknown before not-proven."""
    ran = [a for a in areas if a["outcome"] is not None]
    for reason in REASON_ORDER:
        hit = next((a for a in ran if a["reason"] == reason), None)
        if hit is not None:
            outcome = "unknown" if reason == "timeout" else "not-proven"
            return outcome, reason, hit["elapsed"]
    return "proven", None, None


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
    areas = proof_areas(root)
    if areas is not None:
        return prove_areas(root, base, head, body, areas)
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
    status1, status2, seconds = two_runs(root, base, head, files, command, limit)
    outcome, reason = decide(status1, status2)
    return Result(outcome, reason, base, head, names, seconds)


def prove_areas(root: Path, base: str, head: str, body: str, areas: list[dict]) -> Result:
    """With a `[proof]` table: each area's own command with only the pull request's files."""
    limit = proof_timeout(root)
    changed = changes(root, base, head)
    for area in areas:
        mine = area_files(area, changed)
        area.update(files=sorted(mine), outcome=None, reason=None, seconds=0, elapsed=None)
    names = sorted({p for a in areas for p in a["files"]})

    def result(outcome: str, reason: str | None = None, elapsed: int | None = None) -> Result:
        return Result(outcome, reason, base, head, names, elapsed, areas)

    if declares_unchanged(body):
        return result("skipped")
    if not any(changed[p] != "D" for a in areas for p in a["files"]):
        return result("unknown", "no-test-files")
    run_areas(root, base, head, areas, changed, limit)
    return result(*combine(areas))


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
