# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The Python standards pack (SPEC-0072 rules 6 and 8; REQ-079 AC4; brief #1589, ADR-0669).

`run_gates.py` runs it for the `[[standards]]` entries of `python-pyproject` and `python-pip`
once, and only when the one Accepted stack record chose a Python runtime (`pins.chosen`). Over the
product files that `project_lint_paths` names (unset: the paths of `[architecture] layers`), less
hidden and environment folders and the kit's own `lint_paths`, it runs four steps:

- `floor` (rule 8, Q-S0072-14): the pack's `config` file enables every rule code of `rules` and
  ignores none of them, else it names each missing code;
- `python-lint`: `ruff check` with the pinned codes as `--select`;
- `python-format`: `ruff format --check`;
- `python-type`: `mypy` with `--strict-optional`, `--disallow-untyped-defs` and
  `--disallow-incomplete-defs` (the brief's Q-2: typed from the start, not `--strict`).

Each tool runs as `<this python> -m <tool>` with an argument list, never a shell, so it is the
same on Windows, WSL and macOS, and writes no cache. A tool missing from this Python is a failure
naming the tool and the setting, never a silent pass. A failure names the rule code and the path
class (the glob the file fell under), never a file name or a value (principle 8).

With a `tally` dict, `run` also fills `{step: {file: count}}` for `lint`, `format` and `type`, the
per-file counts the runner holds to the baseline (SPEC-0072 rule 7; brief #1600, ADR-0680).
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

from common import CheckError, load_config  # noqa: E402

from config import PROJECT_LINT, project_lint_paths  # noqa: E402

from . import pins  # noqa: E402

STACKS = ("python-pyproject", "python-pip")
STEP_NAMES = ("python-lint", "python-format", "python-type")
MYPY_VERSION = "2.3.1"  # config/ci-tools.txt; the `rules` table pins ruff (ADR-0669)
RULE = "SPEC-0072 rule 6"
FLOOR = "SPEC-0072 rule 8"
RUFF_DEFAULT = ["E4", "E7", "E9", "F"]  # ruff's own selection when a configuration sets none
SKIP = {".venv", "venv", "node_modules", "__pycache__", "vendor", "third_party", "build", "dist"}
MYPY_FLAGS = ["--strict-optional", "--disallow-untyped-defs", "--disallow-incomplete-defs"]
RUFF_CODE = re.compile(r"^[A-Z]{1,4}[0-9]{0,4}$")
MYPY_LINE = re.compile(r"^(.+?):\d+(?::\d+)?: error: .*?(?:\[([a-z][a-z-]*)\])?$")


def on(root: Path) -> bool:
    """The pack runs only when the Accepted stack record chose a Python runtime."""
    found = pins.chosen(Path(root))
    return found is not None and found[0] == pins.STACKS["python"]


def installed(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def patterns(root: Path) -> list[str]:
    """`project_lint_paths`, else the paths of the composed `[architecture] layers`."""
    own = project_lint_paths(root)
    if own is not None:
        return own
    import check_playbooks
    import playbook_format

    path = playbook_format.selected(root) or root / playbook_format.FOLDER / "default.toml"
    architecture = check_playbooks.standard(path, root)[0]
    return [p for layer in architecture.get("layers", []) for p in layer.get("paths", [])]


def files(root: Path, globs: list[str]) -> list[tuple[str, str]]:
    """(relative path, the glob it fell under) of each product `.py` file, first glob wins."""
    kit = [p.strip("/") for p in load_config(root)["lint_paths"] if isinstance(p, str)]
    seen: dict[str, str] = {}
    for glob in globs:
        for hit in sorted(root.glob(glob)):
            for path in sorted(hit.rglob("*.py")) if hit.is_dir() else [hit]:
                rel = path.relative_to(root).as_posix()
                parts = rel.split("/")
                hidden = any(p.startswith(".") or p in SKIP for p in parts[:-1])
                if path.suffix != ".py" or not path.is_file() or hidden:
                    continue
                if any(rel == k or rel.startswith(k + "/") for k in kit):
                    continue
                seen.setdefault(rel, glob)
    return sorted(seen.items())


def _tool(root: Path, argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(  # nosec B603 - fixed argument list, no shell
        [sys.executable, "-m", *argv], cwd=root, capture_output=True, text=True, check=False
    )


def _config(root: Path) -> list[str]:
    config = root / "pyproject.toml"
    return ["--config", str(config)] if config.is_file() else ["--isolated"]


def _ruff_table(path: Path) -> dict[str, Any] | None:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    table = data.get("tool", {}).get("ruff") if path.name == "pyproject.toml" else data
    return table if isinstance(table, dict) else None


def floor(root: Path, entry: dict[str, Any]) -> list[str]:
    """Rule 8: the pack's codes the configuration does not enable, or ignores in part."""
    rel = entry.get("config")
    path = root / rel if isinstance(rel, str) else None
    if path is None or not path.is_file():
        return [f"{FLOOR}: the pack's configuration file is missing (setting: standards.config)"]
    try:
        table = _ruff_table(path) or {}
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return [f"{FLOOR}: the pack's configuration file is unreadable (setting: standards.config)"]
    lint: dict[str, Any] = table["lint"] if isinstance(table.get("lint"), dict) else {}

    def codes(key: str) -> list[str]:
        value = lint.get(key, table.get(key))
        return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []

    selected = codes("select") if "select" in lint or "select" in table else list(RUFF_DEFAULT)
    selected += codes("extend-select")
    ignored = codes("ignore") + codes("extend-ignore")
    per_file = lint.get("per-file-ignores", table.get("per-file-ignores"))
    for value in per_file.values() if isinstance(per_file, dict) else []:
        ignored += [v for v in value if isinstance(v, str)] if isinstance(value, list) else []
    out = []
    for code in entry.get("rules", {}).get("codes", []):
        enabled = any(s == "ALL" or code.startswith(s) for s in selected)
        cut = any(i == "ALL" or i.startswith(code) or code.startswith(i) for i in ignored)
        if not enabled or cut:
            shown = code if RUFF_CODE.match(code) else "of the pack"
            out.append(
                f"{FLOOR}: the configuration does not enable the pack's rule {shown} "
                "(setting: standards.config)"
            )
    return out


Tally = dict[str, int]


def _count(tally: Tally | None, rel: str) -> None:
    if tally is not None:
        tally[rel] = tally.get(rel, 0) + 1


def _ruff(
    root: Path, argv: list[str], found: list[tuple[str, str]], step: str, tally: Tally | None = None
) -> list[str]:
    """Ruff's JSON findings as (rule, path class) lines; exit 0 passes, 1 has findings, any other
    exit or output is a failure that the tool did not run, never a silent pass."""
    proc = _tool(root, ["ruff", *argv, "--output-format", "json", *[r for r, _ in found]])
    if proc.returncode == 0:
        return []
    try:
        items = json.loads(proc.stdout) if proc.returncode == 1 else None
    except ValueError:
        items = None
    if not isinstance(items, list) or not items:
        return [f"{RULE}: the {step} tool did not run (setting: standards.{step})"]
    where, base = dict(found), root.resolve()
    out = set()
    for item in items:
        code = str(item.get("code") or "") if isinstance(item, dict) else ""
        path = Path(str(item.get("filename", "") if isinstance(item, dict) else "")).resolve()
        rel = path.relative_to(base).as_posix() if path.is_relative_to(base) else ""
        _count(tally, rel or "product code")
        cls = where.get(rel) or "product code"
        if step == "format":
            out.add(f"{RULE}: the file is not formatted, ruff format (path class: {cls})")
        else:
            shown = code if RUFF_CODE.match(code) else "syntax"
            out.add(f"{RULE}: lint rule {shown} (path class: {cls})")
    return sorted(out)


def lint(
    root: Path, codes: list[str], found: list[tuple[str, str]], tally: Tally | None = None
) -> list[str]:
    argv = ["check", "--no-cache", *_config(root), "--select", ",".join(codes)]
    return _ruff(root, argv, found, "lint", tally)


def format_check(
    root: Path, found: list[tuple[str, str]], tally: Tally | None = None
) -> list[str]:
    argv = ["format", "--check", "--no-cache", *_config(root)]
    return _ruff(root, argv, found, "format", tally)


def type_check(
    root: Path, found: list[tuple[str, str]], tally: Tally | None = None
) -> list[str]:
    config = root / "pyproject.toml"
    argv = ["mypy", *(["--config-file", str(config)] if config.is_file() else []), *MYPY_FLAGS]
    argv += ["--no-error-summary", "--no-color-output", "--show-error-codes"]
    proc = _tool(root, [*argv, "--cache-dir", os.devnull, *[r for r, _ in found]])
    if proc.returncode == 0:
        return []
    where = dict(found)
    out = set()
    for ln in proc.stdout.splitlines():
        m = MYPY_LINE.match(ln)
        if m:
            _count(tally, Path(m.group(1)).as_posix())
            cls = where.get(Path(m.group(1)).as_posix(), "product code")
            out.add(f"{RULE}: type rule {m.group(2) or 'error'} (path class: {cls})")
    return sorted(out) or [f"{RULE}: the type tool did not run (setting: standards.type)"]


def run(
    root: Path, entry: dict[str, Any], tally: dict[str, Tally] | None = None
) -> list[tuple[str, list[str]]]:
    """(step, failure lines) for the floor and the three steps, in order; TALLY gets the
    per-file counts of the three steps when given."""
    root = Path(root)
    tools = (("ruff", "standards.rules"), ("mypy", "standards.type"))
    missing = [f"{RULE}: the pack's tool {t} is not installed (setting: {s})" for t, s in tools]
    gone = [m for (t, _), m in zip(tools, missing, strict=True) if not installed(t)]
    if gone:
        return [("tools", gone)]
    try:
        found = files(root, patterns(root))
    except CheckError:
        return [("paths", [f"{RULE}: not an accepted value (setting: {PROJECT_LINT})"])]
    codes = [c for c in entry.get("rules", {}).get("codes", []) if isinstance(c, str)]
    steps = [("floor", floor(root, entry))]
    if found:
        own: dict[str, Tally] = {"lint": {}, "format": {}, "type": {}}
        steps += [
            ("lint", lint(root, codes, found, own["lint"])),
            ("format", format_check(root, found, own["format"])),
            ("type", type_check(root, found, own["type"])),
        ]
        if tally is not None:
            tally.update(own)
    return steps
