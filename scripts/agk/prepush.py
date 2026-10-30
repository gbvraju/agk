"""The fast checks before a push (brief #326, ADR-0186).

    python3 scripts/agk/prepush.py [--body FILE] [--base REF] [--quick] [--record FILE]

Runs, in order, the checks CI would fail a pull request on first, and stops at the first failure
with that step's own output:

1. `pr-body`: `check_pr_body.py --draft false FILE`, when `--body FILE` is given;
2. `lint`: `make lint`, when the project's Makefile has a `lint` target;
3. `governance`: `make -f agk.mk agk-governance` with `AGK_BASE` set to the base (the governance
   checks that need no network);
4. `secret-scan`: gitleaks over the branch's commits (merge base to `HEAD`), when installed;
5. `tests`: each run of `test_plan.py` (the plan proof runs), its command in its folder; `--quick`
   skips this step.

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
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, git, merge_base, proof_timeout, resolve_base
from proof import execute, timeout_note

HERE = Path(__file__).resolve().parent
USAGE = "usage: prepush.py [--body FILE] [--base REF] [--quick] [--record FILE]"
SCHEMA = 1


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
    options: dict = {"body": None, "base": None, "quick": False, "record": None}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--body", "--base", "--record") and i + 1 < len(args):
            options[arg[2:]] = args[i + 1]
            i += 2
        elif arg == "--quick":
            options["quick"] = True
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


def tests(root: Path, mb: str, quick: bool) -> Step:
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
    runs = json.loads(out)["runs"]
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
        code, run_out, _ = execute(item["command"], folder, limit)
        made.append(
            {
                "name": item["name"],
                "command": safe_command(item["command"], root),
                "cwd": safe_cwd(folder, root),
                "exit": code,
                "seconds": round(time.monotonic() - started, 3),
                **digest(run_out),
            }
        )
        lines.append(f"tests: {item['name']} ({len(item['files'])} test files) in {item['cwd']}")
        if code is None:
            return Step("FAIL", "\n".join([*lines, timeout_note(limit)]), ran=ran, runs=made)
        if code != 0:
            return Step("FAIL", "\n".join([*lines, run_out.rstrip("\n")]), ran=ran, runs=made)
    return Step("ok", "\n".join(lines), ran=ran, runs=made)


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
        ("tests", lambda: tests(root, mb, options["quick"])),
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
