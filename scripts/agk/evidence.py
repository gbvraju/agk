# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""Check a local evidence record against the head and re-run a sample of it (brief #434, ADR-0233).

    python3 scripts/agk/evidence.py check RECORD [--head SHA] [--sample N] [--json]
    python3 scripts/agk/evidence.py check --head SHA [--sample N] [--json]
    python3 scripts/agk/evidence.py push --branch BRANCH [--remote REMOTE]

RECORD is the file that `prepush.py --record` wrote (schema 1, brief #374, ADR-0208). A record of
another schema, or one whose fields are not those of schema 1, is refused (exit 2, naming the field,
never its value). The check reports, in this order:

- `stale` when the record's `head` is not SHA (by default the current `HEAD`);
- `dirty` when its `tree_clean` is false;
- `failed` when a recorded step did not exit 0 or has the outcome `FAIL`, a run of the tests step
  did not exit 0, or the record's `result` is not `passed`.

Any of these is a difference and nothing is re-run. Otherwise it adds a detached worktree of the
head in a new temporary folder, with `-c core.autocrlf=false -c core.eol=lf` so that it holds the
committed bytes whatever the person's git configuration says, runs `make -f agk.mk agk-governance`
there with the conductor's environment (`PATH`, a scratch `HOME` and `AGK_BASE` set to the record's
`base`; brief #1291, ADR-0550), so that a correct record agrees with the conductor's own run, and
rebuilds from the head what prepush runs: each step it knows (`pr-body`,
`lint`, `governance`, `secret-scan`, `tests`) as prepush builds it, and the test runs from
`test_plan.py --json` in the worktree (and the regression set of a `[testing]` table), matched to
the recorded runs by name. A step or run whose name prepush does not know, or whose recorded argv,
command or folder is not the rebuilt one, is a difference (`not what prepush runs: <name> (field:
<f>)`). Nothing of the record is ever executed. Then it re-runs N rebuilt units (default 1), chosen
from the head sha (a sha256 of the sha and the unit's name orders them), so the same head always
gives the same sample. A body file outside the repository, or a gitleaks that is not installed here,
cannot be repeated: the unit is listed, not sampled. It compares exit codes with the record's; a
different output digest is a note, never a failure, since outputs carry timings. A run's optional
`timing` object (SPEC-0044 rule 3) is accepted in its one form and never re-run or compared.
The full run's command is rebuilt with `[testing] workers` as prepush builds it (SPEC-0044 rule
4, `prepush.full_command`) and each selected run with `prepush.selected_workers` (brief #980,
ADR-0422), so a record made with workers agrees on the same machine.
Governance and the re-runs hold the heavy-step lock (`lock.py`, name `heavy`), unless the caller
already holds it. Each command runs in its own process group, and on a timeout, a signal or an
error its whole tree is killed before the lock is released and the worktree is removed, also on a
failure or an interrupt.

One line per finding (`evidence: ...`), then one line for the conductor to quote in the verdict:
`Evidence check: agrees|differs, head <sha12>, record <sha12 of the file>, governance <outcome>,
sample <k> of <m> same exit`. `--json` prints one JSON object instead.

Brief #1269 (ADR-0536): RECORD is optional when `--head` is given. Without it the check reads
`<git common dir>/agk-evidence/<40-hex head>.json`, the clone's shared evidence folder that
`prepush.py --record` with no FILE writes, shared by every worktree of the clone. When that file is
missing it exits 3 with `evidence: no record for this head in the shared evidence folder (option:
--record)`, naming the option, never a path. Without RECORD and without `--head` it is a usage
error.

Brief #1447 (ADR-0605): when that folder has no record of the head, the check runs one `git fetch
origin +refs/notes/agk-evidence:refs/notes/agk-evidence-origin` and reads the note of the head from
that ref, which `prepush.py --record` writes in local mode and `push` sends; it prints `evidence:
record read from the note of the head (ref: refs/notes/agk-evidence)` and checks the note exactly as
a record file, its printed digest being that of the note's bytes. No note, no remote or a refused
fetch is the exit 3 above. `push --branch B [--remote R]` (default `origin`) merges the remote's
notes into the clone's with the `ours` strategy and runs `git push R B refs/notes/agk-evidence`;
when only the notes ref is refused it prints one line naming that setting and the fallback (the
record copied by hand) and exits 0, else git's exit code. A fetch or push never prompts.

Exit 0 when the record agrees, 1 when it differs, 2 on a usage error or a bad record, 3 on an I/O
error (a record that cannot be read, a worktree that cannot be made, make not installed). It posts
nothing, needs no network but the notes fetch above and changes nothing in the repository but the
worktree it removes (and the fetched notes ref).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import lock as heavy_lock
from common import CheckError, long_temp_dir, proof_areas, proof_timeout, temp_env, utf8_output
from impact import impact
from prepush import (
    LOCK,
    NOTE_NOT_PUSHED,
    NOTES_REF,
    digest,
    regression_sets,
    safe_command,
    safe_cwd,
    selected_workers,
    shared_record,
    stop_signals,
    take_lock,
)
from proof import WINDOWS, kill_tree, popen_options

HERE = Path(__file__).resolve().parent
USAGE = (
    "usage: evidence.py check RECORD [--head SHA] [--sample N] [--json] | check --head SHA ..."
    " | push --branch BRANCH [--remote REMOTE]"
)
NO_SHARED = "evidence: no record for this head in the shared evidence folder (option: --record)"
FETCHED_REF = NOTES_REF + "-origin"  # the remote's notes, kept apart from the clone's own
NOTE_READ = f"evidence: record read from the note of the head (ref: {NOTES_REF})"
PUSH_USAGE = "usage: evidence.py push --branch BRANCH [--remote REMOTE]"
SCHEMA = 1
DEFAULT_SAMPLE = 1
SHA = re.compile(r"[0-9a-f]{40}")
OUTSIDE = "<outside>/"
OUTCOMES = ("ok", "FAIL", "skipped")
RESULTS = ("passed", "failed")
TIMING_SOURCES = ("durations", "junit", "unknown")
GOVERNANCE = ["make", "-f", "agk.mk", "agk-governance"]


class Usage(Exception):
    """A usage error or a bad record (exit 2)."""


class Unreadable(Exception):
    """An I/O error (exit 3)."""


def parse_args(args: list[str]) -> dict:
    if not args or args[0] != "check":
        raise Usage(USAGE)
    options: dict = {"record": None, "head": None, "sample": DEFAULT_SAMPLE, "json": False}
    i = 1
    while i < len(args):
        arg = args[i]
        if arg in ("--head", "--sample") and i + 1 < len(args):
            value = args[i + 1]
            if arg == "--sample":
                if not value.isdigit() or int(value) < 1:
                    raise Usage(USAGE)
                options["sample"] = int(value)
            else:
                options["head"] = value
            i += 2
        elif arg == "--json":
            options["json"] = True
            i += 1
        elif not arg.startswith("-") and options["record"] is None:
            options["record"] = arg
            i += 1
        else:
            raise Usage(USAGE)
    if options["record"] is None and options["head"] is None:
        raise Usage(USAGE)
    return options


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8"
    )


def bad(field: str) -> Usage:
    return Usage(f"evidence: the record is not a schema {SCHEMA} record (field: {field})")


def is_exit(value) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool))


def valid_step(item) -> bool:
    if not isinstance(item, dict):
        return False
    if not isinstance(item.get("name"), str) or not isinstance(item.get("cwd"), str):
        return False
    argv = item.get("argv")
    if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
        return False
    if "exit" not in item or not is_exit(item["exit"]):
        return False
    if not isinstance(item.get("output_sha256"), str):
        return False
    if item.get("outcome") not in OUTCOMES:
        return False
    runs = item.get("runs")
    if runs is None:
        return True
    return isinstance(runs, list) and all(valid_run(r) for r in runs)


def valid_run(item) -> bool:
    return (
        isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and isinstance(item.get("command"), str)
        and isinstance(item.get("cwd"), str)
        and "exit" in item
        and is_exit(item["exit"])
        and ("timing" not in item or valid_timing(item["timing"]))
    )


def is_seconds(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def valid_timing(item) -> bool:
    """The one optional field of a run (SPEC-0044 rule 3): accepted in this form, never re-run
    or compared."""
    if not isinstance(item, dict) or item.get("source") not in TIMING_SOURCES:
        return False
    total, files = item.get("total_seconds"), item.get("files")
    if not (total is None or is_seconds(total)) or not isinstance(files, list):
        return False
    return all(
        isinstance(f, dict) and isinstance(f.get("path"), str) and is_seconds(f.get("seconds"))
        for f in files
    )


def load(path: Path) -> tuple[dict, str]:
    """The record and the sha256 of its bytes. Unreadable on an I/O error, Usage on a bad record."""
    try:
        data = path.read_bytes()
    except OSError:
        raise Unreadable("evidence: the record cannot be read (option: RECORD)") from None
    return parse(data)


def parse(data: bytes) -> tuple[dict, str]:
    """A record's bytes, from a file or a note, as `load` reads them (brief #1447 answer 3)."""
    try:
        record = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise bad("schema") from None
    if not isinstance(record, dict):
        raise bad("schema")
    schema = record.get("schema")
    if isinstance(schema, bool) or schema != SCHEMA:
        raise bad("schema")
    for field in ("head", "base"):
        if not isinstance(record.get(field), str) or not SHA.fullmatch(record[field]):
            raise bad(field)
    if not isinstance(record.get("tree_clean"), bool):
        raise bad("tree_clean")
    steps = record.get("steps")
    if not isinstance(steps, list) or not all(valid_step(s) for s in steps):
        raise bad("steps")
    if record.get("result") not in RESULTS:
        raise bad("result")
    return record, hashlib.sha256(data).hexdigest()


def load_shared(root: Path, head: str, as_json: bool = False) -> tuple[dict, str]:
    """The record of HEAD in the clone's shared evidence folder (brief #1269), as `load` reads it;
    Unreadable naming the option when it is missing."""
    path = shared_record(root, head)
    if path is not None and path.is_file():
        return load(path)
    data = fetched_note(root, head)  # brief #1447: the folder first, then the pushed note
    if data is None:
        raise Unreadable(NO_SHARED)
    print(NOTE_READ, file=sys.stderr if as_json else sys.stdout)
    return parse(data)


def quiet_git(root: Path, *args: str) -> subprocess.CompletedProcess:
    """git with bytes out and no prompt for credentials: a fetch or push never waits on a person."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", *args], cwd=root, capture_output=True, env=env
    )


def fetch_notes(root: Path, remote: str) -> bool:
    """The remote's notes ref into `FETCHED_REF`; False when it has none or cannot be read."""
    return quiet_git(root, "fetch", "-q", remote, f"+{NOTES_REF}:{FETCHED_REF}").returncode == 0


def fetched_note(root: Path, head: str) -> bytes | None:
    """The bytes of HEAD's note on `origin`, after one fetch of its notes ref, or None."""
    if not fetch_notes(root, "origin"):
        return None
    listed = quiet_git(root, "notes", "--ref", FETCHED_REF, "list", head)
    blob = listed.stdout.decode("ascii", errors="replace").split()
    if listed.returncode != 0 or not blob:
        return None
    shown = quiet_git(root, "cat-file", "blob", blob[0])
    return shown.stdout if shown.returncode == 0 else None


def push(root: Path, args: list[str]) -> int:
    """`push --branch B [--remote R]` (brief #1447 answers 1 and 6): merge the remote's notes into
    the clone's (`ours`: notes are keyed by head), then push the branch and the notes ref. When the
    branch landed and only the notes ref was refused, print `NOTE_NOT_PUSHED` and exit 0."""
    if len(args) % 2 or any(a not in ("--branch", "--remote") for a in args[::2]):
        raise Usage(PUSH_USAGE)
    options = dict(zip(args[::2], args[1::2], strict=True))
    branch, remote = options.get("--branch", ""), options.get("--remote", "origin")
    if not branch or not remote:
        raise Usage(PUSH_USAGE)
    has_notes = quiet_git(root, "rev-parse", "-q", "--verify", NOTES_REF).returncode == 0
    if fetch_notes(root, remote):
        if has_notes:
            quiet_git(root, "notes", "--ref", NOTES_REF, "merge", "-q", "-s", "ours", FETCHED_REF)
        else:
            has_notes = quiet_git(root, "update-ref", NOTES_REF, FETCHED_REF).returncode == 0
    refs = [branch, NOTES_REF] if has_notes else [branch]
    pushed = quiet_git(root, "push", "-q", remote, *refs)
    sys.stdout.write((pushed.stdout + pushed.stderr).decode("utf-8", errors="replace"))
    if pushed.returncode == 0:
        return 0
    there = quiet_git(root, "ls-remote", remote, f"refs/heads/{branch}").stdout.split()
    here = quiet_git(root, "rev-parse", "-q", "--verify", f"refs/heads/{branch}").stdout.strip()
    if has_notes and there and there[0] == here:
        print(NOTE_NOT_PUSHED)
        return 0
    return pushed.returncode


def resolve(root: Path, ref: str | None, given: bool) -> str:
    proc = git(root, "rev-parse", "--verify", "-q", f"{ref or 'HEAD'}^{{commit}}")
    if proc.returncode != 0:
        raise Usage("evidence: the head does not resolve (option: --head)" if given else USAGE)
    return proc.stdout.strip()


def problems(record: dict, head: str) -> list[str]:
    """`stale`, `dirty` and `failed`, each as one line, in that order (answer 1). A step fails on a
    non-zero exit or a `FAIL` outcome (prepush records some FAIL steps with no exit, or with the
    exit 0 of a command a refusal followed: verdict on 57c122a, item 2), a test run on any exit but
    0, and the record on any result but `passed`."""
    found = []
    if record["head"] != head:
        found.append(f"stale: the record is of head {record['head'][:12]}, not {head[:12]}")
    if not record["tree_clean"]:
        found.append("dirty: the record's work tree was not clean (field: tree_clean)")
    for item in record["steps"]:
        if item["exit"] is not None and item["exit"] != 0:
            found.append(f"failed: step {item['name']} exited {item['exit']}")
        elif item["outcome"] == "FAIL":
            found.append(f"failed: step {item['name']} FAIL")
        for run in item.get("runs") or []:
            if run["exit"] != 0:
                code = "none" if run["exit"] is None else run["exit"]
                found.append(f"failed: run {item['name']}/{run['name']} exited {code}")
    if record["result"] != "passed":
        found.append(f"failed: the record's result is {record['result']} (field: result)")
    return found


def sample(head: str, names: list[str], count: int) -> list[str]:
    """`count` of `names`, chosen from the head sha alone: the same head, the same steps (answer 2).

    Each name is ranked by the sha256 of `<head>:<name>`; the order of the record does not matter
    and no random generator is involved, so no Python version changes the pick."""

    def rank(name: str) -> str:
        return hashlib.sha256(f"{head}:{name}".encode()).hexdigest()

    return sorted(dict.fromkeys(names), key=rank)[:count]


class Unit:
    """One thing the check may re-run: a command rebuilt from the head, never from the record.

    `argv` runs without a shell, `command` through `sh -c` (a test run, as proof runs it); `exit`
    and `digest` are what the record says it gave."""

    def __init__(
        self,
        name: str,
        cwd: Path,
        exit: int | None,
        digest: str | None,
        argv: list[str] | None = None,
        command: str | None = None,
    ) -> None:
        self.name = name
        self.cwd = cwd
        self.exit = exit
        self.digest = digest
        self.argv = argv
        self.command = command


def tool_name(argv0: str) -> str:
    """The executable's base name, lower-cased, with one trailing `.exe` removed (brief #504).

    A value that holds a backslash is read as a Windows path on any operating system, so that a
    record written on Windows (`C:\\...\\gitleaks.EXE`) names the same tool as `gitleaks`."""
    path = PureWindowsPath(argv0) if "\\" in argv0 else PurePosixPath(argv0)
    name = path.name.lower()
    return name[: -len(".exe")] if name.endswith(".exe") else name


def kit_script(tree: Path, name: str) -> str:
    """A kit script of the head's worktree, or of this kit when the head has none."""
    path = tree / "scripts" / "agk" / name
    return str(path if path.is_file() else HERE / name)


def rebuild(
    tree: Path, record: dict, env: dict, limit: int
) -> tuple[dict[str, Unit], list[str], list[str]]:
    """The units prepush runs on the head, matched to the record's steps and runs by name.

    Returns the repeatable units, the differences (a name prepush does not know, or a recorded argv,
    command or folder that is not the rebuilt one: `not what prepush runs: <name> (field: <f>)`)
    and the notes (a unit that cannot be repeated here). Nothing of the record is ever executed
    (verdict on 57c122a, item 1)."""
    units: dict[str, Unit] = {}
    diffs: list[str] = []
    notes: list[str] = []
    head = record["head"]
    mb = git(tree, "merge-base", record["base"], "HEAD").stdout.strip()

    def differ(name: str, field: str) -> None:
        diffs.append(f"not what prepush runs: {name} (field: {field})")

    for item in record["steps"]:
        name = item["name"]
        recorded = item["argv"]
        if not recorded and item["exit"] is None and item["outcome"] == "skipped":
            continue  # a skipped step ran nothing
        if item["cwd"] != ".":
            differ(name, "cwd")
            continue
        if name == "governance":
            if recorded != GOVERNANCE:
                differ(name, "argv")
            continue  # always re-run on its own
        if name == "pr-body":
            want = ["python3", "scripts/agk/check_pr_body.py", "--draft", "false"]
            if recorded[:-1] != want or len(recorded) != len(want) + 1:
                differ(name, "argv")
            elif OUTSIDE in recorded[-1]:
                notes.append(f"not repeatable: {name} (a path outside the repository)")
            else:
                argv = [sys.executable, kit_script(tree, "check_pr_body.py"), *want[2:]]
                units[name] = Unit(
                    name, tree, item["exit"], item["output_sha256"], [*argv, recorded[-1]]
                )
            continue
        if name == "lint":
            if recorded != ["make", "lint"]:
                differ(name, "argv")
            else:
                units[name] = Unit(
                    name, tree, item["exit"], item["output_sha256"], ["make", "lint"]
                )
            continue
        if name == "secret-scan":
            tail = [
                "git",
                "--no-banner",
                "--redact",
                "--exit-code",
                "1",
                f"--log-opts={mb}..{head}",
                ".",
            ]
            if not recorded or tool_name(recorded[0]) != "gitleaks" or recorded[1:] != tail:
                differ(name, "argv")
            elif shutil.which("gitleaks") is None:
                notes.append(f"not repeatable: {name} (gitleaks is not installed here)")
            else:
                argv = [str(shutil.which("gitleaks")), *tail]
                units[name] = Unit(name, tree, item["exit"], item["output_sha256"], argv)
            continue
        if name == "tests":
            want = ["python3", "scripts/agk/test_plan.py", "--json", "--base", mb, "--head", "HEAD"]
            if recorded != want:
                differ(name, "argv")
                continue
            argv = [sys.executable, kit_script(tree, "test_plan.py"), *want[2:]]
            units[name] = Unit(name, tree, item["exit"], item["output_sha256"], argv)
            planned = planned_runs(tree, argv, env, mb, limit)
            for run in item.get("runs") or []:
                key = (run.get("set") or "proof", run["name"])
                label = (
                    f"tests/{run['name']}" if key[0] == "proof" else f"tests/{key[0]}/{run['name']}"
                )
                if key not in planned:
                    differ(label, "name")
                    continue
                command, folder = planned[key]
                if run["command"] != safe_command(command, tree):
                    differ(label, "command")
                elif run["cwd"] != safe_cwd(folder, tree):
                    differ(label, "cwd")
                else:
                    units[label] = Unit(
                        label, folder, run["exit"], run.get("output_sha256"), command=command
                    )
            continue
        differ(name, "name")
    return units, diffs, notes


def planned_runs(
    tree: Path, argv: list[str], env: dict, mb: str, limit: int
) -> dict[tuple[str, str], tuple[str, Path]]:
    """(set, name) -> (command, folder) of the test runs prepush makes on the head: the plan of
    `test_plan.py`, then the regression set where the head has a `[testing]` table."""
    code, out = spawn(argv, tree, env, limit)
    if code != 0:
        return {}
    try:
        shown = json.loads(out)
    except ValueError:
        return {}
    planned = {("proof", r["name"]): (r["command"], tree / r["cwd"]) for r in shown.get("runs", [])}
    if (shown.get("regression") or {}).get("table"):
        try:
            sets, _ = regression_sets(tree, impact(tree, mb, "HEAD"), proof_areas(tree))
        except CheckError:
            return planned
        sets, _ = selected_workers(tree, sets)  # as prepush.gate runs them (brief #980)
        for name, command, cwd, _reason in sets:
            planned[("regression", name)] = (command, tree / cwd)
    return planned


def spawn(cmd: list[str], cwd: Path, env: dict, limit: int | None = None) -> tuple[int | None, str]:
    """Run `cmd` in its own process group; on a timeout, a signal or any other exception the whole
    tree is killed before this returns or re-raises (verdict on 57c122a, item 3). None on a
    timeout, 127 when it cannot start."""
    try:
        proc = subprocess.Popen(  # nosec B603 - a command rebuilt from the head, never the record
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            **popen_options(WINDOWS),
        )
    except OSError:
        return 127, ""
    try:
        out, _ = proc.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        return None, ""
    except BaseException:
        kill_tree(proc)
        raise
    return proc.returncode, (out or "").rstrip("\n")


def rerun(unit: Unit, env: dict, limit: int) -> tuple[int | None, str]:
    if unit.command is not None:
        return spawn(["sh", "-c", unit.command], unit.cwd, env, limit)
    return spawn(unit.argv or [], unit.cwd, env)


def governance(tree: Path, env: dict) -> tuple[int, str]:
    if shutil.which("make") is None:
        raise Unreadable("evidence: make is not installed; governance cannot run (tool: make)")
    code, out = spawn(GOVERNANCE, tree, env)
    return (127 if code is None else code), out


def remove(root: Path, temp: Path, tree: Path) -> None:
    """Remove the worktree and its temporary folder; prune git's note of it (answer 2)."""
    git(root, "worktree", "remove", "--force", str(tree))
    shutil.rmtree(temp, ignore_errors=True)
    git(root, "worktree", "prune")


def run_env(base: str) -> dict:
    """The environment of governance and every re-run: this process's, with `AGK_BASE`, and on
    Windows the long temporary folder in `TEMP`, `TMP` and `TMPDIR` (brief #508, ADR-0257)."""
    return temp_env({**os.environ, "AGK_BASE": base})


# What governance keeps of this process's environment besides PATH (brief #1291, ADR-0550): on
# Windows only, what Python and the shell need to start; never a token, never HOME or git settings.
WINDOWS_KEEP = ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT")
# The line ends of the worktree: the committed bytes, whatever the person's git configuration says.
CHECKOUT = ("-c", "core.autocrlf=false", "-c", "core.eol=lf")


def governance_env(base: str, home: Path) -> dict:
    """The environment of the governance run, the conductor's (`env -i PATH="$PATH" HOME=<scratch>
    AGK_BASE=<base>`, the local-mode guide): `PATH`, a scratch `HOME` inside the temporary folder
    and `AGK_BASE`; on Windows also `WINDOWS_KEEP`, `USERPROFILE` as that `HOME`, and the long
    temporary folder in `TEMP`, `TMP` and `TMPDIR` (brief #508). The person's own `HOME`, git
    configuration and tokens never reach it (brief #1291, ADR-0550)."""
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "AGK_BASE": base}
    if WINDOWS:
        env.update({k: os.environ[k] for k in WINDOWS_KEEP if k in os.environ})
        env["USERPROFILE"] = str(home)
    return temp_env(env)


def in_worktree(root: Path, record: dict, head: str, count: int) -> dict:
    """Governance and the sample, in a detached worktree of `head`, under the heavy-step lock."""
    try:
        temp = Path(tempfile.mkdtemp(prefix="agk-evidence-", dir=long_temp_dir()))
    except OSError:
        raise Unreadable(
            "evidence: the temporary folder cannot be made (setting: TMPDIR)"
        ) from None
    tree = temp / "head"
    taken = None
    previous = {sig: signal.signal(sig, heavy_lock.on_signal) for sig in stop_signals()}
    try:
        made = git(root, *CHECKOUT, "worktree", "add", "--detach", "-q", str(tree), head)
        if made.returncode != 0:
            raise Unreadable(
                "evidence: the worktree of the head cannot be made (path class: TMPDIR)"
            )
        try:
            taken = take_lock(root)
        except heavy_lock.Usage as exc:
            raise Usage(f"evidence: {exc}") from None
        except OSError:
            raise Unreadable(
                f"evidence: lock {LOCK}: the lock folder cannot be written (setting: lock_dir)"
            ) from None
        home = temp / "home"
        home.mkdir()
        code, out = governance(tree, governance_env(record["base"], home))
        env = run_env(record["base"])
        try:
            limit = proof_timeout(tree)
        except CheckError as exc:
            raise Usage(f"evidence: {exc}") from None
        found, diffs, notes = rebuild(tree, record, env, limit)
        picked = sample(head, list(found), count)
        results = []
        for name in picked:
            unit = found[name]
            got, output = rerun(unit, env, limit)
            same_output = digest(output)["output_sha256"] == unit.digest
            results.append(
                {
                    "name": name,
                    "recorded_exit": unit.exit,
                    "exit": got,
                    "same_exit": got == unit.exit,
                    "same_output": same_output,
                }
            )
        return {
            "governance": {"exit": code, "output": out},
            "differences": diffs,
            "sample": results,
            "notes": notes,
            "candidates": len(found),
        }
    except heavy_lock.Stopped as exc:
        raise SystemExit(exc.code) from None
    finally:
        if taken is not None:
            heavy_lock.clear_if_same(*taken)
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        remove(root, temp, tree)


def report(head: str, sha: str, found: list[str], ran: dict | None, as_json: bool) -> int:
    differs = bool(found)
    gov = "not run"
    same = 0
    total = 0
    lines = [f"evidence: {p}" for p in found]
    if ran is not None:
        ok = ran["governance"]["exit"] == 0
        gov = "ok" if ok else "FAIL"
        differs = differs or not ok
        lines.append(f"evidence: governance {gov} in a clean worktree of {head[:12]}")
        if not ok and not as_json and ran["governance"]["output"]:
            lines.append(ran["governance"]["output"])
        lines.extend(f"evidence: {d}" for d in ran["differences"])
        differs = differs or bool(ran["differences"])
        lines.extend(f"evidence: {n}" for n in ran["notes"])
        total = len(ran["sample"])
        for item in ran["sample"]:
            code = "none" if item["exit"] is None else item["exit"]
            was = "none" if item["recorded_exit"] is None else item["recorded_exit"]
            verdict = "same" if item["same_exit"] else "DIFFERS"
            note = "" if item["same_output"] else "; output digest differs (a note)"
            lines.append(
                f"evidence: re-ran {item['name']}: exit {code} (recorded {was}) {verdict}{note}"
            )
            same += item["same_exit"]
            differs = differs or not item["same_exit"]
        if total == 0:
            lines.append("evidence: no repeatable step to re-run")
    result = "differs" if differs else "agrees"
    if as_json:
        data = {
            "result": result,
            "head": head,
            "record_sha256": sha,
            "problems": found + (ran["differences"] if ran else []),
            "governance": {"exit": ran["governance"]["exit"]} if ran else None,
            "sample": ran["sample"] if ran else [],
            "notes": ran["notes"] if ran else [],
        }
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        for line in lines:
            print(line)
        print(
            f"Evidence check: {result}, head {head[:12]}, record {sha[:12]}, governance {gov}, "
            f"sample {same} of {total} same exit"
        )
    return 1 if differs else 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        options = parse_args(args) if args[:1] != ["push"] else {}
        top = git(Path.cwd(), "rev-parse", "--show-toplevel")
        if top.returncode != 0:
            raise Usage("evidence: not inside a git work tree (path class: root)")
        root = Path(top.stdout.strip())
        if not options:
            return push(root, args[1:])
        head = resolve(root, options["head"], options["head"] is not None)
        if options["record"] is not None:
            record, sha = load(Path(options["record"]))
        else:
            record, sha = load_shared(root, head, options["json"])
        found = problems(record, head)
        ran = None if found else in_worktree(root, record, head, options["sample"])
        return report(head, sha, found, ran, options["json"])
    except Usage as exc:
        print(exc, file=sys.stderr)
        return 2
    except Unreadable as exc:
        print(exc, file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
