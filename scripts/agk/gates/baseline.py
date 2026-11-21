# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The baseline of an adopted project's findings (SPEC-0072 rule 7; REQ-079 AC5; brief #1600,
ADR-0680). Installed with `run_gates.py`; standard library only, so `check_protected_changes.py`
reads it too.

`config/agk-baseline/<gate id>.txt` holds one line `<path> <count>` per file with findings, the
path with forward slashes, the lines sorted bytewise, so two machines write the same file. A
gate id's runs of other characters than `a-z0-9` are `-` in its file name. The files are the
project's (SPEC-0071 rule 2); the runner writes one only in `mode = "adopt"` and only when it is
missing, and `run_gates.py --baseline` writes missing ones and lowers lines, never raising one.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

FOLDER = "config/agk-baseline"
RULE = "SPEC-0072 rule 7: a finding is new or its count rose against the baseline"
CLASS = f"{FOLDER}/"


def name(gate_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", gate_id.lower()).strip("-")


def path(root: Path, gate_id: str) -> Path:
    return Path(root) / FOLDER / f"{name(gate_id)}.txt"


def text(counts: dict[str, int]) -> str:
    rows = {p.replace("\\", "/"): n for p, n in counts.items() if n > 0}
    return "".join(f"{p} {rows[p]}\n" for p in sorted(rows, key=lambda p: p.encode("utf-8")))


def parse(body: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for line in body.splitlines():
        rel, _, count = line.rstrip().rpartition(" ")
        if rel and count.isdigit():
            out[rel] = int(count)
    return out


def read(root: Path, gate_id: str) -> dict[str, int] | None:
    """The baseline of a gate, or None when it has no file."""
    file = path(root, gate_id)
    return parse(file.read_text(encoding="utf-8")) if file.is_file() else None


def adopted(root: Path) -> bool:
    try:
        data = tomllib.loads((Path(root) / "agk.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return False
    return data.get("mode") == "adopt"


def compare(base: dict[str, int], counts: dict[str, int]) -> tuple[int, int]:
    """(files over their line, files under it): a file not listed counts from 0."""
    counts = {p.replace("\\", "/"): n for p, n in counts.items()}
    over = sum(1 for p, n in counts.items() if n > base.get(p, 0))
    under = sum(1 for p, n in base.items() if counts.get(p, 0) < n)
    return over, under


def write(root: Path, gate_id: str, counts: dict[str, int]) -> bool:
    """Write a missing file from COUNTS, or lower the lines of an existing one; never raise a
    line or add one. True when the file changed."""
    file = path(root, gate_id)
    base = read(root, gate_id)
    counts = {p.replace("\\", "/"): n for p, n in counts.items()}
    new = text(counts if base is None else {p: min(n, counts.get(p, 0)) for p, n in base.items()})
    if base is not None and new == file.read_text(encoding="utf-8"):
        return False
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(new, encoding="utf-8", newline="\n")
    return True
