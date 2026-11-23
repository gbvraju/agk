# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The Node standards pack (SPEC-0072 rules 6 and 8; REQ-079; briefs #1764 and #1766, ADR-0739
and ADR-0740).

`run_gates.py` runs it for the `node` entry of `[[standards]]`, only when the one Accepted stack
record chose a Node runtime (`pins.chosen`) and the product has a `package.json`. Over the product
`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` and `.cjs` files that `project_lint_paths` names (unset: the
paths of `[architecture] layers`, as for Python), less hidden, `node_modules/`, build folders and
the kit's own `lint_paths`, it runs these steps:

- `floor` (rule 8): `eslint --print-config <file>` shows every rule id of `rules.codes` at `error`
  or `warn`, never `off` or absent, else it names each missing id;
- `node-lint`: `eslint --max-warnings 0` (a "File ignored" notice of the config's own `ignores` is
  not counted);
- `node-format`: `prettier --check --end-of-line auto --config-precedence file-override`: each
  file keeps its own line end unless the project's configuration sets one (brief #1839);
- `type-floor` (rule 8, brief #1766): `tsconfig.json`, read as JSON with comments through its
  `extends` chain inside the product (a package base from `node_modules/` when installed, else
  skipped) and each config of its `references`, sets `strict` and leaves `noImplicitAny` and
  `strictNullChecks` on; each option that is not is named, never its value;
- `node-type`: `tsc --noEmit -p <config>` for the root config and each referenced one; a failure
  names the compiler's `TS<n>` code and the path class.

A product with no `.ts` or `.tsx` file skips both type steps and says so in one note.
Each tool is the product's own pinned copy in `node_modules/.bin/` (its exact `devDependencies`,
which the pins gate holds), run with an argument list and never a shell, `npx` or a download. A
tool that is missing fails naming the tool, the setting and `npm ci`, never a version. A failure
names the rule id (or the format) and the path class, never a file name or a value (principle 8).
With a `tally` dict, `run` fills `{step: {file: count}}` for `lint`, `format` and `type` (rule 7),
and for `floor` and `type-floor` the count of their lines per configuration read (the entry's
`config`; each compiler config), an unreadable one counting 1 (brief #1837, ADR-0766). While that
floor is held for an unreadable configuration the runner does not run `NEEDS_CONFIG` (`lint`).
With no product file in scope no step runs: `run` returns `(NO_FILE, [])`.
"""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

from common import CheckError, load_config  # noqa: E402

from config import PROJECT_LINT  # noqa: E402

from . import pins  # noqa: E402
from .python_pack import NO_FILE, patterns  # noqa: E402,F401 - the one reading of the globs

STACKS = ("node",)
STEP_NAMES = ("node-lint", "node-format", "node-type")
RULE = "SPEC-0072 rule 6"
FLOOR = "SPEC-0072 rule 8"
INSTALL = "npm ci"
SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
SKIP = {"node_modules", "build", "dist", "out", "coverage", "vendor", "third_party"}
TOOLS = (("eslint", "standards.rules"), ("prettier", "standards.format"))
TYPED = {".ts", ".tsx"}
TSCONFIG = "tsconfig.json"
STRICT_OFF = ("noImplicitAny", "strictNullChecks")  # each on under `strict`; `false` weakens it
TSC_LINE = re.compile(r"^(?:(.+?)\(\d+,\d+\): )?error (TS\d+):")
SKIPPED = "the type step is skipped: no TypeScript file"
RULE_ID = re.compile(r"^(?:@?[a-z0-9-]+/)?[a-z][a-z0-9-]*$")
IGNORED = "File ignored"
OFF = ("off", 0)
UNREADABLE = "the pack's configuration is unreadable"
NEEDS_CONFIG = ("lint",)  # brief #1837: not run while the floor holds an unreadable configuration
CONFIG_HELD = "the pack's configuration is held (setting: standards.config)"
# Brief #1839, ADR-0769: each file keeps its own line end, as `ruff format`'s `auto` does, unless
# the project's own prettier configuration or `.editorconfig` sets one.
FORMAT_FLAGS = ("--check", "--end-of-line", "auto", "--config-precedence", "file-override")

Tally = dict[str, int]


def on(root: Path) -> bool:
    """The pack runs only when the Accepted stack record chose Node and a `package.json` exists."""
    found = pins.chosen(Path(root))
    node = found is not None and found[0] == pins.STACKS["node"]
    return node and (Path(root) / "package.json").is_file()


def files(root: Path, globs: list[str]) -> list[tuple[str, str]]:
    """(relative path, the glob it fell under) of each product source file, first glob wins."""
    kit = [p.strip("/") for p in load_config(root)["lint_paths"] if isinstance(p, str)]
    seen: dict[str, str] = {}
    for glob in globs:
        for hit in sorted(root.glob(glob.replace("\\", "/"))):
            for path in sorted(hit.rglob("*")) if hit.is_dir() else [hit]:
                rel = path.relative_to(root).as_posix()
                parts = rel.split("/")
                hidden = any(p.startswith(".") or p in SKIP for p in parts[:-1])
                if path.suffix not in SUFFIXES or not path.is_file() or hidden:
                    continue
                if any(rel == k or rel.startswith(k + "/") for k in kit):
                    continue
                seen.setdefault(rel, glob)
    return sorted(seen.items())


def tool(root: Path, name: str) -> Path | None:
    """The product's own copy of the tool, or None."""
    for suffix in (".cmd", "") if os.name == "nt" else ("",):
        path = root / "node_modules" / ".bin" / f"{name}{suffix}"
        if path.is_file():
            return path
    return None


def _run(root: Path, name: str, argv: list[str]) -> subprocess.CompletedProcess:
    exe = tool(root, name)
    return subprocess.run(  # nosec B603 - the product's pinned tool, fixed argument list, no shell
        [str(exe), *argv], cwd=root, capture_output=True, text=True, check=False
    )


def _on(value: object) -> bool:
    level = value[0] if isinstance(value, list) and value else value
    return level not in OFF and level not in ("0",) and level is not None


def floor(root: Path, entry: dict[str, Any], found: list[tuple[str, str]]) -> list[str]:
    """Rule 8: each pinned rule id that the resolved configuration leaves off or absent."""
    rules = None
    for rel, _ in found[:20]:  # a file the config ignores resolves to no config; try the next
        proc = _run(root, "eslint", ["--print-config", rel])
        try:
            data = json.loads(proc.stdout) if proc.returncode == 0 else None
        except ValueError:
            data = None
        if isinstance(data, dict) and isinstance(data.get("rules"), dict):
            rules = data["rules"]
            break
    if rules is None:
        return [f"{FLOOR}: {UNREADABLE} (setting: standards.config)"]
    out = []
    for code in entry.get("rules", {}).get("codes", []):
        if not _on(rules.get(code, "off")):
            shown = code if isinstance(code, str) and RULE_ID.match(code) else "of the pack"
            out.append(
                f"{FLOOR}: the configuration does not enable the pack's rule {shown} "
                "(setting: standards.config)"
            )
    return out


def _count(tally: Tally | None, rel: str) -> None:
    if tally is not None:
        tally[rel] = tally.get(rel, 0) + 1


def _rel(root: Path, name: str) -> str:
    path = Path(name.replace("\\", "/"))
    path = (root / path if not path.is_absolute() else path).resolve()
    base = root.resolve()
    return path.relative_to(base).as_posix() if path.is_relative_to(base) else ""


def lint(root: Path, found: list[tuple[str, str]], tally: Tally | None = None) -> list[str]:
    """ESLint's JSON findings as (rule, path class) lines; a run that did not report fails."""
    argv = ["--max-warnings", "0", "--format", "json", *[r for r, _ in found]]
    proc = _run(root, "eslint", argv)
    if proc.returncode == 0:
        return []
    try:
        items = json.loads(proc.stdout) if proc.returncode == 1 else None
    except ValueError:
        items = None
    if not isinstance(items, list):
        return [f"{RULE}: the lint tool did not run (setting: standards.lint)"]
    where, out = dict(found), set()
    for item in items:
        if not isinstance(item, dict):
            continue
        rel = _rel(root, str(item.get("filePath", "")))
        for msg in item.get("messages") or []:
            code = msg.get("ruleId") if isinstance(msg, dict) else None
            if code is None and str(msg.get("message", "")).startswith(IGNORED):
                continue
            _count(tally, rel or "product code")
            shown = code if isinstance(code, str) and RULE_ID.match(code) else "syntax"
            out.add(f"{RULE}: lint rule {shown} (path class: {where.get(rel, 'product code')})")
    return sorted(out)


def format_check(root: Path, found: list[tuple[str, str]], tally: Tally | None = None) -> list[str]:
    """`prettier --check`: exit 1 lists the files that are not formatted; any other exit fails."""
    proc = _run(root, "prettier", [*FORMAT_FLAGS, *[r for r, _ in found]])
    if proc.returncode == 0:
        return []
    where, out = dict(found), set()
    for ln in (proc.stdout + proc.stderr).splitlines():
        rel = ln.removeprefix("[warn] ").strip().replace("\\", "/")
        if ln.startswith("[warn] ") and rel in where:
            _count(tally, rel)
            out.add(f"{RULE}: the file is not formatted, prettier (path class: {where[rel]})")
    if proc.returncode != 1 or not out:
        return [f"{RULE}: the format tool did not run (setting: standards.format)"]
    return sorted(out)


def _jsonc(path: Path) -> dict[str, Any] | None:
    """A tsconfig file read as JSON with comments and trailing commas, or None."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    strings = r'"(?:\\.|[^"\\])*"'
    text = re.sub(
        strings + r"|//[^\n]*|/\*.*?\*/",
        lambda m: m.group(0) if m.group(0)[0] == '"' else "",
        text,
        flags=re.S,
    )
    text = re.sub(strings + r"|,(\s*[}\]])", lambda m: m.group(1) or m.group(0), text)
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _base(root: Path, here: Path, spec: str) -> Path | None:
    """The file an `extends` names, inside the product, or None (absent: the own file alone)."""
    if spec.startswith("."):
        tries = [here.parent / spec, here.parent / f"{spec}.json"]
    else:
        mod = root / "node_modules" / spec
        tries = [mod, mod.with_name(mod.name + ".json"), mod / TSCONFIG]
    base = root.resolve()
    for path in tries:
        if path.is_file() and path.resolve().is_relative_to(base):
            return path
    return None


def options(root: Path, path: Path, seen: frozenset[Path] = frozenset()) -> dict[str, Any] | None:
    """The `compilerOptions` of PATH merged over its `extends` chain (later wins), or None."""
    data = _jsonc(path)
    if data is None or path.resolve() in seen:
        return None
    merged: dict[str, Any] = {}
    chain = data.get("extends")
    for spec in chain if isinstance(chain, list) else [chain] if chain else []:
        found = _base(root, path, spec) if isinstance(spec, str) else None
        merged.update((options(root, found, seen | {path.resolve()}) or {}) if found else {})
    own = data.get("compilerOptions")
    merged.update(own if isinstance(own, dict) else {})
    return merged


def configs(root: Path) -> list[tuple[Path, str]]:
    """(config, path class) of the root `tsconfig.json` and each config its `references` name."""
    top = root / TSCONFIG
    out = [(top, TSCONFIG)]
    refs = (_jsonc(top) or {}).get("references")
    for ref in refs if isinstance(refs, list) else []:
        rel = ref.get("path") if isinstance(ref, dict) else None
        path = root / rel if isinstance(rel, str) else None
        path = path / TSCONFIG if path is not None and path.is_dir() else path
        if path is not None and path.resolve().is_relative_to(root.resolve()):
            out.append((path, f"{TSCONFIG} references"))
    return out


def type_floor(root: Path, tally: Tally | None = None) -> list[str]:
    """Rule 8: each compiler option of each config that is not at strict, named, never a value;
    TALLY gets the count per config (brief #1837)."""
    tally = {} if tally is None else tally
    if not (root / TSCONFIG).is_file():
        tally[TSCONFIG] = 1
        return [f"{FLOOR}: the compiler configuration is missing (path class: {TSCONFIG})"]
    out = []
    for path, cls in configs(root):
        opts = options(root, path)
        rel = path.relative_to(root).as_posix()
        if opts is None:
            tally[rel] = 1
            out.append(f"{FLOOR}: the compiler configuration is unreadable (path class: {cls})")
            continue
        weak = ([] if opts.get("strict") is True else ["strict"]) + [
            o for o in STRICT_OFF if opts.get(o) is False
        ]
        if weak:
            tally[rel] = len(weak)
        out += [
            f"{FLOOR}: the configuration weakens the compiler option {o} (path class: {cls})"
            for o in weak
        ]
    return sorted(set(out))


def type_check(root: Path, found: list[tuple[str, str]], tally: Tally | None = None) -> list[str]:
    """`tsc --noEmit -p <config>` per config: each error as (TS code, path class)."""
    where, out = dict(found), set()
    for path, cls in configs(root) if (root / TSCONFIG).is_file() else []:
        argv = ["--noEmit", "--pretty", "false", "-p", path.relative_to(root).as_posix()]
        proc = _run(root, "tsc", argv)
        if proc.returncode == 0:
            continue
        hits = [m for m in map(TSC_LINE.match, proc.stdout.splitlines()) if m]
        for m in hits:
            rel = _rel(root, m.group(1)) if m.group(1) else ""
            _count(tally, rel or cls)
            out.add(f"{RULE}: type rule {m.group(2)} (path class: {where.get(rel) or cls})")
        if not hits:
            out.add(f"{RULE}: the type tool did not run (setting: standards.type)")
    return sorted(out)


def run(
    root: Path, entry: dict[str, Any], tally: dict[str, Tally] | None = None
) -> list[tuple[str, list[str]]]:
    """(step, failure lines) for the floors and the three steps, in order (`note` lines are
    information, not failures); TALLY gets the per-file counts of the three steps when given."""
    root = Path(root)
    gone = [
        f"{RULE}: the pack's tool {t} is not installed (setting: {s}); install: {INSTALL}"
        for t, s in TOOLS
        if tool(root, t) is None
    ]
    try:
        found = files(root, patterns(root))
    except CheckError:
        return (
            [("tools", gone)]
            if gone
            else [("paths", [f"{RULE}: not an accepted value (setting: {PROJECT_LINT})"])]
        )
    typed = any(Path(rel).suffix in TYPED for rel, _ in found)
    if typed and tool(root, "tsc") is None:
        gone.append(
            f"{RULE}: the pack's tool tsc is not installed (setting: standards.type); "
            f"install: {INSTALL}"
        )
    if gone:
        return [("tools", gone)]
    if not found:
        return [(NO_FILE, [])]
    lines = floor(root, entry, found)
    own: dict[str, Tally] = {"floor": {str(entry.get("config")): len(lines)} if lines else {}}
    own.update(lint={}, format={}, type={}, **{"type-floor": {}})
    steps = [
        ("floor", lines),
        ("lint", lint(root, found, own["lint"])),
        ("format", format_check(root, found, own["format"])),
    ]
    if typed:
        steps += [
            ("type-floor", type_floor(root, own["type-floor"])),
            ("type", type_check(root, found, own["type"])),
        ]
    else:
        del own["type"], own["type-floor"]
        steps.append(("note", [SKIPPED]))
    if tally is not None:
        tally.update(own)
    return steps
