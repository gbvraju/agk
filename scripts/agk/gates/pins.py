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
chosen`; in a project not adopted, while `docs/architecture.md`, the lock and every declared
dependency are absent, it prints `not run: no foundation yet` (brief #1909, ADR-0791, amendment
234), never `ok`. Lock line ends are normalised. The lock is made by the stack's own tool on the
builder's machine, never here; the build file comes from `kit/templates/stacks/<folder>/` by
`engines.py stack-files`. The runner's interface (`RULE`, `check(root, playbook)`) is that of
`scripts/agk/gates/` (brief #1586); `run_gates.py` runs it where a work type is declared
(`applies`), prints `not run pins: no stack chosen` without a stack (`skipped`), and holds its
per-file `counts` to the baseline (brief #1776, ADR-0742). With a Python runtime the dependency
files are `python_files` (brief #1838, ADR-0768): `pyproject.toml`, the root requirements file, the
files of `[tool.setuptools.dynamic]` and each file a `-r` line names, each read once; a finding is
held to the file it is in. With two runtimes in the chosen option (brief #1932, ADR-0800,
amendment 247), `runtimes` gives each its own folder, the one tracked folder that holds its build
file (the root wins), and the step reads each runtime's build file and lock there, each finding
held to its path from the root; `pick` and `chosen` still read one runtime only. The committed
lock picks the reader (brief #2075, ADR-0865, SPEC-0076 rule 11): `LOCKS` lists per runtime its
lock files in order, the first present in the runtime's folder gives the row, so `pyproject.toml`
with `uv.lock` is read by `uv` and `package.json` with `pnpm-lock.yaml` by `pnpm`; with none, the
`STACKS` row. Installed; it imports only installed modules.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - fixed argument list only, no shell
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # isolated mode (-I) leaves it off

from common import utf8_output  # noqa: E402
from playbook_format import declaration  # noqa: E402

from gates import baseline  # noqa: E402

RULE = "SPEC-0072 rule 4: the stack's build file and lock are not pinned and in step"
# runtime part name -> its template folder, build file, lock file and reader (amendment 201).
STACKS = {
    "python": ("python-pyproject", "pyproject.toml", "requirements.lock", "requirements"),
    "node": ("node", "package.json", "package-lock.json", "npm"),
}
# brief #2075 answer 1 (ADR-0865): per runtime its lock files in order with their readers; the
# first is the `STACKS` row's, so a folder with two locks reads today's (Q-PH-3).
LOCKS = {
    "python": (("requirements.lock", "requirements"), ("uv.lock", "uv")),
    "node": (("package-lock.json", "npm"), ("pnpm-lock.yaml", "pnpm")),
}
JS_READERS = ("npm", "pnpm")  # a `package.json` build file, read as npm's
# brief #2075 answer 3: pnpm 9's lock form only (verify: the version pnpm 9 and 10 write).
PNPM_VERSION = re.compile(r"""^lockfileVersion:\s*(['"]?)9\.0\1\s*$""")
# brief #1843 (ADR-0771): the one table of a runtime's common spellings, case-folded -> its key.
RUNTIME_NAMES = {
    "node": "node",
    "node.js": "node",
    "nodejs": "node",
    "python": "python",
    "python3": "python",
    "cpython": "python",
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
# brief #1909 (ADR-0791, amendment 234): in a project not adopted, before the foundation.
NO_FOUNDATION = "no foundation yet"
ARCHITECTURE = "docs/architecture.md"  # `layers.RECORD`: layers imports this module
USAGE = "usage: python3 scripts/agk/gates/pins.py [--root DIR]"
PEP508 = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*?)\s*(;.*)?$")
EXACT_PY = re.compile(r"^==\s*([0-9][0-9A-Za-z.+!-]*)$")
EXACT_NPM = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
LOCKED_PY = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s;\\]+)")
UNPINNED = "a direct dependency is not pinned exactly"
STALE = "a direct dependency differs from the lock"
NPM_GROUPS = ("dependencies", "devDependencies", "optionalDependencies")
REQUIREMENTS = "requirements.txt"  # brief #1838: the one name of the root requirements file
INCLUDES = ("--requirement", "-r")
EDITABLE = ("-e", "--editable")
COMMENT = re.compile(r"(^|\s)#.*$")
# brief #1932 answer 2: the build files that place a runtime in a folder, the first name first.
PLACES = {"node": ("package.json",), "python": ("pyproject.toml", REQUIREMENTS)}
SPLIT = "a runtime's build file is in more than one folder"


class Runtime(NamedTuple):
    """Brief #1932 answer 1: one runtime of the chosen option, its folder ('' for the root), the
    build file read there, the parts compared with its lock (the runtime part and those after it),
    whether it is in two folders, and every part of the option (the licences' names)."""

    row: tuple[str, str, str, str]
    folder: str
    build: str
    parts: list[tuple[str, str, str]]
    split: bool = False
    option: list[tuple[str, str, str]] = []

    def at(self, rel: str) -> str:
        return f"{self.folder}/{rel}" if self.folder else rel


class Unreadable(Exception):
    """A Python dependency file that cannot be read, held to the file that names it."""

    def __init__(self, held: str) -> None:
        super().__init__(held)
        self.held = held


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def line(rule: str, cls: str) -> str:
    return f"FAIL pins: {rule} (component class: {cls})"


def option_parts(body: str) -> list[tuple[str, str, str]] | None:
    """Brief #1592 answer 1: an option's parts as (name, version, licence), None with no `Parts:`.
    A missing version or licence is ''; `(verify)` marks are dropped (versions read that day).
    A name of `RUNTIME_NAMES` but for case is its `STACKS` key (`Node.js` -> `node`, briefs #1778
    and #1843); every other name is kept as written."""
    _, key, tail = body.partition(PARTS_KEY)
    if not key:
        return None
    tail = tail[: min((tail.find(e) for e in PARTS_ENDS if e in tail), default=len(tail))]
    out = []
    for raw in tail.replace(VERIFY, " ").strip(" .;").split(","):
        words = raw.split()
        if words:
            name = RUNTIME_NAMES.get(words[0].casefold(), words[0])
            out.append((name, words[1] if len(words) > 1 else "", " ".join(words[2:])))
    return out


def records(root: Path) -> list[str] | None:
    """The texts of the stack records, None with no declared work type."""
    if declaration(root)[0] is None:
        return None
    files = [p for p in root.glob("docs/adr/*.md") if RECORD.match(p.relative_to(root).as_posix())]
    return [p.read_text(encoding="utf-8") for p in files]


def chosen(root: Path) -> tuple[tuple[str, str, str, str], list[tuple[str, str, str]]] | None:
    """(the stack's STACKS row, the chosen option's parts) when one runtime is chosen, else None."""
    texts = records(root)
    return None if texts is None else pick(texts)


def chosen_parts(texts: list[str]) -> list[tuple[str, str, str]] | None:
    """The parts of the one Accepted record's chosen option; None with no such option."""
    if len(texts) != 1:
        return None
    text = texts[0]
    letter = CHOSEN.search(text)
    if not ACCEPTED.search(text) or not letter:
        return None
    options = [m for ln in text.splitlines() if (m := OPTION.match(ln))]
    body = next((m.group(2) for m in options if m.group(1) == letter.group(1)), "")
    return option_parts(body) or []


def pick(texts: list[str]) -> tuple[tuple[str, str, str, str], list[tuple[str, str, str]]] | None:
    """`chosen` on the texts of the stack records, so a reader of a commit (`sbom.py`) shares it."""
    parts = chosen_parts(texts)
    rows = [STACKS[p[0]] for p in parts or [] if p[0] in STACKS]
    return (rows[0], parts or []) if len(rows) == 1 else None


def tracked(root: Path) -> list[str]:
    """The tracked files under the root (`git ls-files`), else every file there (no git)."""
    proc = subprocess.run(  # nosec B603 B607 - fixed argument list, no shell
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True, check=False
    )
    if proc.returncode == 0:
        return [f for f in proc.stdout.split("\0") if f]
    base = Path(root)
    return [
        p.relative_to(base).as_posix()
        for p in base.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(base).parts
    ]


def place(key: str, files: list[str]) -> tuple[str, str, bool]:
    """Brief #1932 answer 2: (folder, build file, in two folders) of a runtime among the files."""
    split = [f.rpartition("/") for f in files]
    for name in PLACES[key]:
        found = {d for d, _, n in split if n == name}
        folders = sorted(d for d in found if "node_modules" not in d.split("/"))
        if "" in folders:
            return "", name, False
        if folders:
            return folders[0], name, len(folders) > 1
    return "", STACKS[key][1], False


def row_of(key: str, folder: str, build: str, listed: list[str]) -> tuple[str, str, str, str]:
    """Brief #2075 answer 1: the row of the first lock of `LOCKS` in the folder; a later reader
    needs the runtime's own build file (`pyproject.toml` for uv). With none, the `STACKS` row."""
    have = set(listed)
    for lock, reader in LOCKS.get(key, ()):  # a runtime with no LOCKS entry keeps its row
        if (f"{folder}/{lock}" if folder else lock) in have:
            if reader == STACKS[key][3] or build == STACKS[key][1]:
                return (STACKS[key][0], STACKS[key][1], lock, reader)
            break
    return STACKS[key]


def runtimes(texts: list[str], files: Callable[[], list[str]]) -> list[Runtime] | None:
    """Brief #1932 answer 1: one entry per runtime part of the chosen option, in the record's
    order, each part held to the runtime it follows; one runtime keeps the root and every part.
    `files` (the tracked paths) is read for every runtime, its lock choosing the row (brief
    #2075). None exactly as `pick` gives None for any reason but two runtimes."""
    parts = chosen_parts(texts)
    keys = list(dict.fromkeys(p[0] for p in parts or [] if p[0] in STACKS))
    if not keys or parts is None:
        return None
    if len(keys) == 1:
        build = STACKS[keys[0]][1]
        row = row_of(keys[0], "", build, files())
        return [Runtime(row, "", build, parts, False, parts)]
    groups: dict[str, list[tuple[str, str, str]]] = {k: [] for k in keys}
    owner = keys[0]
    for part in parts:
        owner = part[0] if part[0] in STACKS else owner
        groups[owner].append(part)
    listed = files()
    out = []
    for key in keys:
        folder, build, split = place(key, listed)
        out.append(
            Runtime(row_of(key, folder, build, listed), folder, build, groups[key], split, parts)
        )
    return out


def runtimes_of(root: Path) -> list[Runtime] | None:
    texts = records(Path(root))
    return None if texts is None else runtimes(texts, lambda: tracked(Path(root)))


def direct(reader: str, text: str) -> list[tuple[str, str | None]]:
    """(name, exact version or None) of each direct dependency of the build file."""
    out: list[tuple[str, str | None]] = []
    if reader in JS_READERS:
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
    if reader == "uv":  # brief #2075 answer 2 (Q-PH-5): uv installs its groups too (verify)
        data = tomllib.loads(text)
        for group in (data.get("dependency-groups") or {}).values():
            specs += [s for s in group if isinstance(s, str)]  # an `include-group` is skipped
        specs += list(((data.get("tool") or {}).get("uv") or {}).get("dev-dependencies") or [])
    return [r for spec in specs if (r := requirement(spec)) is not None]


def requirement(spec: str) -> tuple[str, str | None] | None:
    """(name, exact version or None) of one PEP 508 requirement; None when it has no name."""
    m = PEP508.match(spec)
    if not m:
        return None
    pin = EXACT_PY.match(m.group(3))
    return norm(m.group(1)), pin.group(1) if pin and "*" not in pin.group(1) else None


def requirement_lines(text: str) -> tuple[list[tuple[str, str | None]], list[str]]:
    """Brief #1838 answer 1: (the requirements, the `-r` files) of a requirements file. Options,
    `-c` files, comments and `--hash=` are not dependencies; `-e .` is the project itself."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\\\n", " ")
    reqs: list[tuple[str, str | None]] = []
    includes: list[str] = []
    for raw in text.split("\n"):
        words = COMMENT.sub("", raw).split()
        if not words:
            continue
        first = words[0]
        flag = next((f for f in INCLUDES if first.startswith(f)), "")
        if flag and (first == flag or flag == "-r" or first[len(flag)] == "="):
            includes.append(first[len(flag) :].lstrip("=") or " ".join(words[1:2]))
        elif first in EDITABLE:
            if words[1:2] != ["."]:
                reqs.append((" ".join(words[1:2]), None))
        elif not first.startswith("-"):
            spec = " ".join(words).split(" --")[0]
            reqs.append(requirement(spec) or (spec, None))
    return reqs, includes


def dynamic_files(data: dict[str, Any]) -> list[str]:
    """The `file` entries of `[tool.setuptools.dynamic]` dependencies and optional groups."""
    table = ((data.get("tool") or {}).get("setuptools") or {}).get("dynamic") or {}
    entries = [table.get("dependencies")]
    entries += list((table.get("optional-dependencies") or {}).values())
    out: list[str] = []
    for entry in entries:
        files = entry.get("file") if isinstance(entry, dict) else None
        out += [files] if isinstance(files, str) else [f for f in files or [] if isinstance(f, str)]
    return out


def python_files(root: Path, build: str = STACKS["python"][1]) -> list[tuple[str, str]]:
    """Brief #1838 answer 4: (path from the root, text) of each Python dependency file, the build
    file first, each once; raises `Unreadable` with the file that names one it cannot read. A
    folder placed by its `requirements.txt` alone (brief #1932 answer 2) starts there."""
    root = Path(root).resolve()
    out: list[tuple[str, str]] = []
    queue: list[tuple[Path, str]] = [(root / REQUIREMENTS, REQUIREMENTS)]
    seen: set[Path] = set()
    if build != REQUIREMENTS:
        try:
            text = (root / build).read_text(encoding="utf-8")
            named = dynamic_files(tomllib.loads(text))
        except (OSError, UnicodeDecodeError, ValueError, AttributeError) as exc:
            raise Unreadable(build) from exc
        out = [(build, text)]
        queue = [(root / f, build) for f in named]
        if (root / REQUIREMENTS).is_file():
            queue.insert(0, (root / REQUIREMENTS, build))
        seen = {(root / build).resolve()}
    while queue:
        path, held = queue.pop(0)
        path = Path(path).resolve()
        if path in seen:
            continue
        if not path.is_relative_to(root) or not path.is_file():
            raise Unreadable(held)
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise Unreadable(held) from exc
        seen.add(path)
        out.append((rel, text))
        for name in requirement_lines(text)[1]:
            if not name:
                raise Unreadable(rel)
            queue.append((path.parent / name, rel))
    return out


def declared(root: Path, reader: str, build_file: str) -> list[tuple[str, str | None, str]]:
    """(name, exact version or None, the file it is in) of each direct dependency: a name floating
    in any file is one row, held to the first such file (brief #1838 answer 6); else one row per
    distinct version. The uv reader reads `pyproject.toml` alone (brief #2075 answer 2)."""
    if reader in JS_READERS:
        text = (Path(root) / build_file).read_text(encoding="utf-8")
        return [(n, v, build_file) for n, v in direct(reader, text)]
    rows: list[tuple[str, str | None, str]] = []
    if reader == "uv":
        text = (Path(root) / build_file).read_text(encoding="utf-8")
        rows = [(n, v, build_file) for n, v in direct(reader, text)]
    for rel, text in python_files(root, build_file) if reader != "uv" else []:
        toml = rel == build_file != REQUIREMENTS
        found = direct(reader, text) if toml else requirement_lines(text)[0]
        rows += [(n, v, rel) for n, v in found]
    floats: dict[str, str] = {}
    for name, version, rel in rows:
        if version is None:
            floats.setdefault(name, rel)
    out = [(n, None, rel) for n, rel in floats.items()]
    pinned = {(n, v): rel for n, v, rel in reversed(rows) if n not in floats}
    return out + [(n, v, rel) for (n, v), rel in pinned.items()]


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
    if reader == "uv":  # brief #2075 answer 2: each `[[package]]`'s name and version
        packages = tomllib.loads(text).get("package")
        if not isinstance(packages, list):
            raise ValueError("no package list")
        return {
            norm(p["name"]): str(p["version"])
            for p in packages
            if isinstance(p, dict) and isinstance(p.get("name"), str) and "version" in p
        }
    if reader == "pnpm":
        return pnpm_locked(text)
    return {norm(m.group(1)): m.group(2) for ln in text.split("\n") if (m := LOCKED_PY.match(ln))}


def pnpm_locked(text: str) -> dict[str, str]:
    """Brief #2075 answer 3: name -> version of each key two spaces in under the top-level
    `packages:` of a `lockfileVersion: '9.0'` lock, `<name>@<version>:`, quotes and a peer
    suffix from `(` removed, split at the last `@` after the first character. Another version,
    or no `packages:`, raises ValueError (the lock is unreadable)."""
    lines = text.split("\n")
    top = [ln for ln in lines if ln and not ln.startswith((" ", "#"))]
    if not top or not PNPM_VERSION.match(top[0].rstrip()):
        raise ValueError("not a pnpm 9 lock")
    out: dict[str, str] = {}
    inside = seen = False
    for ln in lines:
        if ln and not ln.startswith((" ", "#")):
            inside = ln.rstrip() == "packages:"
            seen = seen or inside
        elif (
            inside
            and ln.startswith("  ")
            and ln[2:3] not in (" ", "#", "")
            and ln.rstrip().endswith(":")
        ):
            key = ln.strip()[:-1].strip("'\"").split("(", 1)[0]
            at = key.rfind("@")
            if at > 0:
                out.setdefault(norm(key[:at]), key[at + 1 :])
    if not seen:
        raise ValueError("no packages")
    return out


def waiting(root: Path) -> bool:
    """Brief #1909 answer 2: True only in a project not adopted, with a stack chosen, while the
    architecture record and the lock are absent and the build file is absent or declares no
    direct dependency. A build file that cannot be read never waits; any one dependency, a lock
    or the record ends the wait (answer 3)."""
    root = Path(root)
    found = runtimes_of(root)
    if found is None or baseline.adopted(root) or (root / ARCHITECTURE).exists():
        return False
    return all(waits(root / one.folder, one) for one in found)  # brief #1932: every runtime


def waits(base: Path, one: Runtime) -> bool:
    _, build_file, lock_file, reader = one.row
    if one.split or (base / lock_file).exists():
        return False
    if not (base / one.build).exists():
        return reader == "npm" or not (base / REQUIREMENTS).exists()
    try:
        return not declared(base, reader, one.build)
    except (Unreadable, OSError, UnicodeDecodeError, ValueError, AttributeError):
        return False


def findings(root: Path) -> list[tuple[str, str, str]] | None:
    """(the rule's line, the component class, the file it is held to) of each failure, one per
    dependency or part (brief #1776: the baseline counts them); None when no stack is chosen or
    the project waits for its foundation (brief #1909)."""
    found = runtimes_of(Path(root))
    if found is None or waiting(Path(root)):
        return None
    return [f for one in found for f in runtime_findings(Path(root), one)]


def runtime_findings(root: Path, one: Runtime) -> list[tuple[str, str, str]]:
    """Brief #1932 answer 3: today's reading of one runtime, in its folder, held from the root."""
    (_, _, lock_file, reader), build_file, parts = one.row, one.build, one.parts
    if one.split:
        return [(f"{RULE}: {SPLIT}", "build file", one.at(build_file))]
    base = root / one.folder
    try:
        deps = [(n, v, one.at(h)) for n, v, h in declared(base, reader, build_file)]
    except Unreadable as exc:
        held = one.at(exc.held)
        return [(f"{RULE}: the build file is missing or unreadable", "build file", held)]
    except (OSError, UnicodeDecodeError, ValueError, AttributeError):
        held = one.at(build_file)
        return [(f"{RULE}: the build file is missing or unreadable", "build file", held)]
    lock_file = one.at(lock_file)
    try:
        have = locked(reader, (root / lock_file).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [(f"{RULE}: the lock file is missing", "lock file", lock_file)]
    except (OSError, UnicodeDecodeError, ValueError, AttributeError):
        return [(f"{RULE}: the lock file is unreadable", "lock file", lock_file)]
    out: list[tuple[str, str, str]] = []
    for name, version, held in deps:
        if version is None:
            out.append((f"{RULE}: {UNPINNED}", "dependency", held))
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
    """Brief #1776 answer 2: with no stack chosen the runner prints a not-run row, never `ok`;
    brief #1909: so does a new project that waits for its foundation."""
    if runtimes_of(Path(root)) is None:
        return NO_STACK
    return NO_FOUNDATION if waiting(Path(root)) else None


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
        print(f"pins: not run: {skipped(root) or NO_STACK}")
        return 0
    for item in found:
        print(item)
    if found:
        return 1
    print("ok pins")
    return 0


if __name__ == "__main__":
    sys.exit(main())
