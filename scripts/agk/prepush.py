"""The fast checks before a push (brief #326, ADR-0186).

    python3 scripts/agk/prepush.py [--body FILE] [--base REF] [--quick] [--no-lock] [--record FILE]

Runs, in order, the checks CI would fail a pull request on first, and stops at the first failure
with that step's own output:

1. `pr-body`: `check_pr_body.py --draft false FILE`, when `--body FILE` is given;
2. `lint`: `make lint`, when the project's Makefile has a `lint` target;
3. `governance`: `make -f agk.mk agk-governance` with `AGK_BASE` set to the base (the governance
   checks that need no network);
4. `secret-scan`: gitleaks over the branch's commits (merge base to `HEAD`), when installed;
5. `tests`: each run of `test_plan.py` (the plan proof runs), its command in its folder; `--quick`
   skips this step. With a `[testing]` table (brief #417, ADR-0227) it then runs the regression
   set of `impact.py`: `project_tests` once when the set is full (or when no `[proof]` table can
   take the selected files), otherwise each selected file through the command of the `[proof]`
   area it lies in, with `{files}` filled in as proof fills it; a selected file in no area is
   listed as `not run (in no [proof] area)`. Each run prints
   `prepush: tests <area or full> ok|FAIL (<s>s): <reason>`. The whole step holds the heavy-step
   lock (`lock.py`, name `heavy`), with lock.py's wait lines; `--no-lock` leaves it out (for CI),
   and a run whose caller already holds it (`lock.py run --name heavy -- prepush.py`, session
   rule 31) does not take it again. With `lock_slots` (brief #426, ADR-0231) it takes any free
   slot, finds its caller in any slot, and releases the slot it took. Without the table the step
   runs as before, with no lock.

One line per step, `prepush: <step> ok|FAIL|skipped (<s>s)`. Exit 0 when no step failed, 1 when
one did, 2 usage, an unreadable body file or a base that does not resolve. It installs nothing,
downloads nothing and changes no file other than the record.

`--record FILE` (brief #374, ADR-0208) also writes one JSON record of the run, `schema: 1`: the
head and base shas, `started` (UTC), `tree_clean` (a dirty tree is recorded, never hidden), each
step that ran with its `name`, `outcome`, `argv`, `cwd`, `exit`, `seconds`, `output_sha256` and
`output_bytes` (the tests step adds each run it made), and the `versions` of python3, git, make
and gitleaks where found. It holds no output text, no environment value and no path outside the
repository (one outside is written `<outside>/<name>`, the interpreter `python3`). A failed step
still writes it. Then it prints one line for the pull request body:
`Evidence: prepush schema 1, head <sha12>, <n> steps ok, record <sha12 of the file>`. A record
file that cannot be written exits 2.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import lock as heavy_lock
from common import (
    CheckError,
    git,
    load_config,
    merge_base,
    proof_areas,
    proof_timeout,
    resolve_base,
)
from impact import Impact, Selected, impact
from proof import area_command, execute, is_test_file, timeout_note

HERE = Path(__file__).resolve().parent
USAGE = "usage: prepush.py [--body FILE] [--base REF] [--quick] [--no-lock] [--record FILE]"
SCHEMA = 1
LOCK = "heavy"
OWN = "the pull request's own test files (the proof plan)"


class Usage(Exception):
    """A usage error (exit 2)."""


class Step:
    """The outcome of one step: `ok`, `FAIL` or `skipped`, with its note or output.

    `argv`, `cwd`, `exit` and `output` are what the step ran (the record, brief #374); a skipped
    step ran nothing. `runs` lists the runs of the tests step."""

    def __init__(
        self,
        outcome: str,
        text: str = "",
        not_run: bool = False,
        ran: Ran | None = None,
        runs: list[dict] | None = None,
    ) -> None:
        self.outcome = outcome
        self.text = text
        self.not_run = not_run  # skipped although it should have run (a missing tool)
        self.ran = ran
        self.runs = runs


class Ran:
    """One command a step ran: its argument list, folder, exit code and whole output."""

    def __init__(self, argv: list[str], cwd: Path, code: int | None, output: str) -> None:
        self.argv = argv
        self.cwd = cwd
        self.code = code
        self.output = output


def parse_args(args: list[str]) -> dict:
    options: dict = {"body": None, "base": None, "quick": False, "lock": True, "record": None}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--body", "--base", "--record") and i + 1 < len(args):
            options[arg[2:]] = args[i + 1]
            i += 2
        elif arg == "--quick":
            options["quick"] = True
            i += 1
        elif arg == "--no-lock":
            options["lock"] = False
            i += 1
        else:
            raise Usage(USAGE)
    return options


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> tuple[int, str]:
    """Run a fixed argument list, stdout and stderr together, read as UTF-8."""
    proc = subprocess.run(  # nosec B603 - fixed argument list, no shell
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return proc.returncode, (proc.stdout + proc.stderr).rstrip("\n")


def outcome(code: int, out: str, ran: Ran | None = None) -> Step:
    return Step("ok" if code == 0 else "FAIL", out, ran=ran)


def ran_step(cmd: list[str], cwd: Path, env: dict | None = None) -> Step:
    """Run `cmd` and keep what ran for the record."""
    code, out = run(cmd, cwd, env)
    return outcome(code, out, Ran(cmd, cwd, code, out))


def pr_body(root: Path, body: Path | None) -> Step:
    if body is None:
        return Step("skipped", "no body file given (--body FILE)")
    cmd = [sys.executable, str(HERE / "check_pr_body.py"), "--draft", "false", str(body)]
    return ran_step(cmd, root)


def has_lint(root: Path) -> bool:
    if not any((root / n).is_file() for n in ("Makefile", "makefile", "GNUmakefile")):
        return False
    code, _ = run(["make", "-n", "lint"], root)
    return code == 0


def lint(root: Path) -> Step:
    if shutil.which("make") is None:
        return Step("skipped", "make is not installed")
    if not has_lint(root):
        return Step("skipped", "no lint target in the Makefile (target: lint)")
    return ran_step(["make", "lint"], root)


def governance(root: Path, base: str) -> Step:
    if not (root / "agk.mk").is_file():
        return Step("FAIL", "agk.mk is missing; governance cannot run (path class: agk.mk)")
    if shutil.which("make") is None:
        return Step("skipped", "governance: not run (make is not installed)", not_run=True)
    env = {**os.environ, "AGK_BASE": base}
    return ran_step(["make", "-f", "agk.mk", "agk-governance"], root, env)


def secret_scan(root: Path, mb: str) -> Step:
    tool = shutil.which("gitleaks")
    if tool is None:
        return Step("skipped", "gitleaks is not installed; secret scan: not run", not_run=True)
    head = git(root, "rev-parse", "HEAD").strip()
    cmd = [tool, "git", "--no-banner", "--redact", "--exit-code", "1", f"--log-opts={mb}..{head}"]
    return ran_step([*cmd, "."], root)


def tests(root: Path, mb: str, quick: bool, use_lock: bool = True) -> Step:
    if quick:
        return Step("skipped", "--quick")
    plan = HERE / "test_plan.py"
    if not plan.is_file():
        return Step("skipped", "test_plan.py is not installed; no tests run")
    cmd = [sys.executable, str(plan), "--json", "--base", mb, "--head", "HEAD"]
    code, out = run(cmd, root)
    ran = Ran(cmd, root, code, out)
    if code != 0:
        return Step("FAIL", out, ran=ran)
    shown = json.loads(out)
    if not (shown.get("regression") or {}).get("table"):
        return proof_runs(root, shown["runs"], ran)  # no [testing] table: as before (answer 4)
    try:
        limit = proof_timeout(root)
        found = impact(root, mb, "HEAD")
        areas = proof_areas(root)
    except CheckError as exc:
        return Step("FAIL", str(exc), ran=ran)
    try:
        taken = take_lock(root) if use_lock else None
    except heavy_lock.Usage as exc:
        return Step("FAIL", str(exc), ran=ran)
    except OSError:
        return Step("FAIL", f"lock {LOCK}: the lock folder cannot be written (setting: lock_dir)")
    previous = {sig: signal.signal(sig, heavy_lock.on_signal) for sig in stop_signals()}
    try:
        return gate(root, shown["runs"], found, areas, limit, ran)
    except heavy_lock.Stopped as exc:
        raise SystemExit(exc.code) from None
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        if taken is not None:
            heavy_lock.clear_if_same(*taken)


def proof_runs(root: Path, runs: list[dict], ran: Ran) -> Step:
    """The tests step without a `[testing]` table: proof's plan alone, as brief #326 made it."""
    if not runs:
        return Step("ok", "tests: nothing to run (the test plan selects no test file)", ran=ran)
    try:
        limit = proof_timeout(root)
    except CheckError as exc:
        return Step("FAIL", str(exc), ran=ran)
    lines: list[str] = []
    made: list[dict] = []
    for item in runs:
        folder = root / item["cwd"]
        started = time.monotonic()
        run_code, run_out, _ = execute(item["command"], folder, limit)
        made.append(
            {
                "name": item["name"],
                "command": safe_command(item["command"], root),
                "cwd": safe_cwd(folder, root),
                "exit": run_code,
                "seconds": round(time.monotonic() - started, 3),
                **digest(run_out),
            }
        )
        lines.append(f"tests: {item['name']} ({len(item['files'])} test files) in {item['cwd']}")
        if run_code is None:
            return Step("FAIL", "\n".join([*lines, timeout_note(limit)]), ran=ran, runs=made)
        if run_code != 0:
            return Step("FAIL", "\n".join([*lines, run_out.rstrip("\n")]), ran=ran, runs=made)
    return Step("ok", "\n".join(lines), ran=ran, runs=made)


def stop_signals() -> list[int]:
    return [s for s in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGHUP", None)) if s]


def caller_slot(held: Path, slots: int) -> Path | None:
    """The slot this run's caller holds, in any of the lock's slots (brief #426, ADR-0231)."""
    for folder in heavy_lock.slot_folders(held, slots):
        if folder.exists() and caller_holds(heavy_lock.read_owner(folder)):
            return folder
    return None


def caller_holds(owner: dict | None) -> bool:
    """The lock is this run's own: `lock.py run --name heavy -- prepush.py` took it, and this
    process is its command (session rule 31), so taking it again would wait for itself."""
    if not owner or owner.get("host") != socket.gethostname():
        return False
    return owner.get("child") == os.getpid() or owner.get("pid") == os.getppid()


def take_lock(root: Path) -> tuple[Path, str] | None:
    """Take the heavy-step lock with lock.py's own wait lines; None when the caller holds it.
    A refused setting raises `lock.Usage`, a folder that cannot be written OSError."""
    held = heavy_lock.lock_folder(root, LOCK)
    limit = heavy_lock.stale_minutes(root)
    slots = heavy_lock.slots_setting(root)
    if caller_slot(held, slots) is not None:
        print(f"lock {LOCK}: held by this run's caller (lock.py run); not taken again", flush=True)
        return None
    token = uuid.uuid4().hex
    owner = {
        "session": os.environ.get("AGK_SESSION") or "",
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token": token,
    }
    # No timeout: it waits its turn. The slot taken is the one released (brief #426, ADR-0231).
    taken = heavy_lock.take(held, LOCK, owner, limit, None, slots=slots)
    return (taken or held), token


def rule(item: Selected) -> str:
    return f"{item.changed} matches code {item.code}, tests {', '.join(item.tests)}"


def reasons(items: list[Selected]) -> str:
    return "; ".join(dict.fromkeys(rule(i) for i in items))


def regression_sets(
    root: Path, found: Impact, areas: list[dict] | None
) -> tuple[list[tuple[str, str, str, str]], list[str]]:
    """The regression runs (name, command, folder, reason) and the lines of what is not run."""
    notes = [f"tests: unmapped (no [testing] map entry covers it): {p}" for p in found.unmapped]
    project = str(load_config(root)["project_tests"] or "").strip()
    if found.full or (found.selected and areas is None):
        reason = found.reason or (
            f"{reasons(found.selected)}; no [proof] table runs single files, "
            "so project_tests runs once"
        )
        if not project:
            notes.append(f"tests: full not run: project_tests is not set ({reason})")
            return [], notes
        return [("full", project, ".", reason)], notes
    if not found.selected:
        extra = " (only documentation changed)" if found.docs_only else ""
        return [], [f"tests: regression: nothing selected{extra}", *notes]
    sets = []
    placed: set[str] = set()
    for area in areas or []:
        mine = [s for s in found.selected if is_test_file(s.test, area["dirs"], area["patterns"])]
        if mine:
            command = area_command(area, [s.test for s in mine])
            sets.append((area["name"], command, area["cwd"], reasons(mine)))
            placed.update(s.test for s in mine)
    notes.extend(
        f"tests: not run (in no [proof] area): {s.test}"
        for s in found.selected
        if s.test not in placed
    )
    return sets, notes


def gate(
    root: Path,
    runs: list[dict],
    found: Impact,
    areas: list[dict] | None,
    limit: int,
    ran: Ran,
) -> Step:
    """Proof's runs, then the regression set (brief #417 answers 1 and 2), each run with its line
    printed when it ends; what is not run is printed before the regression runs."""
    made: list[dict] = []
    sets, notes = regression_sets(root, found, areas)
    planned = [(r["name"], r["command"], r["cwd"], OWN, "proof") for r in runs]
    planned.extend((*item, "regression") for item in sets)
    shown = False
    for name, command, cwd, reason, kind in planned:
        if kind == "regression" and not shown:
            say(notes)
            shown = True
        folder = root / cwd
        started = time.monotonic()
        code, out, _ = execute(command, folder, limit)
        seconds = time.monotonic() - started
        made.append(
            {
                "name": name,
                "set": kind,
                "reason": reason,
                "command": safe_command(command, root),
                "cwd": safe_cwd(folder, root),
                "exit": code,
                "seconds": round(seconds, 3),
                **digest(out),
            }
        )
        word = "ok" if code == 0 else "FAIL"
        print(f"prepush: tests {name} {word} ({seconds:.1f}s): {reason}", flush=True)
        if code is None:
            return Step("FAIL", timeout_note(limit), ran=ran, runs=made)
        if code != 0:
            return Step("FAIL", out.rstrip("\n"), ran=ran, runs=made)
    if not shown:
        say(notes)
    not_run = any("not run" in n for n in notes)
    return Step("ok", "", not_run=not_run, ran=ran, runs=made)


def say(lines: list[str]) -> None:
    for line in lines:
        print(line, flush=True)


def digest(output: str) -> dict:
    data = output.encode("utf-8", errors="replace")
    return {"output_sha256": hashlib.sha256(data).hexdigest(), "output_bytes": len(data)}


def safe_arg(arg: str, root: Path) -> str:
    """An argument as the record holds it: no path outside the repository (brief #374 answer 1)."""
    if arg == sys.executable:
        return "python3"
    if not os.path.isabs(arg):
        return arg
    path = Path(arg)
    try:
        return path.resolve().relative_to(root.resolve()).as_posix() or "."
    except ValueError:
        pass
    if path.resolve() == (HERE / path.name).resolve():
        return f"scripts/agk/{path.name}"
    return f"<outside>/{path.name}"


# An absolute path inside a shell command: a `/` that starts a word (or follows `=`), up to a
# character that ends a shell word.
ABSOLUTE = re.compile(r"(?<![^\s='\"(])/[^\s;|&()<>'\"`$]+")


def safe_command(command: str, root: Path) -> str:
    """A run's shell command as the record holds it: each absolute path scrubbed by `safe_arg`
    (verdict on 1511951, item 2)."""
    return ABSOLUTE.sub(lambda m: safe_arg(m.group(0), root), command)


def safe_cwd(cwd: Path, root: Path) -> str:
    try:
        return cwd.resolve().relative_to(root.resolve()).as_posix() or "."
    except ValueError:
        return "<outside>"


def version(cmd: list[str], root: Path) -> str | None:
    """The first line a tool prints for its version, `unknown` when it prints none, or None when
    it is not installed."""
    if shutil.which(cmd[0]) is None:
        return None
    try:
        code, out = run(cmd, root)
    except OSError:
        return None
    line = out.splitlines()[0].strip() if out else ""
    return line if code == 0 and line else "unknown"


def versions(root: Path) -> dict:
    found = {"python3": ".".join(map(str, sys.version_info[:3]))}
    for name, cmd in (
        ("git", ["git", "--version"]),
        ("make", ["make", "--version"]),
        ("gitleaks", ["gitleaks", "version"]),
    ):
        line = version(cmd, root)
        if line is not None:
            found[name] = line
    return found


def step_record(name: str, result: Step, seconds: float, root: Path) -> dict:
    ran = result.ran
    entry: dict = {
        "name": name,
        "outcome": result.outcome,
        "not_run": result.not_run,
        "argv": [safe_arg(a, root) for a in ran.argv] if ran else [],
        "cwd": safe_cwd(ran.cwd, root) if ran else ".",
        "exit": ran.code if ran else None,
        "seconds": round(seconds, 3),
        **digest(ran.output if ran else ""),
    }
    if result.runs is not None:
        entry["runs"] = result.runs
    return entry


def write_record(path: Path, record: dict) -> str:
    """Write the record; return the sha256 of the file. OSError when it cannot be written."""
    data = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main(argv: list[str] | None = None) -> int:
    try:
        options = parse_args(list(sys.argv[1:] if argv is None else argv))
    except Usage as exc:
        print(exc, file=sys.stderr)
        return 2
    code, top = run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    if code != 0:
        print("prepush: not inside a git work tree (path class: root)")
        return 2
    root = Path(top.strip())
    body = Path(options["body"]) if options["body"] else None
    if body is not None and not body.is_file():
        print("prepush: the body file cannot be read (option: --body)")
        return 2
    try:
        base = resolve_base(root, options["base"])
        if base is None:
            raise CheckError("no base ref resolves")
        mb = merge_base(root, base)
    except CheckError:
        print("prepush: the base does not resolve (setting: --base, AGK_BASE, default_branch)")
        return 2
    record_path = Path(options["record"]) if options["record"] else None
    record: dict | None = None
    if record_path is not None:
        if not record_path.parent.is_dir():
            print("prepush: the record file cannot be written (option: --record)")
            return 2
        record = {
            "schema": SCHEMA,
            "head": git(root, "rev-parse", "HEAD").strip(),
            "base": git(root, "rev-parse", f"{base}^{{commit}}").strip(),
            "started": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "tree_clean": git(root, "status", "--porcelain").strip() == "",
            "versions": versions(root),
            "steps": [],
        }
    steps: list[tuple[str, Callable[[], Step]]] = [
        ("pr-body", lambda: pr_body(root, body)),
        ("lint", lambda: lint(root)),
        ("governance", lambda: governance(root, base)),
        ("secret-scan", lambda: secret_scan(root, mb)),
        ("tests", lambda: tests(root, mb, options["quick"], options["lock"])),
    ]
    not_run: list[str] = []
    for name, step in steps:
        started = time.monotonic()
        result = step()
        seconds = time.monotonic() - started
        if record is not None:
            record["steps"].append(step_record(name, result, seconds, root))
        line = f"prepush: {name} {result.outcome} ({seconds:.1f}s)"
        if result.outcome == "skipped":
            print(f"{line}: {result.text}")
        else:
            print(line)
        if result.not_run:
            not_run.append(name)
        if result.outcome == "FAIL":
            if result.text:
                print(result.text)
            print(f"prepush: stopped at {name}; nothing after it ran")
            return finish(record, record_path, not_run, "failed", 1)
        if result.outcome == "ok" and name == "tests" and result.text:
            print(result.text)
    if not_run:
        print(f"prepush: passed; not run: {', '.join(not_run)}")
    else:
        print("prepush: all steps passed")
    return finish(record, record_path, not_run, "passed", 0)


def finish(
    record: dict | None, path: Path | None, not_run: list[str], result: str, code: int
) -> int:
    """Write the record when one was asked for and print the `Evidence:` line; keep the exit."""
    if record is None or path is None:
        return code
    record["not_run"] = list(not_run)
    record["result"] = result
    try:
        sha = write_record(path, record)
    except OSError:
        print("prepush: the record file cannot be written (option: --record)")
        return 2
    ok = sum(1 for step in record["steps"] if step["outcome"] == "ok")
    head = record["head"][:12]
    print(f"Evidence: prepush schema {SCHEMA}, head {head}, {ok} steps ok, record {sha[:12]}")
    return code


if __name__ == "__main__":
    sys.exit(main())
