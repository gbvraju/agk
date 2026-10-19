"""agk playbook: the architect's start-up check and the brief skeleton (SPEC-0013 rules 7 and 16).

Usage:
    python3 playbook.py architect [--root DIR]
    python3 playbook.py brief --kind overnight|day --branch-prefix PREFIX [--repo O/R]
                              [--ref REF] [--date D] [--root DIR]

Kit-only (never installed). `architect` prints how to start the role and checks, read-only, that
`agk.toml` is present, that `gh` is logged in and which branch is the default. `brief` prints a
brief skeleton from `kit/templates/playbook/` in which the next requirement, ADR and spec numbers
are read from `origin/<default branch>` (`common.next_free_ids`), the repository and the default
branch come from `origin` and `agk.toml`, and no pull request number is written in advance.
Nothing is written.
"""

from __future__ import annotations

import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from datetime import UTC, datetime
from pathlib import Path

from common import CheckError, load_config, next_free_ids
from doctor import origin_repo

KIT = Path(__file__).resolve().parents[2]
TEMPLATES = KIT / "kit" / "templates" / "playbook"
USAGE = (
    "usage: playbook.py architect [--root DIR] | brief --kind overnight|day --branch-prefix P "
    "[--repo O/R] [--ref REF] [--date D] [--root DIR]"
)
PREFIX = re.compile(r"^[a-z0-9][a-z0-9-]*(/[a-z0-9][a-z0-9-]*)*$")
FLAGS = ("--root", "--kind", "--branch-prefix", "--repo", "--ref", "--date")


def cmd_architect(root: Path) -> int:
    print(
        "Start the architect role from the repository root with:\n\n    claude --agent architect\n"
    )
    config = root / "agk.toml"
    missing = "missing (run /agk:init or /agk:adopt first)"
    print(f"agk.toml: {'present' if config.is_file() else missing}")
    try:
        gh = subprocess.run(  # nosec B603 B607 - fixed argument list, read-only, no shell
            ["gh", "auth", "status"], capture_output=True, text=True
        ).returncode
        print(f"gh: {'logged in' if gh == 0 else 'not logged in or not working'}")
    except OSError:
        print("gh: not installed")
    if config.is_file():
        print(f"default branch: {load_config(root)['default_branch']}")
    print("The role file is .claude/agents/architect.md;")
    print("its guard is .claude/hooks/architect_guard.py.")
    return 0 if config.is_file() else 1


def cmd_brief(root: Path, opts: dict[str, str]) -> int:
    kind = opts.get("kind")
    prefix = opts.get("branch-prefix", "")
    if kind not in ("overnight", "day") or not PREFIX.match(prefix):
        raise CheckError("usage: --kind overnight|day and --branch-prefix like 'day-14' (rule 16)")
    branch = load_config(root)["default_branch"]
    ids = next_free_ids(root, opts.get("ref") or f"origin/{branch}")
    repo = opts.get("repo") or origin_repo(root)
    if not repo:
        raise CheckError("repository unknown; pass --repo OWNER/REPO (path class: git remote)")
    values = {
        "repo": repo,
        "default_branch": branch,
        "next_req": ids["req"],
        "next_adr": f"ADR-{ids['adr']}",
        "next_spec": f"SPEC-{ids['spec']}",
        "branch_prefix": prefix,
        "date": opts.get("date") or datetime.now(UTC).date().isoformat(),
    }
    text = (TEMPLATES / f"brief-{kind}.md").read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    sys.stdout.write(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in ("architect", "brief"):
        print(USAGE, file=sys.stderr)
        return 2
    opts: dict[str, str] = {}
    it = iter(args[1:])
    for arg in it:
        value = next(it, None)
        if arg not in FLAGS or value is None:
            print(USAGE, file=sys.stderr)
            return 2
        opts[arg[2:]] = value
    root = Path(opts.get("root", "."))
    try:
        if args[0] == "architect":
            return cmd_architect(root)
        return cmd_brief(root, opts)
    except CheckError as exc:
        print(f"FAIL playbook: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
