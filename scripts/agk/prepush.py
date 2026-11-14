"""The fast checks before a push (brief #326, ADR-0186).

    python3 scripts/agk/prepush.py [--body FILE] [--base REF] [--quick] [--no-lock]
        [--record [FILE]] [--queue]

Runs, in order, the checks CI would fail a pull request on first, and stops at the first failure
with that step's own output:

1. `pr-body`: `check_pr_body.py --draft false FILE`, when `--body FILE` is given;
2. `lint`: `make lint`, when the project's Makefile has a `lint` target;
3. `governance`: `make -f agk.mk agk-governance` with `AGK_BASE` set to the base (the governance
   checks that need no network), and `AGK_PR_BODY` set to the body file when `--body` is given, so
   that `check_protected_changes.py` reads its `Covered-by:` line (brief #545, ADR-0271); with
   that line and a SPEC-0021 rule 3a record on the base, the Final comment of each record, one
   `gh api` GET each (the workflow's `Record comments` step), in a temporary file outside the
   checkout that `AGK_RECORD_COMMENTS` names and that is removed afterwards; a comment that
   cannot be read fails the step, naming the option (brief #601, ADR-0293);
4. `secret-scan`: gitleaks over the branch's commits (merge base to `HEAD`); a missing gitleaks
   fails the step, naming the tool and the version the governance workflow pins (`GITLEAKS_PIN`),
   and is never `not run`, in any mode and also with `--quick` (brief #632, ADR-0306);
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
   runs as before, with no lock. Brief #505 (ADR-0254): the caller's slot is also the one whose
   token is `AGK_LOCK_TOKEN` under the name `AGK_LOCK_NAME` on this host, which `lock.py run`
   passes down through any wrapper; a slot held in another process by the same non-empty
   `AGK_SESSION`, without that token, fails the step at once with one line naming the fix.

SPEC-0044 rules 4 and 5 (brief #583): with `[testing] workers` above 1 the regression run named
`full` is `full_command`'s: `-n <workers>` at the end of a simple pytest command whose interpreter
imports xdist in the run's folder, `[testing] parallel_command` for another runner, or else the
command of today after one line naming the setting. Proof's own runs stay single.
Brief #980 (ADR-0422): each other regression run, a selected one, takes the same rule through
`selected_workers`: `-n <workers>` at the end of a pytest command (the whole command, or its one
simple command after a last `;`) whose interpreter imports xdist, else the command of today after
the one line of SPEC-0044 rule 4 (`NO_XDIST`, printed once with the full run's); `parallel_command`
stays the full run's alone.
Brief #1021 (ADR-0436): with `[testing] tools_file` set (unset by default), a run whose interpreter
cannot import xdist first runs `<python> -m pip install -q -r <tools_file>` once per interpreter
(`--break-system-packages` added only when pip refuses without it) and checks again; a failed
install prints `NO_TOOLS`, naming the setting, and the run stays in one process. A full run that
takes `parallel_command` whose last part is a pytest command gets the same install before it, and
the command of today with that line when xdist is still missing.
Brief #1031 (ADR-0440): with `[testing] local_full = "ci"`, a selection that `impact` made full only
because a changed file matches `always_full` (not under `profile = "thorough"`, not with
`pr_tests = "full"`, and below `full_when_share` of the `[proof]` areas' test files) runs as a
selection (`left_to_ci`): the mapped test files through their areas, with the same workers and the
same lock, after one line `tests: full suite left to CI's proof job (always_full <glob>); ran the
<n> mapped test files` (`0` when nothing is mapped, and nothing runs). The record names each such
run's set `selected (full left to CI)`, so the evidence check and the verdict see that the full
suite did not run here. CI's runs are not changed: `project_tests.py` never calls `left_to_ci`.

One line per step, `prepush: <step> ok|FAIL|skipped (<s>s)`. Exit 0 when no step failed, 1 when
one did, 2 usage, an unreadable body file or a base that does not resolve. It installs nothing but
the `tools_file` of brief #1021 when that is set, and changes no file other than the record.

Brief #507 (ADR-0256): when `make lint` exits non-zero and its output shows that a command could not
be started (`CreateProcess(NULL, <cmd> ...) failed`, `<cmd>: command not found`, `<cmd>: not found`,
`<cmd>: No such file or directory` with an exit of 127, or an exit of 127 alone), the lint step
fails with one line naming `<cmd>` and how to install it, and the raw output is not echoed; any
other lint failure prints as before. It stays a FAIL, never `not run`: lint is a rule of the
project, as the secret scan is.

Brief #509 (ADR-0258): after the regression run named `full` finishes, when its seconds exceed
`proof_timeout`, the tests step prints `prepush: warning: the full suite took <n> s, more than
proof_timeout (<m> s); proof will not finish (setting: proof_timeout); a value of about <v> s leaves
headroom`, with `<v>` = ceil(n * 1.5 / 60) * 60, and puts the line in the record's `notes`. The
outcome does not change; a run ended by the limit already prints the timeout note instead.

`--record FILE` (brief #374, ADR-0208) also writes one JSON record of the run, `schema: 1`: the
head and base shas, `started` (UTC), `tree_clean` (a dirty tree is recorded, never hidden), each
step that ran with its `name`, `outcome`, `argv`, `cwd`, `exit`, `seconds`, `output_sha256` and
`output_bytes` (the tests step adds each run it made), and the `versions` of python3, git, make
and gitleaks where found, and `notes`: the warnings of the run, such as brief #509's (ADR-0258).
Each run of the tests step also has a `timing` object (SPEC-0044 rule 3, brief #560): `files`
(path and seconds, slowest first, at most 50), `total_seconds` and `source` (`durations`, `junit`
or `unknown`), read by `impact.run_timing` from what the run already wrote; the kit adds no flag to
the command, and nothing fails because timing is missing. A `[testing] junit` report that cannot be
read, or that the run did not write, prints one line naming the setting.
It holds no output text, no environment value and no path outside the
repository (one outside is written `<outside>/<name>`, the interpreter `python3`). A failed step
still writes it. Then it prints one line for the pull request body:
`Evidence: prepush schema 1, head <sha12>, <n> steps ok, record <sha12 of the file>`. A record
file that cannot be written exits 2.

Brief #1269 (ADR-0536): `--record` with no FILE, or `--record auto`, writes the record to
`<git common dir>/agk-evidence/<40-hex head>.json`, the folder `git rev-parse --git-common-dir`
names: one per clone, shared by every worktree of it, never tracked and never making the tree
dirty, so the conductor finds it from the head alone (`evidence.py check --head <sha>`). The
folder is made when missing. `--record FILE` writes FILE as before, and the `Evidence:` line is
the same either way. A `--queue` run passes `auto` on, so the record is named by the head the
job runs on.

SPEC-0046 rule 11 (build (f)): the run folders of brief #613 (ADR-0299) are retired. The keys
`[testing] results_dir`, `keep_passed` and `keep_runs` keep their checks and do nothing: no folder,
no `AGK_RUN_DIR`, no `run_dir` in the record. When one is set, prepush prints one line
`deprecated: testing.results_dir (ADR-0303)` before its steps, and the record's `notes` hold it.

Brief #566 (SPEC-0040 build (c), rule 9): with `[locks] queue = true`, `--record FILE --queue`
runs no step here: it submits the same command without `--queue`, with the body and record paths
made absolute, as one heavy job of kind `prepush` (`lock.py submit`, with `--brief` from the
body's `Brief: #n` line and the session from `AGK_SESSION`), prints the `queued` line and returns
at once. `--queue` with the setting off, without `--record`, or with `--quick` (never queued)
exits 2 naming the setting or the option.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
import time
import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import lock as heavy_lock
from common import (
    GITLEAKS_INSTALL,
    CheckError,
    final_records,
    git,
    load_config,
    merge_base,
    proof_areas,
    proof_timeout,
    resolve_base,
    temp_env,
    utf8_output,
)
from impact import (
    NAMED,
    Impact,
    Selected,
    full_when_share,
    impact,
    junit_setting,
    level_groups,
    link_groups,
    local_full,
    machine_env,
    map_lines,
    parallel_command,
    pr_tests,
    report_of,
    run_folder_deprecation,
    run_timing,
    tools_file,
    unmapped_lines,
    workers_line,
    workers_setting,
)
from proof import area_command, execute, is_test_file, timeout_note
from test_map import refresh

HERE = Path(__file__).resolve().parent
USAGE = (
    "usage: prepush.py [--body FILE] [--base REF] [--quick] [--no-lock] [--record [FILE]] [--queue]"
)
SCHEMA = 1
AUTO_RECORD = "auto"  # `--record` with no FILE (brief #1269, ADR-0536)
EVIDENCE_FOLDER = "agk-evidence"  # in the git common dir, shared by every worktree of a clone
LEFT_TO_CI = "selected (full left to CI)"  # the record's set of such a run (brief #1031 answer 3)
LEFT_LINE = (
    "tests: full suite left to CI's proof job (always_full {glob}); ran the {n} mapped test files"
)
ALWAYS_FULL = re.compile(r"^always_full (\S+) matches ")
LOCK = "heavy"
OWN = "the pull request's own test files (the proof plan)"
NO_XDIST = (
    "tests: pytest-xdist is not importable, running in one process (setting: testing.workers)"
)
NO_PARALLEL = (
    "tests: the command is not a simple pytest command and parallel_command is not set, running "
    "in one process (setting: testing.parallel_command)"
)
NO_TOOLS = (
    "tests: the install of the test tools failed, running in one process "
    "(setting: testing.tools_file)"
)
INSTALLS: dict[tuple[str, str], bool] = {}  # one install per interpreter and file (brief #1021)
SELECTED_NOT_PYTEST = (
    "tests: {name} is not a simple pytest command, running in one process "
    "(setting: testing.workers)"
)
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
PYTHON = re.compile(r"python(?:\d+(?:\.\d+)?)?")
SHELL_SYNTAX = set(";&|<>()`$\n\\*?[]{}~#")


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
        notes: list[str] | None = None,
    ) -> None:
        self.outcome = outcome
        self.text = text
        self.not_run = not_run  # skipped although it should have run (a missing tool)
        self.ran = ran
        self.runs = runs
        self.notes = list(notes or [])  # warnings that do not change the outcome (brief #509)


class Ran:
    """One command a step ran: its argument list, folder, exit code and whole output."""

    def __init__(self, argv: list[str], cwd: Path, code: int | None, output: str) -> None:
        self.argv = argv
        self.cwd = cwd
        self.code = code
        self.output = output


def parse_args(args: list[str]) -> dict:
    options: dict = {
        "body": None, "base": None, "quick": False, "lock": True, "record": None, "queue": False
    }  # fmt: skip
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--record" and (i + 1 == len(args) or args[i + 1].startswith("--")):
            options["record"] = AUTO_RECORD  # brief #1269: the clone's shared evidence folder
            i += 1
        elif arg in ("--body", "--base", "--record") and i + 1 < len(args):
            options[arg[2:]] = args[i + 1]
            i += 2
        elif arg == "--quick":
            options["quick"] = True
            i += 1
        elif arg == "--no-lock":
            options["lock"] = False
            i += 1
        elif arg == "--queue":
            options["queue"] = True
            i += 1
        else:
            raise Usage(USAGE)
    return options


def queued(options: dict) -> int:
    """`--queue` (SPEC-0040 rule 9): hand the run to the heavy queue and run no step here."""
    if options["quick"]:
        print("prepush: --quick is never queued; run it here (option: --quick)", file=sys.stderr)
        return 2
    if not options["record"]:
        print(
            "prepush: --queue needs --record FILE, since a queued run without a record leaves"
            " no evidence (option: --record)",
            file=sys.stderr,
        )
        return 2
    if options["body"] and not Path(options["body"]).is_file():
        print("prepush: the body file cannot be read (option: --body)")
        return 2
    args: list[str] = []
    for key in ("body", "base", "record"):
        if options[key]:
            keep = key == "base" or (key == "record" and options[key] == AUTO_RECORD)
            value = options[key] if keep else os.path.abspath(options[key])
            args += [f"--{key}", value]
    args += [] if options["lock"] else ["--no-lock"]
    return heavy_lock.queue_self("prepush.py", "prepush", Path(__file__), args, options["body"])


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
    step = ran_step(["make", "lint"], root)
    if step.outcome == "FAIL" and step.ran is not None:
        cmd = missing_tool(step.ran.code, step.ran.output)
        if cmd is not None:
            step.text = (
                f"lint: the lint target runs {cmd}, which is not installed (target: lint); "
                f"install it (for example: uv tool install {cmd} or pip install {cmd}) "
                "and run prepush again"
            )
    return step


CREATE_PROCESS = re.compile(r'CreateProcess\(NULL,\s*("[^"]+"|[^\s,]+)')
NOT_FOUND = re.compile(r"(?:^|: )([^\s:]+): (?:command not found|not found)\s*$")
NO_SUCH_FILE = re.compile(r"(?:^|: )([^\s:]+): No such file or directory\s*$")
EXIT_127 = re.compile(r"\bError 127\b")
TOOL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")


def tool_name(word: str) -> str | None:
    """A command's file name as the line shows it: no quotes, folder or `.exe`; None when it is
    not a plain name."""
    name = re.split(r"[\\/]", word.strip().strip('"'))[-1]
    if name.lower().endswith(".exe"):
        name = name[:-4]
    return name if TOOL.fullmatch(name) else None


def missing_tool(code: int | None, output: str) -> str | None:
    """The command `make lint` could not start, by the signs of brief #507 answer 1, or None."""
    lines = output.splitlines()
    found = CREATE_PROCESS.search(output)
    if found:
        return tool_name(found.group(1))
    for text in lines:
        found = NOT_FOUND.search(text)
        if found:
            return tool_name(found.group(1))
    exit_127 = code == 127 or any(EXIT_127.search(text) for text in lines)
    if not exit_127:
        return None
    for text in lines:
        found = NO_SUCH_FILE.search(text)
        if found:
            return tool_name(found.group(1))
    echoed = [t for t in lines if t.strip() and not t.startswith(("make", "process_begin"))]
    return tool_name(echoed[-1].split()[0]) if echoed else None


RECORD_COMMENTS = "AGK_RECORD_COMMENTS"  # the comments file the checks read (amendment 122)
ORIGIN = re.compile(r"github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$")
NO_RECORD_COMMENTS = (
    "governance: rule 3a: the Final comments of the base's records cannot be read for the "
    "'Covered-by:' line (option: --comments, AGK_RECORD_COMMENTS)"
)


def covers(body: Path) -> bool:
    """Whether the body file has a `Covered-by:` line, as check_protected_changes.py reads it."""
    try:
        text = body.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return any(line.startswith("Covered-by:") for line in text.splitlines())


def fetch_record_comments(root: Path, base: str, folder: Path) -> Path | None:
    """With records on BASE (SPEC-0021 rule 3a), the Final comment of each, one `gh api` GET each
    as the workflow's `Record comments` step makes them, in a file of FOLDER: its path; None when
    any cannot be read (fail closed); the folder alone when BASE holds no record."""
    ids = sorted({record[1] for record in final_records(root, base).values()})
    if not ids:
        return folder
    code, url = run(["git", "remote", "get-url", "origin"], root)
    match = ORIGIN.search(url.strip()) if code == 0 else None
    if match is None or shutil.which("gh") is None:
        return None
    found: list = []
    for cid in ids:
        endpoint = f"repos/{match.group(1)}/issues/comments/{cid}"
        try:
            proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
                ["gh", "api", "--method", "GET", endpoint],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            value = json.loads(proc.stdout) if proc.returncode == 0 else None
        except (OSError, ValueError):
            value = None
        if not isinstance(value, dict):
            return None
        found.append(value)
    path = folder / "record-comments.json"
    path.write_text(json.dumps(found), encoding="utf-8")
    return path


def governance(root: Path, base: str, body: Path | None = None) -> Step:
    if not (root / "agk.mk").is_file():
        return Step("FAIL", "agk.mk is missing; governance cannot run (path class: agk.mk)")
    if shutil.which("make") is None:
        return Step("skipped", "governance: not run (make is not installed)", not_run=True)
    env = {**os.environ, "AGK_BASE": base}
    if body is None:
        return ran_step(["make", "-f", "agk.mk", "agk-governance"], root, env)
    env["AGK_PR_BODY"] = str(body.resolve())  # the body's `Covered-by:` line (ADR-0271)
    if not covers(body):
        return ran_step(["make", "-f", "agk.mk", "agk-governance"], root, env)
    # a `Covered-by:` ADR a Final accepted needs its record's comment (brief #601, ADR-0293)
    folder = Path(tempfile.mkdtemp(prefix="agk-prepush-"))
    try:
        path = fetch_record_comments(root, base, folder)
        if path is None:
            return Step("FAIL", NO_RECORD_COMMENTS)
        if path != folder:
            env[RECORD_COMMENTS] = str(path)
        return ran_step(["make", "-f", "agk.mk", "agk-governance"], root, env)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


NO_GITLEAKS = (
    "gitleaks is not installed, so the secret scan cannot run and the run stops (tool: gitleaks); "
    + GITLEAKS_INSTALL
)


LEAK_RUNBOOK = (
    "if this is a finding: follow docs/runbooks/leaked-secret.md; never paste the value anywhere"
)
DEFER_LINE = "Secret-scan: deferred to CI"  # the one body line of a deferral (brief #683, ADR-0327)
BUILDER_BRANCH = re.compile(r"^claude/brief-[1-9][0-9]*$")
DEFERRED = (
    "secret-scan deferred to CI: no gitleaks in this session and the body declares "
    f"`{DEFER_LINE}` on a builder branch; the governance run's `Secret scan` step must pass on "
    "this head before a merge (SPEC-0006 rule 11, amendment 136)"
)
NOT_BUILDER = (
    f"`{DEFER_LINE}` is accepted on a builder branch only (claude/brief-<n>), never here "
    "(SPEC-0006 rule 11, amendment 136); "
)


def deferred(root: Path, body: Path | None) -> str | None:
    """The deferral of brief #683: gitleaks is absent, the body carries DEFER_LINE and the branch
    is a builder's; the CI step then stands as the mandatory scan. The reason it does not apply,
    else None."""
    if body is None:
        return "no body file names the deferral (option: --body); "
    lines = [ln.strip() for ln in body.read_text(encoding="utf-8", errors="replace").splitlines()]
    if DEFER_LINE not in lines:
        return None
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    return None if BUILDER_BRANCH.fullmatch(branch) else NOT_BUILDER


def secret_scan(root: Path, mb: str, body: Path | None = None) -> Step:
    tool = shutil.which("gitleaks")
    if tool is None:  # never skipped, in any mode (brief #632, ADR-0306): deferred to CI, or FAIL
        reason = deferred(root, body)
        if (
            reason is None
            and body is not None
            and DEFER_LINE
            in [
                ln.strip() for ln in body.read_text(encoding="utf-8", errors="replace").splitlines()
            ]
        ):
            return Step("ok", DEFERRED)
        return Step("FAIL", (reason or "") + NO_GITLEAKS if reason == NOT_BUILDER else NO_GITLEAKS)
    head = git(root, "rev-parse", "HEAD").strip()
    cmd = [tool, "git", "--no-banner", "--redact", "--exit-code", "1", f"--log-opts={mb}..{head}"]
    found = ran_step([*cmd, "."], root)
    if found.outcome == "FAIL":  # the page, never a value (SPEC-0056 rule 13)
        found.text = f"{found.text.rstrip()}\n{LEAK_RUNBOOK}".lstrip()
    return found


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
    table = (shown.get("regression") or {}).get("table")
    own = shown.get("level_runs", shown["runs"])  # a level's own command (SPEC-0055 rule 3)
    notes = shown.get("level_notes", [])
    if not table:
        if shown.get("level_env"):  # a level with `env` is a heavy step (SPEC-0055 rule 4)
            return locked(root, ran, use_lock, lambda: proof_runs(root, own, ran, notes))
        return proof_runs(root, own, ran, notes)  # as before (brief #417 answer 4)
    return regression_step(root, mb, own, notes, ran, use_lock)


def regression_step(
    root: Path, mb: str, own: list[dict], own_notes: list[str], ran: Ran, use_lock: bool
) -> Step:
    """The tests step with a `[testing]` table: the lock, proof's runs, the regression set."""
    try:
        limit = proof_timeout(root)
        refresh(root)
        found = impact(root, mb, "HEAD")
        areas = proof_areas(root)
    except CheckError as exc:
        return Step("FAIL", str(exc), ran=ran)
    return locked(root, ran, use_lock, lambda: gate(root, own, found, areas, limit, ran, own_notes))


def locked(root: Path, ran: Ran, use_lock: bool, work: Callable[[], Step]) -> Step:
    """WORK under the heavy-step lock, released however it ends."""
    try:
        taken = take_lock(root) if use_lock else None
    except (heavy_lock.Usage, HeldBySession) as exc:
        return Step("FAIL", str(exc), ran=ran)
    except OSError:
        return Step("FAIL", f"lock {LOCK}: the lock folder cannot be written (setting: lock_dir)")
    previous = {sig: signal.signal(sig, heavy_lock.on_signal) for sig in stop_signals()}
    try:
        return work()
    except heavy_lock.Stopped as exc:
        raise SystemExit(exc.code) from None
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        if taken is not None:
            heavy_lock.clear_if_same(*taken)


def proof_runs(root: Path, runs: list[dict], ran: Ran, notes: list[str] | None = None) -> Step:
    """The tests step without a `[testing]` table: proof's plan alone, as brief #326 made it."""
    say(notes or [])
    not_run = any("not run" in n for n in notes or [])
    if not runs:
        text = "tests: nothing to run (the test plan selects no test file)"
        return Step("ok", text, not_run=not_run, ran=ran)
    try:
        limit = proof_timeout(root)
    except CheckError as exc:
        return Step("FAIL", str(exc), ran=ran)
    lines: list[str] = []
    made: list[dict] = []
    for item in runs:
        folder = root / item["cwd"]
        started, since = time.monotonic(), wall_clock()
        run_code, run_out, _ = execute(item["command"], folder, limit, env=temp_env())
        made.append(
            {
                "name": item["name"],
                "command": safe_command(item["command"], root),
                "cwd": safe_cwd(folder, root),
                "exit": run_code,
                "seconds": round(time.monotonic() - started, 3),
                **digest(run_out),
                "timing": run_timing(run_out, folder, own_report(root, item["name"]), since)[0],
            }
        )
        lines.append(f"tests: {item['name']} ({len(item['files'])} test files) in {item['cwd']}")
        if run_code is None:
            return Step("FAIL", "\n".join([*lines, timeout_note(limit)]), ran=ran, runs=made)
        if run_code != 0:
            return Step("FAIL", "\n".join([*lines, run_out.rstrip("\n")]), ran=ran, runs=made)
    return Step("ok", "\n".join(lines), not_run=not_run, ran=ran, runs=made)


def own_report(root: Path, name: str) -> str | None:
    """The report of a level's run where there is no `[testing] junit` to fall back on."""
    return report_of(proof_areas(root), name, None)


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
    process is its command (session rule 31), so taking it again would wait for itself. Through
    wrappers, the slot's token that `lock.py run` passed down names it (brief #505, ADR-0254)."""
    if not owner or owner.get("host") != socket.gethostname():
        return False
    if owner.get("child") == os.getpid() or owner.get("pid") == os.getppid():
        return True
    token = os.environ.get("AGK_LOCK_TOKEN") or ""
    return bool(token) and os.environ.get("AGK_LOCK_NAME") == LOCK and owner.get("token") == token


class HeldBySession(Exception):
    """A slot held by this run's own session in another process, which the token cannot name."""


def session_slot(held: Path, slots: int, limit: int, session: str) -> Path | None:
    """A live slot held by `session` (non-empty) that is not this run's caller's (brief #505
    answer 3); a stale one is left to `take`, which clears it as before."""
    if not session:
        return None
    for folder in heavy_lock.slot_folders(held, slots):
        owner = heavy_lock.read_owner(folder) if folder.exists() else None
        if owner and owner.get("session") == session:
            if heavy_lock.stale_reason(owner, folder, limit) is None:
                return folder
    return None


def take_lock(root: Path) -> tuple[Path, str] | None:
    """Take the heavy-step lock with lock.py's own wait lines; None when the caller holds it.
    A refused setting raises `lock.Usage`, a folder that cannot be written OSError, and a slot
    that this run's own session holds in another process `HeldBySession` (it would never free)."""
    held = heavy_lock.lock_folder(root, LOCK)
    limit = heavy_lock.stale_minutes(root)
    slots = heavy_lock.slots_setting(root)
    if caller_slot(held, slots) is not None:
        print(f"lock {LOCK}: held by this run's caller (lock.py run); not taken again", flush=True)
        return None
    session = os.environ.get("AGK_SESSION") or ""
    if session_slot(held, slots, limit, session) is not None:
        raise HeldBySession(
            f"lock {LOCK}: held by this session ({session}) in another process; run prepush "
            f"directly under lock.py run --name {LOCK}, or end that run first"
        )
    token = uuid.uuid4().hex
    owner = {
        "session": session,
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "token": token,
    }
    # No timeout: it waits its turn. The slot taken is the one released (brief #426, ADR-0231).
    taken = heavy_lock.take(held, LOCK, owner, limit, None, slots=slots)
    return (taken or held), token


def rule(item: Selected) -> str:
    if item.code == NAMED:
        return f"a test names {item.changed}"
    return f"{item.changed} matches code {item.code}, tests {', '.join(item.tests)}"


def reasons(items: list[Selected]) -> str:
    return "; ".join(dict.fromkeys(rule(i) for i in items))


def pytest_interpreter(command: str) -> str | None:
    """The interpreter of a simple pytest command (`pytest ...` or `<python> -m pytest ...`, after
    any `NAME=value` words), `python3` for a bare `pytest`; None for anything else, a command with
    shell syntax among them, since `-n` added at its end could reach another program."""
    if not command or SHELL_SYNTAX & set(command):
        return None
    try:
        words = shlex.split(command)
    except ValueError:
        return None
    while words and ASSIGNMENT.fullmatch(words[0]):
        words.pop(0)
    if words and Path(words[0]).name == "pytest":
        return "python3"  # (verify: a bare pytest may run under another interpreter)
    if words[1:3] == ["-m", "pytest"] and PYTHON.fullmatch(Path(words[0]).name):
        return words[0]
    return None


def imports_xdist(python: str, folder: Path) -> bool:
    """`import xdist` succeeds with this interpreter in the run's folder; this check installs
    nothing (SPEC-0044 rule 4; the opt-in install is `xdist_ready`'s, brief #1021)."""
    try:
        proc = subprocess.run(  # nosec B603 - the project's own interpreter, fixed arguments
            [python, "-c", "import xdist"], cwd=folder, capture_output=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def pip_install(python: str, tools: Path, folder: Path) -> bool:
    """`<python> -m pip install -q -r <tools>` in FOLDER, again with `--break-system-packages` only
    when pip refuses without it (brief #1021 answer 2); True when it succeeded."""
    base = [python, "-m", "pip", "install", "-q", "-r", str(tools)]
    for argv in (base, [*base, "--break-system-packages"]):
        try:
            proc = subprocess.run(  # nosec B603 - the project's interpreter, its own pinned file
                argv,
                cwd=folder,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        if proc.returncode == 0:
            return True
        if "externally-managed-environment" not in proc.stdout + proc.stderr:
            return False
    return False


def xdist_ready(python: str, folder: Path, root: Path | None) -> str | None:
    """None when PYTHON imports xdist in FOLDER, after one install of `[testing] tools_file` when
    it is set and the first check fails (brief #1021, ADR-0436); else the one line of the run
    that stays in one process: NO_TOOLS when the install failed, NO_XDIST otherwise."""
    if imports_xdist(python, folder):
        return None
    tools = tools_file(root) if root is not None else None
    if tools is None or root is None:  # tools is None whenever root is
        return NO_XDIST
    key = (python, str(root / tools))
    if key not in INSTALLS:
        INSTALLS[key] = pip_install(python, root / tools, folder)
    if not INSTALLS[key]:
        return NO_TOOLS
    return None if imports_xdist(python, folder) else NO_XDIST


def pytest_workers(
    command: str, folder: Path, workers: int, python: str, root: Path | None = None
) -> tuple[str | None, str | None]:
    """The one rule of the workers (SPEC-0044 rule 4, brief #980): COMMAND with `-n <workers>` at
    its end when WORKERS is above 1 and PYTHON imports xdist in FOLDER (after the one install of
    brief #1021 with ROOT's `tools_file`), else None with the line of the single run."""
    if workers <= 1:
        return None, None
    line = xdist_ready(python, folder, root)
    return (None, line) if line else (f"{command} -n {workers}", None)


def full_command(root: Path, command: str, folder: Path) -> tuple[str, str | None]:
    """The full run's command with `[testing] workers` (SPEC-0044 rules 4 and 5) and the one line
    when it stays single: `-n <workers>` at the end of a pytest command whose interpreter imports
    xdist, `parallel_command` for another runner; with one worker the command of today."""
    workers = workers_setting(root)
    if workers <= 1:
        return command, None
    python = pytest_interpreter(command)
    if python is not None:
        with_n, line = pytest_workers(command, folder, workers, python, root)
        return (with_n, None) if with_n else (command, line)
    parallel = parallel_command(root)
    if parallel is None:
        return command, NO_PARALLEL
    parallel = parallel.replace("{workers}", str(workers))
    python = last_pytest(parallel) if tools_file(root) is not None else None
    if python is not None:  # the same one-time install before it (Q-1021-1 ruled (b))
        line = xdist_ready(python, folder, root)
        if line:
            return command, line
    return parallel, None


def last_pytest(command: str) -> str | None:
    """The interpreter of the pytest command that `-n` at the end of COMMAND reaches: the whole
    command, or the one simple command after its last `;` when the part before has no `#`."""
    python = pytest_interpreter(command)
    if python is not None:
        return python
    head, sep, tail = command.rpartition(";")
    if not sep or "#" in head:
        return None
    return pytest_interpreter(tail.strip())


def selected_workers(
    root: Path, sets: list[tuple[str, str, str, str]]
) -> tuple[list[tuple[str, str, str, str]], list[str]]:
    """Each selected run (every run but `full`) with the workers of the full run's rule (brief
    #980, ADR-0422), and the lines of the runs that stay in one process. The files never change."""
    workers = workers_setting(root)
    if workers <= 1:
        return sets, []
    made, lines = [], []
    for name, command, cwd, reason in sets:
        python = last_pytest(command) if name != "full" else None
        if name != "full" and python is None:
            lines.append(SELECTED_NOT_PYTEST.format(name=name))
        elif python is not None:
            with_n, line = pytest_workers(command, root / cwd, workers, python, root)
            lines.extend([line] if line else [])  # the one line of SPEC-0044 rule 4
            command = with_n or command
        made.append((name, command, cwd, reason))
    return made, list(dict.fromkeys(lines))


def workers_notes(root: Path, sets: list[tuple[str, str, str, str]]) -> list[str]:
    """The one line `tests: <n> workers (...)` when a run of SETS starts in workers: a command
    that `pytest_workers` gave `-n <n>`, or the full run's filled `parallel_command` (brief
    #1032 answer 4, ADR-0441); none when every run stays in one process."""
    workers = workers_setting(root)
    if workers <= 1:
        return []
    parallel = parallel_command(root)
    filled = parallel.replace("{workers}", str(workers)) if parallel else None
    started = any(
        command.endswith(f" -n {workers}") or (name == "full" and command == filled)
        for name, command, _cwd, _reason in sets
    )
    return [workers_line(root)] if started else []


def suite_test_files(root: Path, areas: list[dict] | None) -> int:
    """The tracked test files that the `[proof]` areas hold (brief #980 answer 3)."""
    files = git(root, "ls-files", check=False).splitlines()
    return sum(any(is_test_file(f, a["dirs"], a["patterns"]) for a in areas or []) for f in files)


def regression_sets(
    root: Path, found: Impact, areas: list[dict] | None
) -> tuple[list[tuple[str, str, str, str]], list[str]]:
    """The regression runs and the lines of what is not run, led by `tests: map` where it is set."""
    sets, notes = selection_sets(root, found, areas)
    groups, said = link_groups(found, areas, {s[0] for s in sets}, machine_env())
    for group in groups:
        notes = [n for n in notes if not n.startswith(f"tests: {group['label']} runs on ")]
        level = group["level"]
        command = area_command(level, group["files"])
        if group["failed"]:  # fails where a run fails, naming the setting (SPEC-0055 rule 7)
            command = f"echo {shlex.quote(group['reason'])}; exit 1"
        sets = [*sets, (group["label"], command, level["cwd"], group["reason"])]
    return sets, map_lines(found) + list(dict.fromkeys([*notes, *said]))


def selection_sets(
    root: Path, found: Impact, areas: list[dict] | None
) -> tuple[list[tuple[str, str, str, str]], list[str]]:
    """The regression runs (name, command, folder, reason) and the lines of what is not run."""
    notes = [f"tests: {line}" for line in unmapped_lines(found)]
    project = str(load_config(root)["project_tests"] or "").strip()
    if found.full or (found.selected and areas is None):
        reason = found.reason or (
            f"{reasons(found.selected)}; no [proof] table runs single files, "
            "so project_tests runs once"
        )
        if not project:
            notes.append(f"tests: full not run: project_tests is not set ({reason})")
            return [], notes
        command, single = full_command(root, project, root)
        return [("full", command, ".", reason)], notes + ([single] if single else [])
    if not found.selected:
        extra = " (only documentation changed)" if found.docs_only else ""
        return [], [f"tests: regression: nothing selected{extra}", *notes]
    sets = []
    placed: set[str] = set()
    for area in areas or []:
        mine = [s for s in found.selected if is_test_file(s.test, area["dirs"], area["patterns"])]
        if mine and area.get("levels"):
            placed.update(s.test for s in mine)
            of = {s.test: s for s in mine}
            groups, said = level_groups(area, list(of), "pr", machine_env())
            notes.extend(said)
            for group in groups:
                level = group["level"]
                command = area_command(level, group["files"])
                sets.append(
                    (
                        group["label"],
                        command,
                        level["cwd"],
                        reasons([of[f] for f in group["files"]]),
                    )
                )
        elif mine:
            command = area_command(area, [s.test for s in mine])
            sets.append((area["name"], command, area["cwd"], reasons(mine)))
            placed.update(s.test for s in mine)
    notes.extend(
        f"tests: not run (in no [proof] area): {s.test}"
        for s in found.selected
        if s.test not in placed
    )
    return sets, notes


def left_to_ci(root: Path, found: Impact, areas: list[dict] | None) -> tuple[Impact, str | None]:
    """With `[testing] local_full = "ci"` (brief #1031, ADR-0440), a selection that is full only
    because a changed file matches `always_full` as a selection of its mapped files, and the one
    line that says so; any other selection unchanged, with None. Not under `profile = "thorough"`,
    not with `pr_tests = "full"`, not at `full_when_share` or above, not without a `[proof]` table
    (which runs no single file). Used by the local tests step only, never by CI's runs."""
    hit = ALWAYS_FULL.match(found.reason or "")
    if not (found.full and hit and areas) or local_full(root) != "ci":
        return found, None
    if found.profile == "thorough" or pr_tests(root) == "full":
        return found, None
    chosen, total = len({s.test for s in found.selected}), suite_test_files(root, areas)
    if total and chosen / total >= full_when_share(root):
        return found, None
    return replace(found, full=False, reason=None), LEFT_LINE.format(glob=hit.group(1), n=chosen)


def full_suite_warning(seconds: float, limit: int) -> str | None:
    """The warning when the full suite took longer than `proof_timeout` (brief #509, ADR-0258):
    proof, held to the same limit, can never finish; the value suggested leaves half again as much,
    rounded up to a whole minute."""
    if seconds <= limit:
        return None
    took = round(seconds)
    headroom = math.ceil(took * 1.5 / 60) * 60
    return (
        f"prepush: warning: the full suite took {took} s, more than proof_timeout ({limit} s); "
        f"proof will not finish (setting: proof_timeout); a value of about {headroom} s leaves "
        "headroom"
    )


def gate(
    root: Path,
    runs: list[dict],
    found: Impact,
    areas: list[dict] | None,
    limit: int,
    ran: Ran,
    own_notes: tuple[str, ...] | list[str] = (),
) -> Step:
    """Proof's runs, then the regression set (brief #417 answers 1 and 2), each run with its line
    printed when it ends; what is not run is printed before the regression runs."""
    made: list[dict] = []
    warnings: list[str] = []
    found, left = left_to_ci(root, found, areas)
    sets, notes = regression_sets(root, found, areas)
    sets, single = selected_workers(root, sets)
    notes = [*([left] if left else []), *workers_notes(root, sets), *notes, *single, *own_notes]
    notes = list(dict.fromkeys(notes))
    junit = junit_setting(root)
    planned = [(r["name"], r["command"], r["cwd"], OWN, "proof") for r in runs]
    planned.extend((*item, "regression") for item in sets)
    shown = False
    for name, command, cwd, reason, kind in planned:
        if kind == "regression" and not shown:
            say(notes)
            shown = True
        folder = root / cwd
        started, since = time.monotonic(), wall_clock()
        code, out, _ = execute(command, folder, limit, env=temp_env())
        seconds = time.monotonic() - started
        timing, timing_note = run_timing(out, folder, report_of(areas, name, junit), since)
        if timing_note:
            print(timing_note, flush=True)
        made.append(
            {
                "name": name,
                "set": LEFT_TO_CI if left and kind == "regression" else kind,
                "reason": reason,
                "command": safe_command(command, root),
                "cwd": safe_cwd(folder, root),
                "exit": code,
                "seconds": round(seconds, 3),
                **digest(out),
                "timing": timing,
            }
        )
        word = "ok" if code == 0 else "FAIL"
        print(f"prepush: tests {name} {word} ({seconds:.1f}s): {reason}", flush=True)
        if kind == "regression" and name == "full" and code is not None:
            warning = full_suite_warning(seconds, limit)
            if warning:
                print(warning, flush=True)
                warnings.append(warning)
        if code is None:
            return Step("FAIL", timeout_note(limit), ran=ran, runs=made, notes=warnings)
        if code != 0:
            return Step("FAIL", out.rstrip("\n"), ran=ran, runs=made, notes=warnings)
    if not shown:
        say(notes)
    not_run = any("not run" in n for n in notes)
    return Step("ok", "", not_run=not_run, ran=ran, runs=made, notes=warnings)


def wall_clock() -> float:
    """Now, in seconds since the epoch: a JUnit report older than its run is not its report."""
    return datetime.now(UTC).timestamp()


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


def shared_record(root: Path, head: str) -> Path | None:
    """`<git common dir>/agk-evidence/<head>.json` of the clone at ROOT (brief #1269), or None
    when git names no common dir."""
    code, out = run(["git", "rev-parse", "--git-common-dir"], root)
    if code != 0 or not out.strip():
        return None
    return (root / out.strip()).resolve() / EVIDENCE_FOLDER / f"{head}.json"


def record_file(root: Path, option: str | None) -> Path | None:
    """The record path of `--record`: FILE as given, or for `auto` the clone's shared folder,
    made when missing. A folder that cannot be made is left for the writability check."""
    if not option:
        return None
    if option != AUTO_RECORD:
        return Path(option)
    path = shared_record(root, git(root, "rev-parse", "HEAD").strip())
    if path is None:
        return Path(EVIDENCE_FOLDER) / "missing" / "record.json"  # refused below, naming the option
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # the check below refuses it naming the option
    return path


def write_record(path: Path, record: dict) -> str:
    """Write the record; return the sha256 of the file. OSError when it cannot be written."""
    data = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def retired_keys_line(root: Path) -> str | None:
    """SPEC-0046 rule 11: the deprecation line of the retired run-folder keys, or None. A malformed
    `[testing]` table prints nothing here: the steps that read it refuse it naming the setting."""
    try:
        return run_folder_deprecation(root)
    except CheckError:
        return None


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    try:
        options = parse_args(list(sys.argv[1:] if argv is None else argv))
    except Usage as exc:
        print(exc, file=sys.stderr)
        return 2
    if options["queue"]:
        return queued(options)
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
    record_path = record_file(root, options["record"])
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
            "notes": [],
        }
    deprecated = retired_keys_line(root)
    if deprecated is not None:
        print(deprecated)
        if record is not None:
            record["notes"].append(deprecated)
    steps: list[tuple[str, Callable[[], Step]]] = [
        ("pr-body", lambda: pr_body(root, body)),
        ("lint", lambda: lint(root)),
        ("governance", lambda: governance(root, base, body)),
        ("secret-scan", lambda: secret_scan(root, mb, body)),
        ("tests", lambda: tests(root, mb, options["quick"], options["lock"])),
    ]
    not_run: list[str] = []
    for name, step in steps:
        started = time.monotonic()
        result = step()
        seconds = time.monotonic() - started
        if record is not None:
            record["steps"].append(step_record(name, result, seconds, root))
            record["notes"].extend(result.notes)
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
        if result.outcome == "ok" and name in ("tests", "secret-scan") and result.text:
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
