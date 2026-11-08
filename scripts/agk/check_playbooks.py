"""The playbook check (SPEC-0038 rules 1 to 4; REQ-045 AC1 and AC4). Installed: `kit/manifest.json`
lists it in `verbatim`, with the module it imports, `playbook_format.py`.

Checks every `config/playbooks/*.toml` of the repository with `playbook_format.problems` and
prints `ok playbooks (<n> playbooks)`, `ok playbooks (none)` when there is no playbook, or one
`FAIL playbooks:` line per problem, naming the rule and the file and never a value, and exits 1.
It checks the declaration of rule 5 as well (`playbook_format.declaration`, brief #650, ADR-0312):
an unknown `work_type`, or one whose playbook is missing, is one more `FAIL playbooks:` line naming
the setting; with no declaration, or a sound one, the output is unchanged. A step of
`agk-governance` after `check_design.py`. Files only: no network, nothing written.

The composed gates (SPEC-0048 rules 21 and 23; REQ-055 AC8; brief #693): `composed(path, root)`
gives a playbook's gates and evidence, `default`, then each module it names, then its own, each id
or item once at its first place, and the problems of the composition. A gate restated with the
same or a stronger kind and `owner_only` replaces the one held; a restatement as `judgement` of a
`check`, or one that turns `owner_only` from `true` to `false`, keeps the gate held and is one
`FAIL playbooks:` line naming the rule and the key, never a value, as is a module that names
modules of its own.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import playbook_format
from common import repo_root, run

NAME = "playbooks"
CHECK, JUDGEMENT = playbook_format.GATE_KINDS


def _load(path: Path) -> dict[str, Any]:
    """The playbook at `path`, or an empty table when it cannot be read: `problems` reports it."""
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return {}


def _gates(data: dict[str, Any]) -> list[dict[str, Any]]:
    """The gates of a playbook with a string id; `problems` reports any other."""
    found = data.get("gates")
    if not isinstance(found, list):
        return []
    return [g for g in found if isinstance(g, dict) and isinstance(g.get("id"), str)]


def _evidence(data: dict[str, Any]) -> list[str]:
    found = data.get("evidence")
    return [e for e in found if isinstance(e, str)] if isinstance(found, list) else []


def _weakened(new: dict[str, Any], held: dict[str, Any]) -> list[str]:
    """The keys in which `new` is weaker than `held` (SPEC-0048 rule 21)."""
    keys = []
    if new.get("kind") == JUDGEMENT and held.get("kind") == CHECK:
        keys.append("kind")
    if new.get("owner_only") is False and held.get("owner_only") is True:
        keys.append("owner_only")
    return keys


def _layers(path: Path, root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """`default`, then each module, then the playbook; and the problem of a module with modules."""
    folder = root / playbook_format.FOLDER
    base = folder / f"{playbook_format.BASE}.toml"
    layers = [_load(base)] if path.stem != playbook_format.BASE and base.is_file() else []
    named = [_load(folder / f"{name}.toml") for name in playbook_format.modules(path, root)]
    problems = []
    if any(module.get("modules") for module in named):
        rel = f"{playbook_format.FOLDER}/{path.name}"
        problems.append(f"rule 23: {rel}: a playbook in `modules` names modules (key: modules)")
    return [*layers, *named, _load(path)], problems


def composed(path: Path, root: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """SPEC-0048 rules 21 and 23: the composed gates and evidence of the playbook at `path`, and the
    problems of the composition, each naming the rule, the file and the key, never a value."""
    path, root = Path(path), Path(root)
    layers, problems = _layers(path, root)
    rel = f"{playbook_format.FOLDER}/{path.name}"
    gates: dict[str, dict[str, Any]] = {}
    evidence: dict[str, None] = {}
    weak: set[str] = set()
    for layer in layers:
        evidence.update(dict.fromkeys(_evidence(layer)))
        for gate in _gates(layer):
            held = gates.get(gate["id"])
            keys = _weakened(gate, held) if held else []
            weak.update(keys)
            if not keys:
                gates[gate["id"]] = gate
    problems += [f"rule 21: {rel}: a gate is restated weaker (key: {key})" for key in sorted(weak)]
    return list(gates.values()), list(evidence), problems


def cmd_check(root: Path) -> int:
    files = playbook_format.playbooks(root)
    found = [
        line
        for path in files
        for line in playbook_format.problems(path, root) + composed(path, root)[2]
    ]
    found += playbook_format.declaration(root)[1]
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
