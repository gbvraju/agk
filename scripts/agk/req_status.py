"""A requirement's status follows its evidence (brief #668, ADR-0321, proposed spec amendments 133
to SPEC-0010).

    python3 scripts/agk/req_status.py report [--json] [--req REQ-nnn ...] [ROOT]
    python3 scripts/agk/req_status.py apply [--req REQ-nnn ...] [ROOT]

The proof of a requirement is what SPEC-0010 rule 1 says it is: for every criterion `ACn` of its
`- Acceptance:` line, at least one `REQ-nnn ACn` marker in the test files (`common.parse_acceptance`
and `common.find_ac_markers`, never parsed again). The proof passes when every test file holding one
of those markers passes when its `[proof]` area's own command runs it alone (one run per file,
however many requirements it proves, each within `proof_timeout`). A requirement whose criteria are
not all marked, whose acceptance line has no `ACn`, or whose test files no `[proof]` area runs, has
no proof mapped and is never changed. A `retired` requirement is not read.

`report` prints one line for each requirement whose status disagrees with its evidence, and changes
nothing:

    REQ-nnn planned -> done (proof: <n> tests pass)     (also `in-progress -> done`)
    REQ-nnn done but proof fails (<test file>, ...)
    REQ-nnn proof unknown (<test file> timed out)       (no evidence either way, SPEC-0010 rule 15)
    REQ-nnn: no proof mapped

then one summary line. `apply` does the same and then sets the `- Status:` line of each `-> done`
requirement to `done`, editing no other line; it refuses when `docs/requirements.md` already differs
from the commit in the work tree, so that its edit is the only change. A `done` whose proof fails
is flagged and never edited. `apply` is run in the one pull request the conductor opens for it,
never by a builder in a feature pull request.

Exit 0 when no `done` proof fails and none is unknown; 1 on any `done but proof fails`; 4 when a
proof is unknown and none fails; 2 usage; 3 I/O or a refused setting. The output of the test runs
is never printed or stored.
"""

from __future__ import annotations

import json
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

from common import (
    CheckError,
    ac_markers_for,
    parse_acceptance,
    parse_requirements,
    proof_areas,
    proof_timeout,
    temp_env,
)
from proof import area_command, execute, is_test_file

NAME = "req-status"
PATH = "docs/requirements.md"
USAGE = "usage: req_status.py report|apply [--json] [--req REQ-nnn ...] [ROOT]"
PASS, FAIL, TIMEOUT = "pass", "fail", "timeout"


class Usage(Exception):
    pass


def parse_args(argv: list[str]) -> dict:
    if not argv or argv[0] not in ("report", "apply"):
        raise Usage(USAGE)
    opts: dict = {"command": argv[0], "json": False, "req": [], "root": None}
    args = argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--json" and opts["command"] == "report":
            opts["json"] = True
        elif arg == "--req":
            if i + 1 >= len(args) or args[i + 1].startswith("-"):
                raise Usage("--req needs a requirement id")
            opts["req"].append(args[i + 1])
            i += 1
        elif arg.startswith("-") or opts["root"] is not None:
            raise Usage(USAGE)
        else:
            opts["root"] = arg
        i += 1
    return opts


def git_root(start: Path) -> Path:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise CheckError("not inside a git repository")
    return Path(proc.stdout.strip())


def proof_files(req: dict, markers: list[dict]) -> list[str] | None:
    """The test files of a requirement's proof, or None when a criterion has no marker."""
    ids = list(dict.fromkeys(ac for ac, _ in parse_acceptance(req["acceptance"] or "")))
    if not ids:
        return None
    files: set[str] = set()
    for ac in ids:
        mine = {m["file"] for m in markers if m["req"] == req["id"] and m["ac"] == ac}
        if not mine:
            return None
        files |= mine
    return sorted(files)


def area_of(path: str, areas: list[dict]) -> dict | None:
    return next((a for a in areas if is_test_file(path, a["dirs"], a["patterns"])), None)


def run_file(root: Path, area: dict, path: str, limit: int) -> str:
    code, _, _ = execute(area_command(area, [path]), root / area["cwd"], limit, env=temp_env())
    if code is None:
        return TIMEOUT
    return PASS if code == 0 else FAIL


def evaluate(root: Path, wanted: list[str]) -> tuple[list[dict], int]:
    """One entry per requirement that is not retired (its outcome and the files of its proof),
    and the number of requirements read."""
    path = root / PATH
    if not path.is_file():
        raise CheckError(f"{PATH} is missing (path class: docs/requirements.md)")
    reqs = [r for r in parse_requirements(path.read_text(encoding="utf-8")) if r["status"]]
    if wanted:
        unknown = sorted(set(wanted) - {r["id"] for r in reqs})
        if unknown:
            raise Usage(f"--req names no requirement of {PATH}: {', '.join(unknown)}")
        reqs = [r for r in reqs if r["id"] in wanted]
    markers = ac_markers_for(root)
    areas = proof_areas(root) or []
    limit = proof_timeout(root)
    results: dict[str, str] = {}
    found: list[dict] = []
    for req in reqs:
        if req["status"] == "retired":
            continue
        entry = {"id": req["id"], "status": req["status"], "files": [], "failing": [], "slow": []}
        files = proof_files(req, markers)
        plan = {f: a for f in files or [] if (a := area_of(f, areas)) is not None}
        if not files or len(plan) != len(files):
            found.append({**entry, "outcome": "no-proof"})
            continue
        for file, area in plan.items():
            if file not in results:
                results[file] = run_file(root, area, file, limit)
        entry["files"] = files
        entry["failing"] = [f for f in files if results[f] == FAIL]
        entry["slow"] = [f for f in files if results[f] == TIMEOUT]
        passed = not entry["failing"] and not entry["slow"]
        if req["status"] == "done":
            outcome = (
                "proof-fails" if entry["failing"] else "unknown" if entry["slow"] else "agrees"
            )
        else:
            outcome = "to-done" if passed else "unknown" if not entry["failing"] else "agrees"
        found.append({**entry, "outcome": outcome})
    return found, len(reqs)


def line(entry: dict) -> str | None:
    rid, outcome = entry["id"], entry["outcome"]
    if outcome == "to-done":
        return f"{rid} {entry['status']} -> done (proof: {len(entry['files'])} tests pass)"
    if outcome == "proof-fails":
        return f"{rid} done but proof fails ({', '.join(entry['failing'])})"
    if outcome == "unknown":
        return f"{rid} proof unknown ({', '.join(entry['slow'])} timed out)"
    if outcome == "no-proof":
        return f"{rid}: no proof mapped"
    return None


def summary(found: list[dict], total: int) -> str:
    kinds = ("to-done", "proof-fails", "unknown", "no-proof", "agrees")
    count = {k: sum(e["outcome"] == k for e in found) for k in kinds}
    return (
        f"{NAME}: {count['to-done']} to done, {count['proof-fails']} proof fails, "
        f"{count['unknown']} unknown, {count['no-proof']} no proof mapped, "
        f"{count['agrees']} agree ({total} requirements)"
    )


def exit_code(found: list[dict]) -> int:
    if any(e["outcome"] == "proof-fails" for e in found):
        return 1
    return 4 if any(e["outcome"] == "unknown" for e in found) else 0


def dirty(root: Path) -> bool:
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "status", "--porcelain", "--", PATH],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise CheckError("git status cannot be read (path class: docs/requirements.md)")
    return bool(proc.stdout.strip())


def edit(root: Path, ids: set[str]) -> None:
    """Set the one `- Status:` line of each named requirement to `done`; no other line changes."""
    path = root / PATH
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    current = None
    for n, raw in enumerate(lines):
        header = parse_requirements(raw.rstrip("\r\n"))
        if header:
            current = header[0]["id"]
            continue
        if current in ids and raw.startswith("- Status:"):
            ending = raw[len(raw.rstrip("\r\n")) :]
            lines[n] = "- Status: done" + ending
    path.write_text("".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        opts = parse_args(argv)
        root = git_root(Path(opts["root"] or "."))
        if opts["command"] == "apply" and dirty(root):
            raise Usage(
                f"apply needs {PATH} unchanged in the work tree (path class: docs/requirements.md)"
            )
        found, total = evaluate(root, opts["req"])
    except Usage as exc:
        print(f"{NAME}: {exc}", file=sys.stderr)
        return 2
    except CheckError as exc:
        print(f"FAIL {NAME}: {exc}")
        return 3
    except OSError as exc:
        print(f"FAIL {NAME}: {exc.__class__.__name__} (path class: docs/requirements.md)")
        return 3
    if opts["json"]:
        print(json.dumps({"requirements": found, "total": total}, indent=2, sort_keys=True))
        return exit_code(found)
    for entry in found:
        text = line(entry)
        if text:
            print(text)
    if opts["command"] == "apply":
        moved = [e for e in found if e["outcome"] == "to-done"]
        if moved:
            edit(root, {e["id"] for e in moved})
        for e in moved:
            print(f"edited {e['id']}: {e['status']} -> done")
    print(summary(found, total))
    return exit_code(found)


if __name__ == "__main__":
    sys.exit(main())
