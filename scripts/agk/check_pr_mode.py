"""Declared dependence and the pull-request mode (SPEC-0025 rules 5 and 6).

    python3 check_pr_mode.py [--body FILE] [--states FILE] [--open FILE] [--number N]
    python3 check_pr_mode.py --list-depends --body FILE

`agk.toml` `pr_mode` is `strict` (the default) or `flow`. A body line `Depends-on: #n` fails
in flow mode until #n is a merged pull request or an issue (a brief) closed as completed, read
from the states file, and always in strict mode.
In strict mode a pull request whose author has an older open pull request fails (the lowest number
wins; read from the open pull requests file). Without a file the part that needs it prints a
`skipped` line and passes. Files and git only: no network, no model. Messages name the rule, the
setting or a pull request number, never a value.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError, json_records, pr_mode, repo_root, run

NAME = "pr-mode"
USAGE = (
    "usage: check_pr_mode.py [--body FILE] [--states FILE] [--open FILE] [--number N]\n"
    "       check_pr_mode.py --list-depends --body FILE"
)
DEPENDS = re.compile(r"Depends-on: #(\d+)")
OPTIONS = {"--body", "--states", "--open", "--number"}


def depends_on(body: Path | None) -> list[int]:
    """The numbers of the `Depends-on: #n` lines of the body, in order, once each."""
    if body is None:
        return []
    try:
        text = body.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CheckError("the body file cannot be read") from exc
    found = [int(m.group(1)) for ln in text.splitlines() if (m := DEPENDS.fullmatch(ln.strip()))]
    return list(dict.fromkeys(found))


def unmet(record: dict | None) -> str | None:
    """Why a named number is not yet in, or None when it is (rule 5, brief #282).

    A merged pull request is in, and so is an issue (a brief) closed as completed. A record is an
    issue only when it says `pull_request: false`; one that does not say is read as before, a pull
    request, so the fallback record the workflow writes when a fetch fails is never in.
    """
    if record is None:
        return "is not merged"
    if record.get("merged") is True:
        return None
    kind = record.get("pull_request")
    if kind is True:
        return "is a pull request that is not merged"
    if kind is not False:
        return "is not merged"
    if record.get("state") == "open":
        return "is an open issue"
    reason = record.get("state_reason")
    if record.get("state") == "closed" and reason == "completed":
        return None
    if reason == "not_planned":
        return "is an issue closed as not planned"
    return "is an issue not closed as completed"


def number_of(value: str | None) -> int | None:
    return int(value) if value and value.isdigit() else None


def check(root: Path, opts: dict[str, str]) -> int:
    mode = pr_mode(root)
    named = depends_on(Path(opts["--body"]) if opts.get("--body") else None)
    problems: list[str] = []
    skipped: list[str] = []
    if named and mode == "strict":
        problems.append("rule 6: pr_mode does not allow a Depends-on line")
    elif named and opts.get("--states"):
        states = {
            r["number"]: r
            for r in json_records(Path(opts["--states"]), "states")
            if isinstance(r.get("number"), int)
        }
        problems += [f"rule 5: #{n} {why}" for n in named if (why := unmet(states.get(n)))]
    elif named:
        skipped.append("no states file")
    own = number_of(opts.get("--number"))
    if opts.get("--open"):
        opened = json_records(Path(opts["--open"]), "open pull requests")
        older = sorted(
            r["number"]
            for r in opened
            if isinstance(r.get("number"), int) and own and r["number"] < own
        )
        if mode == "strict" and older:
            problems.append(
                f"rule 6: pr_mode allows one open pull request per author; #{older[0]} is older"
            )
    else:
        skipped.append("no open pull requests file")
    if problems:
        raise CheckError("; ".join(problems))
    print(f"skipped ({'; '.join(skipped)})" if skipped else f"ok {NAME}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    listing = "--list-depends" in args
    rest = [a for a in args if a != "--list-depends"]
    opts = dict(zip(rest[::2], rest[1::2], strict=False))
    if len(rest) % 2 or not set(opts) <= OPTIONS or (listing and set(opts) != {"--body"}):
        print(USAGE)
        return 2
    if listing:
        for n in depends_on(Path(opts["--body"])):
            print(n)
        return 0
    root = repo_root()
    return run(NAME, lambda: check(root, opts))


if __name__ == "__main__":
    sys.exit(main())
