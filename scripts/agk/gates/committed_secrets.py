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
never a path or a value (principle 8); no pattern list grows (principle 9). With `mode = "adopt"`
the findings are held until brief #1600's baseline, so nothing existing goes red.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

import guard  # noqa: E402
from common import load_config  # noqa: E402

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
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603 - fixed argv
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


def shaped(text: str, patterns: list) -> bool:
    for f in guard.scan_text(text, patterns):
        value = text[f.start : f.start + f.length]
        if f.kind.startswith("CUSTOM-") or (f.kind in SHAPES and re.search(r"\d", value)):
            return True
    return False


def problems(root: Path) -> list[str]:
    tracked = files(root)
    out = []
    if any(guard.secret_file_name(rel) for rel in tracked):
        out.append("secret files (tracked)")
    if any(env_file(rel) for rel in files(root, "--others", "--exclude-standard")):
        out.append("environment files (not ignored)")
    patterns = guard_patterns(root)
    for rel in tracked:
        path = root / rel
        if rel.casefold() == EXAMPLE or not path.is_file() or path.stat().st_size > MAX_BYTES:
            continue
        data = path.read_bytes()
        if b"\0" not in data[:8192] and shaped(data.decode("utf-8", "replace"), patterns):
            out.append("tracked files (a secret shape)")
            break
    example = root / EXAMPLE
    if example.is_file():
        text = example.read_text(encoding="utf-8", errors="replace")
        if any(not PLACEHOLDER.match(v) for _, v in example_values(text)):
            out.append("example settings file (a value)")
    return out


def check(root: Path, playbook: dict[str, Any]) -> list[str]:
    """The runner's interface: the path classes that fail, none when the step passes."""
    found = problems(root)
    return [] if load_config(root)["mode"] == "adopt" else found
