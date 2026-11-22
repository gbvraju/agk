# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The Node standards pack (SPEC-0072 rules 6 and 8; REQ-079; brief #1764, ADR-0739).

`run_gates.py` runs it for the `node` entry of `[[standards]]`, only when the one Accepted stack
record chose a Node runtime (`pins.chosen`) and the product has a `package.json`. Over the product
`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` and `.cjs` files that `project_lint_paths` names (unset: the
paths of `[architecture] layers`, as for Python), less hidden, `node_modules/`, build folders and
the kit's own `lint_paths`, it runs three steps:

- `floor` (rule 8): `eslint --print-config <file>` shows every rule id of `rules.codes` at `error`
  or `warn`, never `off` or absent, else it names each missing id;
- `node-lint`: `eslint --max-warnings 0` (a "File ignored" notice of the config's own `ignores` is
  not counted);
- `node-format`: `prettier --check`.

The `node-type` step is part 2 of the brief's plan; the entry names it and this part runs none.
Each tool is the product's own pinned copy in `node_modules/.bin/` (its exact `devDependencies`,
which the pins gate holds), run with an argument list and never a shell, `npx` or a download. A
tool that is missing fails naming the tool, the setting and `npm ci`, never a version. A failure
names the rule id (or the format) and the path class, never a file name or a value (principle 8).
With a `tally` dict, `run` fills `{step: {file: count}}` for `lint` and `format` (rule 7).
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
from .python_pack import patterns  # noqa: E402,F401 - the one reading of the product's globs

STACKS = ("node",)
STEP_NAMES = ("node-lint", "node-format", "node-type")
RULE = "SPEC-0072 rule 6"
FLOOR = "SPEC-0072 rule 8"
INSTALL = "npm ci"
SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
SKIP = {"node_modules", "build", "dist", "out", "coverage", "vendor", "third_party"}
TOOLS = (("eslint", "standards.rules"), ("prettier", "standards.format"))
RULE_ID = re.compile(r"^(?:@?[a-z0-9-]+/)?[a-z][a-z0-9-]*$")
IGNORED = "File ignored"
OFF = ("off", 0)

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
        return [f"{FLOOR}: the pack's configuration is unreadable (setting: standards.config)"]
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
    proc = _run(root, "prettier", ["--check", *[r for r, _ in found]])
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


def run(
    root: Path, entry: dict[str, Any], tally: dict[str, Tally] | None = None
) -> list[tuple[str, list[str]]]:
    """(step, failure lines) for the floor and the two steps, in order; TALLY gets the per-file
    counts of the two steps when given."""
    root = Path(root)
    gone = [
        f"{RULE}: the pack's tool {t} is not installed (setting: {s}); install: {INSTALL}"
        for t, s in TOOLS
        if tool(root, t) is None
    ]
    if gone:
        return [("tools", gone)]
    try:
        found = files(root, patterns(root))
    except CheckError:
        return [("paths", [f"{RULE}: not an accepted value (setting: {PROJECT_LINT})"])]
    if not found:
        return []
    own: dict[str, Tally] = {"lint": {}, "format": {}}
    steps = [
        ("floor", floor(root, entry, found)),
        ("lint", lint(root, found, own["lint"])),
        ("format", format_check(root, found, own["format"])),
    ]
    if tally is not None:
        tally.update(own)
    return steps
