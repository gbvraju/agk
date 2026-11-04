"""The playbook check (SPEC-0038 rules 1 to 4; REQ-045 AC1 and AC4). Installed: `kit/manifest.json`
lists it in `verbatim`, with the module it imports, `playbook_format.py`.

Checks every `config/playbooks/*.toml` of the repository with `playbook_format.problems` and
prints `ok playbooks (<n> playbooks)`, `ok playbooks (none)` when there is no playbook, or one
`FAIL playbooks:` line per problem, naming the rule and the file and never a value, and exits 1.
A step of `agk-governance` after `check_design.py`. Files only: no network, nothing written.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import playbook_format
from common import repo_root, run

NAME = "playbooks"


def cmd_check(root: Path) -> int:
    files = playbook_format.playbooks(root)
    found = [line for path in files for line in playbook_format.problems(path, root)]
    for line in found:
        print(f"FAIL {NAME}: {line}")
    if found:
        return 1
    print(f"ok {NAME} ({len(files)} playbooks)" if files else f"ok {NAME} (none)")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[1]) if args[:1] == ["--root"] and len(args) == 2 else None
    if root is None and args:
        print("usage: check_playbooks.py [--root DIR]", file=sys.stderr)
        return 2
    return run(NAME, lambda: cmd_check(root or repo_root()))


if __name__ == "__main__":
    sys.exit(main())
