# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The gate runner (SPEC-0072 rule 3; REQ-079 AC2; brief #1586, ADR-0666). Installed: a verbatim
entry of `kit/manifest.json`, with its step registry `scripts/agk/gates/`; `check_playbooks.py`
runs it once the playbooks pass, so it runs in the `governance` job and `make governance` with no
workflow change (Q-1586-3).

    python3 scripts/agk/run_gates.py [--root DIR]

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

NAME = "gates"
REGISTRY = Path(__file__).resolve().parent / "gates"
STEP = re.compile(r"^[a-z][a-z0-9-]*$")
# SPEC-0072 rule 5 (brief #1588, ADR-0668): steps of the composed `[architecture]`, not of a gate;
# each runs, under its own name, only where its `applies(root)` is true (two or more layers).
ARCHITECTURE_STEPS = ("layers",)
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


def results(root: Path) -> list[tuple[bool | None, str]]:
    """(passed, line) for each check gate of the composed playbook, in the composed order; passed
    is None for a step that is not run (`skipped`), and the line gives its reason."""
    path = playbook(root)
    if not path.is_file():
        return []
    gates, _, _ = check_playbooks.composed(path, root)
    data = playbook_format.load(path)
    out: list[tuple[bool | None, str]] = []
    checks = [g for g in gates if g.get("kind") == check_playbooks.CHECK]
    for step in ARCHITECTURE_STEPS:
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
        out += [(False, f"{gate['id']}: {rule} (path class: {cls})") for rule, cls in failed]
        if not failed:
            out.append((True, gate["id"]))
    return out


def cmd_check(root: Path, quiet: bool = False) -> int:
    """Print the lines and give the exit code; \`quiet\` prints nothing when no gate is a check."""
    found = results(root)
    if quiet and not found:
        return 0
    for passed, line in found:
        word = {True: "ok ", None: "not run "}.get(passed, f"FAIL {NAME}: ")
        print(f"{word}{line}")
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
    root = Path(args[1]) if args[:1] == ["--root"] and len(args) == 2 else None
    if root is None and args:
        print("usage: run_gates.py [--root DIR]", file=sys.stderr)
        return 2
    return run(NAME, lambda: cmd_check(root or repo_root()))


if __name__ == "__main__":
    sys.exit(main())
