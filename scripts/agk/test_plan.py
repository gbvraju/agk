"""The test plan: which tests a change will run in proof, and why (brief #325, ADR-0185).

Standard library only. Read-only: it reads git and files and runs nothing else, no test and no
worktree. It prints the plan that `proof.py` runs for the change base..head, built by the same
function (`proof.plan`), so the plan shown is the plan run:

- for each `[proof]` area with added or changed test files: its files, the command line with
  `{files}` filled in exactly as proof fills it, and the folder it runs in;
- the areas with nothing to run;
- the added or changed test files (`test_dirs`, `test_patterns`) that match no area, as "not run by
  proof", so a missing area is visible;
- a `regression` section (brief #373, ADR-0220): the regression tests that the `[testing]` table of
  `agk.toml` selects for the change, each with the rule that chose it, or `full (<reason>)`, then
  the unmapped files (`impact.py`). Without the table it is `regression: full (no [testing] table)`.
  `prepush.py` runs the selected regression tests (brief #417), and `proof.py` runs them only
  with `proof_regression = true` in the `[testing]` table (brief #442, off by default).

Without a `[proof]` table it prints `project_tests` and the test files `test_dirs` and
`test_patterns` select. The base defaults to the merge base with the default branch, as in proof.

Exit: 0 printed, 2 usage or a refused setting, 3 I/O.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, git
from impact import Impact, impact
from impact import text as regression_text
from proof import Failure, Plan, plan, resolve_range

NAME = "test-plan"
USAGE = "usage: test_plan.py [--base REF] [--head REF] [--json] [ROOT]"


class Usage(Exception):
    """A usage error (exit 2)."""


def parse_args(args: list[str]) -> dict:
    options: dict = {"base": None, "head": "HEAD", "json": False, "root": "."}
    positional: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--base", "--head") and i + 1 < len(args):
            options[arg[2:]] = args[i + 1]
            i += 2
        elif arg == "--json":
            options["json"] = True
            i += 1
        elif arg.startswith("--") or positional:
            raise Usage(USAGE)
        else:
            positional.append(arg)
            i += 1
    if positional:
        options["root"] = positional[0]
    return options


def data(shown: Plan, base: str, head: str, found: Impact) -> dict:
    return {
        "regression": found.data(),
        "base": base,
        "head": head,
        "proof_table": shown.table,
        "runs": [
            {"name": r.name, "files": r.files, "command": r.command, "cwd": r.cwd}
            for r in shown.runs
        ],
        "nothing_to_run": shown.idle,
        "not_run_by_proof": shown.outside,
        "deleted": sorted(p for p, s in shown.files.items() if s == "D"),
        "project_tests": None
        if shown.table
        else {"command": shown.command or None, "files": selected(shown)},
    }


def selected(shown: Plan) -> list[str]:
    """The added or changed test files of the plan (deletions left out)."""
    return sorted(p for p, s in shown.files.items() if s != "D")


def why(shown: Plan, name: str) -> str:
    if not shown.table:
        return "selected by test_dirs and test_patterns"
    area = next(a for a in shown.areas or [] if a["name"] == name)
    return f"they match dirs {', '.join(area['dirs'])} and patterns {', '.join(area['patterns'])}"


def text(shown: Plan, base: str, head: str, found: Impact) -> list[str]:
    lines = [f"test plan: base {base[:12]}, head {head[:12]}"]
    if not shown.table:
        lines.append("no [proof] table: proof runs project_tests once, on the base and on the head")
    for run in shown.runs:
        count = len(run.files)
        noun = "test file" if count == 1 else "test files"
        lines.append(f"{run.name}: runs {count} {noun} ({why(shown, run.name)})")
        lines.append(f"  folder: {run.cwd}")
        lines.append(f"  command: {run.command}")
        lines.extend(f"  file: {p}" for p in run.files)
    for name in shown.idle:
        if shown.table:
            lines.append(f"{name}: nothing to run (no added or changed test file is selected)")
            continue
        # Without a table the command and the selected files are always shown (brief #325 answer 1).
        files = selected(shown)
        if not shown.command:
            lines.append(f"{name}: nothing to run (it is not set; setting: project_tests)")
        else:
            lines.append(f"{name}: nothing to run (no added or changed test file is selected)")
        lines.append("  folder: .")
        lines.append(f"  command: {shown.command or 'not set (setting: project_tests)'}")
        lines.extend(f"  file: {p} ({why(shown, name)})" for p in files)
    lines.extend(f"not run by proof (in no [proof] area): {p}" for p in shown.outside)
    lines.extend(
        f"deleted (removed on the base, not run): {p}"
        for p, s in sorted(shown.files.items())
        if s == "D"
    )
    lines.extend(regression_text(found))
    return lines


def main(argv: list[str] | None = None) -> int:
    try:
        options = parse_args(list(sys.argv[1:] if argv is None else argv))
        root = Path(options["root"])
        if git(root, "rev-parse", "--is-inside-work-tree", check=False).strip() != "true":
            raise Failure("ROOT is not a git work tree (path class: root)")
        base, head = resolve_range(root, options["base"], options["head"])
        shown = plan(root, base, head)
        found = impact(root, base, head)
    except Usage as exc:
        print(exc, file=sys.stderr)
        return 2
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}")
        return 2
    except Failure as exc:
        print(f"FAIL {NAME}: {exc}")
        return 3
    except OSError:
        print(f"FAIL {NAME}: an input or output error (path class: root)")
        return 3
    if options["json"]:
        print(json.dumps(data(shown, base, head, found), sort_keys=True))
    else:
        print("\n".join(text(shown, base, head, found)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
