# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
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

The composed standard part (SPEC-0072 rule 2; REQ-079 AC1; brief #1585, ADR-0665):
`standard(path, root)` gives the composed `[architecture]` (the last one declared), the composed
`[[standards]]` and the problems. A weaker restatement of one of the eight enterprise gates names
its fixed id; an `allow` entry that a project's own (derived) playbook adds without an `adr` whose
file is under `docs/adr/` is refused naming the key `allow`; a pack restated for the same stack that
drops a held rule code is refused naming the key `standards.rules`. A stack of
`config/stack-signals.toml` with no `[[standards]]` entry in any playbook is one `warn playbooks:`
line on stderr, never a failure.

The gate runner (SPEC-0072 rule 3; REQ-079 AC2; brief #1586, ADR-0666): once the playbooks pass,
the check runs `run_gates.py` in the same process, so every check gate's step runs in the step
`check_playbooks` of the `governance` job and in `make governance` with no workflow change
(Q-1586-3), and its exit code is the runner's; with no check gate it adds no line.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # isolated mode (-I) leaves it off

import playbook_format
from common import repo_root, run, utf8_output

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
    base = playbook_format.default_playbook(root)  # brief #1666: the project's, else the plugin's
    layers = [_load(base)] if path.stem != playbook_format.BASE and base is not None else []
    named = [_load(playbook_format.path(root, n)) for n in playbook_format.modules(path, root)]
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
            # SPEC-0072 rule 2: the eight enterprise ids are the kit's own names, never a value
            named = gate["id"] in playbook_format.ENTERPRISE
            prefix = f"gate: {gate['id']}, " if named else ""
            weak.update(f"{prefix}key: {key}" for key in keys)
            if not keys:
                gates[gate["id"]] = gate
    problems += [f"rule 21: {rel}: a gate is restated weaker ({key})" for key in sorted(weak)]
    return list(gates.values()), list(evidence), problems


def _added_without_adr(layer: dict[str, Any], held: set[tuple[Any, Any]], root: Path) -> bool:
    """A project's own playbook adds an `allow` entry that names no ADR file of the project."""
    name = layer.get("work_type")
    if not isinstance(name, str) or not playbook_format.is_derived(name, root):
        return False
    allow = layer["architecture"].get("allow", [])
    for entry in allow if isinstance(allow, list) else []:
        if not isinstance(entry, dict) or (entry.get("from"), entry.get("to")) in held:
            continue
        adr = entry.get("adr")
        number = adr[4:] if isinstance(adr, str) and playbook_format.ADR_ID.match(adr) else None
        if number is None or not list((root / "docs" / "adr").glob(f"{number}-*.md")):
            return True
    return False


def _codes(entry: dict[str, Any]) -> set[str]:
    rules = entry.get("rules")
    codes = rules.get("codes") if isinstance(rules, dict) else None
    return {c for c in codes if isinstance(c, str)} if isinstance(codes, list) else set()


def standard(path: Path, root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """SPEC-0072 rule 2: the composed `[architecture]` and `[[standards]]` of the playbook at
    `path`, and the problems of their composition, naming the rule, the file and the key."""
    path, root = Path(path), Path(root)
    layers, _ = _layers(path, root)
    rel = f"{playbook_format.FOLDER}/{path.name}"
    architecture: dict[str, Any] = {}
    packs: dict[str, dict[str, Any]] = {}
    keys: set[str] = set()
    for layer in layers:
        own = layer.get("architecture")
        if isinstance(own, dict):
            held = {(e.get("from"), e.get("to")) for e in architecture.get("allow", [])}
            if _added_without_adr(layer, held, root):
                keys.add("an `allow` entry is added without an ADR in the project (key: allow)")
            architecture = own
        found = layer.get("standards")
        for entry in found if isinstance(found, list) else []:
            stack = entry.get("stack") if isinstance(entry, dict) else None
            if not isinstance(stack, str):
                continue
            if stack in packs and not _codes(packs[stack]) <= _codes(entry):
                keys.add("a pack's `rules` drops a rule code (key: standards.rules)")
            packs[stack] = entry
    problems = [f"{playbook_format.SPEC72}: {rel}: {key}" for key in sorted(keys)]
    return architecture, list(packs.values()), problems


def findings(root: Path, files: list[Path] | None = None) -> list[str]:
    """The problems of the check: the given playbooks, or all of them, and the declaration."""
    paths = playbook_format.playbooks(root) if files is None else files
    found = [
        line
        for path in paths
        for line in playbook_format.problems(path, root)
        + composed(path, root)[2]
        + standard(path, root)[2]
    ]
    return found + playbook_format.declaration(root)[1]


def cmd_check(root: Path) -> int:
    files = playbook_format.playbooks(root)
    chosen = playbook_format.selected(root)  # brief #1666: a clean project selects the plugin's
    if chosen is not None and chosen not in files:
        files.append(chosen)
    found = findings(root, files)
    for line in found:
        print(f"FAIL {NAME}: {line}")
    if found:
        return 1
    known = playbook_format.stacks(root) or []
    packed = {e.get("stack") for path in files for e in standard(path, root)[1]}
    missing = [name for name in known if name not in packed]
    if missing:
        print(
            f"warn {NAME}: {len(missing)} stacks have no [[standards]] entry in any playbook: "
            "no pack for them yet (SPEC-0072 rule 2)",
            file=sys.stderr,
        )
    print(f"ok {NAME} ({len(files)} playbooks)" if files else f"ok {NAME} (none)")
    import run_gates  # here: the runner imports this module

    return run_gates.cmd_check(root, quiet=True)


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[1]) if args[:1] == ["--root"] and len(args) == 2 else None
    if root is None and args:
        print("usage: check_playbooks.py [--root DIR]", file=sys.stderr)
        return 2
    return run(NAME, lambda: cmd_check(root or repo_root()))


if __name__ == "__main__":
    sys.exit(main())
