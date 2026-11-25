# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `layers` step and the architecture record (brief #1588, ADR-0668; SPEC-0072 rule 5; REQ-079).

    python3 scripts/agk/gates/layers.py [--root DIR] [--write-record | --draft]

Reads each `.py` file of a layer of the composed `[architecture]` (`default.toml`, the modules,
then the playbook of `[delivery] work_type`; a file belongs to the first layer whose glob matches
it, paths by forward slash), resolves its `import` and `from` lines, relative ones included, and
fails on one that lands in another layer with no `allow` entry from the first to the second. Each
failure names the rule, both layers and the layer's glob, never a file, a module or a value
(principle 8). `default.toml`'s one `src` layer constrains nothing. With an Accepted stack record
whose runtime is not Python the step is not run (`no reader for <stack>`), never a pass (brief
#1588 `Q-1`). `--write-record` writes `docs/architecture.md` from `kit/templates/architecture.md`
once, and never over a record. Brief #1842 (ADR-0767): with `mode = "adopt"` a set of two or more
layers that holds no source file fails (`no source file is in any layer`), held by no baseline, and
`--write-record` refuses it; with any other mode it is `not run`. `--draft` prints the layers of
an adopted tree, its import directions and a `[testing] map`, for the person's yes; it writes
nothing. Files only: no network. Installed; it imports only installed
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
from common import load_config, utf8_output  # noqa: E402
from impact import matches  # noqa: E402

from gates import pins  # noqa: E402

RULE = "SPEC-0072 rule 5: an import crosses layers in a direction `allow` does not list"
UNREAD = "SPEC-0072 rule 5: a source file of a layer cannot be read"
RECORD = "docs/architecture.md"
TEMPLATE = Path(__file__).resolve().parents[3] / "kit" / "templates" / "architecture.md"
SKIP_DIRS = {"node_modules", "__pycache__", "venv"}
USAGE = "usage: python3 scripts/agk/gates/layers.py [--root DIR] [--write-record | --draft]"
EMPTY = "SPEC-0072 rule 5: no source file is in any layer"
KEY = "key: architecture.layers"
NO_FILE = "no source file in any layer yet"
DRAFT = "draft layers"
LEFT_OUT = ("docs", "config")  # with the `test_dirs` and the kit's `lint_paths`


def architecture(root: Path) -> tuple[list[tuple[str, list[str]]], set[tuple[str, str]]]:
    """The composed layers as (name, globs) and the allowed (from, to) pairs."""
    import run_gates  # brief #1666: the one resolver of the gates' playbook

    path = run_gates.playbook(root)
    if path is None or not path.is_file():
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


def findings(root: Path) -> list[tuple[str, str, str]]:
    """(file, rule, path class) of each failure: one per disallowed import, one per unread file."""
    layers, allow = architecture(root)
    if len(layers) < 2:
        return []  # one layer constrains nothing (`default.toml`'s `src`)
    found: list[tuple[str, str, str]] = []
    for rel in sources(root):
        own = layer_of(rel, layers)
        if own is None:
            continue
        try:
            tree = ast.parse((root / rel).read_bytes())
        except (OSError, SyntaxError, ValueError):
            found.append((rel, UNREAD, own[1]))
            continue
        for module in targets(rel, tree):
            other = module_layer(module, layers)
            if other and other[0] != own[0] and (own[0], other[0]) not in allow:
                found.append((rel, RULE, f"{own[1]}; layers: {own[0]} to {other[0]}"))
    return found


def problems(root: Path) -> list[tuple[str, str]]:
    """(rule, path class) of each failure, sorted and once each."""
    return sorted({(rule, cls) for _, rule, cls in findings(root)})


def counts(root: Path, playbook: dict[str, Any]) -> dict[str, int]:
    """The runner's baseline interface (brief #1600, ADR-0680): findings per file."""
    out: dict[str, int] = {}
    for rel, _, _ in findings(root):
        out[rel] = out.get(rel, 0) + 1
    return out


def adopted(root: Path) -> bool:
    """Only `mode = "adopt"` reads as adopt; init, none or another value does not."""
    return load_config(root).get("mode") == "adopt"


def empty(root: Path) -> bool:
    """Brief #1842 answer 3: two or more layers and no source file in any of them."""
    found, _ = architecture(root)
    return len(found) >= 2 and not any(layer_of(rel, found) for rel in sources(root))


def unheld(root: Path) -> bool:
    """The runner's hook: a failure no baseline holds or is written from (it counts no file)."""
    return adopted(root) and empty(root)


def applies(root: Path) -> bool:
    """The runner runs the step only where the architecture has two or more layers."""
    return len(architecture(root)[0]) >= 2


def skipped(root: Path) -> str | None:
    """Brief #1588 `Q-1`: the reason the step is not run, or None when it reads the project;
    brief #1842: outside adopt, a layer set that holds no file is not run, never `ok`."""
    runtime = runtime_of(root)
    if runtime != "python":
        return f"no reader for {runtime}"
    return NO_FILE if empty(root) and not adopted(root) else None


def runtime_of(root: Path) -> str:
    """The Accepted stack record's runtime; `python` with none chosen."""
    picked = pins.chosen(root)
    if picked is None:
        return "python"
    return next((p[0] for p in picked[1] if p[0] in pins.STACKS), "python")


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    """The runner's interface: (rule, path class) of each failure; each names both layers."""
    if unheld(root):
        return [(EMPTY, KEY)]
    return problems(root)


def stack_adr(root: Path) -> str:
    files = [
        p for p in root.glob("docs/adr/*.md") if pins.RECORD.match(p.relative_to(root).as_posix())
    ]
    return f"ADR-{files[0].name[:4]}" if len(files) == 1 else "none chosen yet"


def front_door_services(root: Path) -> list[str]:
    import front_door  # noqa: PLC0415 - only the record writer needs it

    return front_door.chosen_services(root)


def services(root: Path) -> str:
    """Brief #1595 (amendment 204): the chosen option's `External services:` as bullets; the
    diagram draws each, so the written record passes the `architecture-record` step."""
    names = front_door_services(root)
    return "\n".join(f"- {n}: TODO(architect)" for n in names) or "None named by the chosen option."


def write_record(root: Path) -> int:
    """Rule 5: the foundation writes the record once; it changes only by the project's ADR."""
    work_type = playbook_format.declaration(root)[0]
    if work_type is None:
        print("FAIL layers: SPEC-0072 rule 5: the record needs a work type (setting: work_type)")
        return 1
    if adopted(root) and empty(root):
        print(
            "FAIL layers: SPEC-0072 rule 5: the record needs layers that hold the code"
            f" ({KEY}); next: layers.py --draft"
        )
        return 1
    target = root / RECORD
    if target.exists():
        print(f"FAIL layers: SPEC-0072 rule 5: the record exists (path class: {RECORD})")
        return 1
    if not TEMPLATE.is_file():
        print("FAIL layers: SPEC-0072 rule 5: the template is missing (path class: kit/templates/)")
        return 1
    text = TEMPLATE.read_text(encoding="utf-8")
    import front_door  # noqa: PLC0415 - brief #1952: the one tuple the check reads

    if any(f"\n## {name}\n" not in text for name in front_door.QUALITY_SECTIONS):
        print("FAIL layers: SPEC-0072 rule 5: the template lacks a section (path class: kit/templates/)")
        return 1
    layers, allow = architecture(root)
    rows = "\n".join(f"| `{n}` | {', '.join(f'`{g}`' for g in gs)} |" for n, gs in layers)
    ends = "\n".join(f"- `{a}` may import `{b}`" for a, b in sorted(allow)) or "- none"
    for key, value in {
        "work_type": work_type,
        "layers": rows,
        "allow": ends,
        "stack_adr": stack_adr(root),
        "services": services(root),
        "drawn": "\n".join(f"app -> {n}" for n in front_door_services(root)),
    }.items():
        text = text.replace("{{" + key + "}}", value)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"ok layers: wrote {RECORD}")
    import check_protected_changes  # brief #1829 answer 4: the classes the record meets

    print(check_protected_changes.protected_line(root, [RECORD]))
    return 0


# --- brief #1842 (ADR-0767): the layers drafted from an adopted tree ------------------------------


def slug(word: str) -> str:
    out = "-".join(
        x for x in "".join(c if c.isalnum() else "-" for c in word.lower()).split("-") if x
    )
    out = "".join(c for c in out if c.isascii())
    return out if playbook_format.SLUG.match(out) else f"layer-{out}".rstrip("-")


def product_files(root: Path, suffixes: set[str]) -> list[str]:
    """The product's source files: hidden folders, `SKIP_DIRS`, the `test_dirs`, the kit's
    `lint_paths`, `docs/` and `config/` left out; paths by forward slash."""
    cfg = load_config(root)
    tests = [str(d).replace("\\", "/").strip("/") for d in cfg["test_dirs"] if isinstance(d, str)]
    kit = [str(d).strip("/") for d in cfg["lint_paths"] if isinstance(d, str)]
    out = []
    for folder, dirs, files in os.walk(root):
        rel = Path(folder).relative_to(root).as_posix()
        keep = []
        for d in sorted(dirs):
            sub = d if rel == "." else f"{rel}/{d}"
            if d.startswith(".") or d in SKIP_DIRS or sub in (*LEFT_OUT, *tests, *kit):
                continue
            keep.append(d)
        dirs[:] = keep
        out += [
            f if rel == "." else f"{rel}/{f}" for f in sorted(files) if Path(f).suffix in suffixes
        ]
    return out


def split(files: list[str], root: Path) -> tuple[str, list[tuple[str, list[str]]]] | None:
    """The shallowest folder level that splits the files into two or more groups: a level with
    one folder and no loose file is descended. (folder, [(name, paths)]), or None."""
    base = ""
    while True:
        inner = [f[len(base) :] for f in files if f.startswith(base)]
        loose = sorted(f"{base}{f}" for f in inner if "/" not in f)
        folders = sorted({f.split("/", 1)[0] for f in inner if "/" in f})
        if len(folders) + bool(loose) >= 2:
            break
        if loose or not folders:
            return None
        base += f"{folders[0]}/"
    groups = [(base.rstrip("/").rsplit("/", 1)[-1] or root.resolve().name, loose)] if loose else []
    groups += [(name, [f"{base}{name}/**"]) for name in folders]
    out: list[tuple[str, list[str]]] = []
    for name, paths in groups:
        named = slug(name) or "layer"
        taken = {n for n, _ in out}
        n, k = named, 2
        while n in taken:
            n, k = f"{named}-{k}", k + 1
        out.append((n, paths))
    return base, out


def directions(root: Path, files: list[str], drafted: list[tuple[str, list[str]]]) -> list:
    """Each (from, to) a Python import takes today between two drafted layers."""
    ends = set()
    for rel in files:
        own = layer_of(rel, drafted)
        if own is None:
            continue
        try:
            tree = ast.parse((root / rel).read_bytes())
        except (OSError, SyntaxError, ValueError):
            continue
        for module in targets(rel, tree):
            other = module_layer(module, drafted)
            if other and other[0] != own[0]:
                ends.add((own[0], other[0]))
    return sorted(ends)


def toml_text(drafted: list, allow: list, tests: str) -> list[str]:
    """The `[architecture]` and `[testing] map` tables, one map code per layer path; an `allow`
    entry (from, to[, adr]) names its ADR when it has one."""
    q = '"{}"'.format
    lines = ["[architecture]", "layers = ["]
    lines += [
        f"  {{ name = {q(n)}, paths = [{', '.join(q(p) for p in ps)}] }}," for n, ps in drafted
    ]
    lines += ["]", "allow = ["]
    for a, b, *adr in allow:
        tail = f", adr = {q(adr[0])}" if adr and adr[0] else ""
        lines.append(f"  {{ from = {q(a)}, to = {q(b)}{tail} }},")
    lines += ["]", "", "[testing]", "map = ["]
    lines += [f"  {{ code = {q(p)}, tests = {q(tests)} }}," for _, ps in drafted for p in ps]
    return [*lines, "]"]


def draft(root: Path) -> tuple[list[str], tuple[list, list, str] | None]:
    """Answer 1: the lines `--draft` prints and the (layers, allow, test glob) they propose."""
    if load_config(root).get("mode") == "init":
        return [f"{DRAFT}: a new project takes the playbook's layers"], None
    runtime = runtime_of(root)
    suffixes = {".py"}
    if runtime == "node":
        from gates import node_pack  # noqa: PLC0415 - only a Node tree needs its suffixes

        suffixes = set(node_pack.SUFFIXES)
    files = product_files(root, suffixes)
    found = split(files, root)
    if found is None:
        return [f"{DRAFT}: one part only; the playbook's layers are kept"], None
    drafted = found[1]
    allow = directions(root, files, drafted) if runtime == "python" else []
    dirs = [str(d).replace("\\", "/").strip("/") for d in load_config(root)["test_dirs"]]
    tests = f"{dirs[0]}/**" if dirs and isinstance(dirs[0], str) and dirs[0] else "tests/**"
    head = [f"{DRAFT}: proposal only; a person confirms it"]
    if runtime != "python":
        head.append(f"{DRAFT}: no reader for {runtime}")
    return [*head, *toml_text(drafted, allow, tests)], (drafted, allow, tests)


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    write = "--write-record" in args
    drafting = "--draft" in args
    rest = [a for a in args if a not in ("--write-record", "--draft")]
    bad = write and drafting or len(args) - len(rest) > 1
    if bad or rest and not (len(rest) == 2 and rest[0] == "--root" and rest[1]):
        print(USAGE, file=sys.stderr)
        return 2
    root = Path(rest[1]) if rest else Path.cwd()
    if write:
        return write_record(root)
    if drafting:
        print("\n".join(draft(root)[0]))
        return 0
    import run_gates  # brief #1666: no playbook found is `not run`, never `ok`

    reason = run_gates.missing(root) or skipped(root)
    if reason:
        print(f"layers: not run: {reason}")
        return 0
    found = check(root, {})
    for rule, cls in found:
        print(f"FAIL layers: {rule} {run_gates.where(cls)}")
    if not found:
        print("ok layers")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
