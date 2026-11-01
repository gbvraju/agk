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

`check_release.py` is kit-only (never installed), so `toml_version` restates its reading of
`version`; a kit test pins the two equal (Q-453-7).
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - the project's own test command, run as the caller
import sys
import time
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, git, load_config, merge_base, proof_areas, repo_root, resolve_base
from impact import impact, pr_tests, text
from prepush import regression_sets

NOTICE = "agk: no project_tests configured; the project runs its own tests"
EVENT = "pull_request"


def shell(command: str, cwd: Path) -> int:
    """Run the project's command with its output shown as it comes, as `sh -c` in agk.mk did."""
    proc = subprocess.run(  # nosec B603 B607 - the project's own test command, run as the caller
        ["sh", "-c", command], cwd=cwd
    )
    return proc.returncode


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
    found = impact(root, mb, "HEAD")
    sets, notes = regression_sets(root, found, proof_areas(root))
    lines = [*head, *text(found), *notes]
    if any(n.startswith("tests: not run (in no [proof] area)") for n in notes):
        why = "a selected file is in no [proof] area"
        return [("full", project, ".", why)], [*lines, f"project tests: full ({why})"]
    if sets and sets[0][0] == "full":
        lines.append(f"project tests: full ({sets[0][3]})")
    else:
        lines.extend(f"project tests: will run {name} in {cwd}" for name, _, cwd, _ in sets)
    return sets, lines


def main() -> int:
    root = repo_root()
    project = str(load_config(root)["project_tests"] or "").strip()
    if not project:
        print(NOTICE)
        return 0
    try:
        mode = pr_tests(root)
    except CheckError as exc:
        print(f"project tests: {exc}")
        return 1
    if mode == "full":
        return shell(project, root)
    try:
        runs, lines = plan(root, project)
    except CheckError as exc:
        print(f"project tests: {exc}")
        return 1
    say(lines)
    for name, command, cwd, reason in runs:
        started = time.monotonic()
        code = shell(command, root / cwd)
        word = "ok" if code == 0 else "FAIL"
        say([f"project tests: {name} {word} ({time.monotonic() - started:.1f}s): {reason}"])
        if code != 0:
            return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CheckError as exc:
        print(f"project tests: {exc}")
        sys.exit(1)
