# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `committed-secrets` step of the `secrets` gate (SPEC-0072 rules 2 and 12 build (f);
REQ-079 AC4; brief #1593, ADR-0673).

Offline, on the project's own files, beside gitleaks and never in its place (prepush's secret
scan stays as it is). It fails on a tracked secret file (the names the data guard refuses,
`guard.secret_file_name`), on an environment file on disk that `.gitignore` does not ignore, on
a tracked file holding a secret shape of the data guard's detectors (`guard.scan_text`) or a
`[guard] patterns` entry, and on an example settings file (`.env.example`, Q-1593-1) whose
values are not empty or `<placeholder>`. A secret shape of only letters and separators is a
word, not a key, and is not counted. Names compare case-folded. Each failure is one path class,
never a path or a value (principle 8); no pattern list grows (principle 9). `counts` gives the
findings per file, so the runner's baseline holds an adopted project's existing ones, named and
counted on every run, while a new one fails as rule 7 (brief #1777, ADR-0743).
"""

from __future__ import annotations

import re
import subprocess  # nosec B404 - fixed argument lists only, no shell
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

import guard  # noqa: E402

from config import guard_patterns  # noqa: E402

RULE = "SPEC-0072 rule 2: a secret or an environment file is committed or left unignored"
EXAMPLE = ".env.example"
SHAPES = ("SECRET", "TOKEN", "JWT")
MAX_BYTES = 1_000_000
PLACEHOLDER = re.compile(r'^(?:|""|\'\'|<[^<>]+>)$')
SETTING = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$")


def files(root: Path, *extra: str) -> list[str]:
    """`git ls-files` with EXTRA options, as `/` paths; every file when ROOT is no repository."""
    cmd = ["git", "-C", str(root), "ls-files", "-z", *extra]
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603 B607 - fixed argv
    if done.returncode == 0:
        return [f for f in done.stdout.split("\0") if f]
    return [] if extra else [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]


def env_file(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1].casefold()
    return name != EXAMPLE and (name == ".env" or name.startswith(".env."))


def example_values(text: str) -> list[tuple[str, str]]:
    """(name, value) of each setting line of an example settings file."""
    out = []
    for raw in text.splitlines():
        m = SETTING.match(raw)
        if m and not raw.lstrip().startswith("#"):
            out.append((m.group(1), m.group(2).strip()))
    return out


def shapes(text: str, patterns: list) -> int:
    """The secret shapes of TEXT: a custom pattern's, or a key shape holding a digit."""
    n = 0
    for f in guard.scan_text(text, patterns):
        value = text[f.start : f.start + f.length]
        n += f.kind.startswith("CUSTOM-") or (f.kind in SHAPES and bool(re.search(r"\d", value)))
    return n


def findings(root: Path) -> list[tuple[str, str, int]]:
    """(path class, file, count) of each finding."""
    tracked = files(root)
    out = [("secret files (tracked)", r, 1) for r in tracked if guard.secret_file_name(r)]
    unignored = files(root, "--others", "--exclude-standard")
    out += [("environment files (not ignored)", r, 1) for r in unignored if env_file(r)]
    patterns = guard_patterns(root)
    for rel in tracked:
        path = root / rel
        if rel.casefold() == EXAMPLE or not path.is_file() or path.stat().st_size > MAX_BYTES:
            continue
        data = path.read_bytes()
        n = 0 if b"\0" in data[:8192] else shapes(data.decode("utf-8", "replace"), patterns)
        out += [("tracked files (a secret shape)", rel, n)] if n else []
    example = root / EXAMPLE
    if example.is_file():
        text = example.read_text(encoding="utf-8", errors="replace")
        n = sum(1 for _, v in example_values(text) if not PLACEHOLDER.match(v))
        out += [("example settings file (a value)", EXAMPLE, n)] if n else []
    return out


ORDER = (
    "secret files (tracked)",
    "environment files (not ignored)",
    "tracked files (a secret shape)",
    "example settings file (a value)",
)
_last: dict[Path, list[tuple[str, str, int]]] = {}  # one scan serves `check` and then `counts`


def problems(root: Path) -> list[str]:
    found = findings(root)
    _last[Path(root).resolve()] = found
    return [c for c in ORDER if any(f[0] == c for f in found)]


HELD = True  # brief #1777: a pass on a baseline that holds findings prints `held`, never `ok`


def check(root: Path, playbook: dict[str, Any]) -> list[str]:
    """The runner's interface: the path classes that fail, none when the step passes."""
    return problems(root)


def counts(root: Path, playbook: dict[str, Any]) -> dict[str, int]:
    """The runner's baseline interface (SPEC-0072 rule 7): the findings per file."""
    found = _last.pop(Path(root).resolve(), None)
    out: dict[str, int] = {}
    for _, rel, n in findings(root) if found is None else found:
        out[rel] = out.get(rel, 0) + n
    return out
