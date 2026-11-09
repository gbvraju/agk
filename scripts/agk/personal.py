"""Personal mode's command (SPEC-0041): the api view, and the confirmation's refusal.

    python3 personal.py api-view DIR [--clone DIR]
    python3 personal.py confirm

`api-view` renders the sidecar's `forge/` and the product's git, read-only, into a new or empty DIR
outside the clone: the files `metrics.ApiDir` reads, so that `facts.py --api-dir DIR`,
`metrics.py --api-dir DIR` and `check_final_clearance.py --comments DIR/comments-<n>.json` read
personal state with no change to their code (rule 7). `confirm` is refused in an agent session, as
`local_mode.py --write` is; the command itself comes in build (g) (rule 8). The other subcommands
come in later builds. Refusals name the rule or the setting, never a value.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import CheckError  # noqa: E402
from facts import BRIEF_LABEL, LABELS, SHADOW_LABEL  # noqa: E402
from forge import FilesForge, dump  # noqa: E402
from local_mode import SESSION_SETTING  # noqa: E402

USAGE = "usage: personal.py api-view DIR [--clone DIR] | personal.py confirm"
OUTSIDE = "the api view is written outside the clone (rule 7)"
NOT_EMPTY = "the api view needs a new or empty folder (rule 7)"
ISSUES = "repos/{{repo}}/issues?state={state}&labels={label}"
NUMBERED = {
    "pulls": ("pull", "comments", "files", "commits"),
    "issues": ("issue", "comments"),
}


def state_helpers() -> tuple:
    """`personal_state.py` is not installed by the kit: a clean refusal, not a traceback."""
    try:
        from personal_state import PROJECTS, agk_home, common_dir, read, registry
    except ImportError:
        raise CheckError(
            "personal mode runs from its own install (path class: scripts/agk/personal_state.py)"
        ) from None
    return PROJECTS, agk_home, common_dir, read, registry


def inside(path: Path, folder: Path) -> bool:
    return path == folder or folder in path.parents


def render(forge: FilesForge, out: Path) -> int:
    """Every name that has an answer; a name without one writes no file (`unknown` to a reader)."""
    wanted = {
        "pulls": "repos/{repo}/pulls?state=closed&sort=updated&direction=desc",
        "pulls-open": "repos/{repo}/pulls?state=open",
        f"issues-{SHADOW_LABEL}": ISSUES.format(state="open", label=SHADOW_LABEL),
    }
    for label in (*LABELS, BRIEF_LABEL):
        wanted[f"issues-{label}"] = ISSUES.format(state="all", label=label)
    for kind, names in NUMBERED.items():
        for number in forge.numbers(kind):
            wanted.update({f"{name}-{number}": "" for name in names})
    written = 0
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, endpoint in wanted.items():
        answer = forge.get(name, endpoint)
        if answer is not None:
            (out / f"{name}.json").write_text(dump(answer), encoding="utf-8")
            written += 1
    return written


def api_view(target: str, clone_arg: str) -> int:
    projects, agk_home, common_dir, read, registry = state_helpers()
    clone = Path(clone_arg)
    out = Path(os.path.realpath(target))
    common = common_dir(clone)
    top = Path(os.path.realpath(read(clone, "rev-parse", "--show-toplevel") or "."))
    if inside(out, top) or inside(out, Path(common)):
        raise CheckError(OUTSIDE)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise CheckError(NOT_EMPTY)
    home = agk_home()
    clones = registry(home)
    if common not in clones:
        raise CheckError("this clone is not attached (rule 3)")
    forge = FilesForge(home / projects / clones[common], clone=clone)
    print(f"api-view: {render(forge, out)} files")
    return 0


def confirm() -> int:
    if os.environ.get(SESSION_SETTING):
        raise CheckError(
            "confirm is refused inside an agent session; a person runs it in their own terminal "
            f"(environment setting: {SESSION_SETTING})"
        )
    print("confirm: this command comes in SPEC-0041 build (g); nothing was written")
    return 1


def parse(args: list[str]) -> dict | None:
    if args == ["confirm"]:
        return {"command": "confirm"}
    if len(args) in (2, 4) and args[0] == "api-view" and not args[1].startswith("-"):
        if len(args) == 4 and args[2] != "--clone":
            return None
        return {"command": "api-view", "dir": args[1], "clone": args[3] if len(args) == 4 else "."}
    return None


def main(argv: list[str] | None = None) -> int:
    options = parse(list(sys.argv[1:] if argv is None else argv))
    if options is None:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        if options["command"] == "confirm":
            return confirm()
        return api_view(options["dir"], options["clone"])
    except CheckError as exc:
        print(f"refused: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
