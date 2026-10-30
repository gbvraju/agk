"""The fast checks before a push (brief #326, ADR-0186).

    python3 scripts/agk/prepush.py [--body FILE] [--base REF] [--quick]

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
downloads nothing and changes no file.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # nosec B404 - fixed argument lists; a configured command runs as the person's own
import sys
import time
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, git, merge_base, resolve_base

HERE = Path(__file__).resolve().parent
USAGE = "usage: prepush.py [--body FILE] [--base REF] [--quick]"


class Usage(Exception):
    """A usage error (exit 2)."""


class Step:
    """The outcome of one step: `ok`, `FAIL` or `skipped`, with its note or output."""

    def __init__(self, outcome: str, text: str = "", not_run: bool = False) -> None:
        self.outcome = outcome
        self.text = text
        self.not_run = not_run  # skipped although it should have run (a missing tool)


def parse_args(args: list[str]) -> dict:
    options: dict = {"body": None, "base": None, "quick": False}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--body", "--base") and i + 1 < len(args):
            options[arg[2:]] = args[i + 1]
            i += 2
        elif arg == "--quick":
            options["quick"] = True
            i += 1
        else:
            raise Usage(USAGE)
    return options


def run(cmd: list[str] | str, cwd: Path, env: dict | None = None) -> tuple[int, str]:
    """Run a command, stdout and stderr together; a list runs without a shell."""
    proc = subprocess.run(  # nosec B602 B603 - the kit's fixed lists, or the project's own command
        cmd,
        cwd=cwd,
        shell=isinstance(cmd, str),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, (proc.stdout + proc.stderr).rstrip("\n")


def outcome(code: int, out: str) -> Step:
    return Step("ok" if code == 0 else "FAIL", out)


def pr_body(root: Path, body: Path | None) -> Step:
    if body is None:
        return Step("skipped", "no body file given (--body FILE)")
    cmd = [sys.executable, str(HERE / "check_pr_body.py"), "--draft", "false", str(body)]
    return outcome(*run(cmd, root))


def has_lint(root: Path) -> bool:
    if shutil.which("make") is None:
        return False
    if not any((root / n).is_file() for n in ("Makefile", "makefile", "GNUmakefile")):
        return False
    code, _ = run(["make", "-n", "lint"], root)
    return code == 0


def lint(root: Path) -> Step:
    if not has_lint(root):
        return Step("skipped", "no lint target in the Makefile (target: lint)")
    return outcome(*run(["make", "lint"], root))


def governance(root: Path, base: str) -> Step:
    if not (root / "agk.mk").is_file():
        return Step("FAIL", "agk.mk is missing; the governance checks cannot run (path class: agk.mk)")
    if shutil.which("make") is None:
        return Step("FAIL", "make is not installed, so the governance checks cannot run")
    env = {**os.environ, "AGK_BASE": base}
    return outcome(*run(["make", "-f", "agk.mk", "agk-governance"], root, env))


def secret_scan(root: Path, mb: str) -> Step:
    tool = shutil.which("gitleaks")
    if tool is None:
        return Step("skipped", "gitleaks is not installed; secret scan: not run", not_run=True)
    head = git(root, "rev-parse", "HEAD").strip()
    cmd = [tool, "git", "--no-banner", "--redact", "--exit-code", "1", f"--log-opts={mb}..{head}"]
    return outcome(*run([*cmd, "."], root))


def tests(root: Path, mb: str, quick: bool) -> Step:
    if quick:
        return Step("skipped", "--quick")
    plan = HERE / "test_plan.py"
    if not plan.is_file():
        return Step("skipped", "test_plan.py is not installed; no tests run")
    code, out = run([sys.executable, str(plan), "--json", "--base", mb, "--head", "HEAD"], root)
    if code != 0:
        return Step("FAIL", out)
    runs = json.loads(out)["runs"]
    if not runs:
        return Step("ok", "tests: nothing to run (the test plan selects no test file)")
    lines: list[str] = []
    for item in runs:
        code, out = run(item["command"], root / item["cwd"])
        lines.append(f"tests: {item['name']} ({len(item['files'])} test files) in {item['cwd']}")
        if code != 0:
            return Step("FAIL", "\n".join([*lines, out]))
    return Step("ok", "\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    try:
        options = parse_args(list(sys.argv[1:] if argv is None else argv))
    except Usage as exc:
        print(exc, file=sys.stderr)
        return 2
    top = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if top.returncode != 0:
        print("prepush: not inside a git work tree (path class: root)")
        return 2
    root = Path(top.stdout.strip())
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
        print("prepush: the base does not resolve (option: --base; setting: AGK_BASE, default_branch)")
        return 2
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
            return 1
        if result.outcome == "ok" and name == "tests" and result.text:
            print(result.text)
    if not_run:
        print(f"prepush: passed; not run: {', '.join(not_run)}")
    else:
        print("prepush: all steps passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
