# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The gate runner (SPEC-0072 rule 3; REQ-079 AC2; brief #1586, ADR-0666). Installed: a verbatim
entry of `kit/manifest.json`, with its step registry `scripts/agk/gates/`; `check_playbooks.py`
runs it once the playbooks pass, so it runs in the `governance` job and `make governance` with no
workflow change (Q-1586-3).

    python3 scripts/agk/run_gates.py [--baseline] [--root DIR]

Composes the playbook of `[delivery] work_type` (or `default.toml` alone when none is declared)
with `check_playbooks.composed` and runs the `step` of each `kind = "check"` gate from its module
under `scripts/agk/gates/`, the step's name with `-` as `_`. Prints one `ok <gate id>` line per
gate that passes and one `FAIL gates: <gate id>: <rule> (path class: <class>)` line per failure,
never a value; a step with no module is one such line naming the gate id. Ends with
`ok gates (<n> check gates)`, or `ok gates (no check gate)`, or exits 1. The steps of the composed
`[architecture]` (`ARCHITECTURE_STEPS`: `layers`) run after the gates under their own name where
they apply (two or more layers), so the kit's own output is unchanged. A step module may hold
`skipped(root)`: a reason it prints as `not run <gate id>: <reason>`, never `ok`, and names in the
last line (`; not run: <ids>`; brief #1588, ADR-0668). Files only: no network,
no hosted scanner, nothing written. From `check_playbooks.py` it prints nothing when no gate is a
check, so that check's output is unchanged there (the kit's own repository's case).
`required_checks` is unchanged: it runs inside `governance`.

The standards packs (SPEC-0072 rule 6; brief #1589, ADR-0669): after the gates, each composed
`[[standards]]` entry whose stack a pack module of `PACKS` serves is run once per module, only when
that module is `on` (its stack chosen in the Accepted stack record). Its steps print `ok standards
<stack>` or `FAIL gates: standards <stack> <step>: <rule> (path class or setting)`; a `lint`,
`format` or `type` step name the module does not hold is refused naming the stack.

The baseline (SPEC-0072 rule 7; brief #1600, ADR-0680): a step that reports per-file counts (a
module's `counts(root, playbook)`, or a pack's tally) is held to `config/agk-baseline/<gate id>.txt`
when that file exists: it passes while no file's count exceeds its line (`ok <id> (baseline)`),
prints `baseline <id>: a count fell in <n> file(s)` when one falls, and otherwise adds one
`SPEC-0072 rule 7` line to its own. In `mode = "adopt"` a missing file is written from today's
tree and the step passes; in `mode = "init"` nothing is written. `--baseline` writes the missing
files and lowers lines, never raising one (the owner's yes on an upgrade, `Q-S0072-5`, and the
next build's lowering commit). Output names counts and path classes, never a file.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import check_playbooks
import playbook_format
from common import repo_root, run, utf8_output
from gates import baseline

NAME = "gates"
REGISTRY = Path(__file__).resolve().parent / "gates"
STEP = re.compile(r"^[a-z][a-z0-9-]*$")
# SPEC-0072 rule 5 (brief #1588, ADR-0668): steps of the composed `[architecture]`, not of a gate;
# each runs, under its own name, only where its `applies(root)` is true (two or more layers).
ARCHITECTURE_STEPS = ("layers",)
# brief #1596 (ADR-0676, amendment 206): the product's bill and licence steps, run the same way
# only where a stack is chosen and its lock is read; a project without one (the kit's) is unchanged.
PRODUCT_STEPS = ("bom", "licences")
PACKS = ("python_pack",)  # pack modules of the registry, imported by name
STEP_KEYS = ("lint", "format", "type")
NO_PACK_STEP = "SPEC-0072 rule 6: a pack step has no implementation (key: standards)"
MISSING = "SPEC-0072 rule 3: the step has no implementation (path class: scripts/agk/gates/)"


def step_module(step: object) -> ModuleType | None:
    """The registry module of a step name, or None when the registry holds none."""
    if not isinstance(step, str) or not STEP.match(step):
        return None
    name = step.replace("-", "_")
    if not (REGISTRY / f"{name}.py").is_file():
        return None
    return importlib.import_module(f"gates.{name}")


def playbook(root: Path) -> Path:
    """The declared playbook, or `default.toml` when none is declared (the kit's own case)."""
    return playbook_format.selected(root) or root / playbook_format.FOLDER / "default.toml"


Row = tuple[bool | None | str, str]  # passed (True, False, None: not run) or NOTE, and the line
NOTE = "note"


def ratchet(root: Path, gate_id: str, found: dict[str, int], failed: list, write: bool) -> list:
    """The rows of a step with per-file counts against its baseline (rule 7); with no baseline
    file, and none written, its own FAILED rows."""
    where = f"(path class: {baseline.CLASS})"
    notes: list[Row] = []
    had = baseline.read(root, gate_id)
    if (had is None and baseline.adopted(root)) or write:
        if baseline.write(root, gate_id, found):
            done = "written" if had is None else "lowered"
            notes.append((NOTE, f"baseline {gate_id}: {done} {where}"))
    base = baseline.read(root, gate_id)
    if base is None:
        return failed
    over, under = baseline.compare(base, found)
    if over:
        return [*failed, (False, f"{gate_id}: {baseline.RULE} {where}"), *notes]
    if under:
        files = "file" if under == 1 else "files"
        notes.append((NOTE, f"baseline {gate_id}: a count fell in {under} {files} {where}"))
    return [(True, f"{gate_id} (baseline)" if failed else gate_id), *notes]


def results(root: Path, write: bool = False) -> list[Row]:
    """(passed, line) for each check gate of the composed playbook, in the composed order; passed
    is None for a step that is not run (`skipped`), and the line gives its reason."""
    path = playbook(root)
    if not path.is_file():
        return []
    gates, _, _ = check_playbooks.composed(path, root)
    data = playbook_format.load(path)
    out: list[Row] = []
    checks = [g for g in gates if g.get("kind") == check_playbooks.CHECK]
    for step in ARCHITECTURE_STEPS + PRODUCT_STEPS:
        module = step_module(step)
        if module is not None and module.applies(root):
            checks.append({"id": step, "step": step})
    for gate in checks:
        module = step_module(gate.get("step"))
        if module is None:
            out.append((False, f"{gate['id']}: {MISSING}"))
            continue
        why = module.skipped(root) if hasattr(module, "skipped") else None
        if why:  # brief #1588 (ADR-0668): a step that cannot read the project is never `ok`
            out.append((None, f"{gate['id']}: {why}"))
            continue
        failed = [x if isinstance(x, tuple) else (module.RULE, x) for x in module.check(root, data)]
        rows: list[Row] = [(False, f"{gate['id']}: {r} (path class: {c})") for r, c in failed]
        if hasattr(module, "counts"):
            rows = ratchet(root, gate["id"], module.counts(root, data), rows, write)
        out += rows or [(True, gate["id"])]
    return out + pack_results(path, root, write)


def pack_results(path: Path, root: Path, write: bool = False) -> list[Row]:
    """(passed, line) for each standards pack that is on, once per pack module (rule 6)."""
    out: list[Row] = []  # main's row type; a pack row is never None
    done: set[str] = set()
    for entry in check_playbooks.standard(path, root)[1]:
        stack = entry.get("stack")
        modules = [importlib.import_module(f"gates.{name}") for name in PACKS]
        module = next((m for m in modules if stack in m.STACKS), None)
        if module is None or module.__name__ in done or not module.on(root):
            continue
        done.add(module.__name__)
        if tuple(entry.get(k) for k in STEP_KEYS) != module.STEP_NAMES:
            out.append((False, f"standards {stack}: {NO_PACK_STEP}"))
            continue
        tally: dict[str, dict[str, int]] = {}
        rows: list[Row] = []
        for step, lines in module.run(root, entry, tally):
            gid = f"standards {stack} {step}"
            failed: list[Row] = [(False, f"{gid}: {ln}") for ln in lines]
            rows += ratchet(root, gid, tally[step], failed, write) if step in tally else failed
        out += [r for r in rows if r[0] is not True]
        if not any(r[0] is False for r in rows):
            out.append((True, f"standards {stack}"))
    return out


def cmd_check(root: Path, quiet: bool = False, write: bool = False) -> int:
    """Print the lines and give the exit code; `quiet` prints nothing when no gate is a check."""
    found = results(root, write)
    if quiet and not found:
        return 0
    words: dict[bool | None | str, str] = {True: "ok ", None: "not run ", NOTE: ""}
    for passed, line in found:
        print(f"{words.get(passed, f'FAIL {NAME}: ')}{line}")
    found = [row for row in found if row[0] != NOTE]
    if any(passed is False for passed, _ in found):
        return 1
    count = len(found)
    idle = [line.split(":", 1)[0] for passed, line in found if passed is None]
    tail = f"; not run: {', '.join(idle)}" if idle else ""
    print(f"ok {NAME} ({count} check gates{tail})" if count else f"ok {NAME} (no check gate)")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    write = "--baseline" in args
    args = [a for a in args if a != "--baseline"]
    root = Path(args[1]) if args[:1] == ["--root"] and len(args) == 2 else None
    if root is None and args:
        print("usage: run_gates.py [--baseline] [--root DIR]", file=sys.stderr)
        return 2
    return run(NAME, lambda: cmd_check(root or repo_root(), write=write))


if __name__ == "__main__":
    sys.exit(main())
