# SPDX-FileCopyrightText: 2026 Balavardhi Raju Gangula
# SPDX-License-Identifier: LicenseRef-AGK-Proprietary
# AGK is built and owned by Balavardhi Raju Gangula. Use only in the repository named in the owner's
# written grant; no use in any other repository without the owner's permission. See LICENSE-AGK.
"""The `pins` step (brief #1592, ADR-0672; SPEC-0072 rule 4 as amendment 201 proposes; REQ-079).

    python3 scripts/agk/gates/pins.py [--root DIR]

The chosen option of the one Accepted stack record (`docs/adr/<n>-stack-options.md`) names its
`Parts:`; the part whose name is a runtime of `STACKS` selects that stack's build file and lock.
The step reads them, offline, and fails on a direct dependency not pinned exactly or not in the
lock, on a missing lock, and on a part of the record whose version differs from the lock's; each
line names the rule and the component class, never a name or a version (principle 8). With no
`[delivery] work_type`, no Accepted record or no runtime it knows, it prints `not run: no stack
chosen`. Lock line ends are normalised. The lock is made by the stack's own tool on the builder's
machine, never here; the build file comes from `kit/templates/stacks/<folder>/` by
`engines.py stack-files`. The runner's interface (`RULE`, `check(root, playbook)`) is that of
`scripts/agk/gates/` (brief #1586); `run_gates.py` runs it where a work type is declared
(`applies`), prints `not run pins: no stack chosen` without a stack (`skipped`), and holds its
per-file `counts` to the baseline (brief #1776, ADR-0742). Installed; it imports only installed
modules.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

from common import utf8_output  # noqa: E402
from playbook_format import declaration  # noqa: E402

RULE = "SPEC-0072 rule 4: the stack's build file and lock are not pinned and in step"
# runtime part name -> its template folder, build file, lock file and reader (amendment 201).
STACKS = {
    "python": ("python-pyproject", "pyproject.toml", "requirements.lock", "requirements"),
    "node": ("node", "package.json", "package-lock.json", "npm"),
}
RECORD = re.compile(r"^docs/adr/\d{4}-stack-options\.md$")
OPTION = re.compile(r"^\s*-\s+Option ([A-Z]) — (.+)$")
CHOSEN = re.compile(r"(?m)^\s*3\.\s+\*\*Chosen\*\*:\s+Option ([A-Z])\b")
ACCEPTED = re.compile(r"(?m)^- Status: Accepted\s*$")
PARTS_KEY = "Parts:"
PARTS_ENDS = ("Why:", "External services:", "Practices:")
VERIFY = "(verify)"
NO_STACK = "no stack chosen"
NOT_RUN = f"not run: {NO_STACK}"
USAGE = "usage: python3 scripts/agk/gates/pins.py [--root DIR]"
PEP508 = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*?)\s*(;.*)?$")
EXACT_PY = re.compile(r"^==\s*([0-9][0-9A-Za-z.+!-]*)$")
EXACT_NPM = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
LOCKED_PY = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s;\\]+)")
UNPINNED = "a direct dependency is not pinned exactly"
STALE = "a direct dependency differs from the lock"
NPM_GROUPS = ("dependencies", "devDependencies", "optionalDependencies")


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def line(rule: str, cls: str) -> str:
    return f"FAIL pins: {rule} (component class: {cls})"


def option_parts(body: str) -> list[tuple[str, str, str]] | None:
    """Brief #1592 answer 1: an option's parts as (name, version, licence), None with no `Parts:`.
    A missing version or licence is ''; `(verify)` marks are dropped (versions read that day)."""
    _, key, tail = body.partition(PARTS_KEY)
    if not key:
        return None
    tail = tail[: min((tail.find(e) for e in PARTS_ENDS if e in tail), default=len(tail))]
    out = []
    for raw in tail.replace(VERIFY, " ").strip(" .;").split(","):
        words = raw.split()
        if words:
            out.append((words[0], words[1] if len(words) > 1 else "", " ".join(words[2:])))
    return out


def chosen(root: Path) -> tuple[tuple[str, str, str, str], list[tuple[str, str, str]]] | None:
    """(the stack's STACKS row, the chosen option's parts) when a stack is chosen, else None."""
    if declaration(root)[0] is None:
        return None
    files = [p for p in root.glob("docs/adr/*.md") if RECORD.match(p.relative_to(root).as_posix())]
    return pick([p.read_text(encoding="utf-8") for p in files])


def pick(texts: list[str]) -> tuple[tuple[str, str, str, str], list[tuple[str, str, str]]] | None:
    """`chosen` on the texts of the stack records, so a reader of a commit (`sbom.py`) shares it."""
    if len(texts) != 1:
        return None
    text = texts[0]
    letter = CHOSEN.search(text)
    if not ACCEPTED.search(text) or not letter:
        return None
    options = [m for ln in text.splitlines() if (m := OPTION.match(ln))]
    body = next((m.group(2) for m in options if m.group(1) == letter.group(1)), "")
    parts = option_parts(body) or []
    rows = [STACKS[p[0]] for p in parts if p[0] in STACKS]
    return (rows[0], parts) if len(rows) == 1 else None


def direct(reader: str, text: str) -> list[tuple[str, str | None]]:
    """(name, exact version or None) of each direct dependency of the build file."""
    out: list[tuple[str, str | None]] = []
    if reader == "npm":
        data = json.loads(text)
        for group in NPM_GROUPS:
            for name, spec in (data.get(group) or {}).items():
                ok = isinstance(spec, str) and EXACT_NPM.match(spec)
                out.append((norm(name), spec if ok else None))
        return out
    project = tomllib.loads(text).get("project", {})
    specs = list(project.get("dependencies", []))
    for group in (project.get("optional-dependencies") or {}).values():
        specs += list(group)
    for spec in specs:
        m = PEP508.match(spec)
        if m:
            pin = EXACT_PY.match(m.group(3))
            out.append(
                (norm(m.group(1)), pin.group(1) if pin and "*" not in pin.group(1) else None)
            )
    return out


def locked(reader: str, text: str) -> dict[str, str]:
    """name -> version of each entry of the lock, line ends normalised."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if reader == "npm":
        data = json.loads(text)
        out = {
            norm(key.rsplit("node_modules/", 1)[1]): str(v.get("version"))
            for key, v in (data.get("packages") or {}).items()
            if key.startswith("node_modules/") and isinstance(v, dict)
        }
        for name, v in (data.get("dependencies") or {}).items():  # lockfileVersion 1
            if isinstance(v, dict):
                out.setdefault(norm(name), str(v.get("version")))
        return out
    return {norm(m.group(1)): m.group(2) for ln in text.split("\n") if (m := LOCKED_PY.match(ln))}


def findings(root: Path) -> list[tuple[str, str, str]] | None:
    """(the rule's line, the component class, the file it is held to) of each failure, one per
    dependency or part (brief #1776: the baseline counts them); None when no stack is chosen."""
    found = chosen(Path(root))
    if found is None:
        return None
    (_, build_file, lock_file, reader), parts = found
    build, lock = Path(root) / build_file, Path(root) / lock_file
    try:
        deps = direct(reader, build.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError, AttributeError):
        return [(f"{RULE}: the build file is missing or unreadable", "build file", build_file)]
    try:
        have = locked(reader, lock.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [(f"{RULE}: the lock file is missing", "lock file", lock_file)]
    except (OSError, UnicodeDecodeError, ValueError, AttributeError):
        return [(f"{RULE}: the lock file is unreadable", "lock file", lock_file)]
    out: list[tuple[str, str, str]] = []
    for name, version in deps:
        if version is None:
            out.append((f"{RULE}: {UNPINNED}", "dependency", build_file))
        elif name not in have:
            out.append((f"{RULE}: a direct dependency is not in the lock", "dependency", lock_file))
        elif have[name] != version:
            out.append((f"{RULE}: {STALE}", "dependency", lock_file))
    for name, version, _ in parts:
        if norm(name) in have and have[norm(name)] != version:
            why = f"{RULE}: a part of the Accepted stack record differs from the lock"
            out.append((why, "stack part", lock_file))
    return out


def problems(root: Path) -> list[str] | None:
    """The failure lines, or None when no stack is chosen (the step is not run)."""
    found = findings(root)
    return None if found is None else sorted({line(r, c) for r, c, _ in found})


def applies(root: Path) -> bool:
    """Brief #1776 answer 1: the runner holds the step where a work type is declared."""
    return declaration(Path(root))[0] is not None


def skipped(root: Path) -> str | None:
    """Brief #1776 answer 2: with no stack chosen the runner prints a not-run row, never `ok`."""
    return NO_STACK if chosen(Path(root)) is None else None


def check(root: Path, playbook: dict[str, Any]) -> list[tuple[str, str]]:
    """The runner's interface: (the rule and component class, the file's path class) of each."""
    return sorted({(f"{r} (component class: {c})", f) for r, c, f in findings(root) or []})


def counts(root: Path, playbook: dict[str, Any]) -> dict[str, int]:
    """Brief #1776 answer 3: the findings per build file or lock, for the baseline (rule 7)."""
    out: dict[str, int] = {}
    for _, _, held in findings(root) or []:
        out[held] = out.get(held, 0) + 1
    return out


def main(argv: list[str] | None = None) -> int:
    utf8_output()
    args = list(sys.argv[1:] if argv is None else argv)
    if args and not (len(args) == 2 and args[0] == "--root" and args[1]):
        print(USAGE, file=sys.stderr)
        return 2
    root = Path(args[1]) if args else Path.cwd()
    found = problems(root)
    if found is None:
        print(f"pins: {NOT_RUN}")
        return 0
    for item in found:
        print(item)
    if found:
        return 1
    print("ok pins")
    return 0


if __name__ == "__main__":
    sys.exit(main())
