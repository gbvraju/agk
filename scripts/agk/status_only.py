"""Is the head a status-only final commit, so that proof may report success without the suite?

    python3 status_only.py --head SHA [--parent-proof CONCLUSION | --parent-governance CONCLUSION]
        [--base REF] [ROOT]

Prints `skip` when all of these hold, else `run (<reason>)`; it always exits 0 (a usage error
exits 2). The conditions (brief #216 answer 4): the head is one commit after its parent (a single
parent); that commit changes only `- Status:` lines (the shape `check_final_clearance.py`
recognises: modified files, one removed and one added `- Status:` line in each, no mode change);
the `proof` check passed on the parent (`--parent-proof success`, the conclusion that the workflow
read with one GET, because a check never calls the network); and the current tip of the default
branch (`--base`, else `AGK_BASE`) is already in the parent, so that nothing of it is untested. The
same decision serves `governance` (brief #234): `--parent-governance` gives the conclusion of the
full run of governance on the parent, in place of proof's, and only the reason changes. A reason
names the condition, never a file, a line or a sha. Git only: no network, no model.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import git, repo_root, resolve_base

USAGE = (
    "usage: status_only.py --head SHA [--parent-proof CONCLUSION | --parent-governance CONCLUSION]"
    " [--base REF]"
)
STATUS = re.compile(r"[-+]- Status: \S.*")


def changed_lines(root: Path, parent: str, head: str) -> dict[str, list[str]]:
    """File -> its removed and added lines (hunk bodies only) from `parent` to `head`."""
    out = git(root, "diff", "-U0", "--no-color", "--no-ext-diff", parent, head)
    found: dict[str, list[str]] = {}
    current = ""
    in_hunk = False
    for line in out.splitlines():
        if line.startswith("diff --git "):
            current, in_hunk = line.split(" b/", 1)[-1], False
            found[current] = []
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line[:1] in "+-" and current:
            found[current].append(line)
    return found


def only_status_lines(root: Path, parent: str, head: str) -> bool:
    tokens = git(root, "diff", "-z", "--name-status", "--no-renames", parent, head).split("\0")
    statuses = {tokens[i + 1]: tokens[i][:1] for i in range(0, len(tokens) - 1, 2)}
    if not statuses or set(statuses.values()) != {"M"}:
        return False
    if git(root, "diff", "--summary", parent, head).strip():  # a mode change or a new file
        return False
    lines = changed_lines(root, parent, head)
    for path in statuses:
        edit = lines.get(path, [])
        removed = [x for x in edit if x[0] == "-"]
        added = [x for x in edit if x[0] == "+"]
        if len(removed) != 1 or len(added) != 1 or not all(STATUS.fullmatch(x) for x in edit):
            return False
    return True


def decide(root: Path, head: str, parent_proof: str, base: str | None, check: str = "proof") -> str:
    commit = git(root, "rev-parse", "--verify", "-q", f"{head}^{{commit}}", check=False).strip()
    if not commit:
        return "run (the head is not a commit)"
    parents = git(root, "rev-list", "--parents", "-n", "1", commit).split()[1:]
    if len(parents) != 1:
        return "run (the head is not one commit after its parent)"
    parent = parents[0]
    if not only_status_lines(root, parent, commit):
        return "run (the commit changes more than status lines)"
    if parent_proof != "success":
        what = "proof" if check == "proof" else f"{check} in full"
        return f"run ({what} did not pass on the parent)"
    ref = base or resolve_base(root, None)
    if ref is None:
        return "run (no default branch to compare the parent with)"
    # The parent's run tested the parent merged with the default branch as it was. Nothing of the
    # default branch is untested only when its current tip is already in the parent.
    tip = git(root, "rev-parse", "--verify", "-q", f"{ref}^{{commit}}", check=False).strip()
    common = git(root, "merge-base", parent, ref, check=False).strip()
    if not tip or tip != common:
        return "run (the default branch has moved past the parent)"
    return "skip"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root_arg = args.pop() if len(args) % 2 else None
    opts = dict(zip(args[::2], args[1::2], strict=False))
    allowed = {"--head", "--parent-proof", "--parent-governance", "--base"}
    if "--head" not in opts or not set(opts) <= allowed:
        print(USAGE, file=sys.stderr)
        return 2
    if "--parent-proof" in opts and "--parent-governance" in opts:
        print(USAGE, file=sys.stderr)
        return 2
    check = "governance" if "--parent-governance" in opts else "proof"
    parent = opts.get("--parent-proof", opts.get("--parent-governance", ""))
    root = Path(root_arg) if root_arg else repo_root()
    print(decide(root, opts["--head"], parent, opts.get("--base"), check))
    return 0


if __name__ == "__main__":
    sys.exit(main())
