# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `layers` step and the architecture record (brief #1588, ADR-0668; SPEC-0072 rule 5; REQ-079).

    python3 scripts/agk/gates/layers.py [--root DIR] [--write-record]

Reads each `.py` file of a layer of the composed `[architecture]` (`default.toml`, the modules,
then the playbook of `[delivery] work_type`; a file belongs to the first layer whose glob matches
it, paths by forward slash), resolves its `import` and `from` lines, relative ones included, and
fails on one that lands in another layer with no `allow` entry from the first to the second. Each
failure names the rule, both layers and the layer's glob, never a file, a module or a value
(principle 8). `default.toml`'s one `src` layer constrains nothing. With an Accepted stack record
whose runtime is not Python the step is not run (`no reader for <stack>`), never a pass (brief
#1588 `Q-1`). `--write-record` writes `docs/architecture.md` from `kit/templates/architecture.md`
once, and never over a record. Files only: no network. Installed; it imports only installed
modules. The runner's interface (`RULE`, `check`, `skipped`, `applies`) is that of
`scripts/agk/gates/`; `run_gates.py` runs it after the gates, as a step of `[architecture]`.
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path, PurePosixPath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

import check_playbooks  # noqa: E402
import playbook_format  # noqa: E402
from common import utf8_output  # noqa: E402
from impact import matches  # noqa: E402

from gates import pins  # noqa: E402

RULE = "SPEC-0072 rule 5: an import crosses layers in a direction `allow` does not list"
UNREAD = "SPEC-0072 rule 5: a source file of a layer cannot be read"
RECORD = "docs/architecture.md"
TEMPLATE = Path(__file__).resolve().parents[3] / "kit" / "templates" / "architecture.md"
SKIP_DIRS = {"node_modules", "__pycache__", "venv"}
USAGE = "usage: python3 scripts/agk/gates/layers.py [--root DIR] [--write-record]"


def architecture(root: Path) -> tuple[list[tuple[str, list[str]]], set[tuple[str, str]]]:
    """The composed layers as (name, globs) and the allowed (from, to) pairs."""
    path = playbook_format.selected(root) or root / playbook_format.FOLDER / "default.toml"
    if not path.is_file():
        return [], set()
    arch, _, _ = check_playbooks.standard(path, root)
    layers = [
        (str(x.get("name")), [p for p in x.get("paths", []) if isinstance(p, str)])
        for x in arch.get("layers", [])
        if isinstance(x, dict)
    ]
    allow = {
        (str(e.get("from")), str(e.get("to"))) for e in arch.get("allow", []) if isinstance(e, dict)
    }
    return layers, allow


def layer_of(path: str, layers: list[tuple[str, list[str]]]) -> tuple[str, str] | None:
    """(name, glob) of the first layer whose glob matches the forward-slash path."""
    for name, globs in layers:
        for glob in globs:
            if matches(path, glob):
                return name, glob
    return None


def targets(rel: str, tree: ast.AST) -> list[str]:
    """The module paths (`a/b`) a file imports; relative imports from its own package."""
    package = list(PurePosixPath(rel).parent.parts)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [a.name.replace(".", "/") for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = package[: len(package) - node.level + 1] if node.level else []
            if node.level > len(package) + 1:
                continue
            mod = base + (node.module.split(".") if node.module else [])
            out += ["/".join(mod)] if mod else [a.name for a in node.names]
    return out


def module_layer(module: str, layers: list[tuple[str, list[str]]]) -> tuple[str, str] | None:
    for candidate in (f"{module}.py", f"{module}/__init__.py"):
        found = layer_of(candidate, layers)
        if found:
            return found
    return None


def sources(root: Path) -> list[str]:
    out = []
    for folder, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS)
        rel = Path(folder).relative_to(root).as_posix()
        out += [f if rel == "." else f"{rel}/{f}" for f in sorted(files) if f.endswith(".py")]
    return out


def problems(root: Path) -> list[tuple[str, str]]:
    """(rule, path class) of each failure, sorted and once each."""
    layers, allow = architecture(root)
    if len(layers) < 2:
        return []  # one layer constrains nothing (`default.toml`'s `src`)
    found: set[tuple[str, str]] = set()
    for rel in sources(root):
        own = layer_of(rel, layers)
        if own is None:
            continue
        try:
            tree = ast.parse((root / rel).read_bytes())
        except (OSError, SyntaxError, ValueError):
            found.add((UNREAD, own[1]))
            continue
        for module in targets(rel, tree):
            other = module_layer(module, layers)
            if other and other[0] != own[0] and (own[0], other[0]) not in allow:
                found.add((RULE, f"{own[1]}; layers: {own[0]} to {other[0]}"))
    return sorted(found)


def applies(root: Path) -> bool:
    """The runner runs the step only where the architecture has two or more layers."""
    return len(architecture(root)[0]) >= 2


def skipped(root: Path) -> str | None:
    """Brief #1588 `Q-1`: the reason the step is not run, or None when it reads the project."""
    picked = pins.chosen(root)
    if picked is None:
        return None
    runtime = next((p[0] for p in picked[1] if p[0] in pins.STACKS), "python")
    return None if runtime == "python" else f"no reader for {runtime}"


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    """The runner's interface: (rule, path class) of each failure; each names both layers."""
    return problems(root)


def stack_adr(root: Path) -> str:
    files = [
        p for p in root.glob("docs/adr/*.md") if pins.RECORD.match(p.relative_to(root).as_posix())
    ]
    return f"ADR-{files[0].name[:4]}" if len(files) == 1 else "none chosen yet"


def write_record(root: Path) -> int:
    """Rule 5: the foundation writes the record once; it changes only by the project's ADR."""
    work_type = playbook_format.declaration(root)[0]
    if work_type is None:
        print("FAIL layers: SPEC-0072 rule 5: the record needs a work type (setting: work_type)")
        return 1
    target = root / RECORD
    if target.exists():
        print(f"FAIL layers: SPEC-0072 rule 5: the record exists (path class: {RECORD})")
        return 1
    if not TEMPLATE.is_file():
        print("FAIL layers: SPEC-0072 rule 5: the template is missing (path class: kit/templates/)")
        return 1
    layers, allow = architecture(root)
    rows = "\n".join(f"| `{n}` | {', '.join(f'`{g}`' for g in gs)} |" for n, gs in layers)
    ends = "\n".join(f"- `{a}` may import `{b}`" for a, b in sorted(allow)) or "- none"
    text = TEMPLATE.read_text(encoding="utf-8")
    for key, value in {
        "work_type": work_type,
        "layers": rows,
        "allow": ends,
        "stack_adr": stack_adr(root),
    }.items():
        text = text.replace("{{" + key + "}}", value)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"ok layers: wrote {RECORD}")
    return 0


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    write = "--write-record" in args
    rest = [a for a in args if a != "--write-record"]
    if rest and not (len(rest) == 2 and rest[0] == "--root" and rest[1]):
        print(USAGE, file=sys.stderr)
        return 2
    root = Path(rest[1]) if rest else Path.cwd()
    if write:
        return write_record(root)
    reason = skipped(root)
    if reason:
        print(f"layers: not run: {reason}")
        return 0
    found = problems(root)
    for rule, cls in found:
        print(f"FAIL layers: {rule} (path class: {cls})")
    if not found:
        print("ok layers")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
