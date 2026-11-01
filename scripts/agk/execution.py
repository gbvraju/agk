"""Where a project's heavy checks run, and where the kit recommends they run (brief 441, ADR-0237).

Usage: python3 scripts/agk/execution.py [--json] [--repo OWNER/REPO] [--api-dir DIR]

Standard library only. `execution` in `agk.toml` names where the heavy checks run: `hosted` (the
default, also when absent), `hybrid` (the required light checks on GitHub-hosted runners, the heavy
checks on a pool or locally), `pool` or `local`. This command prints, in one line,

    execution: <set> (recommended: <profile>: <reason>)

from a fixed table: Actions disabled for the repository, or its included minutes used up, gives
`local`; a public repository gives `hosted` (its minutes are not billed); a private repository past
half of its included minutes, or past `minutes_warn`, gives `hybrid`; more than half left, or a
billing reading that is unknown, gives `hosted`, with that reason. With `pool` or `hybrid` set and
no repository variable `AGK_HEAVY_RUNNER`, a second line points to the self-hosted runner guide.

It reads through `minutes.py`'s sources and reading functions (`gh api`, GET only, or recorded
responses with `--api-dir`); it has no API path of its own. It reports only: it changes no workflow
and writes nothing. The variable's value is never printed.

Exit: 0 printed, 1 refused (an invalid setting, or the repository cannot be read), 2 usage.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import execution, minutes_warn, repo_root, run
from metrics import origin_repo
from minutes import HALF, LOCAL_MODE, ApiDir, Gh, billing, reason_of, repo_of

NAME = "execution"
USAGE = "usage: execution.py [--json] [--repo OWNER/REPO] [--api-dir DIR]"
RUNNER_GUIDE = "docs/guides/self-hosted-runner.md"
VARIABLE = "AGK_HEAVY_RUNNER"
NEEDS_RUNNER = ("pool", "hybrid")


def actions_enabled(src: Any) -> bool | None:
    """Whether Actions is enabled for the repository; None when it cannot be read (Q-441-1: an
    unread permission is never taken for a disabled one)."""
    status, data = src.get("permissions", "/repos/{repo}/actions/permissions")
    if status != 200 or not isinstance(data, dict) or not isinstance(data.get("enabled"), bool):
        return None
    return data["enabled"]


def runner_state(src: Any) -> str:
    """`set`, `not set`, or `cannot be read (<reason class>)` for the repository variable."""
    status, _ = src.get("variable", f"/repos/{{repo}}/actions/variables/{VARIABLE}")
    if status == 200:
        return "set"
    if status == 404:
        return "not set"
    return f"cannot be read ({reason_of(status)})"


def recommend(
    repo: dict,
    enabled: bool | None,
    used: int | None,
    included: int | None,
    reason: str | None,
    warn: int,
) -> tuple[str, str]:
    """(profile, reason) from the fixed table of brief #441 answer 2."""
    if enabled is False:
        return "local", f"Actions is disabled for this repository; see {LOCAL_MODE}"
    if repo.get("private") is False:
        return "hosted", "a public repository's minutes are not billed"
    if used is None:
        return "hosted", f"the billing reading is unknown (the token cannot read billing: {reason})"
    if not included:
        return "hosted", (
            "the billing reading is unknown (the plan includes no minutes to compare against)"
        )
    if used >= included:
        return "local", f"the included minutes are used up ({used} of {included}); see {LOCAL_MODE}"
    share = f"{used} of {included} included minutes used ({used * 100 // included}%)"
    if used * 100 >= warn * included:
        return "hybrid", f"{share}, past minutes_warn ({warn}%)"
    if used * 100 >= HALF * included:
        return "hybrid", f"{share}, past half"
    return "hosted", f"{share}, more than half left"


def read(src: Any, setting: str, warn: int, name: str | None) -> dict:
    repo = repo_of(src)
    enabled = actions_enabled(src)
    _, used, included, reason = billing(src, repo.get("owner") or {})
    profile, why = recommend(repo, enabled, used, included, reason, warn)
    runner = None
    if setting in NEEDS_RUNNER:
        runner = {"variable": VARIABLE, "state": runner_state(src), "guide": RUNNER_GUIDE}
    return {
        "execution": setting,
        "recommended": profile,
        "reason": why,
        "repository": name or repo.get("full_name"),
        "private": repo.get("private"),
        "actions_enabled": enabled,
        "used": used,
        "included": included,
        "warn_percent": warn,
        "runner": runner,
    }


def render(data: dict) -> str:
    lines = [
        f"execution: {data['execution']} (recommended: {data['recommended']}: {data['reason']})"
    ]
    runner = data["runner"]
    if runner and runner["state"] != "set":
        verb = "is " if runner["state"] == "not set" else ""
        lines.append(
            f"execution: {data['execution']} runs the heavy checks on a runner named by the "
            f"repository variable {runner['variable']}, which {verb}{runner['state']}; "
            f"see {runner['guide']}"
        )
    return "\n".join(lines) + "\n"


def parse_args(args: list[str]) -> dict | None:
    options: dict = {"json": False, "repo": None, "api": None}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--json" and not options["json"]:
            options["json"] = True
            i += 1
        elif arg in ("--repo", "--api-dir") and i + 1 < len(args):
            options["repo" if arg == "--repo" else "api"] = args[i + 1]
            i += 2
        else:
            return None
    return options


def main(argv: list[str] | None = None) -> int:
    options = parse_args(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        print(USAGE, file=sys.stderr)
        return 2
    root = repo_root()
    setting = execution(root)
    warn = minutes_warn(root)
    if options["api"]:
        src: Any = ApiDir(Path(options["api"]))
        name = options["repo"]
    else:
        name = options["repo"] or origin_repo()
        src = Gh(name)
    data = read(src, setting, warn, name)
    if options["json"]:
        print(json.dumps(data, indent=2))
    else:
        sys.stdout.write(render(data))
    return 0


if __name__ == "__main__":
    sys.exit(run(NAME, main))
