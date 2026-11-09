"""The project's tests in CI: the full suite, or on a pull request only the selected tests (brief
#453, ADR-0242).

    python3 scripts/agk/project_tests.py        (called by `make -f agk.mk agk-project-test`)

Runs the `project_tests` command of `agk.toml`; with none it prints the notice of `agk.mk` and
succeeds. With `[testing] pr_tests = "selected"` it decides by the event, which the workflow passes
in as `EVENT`:

- `pull_request`: the regression set that `prepush.regression_sets` builds for the head against
  its merge base with the base (`AGK_BASE`, else the default branch): the full command when the
  plan is full, else each selected run, the command of its `[proof]` area in that area's folder;
- the full command for a push, any other event, an unset `EVENT`, a release pull request (one
  whose `version` in `agk.toml` differs from the base's, read as `check_release.toml_version`
  reads it), a base that does not resolve, and a selected file that no `[proof]` area can take.

Under `selected` it first prints, and appends to `$GITHUB_STEP_SUMMARY` when that is set, the
line `project tests: pr_tests selected, event <event>`, the plan's `regression` section, the lines
of what is not run and why, and the decision. Each run ends with
`project tests: <name> ok|FAIL (<s>s): <reason>`; the first failure ends it with exit 1. With
`full`, or without a `[testing]` table, it runs the full command exactly as `agk.mk` did and prints
nothing more. A bad setting is refused naming it (exit 1). It calls no network.

With `[testing] workers` above 1 (SPEC-0044 rules 4 and 5, brief #583) the full command is
`prepush.full_command`'s: `-n <workers>` added to a pytest command whose interpreter imports
xdist, `parallel_command` for another runner, or else the command of today after one line naming
the setting. A `[proof]` area's command is never changed.

With `[testing] rerun_alone = true` (brief #670, ADR-0323, SPEC-0044 rule 1 as amendment 135
proposes; `--no-rerun-alone` turns it off for one call, and `--rerun-alone` without the setting is
refused naming it) a full run that fails reruns each failed test alone, once: the ids come from the
JUnit report at `[testing] junit` when readable, else the runner's `FAILED <id>` lines, and the
rerun is the project's pytest command with its `-c`, `-p`, `-o`, `--rootdir` and `--confcutdir`
options and the test id in place of its paths. A pass alone is one strike written by `flakes.py
add` (owner `AGK_SESSION`, else `unassigned`) with its failure signature and the issue action of
`failures.py issue-body` printed (nothing is posted); a failure alone is a real failure. The run
exits 0 only when every failed test passed alone; with no test id found, more than ten failed
tests or a command that is not pytest, it exits as today. Without the setting nothing changes.

Under the same setting a selected run of a level with `rerun`, a command with `{id}`, reruns a
failed test alone for any runner, in the level's `cwd` and under the same limit (SPEC-0055 rule 9,
brief #806). Its ids come only from the reports this run wrote (the level's `junit`, else
`[testing] junit`); with no report there is no rerun and no strike, and it exits as it did.

A pull request's links (SPEC-0055 rule 7, brief #828) run after the selection, after a full run
that a selected file in no area causes, and under `full` after the full command: a linked level
need not be part of it. A linked level whose environment is absent is a failing run that names
`testing.links`.

Under `map_source = "generated"` a pull request's selection, and its links under `full`, first
rebuild the test map when it is missing or of another tree (SPEC-0055 rule 5, brief #833).

`check_release.py` is kit-only (never installed), so `toml_version` restates its reading of
`version`; a kit test pins the two equal (Q-453-7).
"""

from __future__ import annotations

import os
import shlex
import subprocess  # nosec B404 - the project's own test command, run as the caller
import sys
import time
import tomllib
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, git, load_config, merge_base, proof_areas, repo_root, resolve_base
from impact import (
    LINK_REASON,
    MAP_FILE,
    MAP_STALE,
    MAP_UNREAD,
    impact,
    junit_setting,
    level_of,
    pr_tests,
    report_files,
    report_of,
    rerun_alone,
    testing_table,
    text,
)
from prepush import full_command, pytest_interpreter, regression_sets
from test_map import refresh

NOTICE = "agk: no project_tests configured; the project runs its own tests"
EVENT = "pull_request"
USAGE = "usage: project_tests.py [--rerun-alone | --no-rerun-alone]"
MAX_RERUNS = 10
KEPT_OPTIONS = ("-c", "-p", "-o", "--rootdir", "--confcutdir")
NO_SETTING = "project tests: --rerun-alone needs rerun_alone = true (setting: testing.rerun_alone)"


def shell(command: str, cwd: Path) -> int:
    """Run the project's command with its output shown as it comes, as `sh -c` in agk.mk did."""
    proc = subprocess.run(  # nosec B603 B607 - the project's own test command, run as the caller
        ["sh", "-c", command], cwd=cwd
    )
    return proc.returncode


def captured(command: str, cwd: Path) -> tuple[int, str]:
    """Run the command as `shell` does, showing its output as it comes and keeping it."""
    proc = subprocess.Popen(  # nosec B603 B607 - the project's own test command, run as the caller
        ["sh", "-c", command],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    kept = []
    for line in proc.stdout or []:
        print(line, end="", flush=True)
        kept.append(line)
    return proc.wait(), "".join(kept)


def alone_command(command: str, test_id: str) -> str | None:
    """The project's pytest command for one test: its words up to `pytest`, the options of
    KEPT_OPTIONS with their values, then the test id; None for a command that is not pytest."""
    if pytest_interpreter(command) is None:
        return None
    words = shlex.split(command)
    at = next(i for i, w in enumerate(words) if Path(w).name == "pytest")
    head, rest = words[: at + 1], words[at + 1 :]
    kept: list[str] = []
    i = 0
    while i < len(rest):
        word = rest[i]
        if word in KEPT_OPTIONS and i + 1 < len(rest):
            kept += [word, rest[i + 1]]
            i += 2
            continue
        if any(word.startswith(f"{o}=") for o in KEPT_OPTIONS if o.startswith("--")):
            kept.append(word)
        i += 1
    return shlex.join([*head, *kept, test_id])


def rerun_failed(root: Path, project: str, output: str, code: int) -> int:
    """Rerun each failed test alone, once; a pass is a strike (brief #670). The exit code."""
    import failures  # the failure signature and issue action (SPEC-0046)

    junit = junit_setting(root)
    reports = report_files(root, junit) if junit else None
    found = dict(failures.failed_tests(output, reports, pytest=True))
    if alone_command(project, "x") is None:
        say(["project tests: rerun alone needs a pytest command (setting: testing.rerun_alone)"])
        return code
    return rerun_each(root, found, lambda test: alone_command(project, test) or "", root, code)


def level_run(root: Path, name: str, command: str, folder: Path, rerun: bool) -> int:
    """A selected run; with RERUN and its level's `rerun`, failed tests alone (SPEC-0055 rule 9)."""
    areas = proof_areas(root) if rerun else None
    template = (level_of(areas, name) or {}).get("rerun")
    if not template:
        return shell(command, folder)
    import failures  # the ids of the reports (SPEC-0046)

    since = time.time()
    code, _ = captured(command, folder)
    if code == 0:
        return 0
    junit = report_of(areas, name, junit_setting(root))
    reports = report_files(folder, junit, since) if junit else []
    found = dict(failures.failed_tests("", reports))  # never the output: a level reads its report
    # An id comes from a report: quoted, so that it reaches the command as one word.
    return rerun_each(root, found, lambda t: template.replace("{id}", shlex.quote(t)), folder, code)


def rerun_each(
    root: Path, found: dict[str, str], alone: Callable[[str], str], folder: Path, code: int
) -> int:
    """Run ALONE of each failed test in FOLDER; a pass is one strike in ROOT's ledger."""
    import failures
    import flakes

    from config import failures_settings

    if not found:
        say(["project tests: rerun alone: no failed test id was found"])
        return code
    if len(found) > MAX_RERUNS:
        say([f"project tests: rerun alone: {len(found)} failed tests, more than {MAX_RERUNS}"])
        return code
    owner = os.environ.get("AGK_SESSION", "").strip() or flakes.UNASSIGNED
    if not flakes.OWNER.fullmatch(owner):
        owner = flakes.UNASSIGNED
    issues = failures_settings(root)["issues"]
    green = True
    for test, first in found.items():
        if shell(alone(test), folder) != 0:
            say([f"project tests: rerun alone: {test} failed again"])
            green = False
            continue
        try:
            lines = flakes.record_strike(root, test, owner, flakes.utc_today())
        except flakes.Refused as exc:
            say([f"project tests: rerun alone: {test} passed; no strike written: {exc}"])
            green = False
            continue
        strike = lines[0].split(" ")[2]
        sig = failures.signature(test, first)
        action = (
            failures.issue_body(sig, test, []).splitlines()[0]
            if issues
            else "action: none (setting: failures.issues)"
        )
        say(
            [
                f"project tests: rerun alone: {test} passed; strike {strike} recorded in "
                f"{flakes.LEDGER}",
                *(f"project tests: {line.removeprefix('flakes: ')}" for line in lines[1:]),
                f"project tests: failure signature {sig} {test}",
                f"project tests: failure issue: {action}",
            ]
        )
    return 0 if green else (code or 1)


def toml_version(text: str | None) -> str | None:
    """`version` of an agk.toml text, None when absent or unreadable (as check_release reads it)."""
    try:
        value = tomllib.loads(text or "").get("version")
    except tomllib.TOMLDecodeError:
        return None
    return value if isinstance(value, str) else None


def say(lines: list[str]) -> None:
    """Print the lines and append them to the job summary when the runner sets one."""
    for line in lines:
        print(line, flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        try:
            with open(summary, "a", encoding="utf-8") as out:
                out.write("".join(f"{line}\n" for line in lines))
        except OSError:
            print("project tests: the job summary cannot be written (setting: GITHUB_STEP_SUMMARY)")


def version_at(root: Path, ref: str) -> str | None:
    return toml_version(git(root, "show", f"{ref}:agk.toml", check=False) or None)


def plan(root: Path, project: str) -> tuple[list[tuple[str, str, str, str]], list[str]]:
    """The runs (name, command, folder, reason) under `selected`, and the lines said before them."""
    event = os.environ.get("EVENT", "").strip()
    head = [f"project tests: pr_tests selected, event {event or 'unknown'}"]
    if event != EVENT:
        why = f"event {event}" if event else "event unknown"
        return [("full", project, ".", why)], [*head, f"project tests: full ({why})"]
    try:
        base = resolve_base(root, None)
        if base is None:
            raise CheckError("no base")
        mb = merge_base(root, base)
    except CheckError:
        why = "the base does not resolve"
        return [("full", project, ".", why)], [*head, f"project tests: full ({why})"]
    if version_at(root, base) != version_at(root, "HEAD"):
        why = "release: version raised in agk.toml"
        return [("full", project, ".", why)], [*head, f"project tests: full ({why})"]
    refresh(root)
    found = impact(root, mb, "HEAD")
    sets, notes = regression_sets(root, found, proof_areas(root))
    lines = [*head, *text(found), *[n for n in notes if n not in found.map_notes]]
    if any(n.startswith("tests: not run (in no [proof] area)") for n in notes):
        why = "a selected file is in no [proof] area"
        added = [s for s in sets if s[3].startswith(LINK_REASON)]  # a link only adds (rule 7)
        return [("full", project, ".", why), *added], [*lines, f"project tests: full ({why})"]
    if sets and sets[0][0] == "full":
        lines.append(f"project tests: full ({sets[0][3]})")
    else:
        lines.extend(f"project tests: will run {name} in {cwd}" for name, _, cwd, _ in sets)
    return sets, lines


def full_run(root: Path, project: str, command: str, rerun: bool) -> int:
    """The full command; with RERUN its failed tests are rerun alone (brief #670)."""
    if not rerun:
        return shell(command, root)
    code, output = captured(command, root)
    return code if code == 0 else rerun_failed(root, project, output, code)


def linked_runs(root: Path, project: str) -> tuple[list[tuple[str, str, str, str]], list[str]]:
    """Under `full`, what a pull request's links add to the full command (SPEC-0055 rule 7)."""
    table = testing_table(root) or {}
    generated = table.get("map_source") == "generated"
    if not table.get("links") and not generated and not (root / MAP_FILE).is_file():
        return [], []
    runs, lines = plan(root, project)
    added = [r for r in runs if r[3].startswith(LINK_REASON)]
    if added or any(line.startswith(LINK_REASON) for line in lines):
        return added, lines
    return [], [line for line in lines if line in (MAP_STALE, MAP_UNREAD)]


def run_all(root: Path, project: str, runs: list, rerun: bool) -> int:
    """Each run with its line; the first failure ends it, with exit 1."""
    for name, command, cwd, reason in runs:
        started = time.monotonic()
        if name == "full":
            code = full_run(root, project, command, rerun)
        else:
            code = level_run(root, name, command, root / cwd, rerun)
        word = "ok" if code == 0 else "FAIL"
        say([f"project tests: {name} {word} ({time.monotonic() - started:.1f}s): {reason}"])
        if code != 0:
            return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1 or args[:1] not in ([], ["--rerun-alone"], ["--no-rerun-alone"]):
        print(USAGE)
        return 2
    root = repo_root()
    project = str(load_config(root)["project_tests"] or "").strip()
    if not project:
        print(NOTICE)
        return 0
    try:
        mode = pr_tests(root)
        rerun = rerun_alone(root) and args != ["--no-rerun-alone"]
    except CheckError as exc:
        print(f"project tests: {exc}")
        return 1
    if args == ["--rerun-alone"] and not rerun:
        print(NO_SETTING)
        return 1
    if mode == "full":
        command, single = full_command(root, project, root)
        if single:
            print(single, flush=True)
        code = full_run(root, project, command, rerun)
        if code != 0:
            return code
        links, lines = linked_runs(root, project)
        say(lines)
        return run_all(root, project, links, rerun)
    try:
        runs, lines = plan(root, project)
    except CheckError as exc:
        print(f"project tests: {exc}")
        return 1
    say(lines)
    return run_all(root, project, runs, rerun)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CheckError as exc:
        print(f"project tests: {exc}")
        sys.exit(1)
